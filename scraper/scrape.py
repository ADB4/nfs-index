import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
import argparse

from bat_scraper import BATSeleniumScraper


"""
scrapes individual listings for a make and model, saves to json in /data

usage: 
    python3 scrape.py --make "Mercedes-Benz" --model "SLR McLaren" --write-output
    // writes output to json
"""
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape BringATrailer model pages')
    parser.add_argument('--url', help='Direct URL to model page')
    parser.add_argument('--make', help='Make name (e.g., Mercedes-Benz)')
    parser.add_argument('--model', help='Model name (e.g., SLR McLaren)')
    parser.add_argument('--max-listings', type=int, default=32, help='Maximum listings parsed')
    parser.add_argument('--max-clicks', type=int, default=30, help='Maximum pagination clicks')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--write-output', action='store_true', help='Save data to txt')
    parser.add_argument('--output', default='listings.txt', help='Output filename')
    
    args = parser.parse_args()

    print("=" * 70)
    print("BringATrailer Scraper - {args.make} {args.model}")
    print("=" * 70)
    print()

    scraper = BATSeleniumScraper(max_listings=args.max_listings,
                                 make=args.make,
                                 model=args.model, 
                                 write_output=args.write_output, 
                                 headless=False)
    listings = scraper.scrape_model()
    
    # write to json
    if listings:
        print(f"\n{'='*70}")
        print(f"Successfully scraped {len(listings)} {args.model} listings")
        print(f"{'='*70}\n")
        json_ob = json.dumps(listings, indent=4)
        output_path = str.format("data/json/{0}_data.json", self.model)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w+") as f:
            f.write(json_ob)

    else:
        print("\nNo listings found")