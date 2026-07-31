from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud
from ..database import get_db

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/", response_model=List[schemas.EmployeeDetailOut])
def list_employee_details(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_employee_details(db, skip=skip, limit=limit)


@router.get("/user/{user_id}", response_model=schemas.EmployeeDetailOut)
def get_employee_detail_by_user_id(user_id: str, db: Session = Depends(get_db)):
    employee = crud.get_employee_detail_by_user_id(db, user_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.get("/{employee_id}", response_model=schemas.EmployeeDetailOut)
def get_employee_detail(employee_id: int, db: Session = Depends(get_db)):
    employee = crud.get_employee_detail(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("/", response_model=schemas.EmployeeDetailOut, status_code=201)
def create_employee_detail(employee_in: schemas.EmployeeDetailCreate, db: Session = Depends(get_db)):
    return crud.create_employee_detail(db, employee_in)


@router.put("/{employee_id}", response_model=schemas.EmployeeDetailOut)
def update_employee_detail(employee_id: int, employee_in: schemas.EmployeeDetailUpdate, db: Session = Depends(get_db)):
    employee = crud.update_employee_detail(db, employee_id, employee_in)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.delete("/{employee_id}", response_model=schemas.EmployeeDetailOut)
def delete_employee_detail(employee_id: int, db: Session = Depends(get_db)):
    employee = crud.delete_employee_detail(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee
