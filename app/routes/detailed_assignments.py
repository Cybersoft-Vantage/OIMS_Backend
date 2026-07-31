from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud, models
from ..database import get_db
from scripts.emailservice import send_assignment_email, send_return_email_to_receiver, send_return_email_to_returner

router = APIRouter(prefix="/detailed", tags=["detailed"])


def _detailed_asset_model_text(asset: models.DetailedAsset | None) -> str:
    if not asset:
        return "-"
    return (asset.MakeModel or "").strip() or "-"


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

@router.get("/assignments", response_model=List[schemas.DetailedAssetAssignmentOut])
def list_detailed_assignments(detailed_asset_id: int | None = Query(None), skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_detailed_assignments(db, detailed_asset_id=detailed_asset_id, skip=skip, limit=limit)


@router.post("/assignments", response_model=schemas.DetailedAssetAssignmentOut, status_code=201)
def assign_detailed_asset(assignment_in: schemas.DetailedAssetAssignmentCreate, db: Session = Depends(get_db)):
    assignment = crud.assign_detailed_asset(db, assignment_in)
    if assignment is None:
        raise HTTPException(status_code=400, detail="Asset cannot be assigned while damaged or under maintenance")

    employee = crud.get_employee_detail(db, assignment.EmployeeId)
    asset = crud.get_detailed_asset(db, assignment.DetailedAssetId)
    if employee and employee.Email:
        send_assignment_email(
            to_address=employee.Email,
            employee_name=employee.FullName or "Employee",
            assigned_by=assignment.AssignedBy or assignment_in.AssignedBy or "-",
            assigned_date=str(assignment.AssignedDate or assignment_in.AssignedDate or "-"),
            assets=[
                {
                    "asset_tag": asset.AssetTag if asset else "-",
                    "name": asset.Name if asset else "-",
                    "model": _detailed_asset_model_text(asset),
                }
            ],
        )

    return assignment


@router.post("/assignments/bulk", response_model=schemas.DetailedAssetAssignmentBulkResult, status_code=201)
def assign_detailed_assets_bulk(payload: schemas.DetailedAssetAssignmentBulkCreate, db: Session = Depends(get_db)):
    successful_assignments: list[models.DetailedAssetAssignment] = []
    failed_asset_ids: list[int] = []

    for detailed_asset_id in payload.DetailedAssetIds:
        assignment = crud.assign_detailed_asset(
            db,
            schemas.DetailedAssetAssignmentCreate(
                DetailedAssetId=detailed_asset_id,
                EmployeeId=payload.EmployeeId,
                AssignedDate=payload.AssignedDate,
                AssignedBy=payload.AssignedBy,
                Remarks=payload.Remarks,
                IsReturned=0,
            ),
        )
        if assignment is None:
            failed_asset_ids.append(detailed_asset_id)
            continue
        successful_assignments.append(assignment)

    if not successful_assignments:
        raise HTTPException(status_code=400, detail="None of the selected assets could be assigned")

    employee = crud.get_employee_detail(db, payload.EmployeeId)
    if employee and employee.Email:
        assets_payload: list[dict] = []
        for assignment in successful_assignments:
            asset = crud.get_detailed_asset(db, assignment.DetailedAssetId)
            assets_payload.append(
                {
                    "asset_tag": asset.AssetTag if asset else "-",
                    "name": asset.Name if asset else "-",
                    "model": _detailed_asset_model_text(asset),
                }
            )

        send_assignment_email(
            to_address=employee.Email,
            employee_name=employee.FullName or "Employee",
            assigned_by=payload.AssignedBy or "-",
            assigned_date=str(payload.AssignedDate or successful_assignments[0].AssignedDate or "-"),
            assets=assets_payload,
        )

    return {
        "assignments": successful_assignments,
        "failed_asset_ids": failed_asset_ids,
    }


@router.put("/assignments/{assignment_id}/return", response_model=schemas.DetailedAssetAssignmentOut)
def return_detailed_asset(assignment_id: int, return_in: schemas.DetailedAssetAssignmentReturn, db: Session = Depends(get_db)):
    assignment = crud.return_detailed_asset(db, assignment_id, return_in)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    employee = crud.get_employee_detail(db, assignment.EmployeeId)
    asset = crud.get_detailed_asset(db, assignment.DetailedAssetId)
    return_by_name, return_by_emails = _resolve_return_actor(db, return_in.ReturnedBy)

    assets_payload = [
        {
            "asset_tag": asset.AssetTag if asset else "-",
            "name": asset.Name if asset else "-",
            "model": _detailed_asset_model_text(asset),
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


@router.get("/history", response_model=List[schemas.DetailedAssetHistoryOut])
def list_detailed_history(detailed_asset_id: int | None = Query(None), skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_detailed_histories(db, detailed_asset_id=detailed_asset_id, skip=skip, limit=limit)


@router.post("/history", response_model=schemas.DetailedAssetHistoryOut, status_code=201)
def create_detailed_history(history_in: schemas.DetailedAssetHistoryCreate, db: Session = Depends(get_db)):
    return crud.create_detailed_history(db, history_in)
