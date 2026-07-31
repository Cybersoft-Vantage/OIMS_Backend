from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud, models
from ..database import get_db

router = APIRouter(prefix="/procurements", tags=["procurements"])


@router.get("/", response_model=List[schemas.ProcurementRequestOut])
def list_procurements(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_procurements(db, skip=skip, limit=limit)


@router.post("/", response_model=schemas.ProcurementRequestOut, status_code=201)
def create_procurement(proc_in: schemas.ProcurementRequestCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_procurement(db, proc_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{procurement_id}", response_model=schemas.ProcurementRequestOut)
def update_procurement(procurement_id: int, proc_in: schemas.ProcurementRequestUpdate, db: Session = Depends(get_db)):
    try:
        proc = crud.update_procurement(db, procurement_id, proc_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not proc:
        raise HTTPException(status_code=404, detail="Procurement request not found")
    return proc


@router.delete("/{procurement_id}", response_model=schemas.ProcurementRequestOut)
def delete_procurement(procurement_id: int, db: Session = Depends(get_db)):
    proc = crud.delete_procurement(db, procurement_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procurement request not found")
    return proc
