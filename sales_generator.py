#!/usr/bin/env python3
"""
DAY 3: Smart Inventory System - Sales Data Generator
Generates 1000+ realistic sales records for AI/ML training
"""

import mysql.connector
from mysql.connector import Error
import random
from datetime import datetime, timedelta
from faker import Faker
import pandas as pd

# Initialize Faker for realistic data
fake = Faker()

# ======================================================
# DATABASE CONFIGURATION
# ======================================================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin123',  # Change to your MySQL password
    'database': 'smart_inventory'
}

# ======================================================
# CONFIGURATION
# ======================================================
NUM_SALES = 1000  # Minimum number of sales to generate
MIN_ITEMS_PER_SALE = 1
MAX_ITEMS_PER_SALE = 8
START_DATE = datetime(2025, 11, 1)  # Last 6 months
END_DATE = datetime(2026, 5, 23)    # Today

# Payment modes
PAYMENT_MODES = ['CASH', 'CARD', 'ONLINE']
PAYMENT_WEIGHTS = [0.3, 0.5, 0.2]  # 30% Cash, 50% Card, 20% Online

# ======================================================
# DATABASE CONNECTION
# ======================================================

def get_db_connection():
    """Create database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_products(cursor):
    """Fetch all active products with their current prices"""
    cursor.execute("""
        SELECT p.id, p.unit_price, p.name, i.quantity as stock
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        WHERE p.is_active = TRUE
    """)
    return cursor.fetchall()

def get_users(cursor):
    """Fetch all staff users who can process sales"""
    cursor.execute("SELECT id FROM users WHERE role IN ('ADMIN', 'STAFF')")
    return [row[0] for row in cursor.fetchall()]

# ======================================================
# DATA GENERATION FUNCTIONS
# ======================================================

def random_date_between(start_date, end_date):
    """Generate random date between two dates"""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    return start_date + timedelta(days=random_days)

def generate_sale_items(products, num_items):
    selected_products = random.sample(products, min(num_items, len(products)))
    items = []
    
    for product in selected_products:
        quantity = random.randint(1, 5)
        discount = random.choice([0, 0, 0, 0.05, 0.10])
        # Convert Decimal to float first, then calculate
        original_price = float(product[1])  # Convert Decimal to float
        unit_price = original_price * (1 - discount)
        
        items.append({
            'product_id': product[0],
            'quantity': quantity,
            'unit_price': round(unit_price, 2),
            'subtotal': round(quantity * unit_price, 2)
        })
    
    return items

def generate_sales_data(products, users, num_sales):
    """Generate all sales data"""
    sales = []
    sale_items = []
    
    print(f"Generating {num_sales} sales records...")
    
    for i in range(num_sales):
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1}/{num_sales} sales...")
        
        # Random sale date (more recent sales have higher probability)
        if random.random() < 0.6:  # 60% of sales in last 3 months
            sale_date = random_date_between(
                datetime(2026, 2, 1), END_DATE
            )
        else:  # 40% of sales in earlier period
            sale_date = random_date_between(START_DATE, datetime(2026, 1, 31))
        
        # Random time during business hours (9 AM - 8 PM)
        sale_date = sale_date.replace(
            hour=random.randint(9, 20),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        
        # Random user (staff member)
        user_id = random.choice(users)
        
        # Random payment mode with weights
        payment_mode = random.choices(PAYMENT_MODES, weights=PAYMENT_WEIGHTS)[0]
        
        # Generate items for this sale
        num_items = random.randint(MIN_ITEMS_PER_SALE, MAX_ITEMS_PER_SALE)
        items = generate_sale_items(products, num_items)
        
        # Calculate total
        total_amount = sum(item['subtotal'] for item in items)
        
        # Create sale record
        sale = {
            'user_id': user_id,
            'sale_date': sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            'total_amount': round(total_amount, 2),
            'payment_mode': payment_mode,
            'notes': fake.sentence() if random.random() < 0.2 else None  # 20% have notes
        }
        
        sales.append(sale)
        
        # Store sale items (sale_id will be assigned after insertion)
        for item in items:
            item['sale_index'] = i  # Temporary reference
            sale_items.append(item)
    
    return sales, sale_items

# ======================================================
# DATABASE INSERTION FUNCTIONS
# ======================================================

def insert_sales_and_items(conn, sales, sale_items):
    """Insert sales and items into database"""
    cursor = conn.cursor()
    
    try:
        # Insert sales one by one to get IDs
        insert_sale_query = """
            INSERT INTO sales (user_id, sale_date, total_amount, payment_mode, notes)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        insert_item_query = """
            INSERT INTO sale_items (sale_id, product_id, quantity, unit_price_at_sale)
            VALUES (%s, %s, %s, %s)
        """
        
        print("Inserting sales into database...")
        
        for idx, sale in enumerate(sales):
            cursor.execute(insert_sale_query, (
                sale['user_id'],
                sale['sale_date'],
                sale['total_amount'],
                sale['payment_mode'],
                sale['notes']
            ))
            
            # Get the generated sale_id
            sale_id = cursor.lastrowid
            
            # Insert items for this sale
            items_for_sale = [item for item in sale_items if item.get('sale_index') == idx]
            for item in items_for_sale:
                cursor.execute(insert_item_query, (
                    sale_id,
                    item['product_id'],
                    item['quantity'],
                    item['unit_price']
                ))
            
            # Commit every 100 sales to avoid memory issues
            if (idx + 1) % 100 == 0:
                conn.commit()
                print(f"  Committed {idx + 1} sales to database")
        
        conn.commit()
        print(f"✅ Successfully inserted {len(sales)} sales with {len(sale_items)} items")
        
    except Error as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
        return False
    
    finally:
        cursor.close()
    
    return True

def update_inventory_after_sales(conn):
    """Update inventory quantities based on sales"""
    cursor = conn.cursor()
    
    try:
        print("Updating inventory quantities...")
        
        # This query subtracts sold quantities from inventory
        cursor.execute("""
            UPDATE inventory i
            JOIN (
                SELECT product_id, SUM(quantity) as sold_quantity
                FROM sale_items
                GROUP BY product_id
            ) s ON i.product_id = s.product_id
            SET i.quantity = GREATEST(i.quantity - s.sold_quantity, 0)
        """)
        
        conn.commit()
        print("✅ Inventory updated successfully")
        
    except Error as e:
        print(f"Error updating inventory: {e}")
        conn.rollback()
    
    finally:
        cursor.close()

# ======================================================
# VERIFICATION FUNCTIONS
# ======================================================

def verify_data(conn):
    """Verify the generated data"""
    cursor = conn.cursor()
    
    print("\n" + "="*50)
    print("DATA VERIFICATION")
    print("="*50)
    
    # Total sales
    cursor.execute("SELECT COUNT(*) FROM sales")
    total_sales = cursor.fetchone()[0]
    print(f"Total Sales: {total_sales}")
    
    # Total sale items
    cursor.execute("SELECT COUNT(*) FROM sale_items")
    total_items = cursor.fetchone()[0]
    print(f"Total Sale Items: {total_items}")
    
    # Sales by month
    cursor.execute("""
        SELECT DATE_FORMAT(sale_date, '%Y-%m') as month, 
               COUNT(*) as sales_count,
               SUM(total_amount) as total_revenue
        FROM sales
        GROUP BY DATE_FORMAT(sale_date, '%Y-%m')
        ORDER BY month DESC
    """)
    
    print("\nSales by Month:")
    print("-" * 50)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} sales (${row[2]:,.2f})")
    
    # Top 10 products
    cursor.execute("""
        SELECT p.name, SUM(si.quantity) as total_sold, 
               SUM(si.subtotal) as total_revenue
        FROM sale_items si
        JOIN products p ON si.product_id = p.id
        GROUP BY p.id
        ORDER BY total_sold DESC
        LIMIT 10
    """)
    
    print("\nTop 10 Best Selling Products:")
    print("-" * 50)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} units sold (${row[2]:,.2f})")
    
    # Payment mode distribution
    cursor.execute("""
        SELECT payment_mode, COUNT(*) as count, SUM(total_amount) as total
        FROM sales
        GROUP BY payment_mode
    """)
    
    print("\nPayment Mode Distribution:")
    print("-" * 50)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} sales (${row[2]:,.2f})")
    
    cursor.close()

# ======================================================
# EXPORT TO CSV (Optional)
# ======================================================

def export_to_csv(sales, sale_items, products):
    """Export generated data to CSV for backup"""
    print("\nExporting data to CSV...")
    
    # Convert to DataFrames
    sales_df = pd.DataFrame(sales)
    sales_df.to_csv('generated_sales.csv', index=False)
    
    # Create items DataFrame with product names
    items_df = pd.DataFrame(sale_items)
    items_df.to_csv('generated_sale_items.csv', index=False)
    
    print("✅ Exported to generated_sales.csv and generated_sale_items.csv")

# ======================================================
# MAIN EXECUTION
# ======================================================

def main():
    print("="*60)
    print("DAY 3: Smart Inventory System - Sales Data Generator")
    print("="*60)
    
    # Connect to database
    print("\n📡 Connecting to MySQL database...")
    conn = get_db_connection()
    
    if not conn:
        print("❌ Failed to connect to database. Please check your settings.")
        return
    
    cursor = conn.cursor()
    
    try:
        # Get existing data
        print("📦 Fetching products from database...")
        products = get_products(cursor)
        print(f"   Found {len(products)} active products")
        
        users = get_users(cursor)
        print(f"   Found {len(users)} staff users")
        
        if len(products) == 0:
            print("❌ No products found. Please run Day 2 SQL setup first.")
            return
        
        # Generate sales data
        print(f"\n🎲 Generating {NUM_SALES}+ sales records...")
        sales, sale_items = generate_sales_data(products, users, NUM_SALES)
        
        # Insert into database
        print("\n💾 Inserting data into database...")
        if insert_sales_and_items(conn, sales, sale_items):
            # Update inventory
            update_inventory_after_sales(conn)
            
            # Verify data
            verify_data(conn)
            
            # Optional: Export to CSV
            export_to_csv(sales, sale_items, products)
            
            print("\n" + "="*60)
            print("✅ DAY 3 COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\nYou now have:")
            print(f"  - {len(sales)} sales records")
            print(f"  - {len(sale_items)} sale items")
            print("\nReady for Day 4: JWT Authentication!")
        else:
            print("❌ Failed to insert data")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Database connection closed.")

if __name__ == "__main__":
    main()