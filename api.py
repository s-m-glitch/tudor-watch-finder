"""
Tudor Watch Finder - Web API
FastAPI backend for the web interface
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading

from config import WATCH_CONFIG, SEARCH_CONFIG
from scraper import TudorScraper, Retailer
from filter import RetailerFilter
from phone_caller import InventoryChecker, InventoryStatus, BlandAICaller

app = FastAPI(
    title="Tudor Watch Finder",
    description="Find Tudor Ranger 36mm (beige dial) at nearby retailers",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files - THIS WAS MISSING!
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================
# GLOBAL IN-MEMORY CACHE
# This persists for the lifetime of the server process
# ============================================================
class RetailerCache:
    """Thread-safe in-memory cache for retailers"""
    def __init__(self):
        self._retailers: List[Retailer] = []
        self._loaded: bool = False
        self._loading: bool = False
        self._lock = threading.Lock()
        self._load_time: Optional[datetime] = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded and len(self._retailers) > 0

    @property
    def is_loading(self) -> bool:
        return self._loading

    def get_retailers(self) -> List[Retailer]:
        return self._retailers

    def set_retailers(self, retailers: List[Retailer]):
        with self._lock:
            self._retailers = retailers
            self._loaded = True
            self._loading = False
            self._load_time = datetime.now()
            print(f"Cache updated: {len(retailers)} retailers loaded at {self._load_time}")

    def start_loading(self) -> bool:
        """Returns True if this call started the loading, False if already loading"""
        with self._lock:
            if self._loading:
                return False
            self._loading = True
            return True

    def stop_loading(self):
        with self._lock:
            self._loading = False


# Global cache instance
retailer_cache = RetailerCache()

# In-memory storage for call jobs
call_jobs = {}


class SearchRequest(BaseModel):
    zip_code: str
    radius_miles: float = 50
    api_key: Optional[str] = None


class CallRequest(BaseModel):
    zip_code: str
    radius_miles: float = 50
    api_key: str
    max_calls: int = 5


class RetailerResponse(BaseModel):
    name: str
    address: str
    city: str
    state: str
    phone: Optional[str]
    distance_miles: float
    retailer_type: str


def load_retailers_sync() -> List[Retailer]:
    """Synchronously load/scrape retailers"""
    print("Starting retailer scrape...")
    scraper = TudorScraper()
    retailers = scraper.scrape_all_retailers(max_workers=5)
    print(f"Scrape complete: {len(retailers)} retailers found")
    print(f"  - With phone numbers: {sum(1 for r in retailers if r.phone)}")
    print(f"  - With coordinates: {sum(1 for r in retailers if r.latitude)}")
    return retailers


def get_retailers() -> List[Retailer]:
    """Get retailers from cache or trigger a scrape"""

    # If already loaded, return from cache immediately
    if retailer_cache.is_loaded:
        print(f"Returning {len(retailer_cache.get_retailers())} retailers from cache")
        return retailer_cache.get_retailers()

    # If already loading, wait for it to complete
    if retailer_cache.is_loading:
        print("Retailers are being loaded by another request, waiting...")
        # Wait up to 5 minutes for loading to complete
        for _ in range(300):
            if retailer_cache.is_loaded:
                return retailer_cache.get_retailers()
            import time
            time.sleep(1)
        raise HTTPException(status_code=503, detail="Timeout waiting for retailers to load")

    # Start loading
    if retailer_cache.start_loading():
        try:
            retailers = load_retailers_sync()
            retailer_cache.set_retailers(retailers)
            return retailers
        except Exception as e:
            retailer_cache.stop_loading()
            raise HTTPException(status_code=500, detail=f"Failed to load retailers: {str(e)}")
    else:
        # Another thread started loading, wait for it
        for _ in range(300):
            if retailer_cache.is_loaded:
                return retailer_cache.get_retailers()
            import time
            time.sleep(1)
        raise HTTPException(status_code=503, detail="Timeout waiting for retailers to load")


@app.on_event("startup")
async def startup_event():
    """Pre-load retailers when the server starts"""
    print("=" * 60)
    print("Tudor Watch Finder API Starting")
    print("=" * 60)
    # We'll load retailers on first request instead of startup
    # to avoid blocking the server start
    print("Retailers will be loaded on first search request")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")


@app.get("/api/watch")
async def get_watch_info():
    """Get information about the target watch"""
    return {
        "watch": WATCH_CONFIG,
        "default_search": SEARCH_CONFIG
    }


@app.get("/api/cache-status")
async def cache_status():
    """Check the status of the retailer cache"""
    return {
        "loaded": retailer_cache.is_loaded,
        "loading": retailer_cache.is_loading,
        "count": len(retailer_cache.get_retailers()) if retailer_cache.is_loaded else 0
    }


@app.get("/api/search")
async def search_retailers(zip_code: str, radius: float = 50):
    """Search for retailers near a zip code"""
    try:
        # Get retailers (from cache or scrape)
        retailers = get_retailers()

        # Filter by location
        filter = RetailerFilter()
        filtered = filter.filter_by_zip_code(
            retailers,
            zip_code,
            radius
        )

        results = []
        for retailer, distance in filtered:
            results.append({
                "name": retailer.name,
                "address": retailer.address,
                "city": retailer.city,
                "state": retailer.state,
                "zip_code": retailer.zip_code,
                "phone": retailer.phone,
                "website": retailer.website,
                "distance": round(distance, 1),
                "retailer_type": retailer.retailer_type,
                "has_phone": bool(retailer.phone)
            })

        return {
            "zip_code": zip_code,
            "radius": radius,
            "total": len(results),
            "retailers": results
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/call")
async def make_call(retailer_name: str, phone: str, background_tasks: BackgroundTasks):
    """Start a phone call to check inventory at a single retailer"""
    from config import BLAND_AI_CONFIG

    api_key = BLAND_AI_CONFIG.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="Bland AI API key not configured")

    try:
        caller = BlandAICaller(api_key)

        # Start the call
        call_id = caller.start_call(phone, retailer_name)

        if not call_id:
            raise HTTPException(status_code=500, detail="Failed to start call")

        return {
            "call_id": call_id,
            "retailer_name": retailer_name,
            "phone": phone,
            "status": "started"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start call: {str(e)}")


@app.get("/api/call/{call_id}")
async def get_call_status(call_id: str):
    """Get the status of a phone call"""
    from config import BLAND_AI_CONFIG

    api_key = BLAND_AI_CONFIG.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="Bland AI API key not configured")

    try:
        caller = BlandAICaller(api_key)
        result = caller.get_call_result(call_id)

        if result is None:
            return {
                "call_id": call_id,
                "status": "in_progress"
            }

        return {
            "call_id": call_id,
            "status": "completed" if result.status != InventoryStatus.UNKNOWN else "failed",
            "inventory_status": result.status.value,
            "summary": result.summary,
            "retailer_name": result.retailer_name
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get call status: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "retailers_cached": retailer_cache.is_loaded,
        "retailers_count": len(retailer_cache.get_retailers()) if retailer_cache.is_loaded else 0
    }


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
