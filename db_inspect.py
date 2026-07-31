import sqlite3
import os
from pathlib import Path

DB_FILE = Path(__file__).parent / 'oims_2.db'


def main():
    if not DB_FILE.exists():
        print(f'ERROR: Database file not found: {DB_FILE}')
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    print(f'Database: {DB_FILE}\n')
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cur.fetchall()]
    print('Tables:')
    for table in tables:
        print(f'  - {table}')

    print('\nCounts:')
    for table in tables:
        try:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            count = cur.fetchone()[0]
            print(f'  {table}: {count}')
        except sqlite3.Error as e:
            print(f'  {table}: ERROR ({e})')

    if 'users' in tables:
        print('\nUsers:')
        try:
            cur.execute('SELECT id, username, email, role, is_active FROM users')
            for row in cur.fetchall():
                print('  ', row)
        except sqlite3.Error as e:
            print('  users: ERROR', e)

    conn.close()


if __name__ == '__main__':
    main()
