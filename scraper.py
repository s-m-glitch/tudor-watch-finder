"""
Tudor Retailer Scraper
Fetches all Tudor retailers in the United States from tudorwatch.com
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class Retailer:
    """Represents a Tudor retailer"""
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    country: str
    phone: Optional[str]
    website: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    detail_url: str
    retailer_type: str  # e.g., "Tudor Boutique Edition", "Official Retailer"

    def to_dict(self) -> Dict:
        return asdict(self)


class ZipCodeGeocoder:
    """Simple geocoder using Zippopotam.us API"""

    API_URL = "https://api.zippopotam.us/us/{zip_code}"
    _cache = {}

    @classmethod
    def geocode(cls, zip_code: str) -> Optional[tuple]:
        """Returns (latitude, longitude) for a zip code"""
        if not zip_code or len(zip_code) < 5:
            return None

        zip_code = zip_code[:5]

        if zip_code in cls._cache:
            return cls._cache[zip_code]

        try:
            response = requests.get(cls.API_URL.format(zip_code=zip_code), timeout=5)
            if response.status_code == 200:
                data = response.json()
                place = data['places'][0]
                coords = (float(place['latitude']), float(place['longitude']))
                cls._cache[zip_code] = coords
                return coords
        except Exception:
            pass

        return None


class TudorScraper:
    """Scrapes Tudor retailer data from tudorwatch.com"""

    BASE_URL = "https://www.tudorwatch.com"
    RETAILERS_URL = "https://www.tudorwatch.com/en/retailers/unitedstates"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def fetch_retailer_list_page(self) -> str:
        """Fetch the main retailers page HTML"""
        url = f"{self.RETAILERS_URL}?lat=38.555474567327764&lng=-95.66499999999999&z=4"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def extract_retailer_urls(self, html: str) -> List[str]:
        """Extract all retailer detail page URLs from the main page"""
        soup = BeautifulSoup(html, 'html.parser')
        retailer_links = soup.find_all('a', href=re.compile(r'/retailers/details/unitedstates/'))

        urls = set()
        for link in retailer_links:
            href = link.get('href', '')
            if href:
                full_url = f"{self.BASE_URL}{href}" if href.startswith('/') else href
                urls.add(full_url)

        return list(urls)

    def fetch_retailer_details(self, detail_url: str) -> Optional[Retailer]:
        """Fetch and parse details for a single retailer"""
        try:
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')

            page_text = soup.get_text(separator=' ', strip=True)

            # Extract name from title tag
            title_tag = soup.find('title')
            name = "Unknown"
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Format: "Store Name - United States | Official TUDOR..."
                name = title_text.split(' - ')[0].strip()
                name = re.sub(r'^[‭‬\u200e\u200f]+|[‭‬\u200e\u200f]+$', '', name)  # Remove unicode markers

            # Determine retailer type
            retailer_type = "Official Retailer"
            if 'boutique edition' in page_text.lower() or 'tudor boutique' in name.lower():
                retailer_type = "Tudor Boutique Edition"

            # Extract phone - look for tel: links first
            phone = None
            phone_link = soup.find('a', href=re.compile(r'^tel:'))
            if phone_link:
                phone = phone_link.get('href', '').replace('tel:', '').strip()
                # Clean up phone format
                phone = re.sub(r'[^\d+]', '', phone)
                if phone and not phone.startswith('+'):
                    if len(phone) == 10:
                        phone = '+1' + phone
                    elif len(phone) == 11 and phone.startswith('1'):
                        phone = '+' + phone

            # Extract address components from URL and page
            # URL format: /retailers/details/unitedstates/state/city/id-name
            url_parts = detail_url.rstrip('/').split('/')
            state_from_url = ""
            city_from_url = ""

            if len(url_parts) >= 3:
                # Find the state and city parts
                try:
                    us_index = url_parts.index('unitedstates')
                    if us_index + 1 < len(url_parts):
                        state_from_url = url_parts[us_index + 1]
                    if us_index + 2 < len(url_parts):
                        city_from_url = url_parts[us_index + 2]
                except ValueError:
                    pass

            # Clean up state
            state = state_from_url.upper() if len(state_from_url) == 2 else ""

            # State name mapping for longer state names in URL
            state_map = {
                'virginia': 'VA', 'texas': 'TX', 'california': 'CA', 'florida': 'FL',
                'new-york': 'NY', 'newyork': 'NY', 'illinois': 'IL', 'michigan': 'MI',
                'ohio': 'OH', 'georgia': 'GA', 'arizona': 'AZ', 'colorado': 'CO',
                'washington': 'WA', 'massachusetts': 'MA', 'pennsylvania': 'PA',
                'nevada': 'NV', 'oregon': 'OR', 'minnesota': 'MN', 'missouri': 'MO',
                'maryland': 'MD', 'tennessee': 'TN', 'indiana': 'IN', 'wisconsin': 'WI',
                'connecticut': 'CT', 'utah': 'UT', 'oklahoma': 'OK', 'kentucky': 'KY',
                'louisiana': 'LA', 'alabama': 'AL', 'south-carolina': 'SC', 'north-carolina': 'NC',
                'new-jersey': 'NJ', 'newjersey': 'NJ', 'hawaii': 'HI', 'idaho': 'ID',
                'nebraska': 'NE', 'kansas': 'KS', 'arkansas': 'AR', 'mississippi': 'MS',
                'iowa': 'IA', 'new-mexico': 'NM', 'rhode-island': 'RI', 'delaware': 'DE',
                'maine': 'ME', 'montana': 'MT', 'new-hampshire': 'NH', 'vermont': 'VT',
                'wyoming': 'WY', 'alaska': 'AK', 'north-dakota': 'ND', 'south-dakota': 'SD',
                'west-virginia': 'WV', 'dc': 'DC', 'district-of-columbia': 'DC'
            }

            if not state and state_from_url.lower() in state_map:
                state = state_map[state_from_url.lower()]

            # Clean up city
            city = city_from_url.replace('-', ' ').title() if city_from_url else ""

            # Try to extract zip code from page text
            zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', page_text)
            zip_code = zip_match.group(1) if zip_match else ""

            # Try to extract full address
            address = ""
            # Look for address patterns
            address_patterns = [
                r'(\d+[^,\n]{5,50}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct|Circle|Cir|Highway|Hwy)[^,\n]{0,30})',
                r'(\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Plaza|Center|Centre|Mall)[^,\n]{0,50})',
            ]

            for pattern in address_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    address = match.group(1).strip()
                    break

            # Get coordinates from zip code
            latitude = None
            longitude = None
            if zip_code:
                coords = ZipCodeGeocoder.geocode(zip_code)
                if coords:
                    latitude, longitude = coords

            # Extract website
            website = None
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.startswith('http') and 'tudorwatch.com' not in href:
                    if not any(x in href for x in ['facebook', 'instagram', 'twitter', 'youtube', 'tel:', 'mailto:']):
                        website = href
                        break

            return Retailer(
                name=name,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                country="United States",
                phone=phone,
                website=website,
                latitude=latitude,
                longitude=longitude,
                detail_url=detail_url,
                retailer_type=retailer_type
            )

        except Exception as e:
            print(f"Error fetching {detail_url}: {e}")
            return None

    def scrape_all_retailers(self, max_workers: int = 5, delay: float = 0.3) -> List[Retailer]:
        """Scrape all US Tudor retailers"""
        print("Fetching main retailers page...")
        html = self.fetch_retailer_list_page()

        print("Extracting retailer URLs...")
        urls = self.extract_retailer_urls(html)
        print(f"Found {len(urls)} retailer URLs")

        retailers = []

        print("Fetching retailer details...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.fetch_retailer_details, url): url for url in urls}

            for i, future in enumerate(as_completed(future_to_url)):
                url = future_to_url[future]
                try:
                    retailer = future.result()
                    if retailer:
                        retailers.append(retailer)
                        print(f"  [{i+1}/{len(urls)}] {retailer.name} - {retailer.city}, {retailer.state} - Phone: {retailer.phone or 'N/A'}")
                except Exception as e:
                    print(f"  [{i+1}/{len(urls)}] Error: {e}")

                time.sleep(delay)

        return retailers

    def save_retailers(self, retailers: List[Retailer], filepath: str = "retailers.json"):
        """Save retailers to a JSON file"""
        data = [r.to_dict() for r in retailers]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved {len(retailers)} retailers to {filepath}")

    @staticmethod
    def load_retailers(filepath: str = "retailers.json") -> List[Retailer]:
        """Load retailers from a JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return [Retailer(**r) for r in data]


def main():
    """Main function to scrape and save Tudor retailers"""
    scraper = TudorScraper()
    retailers = scraper.scrape_all_retailers()
    scraper.save_retailers(retailers)

    print(f"\nScraping complete!")
    print(f"Total retailers: {len(retailers)}")
    print(f"With phone numbers: {sum(1 for r in retailers if r.phone)}")
    print(f"With coordinates: {sum(1 for r in retailers if r.latitude)}")
    print(f"Boutiques: {sum(1 for r in retailers if 'Boutique' in r.retailer_type)}")


if __name__ == "__main__":
    main()
