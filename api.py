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

from config import WATCH_CONFIG, WATCHES, DEFAULT_WATCH, SEARCH_CONFIG
from scraper import TudorScraper, Retailer
from filter import RetailerFilter
from phone_caller import InventoryChecker, InventoryStatus, BlandAICaller
from website_scraper import WebsiteStockChecker, WebsiteStockStatus
from summarizer import summarize_transcript

# Import BLAND_CONFIG safely (note: config.py uses BLAND_CONFIG, not BLAND_AI_CONFIG)
try:
    from config import BLAND_CONFIG
except ImportError:
    BLAND_CONFIG = {}

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

# Mount static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================
# STARTUP: Log environment variables for debugging
# ============================================================
print("=" * 60)
print("STARTUP: Checking environment variables...")
print(f"  BLAND_API_KEY present: {bool(os.environ.get('BLAND_API_KEY'))}")
print(f"  ANTHROPIC_API_KEY present: {bool(os.environ.get('ANTHROPIC_API_KEY'))}")
# Check for common variations/typos
for key in os.environ:
    if 'ANTHROPIC' in key.upper() or 'CLAUDE' in key.upper():
        print(f"  Found env var: {key} = {os.environ[key][:10]}...")
print("=" * 60)

# ============================================================
# GLOBAL IN-MEMORY CACHE
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

# In-memory storage for call jobs (for both single and batch calls)
call_jobs = {}

# Website stock checker instance
website_stock_checker = WebsiteStockChecker()


# ============================================================
# Request Models
# ============================================================
class SearchRequest(BaseModel):
    zip_code: str
    radius_miles: float = 50
    api_key: Optional[str] = None


class CallRequest(BaseModel):
    """For batch calls to multiple retailers"""
    zip_code: str
    radius_miles: float = 50
    api_key: str
    max_calls: int = 5


class SingleCallRequest(BaseModel):
    """For calling a single retailer"""
    retailer_name: str
    phone: str
    watch_reference: Optional[str] = None  # Which watch to ask about


# ============================================================
# Helper Functions
# ============================================================
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
    if retailer_cache.is_loaded:
        print(f"Returning {len(retailer_cache.get_retailers())} retailers from cache")
        return retailer_cache.get_retailers()

    if retailer_cache.is_loading:
        print("Retailers are being loaded by another request, waiting...")
        for _ in range(300):
            if retailer_cache.is_loaded:
                return retailer_cache.get_retailers()
            import time
            time.sleep(1)
        raise HTTPException(status_code=503, detail="Timeout waiting for retailers to load")

    if retailer_cache.start_loading():
        try:
            retailers = load_retailers_sync()
            retailer_cache.set_retailers(retailers)
            return retailers
        except Exception as e:
            retailer_cache.stop_loading()
            raise HTTPException(status_code=500, detail=f"Failed to load retailers: {str(e)}")
    else:
        for _ in range(300):
            if retailer_cache.is_loaded:
                return retailer_cache.get_retailers()
            import time
            time.sleep(1)
        raise HTTPException(status_code=503, detail="Timeout waiting for retailers to load")


def get_bland_api_key() -> str:
    """Get Bland AI API key from config"""
    if BLAND_CONFIG and BLAND_CONFIG.get("api_key"):
        return BLAND_CONFIG["api_key"]
    return os.environ.get("BLAND_API_KEY", "")


# ============================================================
# API Endpoints
# ============================================================
@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("Tudor Watch Finder API Starting")
    print("=" * 60)
    print("Retailers will be loaded on first search request")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")


@app.get("/api/watches")
async def get_all_watches():
    """Get all available watches"""
    return {
        "watches": list(WATCHES.values()),
        "default": DEFAULT_WATCH
    }


@app.get("/api/watch")
async def get_watch_info(reference: Optional[str] = None):
    """Get information about a specific watch (or default)"""
    if reference and reference in WATCHES:
        watch = WATCHES[reference]
    else:
        watch = WATCH_CONFIG
    return {
        "watch": watch,
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
    """Search for retailers near a zip code (GET version)"""
    print(f"[SEARCH] Request: zip_code={zip_code}, radius={radius}")
    try:
        retailers = get_retailers()
        print(f"[SEARCH] Got {len(retailers)} total retailers from cache")
        filter = RetailerFilter()
        filtered = filter.filter_by_zip_code(retailers, zip_code, radius)
        print(f"[SEARCH] Filtered to {len(filtered)} retailers within {radius} miles of {zip_code}")

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
                "has_phone": bool(retailer.phone),
                "has_website_scraper": website_stock_checker.has_scraper(retailer.name)
            })

        print(f"[SEARCH] Returning {len(results)} retailers")
        return {
            "zip_code": zip_code,
            "radius": radius,
            "total": len(results),
            "retailers": results
        }

    except ValueError as e:
        print(f"[SEARCH] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[SEARCH] Exception: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/search")
async def search_retailers_post(request: SearchRequest):
    """Search for retailers near a zip code (POST version)"""
    try:
        retailers = get_retailers()
        filter = RetailerFilter()
        filtered = filter.filter_by_zip_code(retailers, request.zip_code, request.radius_miles)

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
                "distance_miles": round(distance, 1),
                "retailer_type": retailer.retailer_type,
                "has_phone": bool(retailer.phone)
            })

        return {
            "zip_code": request.zip_code,
            "radius_miles": request.radius_miles,
            "total_retailers": len(results),
            "with_phone": sum(1 for r in results if r["has_phone"]),
            "retailers": results[:20],
            "has_more": len(results) > 20,
            "cache_status": "loaded" if retailer_cache.is_loaded else "loading"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/call")
async def make_single_call(request: SingleCallRequest, background_tasks: BackgroundTasks):
    """Start a phone call to check inventory at a SINGLE retailer"""
    api_key = get_bland_api_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Bland AI API key not configured")

    # Get watch config - use specified reference or default
    print(f"[API] Received watch_reference: {request.watch_reference}")
    watch_ref = request.watch_reference or DEFAULT_WATCH
    if watch_ref not in WATCHES:
        print(f"[API] Watch ref '{watch_ref}' not in WATCHES, using default")
        watch_ref = DEFAULT_WATCH
    watch_config = WATCHES[watch_ref]
    print(f"[API] Using watch: {watch_config['dial']} ({watch_ref})")

    try:
        # Create a unique job ID for this call
        job_id = f"call_{datetime.now().timestamp()}"

        # Initialize job status
        call_jobs[job_id] = {
            "status": "starting",
            "retailer_name": request.retailer_name,
            "phone": request.phone,
            "watch_reference": watch_ref,
            "result": None,
            "error": None,
            "started_at": datetime.now().isoformat()
        }

        # Start the call in background
        background_tasks.add_task(
            run_single_call_background,
            job_id,
            request.retailer_name,
            request.phone,
            api_key,
            watch_config
        )

        return {
            "call_id": job_id,
            "retailer_name": request.retailer_name,
            "phone": request.phone,
            "watch_reference": watch_ref,
            "status": "started"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start call: {str(e)}")


def run_single_call_background(job_id: str, retailer_name: str, phone: str, api_key: str, watch_config: dict = None):
    """Background task to make a single phone call (runs synchronously in thread pool)"""
    try:
        watch = watch_config or WATCH_CONFIG
        print(f"[{job_id}] Starting background call to {retailer_name} at {phone}")
        print(f"[{job_id}] Watch config received: {watch.get('dial', 'unknown')} ({watch.get('reference', 'unknown')})")
        print(f"[{job_id}] Watch full_name: {watch['full_name']}")
        call_jobs[job_id]["status"] = "in_progress"

        # Create caller and make the call (this is synchronous and waits for completion)
        print(f"[{job_id}] Creating BlandAICaller...")
        caller = BlandAICaller(api_key, watch_config=watch)
        print(f"[{job_id}] Making call...")
        result = caller.make_call(phone, retailer_name)
        print(f"[{job_id}] Call completed with status: {result.status.value}")

        # Generate summary using Claude if we have a transcript
        summary = ""
        if result.transcript and result.transcript.strip():
            print(f"[{job_id}] Generating summary with Claude for {retailer_name}...")
            try:
                summary = summarize_transcript(result.transcript, retailer_name)
                print(f"[{job_id}] Summary generated: {summary[:100]}...")
            except Exception as sum_err:
                print(f"[{job_id}] Error generating summary: {sum_err}")
                summary = ""

        # Re-analyze inventory status using BOTH transcript AND Claude summary
        # This catches cases where the summary has clearer language than the transcript
        if summary:
            print(f"[{job_id}] Re-analyzing inventory status with Claude summary...")
            final_status = caller._analyze_inventory_status(result.transcript or "", summary)
            print(f"[{job_id}] Final status after re-analysis: {final_status.value}")
        else:
            final_status = result.status

        # Fallback if Claude summarization failed or no transcript
        if not summary or summary.strip() == "":
            status_val = final_status.value
            if status_val == "in_stock":
                summary = "The retailer confirmed they have the watch in stock."
            elif status_val == "out_of_stock":
                summary = "The retailer confirmed they do not have the watch in stock."
            elif status_val == "waitlist":
                summary = "The watch is not in stock, but you can join a waitlist or client book."
            elif status_val == "can_order":
                summary = "The watch is not in stock, but the retailer can special order it."
            elif status_val == "no_answer":
                summary = "Unable to reach the store - no answer or went to voicemail."
            elif status_val == "call_failed":
                summary = "The call could not be completed due to a technical issue."
            else:
                summary = "Could not determine stock status - may have reached an automated system or the call ended before getting an answer."

        call_jobs[job_id]["status"] = "completed"
        call_jobs[job_id]["result"] = {
            "retailer_name": result.retailer_name,
            "phone": result.retailer_phone,
            "inventory_status": final_status.value,
            "summary": summary,
            "transcript": result.transcript,
            "call_duration": result.call_duration
        }
        call_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        print(f"[{job_id}] Job completed successfully")

    except Exception as e:
        import traceback
        print(f"[{job_id}] ERROR in background task: {e}")
        print(f"[{job_id}] Traceback: {traceback.format_exc()}")
        call_jobs[job_id]["status"] = "failed"
        call_jobs[job_id]["error"] = str(e)


@app.get("/api/call/{call_id}")
async def get_call_status(call_id: str):
    """Get the status of a phone call"""
    if call_id not in call_jobs:
        raise HTTPException(status_code=404, detail="Call job not found")

    job = call_jobs[call_id]

    response = {
        "call_id": call_id,
        "status": job["status"],
        "retailer_name": job.get("retailer_name"),
        "phone": job.get("phone")
    }

    if job["status"] == "completed" and job.get("result"):
        response["inventory_status"] = job["result"]["inventory_status"]
        response["summary"] = job["result"]["summary"]

    if job["status"] == "failed":
        response["error"] = job.get("error")

    return response


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "retailers_cached": retailer_cache.is_loaded,
        "retailers_count": len(retailer_cache.get_retailers()) if retailer_cache.is_loaded else 0
    }


@app.get("/api/website-stock/{retailer_name}")
async def check_website_stock(retailer_name: str):
    """Check website stock for a specific retailer"""
    reference = WATCH_CONFIG.get("reference", "M79930-0007")

    # Check if we have a scraper for this retailer
    if not website_stock_checker.has_scraper(retailer_name):
        return {
            "retailer_name": retailer_name,
            "has_scraper": False,
            "status": "no_scraper",
            "message": f"No website scraper available for {retailer_name}"
        }

    try:
        result = website_stock_checker.check_stock(retailer_name, reference)
        return {
            "retailer_name": result.retailer_name,
            "has_scraper": True,
            "status": result.status.value,
            "message": result.message,
            "product_url": result.product_url,
            "price": result.price
        }
    except Exception as e:
        return {
            "retailer_name": retailer_name,
            "has_scraper": True,
            "status": "scraper_error",
            "message": f"Error checking website: {str(e)}"
        }


@app.get("/api/supported-retailers")
async def get_supported_retailers():
    """Get list of retailers with website scrapers"""
    return {
        "retailers": website_stock_checker.get_supported_retailers()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
