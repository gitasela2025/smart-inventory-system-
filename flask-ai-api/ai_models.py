"""
DAY 9: Smart Restock Prediction AI Models - SIMPLE VERSION
"""

import pandas as pd
import numpy as np
import mysql.connector
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

# Database configuration - CHANGE YOUR PASSWORD
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin123',  # 🔴 CHANGE THIS to your MySQL password
    'database': 'smart_inventory'
}

def get_data():
    """Get sales and inventory data"""
    conn = mysql.connector.connect(**DB_CONFIG)
    
    query = """
        SELECT 
            p.id as product_id,
            p.name as product_name,
            i.quantity as stock,
            i.reorder_level,
            SUM(si.quantity) as total_sold,
            COUNT(DISTINCT s.id) as sale_count
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
    
    # Calculate daily sales (assuming 30 days of data)
    df['daily_sales'] = df['total_sold'] / 30
    
    # Calculate days until out of stock
    df['days_until_out'] = df['stock'] / df['daily_sales'].replace(0, 0.01)
    
    # Clean data
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    
    return df

def train_model(data):
    """Train the model"""
    
    # Features (X) and Target (y)
    X = data[['stock', 'daily_sales', 'reorder_level', 'total_sold']]
    y = data['days_until_out']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train models
    models = {
        'Linear Regression': LinearRegression(),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
        'Decision Tree': DecisionTreeRegressor(random_state=42)
    }
    
    best_model = None
    best_score = -999
    
    print("\n" + "="*50)
    print("MODEL TRAINING RESULTS")
    print("="*50)
    
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        
        print(f"\n{name}:")
        print(f"  R² Score: {r2:.4f}")
        print(f"  MAE: {mae:.2f} days")
        print(f"  RMSE: {rmse:.2f} days")
        
        if r2 > best_score:
            best_score = r2
            best_model = model
    
    print("\n" + "="*50)
    print(f"BEST MODEL: {best_model.__class__.__name__}")
    print(f"R² Score: {best_score:.4f}")
    print("="*50)
    
    return best_model

def main():
    print("="*50)
    print("SMART RESTOCK PREDICTION - TRAINING")
    print("="*50)
    
    # Get data
    print("\n1. Loading data...")
    data = get_data()
    print(f"   Loaded {len(data)} products")
    
    if len(data) == 0:
        print("   ERROR: No data found!")
        return
    
    # Train model
    print("\n2. Training models...")
    best_model = train_model(data)
    
    # Save model
    print("\n3. Saving model...")
    os.makedirs('models', exist_ok=True)
    joblib.dump(best_model, 'models/restock_model.pkl')
    print("   ✅ Model saved to models/restock_model.pkl")
    
    print("\n✅ TRAINING COMPLETE!")
    print("\nNow run: python app.py")

if __name__ == "__main__":
    main()