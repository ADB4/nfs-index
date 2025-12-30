"""
Ingest BaT scraped data into the NFS Index database

Usage:
    python ingest_bat_data.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bat_scraper import BATSeleniumScraper
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

def get_db_connection():
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nfs_index')
    
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    return psycopg2.connect(db_url)

def get_or_create_make(conn, make_name):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM makes WHERE name = %s", (make_name,))
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        cur.execute("INSERT INTO makes (name) VALUES (%s) RETURNING id", (make_name,))
        conn.commit()
        return cur.fetchone()[0]

def get_or_create_model(conn, make_id, model_name):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM models WHERE make_id = %s AND name = %s",
            (make_id, model_name)
        )
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        cur.execute(
            "INSERT INTO models (make_id, name) VALUES (%s, %s) RETURNING id",
            (make_id, model_name)
        )
        conn.commit()
        return cur.fetchone()[0]

def get_or_create_trim(conn, model_id, trim_name):
    if not trim_name:
        return None
    
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM trims WHERE model_id = %s AND name = %s",
            (model_id, trim_name)
        )
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        cur.execute(
            "INSERT INTO trims (model_id, name) VALUES (%s, %s) RETURNING id",
            (model_id, trim_name)
        )
        conn.commit()
        return cur.fetchone()[0]

def extract_trim_from_title(title):
    title_lower = title.lower()
    
    if '722' in title:
        return '722 Edition'
    elif 'roadster' in title_lower:
        return 'Roadster'
    elif 'coupe' in title_lower or 'coupé' in title_lower:
        return 'Coupe'
    elif 'stirling moss' in title_lower:
        return 'Stirling Moss'
    
    return 'Coupe'

def ingest_listing(conn, listing, make_id, model_id):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM listings WHERE listing_url = %s", (listing['url'],))
        existing = cur.fetchone()
        
        trim_name = extract_trim_from_title(listing['title'])
        trim_id = get_or_create_trim(conn, model_id, trim_name)
        
        sale_price_cents = listing.get('price') * 100 if 'price' in listing else None
        
        values = {
            'listing_url': listing['url'],
            'source': listing['source'],
            'make_id': make_id,
            'model_id': model_id,
            'year': listing.get('year'),
            'trim_id': trim_id,
            'sale_price': sale_price_cents,
            'sale_date': listing.get('sale_date'),
            'reserve_met': True if sale_price_cents else None,
            'number_of_bids': None,
            'mileage': listing.get('mileage'),
            'location': None,
            'vin': None,
        }
        
        if existing:
            cur.execute("""
                UPDATE listings SET
                    source = %(source)s,
                    make_id = %(make_id)s,
                    model_id = %(model_id)s,
                    year = %(year)s,
                    trim_id = %(trim_id)s,
                    sale_price = %(sale_price)s,
                    sale_date = %(sale_date)s,
                    reserve_met = %(reserve_met)s,
                    mileage = %(mileage)s
                WHERE listing_url = %(listing_url)s
            """, values)
            return 'updated'
        else:
            cur.execute("""
                INSERT INTO listings (
                    listing_url, source, make_id, model_id, year, trim_id,
                    sale_price, sale_date, reserve_met, number_of_bids,
                    mileage, location, vin
                ) VALUES (
                    %(listing_url)s, %(source)s, %(make_id)s, %(model_id)s,
                    %(year)s, %(trim_id)s, %(sale_price)s, %(sale_date)s,
                    %(reserve_met)s, %(number_of_bids)s, %(mileage)s,
                    %(location)s, %(vin)s
                )
            """, values)
            return 'inserted'

def main():
    print("="*70)
    print("NFS Index - BaT Data Ingestion")
    print("="*70)
    print()
    
    print("Step 1: Scraping BringATrailer...")
    print("-"*70)
    scraper = BATSeleniumScraper(headless=False)
    listings = scraper.scrape_slr_mclaren(max_clicks=30)
    
    if not listings:
        print("No listings scraped. Exiting.")
        return
    
    print(f"\nScraped {len(listings)} listings")
    
    print("\n" + "="*70)
    print("Step 2: Connecting to database...")
    print("-"*70)
    
    try:
        conn = get_db_connection()
        print("Connected to database")
    except Exception as e:
        print(f"Could not connect to database: {e}")
        return
    
    print("\n" + "="*70)
    print("Step 3: Setting up make and model...")
    print("-"*70)
    
    make_id = get_or_create_make(conn, "Mercedes-Benz")
    print(f"Mercedes-Benz (ID: {make_id})")
    
    model_id = get_or_create_model(conn, make_id, "SLR McLaren")
    print(f"SLR McLaren (ID: {model_id})")
    
    print("\n" + "="*70)
    print("Step 4: Ingesting listings...")
    print("-"*70)
    
    inserted = 0
    updated = 0
    errors = 0
    
    for i, listing in enumerate(listings, 1):
        try:
            result = ingest_listing(conn, listing, make_id, model_id)
            if result == 'inserted':
                inserted += 1
            elif result == 'updated':
                updated += 1
            
            if i % 10 == 0:
                print(f"  Processed {i}/{len(listings)} listings...")
                conn.commit()
        except Exception as e:
            errors += 1
            print(f"  Error on listing {i}: {e}")
            conn.rollback()
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*70)
    print("INGESTION COMPLETE")
    print("="*70)
    print(f"  Inserted: {inserted} new listings")
    print(f"  Updated: {updated} existing listings")
    print(f"  Errors: {errors}")
    print(f"  Total processed: {inserted + updated}")
    print()
    print("Data is now available in the NFS Index")
    print()

if __name__ == '__main__':
    main()