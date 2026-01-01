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
import json
import os

"""
scrapes listings for make and model, returns in format of Listing object
"""
class BATSeleniumScraper:
    def __init__(self, max_listings, make, model, write_output, headless=False):
        self.base_url = "https://bringatrailer.com/"
        self.max_listings = max_listings
        self.max_clicks = 8
        self.make = make
        self.model = model
        self.write_output = write_output
        chrome_options = Options()
        
        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        print("Starting browser...")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Browser started\n")
    
    def click_show_more(self, max_clicks):
        """
        Load all listings by calling Knockout.js loadNextPage() on the auctions container.
        """
        clicks = 0
        consecutive_failures = 0
        
        while clicks < max_clicks:
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                
                listings_before = len(self.driver.find_elements(By.CLASS_NAME, "listing-card"))
                
                result = self.driver.execute_script("""
                    var container = document.querySelector('.auctions-completed-container');
                    if (!container) return {error: 'Container not found'};
                    
                    var context = ko.contextFor(container);
                    if (!context || !context.$data) return {error: 'No Knockout context'};
                    
                    var vm = context.$data;
                    
                    var moreAvailable = ko.unwrap(vm.moreListingsAvailable);
                    if (!moreAvailable) return {done: true, reason: 'moreListingsAvailable = false'};
                    
                    if (typeof vm.loadNextPage === 'function') {
                        vm.loadNextPage();
                        return {success: true};
                    }
                    
                    return {error: 'No loadNextPage function'};
                """)
                
                if 'done' in result:
                    print(f"\nAll listings loaded: {result['reason']}")
                    break
                
                if 'error' in result:
                    print(f"\nError: {result['error']}")
                    consecutive_failures += 1
                    if consecutive_failures >= 2:
                        break
                    continue
                
                if 'success' in result:
                    clicks += 1
                    time.sleep(3)
                    
                    for wait_attempt in range(15):
                        listings_after = len(self.driver.find_elements(By.CLASS_NAME, "listing-card"))
                        
                        if listings_after > listings_before:
                            new_count = listings_after - listings_before
                            print(f"  Click {clicks}: +{new_count} listings (total: {listings_after})")
                            consecutive_failures = 0
                            time.sleep(1)
                            break
                        
                        time.sleep(1)
                    else:
                        print(f"  Click {clicks}: No new listings loaded")
                        consecutive_failures += 1
                        if consecutive_failures >= 2:
                            break
                
            except Exception as e:
                print(f"Exception: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 2:
                    break
        
        final_count = len(self.driver.find_elements(By.CLASS_NAME, "listing-card"))
        print(f"\n{'='*70}")
        print(f"Loading complete: {final_count} listings found")
        print(f"{'='*70}\n")
        return clicks
    
    """
    Listing:
        vin: string // also called "chassis"
        url: string
        year: integer
        make: string
        model: string
        trim: string
        mileage: integer
        price: integer
        endDate: datetime
    """
    def scrape_listing_detail(self, url):
        """
        scrape detailed information from an individual listing page
        """
        try:
            self.driver.get(url)
            time.sleep(2)
            
            # placeholder, todo
            # get information from page, return Listing object
            detail_data = {}

            return detail_data
            
        except Exception as e:
            print(f"    Error scraping detail page: {e}")
            return {}

    def get_model_page(self, url, max_clicks, scrape_details=True):
        print(f"Loading: {url}\n")
        self.driver.get(url)
        
        try:
            time.sleep(2)
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        except:
            pass
        
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "listing-card"))
            )
            initial = len(self.driver.find_elements(By.CLASS_NAME, "listing-card"))
            print(f"Initial page loaded: {initial} listings\n")
        except Exception as e:
            print(f"Timeout waiting for listings: {e}\n")

        print("Loading all listings...")
        print("="*70)
        self.click_show_more(max_clicks=max_clicks)
        
        time.sleep(2)
        html = self.driver.page_source
        
        print("\nParsing listing cards...")
        listings = self.parse_page(html)
        parsed = []
        
        for i, listing in enumerate(listings, 1):
            listing_data = self.parse_listing_data(listing)
            
            if scrape_details:
                if i % 10 == 0 or i == 1:
                    print(f"  Scraping details: {i}/{len(listings)}")
                
                detail_data = self.scrape_listing_detail(listing['url'])
                
                self.driver.back()
                time.sleep(1)
            
            parsed.append(detail_data)
        
        if scrape_details:
            print(f"  Completed detail scraping for {len(listings)} listings")
        
        return parsed
    
    def parse_page(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('a', class_='listing-card')
        
        listings = []
        for card in cards:
            title_elem = card.find('h3') or card.find('h2')
            title = title_elem.get_text(strip=True) if title_elem else None
            url = card.get('href')
            
            if title and url:
                if not url.startswith('http'):
                    url = f"https://bringatrailer.com{url}"
                listings.append({'url': url, 'title': title, 'card_html': str(card)})
            if len(listings) == self.max_listings:
                break
        return listings
    

    # listing card overview, including url if scraping more detail
    def parse_listing_data(self, listing):
        soup = BeautifulSoup(listing['card_html'], 'html.parser')
        data = {'url': listing['url'], 'title': listing['title'], 'source': 'bringatrailer'}

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

        if 'mileage' not in data:
            excerpt = soup.find('div', class_='item-excerpt')
            if excerpt:
                excerpt_text = excerpt.get_text()
                mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*miles', excerpt_text, re.I)
                if mileage_match:
                    data['mileage'] = int(mileage_match.group(1).replace(',', ''))
        
        return data
    
    def scrape_model(self):
        try:
            url = self.base_url + str.format("{0}/{1}/", self.make, self.model)
            parsed = self.get_model_page(url, max_clicks=self.max_clicks)
            # parsed is a list of Listing objects
            return parsed
        finally:
            print("\nClosing browser")
            self.driver.quit()

    def save_to_json(self, data):
        json_ob = json.dumps(data, indent=4)
        output_path = str.format("data/json/{0}_data.json", self.model)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w+") as f:
            f.write(json_ob)
        
    def save_to_txt(self, listings):
        print(f"\n{'='*70}")
        print(f"Successfully scraped {len(listings)} {self.model} listings")
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

        print("\nSaving results to file...")
        filename = 'data/{self.model}_data.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"BringATrailer - {self.model} Listings\n")
            f.write(f"Total: {len(listings)} listings\n")
            f.write(f"Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
        
        print(f"Saved to {filename}")
        print(f"\nDone")

    """
    example
    """
    def scrape_slr_mclaren(self, max_clicks=30, scrape_details=False):
        try:
            url = "https://bringatrailer.com/mercedes-benz/slr-mclaren/"
            parsed = self.get_model_page(url, max_clicks=max_clicks, scrape_details=scrape_details)
            return parsed
        finally:
            print("\nClosing browser...")
            self.driver.quit()
