import os
import json
import argparse
from datetime import datetime

from bat_scraper import BATSeleniumScraper

"""
Scrapes individual listings for a make and model, saves to JSON in /data

Usage: 
    python3 scrape.py --slug "slr-mclaren" --make "Mercedes-Benz" --model-full "SLR McLaren" --model-short "SLR McLaren "
    python3 scrape.py --slug "997-gt3" --make "Porsche" --model-full "911 997 GT3" --model-short "911 GT3 " --min-year 2007 --max-year 2012
    python3 scrape.py --json cars_test.json
"""

def normalize_car_config(car):
    model_short = None
    for key in ['modelShort', 'modelSHort', 'modelshort']:
        if key in car:
            model_short = car[key]
            break
    
    model_full = None
    for key in ['modelFull', 'modelfull']:
        if key in car:
            model_full = car[key]
            break
    
    if not model_short:
        model_short = model_full or ''
    
    if not model_full:
        model_full = model_short.strip()
    
    return {
        'slugs': car['slug'] if isinstance(car['slug'], list) else [car['slug']],
        'make': car['make'],
        'model_full': model_full,
        'model_short': model_short,
        'min_year': car.get('minYear'),
        'max_year': car.get('maxYear')
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape BringATrailer model pages and save to JSON')
    parser.add_argument('--slug', nargs='+', help='Slug(s) for BaT URL (e.g., slr-mclaren)')
    parser.add_argument('--make', help='Make name (e.g., Mercedes-Benz)')
    parser.add_argument('--model-full', help='Full model name (e.g., SLR McLaren)')
    parser.add_argument('--model-short', help='Short model name for variant matching (e.g., "SLR McLaren ")')
    parser.add_argument('--min-year', type=int, help='Minimum model year to include')
    parser.add_argument('--max-year', type=int, help='Maximum model year to include')
    parser.add_argument('--max-listings', type=int, default=100, help='Maximum listings to scrape per slug')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--json', help='Path to JSON file containing array of car objects')
    parser.add_argument('--fields', nargs='+', help='Specific fields to include in output JSON (e.g., --fields url title price year)')
    parser.add_argument('--sort-oldest', action='store_true', help='Sort results by oldest first before scraping')
    parser.add_argument('--append', help='Path to existing JSON file - scrape until duplicate found, save only new listings')
    
    args = parser.parse_args()
    
    if args.append and not os.path.exists(args.append):
        print(f"error: append file not found: {args.append}")
        exit(1)
    
    cars_to_scrape = []
    
    if args.json:
        print(f"loading cars from {args.json}...")
        with open(args.json, 'r') as f:
            cars_data = json.load(f)
        
        for car in cars_data:
            cars_to_scrape.append(normalize_car_config(car))
    else:
        if not all([args.slug, args.make, args.model_full, args.model_short]):
            print("error: --slug, --make, --model-full, and --model-short are required (or use --json)")
            exit(1)
        
        cars_to_scrape.append({
            'slugs': args.slug,
            'make': args.make,
            'model_full': args.model_full,
            'model_short': args.model_short,
            'min_year': args.min_year,
            'max_year': args.max_year
        })
    
    print(f"\ntotal cars to scrape: {len(cars_to_scrape)}\n")
    
    for idx, car_config in enumerate(cars_to_scrape, 1):
        print("=" * 70)
        print(f"[{idx}/{len(cars_to_scrape)}] BringATrailer scraper - {car_config['make']} {car_config['model_full']}")
        print("=" * 70)
        print(f"slugs: {', '.join(car_config['slugs'])}")
        if car_config['min_year']:
            print(f"year range: {car_config['min_year']}-{car_config['max_year'] or 'present'}")
        if args.append:
            print(f"append mode: will stop at first duplicate from {args.append}")
        print()

        scraper = BATSeleniumScraper(
            slugs=car_config['slugs'],
            make=car_config['make'],
            model_full=car_config['model_full'],
            model_short=car_config['model_short'],
            min_year=car_config['min_year'],
            max_year=car_config['max_year'],
            headless=args.headless,
            fields=args.fields,
            sort_oldest=args.sort_oldest,
            append_file=args.append
        )
        
        try:
            listings = scraper.scrape_all_slugs()
            
            if listings:
                print(f"\n{'='*70}")
                print(f"successfully scraped {len(listings)} {car_config['model_full']} listings")
                print(f"{'='*70}\n")
                
                sold = [l for l in listings if 'price' in l]
                if sold:
                    prices = [l['price'] for l in sold]
                    
                    print("summary statistics:")
                    print(f"  total listings: {len(listings)}")
                    print(f"  listings with price data: {len(sold)}")
                    print(f"  average sale price: ${sum(prices)/len(prices):,.0f}")
                    print(f"  price range: ${min(prices):,} - ${max(prices):,}")

                    years = {}
                    for listing in sold:
                        if 'year' in listing:
                            year = listing['year']
                            years[year] = years.get(year, 0) + 1
                    
                    if years:
                        print(f"\n  sales by year:")
                        for year in sorted(years.keys()):
                            print(f"    {year}: {years[year]} listing(s)")
                    
                    variants = {}
                    for listing in sold:
                        if 'variant' in listing:
                            variant = listing['variant']
                            variants[variant] = variants.get(variant, 0) + 1
                    
                    if variants:
                        print(f"\n  sales by variant:")
                        for variant in sorted(variants.keys()):
                            print(f"    {variant}: {variants[variant]} listing(s)")
                    
                    print(f"\n{'='*70}")
                
                model_slug = car_config['slugs'][0]
                
                if args.append:
                    base_name = os.path.splitext(os.path.basename(args.append))[0]
                    output_path = f"data/json/output/raw/{base_name}_n{len(listings)}.json"
                else:
                    output_path = f"data/json/output/raw/{model_slug}_data.json"
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, "w") as f:
                    json.dump(listings, f, indent=4)
                
                print(f"\nsaved {len(listings)} listings to {output_path}")
                print("done\n")
                
            else:
                print("\nno listings found\n")
            
            scraper.close()
        
        except Exception as e:
            print(f"\nerror scraping {car_config['make']} {car_config['model_full']}: {e}\n")
            try:
                scraper.close()
            except:
                pass