
import logging
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env if present
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))

# Prefer explicit DATABASE_URL. If not set, attempt to build one from DB_* env vars.
# Build PostgreSQL connection URL strictly from DB_* environment variables.
# This removes fallback to sqlite and ensures the app connects to Postgres.
# db_host = os.getenv('DB_HOST')
# db_port = os.getenv('DB_PORT') or '5432'
# db_name = os.getenv('DB_NAME')
# db_user = os.getenv('DB_USERNAME')
# db_pass = os.getenv('DB_PASSWORD')

# if not (db_host and db_name and db_user):
#     raise RuntimeError(
#         'Database configuration missing: please set DB_HOST, DB_NAME, and DB_USERNAME in .env or environment'
#     )

# DATABASE_URL = f"postgresql://{db_user}:{db_pass or ''}@{db_host}:{db_port}/{db_name}"

# Ensure directory exists for sqlite file
# No sqlite fallback: we expect Postgres for local development per env settings.

# For Postgres use default connect args
connect_args = {}



# Only use DATABASE_URL for database configuration. use this in prod only 
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
if not DATABASE_URL:
    raise ValueError('DATABASE_URL is required. Set it in .env or your environment.')

connect_args = {} if not DATABASE_URL.startswith('sqlite') else {"check_same_thread": False, "timeout": 30}
# Use NullPool for SQLite file DBs to avoid connection pooling across threads/processes
pool_kwargs = {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, **pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_detailed_category_visibility_column() -> bool:
    """Ensure DetailedCategories."IsHidden" exists.

    Runs in its own transaction on purpose: the bulk column patch-up below shares one
    transaction and swallows OperationalError/ProgrammingError, so on PostgreSQL a
    single unrelated failure aborts that transaction and would silently roll this
    column back. The category show/hide feature does not work without it.

    Returns True when the column was added, False when it was already present.
    Idempotent - safe to call on every startup.
    """
    inspector = inspect(engine)
    if not inspector.has_table("DetailedCategories"):
        # Fresh database: startup create_all() builds the table with the column.
        return False

    existing_columns = {column["name"] for column in inspector.get_columns("DetailedCategories")}
    if "IsHidden" in existing_columns:
        return False

    column_type = "INTEGER NOT NULL DEFAULT 0"
    with engine.begin() as conn:
        conn.execute(text(f'ALTER TABLE "DetailedCategories" ADD COLUMN "IsHidden" {column_type}'))
    return True


def ensure_soft_delete_columns() -> None:
    """Ensure soft-delete columns exist for existing databases."""
    try:
        if ensure_detailed_category_visibility_column():
            logger.info('Added DetailedCategories."IsHidden" column')
    except (OperationalError, ProgrammingError):
        logger.exception('Unable to add DetailedCategories."IsHidden" column')

    with engine.begin() as conn:
        dialect = engine.dialect.name
        inspector = inspect(conn)

        if dialect == "sqlite":
            for table_name, columns_to_add in {
                "Categories": [("IsDeleted", "INTEGER NOT NULL DEFAULT 0"), ("DeletedAt", "DATETIME")],
                "SubCategories": [("IsDeleted", "INTEGER NOT NULL DEFAULT 0"), ("DeletedAt", "DATETIME")],
                "AssetStatus": [("IsDeleted", "INTEGER NOT NULL DEFAULT 0"), ("DeletedAt", "DATETIME")],
                "Assets": [("IsDeleted", "INTEGER NOT NULL DEFAULT 0"), ("DeletedAt", "DATETIME")],
                "AssetComponents": [("IsDeleted", "INTEGER NOT NULL DEFAULT 0"), ("DeletedAt", "DATETIME")],
                "AssetHistory": [("AssetCode", "TEXT"), ("AssetName", "TEXT"), ("EmployeeName", "TEXT")],
                "EmployeeDetail": [("Role", "TEXT DEFAULT 'employee'"), ("ProfileImage", "TEXT")],
                "DetailedAssetAssignments": [("ReturnedBy", "TEXT")],
                "DetailedAssets": [("SoldPrice", "REAL")],
            }.items():
                if not inspector.has_table(table_name):
                    continue

                existing_columns = {
                    row[1]
                    for row in conn.execute(text(f"PRAGMA table_info([{table_name}])")).fetchall()
                }
                for column_name, column_type in columns_to_add:
                    if column_name not in existing_columns:
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))

            if inspector.has_table("EmployeeDetail"):
                existing_columns = {
                    row[1]
                    for row in conn.execute(text('PRAGMA table_info([EmployeeDetail])')).fetchall()
                }
                if "PasswordHash" not in existing_columns:
                    conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN "PasswordHash" TEXT'))
        else:
            # Add missing EmployeeDetail columns for non-sqlite DBs, like Postgres.
            try:
                conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "ProfileImage" TEXT'))
                conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "PasswordHash" VARCHAR(255) NULL'))
                conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "Verify" INTEGER NOT NULL DEFAULT 0'))
                conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "EmailVerifiedAt" TIMESTAMP NULL'))
                conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "VerificationOtpHash" VARCHAR(128) NULL'))
                conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "VerificationOtpExpiresAt" TIMESTAMP NULL'))
                conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "VerificationOtpAttempts" INTEGER NOT NULL DEFAULT 0'))
                conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "VerificationOtpSentAt" TIMESTAMP NULL'))
                conn.execute(text('ALTER TABLE "DetailedCategories" ADD COLUMN IF NOT EXISTS "SubcategoryTagName" VARCHAR(20) NULL'))
                conn.execute(text('ALTER TABLE "DetailedAssets" ADD COLUMN IF NOT EXISTS "SoldPrice" DOUBLE PRECISION NULL'))

                # One-time compatibility backfill: migrate password hashes from legacy users table.
                if inspector.has_table("users"):
                    conn.execute(text(
                        'UPDATE "EmployeeDetail" e '
                        'SET "PasswordHash" = u.hashed_password '
                        'FROM users u '
                        'WHERE e."PasswordHash" IS NULL AND u.username = e."UserId"'
                    ))
            except (OperationalError, ProgrammingError):
                # If EmployeeDetail is not present yet, startup create_all will handle it.
                pass

        # Backfill history snapshot columns for already existing rows so history still shows details.
        # Skip if the history table or its related tables are not present yet.
        if not inspector.has_table("AssetHistory") or not inspector.has_table("Assets") or not inspector.has_table("EmployeeDetail"):
            return

        try:
            rows = conn.execute(text("SELECT HistoryId, AssetId, EmployeeId FROM AssetHistory")).fetchall()
        except (OperationalError, ProgrammingError):
            return

        for history_id, asset_id, employee_id in rows:
            asset_row = conn.execute(text("SELECT AssetCode, AssetName FROM Assets WHERE AssetId = :asset_id"), {"asset_id": asset_id}).fetchone()
            employee_row = conn.execute(text("SELECT FullName FROM EmployeeDetail WHERE EmployeeId = :employee_id"), {"employee_id": employee_id}).fetchone()
            asset_code = asset_row[0] if asset_row else None
            asset_name = asset_row[1] if asset_row else None
            employee_name = employee_row[0] if employee_row else None

            conn.execute(
                text(
                    "UPDATE AssetHistory SET AssetCode = :asset_code, AssetName = :asset_name, EmployeeName = :employee_name WHERE HistoryId = :history_id"
                ),
                {
                    "asset_code": asset_code,
                    "asset_name": asset_name,
                    "employee_name": employee_name,
                    "history_id": history_id,
                },
            )
