"""Tests for scraper.py — Retailer dataclass and URL extraction"""

import json
import pytest
from scraper import Retailer, TudorScraper


class TestRetailer:
    def test_to_dict(self):
        r = Retailer(
            name="Test Store",
            address="123 Main St",
            city="New York",
            state="NY",
            zip_code="10001",
            country="United States",
            phone="+12125551234",
            website="https://example.com",
            latitude=40.7484,
            longitude=-73.9967,
            detail_url="https://tudorwatch.com/en/retailers/details/unitedstates/ny/new-york/123",
            retailer_type="Official Retailer",
        )
        d = r.to_dict()
        assert d["name"] == "Test Store"
        assert d["phone"] == "+12125551234"
        assert d["latitude"] == 40.7484

    def test_to_dict_is_json_serializable(self):
        r = Retailer(
            name="Test", address="", city="", state="", zip_code="",
            country="US", phone=None, website=None, latitude=None,
            longitude=None, detail_url="", retailer_type="Official Retailer",
        )
        # Should not raise
        json.dumps(r.to_dict())


class TestTudorScraper:
    def test_extract_retailer_urls(self):
        """Test URL extraction from a sample HTML snippet"""
        html = """
        <html><body>
            <a href="/en/retailers/details/unitedstates/ny/new-york/123-store-one">Store One</a>
            <a href="/en/retailers/details/unitedstates/ca/los-angeles/456-store-two">Store Two</a>
            <a href="/en/other-page">Not a retailer</a>
        </body></html>
        """
        scraper = TudorScraper()
        urls = scraper.extract_retailer_urls(html)

        assert len(urls) == 2
        assert all("retailers/details/unitedstates" in u for u in urls)
        assert all(u.startswith("https://www.tudorwatch.com") for u in urls)

    def test_extract_retailer_urls_deduplicates(self):
        """Duplicate links should be collapsed"""
        html = """
        <html><body>
            <a href="/en/retailers/details/unitedstates/ny/new-york/123-store">Link 1</a>
            <a href="/en/retailers/details/unitedstates/ny/new-york/123-store">Link 2</a>
        </body></html>
        """
        scraper = TudorScraper()
        urls = scraper.extract_retailer_urls(html)
        assert len(urls) == 1
