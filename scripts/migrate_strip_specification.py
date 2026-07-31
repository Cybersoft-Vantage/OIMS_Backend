"""
One-time migration: strip `specification` property from DetailedCategory.CustomSchema JSON arrays.
Run from the backend root:

python scripts/migrate_strip_specification.py

This script uses the same database URL as the app (reads env or default sqlite).
It is idempotent: running it multiple times is safe.
"""

import json
import sys
from app import models
from app.database import SessionLocal


def main():
    db = SessionLocal()
    try:
        rows = db.query(models.DetailedCategory).all()
        changed = 0
        total = 0
        for r in rows:
            total += 1
            cs = r.CustomSchema
            if not cs:
                continue
            try:
                parsed = json.loads(cs)
            except Exception:
                print(f"Skipping id={r.DetailedCategoryId}: CustomSchema not valid JSON")
                continue
            if not isinstance(parsed, list):
                continue
            modified = False
            new_list = []
            for item in parsed:
                if isinstance(item, dict) and 'specification' in item:
                    modified = True
                    item = {k: v for k, v in item.items() if k != 'specification'}
                new_list.append(item)
            if modified:
                r.CustomSchema = json.dumps(new_list, ensure_ascii=False)
                db.add(r)
                changed += 1
                print(f"Updated DetailedCategoryId={r.DetailedCategoryId}")
        if changed:
            db.commit()
        print(f"Processed {total} categories, updated {changed} entries.")
    finally:
        db.close()


if __name__ == '__main__':
    main()
