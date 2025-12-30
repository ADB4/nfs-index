from flask import Blueprint, jsonify, request
from database import execute_query

listings_bp = Blueprint('listings', __name__, url_prefix='/api')
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

@listings_bp.route('/listings')
def get_listings():
    try:
        model_id = request.args.get('model_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        query = """
            SELECT l.id, l.listing_url, l.source, mk.name as make, md.name as model, 
                   l.year, t.name as trim, l.sale_price, l.sale_date, l.mileage, 
                   l.number_of_bids, l.location, l.reserve_met
            FROM listings l
            LEFT JOIN makes mk ON l.make_id = mk.id
            LEFT JOIN models md ON l.model_id = md.id
            LEFT JOIN trims t ON l.trim_id = t.id
            WHERE (%s::integer IS NULL OR l.model_id = %s)
            ORDER BY l.sale_date DESC
            LIMIT %s OFFSET %s
        """
        
        rows = execute_query(query, (model_id, model_id, per_page, offset))
        
        listings = []
        for row in rows:
            listing = dict(row)
            if listing['sale_price']:
                listing['sale_price'] = listing['sale_price'] / 100
            if listing['sale_date']:
                listing['sale_date'] = listing['sale_date'].isoformat()
            listings.append(listing)
        
        return jsonify({'listings': listings})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@listings_bp.route('/models')
def get_models():
    try:
        query = """
            SELECT m.id, m.name, mk.name as make_name
            FROM models m
            JOIN makes mk ON m.make_id = mk.id
            ORDER BY mk.name, m.name
        """
        rows = execute_query(query)
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/trends')
def get_trends():
    try:
        model_id = request.args.get('model_id')
        if not model_id:
            return jsonify({'error': 'model_id required'}), 400
        
        query = """
            SELECT 
                DATE_TRUNC('month', sale_date) as period,
                AVG(sale_price) as avg_price,
                MIN(sale_price) as min_price,
                MAX(sale_price) as max_price,
                COUNT(*) as count
            FROM listings
            WHERE model_id = %s AND sale_price IS NOT NULL
            GROUP BY period
            ORDER BY period
        """
        
        rows = execute_query(query, (model_id,))
        
        trends = []
        for row in rows:
            trends.append({
                'period': row['period'].isoformat(),
                'avg_price': float(row['avg_price']) / 100,
                'min_price': float(row['min_price']) / 100,
                'max_price': float(row['max_price']) / 100,
                'count': row['count']
            })
        
        return jsonify({'trends': trends})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/stats')
def get_stats():
    try:
        model_id = request.args.get('model_id')
        if not model_id:
            return jsonify({'error': 'model_id required'}), 400
        
        query = """
            SELECT 
                COUNT(*) as total_sales,
                AVG(sale_price) as avg_price,
                MIN(sale_price) as min_price,
                MAX(sale_price) as max_price,
                AVG(mileage) as avg_mileage,
                AVG(number_of_bids) as avg_bids
            FROM listings
            WHERE model_id = %s AND sale_price IS NOT NULL
        """
        
        row = execute_query(query, (model_id,), fetch_one=True)
        
        stats = {
            'total_sales': row['total_sales'],
            'avg_price': float(row['avg_price']) / 100 if row['avg_price'] else None,
            'min_price': float(row['min_price']) / 100 if row['min_price'] else None,
            'max_price': float(row['max_price']) / 100 if row['max_price'] else None,
            'avg_mileage': int(row['avg_mileage']) if row['avg_mileage'] else None,
            'avg_bids': float(row['avg_bids']) if row['avg_bids'] else None
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
