from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime
import json
import os

# robots.txt compliance: https://bringatrailer.com/robots.txt
# crawl-delay: 1 second minimum (enforced via MimicDelayPattern)
# allowed: listing pages, auction data
# disallowed: /wp-admin/, /message/, /member/, /account/, /search/

import bisect

class MimicDelayPattern:
    def __init__(self, min_delay=1.0):
        self.last_action_time = time.time()
        self.action_count = 0
        self.min_delay = min_delay
    
    def get_delay(self):
        self.action_count += 1
        base_delay = random.uniform(1.5, 3.0)
        
        if self.action_count % random.randint(10, 15) == 0:
            print(f"  [taking a break...]")
            return random.uniform(8, 15)
        
        fatigue_factor = 1 + (self.action_count * 0.005)
        
        if random.random() < 0.15:
            delay = random.uniform(0.5, 1.0)
        else:
            delay = base_delay * fatigue_factor
        
        return max(delay, self.min_delay)

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    return random.choice(user_agents)

def get_random_viewport():
    viewports = [
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (1680, 1050),
        (1600, 900),
    ]
    return random.choice(viewports)

def human_click(driver, element):
    try:
        actions = ActionChains(driver)
        size = element.size
        offset_x = random.randint(-size['width']//4, size['width']//4)
        offset_y = random.randint(-size['height']//4, size['height']//4)
        actions.move_to_element_with_offset(element, offset_x, offset_y)
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()
    except:
        element.click()

def human_scroll(driver, target_position=None):
    current_position = driver.execute_script("return window.pageYOffset;")
    
    if target_position is None:
        viewport_height = driver.execute_script("return window.innerHeight;")
        scroll_amount = random.randint(int(viewport_height * 0.4), int(viewport_height * 0.9))
        target_position = current_position + scroll_amount
    
    distance = target_position - current_position
    steps = random.randint(8, 15)
    
    for i in range(steps):
        progress = (i + 1) / steps
        ease = progress * progress * (3.0 - 2.0 * progress)
        scroll_to = int(current_position + (distance * ease))
        driver.execute_script(f"window.scrollTo(0, {scroll_to});")
        time.sleep(random.uniform(0.02, 0.05))
    
    if random.random() < 0.15:
        back_scroll = random.randint(50, 150)
        current = driver.execute_script("return window.pageYOffset;")
        driver.execute_script(f"window.scrollTo(0, {current - back_scroll});")
        time.sleep(random.uniform(0.3, 0.7))
        driver.execute_script(f"window.scrollTo(0, {current});")
        time.sleep(random.uniform(0.2, 0.4))

def scroll_to_bottom_naturally(driver):
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight;")
    current_position = driver.execute_script("return window.pageYOffset;")
    
    while current_position < total_height - viewport_height:
        scroll_amount = random.randint(300, 800)
        target = min(current_position + scroll_amount, total_height)
        
        human_scroll(driver, target)
        
        if random.random() < 0.2:
            time.sleep(random.uniform(1.5, 3.0))
        else:
            time.sleep(random.uniform(0.3, 0.8))
        
        current_position = driver.execute_script("return window.pageYOffset;")
        total_height = driver.execute_script("return document.body.scrollHeight")

class BATSeleniumScraper:
    def __init__(self, slugs, make, model_full, model_short, min_year=None, max_year=None, max_listings=1024, headless=False, fields=None, sort_oldest=False, append_file=None):
        self.base_url = "https://bringatrailer.com/"
        self.slugs = slugs if isinstance(slugs, list) else [slugs]
        self.make = make
        self.model_full = model_full
        self.model_short = model_short
        self.min_year = min_year
        self.max_year = max_year
        self.max_listings = max_listings
        self.max_clicks = 48
        self.fields = fields
        self.sort_oldest = sort_oldest
        self.append_file = append_file
        self.existing_lot_numbers = set()
        
        if self.append_file:
            try:
                with open(self.append_file, 'r') as f:
                    existing_data = json.load(f)
                    for listing in existing_data:
                        if 'lot_number' in listing and listing['lot_number'] != 'N/A':
                            self.existing_lot_numbers.add(listing['lot_number'])
                print(f"loaded {len(self.existing_lot_numbers)} existing lot numbers from {self.append_file}")
            except Exception as e:
                print(f"could not load append file: {e}")
                self.existing_lot_numbers = set()
        
        self.delay_pattern = MimicDelayPattern()
        
        chrome_options = Options()
        
        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        
        user_agent = get_random_user_agent()
        chrome_options.add_argument(f'user-agent={user_agent}')
        print(f"using user agent: {user_agent[:50]}...")
        
        width, height = get_random_viewport()
        chrome_options.add_argument(f'--window-size={width},{height}')
        print(f"viewport size: {width}x{height}")
        
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-notifications')
        
        print("starting browser...")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("browser started\n")
    
    def click_show_more(self, max_clicks):
        clicks = 0
        consecutive_failures = 0
        
        while clicks < max_clicks:
            try:
                total_height = self.driver.execute_script("return document.body.scrollHeight")
                offset = random.randint(-50, 0)
                self.driver.execute_script(f"window.scrollTo(0, {total_height + offset});")
                
                delay = self.delay_pattern.get_delay()
                time.sleep(delay)
                
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
                    print(f"\nall listings loaded: {result['reason']}")
                    break
                
                if 'error' in result:
                    print(f"\nerror: {result['error']}")
                    consecutive_failures += 1
                    if consecutive_failures >= 2:
                        break
                    continue
                
                if 'success' in result:
                    clicks += 1
                    wait_time = random.uniform(3, 5) + self.delay_pattern.get_delay() * 0.5
                    time.sleep(wait_time)
                    
                    for wait_attempt in range(15):
                        listings_after = len(self.driver.find_elements(By.CLASS_NAME, "listing-card"))
                        
                        if listings_after > listings_before:
                            new_count = listings_after - listings_before
                            print(f"  click {clicks}: +{new_count} listings (total: {listings_after})")
                            consecutive_failures = 0
                            time.sleep(self.delay_pattern.get_delay())
                            break
                        
                        time.sleep(random.uniform(1, 2))
                    else:
                        print(f"  click {clicks}: no new listings loaded")
                        consecutive_failures += 1
                        if consecutive_failures >= 2:
                            break
                
            except Exception as e:
                print(f"exception: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 2:
                    break
        
        final_count = len(self.driver.find_elements(By.CLASS_NAME, "listing-card"))
        print(f"\n{'='*70}")
        print(f"loading complete: {final_count} listings found")
        print(f"{'='*70}\n")
        return clicks

    def scrape_listing_detail(self, url, sale_price=None):
        try:
            self.driver.get(url)
            page_load_delay = random.uniform(2, 3.5) + self.delay_pattern.get_delay() * 0.3
            time.sleep(page_load_delay)
            
            if random.random() < 0.7:
                viewport_height = self.driver.execute_script("return window.innerHeight;")
                scroll_distance = random.randint(int(viewport_height * 0.3), int(viewport_height * 0.7))
                human_scroll(self.driver, scroll_distance)
                time.sleep(random.uniform(0.5, 1.2))
            
            detail_data = {}
            
            try:
                country_elem = self.driver.find_element(By.CLASS_NAME, "show-country-name")
                country = country_elem.text.strip()
                detail_data['country'] = country
            except:
                detail_data['country'] = None
            
            try:
                category_buttons = self.driver.find_elements(By.CLASS_NAME, "group-title")
                is_convertible = False
                
                for button in category_buttons:
                    button_text = button.text.strip()
                    if 'Convertibles' in button_text or 'Convertible' in button_text:
                        is_convertible = True
                        break
                
                detail_data['convertible'] = is_convertible
            except:
                detail_data['convertible'] = False
            
            try:
                essentials = self.driver.find_element(By.CLASS_NAME, "essentials")
                
                all_strongs = essentials.find_elements(By.TAG_NAME, "strong")
                for strong in all_strongs:
                    try:
                        label = strong.text.strip()
                        
                        if label == "Location":
                            parent = strong.find_element(By.XPATH, "..")
                            links = parent.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                if 'google.com/maps' in link.get_attribute('href'):
                                    detail_data['location'] = link.text.strip()
                                    break
                        
                        elif label == "Seller":
                            parent = strong.find_element(By.XPATH, "..")
                            links = parent.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute('href')
                                if href and 'bringatrailer.com/member/' in href:
                                    detail_data['seller'] = link.text.strip()
                                    break
                        
                        elif label == "Private Party or Dealer":
                            parent = strong.find_element(By.XPATH, "..")
                            parent_text = parent.text.strip()
                            if ':' in parent_text:
                                value = parent_text.split(':', 1)[1].strip()
                                if value in ['Private Party', 'Dealer']:
                                    detail_data['seller_type'] = value
                        
                        elif label == "Lot":
                            parent = strong.find_element(By.XPATH, "..")
                            parent_text = parent.text.strip()
                            lot_match = re.search(r'#?(\d+)', parent_text)
                            if lot_match:
                                detail_data['lot_number'] = lot_match.group(1)
                        
                        elif label == "Listing Details":
                            parent = strong.find_element(By.XPATH, "..")
                            ul = parent.find_element(By.TAG_NAME, "ul")
                            li_elements = ul.find_elements(By.TAG_NAME, "li")
                            
                            listing_details = []
                            for li in li_elements:
                                text = li.text.strip()
                                if text:
                                    listing_details.append(text)
                            
                            detail_data['listing_details'] = listing_details
                            
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
                                    normalized_text = text.replace('‑', '-').replace('–', '-').replace('—', '-')
                                    transmission_match = re.search(
                                        r'[\w\s-]*\b(\w+)-Speed[\w\s-]*',
                                        normalized_text,
                                        re.I
                                    )
                                    if transmission_match:
                                        detail_data['transmission'] = transmission_match.group(0).strip()
                                
                                elif 'paint' in text.lower() and 'exterior_color' not in detail_data:
                                    paint_match = re.search(r'(.+?Paint)', text, re.I)
                                    if paint_match:
                                        detail_data['exterior_color'] = paint_match.group(1).strip()
                                        found_exterior_color = True
                                        if idx + 1 < len(li_elements):
                                            next_text = li_elements[idx + 1].text.strip()
                                            if next_text:
                                                detail_data['interior_color'] = next_text
                                
                                elif ('liter' in text.lower() or 'L' in text) and 'engine' not in detail_data:
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
            
            if ('exterior_color' not in detail_data or detail_data.get('exterior_color') == 'N/A') and 'listing_details' in detail_data:
                listing_details = detail_data['listing_details']
                
                interior_keywords = [
                    r'leather', r'cloth', r'upholstery', r'nappa', r'alcantara', 
                    r'vinyl', r'suede', r'interior', r'seats?'
                ]
                
                color_keywords = [
                    r'white', r'black', r'red', r'blue', r'silver', r'grey', r'gray',
                    r'green', r'yellow', r'orange', r'brown', r'gold', r'bronze',
                    r'titanium', r'platinum', r'carbon', r'pearl', r'metallic',
                    r'alpine', r'imola', r'laguna', r'mystic', r'estoril', r'phoenix',
                    r'paint', r'refinished', r'repainted'
                ]
                
                skip_keywords = [
                    r'chassis', r'miles', r'turbo', r'liter', r'speed', r'manual', r'automatic',
                    r'differential', r'drive', r'wheel', r'transmission', r'engine', r'brake',
                    r'exhaust', r'suspension', r'stereo', r'air', r'power', r'carfax', r'report',
                    r'block', r'intercooler', r'intake', r'system', r'spoiler', r'wing', r'scoop',
                    r'caliper', r'alloy', r'brembo', r'disc', r'aftermarket', r'replacement', 
                    r'records', r'vanos', r'bearing', r'subframe', r'reinforced', r'upgraded',
                    r'camshaft', r'radiator', r'cooling', r'oil', r'filter', r'service',
                    r'soft top', r'hard top', r'convertible top', r'roof',
                    r'sunroof', r'moonroof', r'package', r'xenon', r'headlight', r'fog',
                    r'navigation', r'bluetooth', r'audio', r'speaker', r'heated'
                ]
                
                found_exterior = None
                found_interior = None
                
                for detail in listing_details:
                    detail_lower = detail.lower()
                    
                    if any(re.search(pattern, detail_lower) for pattern in skip_keywords):
                        continue
                    
                    if not detail.strip() or len(detail.split()) > 8:
                        continue
                    
                    if not found_interior:
                        if any(re.search(pattern, detail_lower) for pattern in interior_keywords):
                            found_interior = detail.strip()
                            continue
                    
                    if not found_exterior:
                        if any(re.search(pattern, detail_lower) for pattern in color_keywords):
                            found_exterior = detail.strip()
                            continue
                    
                    if found_exterior and found_interior:
                        break
                
                if found_exterior:
                    detail_data['exterior_color'] = found_exterior
                if found_interior:
                    detail_data['interior_color'] = found_interior
            
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
                max_clicks = 10
                clicks = 0
                
                while clicks < max_clicks:
                    bid_links = self.driver.find_elements(By.CLASS_NAME, "bid-notification-link")
                    
                    if bid_links and sale_price:
                        for bid_link in reversed(bid_links):
                            try:
                                comment_text_elem = bid_link.find_element(By.XPATH, "../..")
                                comment_text = comment_text_elem.text.strip()
                                
                                bid_match = re.search(r'USD\s+\$([0-9,]+)', comment_text, re.I)
                                if bid_match:
                                    bid_amount_str = bid_match.group(1).replace(',', '')
                                    bid_amount = int(bid_amount_str)
                                    
                                    if bid_amount == sale_price:
                                        high_bidder = bid_link.text.strip()
                                        if high_bidder:
                                            detail_data['high_bidder'] = high_bidder
                                            break
                            except:
                                continue
                        
                        if 'high_bidder' in detail_data:
                            break
                    elif bid_links and not sale_price:
                        last_bid_link = bid_links[-1]
                        high_bidder = last_bid_link.text.strip()
                        if high_bidder:
                            detail_data['high_bidder'] = high_bidder
                            break
                    
                    try:
                        show_more_button = self.driver.find_element(By.ID, "comments-load-button")
                        
                        if show_more_button.is_displayed() and show_more_button.is_enabled():
                            button_y = show_more_button.location['y']
                            viewport_height = self.driver.execute_script("return window.innerHeight;")
                            scroll_target = max(0, button_y - viewport_height // 2)
                            
                            human_scroll(self.driver, scroll_target)
                            time.sleep(random.uniform(0.3, 0.7))
                            
                            human_click(self.driver, show_more_button)
                            clicks += 1
                            
                            wait_time = random.uniform(2, 3.5) + self.delay_pattern.get_delay() * 0.2
                            time.sleep(wait_time)
                        else:
                            break
                    except:
                        break
                
                if 'high_bidder' not in detail_data:
                    try:
                        comment_stream = self.driver.find_element(By.ID, "comments")
                        all_text = comment_stream.text
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
            
            try:
                post_excerpt = self.driver.find_element(By.CLASS_NAME, "post-excerpt")
                paragraphs = post_excerpt.find_elements(By.TAG_NAME, "p")
                
                excerpt_paragraphs = []
                for p in paragraphs:
                    text = p.text.strip()
                    if text:
                        excerpt_paragraphs.append(text)
                
                detail_data['excerpt'] = excerpt_paragraphs
            except:
                detail_data['excerpt'] = []
            
            return detail_data
            
        except Exception as e:
            print(f"    error scraping detail page: {e}")
            return {}
    
    def extract_variant_from_title(self, title):
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
            print(f"    error extracting variant: {e}")
            return "Standard"
    
    def filter_fields(self, data):
        if self.fields is None:
            return data
        
        filtered_data = {}
        for field in self.fields:
            if field in data:
                filtered_data[field] = data[field]
        
        return filtered_data

    def get_model_page(self, url, max_clicks, scrape_details=True):
        print(f"loading: {url}\n")
        
        if self.fields:
            print(f"field filtering enabled: {len(self.fields)} field(s) will be included")
            print(f"fields: {', '.join(self.fields)}\n")
        
        self.driver.get(url)
        
        try:
            initial_load_delay = random.uniform(2, 3.5) + self.delay_pattern.get_delay() * 0.3
            time.sleep(initial_load_delay)
            from selenium.webdriver.common.keys import Keys
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        except:
            pass
        
        if self.sort_oldest:
            try:
                print("sorting by oldest...")
                sort_dropdown = self.driver.find_element(By.CSS_SELECTOR, ".toolbar-dropdown.sort-dropdown")
                dropdown_title = sort_dropdown.find_element(By.CLASS_NAME, "dropdown-title")
                human_click(self.driver, dropdown_title)
                time.sleep(random.uniform(0.5, 1.0))
                
                dropdown_options = sort_dropdown.find_elements(By.CLASS_NAME, "dropdown-option")
                for option in dropdown_options:
                    if "Oldest" in option.text:
                        human_click(self.driver, option)
                        time.sleep(random.uniform(1.0, 2.0))
                        print("sorted by oldest")
                        break
            except Exception as e:
                print(f"could not sort by oldest: {e}")
        
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "listing-card"))
            )
            initial = len(self.driver.find_elements(By.CLASS_NAME, "listing-card"))
            print(f"initial page loaded: {initial} listings\n")
        except Exception as e:
            print(f"timeout waiting for listings: {e}\n")

        print("loading all listings...")
        print("="*70)
        self.click_show_more(max_clicks=max_clicks)
        
        time.sleep(self.delay_pattern.get_delay())
        html = self.driver.page_source
        
        print("\nparsing listing cards...")
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
                    print(f"  scraping details: {i}/{self.max_listings}")
                
                detail_data = self.scrape_listing_detail(listing['url'], sale_price=listing_data.get('price'))
                
                if self.append_file and detail_data.get('lot_number') and detail_data['lot_number'] != 'N/A':
                    if detail_data['lot_number'] in self.existing_lot_numbers:
                        print(f"\n  found duplicate lot #{detail_data['lot_number']}, stopping scrape")
                        print(f"  scraped {len(parsed)} new listings before duplicate")
                        self.driver.back()
                        return parsed
                
                if detail_data.get('country') and detail_data['country'] != 'USA':
                    skipped += 1
                    print(f"    skipped (non-USA): {listing_data['title'][:50]}... ({detail_data['country']})")
                    self.driver.back()
                    time.sleep(self.delay_pattern.get_delay())
                    continue
                
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
                    'convertible': detail_data.get('convertible', False),
                    'engine': detail_data.get('engine') or 'N/A',
                    'transmission': detail_data.get('transmission') or 'N/A',
                    'exterior_color': detail_data.get('exterior_color') or 'N/A',
                    'interior_color': detail_data.get('interior_color') or 'N/A',
                    'mileage': detail_data.get('mileage') or listing_data.get('mileage'),
                    'location': detail_data.get('location') or 'N/A',
                    'listing_details': detail_data.get('listing_details') or [],
                    'excerpt': detail_data.get('excerpt') or []
                }
                
                for field in missing_fields.keys():
                    if field in ordered_data:
                        value = ordered_data[field]
                        if value == 'N/A' or value is None or (isinstance(value, list) and len(value) == 0):
                            missing_fields[field] += 1
                
                if 'vin' not in ordered_data or ordered_data['vin'] == 'N/A' or not ordered_data['vin']:
                    skipped += 1
                    print(f"    skipped (no VIN): {listing_data['title'][:50]}...")
                    self.driver.back()
                    time.sleep(self.delay_pattern.get_delay())
                    continue
                
                self.driver.back()
                time.sleep(self.delay_pattern.get_delay())
                
                filtered_data = self.filter_fields(ordered_data)
                
                parsed.append(filtered_data)
            else:
                parsed.append(listing_data)
            if (len(parsed) == self.max_listings):
                return parsed
        if scrape_details:
            print(f"  completed detail scraping for {len(listings)} listings")
            print(f"  skipped {skipped} listings (no VIN, non-USA, modified, or outside year range)")
            print(f"  kept {len(parsed)} car listings")
            
            if len(parsed) > 0:
                print(f"\n{'='*70}")
                print("MISSING FIELDS SUMMARY")
                print(f"{'='*70}")
                print(f"total listings scraped: {len(parsed)}")
                print()
                
                sorted_missing = sorted(missing_fields.items(), key=lambda x: x[1], reverse=True)
                
                for field, count in sorted_missing:
                    if count > 0:
                        percentage = (count / len(parsed)) * 100
                        print(f"  {field:20} : {count:3} missing ({percentage:5.1f}%)")
                
                complete_fields = [field for field, count in sorted_missing if count == 0]
                if complete_fields:
                    print(f"\n  complete fields (100%): {', '.join(complete_fields)}")
                
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
        all_listings = []
        
        for i, slug in enumerate(self.slugs, 1):
            print(f"\n{'='*70}")
            print(f"scraping slug {i}/{len(self.slugs)}: {slug}")
            print(f"{'='*70}\n")
            
            url = self.base_url + slug + "/"
            listings = self.get_model_page(url, max_clicks=self.max_clicks, scrape_details=True)
            all_listings.extend(listings)
        
        if self.fields is None or 'url' in self.fields:
            seen_urls = set()
            unique_listings = []
            for listing in all_listings:
                if 'url' in listing:
                    if listing['url'] not in seen_urls:
                        seen_urls.add(listing['url'])
                        unique_listings.append(listing)
                else:
                    unique_listings.append(listing)
            
            print(f"\n{'='*70}")
            print(f"combined {len(all_listings)} listings from {len(self.slugs)} slug(s)")
            print(f"removed {len(all_listings) - len(unique_listings)} duplicates")
            print(f"final count: {len(unique_listings)} unique listings")
            print(f"{'='*70}\n")
            
            return unique_listings
        else:
            print(f"\n{'='*70}")
            print(f"combined {len(all_listings)} listings from {len(self.slugs)} slug(s)")
            print(f"note: deduplication skipped (url field not requested)")
            print(f"final count: {len(all_listings)} listings")
            print(f"{'='*70}\n")
            
            return all_listings
    
    def close(self):
        print("\nclosing browser")
        self.driver.quit()