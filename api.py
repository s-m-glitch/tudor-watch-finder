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

# In-memory storage for results (use Redis/DB in production)
search_results = {}
call_jobs = {}

# Cache for retailers
retailers_cache = None
retailers_cache_time = None


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


def get_retailers():
    """Get retailers from cache or scrape fresh"""
    global retailers_cache, retailers_cache_time

    cache_file = "retailers.json"

    # Try to load from file cache first
    if os.path.exists(cache_file):
        try:
            retailers_cache = TudorScraper.load_retailers(cache_file)
            return retailers_cache
        except Exception:
            pass

    # If we have in-memory cache less than 1 hour old, use it
    if retailers_cache and retailers_cache_time:
        age = (datetime.now() - retailers_cache_time).seconds
        if age < 3600:
            return retailers_cache

    # Scrape fresh data
    scraper = TudorScraper()
    retailers_cache = scraper.scrape_all_retailers(max_workers=3)
    retailers_cache_time = datetime.now()

    # Save to file cache
    try:
        scraper.save_retailers(retailers_cache, cache_file)
    except Exception:
        pass

    return retailers_cache


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


@app.post("/api/search")
async def search_retailers(request: SearchRequest):
    """Search for retailers near a zip code"""
    try:
        retailers = get_retailers()
        filter = RetailerFilter()

        filtered = filter.filter_by_zip_code(
            retailers,
            request.zip_code,
            request.radius_miles
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
                "distance_miles": round(distance, 1),
                "retailer_type": retailer.retailer_type,
                "has_phone": bool(retailer.phone)
            })

        # Store results for later use
        search_id = f"{request.zip_code}_{request.radius_miles}_{datetime.now().timestamp()}"
        search_results[search_id] = {
            "zip_code": request.zip_code,
            "radius_miles": request.radius_miles,
            "retailers": results,
            "timestamp": datetime.now().isoformat()
        }

        return {
            "search_id": search_id,
            "zip_code": request.zip_code,
            "radius_miles": request.radius_miles,
            "total_retailers": len(results),
            "with_phone": sum(1 for r in results if r["has_phone"]),
            "retailers": results[:20],  # Limit response size
            "has_more": len(results) > 20
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/call")
async def start_calls(request: CallRequest, background_tasks: BackgroundTasks):
    """Start making phone calls to check inventory"""
    if not request.api_key:
        raise HTTPException(status_code=400, detail="Bland AI API key is required")

    try:
        # Get retailers
        retailers = get_retailers()
        filter = RetailerFilter()
        filtered = filter.filter_by_zip_code(
            retailers,
            request.zip_code,
            request.radius_miles
        )

        # Filter to those with phones
        with_phones = [(r, d) for r, d in filtered if r.phone]

        if not with_phones:
            raise HTTPException(
                status_code=404,
                detail="No retailers with phone numbers found in this area"
            )

        # Limit calls
        to_call = with_phones[:request.max_calls]

        # Create job ID
        job_id = f"call_{datetime.now().timestamp()}"
        call_jobs[job_id] = {
            "status": "starting",
            "total": len(to_call),
            "completed": 0,
            "results": [],
            "started_at": datetime.now().isoformat()
        }

        # Start background task
        background_tasks.add_task(
            run_calls_background,
            job_id,
            to_call,
            request.api_key
        )

        return {
            "job_id": job_id,
            "status": "started",
            "total_calls": len(to_call),
            "retailers": [
                {"name": r.name, "phone": r.phone, "distance": round(d, 1)}
                for r, d in to_call
            ]
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start calls: {str(e)}")


async def run_calls_background(job_id: str, retailers: list, api_key: str):
    """Background task to make phone calls"""
    try:
        caller = BlandAICaller(api_key)
        call_jobs[job_id]["status"] = "in_progress"

        for i, (retailer, distance) in enumerate(retailers):
            call_jobs[job_id]["current"] = retailer.name

            # Make the call
            result = caller.make_call(retailer.phone, retailer.name)

            call_jobs[job_id]["results"].append({
                "retailer_name": result.retailer_name,
                "phone": result.retailer_phone,
                "status": result.status.value,
                "summary": result.summary,
                "distance": round(distance, 1)
            })
            call_jobs[job_id]["completed"] = i + 1

            # Wait between calls
            if i < len(retailers) - 1:
                await asyncio.sleep(30)

        call_jobs[job_id]["status"] = "completed"
        call_jobs[job_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        call_jobs[job_id]["status"] = "failed"
        call_jobs[job_id]["error"] = str(e)


@app.get("/api/call/{job_id}")
async def get_call_status(job_id: str):
    """Get the status of a call job"""
    if job_id not in call_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = call_jobs[job_id]

    # Generate summary if completed
    summary = None
    if job["status"] == "completed":
        in_stock = [r for r in job["results"] if r["status"] == "in_stock"]
        summary = {
            "total_calls": job["total"],
            "in_stock": len(in_stock),
            "in_stock_retailers": in_stock
        }

    return {
        "job_id": job_id,
        "status": job["status"],
        "total": job["total"],
        "completed": job["completed"],
        "current": job.get("current"),
        "results": job["results"],
        "summary": summary,
        "error": job.get("error")
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
