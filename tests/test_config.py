"""Tests for config.py — watch definitions and configuration"""

from config import WATCHES, DEFAULT_WATCH, WATCH_CONFIG, SEARCH_CONFIG, TUDOR_URLS


class TestWatchDefinitions:
    """Tests for the WATCHES dictionary structure"""

    REQUIRED_FIELDS = [
        "model", "reference", "case_size", "case_material",
        "dial", "price", "full_name", "image"
    ]

    def test_watches_is_not_empty(self):
        assert len(WATCHES) > 0, "WATCHES dict should have at least one watch"

    def test_default_watch_exists(self):
        assert DEFAULT_WATCH in WATCHES, f"DEFAULT_WATCH '{DEFAULT_WATCH}' must exist in WATCHES"

    def test_watch_config_matches_default(self):
        assert WATCH_CONFIG == WATCHES[DEFAULT_WATCH]

    def test_all_watches_have_required_fields(self):
        for ref, watch in WATCHES.items():
            for field in self.REQUIRED_FIELDS:
                assert field in watch, f"Watch {ref} missing required field: {field}"

    def test_watch_references_match_keys(self):
        """The 'reference' field inside each watch should match its dict key"""
        for ref, watch in WATCHES.items():
            assert watch["reference"] == ref, (
                f"Watch key '{ref}' doesn't match reference field '{watch['reference']}'"
            )

    def test_watch_prices_are_positive(self):
        for ref, watch in WATCHES.items():
            assert isinstance(watch["price"], (int, float)), f"Watch {ref} price must be numeric"
            assert watch["price"] > 0, f"Watch {ref} price must be positive"

    def test_watch_images_start_with_static(self):
        for ref, watch in WATCHES.items():
            assert watch["image"].startswith("/static/"), (
                f"Watch {ref} image path should start with /static/"
            )

    def test_watch_full_name_contains_model(self):
        for ref, watch in WATCHES.items():
            assert watch["model"] in watch["full_name"], (
                f"Watch {ref} full_name should contain the model name"
            )


class TestSearchConfig:
    def test_has_zip_code(self):
        assert "zip_code" in SEARCH_CONFIG
        assert len(SEARCH_CONFIG["zip_code"]) == 5

    def test_has_radius(self):
        assert "radius_miles" in SEARCH_CONFIG
        assert SEARCH_CONFIG["radius_miles"] > 0

    def test_has_country(self):
        assert "country" in SEARCH_CONFIG


class TestTudorUrls:
    def test_urls_are_https(self):
        for key, url in TUDOR_URLS.items():
            assert url.startswith("https://"), f"URL '{key}' should use HTTPS"

    def test_urls_point_to_tudor(self):
        for key, url in TUDOR_URLS.items():
            assert "tudorwatch.com" in url, f"URL '{key}' should point to tudorwatch.com"
