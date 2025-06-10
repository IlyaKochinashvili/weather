import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "weather.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS temperatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            temperature REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_day ON temperatures (timestamp)")
        conn.commit()

if __name__ == "__main__":
    init_db()
