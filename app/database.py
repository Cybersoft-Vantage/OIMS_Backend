
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


def _run_isolated(conn, statement: str, params: dict | None = None):
    """Run one patch-up statement inside its own SAVEPOINT.

    On PostgreSQL a failed statement aborts the whole transaction, so sharing one
    transaction across every patch meant a single failure discarded all of them at
    COMMIT - silently, because the errors were swallowed. A SAVEPOINT keeps the damage to
    the statement that failed.

    Returns True when the statement ran, False when it failed (and was rolled back).
    """
    try:
        with conn.begin_nested():
            conn.execute(text(statement), params or {})
        return True
    except (OperationalError, ProgrammingError):
        logger.warning('Schema patch-up skipped: %s', statement.split('\n')[0], exc_info=True)
        return False


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
                "ProcurementRequests": [
                    ("RequestedByEmployeeId", "INTEGER"),
                    ("RequestedByName", "TEXT"),
                    ("Justification", "TEXT"),
                ],
                "WorkOrders": [
                    ("ResolvedByEmployeeId", "INTEGER"),
                    ("ResolvedByName", "TEXT"),
                    ("Resolution", "TEXT"),
                ],
            }.items():
                if not inspector.has_table(table_name):
                    continue

                existing_columns = {
                    row[1]
                    for row in conn.execute(text(f"PRAGMA table_info([{table_name}])")).fetchall()
                }
                for column_name, column_type in columns_to_add:
                    if column_name not in existing_columns:
                        _run_isolated(conn, f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

            if inspector.has_table("EmployeeDetail"):
                existing_columns = {
                    row[1]
                    for row in conn.execute(text('PRAGMA table_info([EmployeeDetail])')).fetchall()
                }
                if "PasswordHash" not in existing_columns:
                    conn.execute(text('ALTER TABLE "EmployeeDetail" ADD COLUMN "PasswordHash" TEXT'))
        else:
            # Add missing columns for non-sqlite DBs, like Postgres. Each statement stands
            # on its own, so one that cannot run does not take the others down with it.
            for statement in (
                'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "ProfileImage" TEXT',
                'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "PasswordHash" VARCHAR(255) NULL',
                'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "Verify" INTEGER NOT NULL DEFAULT 0',
                'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "EmailVerifiedAt" TIMESTAMP NULL',
                'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "VerificationOtpHash" VARCHAR(128) NULL',
                'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "VerificationOtpExpiresAt" TIMESTAMP NULL',
                'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "VerificationOtpAttempts" INTEGER NOT NULL DEFAULT 0',
                'ALTER TABLE "EmployeeDetail" ADD COLUMN IF NOT EXISTS "VerificationOtpSentAt" TIMESTAMP NULL',
                'ALTER TABLE "DetailedCategories" ADD COLUMN IF NOT EXISTS "SubcategoryTagName" VARCHAR(20) NULL',
                'ALTER TABLE "DetailedAssets" ADD COLUMN IF NOT EXISTS "SoldPrice" DOUBLE PRECISION NULL',
                # Requester details, set when an employee raises the request themselves.
                'ALTER TABLE "ProcurementRequests" ADD COLUMN IF NOT EXISTS "RequestedByEmployeeId" INTEGER NULL',
                'ALTER TABLE "ProcurementRequests" ADD COLUMN IF NOT EXISTS "RequestedByName" VARCHAR(150) NULL',
                'ALTER TABLE "ProcurementRequests" ADD COLUMN IF NOT EXISTS "Justification" TEXT NULL',
                # Who closed a reported issue off, and what was done about it.
                'ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS "ResolvedByEmployeeId" INTEGER NULL',
                'ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS "ResolvedByName" VARCHAR(150) NULL',
                'ALTER TABLE "WorkOrders" ADD COLUMN IF NOT EXISTS "Resolution" TEXT NULL',
            ):
                _run_isolated(conn, statement)

            # One-time compatibility backfill: migrate password hashes from legacy users table.
            if inspector.has_table("users"):
                _run_isolated(
                    conn,
                    'UPDATE "EmployeeDetail" e '
                    'SET "PasswordHash" = u.hashed_password '
                    'FROM users u '
                    'WHERE e."PasswordHash" IS NULL AND u.username = e."UserId"',
                )

        # Backfill history snapshot columns for rows saved before those columns existed, so
        # history still shows asset and employee details. Identifiers are quoted because
        # PostgreSQL folds unquoted ones to lower case, and "AssetHistory" would then read
        # as a table that does not exist.
        if not inspector.has_table("AssetHistory") or not inspector.has_table("Assets") or not inspector.has_table("EmployeeDetail"):
            return

        _run_isolated(
            conn,
            'UPDATE "AssetHistory" h SET '
            '"AssetCode" = a."AssetCode", '
            '"AssetName" = a."AssetName" '
            'FROM "Assets" a '
            'WHERE a."AssetId" = h."AssetId" '
            'AND (h."AssetCode" IS NULL OR h."AssetName" IS NULL)'
            if engine.dialect.name != "sqlite"
            else 'UPDATE "AssetHistory" SET '
            '"AssetCode" = (SELECT "AssetCode" FROM "Assets" WHERE "Assets"."AssetId" = "AssetHistory"."AssetId"), '
            '"AssetName" = (SELECT "AssetName" FROM "Assets" WHERE "Assets"."AssetId" = "AssetHistory"."AssetId") '
            'WHERE "AssetCode" IS NULL OR "AssetName" IS NULL',
        )

        _run_isolated(
            conn,
            'UPDATE "AssetHistory" h SET "EmployeeName" = e."FullName" '
            'FROM "EmployeeDetail" e '
            'WHERE e."EmployeeId" = h."EmployeeId" AND h."EmployeeName" IS NULL'
            if engine.dialect.name != "sqlite"
            else 'UPDATE "AssetHistory" SET "EmployeeName" = '
            '(SELECT "FullName" FROM "EmployeeDetail" WHERE "EmployeeDetail"."EmployeeId" = "AssetHistory"."EmployeeId") '
            'WHERE "EmployeeName" IS NULL',
        )
