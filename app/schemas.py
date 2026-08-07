from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import date, datetime


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    identifier: str
    password: str


class VerifyEmailRequest(BaseModel):
    identifier: str
    otp: str


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    role: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    profile_image: Optional[str] = None
    verification_required: bool = False
    verification_message: Optional[str] = None
    verification_identifier: Optional[str] = None
    retry_after_seconds: Optional[int] = None


class EmployeeDetailBase(BaseModel):
    UserId: str
    FullName: str
    Department: Optional[str] = None
    Designation: Optional[str] = None
    Email: Optional[EmailStr] = None
    Phone: Optional[str] = None
    ProfileImage: Optional[str] = None
    IsActive: Optional[int] = 1
    Role: Optional[str] = "employee"
    Verify: Optional[int] = 0
    EmailVerifiedAt: Optional[datetime] = None

    @field_validator("Email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class EmployeeDetailCreate(EmployeeDetailBase):
    Password: Optional[str] = None


class EmployeeDetailUpdate(BaseModel):
    UserId: Optional[str] = None
    FullName: Optional[str] = None
    Department: Optional[str] = None
    Designation: Optional[str] = None
    Email: Optional[EmailStr] = None
    Phone: Optional[str] = None
    ProfileImage: Optional[str] = None
    IsActive: Optional[int] = None
    Role: Optional[str] = None
    Password: Optional[str] = None

    @field_validator("Email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class EmployeeDetailOut(EmployeeDetailBase):
    EmployeeId: int
    CreatedAt: datetime

    model_config = {"from_attributes": True}


class UserSessionOut(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: str
    profile_image: Optional[str] = None
    employee: Optional[EmployeeDetailOut] = None

    model_config = {"from_attributes": True}


class CategoryBase(BaseModel):
    CategoryName: str
    Description: Optional[str] = None
    IsActive: Optional[int] = 1


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    CategoryName: Optional[str] = None
    Description: Optional[str] = None
    IsActive: Optional[int] = None


class CategoryOut(CategoryBase):
    CategoryId: int

    model_config = {"from_attributes": True}


class SubCategoryBase(BaseModel):
    CategoryId: int
    SubCategoryName: str
    Description: Optional[str] = None


class SubCategoryCreate(SubCategoryBase):
    pass


class SubCategoryUpdate(BaseModel):
    CategoryId: Optional[int] = None
    SubCategoryName: Optional[str] = None
    Description: Optional[str] = None


class SubCategoryOut(SubCategoryBase):
    SubCategoryId: int

    model_config = {"from_attributes": True}


class AssetStatusBase(BaseModel):
    StatusId: Optional[int] = None
    StatusName: str


class AssetStatusCreate(BaseModel):
    StatusName: str


class AssetStatusUpdate(BaseModel):
    StatusName: Optional[str] = None


class AssetStatusOut(AssetStatusBase):
    StatusId: int

    model_config = {"from_attributes": True}


class AssetBase(BaseModel):
    AssetCode: Optional[str] = None
    CategoryId: Optional[int] = None
    SubCategoryId: Optional[int] = None
    AssetName: Optional[str] = None
    IsDeleted: Optional[int] = 0
    DeletedAt: Optional[datetime] = None
    Brand: Optional[str] = None
    Model: Optional[str] = None
    SerialNumber: Optional[str] = None
    MacAddress: Optional[str] = None
    PurchaseDate: Optional[date] = None
    PurchasePrice: Optional[float] = None
    StatusId: Optional[int] = None
    CurrentEmployeeId: Optional[int] = None
    Remarks: Optional[str] = None
    IsAvailable: Optional[int] = 1


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    AssetCode: Optional[str] = None
    CategoryId: Optional[int] = None
    SubCategoryId: Optional[int] = None
    AssetName: Optional[str] = None
    Brand: Optional[str] = None
    Model: Optional[str] = None
    SerialNumber: Optional[str] = None
    MacAddress: Optional[str] = None
    PurchaseDate: Optional[date] = None
    PurchasePrice: Optional[float] = None
    StatusId: Optional[int] = None
    CurrentEmployeeId: Optional[int] = None
    Remarks: Optional[str] = None
    IsAvailable: Optional[int] = None


class AssetOut(AssetBase):
    AssetId: int
    CreatedAt: datetime

    model_config = {"from_attributes": True}


class AssetComponentBase(BaseModel):
    AssetId: int
    SubCategoryId: Optional[int] = None
    ComponentCode: Optional[str] = None
    ComponentName: Optional[str] = None
    IsDeleted: Optional[int] = 0
    DeletedAt: Optional[datetime] = None
    Brand: Optional[str] = None
    Model: Optional[str] = None
    SerialNumber: Optional[str] = None
    Quantity: Optional[int] = 1
    Remarks: Optional[str] = None


class AssetComponentCreate(AssetComponentBase):
    pass


class AssetComponentUpdate(BaseModel):
    AssetId: Optional[int] = None
    SubCategoryId: Optional[int] = None
    ComponentName: Optional[str] = None
    Brand: Optional[str] = None
    Model: Optional[str] = None
    SerialNumber: Optional[str] = None
    Quantity: Optional[int] = None
    Remarks: Optional[str] = None


class AssetComponentOut(AssetComponentBase):
    ComponentId: int

    model_config = {"from_attributes": True}


class AssetAssignmentBase(BaseModel):
    AssetId: int
    EmployeeId: int
    AssignedDate: Optional[date] = None
    ReturnedDate: Optional[date] = None
    AssignedBy: Optional[str] = None
    Remarks: Optional[str] = None
    IsReturned: Optional[int] = 0


class AssetAssignmentCreate(AssetAssignmentBase):
    pass


class AssetAssignmentReturn(BaseModel):
    ReturnedDate: Optional[date] = None
    Remarks: Optional[str] = None
    ReturnedBy: Optional[str] = None


class AssetAssignmentOut(AssetAssignmentBase):
    AssignmentId: int

    model_config = {"from_attributes": True}


class DetailedAssetAssignmentBase(BaseModel):
    DetailedAssetId: int
    EmployeeId: int
    AssignedDate: Optional[date] = None
    ReturnedDate: Optional[date] = None
    AssignedBy: Optional[str] = None
    Remarks: Optional[str] = None
    IsReturned: Optional[int] = 0


class DetailedAssetAssignmentCreate(DetailedAssetAssignmentBase):
    pass


class DetailedAssetAssignmentReturn(BaseModel):
    ReturnedDate: Optional[date] = None
    Remarks: Optional[str] = None
    ReturnedBy: Optional[str] = None
    Status: Optional[str] = None


class DetailedAssetAssignmentOut(DetailedAssetAssignmentBase):
    AssignmentId: int
    ReturnedBy: Optional[str] = None

    model_config = {"from_attributes": True}


class DetailedAssetAssignmentBulkCreate(BaseModel):
    DetailedAssetIds: List[int]
    EmployeeId: int
    AssignedDate: Optional[date] = None
    AssignedBy: Optional[str] = None
    Remarks: Optional[str] = None


class DetailedAssetAssignmentBulkResult(BaseModel):
    assignments: List[DetailedAssetAssignmentOut]
    failed_asset_ids: List[int]


class DetailedAssetAssignmentBulkReturn(BaseModel):
    AssignmentIds: List[int]
    ReturnedDate: Optional[date] = None
    ReturnedBy: Optional[str] = None
    Remarks: Optional[str] = None
    Status: Optional[str] = None


class DetailedAssetAssignmentBulkReturnResult(BaseModel):
    returns: List[DetailedAssetAssignmentOut]
    failed_assignment_ids: List[int]


class AssetHistoryBase(BaseModel):
    AssetId: int
    EmployeeId: Optional[int] = None
    Action: str
    Notes: Optional[str] = None
    AssetCode: Optional[str] = None
    AssetName: Optional[str] = None
    EmployeeName: Optional[str] = None


class AssetHistoryCreate(AssetHistoryBase):
    pass


class AssetHistoryOut(AssetHistoryBase):
    HistoryId: int
    ActionDate: datetime

    model_config = {"from_attributes": True}


class DetailedAssetHistoryBase(BaseModel):
    DetailedAssetId: int
    EmployeeId: Optional[int] = None
    Action: str
    Notes: Optional[str] = None
    AssetTag: Optional[str] = None
    AssetName: Optional[str] = None
    EmployeeName: Optional[str] = None


class DetailedAssetHistoryCreate(DetailedAssetHistoryBase):
    pass


class DetailedAssetHistoryOut(DetailedAssetHistoryBase):
    HistoryId: int
    ActionDate: datetime

    model_config = {"from_attributes": True}


class ImportErrorDetail(BaseModel):
    row: Optional[int] = None
    error: str


class DetailedAssetImportResult(BaseModel):
    processed: int
    created: int
    errors: List[ImportErrorDetail]


class UserImportResult(BaseModel):
    processed: int
    created: int
    updated: int
    errors: List[ImportErrorDetail]


class DeleteErrorResponse(BaseModel):
    error: str
    detail: str = "Cannot delete this item. It is still in use by other records."


class DetailedCategoryBase(BaseModel):
    Name: str
    ParentId: Optional[int] = None
    SubcategoryTagName: Optional[str] = None
    Description: Optional[str] = None
    CustomSchema: Optional[str] = None

    @field_validator("SubcategoryTagName", mode="before")
    @classmethod
    def validate_subcategory_tag_name(cls, value):
        if value is None:
            return None
        normalized = str(value).strip().upper()
        if not normalized:
            return None
        return normalized


class DetailedCategoryCreate(DetailedCategoryBase):
    pass


class DetailedCategoryUpdate(BaseModel):
    Name: Optional[str] = None
    ParentId: Optional[int] = None
    SubcategoryTagName: Optional[str] = None
    Description: Optional[str] = None
    CustomSchema: Optional[str] = None
    IsHidden: Optional[int] = None

    @field_validator("SubcategoryTagName", mode="before")
    @classmethod
    def validate_subcategory_tag_name(cls, value):
        if value is None:
            return None
        normalized = str(value).strip().upper()
        if not normalized:
            return None
        return normalized


class DetailedCategoryVisibility(BaseModel):
    IsHidden: bool
    # Hiding/showing a parent applies to its subcategories too unless disabled.
    Cascade: bool = True


class DetailedCategoryOut(DetailedCategoryBase):
    DetailedCategoryId: int
    IsHidden: Optional[int] = 0

    children: Optional[List["DetailedCategoryOut"]] = None

    model_config = {"from_attributes": True}


class DetailedAssetBase(BaseModel):
    AssetTag: Optional[str] = None
    Name: str
    DetailedCategoryId: Optional[int] = None
    SubCategory: Optional[str] = None
    MakeModel: Optional[str] = None
    SerialNo: Optional[str] = None
    Specifications: Optional[str] = None
    Status: Optional[str] = None
    PurchaseCost: Optional[float] = None
    PurchaseDate: Optional[date] = None
    WarrantyEnd: Optional[date] = None
    SoldPrice: Optional[float] = None
    CustomValues: Optional[str] = None


class DetailedAssetCreate(DetailedAssetBase):
    pass


class DetailedAssetUpdate(BaseModel):
    AssetTag: Optional[str] = None
    Name: Optional[str] = None
    DetailedCategoryId: Optional[int] = None
    SubCategory: Optional[str] = None
    MakeModel: Optional[str] = None
    SerialNo: Optional[str] = None
    Specifications: Optional[str] = None
    Status: Optional[str] = None
    PurchaseCost: Optional[float] = None
    PurchaseDate: Optional[date] = None
    WarrantyEnd: Optional[date] = None
    SoldPrice: Optional[float] = None
    CustomValues: Optional[str] = None


class DetailedAssetOut(DetailedAssetBase):
    DetailedAssetId: int
    CreatedAt: datetime
    UpdatedAt: Optional[datetime] = None

    model_config = {"from_attributes": True}


# allow forward refs for recursive DetailedCategoryOut
try:
    DetailedCategoryOut.model_rebuild()
except Exception:
    pass


class ProcurementRequestBase(BaseModel):
    Reference: Optional[str] = None
    CategoryId: Optional[int] = None
    SubCategoryId: Optional[int] = None
    Item: str
    Quantity: int
    Status: Optional[str] = "Pending"


class ProcurementRequestCreate(ProcurementRequestBase):
    pass


class ProcurementRequestUpdate(BaseModel):
    CategoryId: Optional[int] = None
    SubCategoryId: Optional[int] = None
    Item: Optional[str] = None
    Quantity: Optional[int] = None
    Status: Optional[str] = None


class ProcurementRequestOut(ProcurementRequestBase):
    ProcurementId: int
    CreatedAt: datetime

    model_config = {"from_attributes": True}


class SoftwareLicenseBase(BaseModel):
    SoftwareName: str
    Vendor: Optional[str] = None
    LicenseKey: Optional[str] = None
    Seats: Optional[int] = 1
    PurchaseDate: Optional[date] = None
    RenewalDate: Optional[date] = None
    Status: Optional[str] = "Active"
    Notes: Optional[str] = None


class SoftwareLicenseCreate(SoftwareLicenseBase):
    pass


class SoftwareLicenseUpdate(BaseModel):
    SoftwareName: Optional[str] = None
    Vendor: Optional[str] = None
    LicenseKey: Optional[str] = None
    Seats: Optional[int] = None
    PurchaseDate: Optional[date] = None
    RenewalDate: Optional[date] = None
    Status: Optional[str] = None
    Notes: Optional[str] = None


class SoftwareLicenseOut(SoftwareLicenseBase):
    LicenseId: int
    CreatedAt: datetime
    UpdatedAt: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VendorBase(BaseModel):
    Name: str
    ContactName: Optional[str] = None
    Email: Optional[EmailStr] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    Name: Optional[str] = None
    ContactName: Optional[str] = None
    Email: Optional[EmailStr] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None


class VendorOut(VendorBase):
    VendorId: int

    model_config = {"from_attributes": True}


class WorkOrderBase(BaseModel):
    Reference: Optional[str] = None
    DetailedAssetId: int
    ReportedByEmployeeId: Optional[int] = None
    ReportedByName: Optional[str] = None
    VendorId: Optional[int] = None
    VendorName: Optional[str] = None
    Status: Optional[str] = "open"
    RepairCost: Optional[float] = None
    Notes: Optional[str] = None


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderUpdate(BaseModel):
    Reference: Optional[str] = None
    DetailedAssetId: Optional[int] = None
    ReportedByEmployeeId: Optional[int] = None
    ReportedByName: Optional[str] = None
    VendorId: Optional[int] = None
    Status: Optional[str] = None
    RepairCost: Optional[float] = None
    Notes: Optional[str] = None


class WorkOrderOut(WorkOrderBase):
    WorkOrderId: int
    CreatedAt: datetime
    CompletedAt: Optional[datetime] = None

    model_config = {"from_attributes": True}
