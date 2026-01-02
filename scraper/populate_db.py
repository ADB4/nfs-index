"""
Ingest BaT scraped data into the NFS Index database from JSON file

Usage:
    python3 populate_db.py --json-file data/json/slr-mclaren_data.json
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
    make_name = make_name.upper()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM makes WHERE name = %s", (make_name,))
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        cur.execute("INSERT INTO makes (name) VALUES (%s) RETURNING id", (make_name,))
        conn.commit()
        return cur.fetchone()[0]

def get_or_create_model(conn, make_id, model_name):
    model_name = model_name.upper()
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

def get_or_create_variant(conn, model_id, variant_name):
    if not variant_name:
        variant_name = "STANDARD"
    else:
        variant_name = variant_name.upper()
    
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM variants WHERE model_id = %s AND name = %s",
            (model_id, variant_name)
        )
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        cur.execute(
            "INSERT INTO variants (model_id, name) VALUES (%s, %s) RETURNING id",
            (model_id, variant_name)
        )
        conn.commit()
        return cur.fetchone()[0]

def ingest_listing(conn, listing, make_id, model_id):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM listings WHERE url = %s", (listing['url'],))
        existing = cur.fetchone()
        
        variant_name = listing.get('variant', 'Standard')
        variant_id = get_or_create_variant(conn, model_id, variant_name)
        
        sale_price_cents = listing.get('price') * 100 if 'price' in listing else None
        
        values = {
            'url': listing['url'],
            'source': listing.get('source', 'bringatrailer'),
            'title': listing.get('title'),
            'vin': listing.get('vin'),
            'year': listing.get('year'),
            'make_id': make_id,
            'model_id': model_id,
            'variant_id': variant_id,
            'engine': listing.get('engine'),
            'transmission': listing.get('transmission'),
            'mileage': listing.get('mileage'),
            'sale_price': sale_price_cents,
            'sale_date': listing.get('sale_date'),
            'reserve_met': True if sale_price_cents else None,
            'number_of_bids': listing.get('number_of_bids'),
            'location': listing.get('location'),
        }
        
        if existing:
            cur.execute("""
                UPDATE listings SET
                    source = %(source)s,
                    title = %(title)s,
                    vin = %(vin)s,
                    year = %(year)s,
                    make_id = %(make_id)s,
                    model_id = %(model_id)s,
                    variant_id = %(variant_id)s,
                    engine = %(engine)s,
                    transmission = %(transmission)s,
                    mileage = %(mileage)s,
                    sale_price = %(sale_price)s,
                    sale_date = %(sale_date)s,
                    reserve_met = %(reserve_met)s,
                    number_of_bids = %(number_of_bids)s,
                    location = %(location)s
                WHERE url = %(url)s
            """, values)
            return 'updated'
        else:
            cur.execute("""
                INSERT INTO listings (
                    url, source, title, vin, year, make_id, model_id, variant_id,
                    engine, transmission, mileage, sale_price, sale_date, reserve_met,
                    number_of_bids, location
                ) VALUES (
                    %(url)s, %(source)s, %(title)s, %(vin)s, %(year)s, %(make_id)s,
                    %(model_id)s, %(variant_id)s, %(engine)s, %(transmission)s,
                    %(mileage)s, %(sale_price)s, %(sale_date)s, %(reserve_met)s,
                    %(number_of_bids)s, %(location)s
                )
            """, values)
            return 'inserted'

def main():
    parser = argparse.ArgumentParser(description='Populate NFS Index database from JSON')
    parser.add_argument('--json-file', required=True, help='Path to JSON file (e.g., data/json/slr-mclaren_data.json)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.json_file):
        print(f"Error: File not found: {args.json_file}")
        return
    
    print("="*70)
    print("NFS Index - Database Population from JSON")
    print("="*70)
    print(f"File: {args.json_file}")
    print()
    
    print("Step 1: Loading JSON data...")
    print("-"*70)
    
    with open(args.json_file) as f:
        listings = json.load(f)
    
    if not listings:
        print(f"No listings found in JSON file.")
        return
    
    print(f"Loaded {len(listings)} listings from JSON")
    
    first_listing = listings[0]
    make_name = first_listing.get('make')
    model_name = first_listing.get('model')
    
    if not make_name or not model_name:
        print("Error: JSON listings must contain 'make' and 'model' fields")
        return
    
    print(f"Make: {make_name}")
    print(f"Model: {model_name}")
    
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
    
    make_id = get_or_create_make(conn, make_name)
    print(f"{make_name} -> {make_name.upper()} (ID: {make_id})")
    
    model_id = get_or_create_model(conn, make_id, model_name)
    print(f"{model_name} -> {model_name.upper()} (ID: {model_id})")
    
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