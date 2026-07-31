from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

@router.post("/vendors", response_model=schemas.VendorOut)
def create_vendor(vendor_in: schemas.VendorCreate, db: Session = Depends(get_db)):
    return crud.create_vendor(db, vendor_in)


@router.get("/vendors", response_model=list[schemas.VendorOut])
def list_vendors(skip: int = 0, limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    return crud.get_vendors(db, skip=skip, limit=limit)


@router.put("/vendors/{vendor_id}", response_model=schemas.VendorOut)
def update_vendor(vendor_id: int, vendor_in: schemas.VendorUpdate, db: Session = Depends(get_db)):
    vendor = crud.update_vendor(db, vendor_id, vendor_in)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.post("/workorders", response_model=schemas.WorkOrderOut)
def create_workorder(wo_in: schemas.WorkOrderCreate, db: Session = Depends(get_db)):
    return crud.create_workorder(db, wo_in)


@router.get("/workorders", response_model=list[schemas.WorkOrderOut])
def list_workorders(skip: int = 0, limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    return crud.get_workorders(db, skip=skip, limit=limit)


@router.get("/workorders/{workorder_id}", response_model=schemas.WorkOrderOut)
def get_workorder(workorder_id: int, db: Session = Depends(get_db)):
    wo = db.query(crud.models.WorkOrder).filter(crud.models.WorkOrder.WorkOrderId == workorder_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="WorkOrder not found")
    return wo


@router.put("/workorders/{workorder_id}", response_model=schemas.WorkOrderOut)
def update_workorder(workorder_id: int, wo_in: schemas.WorkOrderUpdate, db: Session = Depends(get_db)):
    wo = crud.update_workorder(db, workorder_id, wo_in)
    if not wo:
        raise HTTPException(status_code=404, detail="WorkOrder not found")
    return wo


@router.get("/assets/{detailed_asset_id}/workorders", response_model=list[schemas.WorkOrderOut])
def workorders_for_asset(detailed_asset_id: int, db: Session = Depends(get_db)):
    return crud.get_workorders_for_asset(db, detailed_asset_id)
