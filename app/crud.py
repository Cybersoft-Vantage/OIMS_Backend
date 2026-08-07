from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
from fastapi import UploadFile
from . import models, security
from .schemas import (
    EmployeeDetailCreate,
    EmployeeDetailUpdate,
    CategoryCreate,
    CategoryUpdate,
    SubCategoryCreate,
    SubCategoryUpdate,
    AssetStatusCreate,
    AssetStatusUpdate,
    AssetCreate,
    AssetUpdate,
    AssetComponentCreate,
    AssetComponentUpdate,
    AssetAssignmentCreate,
    AssetAssignmentReturn,
    AssetHistoryCreate,
    DetailedAssetAssignmentCreate,
    DetailedAssetAssignmentReturn,
    DetailedAssetAssignmentOut,
    DetailedAssetHistoryCreate,
    DetailedCategoryCreate,
    DetailedCategoryUpdate,
    DetailedAssetCreate,
    DetailedAssetUpdate,
    ProcurementRequestCreate,
    ProcurementRequestUpdate,
    SoftwareLicenseCreate,
    SoftwareLicenseUpdate,
)
import datetime
import re

ASSIGNED_STATUS = "Assigned"
AVAILABLE_STATUS = "Available"


def get_employee_detail(db: Session, employee_id: int):
    return db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == employee_id).first()


def get_employee_detail_by_user_id(db: Session, user_id: str):
    return db.query(models.EmployeeDetail).filter(models.EmployeeDetail.UserId == user_id).first()


def get_employee_detail_by_identifier(db: Session, identifier: str):
    normalized = (identifier or "").strip()
    if not normalized:
        return None
    return (
        db.query(models.EmployeeDetail)
        .filter((models.EmployeeDetail.UserId == normalized) | (models.EmployeeDetail.Email == normalized))
        .first()
    )


def get_employee_details(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.EmployeeDetail).offset(skip).limit(limit).all()


def create_employee_detail(db: Session, employee_in: EmployeeDetailCreate):
    data = employee_in.model_dump(exclude={"Password"})
    password = (employee_in.Password or "").strip()
    if password:
        data["PasswordHash"] = security.get_password_hash(password)
    employee = models.EmployeeDetail(**data)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee_detail(db: Session, employee_id: int, employee_in: EmployeeDetailUpdate):
    employee = get_employee_detail(db, employee_id)
    if not employee:
        return None

    original_email = employee.Email
    data = employee_in.model_dump(exclude={"Password"}, exclude_unset=True)
    for field, value in data.items():
        setattr(employee, field, value)

    email_changed = data.get("Email") is not None and data.get("Email") != original_email
    if email_changed:
        employee.Verify = 0
        employee.EmailVerifiedAt = None
        employee.VerificationOtpHash = None
        employee.VerificationOtpExpiresAt = None
        employee.VerificationOtpAttempts = 0
        employee.VerificationOtpSentAt = None

    db.commit()
    db.refresh(employee)

    password = (employee_in.Password or "").strip() if employee_in.Password is not None else ""
    if password:
        employee.PasswordHash = security.get_password_hash(password)
        db.commit()
        db.refresh(employee)

    return employee


def invalidate_employee_verification(db: Session, employee: models.EmployeeDetail):
    employee.Verify = 0
    employee.EmailVerifiedAt = None
    employee.VerificationOtpHash = None
    employee.VerificationOtpExpiresAt = None
    employee.VerificationOtpAttempts = 0
    employee.VerificationOtpSentAt = None
    db.commit()
    db.refresh(employee)
    return employee


def delete_employee_detail(db: Session, employee_id: int):
    employee = get_employee_detail(db, employee_id)
    if not employee:
        return None
    db.delete(employee)
    db.commit()
    return employee


def import_employee_details(db: Session, file: UploadFile):
    import csv
    from io import StringIO

    field_map = {
        "userid": "UserId",
        "user_id": "UserId",
        "fullname": "FullName",
        "full_name": "FullName",
        "department": "Department",
        "designation": "Designation",
        "email": "Email",
        "phone": "Phone",
        "role": "Role",
        "isactive": "IsActive",
        "is_active": "IsActive",
        "password": "Password",
    }
    valid_roles = {"employee", "admin", "hr"}

    file_extension = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    rows = []
    if file_extension == "csv":
        text_data = file.file.read().decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text_data))
        rows = list(reader)
    elif file_extension in {"xls", "xlsx"}:
        try:
            import openpyxl
        except ImportError:
            raise ValueError("XLS/XLSX import requires openpyxl. Please install it before using this feature.")

        workbook = openpyxl.load_workbook(file.file, data_only=True)
        sheet = workbook.active
        header = [str(cell).strip() if cell is not None else "" for cell in next(sheet.iter_rows(values_only=True))]
        for row in sheet.iter_rows(min_row=2, values_only=True):
            rows.append({header[idx].strip(): row[idx] for idx in range(len(header)) if idx < len(row)})
    else:
        raise ValueError("Unsupported file type. Please upload a CSV or XLSX file.")

    processed = 0
    created = 0
    updated = 0
    errors: list[dict] = []

    for index, raw_row in enumerate(rows, start=1):
        processed += 1
        try:
            row = {
                key.strip().lower(): (value if value is None or isinstance(value, str) else str(value))
                for key, value in raw_row.items()
                if key
            }
            payload: dict = {}
            for raw_key, raw_value in row.items():
                target = field_map.get(raw_key)
                if not target:
                    continue
                value = str(raw_value).strip() if raw_value is not None else None
                if target == "IsActive":
                    if value in (None, ""):
                        payload[target] = 1
                    elif value.lower() in {"1", "true", "yes", "active"}:
                        payload[target] = 1
                    elif value.lower() in {"0", "false", "no", "inactive"}:
                        payload[target] = 0
                    else:
                        raise ValueError("IsActive must be one of: 1/0/true/false/yes/no/active/inactive")
                else:
                    payload[target] = value

            user_id = (payload.get("UserId") or "").strip()
            full_name = (payload.get("FullName") or "").strip()
            if not user_id:
                raise ValueError("Missing required field 'UserId'.")
            if not full_name:
                raise ValueError("Missing required field 'FullName'.")

            role = (payload.get("Role") or "employee").strip().lower()
            if role not in valid_roles:
                raise ValueError("Role must be one of: employee, admin, hr")
            payload["Role"] = role

            password = (payload.get("Password") or "").strip()
            payload["Password"] = password or "CSV112233"

            existing = get_employee_detail_by_user_id(db, user_id)
            if existing:
                update_payload = EmployeeDetailUpdate(**payload)
                updated_employee = update_employee_detail(db, existing.EmployeeId, update_payload)
                if not updated_employee:
                    raise ValueError(f"Unable to update user with UserId '{user_id}'")
                updated += 1
            else:
                create_payload = EmployeeDetailCreate(**payload)
                create_employee_detail(db, create_payload)
                created += 1
        except Exception as exc:
            db.rollback()
            errors.append({"row": index, "error": str(exc)})

    return {"processed": processed, "created": created, "updated": updated, "errors": errors}


def get_category(db: Session, category_id: int):
    return db.query(models.Category).filter(models.Category.CategoryId == category_id).first()


def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Category).filter(models.Category.IsDeleted == 0).offset(skip).limit(limit).all()


def create_category(db: Session, category_in: CategoryCreate):
    category = models.Category(**category_in.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, category_in: CategoryUpdate):
    category = get_category(db, category_id)
    if not category:
        return None
    for field, value in category_in.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int):
    category = get_category(db, category_id)
    if not category:
        return None
    
    # Check if category is in use
    asset_count = db.query(models.Asset).filter(models.Asset.CategoryId == category_id).count()
    if asset_count > 0:
        return {"error": f"Cannot delete category. It is assigned to {asset_count} asset(s)."}
    
    # Soft delete
    category.IsDeleted = 1
    category.DeletedAt = datetime.datetime.utcnow()
    db.commit()
    db.refresh(category)
    return category


def get_subcategory(db: Session, subcategory_id: int):
    return db.query(models.SubCategory).filter(models.SubCategory.SubCategoryId == subcategory_id).first()


def get_subcategories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.SubCategory).filter(models.SubCategory.IsDeleted == 0).offset(skip).limit(limit).all()


def create_subcategory(db: Session, subcategory_in: SubCategoryCreate):
    subcategory = models.SubCategory(**subcategory_in.model_dump())
    db.add(subcategory)
    db.commit()
    db.refresh(subcategory)
    return subcategory



def _generate_next_procurement_reference(db: Session) -> str:
    # Find highest existing numeric suffix for references like 'PR-001'
    rows = db.query(models.ProcurementRequest.Reference).all()
    max_num = 0
    for (ref,) in rows:
        if not ref:
            continue
        if ref.upper().startswith('PR-'):
            try:
                num = int(ref.split('-')[-1])
                if num > max_num:
                    max_num = num
            except Exception:
                continue
    return f"PR-{(max_num + 1):03d}"


def _generate_next_workorder_reference(db: Session) -> str:
    rows = db.query(models.WorkOrder.Reference).all()
    max_num = 0
    for (ref,) in rows:
        if not ref:
            continue
        if ref.upper().startswith('WO-'):
            try:
                num = int(ref.split('-')[-1])
                if num > max_num:
                    max_num = num
            except Exception:
                continue
    return f"WO-{(max_num + 1):04d}"


def get_procurement(db: Session, procurement_id: int):
    return db.query(models.ProcurementRequest).filter(models.ProcurementRequest.ProcurementId == procurement_id).first()


def get_procurements(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ProcurementRequest).offset(skip).limit(limit).all()


def create_procurement(db: Session, procurement_in: ProcurementRequestCreate):
    data = procurement_in.model_dump()
    category_id = data.get('CategoryId')
    subcategory_id = data.get('SubCategoryId')

    if category_id is not None and not get_detailed_category(db, category_id):
        raise ValueError(f"Detailed category not found: {category_id}")

    if subcategory_id is not None:
        subcategory = get_detailed_category(db, subcategory_id)
        if not subcategory:
            raise ValueError(f"Detailed subcategory not found: {subcategory_id}")
        if category_id is not None and subcategory.ParentId != category_id:
            raise ValueError(
                f"Subcategory {subcategory_id} does not belong to detailed category {category_id}"
            )
        if category_id is None:
            data['CategoryId'] = subcategory.ParentId

    if not data.get('Reference'):
        data['Reference'] = _generate_next_procurement_reference(db)
    proc = models.ProcurementRequest(**data)
    db.add(proc)
    db.commit()
    db.refresh(proc)
    return proc


def update_procurement(db: Session, procurement_id: int, procurement_in: ProcurementRequestUpdate):
    proc = get_procurement(db, procurement_id)
    if not proc:
        return None

    update_data = procurement_in.model_dump(exclude_unset=True)
    category_id = update_data.get('CategoryId', proc.CategoryId)
    subcategory_id = update_data.get('SubCategoryId', proc.SubCategoryId)

    if category_id is not None and not get_detailed_category(db, category_id):
        raise ValueError(f"Detailed category not found: {category_id}")

    if subcategory_id is not None:
        subcategory = get_detailed_category(db, subcategory_id)
        if not subcategory:
            raise ValueError(f"Detailed subcategory not found: {subcategory_id}")
        if category_id is not None and subcategory.ParentId != category_id:
            raise ValueError(
                f"Subcategory {subcategory_id} does not belong to detailed category {category_id}"
            )
        if category_id is None:
            update_data['CategoryId'] = subcategory.ParentId

    for field, value in update_data.items():
        setattr(proc, field, value)
    db.commit()
    db.refresh(proc)
    return proc


def delete_procurement(db: Session, procurement_id: int):
    proc = get_procurement(db, procurement_id)
    if not proc:
        return None
    db.delete(proc)
    db.commit()
    return proc


def get_licenses(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.SoftwareLicense).offset(skip).limit(limit).all()


def create_license(db: Session, license_in: SoftwareLicenseCreate):
    license = models.SoftwareLicense(**license_in.model_dump())
    db.add(license)
    db.commit()
    db.refresh(license)
    return license


def update_license(db: Session, license_id: int, license_in: SoftwareLicenseUpdate):
    license = db.query(models.SoftwareLicense).filter(models.SoftwareLicense.LicenseId == license_id).first()
    if not license:
        return None
    for field, value in license_in.model_dump(exclude_unset=True).items():
        setattr(license, field, value)
    db.commit()
    db.refresh(license)
    return license


def delete_license(db: Session, license_id: int):
    license = db.query(models.SoftwareLicense).filter(models.SoftwareLicense.LicenseId == license_id).first()
    if not license:
        return None
    db.delete(license)
    db.commit()
    return license


def update_subcategory(db: Session, subcategory_id: int, subcategory_in: SubCategoryUpdate):


    subcategory = get_subcategory(db, subcategory_id)
    if not subcategory:


        return None
    for field, value in subcategory_in.model_dump(exclude_unset=True).items():
        setattr(subcategory, field, value)
    db.commit()
    db.refresh(subcategory)
    return subcategory


def delete_subcategory(db: Session, subcategory_id: int):
    subcategory = get_subcategory(db, subcategory_id)


    if not subcategory:
        return None
    
    # Check if subcategory is in use
    asset_count = db.query(models.Asset).filter(models.Asset.SubCategoryId == subcategory_id).count()
    component_count = db.query(models.AssetComponent).filter(models.AssetComponent.SubCategoryId == subcategory_id).count()
    
    if asset_count > 0 or component_count > 0:
        return {


            "error": f"Cannot delete subcategory. It is assigned to {asset_count} asset(s) and {component_count} component(s)."
        }
    
    # Soft delete
    subcategory.IsDeleted = 1
    subcategory.DeletedAt = datetime.datetime.utcnow()
    db.commit()
    db.refresh(subcategory)
    return subcategory


def get_asset_status(db: Session, status_id: int):
    return db.query(models.AssetStatus).filter(models.AssetStatus.StatusId == status_id).first()


def get_asset_statuses(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AssetStatus).filter(models.AssetStatus.IsDeleted == 0).offset(skip).limit(limit).all()


def create_asset_status(db: Session, status_in: AssetStatusCreate):
    status = models.AssetStatus(**status_in.model_dump())
    db.add(status)
    db.commit()
    db.refresh(status)
    return status


def update_asset_status(db: Session, status_id: int, status_in: AssetStatusUpdate):
    status = get_asset_status(db, status_id)
    if not status:
        return None
    for field, value in status_in.model_dump(exclude_unset=True).items():
        setattr(status, field, value)
    db.commit()
    db.refresh(status)
    return status


def delete_asset_status(db: Session, status_id: int):
    status = get_asset_status(db, status_id)
    if not status:
        return None
    
    # Check if status is in use
    asset_count = db.query(models.Asset).filter(models.Asset.StatusId == status_id).count()
    if asset_count > 0:
        return {"error": f"Cannot delete status. It is assigned to {asset_count} asset(s)."}
    
    # Soft delete
    status.IsDeleted = 1
    status.DeletedAt = datetime.datetime.utcnow()
    db.commit()
    db.refresh(status)
    return status


def get_asset(db: Session, asset_id: int):
    return db.query(models.Asset).filter(models.Asset.AssetId == asset_id, models.Asset.IsDeleted == 0).first()


def get_assets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Asset).filter(models.Asset.IsDeleted == 0).offset(skip).limit(limit).all()


def create_asset(db: Session, asset_in: AssetCreate):
    asset = models.Asset(**asset_in.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(db: Session, asset_id: int, asset_in: AssetUpdate):
    asset = get_asset(db, asset_id)
    if not asset:
        return None
    for field, value in asset_in.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int):
    asset = get_asset(db, asset_id)
    if not asset:
        return None
    asset.IsDeleted = 1
    asset.DeletedAt = datetime.datetime.utcnow()
    db.commit()
    db.refresh(asset)
    return asset


def get_asset_component(db: Session, component_id: int):
    return db.query(models.AssetComponent).filter(models.AssetComponent.ComponentId == component_id, models.AssetComponent.IsDeleted == 0).first()


def get_asset_components(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AssetComponent).filter(models.AssetComponent.IsDeleted == 0).offset(skip).limit(limit).all()


def create_asset_component(db: Session, component_in: AssetComponentCreate):
    component = models.AssetComponent(**component_in.model_dump())
    db.add(component)
    db.commit()
    db.refresh(component)
    return component


def update_asset_component(db: Session, component_id: int, component_in: AssetComponentUpdate):
    component = get_asset_component(db, component_id)
    if not component:
        return None
    for field, value in component_in.model_dump(exclude_unset=True).items():
        setattr(component, field, value)
    db.commit()
    db.refresh(component)
    return component


def delete_asset_component(db: Session, component_id: int):
    component = get_asset_component(db, component_id)
    if not component:
        return None
    component.IsDeleted = 1
    component.DeletedAt = datetime.datetime.utcnow()
    db.commit()
    db.refresh(component)
    return component


def get_asset_assignment(db: Session, assignment_id: int):
    return db.query(models.AssetAssignment).filter(models.AssetAssignment.AssignmentId == assignment_id).first()


def get_asset_assignments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AssetAssignment).offset(skip).limit(limit).all()


def assign_asset(db: Session, assignment_in: AssetAssignmentCreate):
    asset = get_asset(db, assignment_in.AssetId)
    if not asset:
        return None

    if asset.IsAvailable not in (None, 1):
        return None

    status_name = ''
    if asset.StatusId:
        status = get_asset_status(db, asset.StatusId)
        status_name = (status.StatusName or '').strip().lower() if status else ''
    if 'sold' in status_name:
        return None

    assignment = models.AssetAssignment(**assignment_in.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    if asset:
        asset.CurrentEmployeeId = assignment_in.EmployeeId
        asset.IsAvailable = 0
        db.commit()
        db.refresh(asset)

    history = models.AssetHistory(
        AssetId=assignment_in.AssetId,
        EmployeeId=assignment_in.EmployeeId,
        Action="assigned",
        Notes=assignment_in.Remarks,
        AssetCode=asset.AssetCode if asset else None,
        AssetName=asset.AssetName if asset else None,
        EmployeeName=db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == assignment_in.EmployeeId).first().FullName if db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == assignment_in.EmployeeId).first() else None,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return assignment


def return_asset(db: Session, assignment_id: int, return_in: AssetAssignmentReturn):
    assignment = get_asset_assignment(db, assignment_id)
    if not assignment:
        return None
    assignment.ReturnedDate = return_in.ReturnedDate or datetime.datetime.utcnow().date()
    assignment.Remarks = return_in.Remarks
    assignment.IsReturned = 1
    db.commit()
    db.refresh(assignment)

    asset = get_asset(db, assignment.AssetId)
    if asset:
        asset.IsAvailable = 1
        asset.CurrentEmployeeId = None
        db.commit()
        db.refresh(asset)

    history = models.AssetHistory(
        AssetId=assignment.AssetId,
        EmployeeId=assignment.EmployeeId,
        Action="returned",
        Notes=return_in.Remarks,
        AssetCode=asset.AssetCode if asset else None,
        AssetName=asset.AssetName if asset else None,
        EmployeeName=db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == assignment.EmployeeId).first().FullName if db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == assignment.EmployeeId).first() else None,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return assignment


def get_asset_history(db: Session, history_id: int):
    return db.query(models.AssetHistory).filter(models.AssetHistory.HistoryId == history_id).first()


def get_asset_histories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AssetHistory).offset(skip).limit(limit).all()


def create_asset_history(db: Session, history_in: AssetHistoryCreate):
    payload = history_in.model_dump()
    if not payload.get("AssetCode") and not payload.get("AssetName"):
        asset = get_asset(db, history_in.AssetId)
        if asset:
            payload["AssetCode"] = asset.AssetCode
            payload["AssetName"] = asset.AssetName
    if not payload.get("EmployeeName") and history_in.EmployeeId:
        employee = db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == history_in.EmployeeId).first()
        if employee:
            payload["EmployeeName"] = employee.FullName
    history = models.AssetHistory(**payload)
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


# DetailedCategory CRUD
def get_detailed_category(db: Session, category_id: int):
    return db.query(models.DetailedCategory).filter(models.DetailedCategory.DetailedCategoryId == category_id, models.DetailedCategory.IsDeleted == 0).first()


def get_detailed_categories(db: Session, skip: int = 0, limit: int = 100):
    # Return hierarchical categories (top-level parents with children relationship)
    return db.query(models.DetailedCategory).filter(models.DetailedCategory.IsDeleted == 0, models.DetailedCategory.ParentId == None).offset(skip).limit(limit).all()


def create_detailed_category(db: Session, category_in: DetailedCategoryCreate):
    category = models.DetailedCategory(**category_in.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_detailed_category(db: Session, category_id: int, category_in: DetailedCategoryUpdate):
    category = db.query(models.DetailedCategory).filter(models.DetailedCategory.DetailedCategoryId == category_id).first()
    if not category:
        return None
    for field, value in category_in.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def _get_detailed_category_subtree_ids(db: Session, category_id: int):
    category_ids = [category_id]
    child_ids = (
        db.query(models.DetailedCategory.DetailedCategoryId)
        .filter(models.DetailedCategory.ParentId == category_id, models.DetailedCategory.IsDeleted == 0)
        .all()
    )
    for (child_id,) in child_ids:
        category_ids.extend(_get_detailed_category_subtree_ids(db, child_id))
    return category_ids


def delete_detailed_category(db: Session, category_id: int):
    category = db.query(models.DetailedCategory).filter(models.DetailedCategory.DetailedCategoryId == category_id).first()
    if not category:
        return None

    category_ids = _get_detailed_category_subtree_ids(db, category_id)
    asset_count = db.query(models.DetailedAsset).filter(models.DetailedAsset.DetailedCategoryId.in_(category_ids)).count()
    if asset_count > 0:
        return {"error": f"Cannot delete detailed category. It is assigned to {asset_count} asset(s)."}

    category.IsDeleted = 1
    category.DeletedAt = datetime.datetime.utcnow()
    db.commit()
    db.refresh(category)
    return category


def set_detailed_category_visibility(db: Session, category_id: int, is_hidden: bool, cascade: bool = True):
    """Hide or show a category. Hiding keeps the category and its assets, but the
    asset listings and pickers filter them out. Cascades to subcategories by default
    so hiding a parent does not leave visible orphans underneath it."""
    category = (
        db.query(models.DetailedCategory)
        .filter(models.DetailedCategory.DetailedCategoryId == category_id, models.DetailedCategory.IsDeleted == 0)
        .first()
    )
    if not category:
        return None

    target_ids = _get_detailed_category_subtree_ids(db, category_id) if cascade else [category_id]
    flag = 1 if is_hidden else 0
    for target_id in target_ids:
        target = (
            db.query(models.DetailedCategory)
            .filter(models.DetailedCategory.DetailedCategoryId == target_id)
            .first()
        )
        if target:
            target.IsHidden = flag

    db.commit()
    db.refresh(category)
    return category


def get_hidden_detailed_category_ids(db: Session) -> list[int]:
    rows = (
        db.query(models.DetailedCategory.DetailedCategoryId)
        .filter(models.DetailedCategory.IsDeleted == 0, models.DetailedCategory.IsHidden == 1)
        .all()
    )
    return [row[0] for row in rows]


def get_deleted_detailed_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DetailedCategory).filter(models.DetailedCategory.IsDeleted == 1).offset(skip).limit(limit).all()


def restore_detailed_category(db: Session, category_id: int):
    category = db.query(models.DetailedCategory).filter(models.DetailedCategory.DetailedCategoryId == category_id).first()
    if not category:
        return None
    category.IsDeleted = 0
    category.DeletedAt = None
    db.commit()
    db.refresh(category)
    return category


# DetailedAsset CRUD
def get_detailed_asset(db: Session, asset_id: int):
    return db.query(models.DetailedAsset).filter(models.DetailedAsset.DetailedAssetId == asset_id, models.DetailedAsset.IsDeleted == 0).first()


def get_detailed_assets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DetailedAsset).filter(models.DetailedAsset.IsDeleted == 0).offset(skip).limit(limit).all()


def create_detailed_asset(db: Session, asset_in: DetailedAssetCreate):
    asset = models.DetailedAsset(**asset_in.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def import_detailed_assets(db: Session, file: UploadFile):
    import csv
    from io import StringIO
    from datetime import datetime, date

    def parse_date(value: str):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
        raise ValueError(f"Invalid date format: {value}")

    def normalize_header(value) -> str:
        """Headers are matched on letters and digits only, so 'Make / Model',
        'make_model' and 'MakeModel' all resolve to the same field."""
        return re.sub(r"[^a-z0-9]", "", str(value if value is not None else "").strip().lower())

    # Accepts both the internal field names and the friendlier column titles used by
    # the downloadable template (ParentCategory / BrandName / Model).
    field_map = {
        "assettag": "AssetTag",
        "name": "Name",
        "brandname": "Name",
        "detailedcategoryid": "DetailedCategoryId",
        "detailedcategory": "DetailedCategoryId",
        "parentcategory": "DetailedCategoryId",
        "category": "DetailedCategoryId",
        "subcategory": "SubCategory",
        "makemodel": "MakeModel",
        "model": "MakeModel",
        "serialno": "SerialNo",
        "serialnumber": "SerialNo",
        "specifications": "Specifications",
        "specification": "Specifications",
        "status": "Status",
        "purchasecost": "PurchaseCost",
        "purchasedate": "PurchaseDate",
        "warrantyend": "WarrantyEnd",
        "customvalues": "CustomValues"
    }

    categories = {str(cat.DetailedCategoryId): cat for cat in db.query(models.DetailedCategory).filter(models.DetailedCategory.IsDeleted == 0).all()}
    categories_by_name = {cat.Name.strip().lower(): cat for cat in categories.values() if cat.Name}
    # A ParentCategory column names a top-level category, so resolve against those
    # first - a subcategory sharing the name must not win.
    parent_categories_by_name = {
        cat.Name.strip().lower(): cat for cat in categories.values() if cat.Name and cat.ParentId is None
    }

    existing_tags = {str(asset.AssetTag).strip().lower() for asset in db.query(models.DetailedAsset).filter(models.DetailedAsset.AssetTag != None).all()}
    existing_serials = {str(asset.SerialNo).strip().lower() for asset in db.query(models.DetailedAsset).filter(models.DetailedAsset.SerialNo != None).all()}

    file_extension = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    rows = []
    if file_extension == "csv":
        text_data = file.file.read().decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text_data))
        rows = list(reader)
    elif file_extension in {"xls", "xlsx"}:
        try:
            import openpyxl
        except ImportError:
            raise ValueError("XLS/XLSX import requires openpyxl. Please install it before using this feature.")

        workbook = openpyxl.load_workbook(file.file, data_only=True)
        sheet = workbook.active
        header = [str(cell).strip() if cell is not None else "" for cell in next(sheet.iter_rows(values_only=True))]
        for row in sheet.iter_rows(min_row=2, values_only=True):
            rows.append({header[idx].strip(): row[idx] for idx in range(len(header)) if idx < len(row)})
    else:
        raise ValueError("Unsupported file type. Please upload a CSV or XLSX file.")

    created = 0
    processed = 0
    errors: list[dict] = []
    seen_tags: set[str] = set()
    seen_serials: set[str] = set()

    for index, raw_row in enumerate(rows, start=1):
        processed += 1
        row = {normalize_header(key): (value if value is None or isinstance(value, str) else str(value)) for key, value in raw_row.items() if key}
        payload = {}
        try:
            for raw_key, raw_value in row.items():
                target = field_map.get(raw_key)
                if not target:
                    continue
                if target in {"PurchaseDate", "WarrantyEnd"}:
                    payload[target] = parse_date(str(raw_value)) if raw_value is not None else None
                elif target == "PurchaseCost":
                    payload[target] = float(raw_value) if raw_value not in (None, "") else None
                elif target == "DetailedCategoryId":
                    if raw_value is None or str(raw_value).strip() == "":
                        payload[target] = None
                    elif str(raw_value).strip().isdigit():
                        payload[target] = int(str(raw_value).strip())
                    else:
                        lookup = str(raw_value).strip().lower()
                        match = parent_categories_by_name.get(lookup) or categories_by_name.get(lookup)
                        if not match:
                            raise ValueError(f"Parent category not found: {raw_value}")
                        payload[target] = match.DetailedCategoryId
                else:
                    payload[target] = str(raw_value).strip() if raw_value is not None else None

            if "Name" not in payload or not payload["Name"]:
                raise ValueError("Missing required field 'Name'.")

            if payload.get("DetailedCategoryId") is not None and str(payload["DetailedCategoryId"]) not in categories:
                raise ValueError(f"Detailed category not found: {payload.get('DetailedCategoryId')}")

            if payload.get("AssetTag"):
                normalized_tag = str(payload["AssetTag"]).strip().lower()
                if normalized_tag in existing_tags:
                    raise ValueError(f"Duplicate AssetTag already exists: {payload['AssetTag']}")
                if normalized_tag in seen_tags:
                    raise ValueError(f"Duplicate AssetTag in import file: {payload['AssetTag']}")
                seen_tags.add(normalized_tag)

            if payload.get("SerialNo"):
                normalized_serial = str(payload["SerialNo"]).strip().lower()
                if normalized_serial in existing_serials:
                    raise ValueError(f"Duplicate SerialNo already exists: {payload['SerialNo']}")
                if normalized_serial in seen_serials:
                    raise ValueError(f"Duplicate SerialNo in import file: {payload['SerialNo']}")
                seen_serials.add(normalized_serial)

            asset_in = DetailedAssetCreate(**payload)
            create_detailed_asset(db, asset_in)
            created += 1
        except Exception as exc:
            errors.append({"row": index, "error": str(exc)})

    return {"processed": processed, "created": created, "errors": errors}


def update_detailed_asset(db: Session, asset_id: int, asset_in: DetailedAssetUpdate):
    asset = db.query(models.DetailedAsset).filter(models.DetailedAsset.DetailedAssetId == asset_id).first()
    if not asset:
        return None
    old_status = (asset.Status or '').strip().lower()
    data = asset_in.model_dump(exclude_unset=True)

    # Lock sold status once sold price is set: allow sold price edits but prevent status change away from sold.
    status_locked = old_status == 'sold' and asset.SoldPrice is not None
    if status_locked and 'Status' in data:
        requested_status = (data.get('Status') or '').strip().lower()
        if requested_status and requested_status != 'sold':
            data['Status'] = asset.Status

    for field, value in data.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)

    new_status = (asset.Status or '').strip().lower()
    maintenance_states = {"damaged", "damage", "maintenance"}
    # If asset became damaged/maintenance, create a workorder automatically
    if new_status in maintenance_states and old_status not in maintenance_states:
        # Create a workorder record
        ref = _generate_next_workorder_reference(db)
        reported_by_id = data.get('ReportedByEmployeeId') if isinstance(data.get('ReportedByEmployeeId'), int) else None
        reported_by_name = data.get('ReportedByName') if isinstance(data.get('ReportedByName'), str) else None
        wo = models.WorkOrder(
            Reference=ref,
            DetailedAssetId=asset.DetailedAssetId,
            ReportedByEmployeeId=reported_by_id,
            ReportedByName=reported_by_name,
            Status='open',
            Notes=f'Auto-created workorder for status change to {asset.Status}'
        )
        db.add(wo)
        db.commit()
        db.refresh(wo)

        # add detailed history entry
        hist = models.DetailedAssetHistory(
            DetailedAssetId=asset.DetailedAssetId,
            Action='marked-damaged',
            Notes=f'WorkOrder {wo.Reference} created',
            AssetTag=asset.AssetTag,
            AssetName=asset.Name
        )
        db.add(hist)
        db.commit()
        db.refresh(hist)

    return asset


### Vendor & WorkOrder CRUD
def create_vendor(db: Session, vendor_in):
    v = models.Vendor(**vendor_in.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def get_vendors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Vendor).offset(skip).limit(limit).all()


def get_vendor(db: Session, vendor_id: int):
    return db.query(models.Vendor).filter(models.Vendor.VendorId == vendor_id).first()


def update_vendor(db: Session, vendor_id: int, vendor_in):
    vendor = get_vendor(db, vendor_id)
    if not vendor:
        return None
    for field, value in vendor_in.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    db.commit()
    db.refresh(vendor)
    return vendor


def create_workorder(db: Session, wo_in):
    data = wo_in.model_dump()
    if not data.get('Reference'):
        data['Reference'] = _generate_next_workorder_reference(db)
    if data.get('VendorId'):
        vendor = get_vendor(db, data['VendorId'])
        if vendor:
            data['VendorName'] = vendor.Name
    wo = models.WorkOrder(**data)
    db.add(wo)

    if data.get('DetailedAssetId'):
        asset = get_detailed_asset(db, data['DetailedAssetId'])
        if asset:
            asset.Status = data.get('Status', asset.Status)
            db.commit()
            db.refresh(asset)

    db.commit()
    db.refresh(wo)
    return wo


def update_workorder(db: Session, workorder_id: int, wo_in):
    wo = db.query(models.WorkOrder).filter(models.WorkOrder.WorkOrderId == workorder_id).first()
    if not wo:
        return None
    for field, value in wo_in.model_dump(exclude_unset=True).items():
        setattr(wo, field, value)
    if wo.VendorId:
        vendor = get_vendor(db, wo.VendorId)
        if vendor:
            wo.VendorName = vendor.Name
    if getattr(wo, 'Status', None) and wo.Status.lower() in ('closed', 'completed', 'done', 'repaired'):
        wo.CompletedAt = datetime.datetime.utcnow()
        asset = get_detailed_asset(db, wo.DetailedAssetId)
        if asset:
            asset.Status = 'Available'
            db.commit()
            db.refresh(asset)
    db.commit()
    db.refresh(wo)
    return wo


def get_workorder(db: Session, workorder_id: int):
    return db.query(models.WorkOrder).filter(models.WorkOrder.WorkOrderId == workorder_id).first()


def get_workorders(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.WorkOrder).offset(skip).limit(limit).all()


def get_workorders_for_asset(db: Session, detailed_asset_id: int):
    return db.query(models.WorkOrder).filter(models.WorkOrder.DetailedAssetId == detailed_asset_id).all()


def delete_detailed_asset(db: Session, asset_id: int):
    asset = db.query(models.DetailedAsset).filter(models.DetailedAsset.DetailedAssetId == asset_id).first()
    if not asset:
        return None
    asset.IsDeleted = 1
    asset.UpdatedAt = datetime.datetime.utcnow()
    db.commit()
    db.refresh(asset)
    return asset


def get_deleted_detailed_assets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DetailedAsset).filter(models.DetailedAsset.IsDeleted == 1).offset(skip).limit(limit).all()


def restore_detailed_asset(db: Session, asset_id: int):
    asset = db.query(models.DetailedAsset).filter(models.DetailedAsset.DetailedAssetId == asset_id).first()
    if not asset:
        return None
    asset.IsDeleted = 0
    asset.UpdatedAt = datetime.datetime.utcnow()
    db.commit()
    db.refresh(asset)
    return asset


# DetailedAsset Assignment / History
def get_detailed_assignment(db: Session, assignment_id: int):
    return db.query(models.DetailedAssetAssignment).filter(models.DetailedAssetAssignment.AssignmentId == assignment_id).first()


def get_detailed_assignments(db: Session, detailed_asset_id: int | None = None, skip: int = 0, limit: int = 100):
    q = db.query(models.DetailedAssetAssignment)
    if detailed_asset_id is not None:
        q = q.filter(models.DetailedAssetAssignment.DetailedAssetId == detailed_asset_id)
    return q.offset(skip).limit(limit).all()


def assign_detailed_asset(db: Session, assignment_in: DetailedAssetAssignmentCreate):
    # Prevent assigning assets that are marked damaged, under maintenance, or sold
    asset = get_detailed_asset(db, assignment_in.DetailedAssetId)
    if asset:
        status = (asset.Status or '').strip().lower()
        if status in {'damaged', 'damage', 'maintenance', 'sold', 'sold out', 'sold-out'}:
            return None

    # Prevent duplicate active assignment records for the same asset.
    open_assignment = (
        db.query(models.DetailedAssetAssignment)
        .filter(
            models.DetailedAssetAssignment.DetailedAssetId == assignment_in.DetailedAssetId,
            (models.DetailedAssetAssignment.IsReturned == 0) | (models.DetailedAssetAssignment.IsReturned.is_(None))
        )
        .first()
    )
    if open_assignment:
        return None

    assignment = models.DetailedAssetAssignment(**assignment_in.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    asset = get_detailed_asset(db, assignment_in.DetailedAssetId)
    if asset:
        # An asset that is out with an employee is no longer available.
        asset.Status = ASSIGNED_STATUS
        db.commit()
        db.refresh(asset)

    employee = db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == assignment_in.EmployeeId).first()
    notes = str(assignment_in.Remarks or '').strip()
    if assignment_in.AssignedBy:
        notes = f"Assigned by {assignment_in.AssignedBy}" + (f" - {notes}" if notes else "")
    history = models.DetailedAssetHistory(
        DetailedAssetId=assignment_in.DetailedAssetId,
        EmployeeId=assignment_in.EmployeeId,
        Action="assigned",
        Notes=notes,
        AssetTag=asset.AssetTag if asset else None,
        AssetName=asset.Name if asset else None,
        EmployeeName=employee.FullName if employee else None,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return assignment


def return_detailed_asset(db: Session, assignment_id: int, return_in: DetailedAssetAssignmentReturn):
    assignment = get_detailed_assignment(db, assignment_id)
    if not assignment:
        return None
    assignment.ReturnedDate = return_in.ReturnedDate or datetime.datetime.utcnow().date()
    assignment.ReturnedBy = return_in.ReturnedBy
    assignment.Remarks = return_in.Remarks
    assignment.IsReturned = 1
    db.commit()
    db.refresh(assignment)

    asset = get_detailed_asset(db, assignment.DetailedAssetId)
    if asset:
        old_status = (asset.Status or '').strip().lower()
        requested_status = (return_in.Status or '').strip()
        if requested_status:
            asset.Status = requested_status
        elif old_status in {'', ASSIGNED_STATUS.lower()}:
            # No condition supplied - the asset is back on the shelf.
            asset.Status = AVAILABLE_STATUS
        db.commit()
        db.refresh(asset)

        # If the asset was returned and its new status is damaged/maintenance, auto-create a workorder
        maintenance_states = {"damaged", "damage", "maintenance"}
        new_status = (asset.Status or '').strip().lower()
        if new_status in maintenance_states and old_status not in maintenance_states:
            ref = _generate_next_workorder_reference(db)
            reported_by_name = return_in.ReturnedBy if isinstance(return_in.ReturnedBy, str) else None
            wo = models.WorkOrder(
                Reference=ref,
                DetailedAssetId=asset.DetailedAssetId,
                ReportedByEmployeeId=None,
                ReportedByName=reported_by_name,
                Status='open',
                Notes=f'Auto-created workorder for status change to {asset.Status} (returned)'
            )
            db.add(wo)
            db.commit()
            db.refresh(wo)

            # add detailed history entry
            hist = models.DetailedAssetHistory(
                DetailedAssetId=asset.DetailedAssetId,
                Action='marked-damaged',
                Notes=f'WorkOrder {wo.Reference} created (returned)',
                AssetTag=asset.AssetTag,
                AssetName=asset.Name
            )
            db.add(hist)
            db.commit()
            db.refresh(hist)

    employee = db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == assignment.EmployeeId).first()
    notes = str(return_in.Remarks or '').strip()
    if return_in.ReturnedBy:
        notes = f"{notes} (Returned by {return_in.ReturnedBy})" if notes else f"Returned by {return_in.ReturnedBy}"
    history = models.DetailedAssetHistory(
        DetailedAssetId=assignment.DetailedAssetId,
        EmployeeId=assignment.EmployeeId,
        Action="returned",
        Notes=notes,
        AssetTag=asset.AssetTag if asset else None,
        AssetName=asset.Name if asset else None,
        EmployeeName=employee.FullName if employee else None,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return assignment


def get_detailed_history(db: Session, history_id: int):
    return db.query(models.DetailedAssetHistory).filter(models.DetailedAssetHistory.HistoryId == history_id).first()


def get_detailed_histories(db: Session, detailed_asset_id: int | None = None, skip: int = 0, limit: int = 100):
    q = db.query(models.DetailedAssetHistory)
    if detailed_asset_id is not None:
        q = q.filter(models.DetailedAssetHistory.DetailedAssetId == detailed_asset_id)
    return q.offset(skip).limit(limit).all()


def create_detailed_history(db: Session, history_in: DetailedAssetHistoryCreate):
    payload = history_in.model_dump()
    if not payload.get("AssetTag") and not payload.get("AssetName"):
        asset = get_detailed_asset(db, history_in.DetailedAssetId)
        if asset:
            payload["AssetTag"] = asset.AssetTag
            payload["AssetName"] = asset.Name
    if not payload.get("EmployeeName") and history_in.EmployeeId:
        employee = db.query(models.EmployeeDetail).filter(models.EmployeeDetail.EmployeeId == history_in.EmployeeId).first()
        if employee:
            payload["EmployeeName"] = employee.FullName
    history = models.DetailedAssetHistory(**payload)
    db.add(history)
    db.commit()
    db.refresh(history)
    return history
