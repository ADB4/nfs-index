"""
normalization module for scraper.py json output

usage:
    python3 normalize_data.py --input data/json/gallardo_data.json --output data/json/gallardo_data_normalized.json
    python3 normalize_data.py --input data/json/gallardo_data.json --output data/json/gallardo_data_normalized.json --rules custom_rules.json
"""

import json
import re
import argparse
from collections import defaultdict

class DataNormalizer:
    def __init__(self, custom_rules=None):
        """
        Initialize normalizer with custom rules only
        If no custom rules provided, data passes through unchanged
        """
        self.use_normalization = custom_rules is not None
        self.engine_mappings = {}
        self.transmission_mappings = {}
        self.variant_mappings = {}
        
        if custom_rules:
            self._load_custom_rules(custom_rules)
    
    def _load_custom_rules(self, rules_file):
        """load custom normalization rules from JSON file"""
        with open(rules_file, 'r') as f:
            custom = json.load(f)
            
        if 'engine' in custom:
            self.engine_mappings = custom['engine']
        if 'transmission' in custom:
            self.transmission_mappings = custom['transmission']
        if 'variant' in custom:
            # Create case-insensitive mapping for variants
            self.variant_mappings = {k.upper(): v for k, v in custom['variant'].items()}
    
    def normalize_engine(self, engine):
        """normalize engine string using manual mappings only"""
        if not engine or engine == 'N/A' or not self.use_normalization:
            return engine
        
        return self.engine_mappings.get(engine, engine)
    
    def normalize_transmission(self, transmission):
        """normalize transmission string using manual mappings only"""
        if not transmission or transmission == 'N/A' or not self.use_normalization:
            return transmission
        
        return self.transmission_mappings.get(transmission, transmission)
    
    def normalize_variant(self, variant):
        """normalize variant string using case-insensitive manual mappings"""
        if not variant or not self.use_normalization:
            return variant
        
        # Case-insensitive lookup
        return self.variant_mappings.get(variant.upper(), variant)
    
    def normalize_listing(self, listing):
        """normalize a single listing"""
        normalized = listing.copy()
        
        if 'engine' in normalized:
            normalized['engine'] = self.normalize_engine(normalized['engine'])
        
        if 'transmission' in normalized:
            normalized['transmission'] = self.normalize_transmission(normalized['transmission'])
        
        if 'variant' in normalized:
            normalized['variant'] = self.normalize_variant(normalized['variant'])
        
        return normalized
    
    def normalize_all(self, listings):
        """Normalize all listings"""
        return [self.normalize_listing(listing) for listing in listings]
    
    def analyze_fields(self, listings):
        """
        analyze field variations before normalization
        returns stats about unique values
        """
        stats = {
            'engine': defaultdict(int),
            'transmission': defaultdict(int),
            'variant': defaultdict(int)
        }
        
        for listing in listings:
            for field in ['engine', 'transmission', 'variant']:
                value = listing.get(field)
                if value:
                    stats[field][value] += 1
        
        return stats
    
    def print_analysis(self, before_stats, after_stats):
        """print before/after analysis"""
        print("\n" + "="*70)
        print("NORMALIZATION ANALYSIS")
        print("="*70)
        
        for field in ['engine', 'transmission', 'variant']:
            print(f"\n{field.upper()}:")
            print(f"  Before: {len(before_stats[field])} unique values")
            print(f"  After:  {len(after_stats[field])} unique values")
            print(f"  Reduction: {len(before_stats[field]) - len(after_stats[field])} values consolidated")
            
            if len(before_stats[field]) <= 20:
                print(f"\n  Before normalization:")
                for value, count in sorted(before_stats[field].items(), key=lambda x: -x[1]):
                    print(f"    - {value}: {count}")
                
                print(f"\n  After normalization:")
                for value, count in sorted(after_stats[field].items(), key=lambda x: -x[1]):
                    print(f"    - {value}: {count}")

def main():
    parser = argparse.ArgumentParser(description='Normalize BringATrailer JSON data')
    parser.add_argument('--input', required=True, help='Input JSON file path')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--rules', help='Optional custom rules JSON file')
    parser.add_argument('--analyze', action='store_true', help='Print analysis of normalization')
    
    args = parser.parse_args()
    
    print("="*70)
    print("BringATrailer Data Normalizer")
    print("="*70)
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    if args.rules:
        print(f"Rules:  {args.rules}")
    print()
    
    # Load data
    print("Loading data...")
    with open(args.input, 'r') as f:
        listings = json.load(f)
    print(f"Loaded {len(listings)} listings")
    
    # Initialize normalizer
    normalizer = DataNormalizer(custom_rules=args.rules)
    
    # Analyze before
    if args.analyze:
        before_stats = normalizer.analyze_fields(listings)
    
    # Normalize
    print("\nNormalizing data...")
    normalized_listings = normalizer.normalize_all(listings)
    
    # Analyze after
    if args.analyze:
        after_stats = normalizer.analyze_fields(normalized_listings)
        normalizer.print_analysis(before_stats, after_stats)
    
    # Save
    print(f"\nSaving to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(normalized_listings, f, indent=4)
    
    print("\n" + "="*70)
    print("NORMALIZATION COMPLETE")
    print("="*70)
    print(f"Normalized {len(normalized_listings)} listings")
    print()

if __name__ == '__main__':
    main()