"""
One-time migration: add DetailedCategories."IsHidden" (INTEGER NOT NULL DEFAULT 0).

Hidden categories keep their assets and history but are filtered out of the asset
listings and category pickers - see the Show / Hide tab of the category manager.

Run from the backend root:

python scripts/migrate_add_detailed_category_is_hidden.py

Uses the same database URL as the app (PostgreSQL via the DB_* env vars). The API
also applies this on startup; this script exists so the column can be added without
restarting. Idempotent: running it multiple times is safe.
"""

import os
import sys

# Allow `python scripts/migrate_add_detailed_category_is_hidden.py` from the backend root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect  # noqa: E402

from app.database import engine, ensure_detailed_category_visibility_column  # noqa: E402


def main():
    inspector = inspect(engine)
    print(f'Database : {engine.url.render_as_string(hide_password=True)}')
    print(f'Dialect  : {engine.dialect.name}')

    if not inspector.has_table('DetailedCategories'):
        print('Table "DetailedCategories" does not exist yet - start the API once so it is created.')
        return

    added = ensure_detailed_category_visibility_column()
    if added:
        print('Added column "IsHidden" to "DetailedCategories" (existing rows default to 0 = visible).')
    else:
        print('Column "IsHidden" already present - nothing to do.')

    columns = {column['name']: column for column in inspect(engine).get_columns('DetailedCategories')}
    is_hidden = columns.get('IsHidden')
    if is_hidden is None:
        print('WARNING: "IsHidden" is still missing after the migration.')
        return

    print(f'Verified : IsHidden {is_hidden["type"]} nullable={is_hidden["nullable"]} default={is_hidden.get("default")}')

    with engine.connect() as conn:
        hidden, total = conn.exec_driver_sql(
            'SELECT COALESCE(SUM(CASE WHEN "IsHidden" = 1 THEN 1 ELSE 0 END), 0), COUNT(*) '
            'FROM "DetailedCategories" WHERE "IsDeleted" = 0'
        ).one()
    print(f'Categories: {total} active, {hidden} hidden.')


if __name__ == '__main__':
    main()
