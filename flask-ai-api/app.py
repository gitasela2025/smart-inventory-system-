"""
Smart Inventory AI API - Complete
Days 8-10: Flask Setup + Restock Prediction + Product Movement Analysis
"""

from flask import Flask, jsonify
from flask_cors import CORS
import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime
from prophet import Prophet
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins='http://localhost:3000') 

# ======================================================
# DATABASE CONFIGURATION
# ======================================================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin123',
    'database': 'smart_inventory',
    'auth_plugin': 'mysql_native_password'
}

# Model path
MODEL_PATH = 'models/restock_model.pkl'
model = None

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return None

def load_restock_model():
    global model
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print("✅ Restock prediction model loaded")
        return True
    else:
        print("⚠️ No model found. Run python ai_models.py first")
        return False

# ======================================================
# HEALTH CHECK
# ======================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'success',
        'message': 'Flask AI API is running!',
        'timestamp': datetime.now().isoformat()
    })

# ======================================================
# TEST DATABASE
# ======================================================

@app.route('/api/test-db', methods=['GET'])
def test_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'product_count': count})
    return jsonify({'status': 'error', 'message': 'DB connection failed'}), 500

# ======================================================
# GET PRODUCTS
# ======================================================

@app.route('/api/flask-products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'DB connection failed'}), 500
    try:
        query = """
            SELECT p.id, p.name, p.sku, p.category, p.unit_price, 
                   i.quantity as stock, s.name as supplier_name
            FROM products p
            JOIN inventory i ON p.id = i.product_id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.is_active = TRUE
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return jsonify({'status': 'success', 'products': df.to_dict(orient='records'), 'count': len(df)})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# ======================================================
# DAY 9: SMART RESTOCK PREDICTION
# ======================================================

@app.route('/api/restock-prediction', methods=['GET'])
def restock_prediction():
    if model is None:
        if not load_restock_model():
            return jsonify({'status': 'error', 'message': 'Model not trained. Run python ai_models.py'}), 500
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'DB connection failed'}), 500
    
    try:
        query = """
            SELECT p.id, p.name, p.unit_price, p.supplier_id, s.name as supplier_name,
                   i.quantity as stock, i.reorder_level,
                   COALESCE(SUM(si.quantity), 0) as total_sold
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
        
        df['daily_sales'] = df['total_sold'] / 30
        df['daily_sales'] = df['daily_sales'].fillna(0)
        
        features = df[['stock', 'daily_sales', 'reorder_level', 'total_sold']].fillna(0)
        predictions = model.predict(features)
        
        results = []
        for i, row in df.iterrows():
            days = predictions[i]
            if days <= 0:
                days = 1
            
            if days <= 3:
                urgency = "CRITICAL"
                icon = "🔴"
                action = "ORDER NOW! Stock will run out within 3 days"
            elif days <= 7:
                urgency = "HIGH"
                icon = "🟠"
                action = "Place order within 2 days"
            elif days <= 14:
                urgency = "MEDIUM"
                icon = "🟡"
                action = "Plan restock next week"
            else:
                urgency = "LOW"
                icon = "🟢"
                action = "Stock is sufficient"
            
            recommended_qty = int(row['daily_sales'] * 30) if days < 30 else row['reorder_level'] * 2
            if recommended_qty < row['reorder_level']:
                recommended_qty = row['reorder_level']
            
            results.append({
                'product_id': int(row['id']),
                'product_name': row['name'],
                'current_stock': int(row['stock']),
                'avg_daily_sales': round(row['daily_sales'], 2),
                'days_until_out': round(days, 1),
                'urgency': urgency,
                'icon': icon,
                'action': action,
                'recommended_restock_qty': recommended_qty,
                'supplier_name': row['supplier_name'] if row['supplier_name'] else 'Unknown'
            })
        
        urgency_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        results.sort(key=lambda x: urgency_order[x['urgency']])
        
        return jsonify({'status': 'success', 'predictions': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/restock-prediction/<int:product_id>', methods=['GET'])
def restock_prediction_by_id(product_id):
    resp = restock_prediction()
    if isinstance(resp, tuple):
        return resp
    data = resp.get_json()
    if data.get('status') == 'success':
        for p in data.get('predictions', []):
            if p['product_id'] == product_id:
                return jsonify({'status': 'success', 'prediction': p})
        return jsonify({'status': 'error', 'message': 'Product not found'}), 404
    return resp

@app.route('/api/restock-summary', methods=['GET'])
def restock_summary():
    resp = restock_prediction()
    if isinstance(resp, tuple):
        return resp
    data = resp.get_json()
    if data.get('status') == 'success':
        preds = data.get('predictions', [])
        summary = {
            'total_products': len(preds),
            'critical_count': len([p for p in preds if p['urgency'] == 'CRITICAL']),
            'high_count': len([p for p in preds if p['urgency'] == 'HIGH']),
            'medium_count': len([p for p in preds if p['urgency'] == 'MEDIUM']),
            'low_count': len([p for p in preds if p['urgency'] == 'LOW'])
        }
        return jsonify({'status': 'success', 'summary': summary})
    return resp

# ======================================================
# DAY 10: PRODUCT MOVEMENT ANALYSIS (FULL VERSION)
# ======================================================

@app.route('/api/product-movement', methods=['GET'])
def product_movement():
    """Complete product movement analysis with ABC classification"""
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        query = """
            SELECT 
                p.id as product_id,
                p.name as product_name,
                p.category,
                p.unit_price,
                p.cost_price,
                s.id as supplier_id,
                s.name as supplier_name,
                i.quantity as current_stock,
                i.reorder_level,
                COALESCE(SUM(si.quantity), 0) as total_sold,
                COUNT(DISTINCT sa.id) as total_sales,
                MAX(sa.sale_date) as last_sale_date
            FROM products p
            JOIN inventory i ON p.id = i.product_id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            LEFT JOIN sale_items si ON p.id = si.product_id
            LEFT JOIN sales sa ON si.sale_id = sa.id
            WHERE p.is_active = TRUE
            GROUP BY p.id
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Fill NaN values
        df['total_sold'] = df['total_sold'].fillna(0)
        df['total_sales'] = df['total_sales'].fillna(0)
        
        # Calculate sales value for ABC Analysis
        df['sales_value'] = df['total_sold'] * df['unit_price']
        
        # Sort by sales value for ABC Analysis (Pareto: 70-20-10)
        df_sorted = df.sort_values('sales_value', ascending=False).reset_index(drop=True)
        total_value = df_sorted['sales_value'].sum()
        if total_value > 0:
            df_sorted['cumulative_percentage'] = df_sorted['sales_value'].cumsum() / total_value * 100
        else:
            df_sorted['cumulative_percentage'] = 0
        
        def get_abc_category(cum_pct):
            if cum_pct <= 70:
                return "A (High Value - 70% of revenue)"
            elif cum_pct <= 90:
                return "B (Medium Value - 20% of revenue)"
            else:
                return "C (Low Value - 10% of revenue)"
        
        df_sorted['abc_category'] = df_sorted['cumulative_percentage'].apply(get_abc_category)
        
        # Merge back
        df = df.merge(df_sorted[['product_id', 'abc_category', 'cumulative_percentage']], on='product_id', how='left')
        df['abc_category'] = df['abc_category'].fillna("C (Low Value - 10% of revenue)")
        df['cumulative_percentage'] = df['cumulative_percentage'].fillna(0)
        
        # Calculate days since last sale
        df['last_sale_date'] = pd.to_datetime(df['last_sale_date'])
        df['days_since_last_sale'] = (datetime.now() - df['last_sale_date']).dt.days.fillna(999)
        
        # Calculate Inventory Turnover Ratio
        df['inventory_turnover'] = df['total_sold'] / df['current_stock'].replace(0, 1)
        
        # Calculate Days of Inventory Outstanding (DIO)
        df['dio'] = 365 / df['inventory_turnover'].replace(0, 1)
        
        # Classify products by movement
        results = []
        for _, row in df.iterrows():
            # Movement classification
            if row['total_sold'] > 200:
                movement = "FAST MOVING"
                color = "green"
                icon = "⚡"
                recommendation = "Keep high stock, reorder weekly"
                action = "Auto-reorder when stock < 50"
            elif row['total_sold'] > 50:
                movement = "NORMAL"
                color = "blue"
                icon = "✓"
                recommendation = "Monitor monthly, reorder as needed"
                action = "Manual review every 2 weeks"
            elif row['total_sold'] > 0:
                movement = "SLOW MOVING"
                color = "orange"
                icon = "🐢"
                recommendation = "Reduce stock levels, consider promotion"
                action = "Review quarterly"
            else:
                movement = "DEAD STOCK"
                color = "red"
                icon = "💀"
                recommendation = "Clearance sale, discontinue product"
                action = "Remove from catalog"
            
            results.append({
                'product_id': int(row['product_id']),
                'product_name': row['product_name'],
                'category': row['category'],
                'supplier_id': int(row['supplier_id']) if row['supplier_id'] else None,
                'supplier_name': row['supplier_name'] if row['supplier_name'] else 'Unknown',
                'current_stock': int(row['current_stock']),
                'reorder_level': int(row['reorder_level']),
                'total_sold': int(row['total_sold']),
                'total_sales': int(row['total_sales']),
                'sales_value': round(row['sales_value'], 2),
                'days_since_last_sale': int(row['days_since_last_sale']) if row['days_since_last_sale'] < 999 else None,
                'inventory_turnover': round(row['inventory_turnover'], 2),
                'dio': round(row['dio'], 1),
                'abc_category': row['abc_category'],
                'cumulative_percentage': round(row['cumulative_percentage'], 1),
                'movement': movement,
                'color': color,
                'icon': icon,
                'recommendation': recommendation,
                'action': action
            })
        
        # Sort by sales value (highest first)
        results.sort(key=lambda x: x['sales_value'], reverse=True)
        
        # Summary statistics
        summary = {
            'total_products': len(results),
            'fast_moving_count': len([r for r in results if r['movement'] == 'FAST MOVING']),
            'normal_count': len([r for r in results if r['movement'] == 'NORMAL']),
            'slow_moving_count': len([r for r in results if r['movement'] == 'SLOW MOVING']),
            'dead_stock_count': len([r for r in results if r['movement'] == 'DEAD STOCK']),
            'total_sales_value': round(sum(r['sales_value'] for r in results), 2),
            'abc_a_count': len([r for r in results if 'A' in r['abc_category']]),
            'abc_b_count': len([r for r in results if 'B' in r['abc_category']]),
            'abc_c_count': len([r for r in results if 'C' in r['abc_category']]),
            'avg_inventory_turnover': round(sum(r['inventory_turnover'] for r in results) / len(results), 2) if results else 0,
            'total_dead_stock_value': sum(r['current_stock'] for r in results if r['movement'] == 'DEAD STOCK')
        }
        
        return jsonify({
            'status': 'success',
            'products': results,
            'summary': summary,
            'count': len(results),
            'message': 'Product movement analysis with ABC classification completed'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ======================================================
# DAY 11: SALES TREND ANALYSIS
# ======================================================

from prophet import Prophet

@app.route('/api/sales-trend', methods=['GET'])
def sales_trend():
    """Analyze sales trends and predict future sales"""
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get daily sales data
        query = """
            SELECT 
                DATE(s.sale_date) as sale_date,
                COUNT(DISTINCT s.id) as num_orders,
                SUM(si.quantity) as total_units,
                SUM(s.total_amount) as total_revenue
            FROM sales s
            JOIN sale_items si ON s.id = si.sale_id
            WHERE s.sale_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE(s.sale_date)
            ORDER BY sale_date
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        if len(df) < 30:
            return jsonify({'error': 'Not enough sales data for trend analysis'}), 400
        
        # Prepare data for Prophet (needs ds and y columns)
        prophet_df = pd.DataFrame({
            'ds': pd.to_datetime(df['sale_date']),
            'y': df['total_revenue']
        })
        
        # Train Prophet model
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        model.fit(prophet_df)
        
        # Make future predictions (next 30 days)
        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)
        
        # Get weekly and monthly aggregates
        df['weekday'] = pd.to_datetime(df['sale_date']).dt.day_name()
        df['week'] = pd.to_datetime(df['sale_date']).dt.isocalendar().week
        df['month'] = pd.to_datetime(df['sale_date']).dt.strftime('%Y-%m')
        
        weekly_avg = df.groupby('weekday')['total_revenue'].mean().to_dict()
        monthly_trend = df.groupby('month')['total_revenue'].sum().to_dict()
        
        # Detect seasonality
        weekend_avg = sum(df[df['weekday'].isin(['Saturday', 'Sunday'])]['total_revenue']) / len(df[df['weekday'].isin(['Saturday', 'Sunday'])])
        weekday_avg = sum(df[~df['weekday'].isin(['Saturday', 'Sunday'])]['total_revenue']) / len(df[~df['weekday'].isin(['Saturday', 'Sunday'])])
        
        seasonality = {
            'weekend_avg': round(weekend_avg, 2),
            'weekday_avg': round(weekday_avg, 2),
            'weekend_ratio': round((weekend_avg / weekday_avg) * 100, 1) if weekday_avg > 0 else 0,
            'best_day': max(weekly_avg, key=weekly_avg.get),
            'worst_day': min(weekly_avg, key=weekly_avg.get)
        }
        
        # Get predictions for next 30 days
        future_forecast = forecast[forecast['ds'] > datetime.now()][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].head(30)
        
        predictions = []
        for _, row in future_forecast.iterrows():
            predictions.append({
                'date': row['ds'].strftime('%Y-%m-%d'),
                'predicted_revenue': round(row['yhat'], 2),
                'lower_bound': round(row['yhat_lower'], 2),
                'upper_bound': round(row['yhat_upper'], 2)
            })
        
        # Calculate trends
        total_revenue = df['total_revenue'].sum()
        avg_daily_revenue = df['total_revenue'].mean()
        
        # Month over month growth
        monthly_revenue = df.groupby('month')['total_revenue'].sum().reset_index()
        if len(monthly_revenue) >= 2:
            last_month = monthly_revenue.iloc[-1]['total_revenue']
            prev_month = monthly_revenue.iloc[-2]['total_revenue']
            mom_growth = ((last_month - prev_month) / prev_month) * 100
        else:
            mom_growth = 0
        
        # Year over Year (if we have data)
        df['year'] = pd.to_datetime(df['sale_date']).dt.year
        yearly_revenue = df.groupby('year')['total_revenue'].sum()
        if len(yearly_revenue) >= 2:
            yoy_growth = ((yearly_revenue.iloc[-1] - yearly_revenue.iloc[-2]) / yearly_revenue.iloc[-2]) * 100
        else:
            yoy_growth = 0
        
        # Get plot data
        forecast_plot = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(60)
        plot_data = {
            'dates': forecast_plot['ds'].dt.strftime('%Y-%m-%d').tolist(),
            'actual': df.tail(30)['total_revenue'].tolist() if len(df) >= 30 else [],
            'predicted': forecast_plot['yhat'].tolist(),
            'lower_bound': forecast_plot['yhat_lower'].tolist(),
            'upper_bound': forecast_plot['yhat_upper'].tolist()
        }
        
        # Generate insight message
        if seasonality['weekend_ratio'] > 120:
            insight = f"Sales are {seasonality['weekend_ratio']:.0f}% higher on weekends. Consider running promotions on {seasonality['worst_day']} to boost sales."
        elif seasonality['weekend_ratio'] < 80:
            insight = f"Sales are lower on weekends. {seasonality['best_day']} is your best sales day."
        else:
            insight = "Sales are consistent throughout the week."
        
        if mom_growth > 10:
            insight += f" Sales are growing month-over-month (+{mom_growth:.0f}%)."
        elif mom_growth < -10:
            insight += f" Sales have decreased month-over-month. Consider marketing initiatives."
        
        return jsonify({
            'status': 'success',
            'summary': {
                'total_revenue_6months': round(total_revenue, 2),
                'avg_daily_revenue': round(avg_daily_revenue, 2),
                'month_over_month_growth': round(mom_growth, 1),
                'year_over_year_growth': round(yoy_growth, 1),
                'total_orders': int(df['num_orders'].sum()),
                'total_units': int(df['total_units'].sum()),
                'data_days': len(df)
            },
            'seasonality': seasonality,
            'weekly_trend': weekly_avg,
            'monthly_trend': monthly_trend,
            'predictions': predictions,
            'plot_data': plot_data,
            'insight': insight,
            'message': 'Sales trend analysis completed using Prophet model'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

        # ======================================================
# DAY 12: INTELLIGENT ALERTS
# ======================================================

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Generate intelligent alerts for inventory and sales"""
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    alerts = []
    
    try:
        # ==================================================
        # 1. LOW STOCK ALERTS (from restock predictions)
        # ==================================================
        
        # Get restock predictions
        restock_resp = restock_prediction()
        if isinstance(restock_resp, tuple):
            restock_data = restock_resp[0].get_json()
        else:
            restock_data = restock_resp.get_json()
        
        if restock_data.get('status') == 'success':
            for product in restock_data.get('predictions', []):
                if product['urgency'] == 'CRITICAL':
                    alerts.append({
                        'id': len(alerts) + 1,
                        'type': 'LOW_STOCK',
                        'severity': 'HIGH',
                        'severity_level': 1,
                        'icon': '🔴',
                        'title': f'Critical Low Stock: {product["product_name"]}',
                        'message': f'Only {product["current_stock"]} units left. Will run out in {product["days_until_out"]} days!',
                        'action': product['action'],
                        'recommendation': f'Order {product["recommended_restock_qty"]} units from {product["supplier_name"]}',
                        'product_id': product['product_id'],
                        'timestamp': datetime.now().isoformat(),
                        'resolved': False
                    })
                elif product['urgency'] == 'HIGH':
                    alerts.append({
                        'id': len(alerts) + 1,
                        'type': 'LOW_STOCK',
                        'severity': 'MEDIUM',
                        'severity_level': 2,
                        'icon': '🟠',
                        'title': f'Low Stock Alert: {product["product_name"]}',
                        'message': f'Only {product["current_stock"]} units left. Will run out in {product["days_until_out"]} days.',
                        'action': product['action'],
                        'recommendation': f'Consider ordering {product["recommended_restock_qty"]} units',
                        'product_id': product['product_id'],
                        'timestamp': datetime.now().isoformat(),
                        'resolved': False
                    })
        
        # ==================================================
        # 2. OVERSTOCK ALERTS (inventory > reorder_level * 3)
        # ==================================================
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, i.quantity, i.reorder_level, s.name as supplier_name
            FROM inventory i
            JOIN products p ON i.product_id = p.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE i.quantity > i.reorder_level * 3
            ORDER BY i.quantity DESC
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            alerts.append({
                'id': len(alerts) + 1,
                'type': 'OVERSTOCK',
                'severity': 'MEDIUM',
                'severity_level': 2,
                'icon': '📦',
                'title': f'Overstock: {row[1]}',
                'message': f'Current stock: {row[2]} units. Reorder level is only {row[3]}.',
                'action': 'Consider running a promotion or discount',
                'recommendation': f'Reduce price by 10-15% to move excess inventory',
                'product_id': row[0],
                'timestamp': datetime.now().isoformat(),
                'resolved': False
            })
        cursor.close()
        
        # ==================================================
        # 3. SALES DROP DETECTION
        # ==================================================
        
        # Get last 7 days vs previous 7 days sales
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN sale_date >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN total_amount ELSE 0 END) as recent_week,
                SUM(CASE WHEN sale_date BETWEEN DATE_SUB(NOW(), INTERVAL 14 DAY) AND DATE_SUB(NOW(), INTERVAL 7 DAY) THEN total_amount ELSE 0 END) as previous_week
            FROM sales
        """)
        
        row = cursor.fetchone()
        recent_week = row[0] or 0
        previous_week = row[1] or 0
        
        if previous_week > 0:
            drop_percentage = ((previous_week - recent_week) / previous_week) * 100
            
            if drop_percentage > 30:
                alerts.append({
                    'id': len(alerts) + 1,
                    'type': 'SALES_DROP',
                    'severity': 'HIGH',
                    'severity_level': 1,
                    'icon': '📉',
                    'title': 'Significant Sales Drop Detected!',
                    'message': f'Sales dropped by {drop_percentage:.0f}% compared to last week.',
                    'action': 'Review marketing campaigns and check for issues',
                    'recommendation': 'Consider running a promotion or investigating customer feedback',
                    'product_id': None,
                    'timestamp': datetime.now().isoformat(),
                    'resolved': False
                })
            elif drop_percentage > 15:
                alerts.append({
                    'id': len(alerts) + 1,
                    'type': 'SALES_DROP',
                    'severity': 'MEDIUM',
                    'severity_level': 2,
                    'icon': '📉',
                    'title': 'Sales Drop Detected',
                    'message': f'Sales dropped by {drop_percentage:.0f}% compared to last week.',
                    'action': 'Monitor sales closely',
                    'recommendation': 'Check inventory availability and competitor pricing',
                    'product_id': None,
                    'timestamp': datetime.now().isoformat(),
                    'resolved': False
                })
        
        # ==================================================
        # 4. EXPIRING PRODUCTS (from product_expiry table)
        # ==================================================
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pe.product_id, p.name, pe.expiry_date, pe.quantity
            FROM product_expiry pe
            JOIN products p ON pe.product_id = p.id
            WHERE pe.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            ORDER BY pe.expiry_date
        """)
        
        for row in cursor.fetchall():
            days_left = (row[2] - datetime.now().date()).days
            if days_left <= 7:
                severity = "HIGH"
                level = 1
                icon = "⚠️"
            elif days_left <= 30:
                severity = "MEDIUM"
                level = 2
                icon = "📅"
            else:
                severity = "LOW"
                level = 3
                icon = "ℹ️"
            
            alerts.append({
                'id': len(alerts) + 1,
                'type': 'EXPIRING_PRODUCT',
                'severity': severity,
                'severity_level': level,
                'icon': icon,
                'title': f'Product Expiring Soon: {row[1]}',
                'message': f'{row[3]} units expiring on {row[2]} ({days_left} days left)',
                'action': 'Run clearance sale immediately',
                'recommendation': f'Offer {row[3]} units at 30-50% discount',
                'product_id': row[0],
                'timestamp': datetime.now().isoformat(),
                'resolved': False
            })
        cursor.close()
        conn.close()
        
        # ==================================================
        # 5. DEAD STOCK ALERTS (from product movement)
        # ==================================================
        
        movement_resp = product_movement()
        if isinstance(movement_resp, tuple):
            movement_data = movement_resp[0].get_json()
        else:
            movement_data = movement_resp.get_json()
        
        if movement_data.get('status') == 'success':
            for product in movement_data.get('products', []):
                if product['movement'] == 'DEAD STOCK' and product['current_stock'] > 0:
                    alerts.append({
                        'id': len(alerts) + 1,
                        'type': 'DEAD_STOCK',
                        'severity': 'MEDIUM',
                        'severity_level': 2,
                        'icon': '💀',
                        'title': f'Dead Stock Detected: {product["product_name"]}',
                        'message': f'No sales recorded. {product["current_stock"]} units in stock.',
                        'action': product['action'],
                        'recommendation': product['recommendation'],
                        'product_id': product['product_id'],
                        'timestamp': datetime.now().isoformat(),
                        'resolved': False
                    })
        
        # Sort alerts by severity (highest first)
        alerts.sort(key=lambda x: x['severity_level'])
        
        # Summary statistics
        summary = {
            'total_alerts': len(alerts),
            'high_severity': len([a for a in alerts if a['severity'] == 'HIGH']),
            'medium_severity': len([a for a in alerts if a['severity'] == 'MEDIUM']),
            'low_severity': len([a for a in alerts if a['severity'] == 'LOW']),
            'by_type': {
                'LOW_STOCK': len([a for a in alerts if a['type'] == 'LOW_STOCK']),
                'OVERSTOCK': len([a for a in alerts if a['type'] == 'OVERSTOCK']),
                'SALES_DROP': len([a for a in alerts if a['type'] == 'SALES_DROP']),
                'EXPIRING_PRODUCT': len([a for a in alerts if a['type'] == 'EXPIRING_PRODUCT']),
                'DEAD_STOCK': len([a for a in alerts if a['type'] == 'DEAD_STOCK'])
            }
        }
        
        return jsonify({
            'status': 'success',
            'alerts': alerts,
            'summary': summary,
            'count': len(alerts),
            'message': 'Intelligent alerts generated successfully'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/resolve/<int:alert_id>', methods=['POST', 'PUT', 'GET'])
def resolve_alert(alert_id):
    """Mark an alert as resolved"""
    return jsonify({
        'status': 'success',
        'message': f'Alert {alert_id} marked as resolved',
        'alert_id': alert_id,
        'resolved_at': datetime.now().isoformat()
    })
    


@app.route('/api/alerts/summary', methods=['GET'])
def alerts_summary():
    """Get summary of all alerts"""
    alerts_resp = get_alerts()
    if isinstance(alerts_resp, tuple):
        data = alerts_resp[0].get_json()
    else:
        data = alerts_resp.get_json()
    
    if data.get('status') == 'success':
        return jsonify({
            'status': 'success',
            'summary': data.get('summary'),
            'recommendations': {
                'immediate_action_needed': data['summary']['high_severity'] > 0,
                'priority_message': f"You have {data['summary']['high_severity']} critical alerts requiring immediate attention!"
            }
        })
    return alerts_resp


# ======================================================
# MAIN ENTRY POINT
# ======================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Smart Inventory AI API - Complete")
    print("=" * 60)
    
    load_restock_model()
    
    print("\n📍 Server: http://localhost:5000")
    print("\n📋 Endpoints:")
    print("   GET /api/health")
    print("   GET /api/test-db")
    print("   GET /api/flask-products")
    print("   GET /api/restock-prediction  (Day 9)")
    print("   GET /api/product-movement    (Day 10)")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)