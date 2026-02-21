#!/usr/bin/env python3
"""
Seed Supabase with synthetic private_employee_records data.

Creates the table (if not exists) via Supabase SQL and inserts
20 deterministic rows using rng_seed=42.

Usage:
    python seed_supabase.py [--rows 20] [--seed 42]

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in .env or environment.
"""
import os
import sys
import argparse
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv
load_dotenv()

try:
    from supabase import create_client
except ImportError:
    print("supabase required: pip install supabase")
    sys.exit(1)


DEPARTMENTS = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations", "Legal", "Support"]
SALARY_BANDS = ["L1", "L2", "L3", "L4", "L5", "L6"]
STATUSES = ["active", "active", "active", "active", "on_leave"]  # 80% active


def generate_rows(n: int, seed: int) -> list:
    rng = random.Random(seed)
    rows = []
    base_date = date(2020, 1, 1)
    for i in range(1, n + 1):
        emp_id = f"EMP-{i:04d}"
        dept = rng.choice(DEPARTMENTS)
        band = rng.choice(SALARY_BANDS)
        days_offset = rng.randint(0, 1500)
        hire = base_date + timedelta(days=days_offset)
        status = rng.choice(STATUSES)
        rows.append({
            "employee_id": emp_id,
            "department": dept,
            "salary_band": band,
            "hire_date": hire.isoformat(),
            "status": status,
        })
    return rows


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS private_employee_records (
    id SERIAL PRIMARY KEY,
    employee_id TEXT NOT NULL,
    department TEXT NOT NULL,
    salary_band TEXT NOT NULL,
    hire_date DATE NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


def main():
    ap = argparse.ArgumentParser(description="Seed Supabase private_employee_records")
    ap.add_argument("--rows", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--clear", action="store_true", help="Delete existing rows before seeding")
    args = ap.parse_args()

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env or environment")
        return 1

    sb = create_client(url, key)

    # Note: table creation via SQL requires the Supabase SQL Editor or
    # a migration tool. The supabase-py client doesn't support raw DDL.
    # Run CREATE_TABLE_SQL in Supabase SQL Editor if the table doesn't exist.
    print(f"Ensure table exists (run in Supabase SQL Editor if needed):")
    print(CREATE_TABLE_SQL)

    if args.clear:
        print("Clearing existing rows...")
        sb.table("private_employee_records").delete().neq("id", 0).execute()

    rows = generate_rows(args.rows, args.seed)
    print(f"Inserting {len(rows)} rows (seed={args.seed})...")

    response = sb.table("private_employee_records").insert(rows).execute()
    print(f"Inserted {len(response.data)} rows successfully.")

    # Verify
    count = sb.table("private_employee_records").select("id", count="exact").execute()
    print(f"Total rows in table: {count.count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
