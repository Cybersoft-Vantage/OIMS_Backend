"""
Migration script to add soft delete columns to Categories, SubCategories, and AssetStatus tables.
Run this script once to add the IsDeleted and DeletedAt columns.
"""

from sqlalchemy import text, create_engine
from app.database import DATABASE_URL

def add_soft_delete_columns():
    """Add IsDeleted and DeletedAt columns to the necessary tables."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # Check if columns already exist before adding them
        # Add columns to Categories table
        try:
            connection.execute(text("""
                ALTER TABLE Categories
                ADD COLUMN IsDeleted INT DEFAULT 0,
                ADD COLUMN DeletedAt DATETIME NULL
            """))
            connection.commit()
            print("✓ Added soft delete columns to Categories table")
        except Exception as e:
            print(f"Categories table update: {e}")
        
        # Add columns to SubCategories table
        try:
            connection.execute(text("""
                ALTER TABLE SubCategories
                ADD COLUMN IsDeleted INT DEFAULT 0,
                ADD COLUMN DeletedAt DATETIME NULL
            """))
            connection.commit()
            print("✓ Added soft delete columns to SubCategories table")
        except Exception as e:
            print(f"SubCategories table update: {e}")
        
        # Add columns to AssetStatus table
        try:
            connection.execute(text("""
                ALTER TABLE AssetStatus
                ADD COLUMN IsDeleted INT DEFAULT 0,
                ADD COLUMN DeletedAt DATETIME NULL
            """))
            connection.commit()
            print("✓ Added soft delete columns to AssetStatus table")
        except Exception as e:
            print(f"AssetStatus table update: {e}")

if __name__ == "__main__":
    add_soft_delete_columns()
    print("\nMigration completed!")
