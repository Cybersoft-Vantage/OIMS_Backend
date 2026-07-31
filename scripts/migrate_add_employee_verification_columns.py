"""
One-time migration to add login verification columns to EmployeeDetail.

Run from the backend root:

python scripts/migrate_add_employee_verification_columns.py
"""

import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import DATABASE_URL, engine


EMPLOYEE_DETAIL_COLUMNS = [
    ('"ProfileImage"', 'TEXT'),
    ('"Verify"', 'INTEGER NOT NULL DEFAULT 0'),
    ('"EmailVerifiedAt"', 'TIMESTAMP NULL'),
    ('"VerificationOtpHash"', 'VARCHAR(128) NULL'),
    ('"VerificationOtpExpiresAt"', 'TIMESTAMP NULL'),
    ('"VerificationOtpAttempts"', 'INTEGER NOT NULL DEFAULT 0'),
    ('"VerificationOtpSentAt"', 'TIMESTAMP NULL'),
]


def main() -> None:
    print(f"Using database: {DATABASE_URL}")
    with engine.begin() as conn:
        for column_name, column_ddl in EMPLOYEE_DETAIL_COLUMNS:
            statement = f'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS {column_name} {column_ddl}'
            conn.execute(text(statement))
            print(f"Checked {column_name}")

    print("EmployeeDetail verification columns are up to date.")


if __name__ == "__main__":
    main()