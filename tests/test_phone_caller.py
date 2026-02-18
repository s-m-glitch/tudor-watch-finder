"""Tests for phone_caller.py — inventory status analysis and phone number cleaning"""

import pytest
from phone_caller import BlandAICaller, InventoryStatus


class TestInventoryStatusAnalysis:
    """Test the keyword-based inventory status analysis"""

    @pytest.fixture
    def caller(self):
        """Create a BlandAICaller with a dummy key (won't make real calls)"""
        # Patch so it doesn't complain about missing key
        import os
        os.environ["BLAND_API_KEY"] = "test-key-not-real"
        c = BlandAICaller(api_key="test-key-not-real")
        return c

    # ── In Stock ──

    def test_in_stock_we_have_it(self, caller):
        assert caller._analyze_inventory_status("Yes, we have it in stock", "") == InventoryStatus.IN_STOCK

    def test_in_stock_available(self, caller):
        assert caller._analyze_inventory_status("The watch is available now", "") == InventoryStatus.IN_STOCK

    def test_in_stock_from_summary(self, caller):
        assert caller._analyze_inventory_status("", "The store confirmed that the watch is available") == InventoryStatus.IN_STOCK

    # ── Out of Stock ──

    def test_out_of_stock_dont_have(self, caller):
        assert caller._analyze_inventory_status("Sorry, we don't have that model", "") == InventoryStatus.OUT_OF_STOCK

    def test_out_of_stock_sold_out(self, caller):
        assert caller._analyze_inventory_status("That model is sold out", "") == InventoryStatus.OUT_OF_STOCK

    def test_out_of_stock_not_in_stock(self, caller):
        assert caller._analyze_inventory_status("That's not in stock right now", "") == InventoryStatus.OUT_OF_STOCK

    # ── Waitlist ──

    def test_waitlist_explicit(self, caller):
        transcript = "We don't have that in stock but we have a waitlist"
        assert caller._analyze_inventory_status(transcript, "") == InventoryStatus.WAITLIST

    def test_waitlist_client_book(self, caller):
        transcript = "It's not in stock. Come into the store and we can add you to our client book"
        assert caller._analyze_inventory_status(transcript, "") == InventoryStatus.WAITLIST

    def test_waitlist_from_summary(self, caller):
        summary = "The store did not have the Tudor but offered to add the caller to a waitlist"
        assert caller._analyze_inventory_status("", summary) == InventoryStatus.WAITLIST

    # ── Can Order ──

    def test_can_order(self, caller):
        transcript = "We don't have it but we can order it for you"
        assert caller._analyze_inventory_status(transcript, "") == InventoryStatus.CAN_ORDER

    def test_can_order_special(self, caller):
        transcript = "That's out of stock but we can do a special order"
        assert caller._analyze_inventory_status(transcript, "") == InventoryStatus.CAN_ORDER

    # ── No Answer ──

    def test_no_answer_voicemail(self, caller):
        assert caller._analyze_inventory_status("voicemail", "") == InventoryStatus.NO_ANSWER

    # ── Unknown / Automated ──

    def test_unknown_automated_system(self, caller):
        transcript = "Press zero to speak with an associate"
        assert caller._analyze_inventory_status(transcript, "") == InventoryStatus.UNKNOWN

    def test_unknown_no_text(self, caller):
        assert caller._analyze_inventory_status("", "") == InventoryStatus.UNKNOWN


class TestPhoneNumberCleaning:
    @pytest.fixture
    def caller(self):
        import os
        os.environ["BLAND_API_KEY"] = "test-key-not-real"
        return BlandAICaller(api_key="test-key-not-real")

    def test_already_formatted(self, caller):
        assert caller._clean_phone_number("+12125551234") == "+12125551234"

    def test_ten_digit(self, caller):
        assert caller._clean_phone_number("2125551234") == "+12125551234"

    def test_eleven_digit_with_1(self, caller):
        assert caller._clean_phone_number("12125551234") == "+12125551234"

    def test_with_dashes(self, caller):
        assert caller._clean_phone_number("212-555-1234") == "+12125551234"

    def test_with_parens(self, caller):
        assert caller._clean_phone_number("(212) 555-1234") == "+12125551234"
