import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime

class BATScraper:
    def __init__(self):
        self.base_url = "https://bringatrailer.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def search(self, query, max_pages=3):
        listings = []
        
        for page in range(1, max_pages + 1):
            print(f"Scraping page {page}...")
            url = f"{self.base_url}/page/{page}/?q={query.replace(' ', '+')}"
            
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # this will need to be updated based on actual BaT HTML structure
                # inspect the page to find correct selectors
                links = soup.find_all('a', href=re.compile(r'/auctions/'))
                
                for link in links:
                    listing_url = link.get('href')
                    if listing_url and listing_url.startswith('/auctions/'):
                        full_url = f"{self.base_url}{listing_url}"
                        if full_url not in [l['url'] for l in listings]:
                            listings.append({'url': full_url})
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Error on page {page}: {e}")
                break
        
        print(f"Found {len(listings)} listings")
        return listings
    
    def scrape_listing(self, url):
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            data = {'url': url, 'source': 'bringatrailer'}
            
            # these selectors need to be updated for actual BaT structure
            title_elem = soup.find('h1')
            if title_elem:
                data['title'] = title_elem.get_text(strip=True)
                
                year_match = re.search(r'\b(19|20)\d{2}\b', data['title'])
                if year_match:
                    data['year'] = int(year_match.group())
            
            # price 
            price_elem = soup.find(text=re.compile(r'\$\d+,?\d*'))
            if price_elem:
                price_match = re.search(r'\$?([\d,]+)', price_elem)
                if price_match:
                    data['price'] = int(price_match.group(1).replace(',', ''))
            
            # mileage
            mileage_match = soup.find(text=re.compile(r'(\d{1,3}(,\d{3})*)\s*mile', re.I))
            if mileage_match:
                miles = re.search(r'(\d{1,3}(,\d{3})*)', mileage_match)
                if miles:
                    data['mileage'] = int(miles.group(1).replace(',', ''))
            
            return data
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

if __name__ == '__main__':
    scraper = BATScraper()
    
    listings = scraper.search("Mercedes SLR McLaren", max_pages=2)
    
    if listings:
        print(f"\nScraping first listing as example...")
        detail = scraper.scrape_listing(listings[0]['url'])
        if detail:
            print(f"Title: {detail.get('title')}")
            print(f"Year: {detail.get('year')}")
            print(f"Price: ${detail.get('price', 0):,}")
