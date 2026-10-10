
import sqlite3

connection = sqlite3.connect("fulfillment.db")

connection.execute("""
CREATE TABLE IF NOT EXISTS test (
    id INTEGER PRIMARY KEY,
    message TEXT
)
""")

connection.execute(
    "INSERT INTO test (message) VALUES (?)",
    ("Database is working!",)
)

connection.commit()
connection.close()

print("Database created successfully!")
