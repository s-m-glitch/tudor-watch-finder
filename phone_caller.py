"""
Bland AI Phone Caller
Makes automated phone calls to Tudor retailers to check watch inventory
"""

import os
import time
import json
import requests
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from scraper import Retailer
from config import WATCH_CONFIG, BLAND_CONFIG, CALL_SCRIPT


class InventoryStatus(Enum):
    """Possible inventory statuses"""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    CAN_ORDER = "can_order"
    WAITLIST = "waitlist"
    UNKNOWN = "unknown"
    CALL_FAILED = "call_failed"
    NO_ANSWER = "no_answer"


@dataclass
class CallResult:
    """Result of a phone call to a retailer"""
    retailer_name: str
    retailer_phone: str
    call_id: str
    status: InventoryStatus
    transcript: Optional[str]
    summary: Optional[str]
    call_duration: Optional[int]  # in seconds
    timestamp: str
    raw_response: Optional[Dict]

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['status'] = self.status.value
        return result


class BlandAICaller:
    """
    Makes phone calls using Bland AI to check watch inventory

    Bland AI Documentation: https://docs.bland.ai/
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Bland AI caller

        Args:
            api_key: Bland AI API key (or set BLAND_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('BLAND_API_KEY') or BLAND_CONFIG.get('api_key')
        if not self.api_key:
            raise ValueError("Bland AI API key is required. Set BLAND_API_KEY environment variable.")

        self.base_url = BLAND_CONFIG['base_url']
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    def _build_call_prompt(self) -> str:
        """Build the AI prompt for the phone call"""
        watch = WATCH_CONFIG

        prompt = f"""You are calling a watch store to inquire about a specific Tudor watch.

WATCH DETAILS:
- Model: Tudor {watch['model']}
- Reference: {watch['reference']}
- Case: {watch['case_size']} {watch['case_material']}
- Dial: {watch['dial']}
- Price: ${watch['price']:,}

YOUR TASK:
1. Greet the store representative politely
2. Ask if they have the Tudor Ranger 36mm with beige dial in stock (reference M79930-0007)
3. If they don't have it, ask about:
   - When they might get it in stock
   - If there's a waitlist you could join
   - If they can special order it
4. Thank them and end the call politely

IMPORTANT GUIDELINES:
- Be polite and professional
- Keep the call brief and focused
- Listen carefully to their response
- If they ask for contact information, politely say you'll call back
- Don't provide any personal information

CONVERSATION STYLE:
- Speak naturally, like a genuine customer
- Be patient if they need to check inventory
- Express appreciation for their help
"""
        return prompt

    def _build_call_task(self) -> str:
        """Build the specific task/goal for the call"""
        return f"Find out if the store has the Tudor Ranger 36mm with beige dial (ref: M79930-0007) in stock, and if not, ask about availability timeline or waitlist options."

    def make_call(self, phone_number: str, retailer_name: str) -> CallResult:
        """
        Make a phone call to check inventory

        Args:
            phone_number: Phone number to call (with country code)
            retailer_name: Name of the retailer (for logging)

        Returns:
            CallResult with the call outcome
        """
        # Clean phone number - ensure it has country code
        clean_phone = self._clean_phone_number(phone_number)

        timestamp = datetime.now().isoformat()

        # Build the API request
        payload = {
            "phone_number": clean_phone,
            "task": self._build_call_task(),
            "model": "enhanced",  # Use enhanced model for better understanding
            "voice": BLAND_CONFIG.get('voice', 'nat'),
            "first_sentence": CALL_SCRIPT['greeting'],
            "wait_for_greeting": BLAND_CONFIG.get('wait_for_greeting', True),
            "record": BLAND_CONFIG.get('record', True),
            "max_duration": BLAND_CONFIG.get('max_duration', 120),
            "transfer_phone_number": None,  # Don't transfer
            "language": "en",
            "webhook": None,  # We'll poll for results instead
            "metadata": {
                "retailer_name": retailer_name,
                "watch_reference": WATCH_CONFIG['reference'],
                "timestamp": timestamp
            }
        }

        try:
            print(f"  Calling {retailer_name} at {clean_phone}...")

            response = requests.post(
                f"{self.base_url}/calls",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    data = None

                call_id = data.get('call_id') if data and isinstance(data, dict) else None

                if call_id:
                    # Wait for call to complete and get results
                    result = self._wait_for_call_completion(call_id)
                    result.retailer_name = retailer_name
                    result.retailer_phone = clean_phone
                    result.timestamp = timestamp
                    return result
                else:
                    return CallResult(
                        retailer_name=retailer_name,
                        retailer_phone=clean_phone,
                        call_id="",
                        status=InventoryStatus.CALL_FAILED,
                        transcript=None,
                        summary=f"API returned no call_id: {data}",
                        call_duration=None,
                        timestamp=timestamp,
                        raw_response=data
                    )
            else:
                return CallResult(
                    retailer_name=retailer_name,
                    retailer_phone=clean_phone,
                    call_id="",
                    status=InventoryStatus.CALL_FAILED,
                    transcript=None,
                    summary=f"API error: {response.status_code} - {response.text}",
                    call_duration=None,
                    timestamp=timestamp,
                    raw_response=None
                )

        except Exception as e:
            return CallResult(
                retailer_name=retailer_name,
                retailer_phone=clean_phone,
                call_id="",
                status=InventoryStatus.CALL_FAILED,
                transcript=None,
                summary=f"Exception: {str(e)}",
                call_duration=None,
                timestamp=timestamp,
                raw_response=None
            )

    def _wait_for_call_completion(
        self,
        call_id: str,
        max_wait: int = 300,
        poll_interval: int = 5
    ) -> CallResult:
        """
        Wait for a call to complete and retrieve results

        Args:
            call_id: The Bland AI call ID
            max_wait: Maximum time to wait in seconds
            poll_interval: How often to poll for status

        Returns:
            CallResult with the call outcome
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.base_url}/calls/{call_id}",
                    headers=self.headers,
                    timeout=30
                )

                if response.status_code == 200:
                    # Safely parse JSON
                    try:
                        data = response.json()
                    except Exception:
                        data = None

                    # Handle None or empty response gracefully
                    if not data or not isinstance(data, dict):
                        print(f"    Call status: waiting (empty response)...")
                        time.sleep(poll_interval)
                        continue

                    status = data.get('status', '')

                    # Check if call is complete - added 'busy' and 'voicemail' statuses
                    if status in ['completed', 'ended', 'failed', 'no-answer', 'busy', 'voicemail']:
                        return self._parse_call_result(call_id, data)

                    print(f"    Call status: {status}...")
                else:
                    print(f"    Call status: API returned {response.status_code}...")

            except Exception as e:
                print(f"    Error polling call status: {e}")

            time.sleep(poll_interval)

        # Timeout
        return CallResult(
            retailer_name="",
            retailer_phone="",
            call_id=call_id,
            status=InventoryStatus.CALL_FAILED,
            transcript=None,
            summary="Call timed out waiting for completion",
            call_duration=None,
            timestamp="",
            raw_response=None
        )

    def _parse_call_result(self, call_id: str, data: Dict) -> CallResult:
        """Parse the call result data from Bland AI"""

        # Safety check for None data
        if not data or not isinstance(data, dict):
            return CallResult(
                retailer_name="",
                retailer_phone="",
                call_id=call_id,
                status=InventoryStatus.CALL_FAILED,
                transcript=None,
                summary="No data returned from API",
                call_duration=None,
                timestamp="",
                raw_response=None
            )

        status = data.get('status', '')
        transcript = data.get('transcript', '') or data.get('concatenated_transcript', '')
        summary = data.get('summary', '') or (data.get('analysis') or {}).get('summary', '')
        duration = data.get('call_length') or data.get('duration')

        # Handle busy/voicemail/no-answer statuses directly
        if status in ['busy', 'no-answer', 'voicemail']:
            return CallResult(
                retailer_name="",  # Will be set by caller
                retailer_phone="",  # Will be set by caller
                call_id=call_id,
                status=InventoryStatus.NO_ANSWER,
                transcript=transcript,
                summary=f"Call ended with status: {status}",
                call_duration=duration,
                timestamp="",  # Will be set by caller
                raw_response=data
            )

        # Determine inventory status from transcript/summary
        inventory_status = self._analyze_inventory_status(transcript, summary)

        return CallResult(
            retailer_name="",  # Will be set by caller
            retailer_phone="",  # Will be set by caller
            call_id=call_id,
            status=inventory_status,
            transcript=transcript,
            summary=summary,
            call_duration=duration,
            timestamp="",  # Will be set by caller
            raw_response=data
        )

    def _analyze_inventory_status(self, transcript: str, summary: str) -> InventoryStatus:
        """
        Analyze the call transcript to determine inventory status

        Args:
            transcript: Full call transcript
            summary: AI-generated summary

        Returns:
            InventoryStatus enum value
        """
        text = f"{transcript} {summary}".lower()

        # Check for no answer / voicemail first
        no_answer_phrases = [
            "no answer", "voicemail", "didn't pick up",
            "couldn't reach", "busy signal", "not available",
            "leave a message", "after the tone", "mailbox"
        ]
        for phrase in no_answer_phrases:
            if phrase in text:
                return InventoryStatus.NO_ANSWER

        # Check for NEGATIVE indicators FIRST (before positive ones)
        # This prevents "not in stock" from matching "in stock"
        out_of_stock_phrases = [
            "not in stock", "out of stock", "don't have", "do not have",
            "don't carry", "do not carry", "sold out", "not available",
            "currently out", "wasn't in stock", "was not in stock",
            "weren't in stock", "were not in stock", "isn't in stock",
            "is not in stock", "aren't in stock", "are not in stock",
            "doesn't have", "does not have", "didn't have", "did not have",
            "unavailable", "no longer", "discontinued", "can't get",
            "cannot get", "unable to", "don't currently have",
            "do not currently have", "not currently in stock",
            "currently not in stock", "currently unavailable"
        ]

        for phrase in out_of_stock_phrases:
            if phrase in text:
                # Found a negative indicator - now check for waitlist/order options

                # Check for waitlist
                waitlist_phrases = [
                    "waitlist", "waiting list", "wait list", "interest list",
                    "put you on a list", "add you to a list", "notify you",
                    "call you when", "contact you when", "let you know when",
                    "register.*interest", "take your information",
                    "client book", "client list", "come into the store",
                    "stop by", "visit.*store", "in-store visit", "in store visit",
                    "happy to add you", "add you if you"
                ]
                for wp in waitlist_phrases:
                    if re.search(wp, text):
                        return InventoryStatus.WAITLIST

                # Check for can order
                can_order_phrases = [
                    "can order", "could order", "special order", "order it for you",
                    "order one for you", "place an order", "get it in",
                    "take a few weeks", "take some time", "within a month",
                    "expect.*shipment", "expecting.*shipment", "more coming"
                ]
                for cop in can_order_phrases:
                    if re.search(cop, text):
                        return InventoryStatus.CAN_ORDER

                return InventoryStatus.OUT_OF_STOCK

        # Now check for POSITIVE indicators (only if no negative indicators found)
        in_stock_phrases = [
            "we have it", "we do have", "yes we have", "have it in stock",
            "have one in stock", "have them in stock", "is in stock",
            "are in stock", "it's available", "it is available",
            "they're available", "they are available", "got it",
            "got one", "got them", "have that", "have the",
            "currently have", "do have it", "in stock now",
            "available now", "ready for", "can come in today",
            "come pick it up", "have it here"
        ]

        for phrase in in_stock_phrases:
            if phrase in text:
                return InventoryStatus.IN_STOCK

        # Check for waitlist mentions without explicit out of stock
        waitlist_phrases = [
            "waitlist", "waiting list", "wait list", "interest list"
        ]
        for phrase in waitlist_phrases:
            if phrase in text:
                return InventoryStatus.WAITLIST

        # Check for order mentions without explicit out of stock
        order_phrases = [
            "can order", "special order"
        ]
        for phrase in order_phrases:
            if phrase in text:
                return InventoryStatus.CAN_ORDER

        return InventoryStatus.UNKNOWN

    def _clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number for API"""
        # Remove all non-digit characters except +
        digits = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Ensure it starts with +1 for US numbers
        if not digits.startswith('+'):
            if digits.startswith('1') and len(digits) == 11:
                digits = '+' + digits
            elif len(digits) == 10:
                digits = '+1' + digits

        return digits


class InventoryChecker:
    """
    Orchestrates inventory checking across multiple retailers
    """

    def __init__(self, api_key: Optional[str] = None):
        self.caller = BlandAICaller(api_key)
        self.results: List[CallResult] = []

    def check_retailers(
        self,
        retailers: List[Tuple[Retailer, float]],
        delay_between_calls: int = 30,
        max_calls: Optional[int] = None
    ) -> List[CallResult]:
        """
        Check inventory at multiple retailers

        Args:
            retailers: List of (Retailer, distance) tuples
            delay_between_calls: Seconds to wait between calls
            max_calls: Maximum number of calls to make (None for all)

        Returns:
            List of CallResult objects
        """
        # Filter to only retailers with phone numbers
        retailers_with_phones = [
            (r, d) for r, d in retailers if r.phone
        ]

        if not retailers_with_phones:
            print("No retailers with phone numbers found!")
            return []

        # Limit if specified
        if max_calls:
            retailers_with_phones = retailers_with_phones[:max_calls]

        print(f"\nChecking inventory at {len(retailers_with_phones)} retailers...")
        print(f"Watch: {WATCH_CONFIG['full_name']}")
        print(f"Reference: {WATCH_CONFIG['reference']}")
        print("-" * 60)

        for i, (retailer, distance) in enumerate(retailers_with_phones):
            print(f"\n[{i+1}/{len(retailers_with_phones)}] {retailer.name} ({distance:.1f} mi)")

            result = self.caller.make_call(retailer.phone, retailer.name)
            self.results.append(result)

            # Print result
            status_emoji = {
                InventoryStatus.IN_STOCK: "✅",
                InventoryStatus.OUT_OF_STOCK: "❌",
                InventoryStatus.CAN_ORDER: "📦",
                InventoryStatus.WAITLIST: "📋",
                InventoryStatus.NO_ANSWER: "📵",
                InventoryStatus.CALL_FAILED: "⚠️",
                InventoryStatus.UNKNOWN: "❓"
            }

            emoji = status_emoji.get(result.status, "❓")
            print(f"  {emoji} Status: {result.status.value}")

            if result.summary:
                print(f"  Summary: {result.summary[:100]}...")

            # Wait between calls
            if i < len(retailers_with_phones) - 1:
                print(f"  Waiting {delay_between_calls}s before next call...")
                time.sleep(delay_between_calls)

        return self.results

    def save_results(self, filepath: str = "inventory_results.json"):
        """Save results to JSON file"""
        data = {
            "watch": WATCH_CONFIG,
            "timestamp": datetime.now().isoformat(),
            "results": [r.to_dict() for r in self.results],
            "summary": self._generate_summary()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\nResults saved to {filepath}")

    def _generate_summary(self) -> Dict:
        """Generate a summary of all results"""
        status_counts = {}
        for result in self.results:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        in_stock = [r for r in self.results if r.status == InventoryStatus.IN_STOCK]

        return {
            "total_calls": len(self.results),
            "status_breakdown": status_counts,
            "in_stock_retailers": [
                {"name": r.retailer_name, "phone": r.retailer_phone}
                for r in in_stock
            ]
        }

    def print_summary(self):
        """Print a summary of results"""
        summary = self._generate_summary()

        print("\n" + "=" * 60)
        print("INVENTORY CHECK SUMMARY")
        print("=" * 60)
        print(f"Watch: {WATCH_CONFIG['full_name']}")
        print(f"Total calls made: {summary['total_calls']}")
        print("\nStatus breakdown:")
        for status, count in summary['status_breakdown'].items():
            print(f"  - {status}: {count}")

        if summary['in_stock_retailers']:
            print("\n🎉 IN STOCK AT:")
            for r in summary['in_stock_retailers']:
                print(f"  ✅ {r['name']} - {r['phone']}")
        else:
            print("\n😔 Watch not found in stock at any called retailer")


def main():
    """Demo of phone calling functionality"""
    print("Bland AI Phone Caller - Tudor Watch Inventory Checker")
    print("=" * 60)

    # Check for API key
    api_key = os.environ.get('BLAND_API_KEY')
    if not api_key:
        print("ERROR: BLAND_API_KEY environment variable not set")
        print("Set it with: export BLAND_API_KEY='your-api-key'")
        return

    # This would normally be called from main.py with real retailers
    print("\nThis module is designed to be used with main.py")
    print("Run: python main.py --zip 94117 --radius 50")


if __name__ == "__main__":
    main()
