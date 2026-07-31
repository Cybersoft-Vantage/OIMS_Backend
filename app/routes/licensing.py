from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud
from ..database import get_db

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.get("/", response_model=List[schemas.SoftwareLicenseOut])
def list_licenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_licenses(db, skip=skip, limit=limit)


@router.post("/", response_model=schemas.SoftwareLicenseOut, status_code=201)
def create_license(license_in: schemas.SoftwareLicenseCreate, db: Session = Depends(get_db)):
    return crud.create_license(db, license_in)


@router.put("/{license_id}", response_model=schemas.SoftwareLicenseOut)
def update_license(license_id: int, license_in: schemas.SoftwareLicenseUpdate, db: Session = Depends(get_db)):
    license = crud.update_license(db, license_id, license_in)
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    return license


@router.delete("/{license_id}", response_model=schemas.SoftwareLicenseOut)
def delete_license(license_id: int, db: Session = Depends(get_db)):
    license = crud.delete_license(db, license_id)
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    return license
