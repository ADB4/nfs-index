"""
Ingest BaT scraped data into the NFS Index database from JSON file

Usage:
    python3 populate_db.py --make "Mercedes-Benz" --model "SLR McLaren"
    python3 populate_db.py --make "Porsche" --model "911 GT3"
"""

import json
import sys
import os
import argparse

import psycopg2
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

def extract_trim_from_title(title, model_name):
    title_lower = title.lower()
    model_lower = model_name.lower()
    
    if 'slr' in model_lower and 'mclaren' in model_lower:
        if '722' in title:
            return '722 Edition'
        elif 'roadster' in title_lower:
            return 'Roadster'
        elif 'coupe' in title_lower or 'coupé' in title_lower:
            return 'Coupe'
        elif 'stirling moss' in title_lower:
            return 'Stirling Moss'
        return 'Coupe'
    
    elif '911' in model_lower:
        if 'gt3 rs' in title_lower:
            return 'GT3 RS'
        elif 'gt3' in title_lower:
            return 'GT3'
        elif 'gt2 rs' in title_lower:
            return 'GT2 RS'
        elif 'gt2' in title_lower:
            return 'GT2'
        elif 'turbo s' in title_lower:
            return 'Turbo S'
        elif 'turbo' in title_lower:
            return 'Turbo'
        elif 'carrera' in title_lower:
            return 'Carrera'
    
    if 'roadster' in title_lower or 'spider' in title_lower or 'spyder' in title_lower:
        return 'Roadster'
    elif 'coupe' in title_lower or 'coupé' in title_lower:
        return 'Coupe'
    elif 'convertible' in title_lower or 'cabriolet' in title_lower:
        return 'Convertible'
    
    return None

def ingest_listing(conn, listing, make_id, model_id, model_name):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM listings WHERE listing_url = %s", (listing['url'],))
        existing = cur.fetchone()
        
        trim_name = extract_trim_from_title(listing['title'], model_name)
        trim_id = get_or_create_trim(conn, model_id, trim_name)
        
        sale_price_cents = listing.get('price') * 100 if 'price' in listing else None
        
        values = {
            'listing_url': listing['url'],
            'source': listing.get('source', 'bringatrailer'),
            'make_id': make_id,
            'model_id': model_id,
            'year': listing.get('year'),
            'trim_id': trim_id,
            'sale_price': sale_price_cents,
            'sale_date': listing.get('sale_date'),
            'reserve_met': True if sale_price_cents else None,
            'number_of_bids': listing.get('number_of_bids'),
            'mileage': listing.get('mileage'),
            'location': listing.get('location'),
            'vin': listing.get('vin'),
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
                    number_of_bids = %(number_of_bids)s,
                    mileage = %(mileage)s,
                    location = %(location)s,
                    vin = %(vin)s
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

def load_json(model):
    """
    Gets data from JSON, an array of Listing objects:
    {
        url: string
        title: string
        source: string
        vin: string
        year: integer
        mileage: integer
        price: integer
        number_of_bids: integer
        location: string
        sale_date: string (YYYY-MM-DD)
    }
    """
    model_slug = model.lower().replace(' ', '-')
    json_path = f"data/json/{model_slug}_data.json"
    
    if not os.path.exists(json_path):
        return None
    
    with open(json_path) as f:
        data = json.load(f)
    return data

def main():
    parser = argparse.ArgumentParser(description='Populate NFS Index database from JSON')
    parser.add_argument('--make', required=True, help='Make name (e.g., Mercedes-Benz, Porsche)')
    parser.add_argument('--model', required=True, help='Model name (e.g., SLR McLaren, 911 GT3)')
    
    args = parser.parse_args()
    
    print("="*70)
    print("NFS Index - Database Population from JSON")
    print("="*70)
    print(f"Make: {args.make}")
    print(f"Model: {args.model}")
    print()
    
    print("Step 1: Loading JSON data...")
    print("-"*70)
    
    listings = load_json(args.model)
    
    if not listings:
        print(f"No JSON file found for {args.model}. Please run scrape.py first.")
        return
    
    print(f"Loaded {len(listings)} listings from JSON")
    
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
    
    make_id = get_or_create_make(conn, args.make)
    print(f"{args.make} (ID: {make_id})")
    
    model_id = get_or_create_model(conn, make_id, args.model)
    print(f"{args.model} (ID: {model_id})")
    
    print("\n" + "="*70)
    print("Step 4: Ingesting listings...")
    print("-"*70)
    
    inserted = 0
    updated = 0
    errors = 0
    
    for i, listing in enumerate(listings, 1):
        try:
            result = ingest_listing(conn, listing, make_id, model_id, args.model)
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
    print("POPULATION COMPLETE")
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
