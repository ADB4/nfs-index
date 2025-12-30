from flask import Flask
from flask_cors import CORS
from routes import listings_bp, analytics_bp
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    app.register_blueprint(listings_bp)
    app.register_blueprint(analytics_bp)
    
    @app.route('/health')
    def health():
        return {'status': 'ok'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 8000))
    app.run(debug=True, host='0.0.0.0', port=port)
