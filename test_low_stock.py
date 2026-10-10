
import sqlite3

conn = sqlite3.connect("fulfillment.db")

conn.execute("""
    UPDATE inventory
    SET available_stock = 3
    WHERE sku = 'SKU001'
""")

conn.commit()

result = conn.execute("""
    SELECT sku, product, available_stock, reorder_level
    FROM inventory
    WHERE sku = 'SKU001'
""").fetchone()

print("Updated inventory:", result)

conn.close()
