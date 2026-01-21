"""
Configuration for Tudor Watch Finder
"""

# Target watch details
WATCH_CONFIG = {
    "model": "Ranger",
    "reference": "M79930-0007",
    "case_size": "36mm",
    "case_material": "steel",
    "dial": "Beige domed dial",
    "price": 3775,
    "full_name": "Tudor Ranger 36mm steel case with Beige domed dial"
}

# Search parameters
SEARCH_CONFIG = {
    "zip_code": "94117",  # Default zip code (San Francisco)
    "radius_miles": 50,   # Search radius in miles
    "country": "unitedstates"
}

# Tudor website URLs
TUDOR_URLS = {
    "retailers_base": "https://www.tudorwatch.com/en/retailers",
    "retailers_us": "https://www.tudorwatch.com/en/retailers/unitedstates",
    "retailer_details_base": "https://www.tudorwatch.com/en/retailers/details/unitedstates",
    "watch_page": "https://www.tudorwatch.com/en/watches/ranger/m79930-0007"
}

# Bland AI Configuration
BLAND_CONFIG = {
    "api_key": "",  # Set via environment variable BLAND_API_KEY
    "base_url": "https://api.bland.ai/v1",
    "voice": "nat",  # Natural sounding voice
    "max_duration": 120,  # Max call duration in seconds
    "wait_for_greeting": True,
    "record": True
}

# Phone call script
CALL_SCRIPT = {
    "greeting": "Hi, I'm calling to check if you have a specific Tudor watch in stock.",
    "inquiry": "Do you currently have the Tudor Ranger 36mm with the beige dial in stock? The reference number is M79930-0007.",
    "followup_if_no": "Do you know when you might be getting it in stock, or is there a waitlist I could join?",
    "closing": "Thank you so much for your help. Have a great day!"
}

# Output settings
OUTPUT_CONFIG = {
    "results_file": "inventory_results.json",
    "log_file": "search_log.txt"
}
