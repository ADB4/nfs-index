import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_db_connection():
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nfs_index')
    
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return conn

def execute_query(query, params=None, fetch_one=False):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        
        if fetch_one:
            result = cur.fetchone()
        else:
            result = cur.fetchall()
        
        cur.close()
        return result
    finally:
        conn.close()
