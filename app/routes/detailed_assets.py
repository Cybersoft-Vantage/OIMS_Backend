from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/detailed", tags=["detailed-assets"])


def serialize_category(category: models.DetailedCategory, visited: set[int] | None = None):
    if visited is None:
        visited = set()
    if category.DetailedCategoryId in visited:
        return None
    visited.add(category.DetailedCategoryId)
    children = []
    for child in getattr(category, "children", []) or []:
        if not child or child.IsDeleted == 1 or child.DetailedCategoryId in visited:
            continue
        serialized = serialize_category(child, visited)
        if serialized is not None:
            children.append(serialized)
    return {
        "DetailedCategoryId": category.DetailedCategoryId,
        "Name": category.Name,
        "ParentId": category.ParentId,
        "SubcategoryTagName": category.SubcategoryTagName,
        "Description": category.Description,
        "CustomSchema": category.CustomSchema,
        "IsHidden": 1 if category.IsHidden else 0,
        "children": children or None,
    }


# Categories
@router.get("/categories", response_model=list[schemas.DetailedCategoryOut])
def list_categories(skip: int = 0, limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    categories = crud.get_detailed_categories(db, skip=skip, limit=limit)
    return [serialize_category(category) for category in categories]


@router.get("/categories/deleted", response_model=list[schemas.DetailedCategoryOut])
def list_deleted_categories(skip: int = 0, limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    categories = crud.get_deleted_detailed_categories(db, skip=skip, limit=limit)
    return [serialize_category(category) for category in categories if serialize_category(category) is not None]


@router.get("/categories/{category_id}", response_model=schemas.DetailedCategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = crud.get_detailed_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    serialized = serialize_category(category)
    if serialized is None:
        raise HTTPException(status_code=500, detail="Failed to serialize category")
    return serialized


@router.post("/categories", response_model=schemas.DetailedCategoryOut)
def create_category(category_in: schemas.DetailedCategoryCreate, db: Session = Depends(get_db)):
    category = crud.create_detailed_category(db, category_in)
    serialized = serialize_category(category)
    if serialized is None:
        raise HTTPException(status_code=500, detail="Failed to serialize created category")
    return serialized


@router.put("/categories/{category_id}", response_model=schemas.DetailedCategoryOut)
def update_category(category_id: int, category_in: schemas.DetailedCategoryUpdate, db: Session = Depends(get_db)):
    category = crud.update_detailed_category(db, category_id, category_in)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    serialized = serialize_category(category)
    if serialized is None:
        raise HTTPException(status_code=500, detail="Failed to serialize updated category")
    return serialized


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    result = crud.delete_detailed_category(db, category_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=409, detail=result["error"])
    return {"ok": True}


@router.put("/categories/{category_id}/visibility", response_model=schemas.DetailedCategoryOut)
def set_category_visibility(
    category_id: int,
    payload: schemas.DetailedCategoryVisibility,
    db: Session = Depends(get_db),
):
    category = crud.set_detailed_category_visibility(db, category_id, payload.IsHidden, cascade=payload.Cascade)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    serialized = serialize_category(category)
    if serialized is None:
        raise HTTPException(status_code=500, detail="Failed to serialize category")
    return serialized


@router.post("/categories/{category_id}/restore", response_model=schemas.DetailedCategoryOut)
def restore_category(category_id: int, db: Session = Depends(get_db)):
    category = crud.restore_detailed_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    serialized = serialize_category(category)
    if serialized is None:
        raise HTTPException(status_code=500, detail="Failed to serialize restored category")
    return serialized


@router.get("/assets/deleted", response_model=list[schemas.DetailedAssetOut])
def list_deleted_assets(skip: int = 0, limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    return crud.get_deleted_detailed_assets(db, skip=skip, limit=limit)


@router.post("/assets/{asset_id}/restore", response_model=schemas.DetailedAssetOut)
def restore_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = crud.restore_detailed_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# Assets
@router.get("/assets", response_model=list[schemas.DetailedAssetOut])
def list_assets(skip: int = 0, limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    return crud.get_detailed_assets(db, skip=skip, limit=limit)


@router.post("/assets", response_model=schemas.DetailedAssetOut)
def create_asset(asset_in: schemas.DetailedAssetCreate, db: Session = Depends(get_db)):
    result = crud.create_detailed_asset(db, asset_in)
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/assets/{asset_id}", response_model=schemas.DetailedAssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = crud.get_detailed_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/assets/import", response_model=schemas.DetailedAssetImportResult)
def import_assets(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        return crud.import_detailed_assets(db, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}")


@router.put("/assets/{asset_id}", response_model=schemas.DetailedAssetOut)
def update_asset(asset_id: int, asset_in: schemas.DetailedAssetUpdate, db: Session = Depends(get_db)):
    asset = crud.update_detailed_asset(db, asset_id, asset_in)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    result = crud.delete_detailed_asset(db, asset_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=409, detail=result["error"])
    return {"ok": True}
