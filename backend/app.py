from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_db():
    conn = psycopg2.connect(
        host="localhost",
        database="nfs_index",
        user="postgres",
        password="postgres"
    )
    return conn

@app.route('/health')
def health():
    return {'status': 'ok'}

@app.route('/api/listings')
def get_listings():
    conn = get_db()
    cur = conn.cursor()
    
    model_id = request.args.get('model_id')
    
    if model_id:
        cur.execute("""
            SELECT l.id, l.listing_url, l.source, mk.name as make, md.name as model, 
                   l.year, t.name as trim, l.sale_price, l.sale_date, l.mileage, 
                   l.number_of_bids, l.location
            FROM listings l
            LEFT JOIN makes mk ON l.make_id = mk.id
            LEFT JOIN models md ON l.model_id = md.id
            LEFT JOIN trims t ON l.trim_id = t.id
            WHERE l.model_id = %s
            ORDER BY l.sale_date DESC
            LIMIT 50
        """, (model_id,))
    else:
        cur.execute("""
            SELECT l.id, l.listing_url, l.source, mk.name as make, md.name as model, 
                   l.year, t.name as trim, l.sale_price, l.sale_date, l.mileage, 
                   l.number_of_bids, l.location
            FROM listings l
            LEFT JOIN makes mk ON l.make_id = mk.id
            LEFT JOIN models md ON l.model_id = md.id
            LEFT JOIN trims t ON l.trim_id = t.id
            ORDER BY l.sale_date DESC
            LIMIT 50
        """)
    
    rows = cur.fetchall()
    listings = []
    for row in rows:
        listings.append({
            'id': row[0],
            'listing_url': row[1],
            'source': row[2],
            'make': row[3],
            'model': row[4],
            'year': row[5],
            'trim': row[6],
            'sale_price': row[7] / 100 if row[7] else None,
            'sale_date': row[8].isoformat() if row[8] else None,
            'mileage': row[9],
            'number_of_bids': row[10],
            'location': row[11]
        })
    
    cur.close()
    conn.close()
    
    return jsonify({'listings': listings})

@app.route('/api/models')
def get_models():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.name, mk.name as make_name
        FROM models m
        JOIN makes mk ON m.make_id = mk.id
    """)
    rows = cur.fetchall()
    models = [{'id': r[0], 'name': r[1], 'make_name': r[2]} for r in rows]
    cur.close()
    conn.close()
    return jsonify(models)

@app.route('/api/analytics/trends')
def get_trends():
    model_id = request.args.get('model_id')
    if not model_id:
        return jsonify({'error': 'need model_id'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            DATE_TRUNC('month', sale_date) as month,
            AVG(sale_price) as avg_price,
            COUNT(*) as count
        FROM listings
        WHERE model_id = %s AND sale_price IS NOT NULL
        GROUP BY month
        ORDER BY month
    """, (model_id,))
    
    rows = cur.fetchall()
    trends = []
    for row in rows:
        trends.append({
            'period': row[0].isoformat(),
            'avg_price': float(row[1]) / 100,
            'count': row[2]
        })
    
    cur.close()
    conn.close()
    return jsonify({'trends': trends})

if __name__ == '__main__':
    app.run(debug=True, port=5000)