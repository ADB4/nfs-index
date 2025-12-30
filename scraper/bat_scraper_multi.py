"""
usage:
    python bat_scraper_multi.py --model "SLR McLaren" --make "Mercedes-Benz"
    python bat_scraper_multi.py --url "https://bringatrailer.com/mercedes-benz/slr-mclaren/"
"""

import argparse
from bat_scraper_production import BATSeleniumScraper

def scrape_model_page(url, max_clicks=30, headless=False):
    print("="*70)
    print(f"BringATrailer Scraper")
    print("="*70)
    print(f"URL: {url}\n")
    
    scraper = BATSeleniumScraper(headless=headless)
    
    try:
        print(f"Loading: {url}\n")
        scraper.driver.get(url)
        
        try:
            import time
            time.sleep(2)
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(scraper.driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
        except:
            pass
        
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        try:
            WebDriverWait(scraper.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "listing-card"))
            )
            initial = len(scraper.driver.find_elements(By.CLASS_NAME, "listing-card"))
            print(f"Initial page loaded: {initial} listings\n")
        except Exception as e:
            print(f"Timeout waiting for listings: {e}\n")
        
        print("Loading all listings...")
        print("="*70)
        scraper.click_show_more(max_clicks=max_clicks)
        
        import time
        time.sleep(2)
        html = scraper.driver.page_source
        
        print("\nParsing listing data...")
        listings = scraper.parse_page(html)
        parsed = [scraper.parse_listing_data(l) for l in listings]
        
        return parsed
        
    finally:
        print("\nClosing browser...")
        scraper.driver.quit()

def main():
    parser = argparse.ArgumentParser(description='Scrape BringATrailer model pages')
    parser.add_argument('--url', help='Direct URL to model page')
    parser.add_argument('--make', help='Make name (e.g., Mercedes-Benz)')
    parser.add_argument('--model', help='Model name (e.g., SLR McLaren)')
    parser.add_argument('--max-clicks', type=int, default=30, help='Maximum pagination clicks')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--output', default='listings.txt', help='Output filename')
    
    args = parser.parse_args()
    
    if args.url:
        url = args.url
    elif args.make and args.model:
        make_slug = args.make.lower().replace(' ', '-').replace('&', 'and')
        model_slug = args.model.lower().replace(' ', '-')
        url = f"https://bringatrailer.com/{make_slug}/{model_slug}/"
    else:
        print("Error: Provide either --url or both --make and --model")
        return
    
    listings = scrape_model_page(url, max_clicks=args.max_clicks, headless=args.headless)
    
    if listings:
        print(f"\n{'='*70}")
        print(f"Successfully scraped {len(listings)} listings")
        print(f"{'='*70}\n")
        
        from datetime import datetime
        
        print(f"Saving to {args.output}...")
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(f"BringATrailer Listings\n")
            f.write(f"URL: {url}\n")
            f.write(f"Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {len(listings)} listings\n")
            f.write("="*70 + "\n\n")
            
            for i, listing in enumerate(listings, 1):
                f.write(f"{i}. {listing['title']}\n")
                f.write(f"   URL: {listing['url']}\n")
                if 'year' in listing:
                    f.write(f"   Year: {listing['year']}\n")
                if 'price' in listing:
                    f.write(f"   Price: ${listing['price']:,}\n")
                if 'mileage' in listing:
                    f.write(f"   Mileage: {listing['mileage']:,} miles\n")
                if 'sale_date' in listing:
                    f.write(f"   Sale Date: {listing['sale_date']}\n")
                f.write("\n")
        
        print(f"Saved to {args.output}")
        
        sold = [l for l in listings if 'price' in l]
        if sold:
            prices = [l['price'] for l in sold]
            print(f"\nSummary:")
            print(f"  Total: {len(listings)}")
            print(f"  With prices: {len(sold)}")
            print(f"  Avg price: ${sum(prices)/len(prices):,.0f}")
            print(f"  Range: ${min(prices):,} - ${max(prices):,}")
        
        print(f"\nDone")
    else:
        print("\nNo listings found")

if __name__ == '__main__':
    main()