from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud, models
from ..database import get_db
from scripts.emailservice import send_assignment_email, send_return_email_to_receiver, send_return_email_to_returner

router = APIRouter(prefix="/assets", tags=["assets"])


def _asset_model_text(asset: models.Asset | None) -> str:
    if not asset:
        return "-"
    brand = (asset.Brand or "").strip()
    model = (asset.Model or "").strip()
    if brand and model:
        return f"{brand} / {model}"
    return model or brand or "-"


def _resolve_return_actor(db: Session, returned_by: str | None) -> tuple[str, list[str]]:
    if not returned_by:
        return "-", []

    lookup = returned_by.strip()
    if not lookup:
        return "-", []

    recipients: list[str] = []
    display_name = lookup
    if "@" in lookup:
        recipients.append(lookup)

    employee = (
        db.query(models.EmployeeDetail)
        .filter(
            or_(
                models.EmployeeDetail.UserId == lookup,
                models.EmployeeDetail.Email == lookup,
                func.lower(models.EmployeeDetail.FullName) == lookup.lower(),
            )
        )
        .first()
    )
    if employee:
        display_name = employee.FullName or display_name
        if employee.Email:
            recipients.append(employee.Email)

    deduped = list(dict.fromkeys([addr.strip() for addr in recipients if addr and addr.strip()]))
    return display_name, deduped


@router.get("/categories", response_model=List[schemas.CategoryOut])
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_categories(db, skip=skip, limit=limit)


@router.get("/categories/deleted", response_model=List[schemas.CategoryOut])
def list_deleted_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Admin endpoint to view deleted categories for audit purposes."""
    return db.query(models.Category).filter(models.Category.IsDeleted == 1).offset(skip).limit(limit).all()


@router.post("/categories", response_model=schemas.CategoryOut, status_code=201)
def create_category(category_in: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db, category_in)


@router.put("/categories/{category_id}", response_model=schemas.CategoryOut)
def update_category(category_id: int, category_in: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    category = crud.update_category(db, category_id, category_in)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/categories/{category_id}", response_model=schemas.CategoryOut)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    result = crud.delete_category(db, category_id)
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/subcategories", response_model=List[schemas.SubCategoryOut])
def list_subcategories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_subcategories(db, skip=skip, limit=limit)


@router.get("/subcategories/deleted", response_model=List[schemas.SubCategoryOut])
def list_deleted_subcategories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Admin endpoint to view deleted subcategories for audit purposes."""
    return db.query(models.SubCategory).filter(models.SubCategory.IsDeleted == 1).offset(skip).limit(limit).all()


@router.post("/subcategories", response_model=schemas.SubCategoryOut, status_code=201)
def create_subcategory(subcategory_in: schemas.SubCategoryCreate, db: Session = Depends(get_db)):
    return crud.create_subcategory(db, subcategory_in)


@router.put("/subcategories/{subcategory_id}", response_model=schemas.SubCategoryOut)
def update_subcategory(subcategory_id: int, subcategory_in: schemas.SubCategoryUpdate, db: Session = Depends(get_db)):
    subcategory = crud.update_subcategory(db, subcategory_id, subcategory_in)
    if not subcategory:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    return subcategory


@router.delete("/subcategories/{subcategory_id}", response_model=schemas.SubCategoryOut)
def delete_subcategory(subcategory_id: int, db: Session = Depends(get_db)):
    result = crud.delete_subcategory(db, subcategory_id)
    if not result:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/statuses", response_model=List[schemas.AssetStatusOut])
def list_asset_statuses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_asset_statuses(db, skip=skip, limit=limit)


@router.get("/statuses/deleted", response_model=List[schemas.AssetStatusOut])
def list_deleted_asset_statuses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Admin endpoint to view deleted statuses for audit purposes."""
    return db.query(models.AssetStatus).filter(models.AssetStatus.IsDeleted == 1).offset(skip).limit(limit).all()


@router.post("/statuses", response_model=schemas.AssetStatusOut, status_code=201)
def create_asset_status(status_in: schemas.AssetStatusCreate, db: Session = Depends(get_db)):
    return crud.create_asset_status(db, status_in)


@router.put("/statuses/{status_id}", response_model=schemas.AssetStatusOut)
def update_asset_status(status_id: int, status_in: schemas.AssetStatusUpdate, db: Session = Depends(get_db)):
    status = crud.update_asset_status(db, status_id, status_in)
    if not status:
        raise HTTPException(status_code=404, detail="Asset status not found")
    return status


@router.delete("/statuses/{status_id}", response_model=schemas.AssetStatusOut)
def delete_asset_status(status_id: int, db: Session = Depends(get_db)):
    result = crud.delete_asset_status(db, status_id)
    if not result:
        raise HTTPException(status_code=404, detail="Asset status not found")
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/", response_model=List[schemas.AssetOut])
def list_assets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_assets(db, skip=skip, limit=limit)


@router.post("/", response_model=schemas.AssetOut, status_code=201)
def create_asset(asset_in: schemas.AssetCreate, db: Session = Depends(get_db)):
    return crud.create_asset(db, asset_in)


@router.put("/{asset_id}", response_model=schemas.AssetOut)
def update_asset(asset_id: int, asset_in: schemas.AssetUpdate, db: Session = Depends(get_db)):
    asset = crud.update_asset(db, asset_id, asset_in)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/{asset_id}", response_model=schemas.AssetOut)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = crud.delete_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/components", response_model=List[schemas.AssetComponentOut])
def list_asset_components(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_asset_components(db, skip=skip, limit=limit)


@router.post("/components", response_model=schemas.AssetComponentOut, status_code=201)
def create_asset_component(component_in: schemas.AssetComponentCreate, db: Session = Depends(get_db)):
    return crud.create_asset_component(db, component_in)


@router.put("/components/{component_id}", response_model=schemas.AssetComponentOut)
def update_asset_component(component_id: int, component_in: schemas.AssetComponentUpdate, db: Session = Depends(get_db)):
    component = crud.update_asset_component(db, component_id, component_in)
    if not component:
        raise HTTPException(status_code=404, detail="Asset component not found")
    return component


@router.delete("/components/{component_id}", response_model=schemas.AssetComponentOut)
def delete_asset_component(component_id: int, db: Session = Depends(get_db)):
    component = crud.delete_asset_component(db, component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Asset component not found")
    return component


@router.get("/assignments", response_model=List[schemas.AssetAssignmentOut])
def list_asset_assignments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_asset_assignments(db, skip=skip, limit=limit)


@router.post("/assignments", response_model=schemas.AssetAssignmentOut, status_code=201)
def assign_asset(assignment_in: schemas.AssetAssignmentCreate, db: Session = Depends(get_db)):
    assignment = crud.assign_asset(db, assignment_in)
    if assignment is None:
        raise HTTPException(status_code=400, detail="Asset cannot be assigned because it is unavailable or sold")

    employee = crud.get_employee_detail(db, assignment.EmployeeId)
    asset = crud.get_asset(db, assignment.AssetId)
    if employee and employee.Email:
        send_assignment_email(
            to_address=employee.Email,
            employee_name=employee.FullName or "Employee",
            assigned_by=assignment.AssignedBy or assignment_in.AssignedBy or "-",
            assigned_date=str(assignment.AssignedDate or assignment_in.AssignedDate or "-"),
            assets=[
                {
                    "asset_tag": asset.AssetCode if asset else "-",
                    "name": asset.AssetName if asset else "-",
                    "model": _asset_model_text(asset),
                }
            ],
        )
    return assignment


@router.put("/assignments/{assignment_id}/return", response_model=schemas.AssetAssignmentOut)
def return_asset(assignment_id: int, return_in: schemas.AssetAssignmentReturn, db: Session = Depends(get_db)):
    assignment = crud.return_asset(db, assignment_id, return_in)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    employee = crud.get_employee_detail(db, assignment.EmployeeId)
    asset = crud.get_asset(db, assignment.AssetId)
    return_by_name, return_by_emails = _resolve_return_actor(db, return_in.ReturnedBy)

    assets_payload = [
        {
            "asset_tag": asset.AssetCode if asset else "-",
            "name": asset.AssetName if asset else "-",
            "model": _asset_model_text(asset),
        }
    ]
    returned_date = str(assignment.ReturnedDate or return_in.ReturnedDate or "-")
    assignee_name = employee.FullName if employee else "Employee"

    if employee and employee.Email:
        send_return_email_to_returner(
            to_address=employee.Email,
            returner_name=assignee_name,
            received_by_name=return_by_name,
            returned_date=returned_date,
            assets=assets_payload,
        )

    for recipient in return_by_emails:
        if employee and employee.Email and recipient.lower() == employee.Email.lower():
            continue
        send_return_email_to_receiver(
            to_address=recipient,
            receiver_name=return_by_name,
            return_by_name=assignee_name,
            returned_date=returned_date,
            assets=assets_payload,
        )
    return assignment


@router.get("/history", response_model=List[schemas.AssetHistoryOut])
def list_asset_history(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_asset_histories(db, skip=skip, limit=limit)


@router.post("/history", response_model=schemas.AssetHistoryOut, status_code=201)
def create_asset_history(history_in: schemas.AssetHistoryCreate, db: Session = Depends(get_db)):
    return crud.create_asset_history(db, history_in)


@router.get("/{asset_id}", response_model=schemas.AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
