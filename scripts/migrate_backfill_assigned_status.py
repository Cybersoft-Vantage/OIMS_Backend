"""
One-time migration: set DetailedAssets.Status to "Assigned" for assets that are
currently out on an open assignment.

Assigning an asset now marks it as "Assigned" (see crud.assign_detailed_asset), but
rows assigned before that change still carry their pre-assignment status, e.g.
"Available". Run from the backend root:

python scripts/migrate_backfill_assigned_status.py

Assets whose status records a physical condition that blocks assignment (damaged,
under maintenance, sold) are left untouched. The script is idempotent: running it
multiple times is safe.
"""

from app import models
from app.crud import ASSIGNED_STATUS
from app.database import SessionLocal

# Statuses that describe the asset's condition rather than its availability.
PRESERVED_STATUSES = {'damaged', 'damage', 'maintenance', 'sold', 'sold out', 'sold-out'}


def main():
    db = SessionLocal()
    try:
        open_assignments = (
            db.query(models.DetailedAssetAssignment)
            .filter(
                (models.DetailedAssetAssignment.IsReturned == 0)
                | (models.DetailedAssetAssignment.IsReturned.is_(None))
            )
            .all()
        )

        asset_ids = {a.DetailedAssetId for a in open_assignments if a.DetailedAssetId is not None}
        if not asset_ids:
            print('No open assignments found; nothing to backfill.')
            return

        updated = 0
        skipped = 0
        for asset_id in sorted(asset_ids):
            asset = (
                db.query(models.DetailedAsset)
                .filter(models.DetailedAsset.DetailedAssetId == asset_id)
                .first()
            )
            if not asset:
                continue

            current = (asset.Status or '').strip()
            if current.lower() == ASSIGNED_STATUS.lower():
                continue
            if current.lower() in PRESERVED_STATUSES:
                print(f'Skipping DetailedAssetId={asset_id}: keeping status {current!r}')
                skipped += 1
                continue

            print(f'DetailedAssetId={asset_id}: {current or "(empty)"!r} -> {ASSIGNED_STATUS!r}')
            asset.Status = ASSIGNED_STATUS
            db.add(asset)
            updated += 1

        if updated:
            db.commit()
        print(f'Checked {len(asset_ids)} assigned asset(s), updated {updated}, skipped {skipped}.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
