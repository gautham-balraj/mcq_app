"""Create the SQLite database and tables.

Usage (from anywhere):
    python scripts/create_db.py            # create tables if missing (safe to re-run)
    python scripts/create_db.py --reset    # delete the DB file first (destroys all questions; reload with load_data.py)
"""
import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Path(__file__).with_name("schema.sql")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(ROOT / "qbank.db"), help="path to the SQLite file")
    ap.add_argument("--reset", action="store_true", help="delete the existing DB file first")
    args = ap.parse_args()

    db = Path(args.db)
    if args.reset and db.exists():
        db.unlink()
        print(f"Deleted {db}")

    con = sqlite3.connect(db)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.commit()

    tables = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    print(f"DB:     {db}")
    print(f"Tables: {', '.join(tables)}")
    con.close()


if __name__ == "__main__":
    main()
