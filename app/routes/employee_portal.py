"""The signed-in employee's own view of the inventory.

Every endpoint here resolves the employee from the bearer token and never from the
request body, so an employee can only read and create records that belong to them. That
is what keeps these routes safe to expose to the `employee` role, unlike the inventory
management routes, which are written for administrators.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter(prefix="/portal", tags=["employee-portal"])


@router.get("/summary", response_model=schemas.MyPortalSummary)
def my_summary(
    current_user: models.EmployeeDetail = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_my_portal_summary(db, current_user)


@router.get("/assets", response_model=List[schemas.MyAssetOut])
def my_assets(
    include_returned: bool = Query(False, description="Also list assets already handed back."),
    current_user: models.EmployeeDetail = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_my_assets(db, current_user.EmployeeId, include_returned=include_returned)


@router.get("/history", response_model=List[schemas.DetailedAssetHistoryOut])
def my_history(
    skip: int = 0,
    limit: int = Query(200, le=1000),
    current_user: models.EmployeeDetail = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_my_history(db, current_user.EmployeeId, skip=skip, limit=limit)


@router.get("/requests", response_model=List[schemas.ProcurementRequestOut])
def my_requests(
    current_user: models.EmployeeDetail = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_my_procurements(db, current_user.EmployeeId)


@router.post("/requests", response_model=schemas.ProcurementRequestOut, status_code=201)
def create_my_request(
    request_in: schemas.MyProcurementRequestCreate,
    current_user: models.EmployeeDetail = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return crud.create_my_procurement(db, current_user, request_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/issues", response_model=List[schemas.WorkOrderOut])
def my_issues(
    current_user: models.EmployeeDetail = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_my_issues(db, current_user.EmployeeId)


@router.post("/issues", response_model=schemas.WorkOrderOut, status_code=201)
def report_my_issue(
    issue_in: schemas.MyIssueCreate,
    current_user: models.EmployeeDetail = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return crud.create_my_issue(db, current_user, issue_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
