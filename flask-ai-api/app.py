"""
DAY 8-9: Flask AI API - Smart Inventory System
With Smart Restock Prediction Endpoint
"""

from flask import Flask, jsonify
from flask_cors import CORS
import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow React and Java to call this API

# ======================================================
# DATABASE CONFIGURATION
# ======================================================
# ⚠️ IMPORTANT: Change 'your_password_here' to your MySQL password!
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin123',  # 🔴 CHANGE THIS to your MySQL password
    'database': 'smart_inventory'
}

# Model path
MODEL_PATH = 'models/restock_model.pkl'
model = None

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return None

def load_restock_model():
    """Load the trained restock prediction model"""
    global model
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print("✅ Restock prediction model loaded")
        return True
    else:
        print("⚠️ No trained model found. Run python ai_models.py first")
        return False

# ======================================================
# HEALTH CHECK ENDPOINT
# ======================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple endpoint to check if API is running"""
    return jsonify({
        'status': 'success',
        'message': 'Flask AI API is running!',
        'timestamp': datetime.now().isoformat()
    })

# ======================================================
# TEST DATABASE CONNECTION
# ======================================================

@app.route('/api/test-db', methods=['GET'])
def test_database():
    """Test if database connection is working"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        product_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({
            'status': 'success',
            'message': 'Database connected!',
            'product_count': product_count
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Database connection failed'
        }), 500

# ======================================================
# GET PRODUCTS WITH INVENTORY
# ======================================================

@app.route('/api/flask-products', methods=['GET'])
def get_products():
    """Get all products with inventory data"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        query = """
            SELECT 
                p.id, p.name, p.sku, p.category, 
                p.unit_price, i.quantity as stock,
                s.name as supplier_name
            FROM products p
            JOIN inventory i ON p.id = i.product_id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.is_active = TRUE
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return jsonify({
            'status': 'success',
            'products': df.to_dict(orient='records'),
            'count': len(df)
        })
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# ======================================================
# SMART RESTOCK PREDICTION ENDPOINT
# ======================================================

@app.route('/api/restock-prediction', methods=['GET'])
def restock_prediction():
    """Predict when products will run out of stock"""
    
    if model is None:
        if not load_restock_model():
            return jsonify({
                'status': 'error',
                'message': 'Model not trained yet. Run python ai_models.py first.'
            }), 500
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get current inventory with sales data
        query = """
            SELECT 
                p.id as product_id,
                p.name as product_name,
                p.unit_price,
                p.supplier_id,
                s.name as supplier_name,
                i.quantity as stock,
                i.reorder_level,
                COALESCE(SUM(si.quantity), 0) as total_sold,
                COUNT(DISTINCT sa.id) as total_sales
            FROM products p
            JOIN inventory i ON p.id = i.product_id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            LEFT JOIN sale_items si ON p.id = si.product_id
            LEFT JOIN sales sa ON si.sale_id = sa.id AND sa.sale_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            WHERE p.is_active = TRUE
            GROUP BY p.id
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Calculate daily sales (last 30 days)
        df['daily_sales'] = df['total_sold'] / 30
        df['daily_sales'] = df['daily_sales'].fillna(0)
        
        # Use the SAME column names as training
        features = df[['stock', 'daily_sales', 'reorder_level', 'total_sold']].fillna(0)
        
        # Make predictions
        predictions = model.predict(features)
        
        # Prepare response
        results = []
        for i, row in df.iterrows():
            days_until_out = predictions[i]
            
            # Handle negative or zero predictions
            if days_until_out <= 0:
                days_until_out = 1
            
            # Determine urgency
            if days_until_out <= 3:
                urgency = "CRITICAL"
                color = "red"
                icon = "🔴"
                action = "ORDER NOW! Stock will run out within 3 days"
            elif days_until_out <= 7:
                urgency = "HIGH"
                color = "orange"
                icon = "🟠"
                action = "Place order within 2 days"
            elif days_until_out <= 14:
                urgency = "MEDIUM"
                color = "yellow"
                icon = "🟡"
                action = "Plan restock next week"
            else:
                urgency = "LOW"
                color = "green"
                icon = "🟢"
                action = "Stock is sufficient"
            
            # Calculate recommended restock quantity
            if days_until_out < 30:
                recommended_qty = int(row['daily_sales'] * 30)
            else:
                recommended_qty = row['reorder_level'] * 2
            
            if recommended_qty < row['reorder_level']:
                recommended_qty = row['reorder_level']
            
            results.append({
                'product_id': int(row['product_id']),
                'product_name': row['product_name'],
                'current_stock': int(row['stock']),
                'avg_daily_sales': round(row['daily_sales'], 2),
                'days_until_out': round(days_until_out, 1),
                'urgency': urgency,
                'color': color,
                'icon': icon,
                'action': action,
                'recommended_restock_qty': int(recommended_qty),
                'supplier_id': int(row['supplier_id']) if row['supplier_id'] else None,
                'supplier_name': row['supplier_name'] if row['supplier_name'] else 'Unknown'
            })
        
        # Sort by urgency (most urgent first)
        urgency_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        results.sort(key=lambda x: urgency_order[x['urgency']])
        
        # Count by urgency
        urgency_counts = {
            'CRITICAL': len([r for r in results if r['urgency'] == 'CRITICAL']),
            'HIGH': len([r for r in results if r['urgency'] == 'HIGH']),
            'MEDIUM': len([r for r in results if r['urgency'] == 'MEDIUM']),
            'LOW': len([r for r in results if r['urgency'] == 'LOW'])
        }
        
        return jsonify({
            'status': 'success',
            'predictions': results,
            'count': len(results),
            'urgency_counts': urgency_counts,
            'message': 'Restock predictions generated successfully'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ======================================================
# SINGLE PRODUCT RESTOCK PREDICTION
# ======================================================

@app.route('/api/restock-prediction/<int:product_id>', methods=['GET'])
def restock_prediction_by_product(product_id):
    """Get restock prediction for a specific product"""
    
    # Get all predictions
    all_predictions = restock_prediction()
    
    # If the response is a tuple (error), return it
    if isinstance(all_predictions, tuple):
        return all_predictions
    
    # Get JSON data
    data = all_predictions.get_json()
    
    if data.get('status') == 'success':
        for product in data.get('predictions', []):
            if product['product_id'] == product_id:
                return jsonify({
                    'status': 'success',
                    'prediction': product
                })
        
        return jsonify({
            'status': 'error',
            'message': f'Product {product_id} not found'
        }), 404
    
    return all_predictions

# ======================================================
# SUMMARY STATISTICS
# ======================================================

@app.route('/api/restock-summary', methods=['GET'])
def restock_summary():
    """Get summary statistics for restock predictions"""
    
    all_predictions = restock_prediction()
    
    if isinstance(all_predictions, tuple):
        return all_predictions
    
    data = all_predictions.get_json()
    
    if data.get('status') == 'success':
        predictions = data.get('predictions', [])
        
        summary = {
            'total_products': len(predictions),
            'critical_count': len([p for p in predictions if p['urgency'] == 'CRITICAL']),
            'high_count': len([p for p in predictions if p['urgency'] == 'HIGH']),
            'medium_count': len([p for p in predictions if p['urgency'] == 'MEDIUM']),
            'low_count': len([p for p in predictions if p['urgency'] == 'LOW']),
            'avg_days_until_out': round(np.mean([p['days_until_out'] for p in predictions]), 1) if predictions else 0,
            'total_restock_needed': sum([p['recommended_restock_qty'] for p in predictions if p['urgency'] in ['CRITICAL', 'HIGH']])
        }
        
        return jsonify({
            'status': 'success',
            'summary': summary
        })
    
    return all_predictions

# ======================================================
# FAST AND SLOW MOVING PRODUCTS (Day 10 Preview)
# ======================================================

@app.route('/api/product-movement', methods=['GET'])
def product_movement():
    """Analyze product movement speed (Fast/Slow/Dead stock)"""
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        query = """
            SELECT 
                p.id as product_id,
                p.name as product_name,
                p.category,
                i.quantity as current_stock,
                COALESCE(SUM(si.quantity), 0) as total_sold,
                COUNT(DISTINCT s.id) as sale_count,
                MAX(s.sale_date) as last_sale_date
            FROM products p
            JOIN inventory i ON p.id = i.product_id
            LEFT JOIN sale_items si ON p.id = si.product_id
            LEFT JOIN sales s ON si.sale_id = s.id
            WHERE p.is_active = TRUE
            GROUP BY p.id
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Fill NaN values
        df['total_sold'] = df['total_sold'].fillna(0)
        df['sale_count'] = df['sale_count'].fillna(0)
        
        # Calculate days since last sale
        df['last_sale_date'] = pd.to_datetime(df['last_sale_date'])
        df['days_since_last_sale'] = (datetime.now() - df['last_sale_date']).dt.days.fillna(999)
        
        # Classify products
        results = []
        for _, row in df.iterrows():
            if row['total_sold'] > 50:
                movement = "FAST MOVING"
                color = "green"
                icon = "⚡"
                recommendation = "Keep adequate stock, reorder weekly"
            elif row['total_sold'] > 10:
                movement = "NORMAL"
                color = "blue"
                icon = "✓"
                recommendation = "Monitor stock levels monthly"
            elif row['total_sold'] > 0:
                movement = "SLOW MOVING"
                color = "orange"
                icon = "🐢"
                recommendation = "Reduce stock levels, consider promotion"
            else:
                movement = "DEAD STOCK"
                color = "red"
                icon = "💀"
                recommendation = "Clearance sale, discontinue product"
            
            results.append({
                'product_id': int(row['product_id']),
                'product_name': row['product_name'],
                'category': row['category'],
                'current_stock': int(row['current_stock']),
                'total_sold': int(row['total_sold']),
                'days_since_last_sale': int(row['days_since_last_sale']) if row['days_since_last_sale'] < 999 else None,
                'movement': movement,
                'color': color,
                'icon': icon,
                'recommendation': recommendation
            })
        
        # Sort by movement (fast to dead)
        movement_order = {'FAST MOVING': 0, 'NORMAL': 1, 'SLOW MOVING': 2, 'DEAD STOCK': 3}
        results.sort(key=lambda x: movement_order[x['movement']])
        
        return jsonify({
            'status': 'success',
            'products': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================================================
# MAIN ENTRY POINT
# ======================================================

if __name__ == '__main__':
    print("=" * 50)
    print("🤖 Smart Inventory AI API")
    print("=" * 50)
    
    # Try to load the model
    load_restock_model()
    
    print("\n📍 Server running on http://localhost:5000")
    print("\n📋 Available Endpoints:")
    print("   GET /api/health - Health check")
    print("   GET /api/test-db - Test database connection")
    print("   GET /api/flask-products - Get all products")
    print("   GET /api/restock-prediction - Get restock predictions for all products")
    print("   GET /api/restock-prediction/{id} - Get prediction for specific product")
    print("   GET /api/restock-summary - Get summary statistics")
    print("   GET /api/product-movement - Fast/Slow/Dead stock analysis")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)