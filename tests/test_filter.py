"""Tests for filter.py — distance calculation and retailer filtering"""

import math
import pytest
from unittest.mock import patch, MagicMock

from filter import DistanceCalculator, RetailerFilter, ZipCodeGeocoder, ZipCodeLocation
from scraper import Retailer


# ── Fixtures ──────────────────────────────────────────────────────────


def make_retailer(name="Test Store", lat=None, lon=None, zip_code="10001", phone="+12125551234"):
    """Helper to create a Retailer with sensible defaults"""
    return Retailer(
        name=name,
        address="123 Main St",
        city="New York",
        state="NY",
        zip_code=zip_code,
        country="United States",
        phone=phone,
        website="https://example.com",
        latitude=lat,
        longitude=lon,
        detail_url="https://tudorwatch.com/en/retailers/details/unitedstates/ny/new-york/123-test",
        retailer_type="Official Retailer",
    )


# ── DistanceCalculator ────────────────────────────────────────────────


class TestDistanceCalculator:
    def test_same_point_is_zero(self):
        d = DistanceCalculator.haversine_distance(40.0, -74.0, 40.0, -74.0)
        assert d == pytest.approx(0.0, abs=0.01)

    def test_known_distance_nyc_to_la(self):
        """NYC (40.7128, -74.0060) to LA (34.0522, -118.2437) ≈ 2,451 miles"""
        d = DistanceCalculator.haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        assert 2400 < d < 2500

    def test_known_distance_sf_to_oakland(self):
        """SF (37.7749, -122.4194) to Oakland (37.8044, -122.2712) ≈ 8-10 miles"""
        d = DistanceCalculator.haversine_distance(37.7749, -122.4194, 37.8044, -122.2712)
        assert 5 < d < 15

    def test_symmetry(self):
        d1 = DistanceCalculator.haversine_distance(40.0, -74.0, 34.0, -118.0)
        d2 = DistanceCalculator.haversine_distance(34.0, -118.0, 40.0, -74.0)
        assert d1 == pytest.approx(d2, abs=0.01)


# ── RetailerFilter ────────────────────────────────────────────────────


class TestRetailerFilter:
    @patch.object(ZipCodeGeocoder, "geocode")
    def test_filter_by_zip_returns_nearby(self, mock_geocode):
        """Retailers within radius should be returned"""
        # Mock the center zip code
        mock_geocode.return_value = ZipCodeLocation(
            zip_code="10001", latitude=40.7484, longitude=-73.9967, city="New York", state="NY"
        )

        nearby = make_retailer("Nearby Store", lat=40.7580, lon=-73.9855)  # ~0.8 miles
        far = make_retailer("Far Store", lat=34.0522, lon=-118.2437)  # LA

        rf = RetailerFilter()
        results = rf.filter_by_zip_code([nearby, far], "10001", radius_miles=50)

        names = [r.name for r, _ in results]
        assert "Nearby Store" in names
        assert "Far Store" not in names

    @patch.object(ZipCodeGeocoder, "geocode")
    def test_filter_sorted_by_distance(self, mock_geocode):
        mock_geocode.return_value = ZipCodeLocation(
            zip_code="10001", latitude=40.7484, longitude=-73.9967, city="New York", state="NY"
        )

        close = make_retailer("Close", lat=40.7500, lon=-73.9900)
        medium = make_retailer("Medium", lat=40.8000, lon=-74.0000)
        far = make_retailer("Far", lat=41.0000, lon=-74.0000)

        rf = RetailerFilter()
        results = rf.filter_by_zip_code([far, close, medium], "10001", radius_miles=100)

        names = [r.name for r, _ in results]
        assert names == ["Close", "Medium", "Far"]

    @patch.object(ZipCodeGeocoder, "geocode")
    def test_filter_skips_retailers_without_coordinates(self, mock_geocode):
        mock_geocode.side_effect = [
            ZipCodeLocation(zip_code="10001", latitude=40.7484, longitude=-73.9967, city="New York", state="NY"),
            None,  # geocode fails for the retailer's zip
        ]

        no_coords = make_retailer("No Coords", lat=None, lon=None, zip_code="99999")

        rf = RetailerFilter()
        results = rf.filter_by_zip_code([no_coords], "10001", radius_miles=5000)

        assert len(results) == 0

    @patch.object(ZipCodeGeocoder, "geocode")
    def test_filter_raises_on_bad_zip(self, mock_geocode):
        mock_geocode.return_value = None

        rf = RetailerFilter()
        with pytest.raises(ValueError, match="Could not geocode"):
            rf.filter_by_zip_code([], "00000", radius_miles=50)

    def test_filter_by_coordinates(self):
        nearby = make_retailer("Nearby", lat=40.7500, lon=-73.9900)
        far = make_retailer("Far", lat=34.0522, lon=-118.2437)

        rf = RetailerFilter()
        results = rf.filter_by_coordinates([nearby, far], 40.7484, -73.9967, radius_miles=50)

        assert len(results) == 1
        assert results[0][0].name == "Nearby"
