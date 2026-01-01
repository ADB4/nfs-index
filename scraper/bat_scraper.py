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
    def __init__(self, max_listings, make, model, headless=False):
        self.base_url = "https://bringatrailer.com/"
        self.max_listings = max_listings
        self.max_clicks = 1
        self.make = make
        self.model = model
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
    
    def scrape_listing_detail(self, url):
        """
        scrape detailed information from an individual listing page
        
        returns Listing object with:
            vin: string
            mileage: integer
            location: string
            number_of_bids: integer
            variant: string
        """
        try:
            self.driver.get(url)
            time.sleep(2)
            
            detail_data = {}
            
            # some selenium fuckery
            try:
                essentials = self.driver.find_element(By.CLASS_NAME, "essentials")
                
                items = essentials.find_elements(By.CLASS_NAME, "item")
                for item in items:
                    try:
                        strong = item.find_element(By.TAG_NAME, "strong")
                        label = strong.text.strip().lower()
                        
                        if 'location' in label:
                            link = item.find_element(By.TAG_NAME, "a")
                            detail_data['location'] = link.text.strip()
                        
                        elif 'listing details' in label:
                            ul = item.find_element(By.TAG_NAME, "ul")
                            li_elements = ul.find_elements(By.TAG_NAME, "li")
                            
                            for li in li_elements:
                                text = li.text.strip()
                                
                                if 'chassis:' in text.lower():
                                    try:
                                        link = li.find_element(By.TAG_NAME, "a")
                                        vin = link.text.strip()
                                        if len(vin) == 17:
                                            detail_data['vin'] = vin
                                    except:
                                        vin_match = re.search(r'chassis:\s*([A-HJ-NPR-Z0-9]{17})', text, re.I)
                                        if vin_match:
                                            detail_data['vin'] = vin_match.group(1)
                                
                                elif 'miles' in text.lower() and 'mileage' not in detail_data:
                                    mileage_match = re.search(r'([\d,]+)\s*(?:k\s+)?miles', text, re.I)
                                    if mileage_match:
                                        mileage_str = mileage_match.group(1).replace(',', '')
                                        if 'k' in text.lower():
                                            detail_data['mileage'] = int(float(mileage_str) * 1000)
                                        else:
                                            detail_data['mileage'] = int(mileage_str)
                    except:
                        continue
                        
            except:
                pass
            
            try:
                listing_stats = self.driver.find_element(By.ID, "listing-bid")
                stats_rows = listing_stats.find_elements(By.CLASS_NAME, "listing-stats-stat")
                
                for row in stats_rows:
                    try:
                        label = row.find_element(By.CLASS_NAME, "listing-stats-label")
                        value = row.find_element(By.CLASS_NAME, "listing-stats-value")
                        
                        if 'bids' in label.text.lower():
                            bids_text = value.text.strip()
                            bids_match = re.search(r'(\d+)', bids_text)
                            if bids_match:
                                detail_data['number_of_bids'] = int(bids_match.group(1))
                    except:
                        continue
                        
            except:
                pass
            
            try:
                comment_stream = self.driver.find_element(By.CLASS_NAME, "comment-stream")
                comments = comment_stream.find_elements(By.CLASS_NAME, "comment")
                
                for comment in comments:
                    try:
                        if 'bypostauthor' in comment.get_attribute('class'):
                            comment_text = comment.text
                            
                            if 'vin' not in detail_data:
                                vin_patterns = [
                                    r'chassis[:\s]+([A-HJ-NPR-Z0-9]{17})',
                                    r'vin[:\s]+([A-HJ-NPR-Z0-9]{17})',
                                    r'\b([A-HJ-NPR-Z0-9]{17})\b'
                                ]
                                for pattern in vin_patterns:
                                    vin_match = re.search(pattern, comment_text, re.I)
                                    if vin_match:
                                        detail_data['vin'] = vin_match.group(1)
                                        break
                            
                            if 'mileage' not in detail_data:
                                mileage_patterns = [
                                    r'(\d{1,3}(?:,\d{3})*)\s*miles',
                                    r'odometer\s*(?:shows|reads)?\s*(\d{1,3}(?:,\d{3})*)'
                                ]
                                for pattern in mileage_patterns:
                                    match = re.search(pattern, comment_text, re.I)
                                    if match:
                                        detail_data['mileage'] = int(match.group(1).replace(',', ''))
                                        break
                    except:
                        continue
                        
            except:
                pass
            
            return detail_data
            
        except Exception as e:
            print(f"    Error scraping detail page: {e}")
            return {}
    
    def extract_variant_from_title(self, title, model):
        """
        extract variant from title. 
        ex: "294-Mile 2008 Mercedes-Benz SLR McLaren Roadster" -> "Roadster"
        returns "Standard" if no variant found.
        """
        try:
            title_lower = title.lower()
            
            model_parts = model.lower().replace('-', ' ').split()
            
            last_model_word = model_parts[-1] if model_parts else model.lower()
            
            last_word_index = title_lower.rfind(last_model_word)
            
            if last_word_index == -1:
                return "Standard"
            
            after_model_start = last_word_index + len(last_model_word)
            after_model = title[after_model_start:].strip()
            
            if not after_model:
                return "Standard"
            
            variant_words = after_model.split()
            if not variant_words:
                return "Standard"
            
            variant = variant_words[0]
            
            common_words = ['for', 'with', 'in', 'at', 'by', 'from', 'on', 'and', 'the']
            if variant.lower() in common_words or len(variant) < 2:
                return "Standard"
            
            return variant
            
        except:
            return "Standard"

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
        skipped = 0
        
        for i, listing in enumerate(listings, 1):
            listing_data = self.parse_listing_data(listing)
            
            if 'year' in listing_data:
                year = listing_data.pop('year')
                listing_data['year'] = year
                listing_data['make'] = self.make
                listing_data['model'] = self.model
            
            variant = self.extract_variant_from_title(listing_data['title'], self.model)
            listing_data['variant'] = variant
            
            if scrape_details:
                if i % 10 == 0 or i == 1:
                    print(f"  Scraping details: {i}/{self.max_listings}")
                
                detail_data = self.scrape_listing_detail(listing['url'])
                
                ordered_data = {
                    'url': listing_data.get('url'),
                    'source': listing_data.get('source'),
                    'title': listing_data.get('title'),
                    'vin': detail_data.get('vin'),
                    'year': listing_data.get('year'),
                    'make': listing_data.get('make'),
                    'model': listing_data.get('model'),
                    'variant': listing_data.get('variant'),
                    'mileage': detail_data.get('mileage') or listing_data.get('mileage'),
                    'price': listing_data.get('price'),
                    'sale_date': listing_data.get('sale_date'),
                    'number_of_bids': detail_data.get('number_of_bids'),
                    'location': detail_data.get('location')
                }
                
                ordered_data = {k: v for k, v in ordered_data.items() if v is not None}
                
                if 'vin' not in ordered_data or not ordered_data['vin']:
                    skipped += 1
                    print(f"    Skipped (no VIN): {listing_data['title'][:50]}...")
                    self.driver.back()
                    time.sleep(1)
                    continue
                
                self.driver.back()
                time.sleep(1)
                
                parsed.append(ordered_data)
            else:
                parsed.append(listing_data)
            if len(parsed) == self.max_listings:
                break
        
        if scrape_details:
            print(f"  Completed detail scraping for {len(listings)} listings")
            print(f"  Skipped {skipped} listings without VIN (parts/memorabilia)")
            print(f"  Kept {len(parsed)} car listings")
        
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

        return listings
    
    def parse_listing_data(self, listing):
        """
        parse listing card overview, including url if scraping more detail
        """
        soup = BeautifulSoup(listing['card_html'], 'html.parser')
        data = {
            'url': listing['url'], 
            'source': 'bringatrailer',
            'title': listing['title']
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
                    data['sale_date'] = datetime.strptime(date_match.group(1), '%m/%d/%y').strftime('%Y-%m-%d')
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
        """
        main scraping method - returns list of Listing objects
        """
        try:
            url = self.base_url + str.format("{0}/{1}/", self.make, self.model)
            parsed = self.get_model_page(url, max_clicks=self.max_clicks, scrape_details=True)
            return parsed
        finally:
            print("\nClosing browser")
            self.driver.quit()