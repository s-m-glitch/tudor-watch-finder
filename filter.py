"""
Zip Code Distance Filter
Filters Tudor retailers based on distance from a given zip code
"""

import math
import json
import requests
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from scraper import Retailer


@dataclass
class ZipCodeLocation:
    """Represents a zip code with its coordinates"""
    zip_code: str
    latitude: float
    longitude: float
    city: str
    state: str


class ZipCodeGeocoder:
    """
    Geocodes zip codes to latitude/longitude coordinates
    Uses the free Zippopotam.us API
    """

    API_URL = "https://api.zippopotam.us/us/{zip_code}"

    # Backup: US Census Bureau geocoder
    CENSUS_API_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"

    def __init__(self):
        self._cache: Dict[str, ZipCodeLocation] = {}

    def geocode(self, zip_code: str) -> Optional[ZipCodeLocation]:
        """
        Convert a US zip code to latitude/longitude coordinates

        Args:
            zip_code: 5-digit US zip code

        Returns:
            ZipCodeLocation with coordinates, or None if not found
        """
        zip_code = zip_code.strip()[:5]  # Ensure 5-digit format

        # Check cache first
        if zip_code in self._cache:
            return self._cache[zip_code]

        # Try Zippopotam.us API first
        try:
            response = requests.get(
                self.API_URL.format(zip_code=zip_code),
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                place = data['places'][0]
                location = ZipCodeLocation(
                    zip_code=zip_code,
                    latitude=float(place['latitude']),
                    longitude=float(place['longitude']),
                    city=place['place name'],
                    state=place['state abbreviation']
                )
                self._cache[zip_code] = location
                return location
        except Exception as e:
            print(f"Zippopotam API error: {e}")

        # Fallback to Census Bureau API
        try:
            response = requests.get(
                self.CENSUS_API_URL,
                params={
                    'address': zip_code,
                    'benchmark': 'Public_AR_Current',
                    'format': 'json'
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('result', {}).get('addressMatches'):
                    match = data['result']['addressMatches'][0]
                    coords = match['coordinates']
                    location = ZipCodeLocation(
                        zip_code=zip_code,
                        latitude=coords['y'],
                        longitude=coords['x'],
                        city=match.get('addressComponents', {}).get('city', ''),
                        state=match.get('addressComponents', {}).get('state', '')
                    )
                    self._cache[zip_code] = location
                    return location
        except Exception as e:
            print(f"Census API error: {e}")

        return None


class DistanceCalculator:
    """Calculates distances between geographic coordinates"""

    EARTH_RADIUS_MILES = 3959  # Earth's radius in miles

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points on Earth
        using the Haversine formula.

        Args:
            lat1, lon1: Coordinates of first point (in degrees)
            lat2, lon2: Coordinates of second point (in degrees)

        Returns:
            Distance in miles
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return DistanceCalculator.EARTH_RADIUS_MILES * c


class RetailerFilter:
    """Filters retailers by distance from a zip code"""

    def __init__(self):
        self.geocoder = ZipCodeGeocoder()
        self.calculator = DistanceCalculator()

    def filter_by_zip_code(
        self,
        retailers: List[Retailer],
        zip_code: str,
        radius_miles: float = 50
    ) -> List[Tuple[Retailer, float]]:
        """
        Filter retailers within a radius of a zip code

        Args:
            retailers: List of Retailer objects to filter
            zip_code: Center zip code for the search
            radius_miles: Maximum distance in miles

        Returns:
            List of (Retailer, distance) tuples, sorted by distance
        """
        # Geocode the zip code
        location = self.geocoder.geocode(zip_code)
        if not location:
            raise ValueError(f"Could not geocode zip code: {zip_code}")

        print(f"Searching within {radius_miles} miles of {location.city}, {location.state} ({zip_code})")
        print(f"Center coordinates: {location.latitude}, {location.longitude}")

        results = []

        for retailer in retailers:
            # Skip retailers without coordinates
            if retailer.latitude is None or retailer.longitude is None:
                # Try to geocode by address/zip if available
                if retailer.zip_code:
                    retailer_loc = self.geocoder.geocode(retailer.zip_code)
                    if retailer_loc:
                        retailer.latitude = retailer_loc.latitude
                        retailer.longitude = retailer_loc.longitude

            if retailer.latitude is None or retailer.longitude is None:
                continue

            # Calculate distance
            distance = self.calculator.haversine_distance(
                location.latitude, location.longitude,
                retailer.latitude, retailer.longitude
            )

            if distance <= radius_miles:
                results.append((retailer, distance))

        # Sort by distance
        results.sort(key=lambda x: x[1])

        return results

    def filter_by_coordinates(
        self,
        retailers: List[Retailer],
        latitude: float,
        longitude: float,
        radius_miles: float = 50
    ) -> List[Tuple[Retailer, float]]:
        """
        Filter retailers within a radius of specific coordinates

        Args:
            retailers: List of Retailer objects to filter
            latitude, longitude: Center coordinates
            radius_miles: Maximum distance in miles

        Returns:
            List of (Retailer, distance) tuples, sorted by distance
        """
        results = []

        for retailer in retailers:
            if retailer.latitude is None or retailer.longitude is None:
                continue

            distance = self.calculator.haversine_distance(
                latitude, longitude,
                retailer.latitude, retailer.longitude
            )

            if distance <= radius_miles:
                results.append((retailer, distance))

        results.sort(key=lambda x: x[1])
        return results


def main():
    """Demo of the filtering functionality"""
    from scraper import TudorScraper

    # Load or scrape retailers
    try:
        retailers = TudorScraper.load_retailers("retailers.json")
        print(f"Loaded {len(retailers)} retailers from cache")
    except FileNotFoundError:
        print("No cached data found. Please run scraper.py first.")
        return

    # Filter by zip code
    filter = RetailerFilter()
    zip_code = "94117"  # San Francisco
    radius = 50

    results = filter.filter_by_zip_code(retailers, zip_code, radius)

    print(f"\nFound {len(results)} retailers within {radius} miles of {zip_code}:")
    print("-" * 60)

    for retailer, distance in results:
        print(f"{retailer.name}")
        print(f"  Distance: {distance:.1f} miles")
        print(f"  Address: {retailer.address}")
        print(f"  Phone: {retailer.phone or 'N/A'}")
        print()


if __name__ == "__main__":
    main()
