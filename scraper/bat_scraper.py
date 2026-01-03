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

class BATSeleniumScraper:
    def __init__(self, slugs, make, model_full, model_short, min_year=None, max_year=None, max_listings=4, headless=False):
        self.base_url = "https://bringatrailer.com/"
        self.slugs = slugs if isinstance(slugs, list) else [slugs]
        self.make = make
        self.model_full = model_full
        self.model_short = model_short
        self.min_year = min_year
        self.max_year = max_year
        self.max_listings = max_listings
        self.max_clicks = 1
        
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

    def scrape_listing_detail(self, url, sale_price=None):
        try:
            self.driver.get(url)
            time.sleep(2)
            
            detail_data = {}
            
            try:
                country_elem = self.driver.find_element(By.CLASS_NAME, "show-country-name")
                country = country_elem.text.strip()
                detail_data['country'] = country
            except:
                detail_data['country'] = None
            
            try:
                essentials = self.driver.find_element(By.CLASS_NAME, "essentials")
                
                # Get all strong tags directly in essentials (not just in items)
                all_strongs = essentials.find_elements(By.TAG_NAME, "strong")
                for strong in all_strongs:
                    try:
                        label = strong.text.strip()
                        
                        if label == "Location":
                            # Location link comes right after the strong tag
                            parent = strong.find_element(By.XPATH, "..")
                            links = parent.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                if 'google.com/maps' in link.get_attribute('href'):
                                    detail_data['location'] = link.text.strip()
                                    break
                        
                        elif label == "Seller":
                            # Seller link comes right after the strong tag
                            parent = strong.find_element(By.XPATH, "..")
                            links = parent.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute('href')
                                if href and 'bringatrailer.com/member/' in href:
                                    detail_data['seller'] = link.text.strip()
                                    break
                        
                        elif label == "Private Party or Dealer":
                            # The value comes after ": " in the parent element's text
                            parent = strong.find_element(By.XPATH, "..")
                            parent_text = parent.text.strip()
                            # Format is "Private Party or Dealer: Private Party"
                            if ':' in parent_text:
                                value = parent_text.split(':', 1)[1].strip()
                                if value in ['Private Party', 'Dealer']:
                                    detail_data['seller_type'] = value
                        
                        elif label == "Lot":
                            # Lot number comes after the strong tag
                            parent = strong.find_element(By.XPATH, "..")
                            parent_text = parent.text.strip()
                            lot_match = re.search(r'#?(\d+)', parent_text)
                            if lot_match:
                                detail_data['lot_number'] = lot_match.group(1)
                        
                        elif label == "Listing Details":
                            # Get the parent element which contains the ul
                            parent = strong.find_element(By.XPATH, "..")
                            ul = parent.find_element(By.TAG_NAME, "ul")
                            li_elements = ul.find_elements(By.TAG_NAME, "li")
                            
                            # Capture all listing details as an array
                            listing_details = []
                            for li in li_elements:
                                text = li.text.strip()
                                if text:
                                    listing_details.append(text)
                            
                            detail_data['listing_details'] = listing_details
                            
                            # Process listing details to extract specific fields
                            found_exterior_color = False
                            for idx, li in enumerate(li_elements):
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
                                
                                elif 'speed' in text.lower() and 'transmission' not in detail_data:
                                    # Normalize various hyphen types to standard hyphen
                                    normalized_text = text.replace('‑', '-').replace('–', '-').replace('—', '-')
                                    transmission_match = re.search(
                                        r'[\w\s-]*\b(\w+)-Speed[\w\s-]*',
                                        normalized_text,
                                        re.I
                                    )
                                    if transmission_match:
                                        detail_data['transmission'] = transmission_match.group(0).strip()
                                
                                elif 'paint' in text.lower() and 'exterior_color' not in detail_data:
                                    # Extract full exterior color text ending with "Paint"
                                    paint_match = re.search(r'(.+?Paint)', text, re.I)
                                    if paint_match:
                                        detail_data['exterior_color'] = paint_match.group(1).strip()
                                        found_exterior_color = True
                                        # The next item should be interior color
                                        if idx + 1 < len(li_elements):
                                            next_text = li_elements[idx + 1].text.strip()
                                            if next_text:
                                                detail_data['interior_color'] = next_text
                                
                                elif ('liter' in text.lower() or 'L' in text) and 'engine' not in detail_data:
                                    # Normalize hyphens
                                    normalized_text = text.replace('‑', '-').replace('–', '-').replace('—', '-')
                                    engine_match = re.search(
                                        r'[\w\s-]*\b(\d+\.?\d*)[- ]?(?:Liter|L)\b[\w\s-]*',
                                        normalized_text,
                                        re.I
                                    )
                                    if engine_match:
                                        detail_data['engine'] = engine_match.group(0).strip()
                    except:
                        continue
                        
            except:
                pass
            
            if 'transmission' not in detail_data:
                detail_data['transmission'] = 'N/A'
            
            if 'engine' not in detail_data:
                detail_data['engine'] = 'N/A'
            
            if 'exterior_color' not in detail_data:
                detail_data['exterior_color'] = 'N/A'
            
            if 'interior_color' not in detail_data:
                detail_data['interior_color'] = 'N/A'
            
            if 'seller' not in detail_data:
                detail_data['seller'] = 'N/A'
            
            if 'seller_type' not in detail_data:
                detail_data['seller_type'] = 'N/A'
            
            if 'lot_number' not in detail_data:
                detail_data['lot_number'] = 'N/A'
            
            if 'high_bidder' not in detail_data:
                detail_data['high_bidder'] = 'N/A'
            
            if 'location' not in detail_data:
                detail_data['location'] = 'N/A'
            
            if 'vin' not in detail_data:
                detail_data['vin'] = 'N/A'
            
            if 'mileage' not in detail_data:
                detail_data['mileage'] = None
            
            if 'number_of_bids' not in detail_data:
                detail_data['number_of_bids'] = None
            
            if 'listing_details' not in detail_data:
                detail_data['listing_details'] = []
            
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
                # Try to find high bidder, clicking "Show More" only if needed
                max_clicks = 10  # Limit to prevent infinite loops
                clicks = 0
                
                while clicks < max_clicks:
                    # Check for bid-notification-link elements
                    bid_links = self.driver.find_elements(By.CLASS_NAME, "bid-notification-link")
                    
                    if bid_links and sale_price:
                        # Found bid links, now find the one that matches the sale price
                        for bid_link in reversed(bid_links):  # Start from the end (most recent)
                            try:
                                # Get the parent comment-text div to find the bid amount
                                comment_text_elem = bid_link.find_element(By.XPATH, "../..")
                                comment_text = comment_text_elem.text.strip()
                                
                                # Extract bid amount from text like "USD $1,921,000 bid placed by"
                                bid_match = re.search(r'USD\s+\$([0-9,]+)', comment_text, re.I)
                                if bid_match:
                                    # Remove commas and convert to int
                                    bid_amount_str = bid_match.group(1).replace(',', '')
                                    bid_amount = int(bid_amount_str)
                                    
                                    # Check if this bid matches the sale price
                                    if bid_amount == sale_price:
                                        high_bidder = bid_link.text.strip()
                                        if high_bidder:
                                            detail_data['high_bidder'] = high_bidder
                                            break  # Found the matching high bidder
                            except:
                                continue
                        
                        # If we found a matching high bidder, break out of the while loop
                        if 'high_bidder' in detail_data:
                            break
                    elif bid_links and not sale_price:
                        # No sale price to match (reserve not met), just get the last bidder
                        last_bid_link = bid_links[-1]
                        high_bidder = last_bid_link.text.strip()
                        if high_bidder:
                            detail_data['high_bidder'] = high_bidder
                            break
                    
                    # No matching bid found, try to click "Show More" to load more comments
                    try:
                        show_more_button = self.driver.find_element(By.ID, "comments-load-button")
                        
                        # Check if the button is visible and enabled
                        if show_more_button.is_displayed() and show_more_button.is_enabled():
                            # Scroll to button
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", show_more_button)
                            time.sleep(0.5)
                            
                            # Click it
                            show_more_button.click()
                            clicks += 1
                            
                            # Wait for comments to load
                            time.sleep(2)
                        else:
                            # Button not visible/enabled, all comments loaded but no matching bid found
                            break
                    except:
                        # Button not found, all comments loaded but no matching bid found
                        break
                
                # Fallback: if still no high_bidder, try regex extraction
                if 'high_bidder' not in detail_data:
                    try:
                        comment_stream = self.driver.find_element(By.ID, "comments")
                        all_text = comment_stream.text
                        # Look for the last occurrence of "bid placed by"
                        matches = re.findall(r'bid\s+placed\s+by\s+(\w+)', all_text, re.I)
                        if matches:
                            detail_data['high_bidder'] = matches[-1]
                    except:
                        pass
                        
            except:
                pass
            
            try:
                comment_stream = self.driver.find_element(By.ID, "comments")
                all_comments = comment_stream.find_elements(By.CLASS_NAME, "comment")
                
                for comment in all_comments:
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
    
    def extract_variant_from_title(self, title):
        """
        Extract variant from title using model_short.
        Pattern: {make} {model_short}{variant}
        
        Handles cases like:
        - "2005 Mitsubishi Lancer Evolution VIII MR" -> variant = "MR"
        - "2002 Mercedes-Benz CLK55 AMG Coupe" -> variant = "55 AMG Coupe"
        - "1995 Toyota Supra Turbo 6-Speed" -> variant = "Turbo" (ignores transmission)
        
        Returns "Standard" if no variant found.
        """
        try:
            title_upper = title.upper()
            make_upper = self.make.upper()
            model_short_upper = self.model_short.upper()
            
            make_index = title_upper.find(make_upper)
            if make_index == -1:
                return "Standard"
            
            after_make = title[make_index + len(self.make):].strip()
            model_index = after_make.upper().find(model_short_upper)
            
            if model_index == -1:
                return "Standard"
            
            after_model = after_make[model_index + len(self.model_short):].strip()
            
            if not after_model:
                return "Standard"
            
            transmission_match = re.search(r'\d+-Speed', after_model, re.I)
            if transmission_match:
                variant_end = transmission_match.start()
                variant = after_model[:variant_end].strip()
            else:
                variant = after_model.strip()
            
            if not variant:
                return "Standard"
            
            variant_parts = variant.split()
            if variant_parts:
                first_word = variant_parts[0]
                common_words = ['for', 'with', 'in', 'at', 'by', 'from', 'on', 'and', 'the']
                if first_word.lower() in common_words:
                    return "Standard"
            
            return variant
            
        except Exception as e:
            print(f"    Error extracting variant: {e}")
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
        
        # Track missing fields
        missing_fields = {
            'vin': 0,
            'lot_number': 0,
            'seller': 0,
            'seller_type': 0,
            'high_bidder': 0,
            'engine': 0,
            'transmission': 0,
            'exterior_color': 0,
            'interior_color': 0,
            'mileage': 0,
            'location': 0,
            'number_of_bids': 0,
            'listing_details': 0
        }
        
        for i, listing in enumerate(listings, 1):
            listing_data = self.parse_listing_data(listing)
            
            # Skip modified cars
            if 'modified' in listing_data['title'].lower():
                skipped += 1
                continue
            
            if self.min_year and listing_data.get('year'):
                if listing_data['year'] < self.min_year:
                    skipped += 1
                    continue
            
            if self.max_year and listing_data.get('year'):
                if listing_data['year'] > self.max_year:
                    skipped += 1
                    continue
            
            if 'year' in listing_data:
                year = listing_data.pop('year')
                listing_data['year'] = year
                listing_data['make'] = self.make
                listing_data['model'] = self.model_full
            
            variant = self.extract_variant_from_title(listing_data['title'])
            listing_data['variant'] = variant
            
            if scrape_details:
                if i % 10 == 0 or i == 1:
                    print(f"  Scraping details: {i}/{self.max_listings}")
                
                detail_data = self.scrape_listing_detail(listing['url'], sale_price=listing_data.get('price'))
                
                # Skip non-USA listings
                if detail_data.get('country') and detail_data['country'] != 'USA':
                    skipped += 1
                    print(f"    Skipped (non-USA): {listing_data['title'][:50]}... ({detail_data['country']})")
                    self.driver.back()
                    time.sleep(1)
                    continue
                
                # Determine result (sold vs reserve not met)
                result = 'Sold' if listing_data.get('price') else 'Reserve Not Met'
                
                ordered_data = {
                    'url': listing_data.get('url') or 'N/A',
                    'source': listing_data.get('source') or 'N/A',
                    'lot_number': detail_data.get('lot_number') or 'N/A',
                    'seller': detail_data.get('seller') or 'N/A',
                    'seller_type': detail_data.get('seller_type') or 'N/A',
                    'result': result,
                    'high_bidder': detail_data.get('high_bidder') or 'N/A',
                    'price': listing_data.get('price'),
                    'sale_date': listing_data.get('sale_date') or 'N/A',
                    'number_of_bids': detail_data.get('number_of_bids'),
                    'title': listing_data.get('title') or 'N/A',
                    'vin': detail_data.get('vin') or 'N/A',
                    'year': listing_data.get('year'),
                    'make': listing_data.get('make') or 'N/A',
                    'model': listing_data.get('model') or 'N/A',
                    'variant': listing_data.get('variant') or 'N/A',
                    'engine': detail_data.get('engine') or 'N/A',
                    'transmission': detail_data.get('transmission') or 'N/A',
                    'exterior_color': detail_data.get('exterior_color') or 'N/A',
                    'interior_color': detail_data.get('interior_color') or 'N/A',
                    'mileage': detail_data.get('mileage') or listing_data.get('mileage'),
                    'location': detail_data.get('location') or 'N/A',
                    'listing_details': detail_data.get('listing_details') or []
                }
                
                # Track missing fields (N/A or None values)
                for field in missing_fields.keys():
                    if field in ordered_data:
                        value = ordered_data[field]
                        if value == 'N/A' or value is None or (isinstance(value, list) and len(value) == 0):
                            missing_fields[field] += 1
                
                if 'vin' not in ordered_data or ordered_data['vin'] == 'N/A' or not ordered_data['vin']:
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
            if (len(parsed) == self.max_listings):
                return parsed
        if scrape_details:
            print(f"  Completed detail scraping for {len(listings)} listings")
            print(f"  Skipped {skipped} listings (no VIN, non-USA, modified, or outside year range)")
            print(f"  Kept {len(parsed)} car listings")
            
            # Print missing fields summary
            if len(parsed) > 0:
                print(f"\n{'='*70}")
                print("MISSING FIELDS SUMMARY")
                print(f"{'='*70}")
                print(f"Total listings scraped: {len(parsed)}")
                print()
                
                # Sort by number of missing (highest first)
                sorted_missing = sorted(missing_fields.items(), key=lambda x: x[1], reverse=True)
                
                for field, count in sorted_missing:
                    if count > 0:
                        percentage = (count / len(parsed)) * 100
                        print(f"  {field:20} : {count:3} missing ({percentage:5.1f}%)")
                
                # Show which fields are complete
                complete_fields = [field for field, count in sorted_missing if count == 0]
                if complete_fields:
                    print(f"\n  Complete fields (100%): {', '.join(complete_fields)}")
                
                print(f"{'='*70}\n")
        
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
    
    def scrape_all_slugs(self):
        """
        Scrape listings from all slugs and combine them
        """
        all_listings = []
        
        for i, slug in enumerate(self.slugs, 1):
            print(f"\n{'='*70}")
            print(f"Scraping slug {i}/{len(self.slugs)}: {slug}")
            print(f"{'='*70}\n")
            
            url = self.base_url + slug + "/"
            listings = self.get_model_page(url, max_clicks=self.max_clicks, scrape_details=True)
            all_listings.extend(listings)
        
        seen_urls = set()
        unique_listings = []
        for listing in all_listings:
            if listing['url'] not in seen_urls:
                seen_urls.add(listing['url'])
                unique_listings.append(listing)
        
        print(f"\n{'='*70}")
        print(f"Combined {len(all_listings)} listings from {len(self.slugs)} slug(s)")
        print(f"Removed {len(all_listings) - len(unique_listings)} duplicates")
        print(f"Final count: {len(unique_listings)} unique listings")
        print(f"{'='*70}\n")
        
        return unique_listings
    
    def close(self):
        print("\nClosing browser")
        self.driver.quit()