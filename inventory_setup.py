
import sqlite3

conn = sqlite3.connect("fulfillment.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    sku TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    variant TEXT,
    available_stock INTEGER NOT NULL DEFAULT 0,
    reorder_level INTEGER NOT NULL DEFAULT 5
)
""")

products = [
    ("SKU001", "Wireless Mouse", "Black", 25, 5),
    ("SKU002", "Keyboard", "White", 18, 5),
    ("SKU003", "Laptop Stand", "Silver", 12, 4),
    ("SKU004", "USB Hub", "Grey", 30, 8),
    ("SKU005", "Headphones", "Black", 15, 5),
    ("SKU006", "Webcam", "Black", 10, 3),
    ("SKU007", "USB Cable", "White", 40, 10),
    ("SKU008", "Phone Stand", "Blue", 20, 5),
]

conn.executemany("""
INSERT OR IGNORE INTO inventory
(sku, product, variant, available_stock, reorder_level)
VALUES (?, ?, ?, ?, ?)
""", products)

conn.commit()

rows = conn.execute("""
SELECT sku, product, available_stock, reorder_level
FROM inventory
ORDER BY sku
""").fetchall()

print("Inventory table created successfully!")
for row in rows:
    print(row)

conn.close()
