#!/usr/bin/env python3
"""
Tudor Watch Finder - Main Entry Point

Finds Tudor retailers near a zip code and checks inventory via phone calls.
Specifically designed for finding the Tudor Ranger 36mm with beige domed dial.
"""

import argparse
import os
import sys
import json
from datetime import datetime
from typing import Optional

from config import SEARCH_CONFIG, WATCH_CONFIG, OUTPUT_CONFIG
from scraper import TudorScraper, Retailer
from filter import RetailerFilter
from phone_caller import InventoryChecker, InventoryStatus


def load_or_scrape_retailers(force_refresh: bool = False) -> list:
    """Load retailers from cache or scrape fresh data"""
    cache_file = "retailers.json"

    if not force_refresh and os.path.exists(cache_file):
        print(f"Loading retailers from cache ({cache_file})...")
        return TudorScraper.load_retailers(cache_file)

    print("Scraping Tudor retailers (this may take a few minutes)...")
    scraper = TudorScraper()
    retailers = scraper.scrape_all_retailers()
    scraper.save_retailers(retailers, cache_file)
    return retailers


def display_retailers(filtered: list, show_all: bool = False):
    """Display filtered retailers"""
    print(f"\nFound {len(filtered)} retailers within range:")
    print("-" * 70)

    display_list = filtered if show_all else filtered[:10]

    for i, (retailer, distance) in enumerate(display_list, 1):
        phone_status = "📞" if retailer.phone else "❌ No phone"
        print(f"{i:2}. {retailer.name}")
        print(f"    📍 {distance:.1f} miles away")
        print(f"    🏠 {retailer.address or 'Address not available'}")
        print(f"    {phone_status} {retailer.phone or ''}")
        print()

    if not show_all and len(filtered) > 10:
        print(f"... and {len(filtered) - 10} more retailers")
        print("Use --show-all to see all retailers")


def run_inventory_check(
    filtered: list,
    api_key: str,
    max_calls: Optional[int] = None,
    delay: int = 30
):
    """Run the inventory check process"""
    # Filter to retailers with phone numbers
    with_phones = [(r, d) for r, d in filtered if r.phone]

    if not with_phones:
        print("\n❌ No retailers with phone numbers found in the search area!")
        return None

    print(f"\n📞 Found {len(with_phones)} retailers with phone numbers")

    if max_calls:
        print(f"   Will call up to {max_calls} retailers")
        with_phones = with_phones[:max_calls]

    # Confirm before making calls
    print(f"\n⚠️  About to make {len(with_phones)} phone calls using Bland AI")
    print(f"   Watch: {WATCH_CONFIG['full_name']}")
    print(f"   Reference: {WATCH_CONFIG['reference']}")

    confirm = input("\nProceed with calls? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("Cancelled.")
        return None

    # Make the calls
    checker = InventoryChecker(api_key)
    results = checker.check_retailers(with_phones, delay_between_calls=delay, max_calls=max_calls)

    # Save and display results
    checker.save_results(OUTPUT_CONFIG['results_file'])
    checker.print_summary()

    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Find Tudor Ranger 36mm (beige dial) at nearby retailers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search within 50 miles of San Francisco
  python main.py --zip 94117 --radius 50

  # Just list retailers without calling
  python main.py --zip 94117 --no-call

  # Call only the nearest 5 retailers
  python main.py --zip 94117 --max-calls 5

  # Refresh retailer data from Tudor website
  python main.py --zip 94117 --refresh
        """
    )

    parser.add_argument(
        '--zip', '-z',
        type=str,
        default=SEARCH_CONFIG['zip_code'],
        help=f"Center zip code for search (default: {SEARCH_CONFIG['zip_code']})"
    )

    parser.add_argument(
        '--radius', '-r',
        type=float,
        default=SEARCH_CONFIG['radius_miles'],
        help=f"Search radius in miles (default: {SEARCH_CONFIG['radius_miles']})"
    )

    parser.add_argument(
        '--api-key', '-k',
        type=str,
        default=os.environ.get('BLAND_API_KEY'),
        help="Bland AI API key (or set BLAND_API_KEY env var)"
    )

    parser.add_argument(
        '--no-call',
        action='store_true',
        help="Just list retailers, don't make phone calls"
    )

    parser.add_argument(
        '--max-calls', '-m',
        type=int,
        default=None,
        help="Maximum number of calls to make"
    )

    parser.add_argument(
        '--delay', '-d',
        type=int,
        default=30,
        help="Delay between calls in seconds (default: 30)"
    )

    parser.add_argument(
        '--refresh',
        action='store_true',
        help="Force refresh of retailer data from Tudor website"
    )

    parser.add_argument(
        '--show-all',
        action='store_true',
        help="Show all retailers (not just first 10)"
    )

    args = parser.parse_args()

    # Header
    print("=" * 70)
    print("🔍 TUDOR WATCH FINDER")
    print("=" * 70)
    print(f"Watch: {WATCH_CONFIG['full_name']}")
    print(f"Reference: {WATCH_CONFIG['reference']}")
    print(f"Price: ${WATCH_CONFIG['price']:,}")
    print("-" * 70)

    # Load retailers
    retailers = load_or_scrape_retailers(force_refresh=args.refresh)
    print(f"Loaded {len(retailers)} US retailers")

    # Filter by location
    filter = RetailerFilter()
    try:
        filtered = filter.filter_by_zip_code(retailers, args.zip, args.radius)
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    if not filtered:
        print(f"\n❌ No retailers found within {args.radius} miles of {args.zip}")
        sys.exit(1)

    # Display retailers
    display_retailers(filtered, show_all=args.show_all)

    # Make calls if not disabled
    if args.no_call:
        print("\n📋 Call mode disabled. Use without --no-call to check inventory.")
        return

    if not args.api_key:
        print("\n⚠️  No Bland AI API key provided!")
        print("   Set BLAND_API_KEY environment variable or use --api-key")
        print("   Skipping phone calls...")
        return

    run_inventory_check(
        filtered,
        args.api_key,
        max_calls=args.max_calls,
        delay=args.delay
    )


if __name__ == "__main__":
    main()
