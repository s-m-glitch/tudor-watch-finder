"""
Configuration for Tudor Watch Finder
"""

# Available watches - add new watches here
WATCHES = {
    # RANGER COLLECTION
    "M79930-0007": {
        "model": "Ranger",
        "reference": "M79930-0007",
        "case_size": "36mm",
        "case_material": "steel",
        "dial": "Beige domed dial",
        "price": 3775,
        "full_name": "Tudor Ranger 36mm steel case with Beige domed dial",
        "image": "/static/watch-beige.png"
    },
    "M79930-0001": {
        "model": "Ranger",
        "reference": "M79930-0001",
        "case_size": "36mm",
        "case_material": "steel",
        "dial": "Black domed dial",
        "price": 3700,
        "full_name": "Tudor Ranger 36mm steel case with Black domed dial",
        "image": "/static/watch-black.png"
    },

    # BLACK BAY 58 COLLECTION
    "M79030N-0001": {
        "model": "Black Bay Fifty-Eight",
        "reference": "M79030N-0001",
        "case_size": "39mm",
        "case_material": "steel",
        "dial": "Black",
        "price": 4200,
        "full_name": "Tudor Black Bay Fifty-Eight 39mm steel case with Black dial",
        "image": "/static/watch-black.png"
    },
    "M79030B-0001": {
        "model": "Black Bay Fifty-Eight",
        "reference": "M79030B-0001",
        "case_size": "39mm",
        "case_material": "steel",
        "dial": "Blue",
        "price": 4200,
        "full_name": "Tudor Black Bay Fifty-Eight 39mm steel case with Blue dial",
        "image": "/static/watch-black.png"
    },
    "M79010SG-0001": {
        "model": "Black Bay Fifty-Eight",
        "reference": "M79010SG-0001",
        "case_size": "39mm",
        "case_material": "steel and gold",
        "dial": "Black",
        "price": 5850,
        "full_name": "Tudor Black Bay Fifty-Eight 39mm steel and gold case with Black dial",
        "image": "/static/watch-black.png"
    },
    "M79012M-0001": {
        "model": "Black Bay Fifty-Eight",
        "reference": "M79012M-0001",
        "case_size": "39mm",
        "case_material": "bronze",
        "dial": "Brown",
        "price": 4700,
        "full_name": "Tudor Black Bay Fifty-Eight 39mm bronze case with Brown dial",
        "image": "/static/watch-black.png"
    },

    # BLACK BAY 41/32 COLLECTION
    "M79540-0001": {
        "model": "Black Bay 41",
        "reference": "M79540-0001",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Black",
        "price": 3750,
        "full_name": "Tudor Black Bay 41 41mm steel case with Black dial",
        "image": "/static/watch-black.png"
    },
    "M79540-0004": {
        "model": "Black Bay 41",
        "reference": "M79540-0004",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 3750,
        "full_name": "Tudor Black Bay 41 41mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M79580-0001": {
        "model": "Black Bay 32",
        "reference": "M79580-0001",
        "case_size": "32mm",
        "case_material": "steel",
        "dial": "Black",
        "price": 3375,
        "full_name": "Tudor Black Bay 32 32mm steel case with Black dial",
        "image": "/static/watch-black.png"
    },
    "M79580-0004": {
        "model": "Black Bay 32",
        "reference": "M79580-0004",
        "case_size": "32mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 3375,
        "full_name": "Tudor Black Bay 32 32mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },

    # BLACK BAY CHRONO COLLECTION
    "M79360N-0001": {
        "model": "Black Bay Chrono",
        "reference": "M79360N-0001",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Black",
        "price": 5900,
        "full_name": "Tudor Black Bay Chrono 41mm steel case with Black dial",
        "image": "/static/watch-black.png"
    },
    "M79360R-0001": {
        "model": "Black Bay Chrono",
        "reference": "M79360R-0001",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Champagne",
        "price": 5900,
        "full_name": "Tudor Black Bay Chrono 41mm steel case with Champagne dial",
        "image": "/static/watch-black.png"
    },

    # BLACK BAY GMT COLLECTION
    "M79830RB-0001": {
        "model": "Black Bay GMT",
        "reference": "M79830RB-0001",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Black with red and blue bezel",
        "price": 4700,
        "full_name": "Tudor Black Bay GMT 41mm steel case with Black dial and red/blue bezel",
        "image": "/static/watch-black.png"
    },

    # BLACK BAY PRO COLLECTION
    "M79470-0001": {
        "model": "Black Bay Pro",
        "reference": "M79470-0001",
        "case_size": "39mm",
        "case_material": "steel",
        "dial": "Black",
        "price": 4300,
        "full_name": "Tudor Black Bay Pro 39mm steel case with Black dial",
        "image": "/static/watch-black.png"
    },

    # PELAGOS COLLECTION
    "M25600TN-0001": {
        "model": "Pelagos",
        "reference": "M25600TN-0001",
        "case_size": "42mm",
        "case_material": "titanium",
        "dial": "Black",
        "price": 5200,
        "full_name": "Tudor Pelagos 42mm titanium case with Black dial",
        "image": "/static/watch-black.png"
    },
    "M25600TB-0001": {
        "model": "Pelagos",
        "reference": "M25600TB-0001",
        "case_size": "42mm",
        "case_material": "titanium",
        "dial": "Blue",
        "price": 5200,
        "full_name": "Tudor Pelagos 42mm titanium case with Blue dial",
        "image": "/static/watch-black.png"
    },
    "M25407N-0001": {
        "model": "Pelagos 39",
        "reference": "M25407N-0001",
        "case_size": "39mm",
        "case_material": "titanium",
        "dial": "Black",
        "price": 4900,
        "full_name": "Tudor Pelagos 39 39mm titanium case with Black dial",
        "image": "/static/watch-black.png"
    },
    "M25407N-0002": {
        "model": "Pelagos FXD",
        "reference": "M25407N-0002",
        "case_size": "42mm",
        "case_material": "titanium",
        "dial": "Black",
        "price": 4400,
        "full_name": "Tudor Pelagos FXD 42mm titanium case with Black dial",
        "image": "/static/watch-black.png"
    },

    # ROYAL COLLECTION
    "M28600-0001": {
        "model": "Royal",
        "reference": "M28600-0001",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 3100,
        "full_name": "Tudor Royal 41mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M28600-0005": {
        "model": "Royal",
        "reference": "M28600-0005",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Blue",
        "price": 3100,
        "full_name": "Tudor Royal 41mm steel case with Blue dial",
        "image": "/static/watch-black.png"
    },
    "M28600-0006": {
        "model": "Royal",
        "reference": "M28600-0006",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Blue",
        "price": 3100,
        "full_name": "Tudor Royal 41mm steel case with Blue dial",
        "image": "/static/watch-black.png"
    },
    "M28500-0001": {
        "model": "Royal",
        "reference": "M28500-0001",
        "case_size": "38mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 2900,
        "full_name": "Tudor Royal 38mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M28500-0005": {
        "model": "Royal",
        "reference": "M28500-0005",
        "case_size": "38mm",
        "case_material": "steel",
        "dial": "Blue",
        "price": 2900,
        "full_name": "Tudor Royal 38mm steel case with Blue dial",
        "image": "/static/watch-black.png"
    },
    "M28400-0001": {
        "model": "Royal",
        "reference": "M28400-0001",
        "case_size": "34mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 2700,
        "full_name": "Tudor Royal 34mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M28400-0005": {
        "model": "Royal",
        "reference": "M28400-0005",
        "case_size": "34mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 2700,
        "full_name": "Tudor Royal 34mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M28303-0001": {
        "model": "Royal",
        "reference": "M28303-0001",
        "case_size": "28mm",
        "case_material": "steel and gold",
        "dial": "Silver",
        "price": 2550,
        "full_name": "Tudor Royal 28mm steel and gold case with Silver dial",
        "image": "/static/watch-black.png"
    },

    # 1926 COLLECTION
    "M91650-0001": {
        "model": "1926",
        "reference": "M91650-0001",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 2550,
        "full_name": "Tudor 1926 41mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M91650-0004": {
        "model": "1926",
        "reference": "M91650-0004",
        "case_size": "41mm",
        "case_material": "steel",
        "dial": "Diamond-set",
        "price": 3200,
        "full_name": "Tudor 1926 41mm steel case with Diamond-set dial",
        "image": "/static/watch-black.png"
    },
    "M91550-0001": {
        "model": "1926",
        "reference": "M91550-0001",
        "case_size": "39mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 2500,
        "full_name": "Tudor 1926 39mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M91550-0004": {
        "model": "1926",
        "reference": "M91550-0004",
        "case_size": "39mm",
        "case_material": "steel",
        "dial": "Diamond-set",
        "price": 3150,
        "full_name": "Tudor 1926 39mm steel case with Diamond-set dial",
        "image": "/static/watch-black.png"
    },
    "M91450-0001": {
        "model": "1926",
        "reference": "M91450-0001",
        "case_size": "36mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 2425,
        "full_name": "Tudor 1926 36mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M91450-0004": {
        "model": "1926",
        "reference": "M91450-0004",
        "case_size": "36mm",
        "case_material": "steel",
        "dial": "Diamond-set",
        "price": 3075,
        "full_name": "Tudor 1926 36mm steel case with Diamond-set dial",
        "image": "/static/watch-black.png"
    },
    "M91350-0001": {
        "model": "1926",
        "reference": "M91350-0001",
        "case_size": "28mm",
        "case_material": "steel",
        "dial": "Silver",
        "price": 2325,
        "full_name": "Tudor 1926 28mm steel case with Silver dial",
        "image": "/static/watch-black.png"
    },
    "M91350-0004": {
        "model": "1926",
        "reference": "M91350-0004",
        "case_size": "28mm",
        "case_material": "steel",
        "dial": "Diamond-set",
        "price": 2975,
        "full_name": "Tudor 1926 28mm steel case with Diamond-set dial",
        "image": "/static/watch-black.png"
    }
}

# Default watch (for backward compatibility)
DEFAULT_WATCH = "M79930-0007"
WATCH_CONFIG = WATCHES[DEFAULT_WATCH]

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
