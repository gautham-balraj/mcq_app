import sqlite3

db_path = "/Users/gauthambalraj/Dev/mcq_app/mcq_app/qbank.db"

conn = sqlite3.connect(db_path)

try:
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE questions
        SET status = 'verified'
        WHERE chapter = 1
          AND review_note IS NULL;
    """)

    conn.commit()

    print(f"Updated {cursor.rowcount} rows.")

finally:
    conn.close()