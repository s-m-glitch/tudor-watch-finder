"""
Website Stock Scraper for Tudor Retailers
Scrapes individual retailer websites to check for watch availability
"""

import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class WebsiteStockStatus(Enum):
    """Stock status from website scraping"""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    CALL_FOR_AVAILABILITY = "call_for_availability"
    UNKNOWN = "unknown"
    SCRAPER_ERROR = "scraper_error"
    NO_SCRAPER = "no_scraper"


@dataclass
class WebsiteStockResult:
    """Result from checking a retailer's website"""
    retailer_name: str
    status: WebsiteStockStatus
    product_url: Optional[str] = None
    price: Optional[float] = None
    message: Optional[str] = None
    raw_html: Optional[str] = None  # For debugging


class RetailerScraper(ABC):
    """Base class for retailer-specific scrapers"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    @property
    @abstractmethod
    def retailer_name(self) -> str:
        """Name of the retailer this scraper handles"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL of the retailer's website"""
        pass

    @abstractmethod
    def check_stock(self, reference: str) -> WebsiteStockResult:
        """Check if a watch with given reference number is in stock"""
        pass

    def _fetch_page(self, url: str, timeout: int = 15) -> Optional[str]:
        """Fetch a page and return its HTML content"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None


class TourneauScraper(RetailerScraper):
    """Scraper for Tourneau (tourneau.com)"""

    @property
    def retailer_name(self) -> str:
        return "Tourneau"

    @property
    def base_url(self) -> str:
        return "https://www.tourneau.com"

    def check_stock(self, reference: str) -> WebsiteStockResult:
        """Search Tourneau for the watch reference"""
        try:
            # Try search URL
            search_url = f"{self.base_url}/search?q={reference}"
            html = self._fetch_page(search_url)

            if not html:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.SCRAPER_ERROR,
                    message="Failed to fetch search page"
                )

            soup = BeautifulSoup(html, 'html.parser')

            # Look for product cards in search results
            # Tourneau uses product-card class for items
            products = soup.find_all('div', class_=re.compile(r'product', re.I))

            # Also check for "no results" message
            no_results = soup.find(string=re.compile(r'no results|no products|not found', re.I))

            if no_results and not products:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.OUT_OF_STOCK,
                    message="No products found matching reference"
                )

            # Look for the specific reference in product text
            for product in products:
                product_text = product.get_text().lower()
                if reference.lower() in product_text or reference.replace('-', '').lower() in product_text:
                    # Found the watch - check if it's in stock
                    # Look for "Add to Cart", "In Stock", or price indicators
                    add_to_cart = product.find(string=re.compile(r'add to (cart|bag)', re.I))
                    in_stock = product.find(string=re.compile(r'in stock|available', re.I))
                    out_of_stock = product.find(string=re.compile(r'out of stock|sold out|unavailable', re.I))

                    # Try to find product URL
                    product_link = product.find('a', href=True)
                    product_url = None
                    if product_link:
                        href = product_link.get('href', '')
                        product_url = href if href.startswith('http') else f"{self.base_url}{href}"

                    # Try to find price
                    price = None
                    price_elem = product.find(string=re.compile(r'\$[\d,]+'))
                    if price_elem:
                        price_match = re.search(r'\$([\d,]+)', price_elem)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))

                    if out_of_stock:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.OUT_OF_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Listed as out of stock"
                        )
                    elif add_to_cart or in_stock:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.IN_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Available for purchase"
                        )
                    else:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.CALL_FOR_AVAILABILITY,
                            product_url=product_url,
                            price=price,
                            message="Product found but availability unclear"
                        )

            # Reference not found in any products
            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.OUT_OF_STOCK,
                message="Reference not found in search results"
            )

        except Exception as e:
            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.SCRAPER_ERROR,
                message=f"Error: {str(e)}"
            )


class JRDunnScraper(RetailerScraper):
    """Scraper for J.R. Dunn Jewelers (jrdunn.com)"""

    @property
    def retailer_name(self) -> str:
        return "J.R. Dunn Jewelers"

    @property
    def base_url(self) -> str:
        return "https://jrdunn.com"

    def check_stock(self, reference: str) -> WebsiteStockResult:
        """Search J.R. Dunn for the watch reference"""
        try:
            # J.R. Dunn uses Shopify - search via their search endpoint
            search_url = f"{self.base_url}/search?q={reference}&type=product"
            html = self._fetch_page(search_url)

            if not html:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.SCRAPER_ERROR,
                    message="Failed to fetch search page"
                )

            soup = BeautifulSoup(html, 'html.parser')

            # Look for product items
            products = soup.find_all(['div', 'article'], class_=re.compile(r'product', re.I))

            # Check for no results
            no_results = soup.find(string=re.compile(r'no results|no products found|0 results', re.I))

            if no_results or not products:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.OUT_OF_STOCK,
                    message="No products found matching reference"
                )

            # Check each product for the reference
            for product in products:
                product_text = product.get_text().lower()
                ref_clean = reference.lower().replace('-', '')

                if reference.lower() in product_text or ref_clean in product_text.replace('-', ''):
                    # Found matching product
                    product_link = product.find('a', href=True)
                    product_url = None
                    if product_link:
                        href = product_link.get('href', '')
                        product_url = href if href.startswith('http') else f"{self.base_url}{href}"

                    # Check for sold out indicators
                    sold_out = product.find(string=re.compile(r'sold out|out of stock', re.I))

                    # Check for price (indicates availability)
                    price = None
                    price_elem = product.find(string=re.compile(r'\$[\d,]+'))
                    if price_elem:
                        price_match = re.search(r'\$([\d,]+)', price_elem)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))

                    if sold_out:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.OUT_OF_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Listed as sold out"
                        )
                    elif price:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.IN_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Available for purchase"
                        )
                    else:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.CALL_FOR_AVAILABILITY,
                            product_url=product_url,
                            message="Product found but availability unclear"
                        )

            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.OUT_OF_STOCK,
                message="Reference not found in search results"
            )

        except Exception as e:
            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.SCRAPER_ERROR,
                message=f"Error: {str(e)}"
            )


class WestimeScraper(RetailerScraper):
    """Scraper for Westime (westime.com)"""

    @property
    def retailer_name(self) -> str:
        return "Westime"

    @property
    def base_url(self) -> str:
        return "https://westime.com"

    def check_stock(self, reference: str) -> WebsiteStockResult:
        """Search Westime for the watch reference"""
        try:
            search_url = f"{self.base_url}/search?q={reference}"
            html = self._fetch_page(search_url)

            if not html:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.SCRAPER_ERROR,
                    message="Failed to fetch search page"
                )

            soup = BeautifulSoup(html, 'html.parser')

            # Look for product grid items
            products = soup.find_all(['div', 'li'], class_=re.compile(r'product|grid-item', re.I))

            no_results = soup.find(string=re.compile(r'no results|no products|sorry', re.I))

            if no_results and not products:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.OUT_OF_STOCK,
                    message="No products found matching reference"
                )

            for product in products:
                product_text = product.get_text().lower()
                ref_clean = reference.lower().replace('-', '')

                if reference.lower() in product_text or ref_clean in product_text.replace('-', ''):
                    product_link = product.find('a', href=True)
                    product_url = None
                    if product_link:
                        href = product_link.get('href', '')
                        product_url = href if href.startswith('http') else f"{self.base_url}{href}"

                    sold_out = product.find(string=re.compile(r'sold out|out of stock|inquire', re.I))

                    price = None
                    price_elem = product.find(string=re.compile(r'\$[\d,]+'))
                    if price_elem:
                        price_match = re.search(r'\$([\d,]+)', price_elem)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))

                    if sold_out:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.OUT_OF_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Listed as sold out or inquire for availability"
                        )
                    elif price:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.IN_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Available for purchase"
                        )
                    else:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.CALL_FOR_AVAILABILITY,
                            product_url=product_url,
                            message="Product found but availability unclear"
                        )

            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.OUT_OF_STOCK,
                message="Reference not found in search results"
            )

        except Exception as e:
            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.SCRAPER_ERROR,
                message=f"Error: {str(e)}"
            )


class FinksScraper(RetailerScraper):
    """Scraper for Fink's Jewelers (finks.com)"""

    @property
    def retailer_name(self) -> str:
        return "Fink's Jewelers"

    @property
    def base_url(self) -> str:
        return "https://www.finks.com"

    def check_stock(self, reference: str) -> WebsiteStockResult:
        """Search Fink's for the watch reference"""
        try:
            # Fink's uses Shopify
            search_url = f"{self.base_url}/search?q={reference}&type=product"
            html = self._fetch_page(search_url)

            if not html:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.SCRAPER_ERROR,
                    message="Failed to fetch search page"
                )

            soup = BeautifulSoup(html, 'html.parser')

            products = soup.find_all(['div', 'article'], class_=re.compile(r'product', re.I))
            no_results = soup.find(string=re.compile(r'no results|no products|0 results', re.I))

            if no_results or not products:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.OUT_OF_STOCK,
                    message="No products found matching reference"
                )

            for product in products:
                product_text = product.get_text().lower()
                ref_clean = reference.lower().replace('-', '')

                if reference.lower() in product_text or ref_clean in product_text.replace('-', ''):
                    product_link = product.find('a', href=True)
                    product_url = None
                    if product_link:
                        href = product_link.get('href', '')
                        product_url = href if href.startswith('http') else f"{self.base_url}{href}"

                    sold_out = product.find(string=re.compile(r'sold out|out of stock', re.I))

                    price = None
                    price_elem = product.find(string=re.compile(r'\$[\d,]+'))
                    if price_elem:
                        price_match = re.search(r'\$([\d,]+)', price_elem)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))

                    if sold_out:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.OUT_OF_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Listed as sold out"
                        )
                    elif price:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.IN_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Available for purchase"
                        )
                    else:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.CALL_FOR_AVAILABILITY,
                            product_url=product_url,
                            message="Product found but availability unclear"
                        )

            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.OUT_OF_STOCK,
                message="Reference not found in search results"
            )

        except Exception as e:
            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.SCRAPER_ERROR,
                message=f"Error: {str(e)}"
            )


class The1916CompanyScraper(RetailerScraper):
    """Scraper for The 1916 Company (the1916company.com)"""

    @property
    def retailer_name(self) -> str:
        return "The 1916 Company"

    @property
    def base_url(self) -> str:
        return "https://www.the1916company.com"

    def check_stock(self, reference: str) -> WebsiteStockResult:
        """Search The 1916 Company for the watch reference"""
        try:
            search_url = f"{self.base_url}/search?q={reference}"
            html = self._fetch_page(search_url)

            if not html:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.SCRAPER_ERROR,
                    message="Failed to fetch search page"
                )

            soup = BeautifulSoup(html, 'html.parser')

            products = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'product|item', re.I))
            no_results = soup.find(string=re.compile(r'no results|no products|sorry', re.I))

            if no_results or not products:
                return WebsiteStockResult(
                    retailer_name=self.retailer_name,
                    status=WebsiteStockStatus.OUT_OF_STOCK,
                    message="No products found matching reference"
                )

            for product in products:
                product_text = product.get_text().lower()
                ref_clean = reference.lower().replace('-', '')

                if reference.lower() in product_text or ref_clean in product_text.replace('-', ''):
                    product_link = product.find('a', href=True)
                    product_url = None
                    if product_link:
                        href = product_link.get('href', '')
                        product_url = href if href.startswith('http') else f"{self.base_url}{href}"

                    sold_out = product.find(string=re.compile(r'sold out|out of stock|unavailable', re.I))

                    price = None
                    price_elem = product.find(string=re.compile(r'\$[\d,]+'))
                    if price_elem:
                        price_match = re.search(r'\$([\d,]+)', price_elem)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))

                    if sold_out:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.OUT_OF_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Listed as sold out"
                        )
                    elif price:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.IN_STOCK,
                            product_url=product_url,
                            price=price,
                            message="Available for purchase"
                        )
                    else:
                        return WebsiteStockResult(
                            retailer_name=self.retailer_name,
                            status=WebsiteStockStatus.CALL_FOR_AVAILABILITY,
                            product_url=product_url,
                            message="Product found but availability unclear"
                        )

            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.OUT_OF_STOCK,
                message="Reference not found in search results"
            )

        except Exception as e:
            return WebsiteStockResult(
                retailer_name=self.retailer_name,
                status=WebsiteStockStatus.SCRAPER_ERROR,
                message=f"Error: {str(e)}"
            )


class WebsiteStockChecker:
    """
    Main class for checking website stock across multiple retailers.
    Maps retailer names to their specific scrapers.
    """

    # Map retailer names (normalized) to scraper classes
    SCRAPER_MAP: Dict[str, type] = {
        "tourneau": TourneauScraper,
        "j.r. dunn": JRDunnScraper,
        "j.r. dunn jewelers": JRDunnScraper,
        "jr dunn": JRDunnScraper,
        "westime": WestimeScraper,
        "fink's": FinksScraper,
        "finks": FinksScraper,
        "fink's jewelers": FinksScraper,
        "the 1916 company": The1916CompanyScraper,
        "1916 company": The1916CompanyScraper,
    }

    def __init__(self):
        self._scraper_instances: Dict[str, RetailerScraper] = {}

    def _get_scraper(self, retailer_name: str) -> Optional[RetailerScraper]:
        """Get or create a scraper instance for the given retailer"""
        normalized = retailer_name.lower().strip()

        # Check for exact match or partial match
        scraper_class = None
        for key, cls in self.SCRAPER_MAP.items():
            if key in normalized or normalized in key:
                scraper_class = cls
                break

        if not scraper_class:
            return None

        # Cache scraper instances
        class_name = scraper_class.__name__
        if class_name not in self._scraper_instances:
            self._scraper_instances[class_name] = scraper_class()

        return self._scraper_instances[class_name]

    def has_scraper(self, retailer_name: str) -> bool:
        """Check if we have a scraper for this retailer"""
        return self._get_scraper(retailer_name) is not None

    def check_stock(self, retailer_name: str, reference: str) -> WebsiteStockResult:
        """Check stock for a specific retailer and watch reference"""
        scraper = self._get_scraper(retailer_name)

        if not scraper:
            return WebsiteStockResult(
                retailer_name=retailer_name,
                status=WebsiteStockStatus.NO_SCRAPER,
                message=f"No scraper available for {retailer_name}"
            )

        return scraper.check_stock(reference)

    def check_stock_batch(
        self,
        retailers: List[Dict],
        reference: str,
        max_workers: int = 3,
        delay: float = 0.5
    ) -> Dict[str, WebsiteStockResult]:
        """
        Check stock for multiple retailers in parallel.

        Args:
            retailers: List of retailer dicts with 'name' key
            reference: Watch reference number to check
            max_workers: Maximum parallel requests
            delay: Delay between requests (to be polite)

        Returns:
            Dict mapping retailer name to WebsiteStockResult
        """
        results = {}

        # Filter to only retailers we have scrapers for
        retailers_with_scrapers = [
            r for r in retailers
            if self.has_scraper(r.get('name', ''))
        ]

        if not retailers_with_scrapers:
            return results

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_retailer = {
                executor.submit(self.check_stock, r['name'], reference): r['name']
                for r in retailers_with_scrapers
            }

            for future in as_completed(future_to_retailer):
                retailer_name = future_to_retailer[future]
                try:
                    result = future.result()
                    results[retailer_name] = result
                except Exception as e:
                    results[retailer_name] = WebsiteStockResult(
                        retailer_name=retailer_name,
                        status=WebsiteStockStatus.SCRAPER_ERROR,
                        message=f"Error: {str(e)}"
                    )
                time.sleep(delay)

        return results

    def get_supported_retailers(self) -> List[str]:
        """Get list of retailer names we have scrapers for"""
        return list(set(self.SCRAPER_MAP.keys()))


# Convenience function
def check_retailer_website(retailer_name: str, reference: str) -> WebsiteStockResult:
    """Quick function to check a single retailer's website"""
    checker = WebsiteStockChecker()
    return checker.check_stock(retailer_name, reference)


if __name__ == "__main__":
    # Test the scrapers
    checker = WebsiteStockChecker()
    reference = "M79930-0007"  # Tudor Ranger 36mm beige dial

    print(f"Testing website scrapers for reference: {reference}")
    print("=" * 60)

    test_retailers = [
        "Tourneau",
        "J.R. Dunn Jewelers",
        "Westime",
        "Fink's Jewelers",
        "The 1916 Company"
    ]

    for retailer in test_retailers:
        print(f"\nChecking {retailer}...")
        result = checker.check_stock(retailer, reference)
        print(f"  Status: {result.status.value}")
        print(f"  Message: {result.message}")
        if result.product_url:
            print(f"  URL: {result.product_url}")
        if result.price:
            print(f"  Price: ${result.price:,.2f}")
