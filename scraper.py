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


class TudorScraper:
    """Scrapes Tudor retailer data from tudorwatch.com"""

    BASE_URL = "https://www.tudorwatch.com"
    RETAILERS_URL = "https://www.tudorwatch.com/en/retailers/unitedstates"

    # Headers to mimic a browser request
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def fetch_retailer_list_page(self) -> str:
        """Fetch the main retailers page HTML"""
        # Use coordinates for center of US to get all retailers
        url = f"{self.RETAILERS_URL}?lat=38.555474567327764&lng=-95.66499999999999&z=4"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def extract_retailer_urls(self, html: str) -> List[str]:
        """Extract all retailer detail page URLs from the main page"""
        soup = BeautifulSoup(html, 'html.parser')

        # Find all links to retailer detail pages
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

            # Extract retailer name from page title or h1
            name_elem = soup.find('h1') or soup.find('title')
            name = name_elem.get_text(strip=True) if name_elem else "Unknown"
            # Clean up the name
            name = re.sub(r'\s*[-|]\s*.*$', '', name)

            # Try to extract address information
            # Look for address-related content
            address_text = ""
            city = ""
            state = ""
            zip_code = ""
            phone = None
            website = None
            latitude = None
            longitude = None
            retailer_type = "Official Retailer"

            # Look for Tudor Boutique Edition marker
            if soup.find(string=re.compile(r'Tudor Boutique Edition', re.I)):
                retailer_type = "Tudor Boutique Edition"

            # Extract address from the page
            # The address is usually in a specific section
            address_section = soup.find('address') or soup.find(class_=re.compile(r'address', re.I))

            if address_section:
                address_text = address_section.get_text(separator=' ', strip=True)
            else:
                # Try to find address in the page text
                page_text = soup.get_text()
                # Look for patterns like "123 Main St"
                address_match = re.search(r'(\d+[^,]+),?\s*([A-Za-z\s]+),?\s*([A-Z]{2})\s*(\d{5})', page_text)
                if address_match:
                    address_text = address_match.group(1)
                    city = address_match.group(2).strip()
                    state = address_match.group(3)
                    zip_code = address_match.group(4)

            # Extract phone number
            phone_link = soup.find('a', href=re.compile(r'^tel:'))
            if phone_link:
                phone = phone_link.get('href', '').replace('tel:', '')
            else:
                # Try to find phone in text
                phone_match = re.search(r'\+?1?\s*[-.]?\s*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', page_text if 'page_text' in dir() else soup.get_text())
                if phone_match:
                    phone = f"+1 {phone_match.group(1)}-{phone_match.group(2)}-{phone_match.group(3)}"

            # Extract website
            external_links = soup.find_all('a', href=re.compile(r'^https?://(?!.*tudorwatch\.com)'))
            for link in external_links:
                href = link.get('href', '')
                if 'tudorwatch.com' not in href and not href.startswith('tel:') and not href.startswith('mailto:'):
                    website = href
                    break

            # Extract coordinates from any embedded map or data
            # Look for latitude/longitude in scripts or data attributes
            for script in soup.find_all('script'):
                script_text = script.string or ''
                lat_match = re.search(r'"lat(?:itude)?"\s*:\s*([-\d.]+)', script_text)
                lng_match = re.search(r'"lng|lon(?:gitude)?"\s*:\s*([-\d.]+)', script_text)
                if lat_match and lng_match:
                    latitude = float(lat_match.group(1))
                    longitude = float(lng_match.group(1))
                    break

            # Parse city/state from URL if not found
            url_parts = detail_url.split('/')
            if len(url_parts) >= 3:
                if not state:
                    state = url_parts[-2].upper() if len(url_parts[-2]) == 2 else ""
                if not city:
                    city = url_parts[-2].replace('-', ' ').title() if len(url_parts[-2]) > 2 else ""

            return Retailer(
                name=name,
                address=address_text,
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

    def scrape_all_retailers(self, max_workers: int = 5, delay: float = 0.5) -> List[Retailer]:
        """
        Scrape all US Tudor retailers

        Args:
            max_workers: Number of concurrent threads for fetching details
            delay: Delay between requests to be respectful to the server

        Returns:
            List of Retailer objects
        """
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
                        print(f"  [{i+1}/{len(urls)}] {retailer.name}")
                except Exception as e:
                    print(f"  [{i+1}/{len(urls)}] Error: {e}")

                time.sleep(delay)  # Rate limiting

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
    print(f"Boutiques: {sum(1 for r in retailers if 'Boutique' in r.retailer_type)}")


if __name__ == "__main__":
    main()
