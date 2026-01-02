import os
import json
import argparse
from datetime import datetime

from bat_scraper import BATSeleniumScraper

"""
scrapes individual listings for a make and model, saves to json in /data

Usage: 
    python3 scrape.py --make "Mercedes-Benz" --model "SLR McLaren"
    python3 scrape.py --make "Porsche" --model "911 GT3" --max-listings 50
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape BringATrailer model pages')
    parser.add_argument('--make', required=True, help='Make name (e.g., Mercedes-Benz)')
    parser.add_argument('--model', required=True, help='Model name (e.g., SLR McLaren)')
    parser.add_argument('--n', type=int, default=4, help='Maximum listings to scrape')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()

    print("=" * 70)
    print(f"BringATrailer Scraper - {args.make} {args.model}")
    print("=" * 70)
    print()

    scraper = BATSeleniumScraper(
        n=args.n,
        make=args.make,
        model=args.model, 
        headless=args.headless
    )
    
    listings = scraper.scrape_model()
    
    if listings:
        print(f"\n{'='*70}")
        print(f"Successfully scraped {len(listings)} {args.model} listings")
        print(f"{'='*70}\n")
        
        sold = [l for l in listings if 'price' in l]
        if sold:
            prices = [l['price'] for l in sold]
            
            print("SUMMARY STATISTICS:")
            print(f"  Total listings: {len(listings)}")
            print(f"  Listings with price data: {len(sold)}")
            print(f"  Average sale price: ${sum(prices)/len(prices):,.0f}")
            print(f"  Price range: ${min(prices):,} - ${max(prices):,}")

            years = {}
            for listing in sold:
                if 'year' in listing:
                    year = listing['year']
                    years[year] = years.get(year, 0) + 1
            
            if years:
                print(f"\n  Sales by year:")
                for year in sorted(years.keys()):
                    print(f"    {year}: {years[year]} listing(s)")
            
            print(f"\n{'='*70}")
        
        model_slug = args.model.lower().replace(' ', '-')
        output_path = f"data/json/{model_slug}_data.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(listings, f, indent=4)
        
        print(f"\nSaved {len(listings)} listings to {output_path}")
        print("Done")
        
    else:
        print("\nNo listings found")
