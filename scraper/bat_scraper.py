"""
BaT Scraper using Selenium - Clicks "Show More" to load all listings

Install first:
    pip install selenium webdriver-manager
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime

class BATSeleniumScraper:
    def __init__(self, headless=False):
        self.base_url = "https://bringatrailer.com"
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        print("Starting Chrome browser...")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Browser started!\n")
    
    def click_show_more(self, max_clicks=10):
        """
        Click the "Show More" button repeatedly to load all listings
        
        Args:
            max_clicks: Maximum number of times to click (to prevent infinite loop)
        """
        clicks = 0
        
        while clicks < max_clicks:
            try:
                show_more_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button-show-more"))
                )

                self.driver.execute_script("arguments[0].scrollIntoView(true);", show_more_button)
                time.sleep(0.5)

                show_more_button.click()
                clicks += 1
                print(f"  Clicked 'Show More' ({clicks}/{max_clicks})")

                time.sleep(2)
                
            except TimeoutException:
                print(f"  No more 'Show More' button found (loaded all listings)")
                break
            except Exception as e:
                print(f"  Error clicking button: {e}")
                break
        
        if clicks >= max_clicks:
            print(f"  Reached max clicks ({max_clicks})")
        
        return clicks
    
    def get_model_page(self, url, max_clicks=10):
        """
        Load a model page and click "Show More" to load all listings
        
        Args:
            url: The model page URL
            max_clicks: Maximum times to click "Show More"
        """
        print(f"Loading: {url}")
        self.driver.get(url)
        
        try:
            print("Waiting for listings to load...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "listing-card"))
            )
            print("✓ Initial listings loaded\n")
        except Exception as e:
            print(f"⚠️  Timeout waiting for listings: {e}")

        print(f"Loading more listings (max {max_clicks} clicks)...")
        total_clicks = self.click_show_more(max_clicks=max_clicks)
        print(f"\nTotal 'Show More' clicks: {total_clicks}\n")

        time.sleep(2)

        return self.driver.page_source
    
    def parse_page(self, html):
        """Parse listing cards from page HTML"""
        soup = BeautifulSoup(html, 'html.parser')

        cards = soup.find_all('a', class_='listing-card')
        print(f"Found {len(cards)} total listing cards\n")
        
        listings = []
        for card in cards:
            title_elem = card.find('h3')
            if not title_elem:
                title_elem = card.find('h2')
            
            title = title_elem.get_text(strip=True) if title_elem else None
            url = card.get('href')
            
            if title and url:
                if not url.startswith('http'):
                    url = f"https://bringatrailer.com{url}"
                
                listings.append({
                    'url': url,
                    'title': title,
                    'card_html': str(card)
                })
        
        return listings
    
    def parse_listing_data(self, listing):
        """Parse data from a listing card"""
        soup = BeautifulSoup(listing['card_html'], 'html.parser')
        
        data = {
            'url': listing['url'],
            'title': listing['title'],
            'source': 'bringatrailer'
        }

        year_match = re.search(r'\b(19|20)\d{2}\b', data['title'])
        if year_match:
            data['year'] = int(year_match.group())

        mileage_match = re.search(r'(\d+\.?\d*)k-Mile', data['title'], re.I)
        if mileage_match:
            data['mileage'] = int(float(mileage_match.group(1)) * 1000)

        results = soup.find('div', class_='item-results')
        if results:
            text = results.get_text(strip=True)

            price_match = re.search(r'\$\s?([\d,]+)', text)
            if price_match:
                data['price'] = int(price_match.group(1).replace(',', ''))

            date_match = re.search(r'on\s+(\d{1,2}/\d{1,2}/\d{2,4})', text)
            if date_match:
                try:
                    data['sale_date'] = datetime.strptime(date_match.group(1), '%m/%d/%y').date()
                except:
                    pass

        excerpt = soup.find('div', class_='item-excerpt')
        if excerpt and 'mileage' not in data:
            excerpt_text = excerpt.get_text()
            mileage_match = re.search(r'has\s+(\d{1,3}(?:,\d{3})*)\s*miles', excerpt_text, re.I)
            if not mileage_match:
                mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*miles', excerpt_text, re.I)
            
            if mileage_match:
                data['mileage'] = int(mileage_match.group(1).replace(',', ''))
        
        return data
    
    def scrape_slr_mclaren(self, max_clicks=20):
        """
        Scrape Mercedes SLR McLaren from dedicated model page
        
        Args:
            max_clicks: Maximum times to click "Show More" (20 should get ~100+ listings)
        """
        try:
            url = "https://bringatrailer.com/mercedes-benz/slr-mclaren/"
            
            html = self.get_model_page(url, max_clicks=max_clicks)
            listings = self.parse_page(html)
            
            print("Parsing listing data...")
            parsed = [self.parse_listing_data(l) for l in listings]
            
            return parsed
        finally:
            print("\nClosing browser...")
            self.driver.quit()


if __name__ == '__main__':
    print("=" * 70)
    print("Selenium BaT Scraper - Mercedes SLR McLaren")
    print("=" * 70)
    print("\nThis will:")
    print("  1. Open Chrome browser")
    print("  2. Navigate to BaT SLR McLaren page")
    print("  3. Click 'Show More' button repeatedly to load all listings")
    print("  4. Extract all listing data\n")

    scraper = BATSeleniumScraper(headless=False)

    listings = scraper.scrape_slr_mclaren(max_clicks=20)
    
    if listings:
        print(f"\n{'='*70}")
        print(f"✅ FOUND {len(listings)} SLR McLAREN LISTINGS")
        print(f"{'='*70}\n")

        print("First 10 listings:\n")
        for i, listing in enumerate(listings[:10], 1):
            print(f"{i}. {listing['title']}")
            if 'year' in listing:
                print(f"   Year: {listing['year']}")
            if 'price' in listing:
                print(f"   Price: ${listing['price']:,}")
            if 'mileage' in listing:
                print(f"   Mileage: {listing['mileage']:,} miles")
            if 'sale_date' in listing:
                print(f"   Sold: {listing['sale_date']}")
            print(f"   URL: {listing['url']}\n")

        sold = [l for l in listings if 'price' in l]
        if sold:
            prices = [l['price'] for l in sold]
            print(f"{'='*70}")
            print("SUMMARY STATISTICS:")
            print(f"  Total listings scraped: {len(listings)}")
            print(f"  Sold with price data: {len(sold)}")
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
                    print(f"    {year}: {years[year]} listings")
            
            print(f"{'='*70}")

        print("\nSaving results to slr_mclaren_listings.txt...")
        with open('slr_mclaren_listings.txt', 'w') as f:
            for listing in listings:
                f.write(f"{listing['title']}\n")
                f.write(f"  URL: {listing['url']}\n")
                if 'price' in listing:
                    f.write(f"  Price: ${listing['price']:,}\n")
                if 'year' in listing:
                    f.write(f"  Year: {listing['year']}\n")
                if 'mileage' in listing:
                    f.write(f"  Mileage: {listing['mileage']:,}\n")
                if 'sale_date' in listing:
                    f.write(f"  Sold: {listing['sale_date']}\n")
                f.write("\n")
        print("✓ Saved to slr_mclaren_listings.txt")
        
    else:
        print("\n⚠️  No listings found")