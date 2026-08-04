import csv
from io import StringIO, BytesIO
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud
from ..database import get_db

router = APIRouter(prefix="/employees", tags=["employees"])


USER_IMPORT_TEMPLATE_HEADERS = [
    "UserId",
    "FullName",
    "Department",
    "Designation",
    "Email",
    "Phone",
    "Role",
    "IsActive",
    "Password",
]


@router.get("/", response_model=List[schemas.EmployeeDetailOut])
def list_employee_details(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_employee_details(db, skip=skip, limit=limit)


@router.get("/import/template/csv")
def download_import_template_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(USER_IMPORT_TEMPLATE_HEADERS)
    content = output.getvalue().encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="user_import_template.csv"'},
    )


@router.get("/import/template/xlsx")
def download_import_template_xlsx():
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl is required to generate XLSX template")

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Users"
    sheet.append(USER_IMPORT_TEMPLATE_HEADERS)

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return Response(
        content=stream.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="user_import_template.xlsx"'},
    )


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


@router.post("/import", response_model=schemas.UserImportResult)
def import_employee_details(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        return crud.import_employee_details(db, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}")


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
