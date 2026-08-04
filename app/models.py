from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Date, Float, text
from sqlalchemy.orm import relationship
from .database import Base
import datetime
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="employee")


class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    department = Column(String, nullable=True)
    position = Column(String, nullable=True)
    user = relationship("User")


class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    model = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    status = Column(String, default="available")
    remarks = Column(Text, nullable=True)


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    employee_id = Column(Integer, ForeignKey("employees.id"))
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)


class EquipmentRequest(Base):
    __tablename__ = "equipment_requests"
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    employee_id = Column(Integer, ForeignKey("employees.id"))
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EmployeeDetail(Base):
    __tablename__ = "EmployeeDetail"

    EmployeeId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    UserId = Column(String, unique=True, index=True, nullable=False)
    FullName = Column(String, nullable=False)
    Department = Column(String, nullable=True)
    Designation = Column(String, nullable=True)
    Email = Column(String, nullable=True)
    Phone = Column(String, nullable=True)
    ProfileImage = Column(Text, nullable=True)
    IsActive = Column(Integer, default=1, server_default=text("1"))
    Role = Column(String(40), default="employee")
    PasswordHash = Column(String(255), nullable=True)
    Verify = Column(Integer, default=0, server_default=text("0"))
    EmailVerifiedAt = Column(DateTime, nullable=True)
    VerificationOtpHash = Column(String(128), nullable=True)
    VerificationOtpExpiresAt = Column(DateTime, nullable=True)
    VerificationOtpAttempts = Column(Integer, default=0, server_default=text("0"))
    VerificationOtpSentAt = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    assets = relationship("Asset", back_populates="current_employee", foreign_keys="[Asset.CurrentEmployeeId]")
    assignments = relationship("AssetAssignment", back_populates="employee", cascade="all, delete-orphan")
    history = relationship("AssetHistory", back_populates="employee", cascade="all, delete-orphan")
    detailed_assignments = relationship("DetailedAssetAssignment", back_populates="employee", cascade="all, delete-orphan")
    detailed_history = relationship("DetailedAssetHistory", back_populates="employee", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "Categories"

    CategoryId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    CategoryName = Column(String, nullable=False, unique=True)
    Description = Column(Text, nullable=True)
    IsActive = Column(Integer, default=1, server_default=text("1"))
    IsDeleted = Column(Integer, default=0, server_default=text("0"))
    DeletedAt = Column(DateTime, nullable=True)

    subcategories = relationship("SubCategory", back_populates="category", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="category")


class DetailedCategory(Base):
    __tablename__ = "DetailedCategories"

    DetailedCategoryId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Name = Column(String(80), nullable=False)
    ParentId = Column(Integer, ForeignKey("DetailedCategories.DetailedCategoryId"), nullable=True)
    SubcategoryTagName = Column(String(3), nullable=True)
    Description = Column(Text, nullable=True)
    CustomSchema = Column(Text, nullable=True)  # JSON stored as text
    IsDeleted = Column(Integer, default=0, server_default=text("0"))
    DeletedAt = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    parent = relationship("DetailedCategory", remote_side=[DetailedCategoryId], backref="children")


class DetailedAsset(Base):
    __tablename__ = "DetailedAssets"

    DetailedAssetId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    AssetTag = Column(String(40), nullable=True, unique=True)
    Name = Column(String(150), nullable=False)
    DetailedCategoryId = Column(Integer, ForeignKey("DetailedCategories.DetailedCategoryId"), nullable=True)
    SubCategory = Column(String(80), nullable=True)
    MakeModel = Column(String(120), nullable=True)
    SerialNo = Column(String(120), nullable=True, unique=True)
    Specifications = Column(Text, nullable=True)
    Status = Column(String(40), nullable=True)
    PurchaseCost = Column(Float, nullable=True)
    PurchaseDate = Column(Date, nullable=True)
    WarrantyEnd = Column(Date, nullable=True)
    SoldPrice = Column(Float, nullable=True)
    CustomValues = Column(Text, nullable=True)  # JSON stored as text
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    UpdatedAt = Column(DateTime, onupdate=func.now())
    IsDeleted = Column(Integer, default=0, server_default=text("0"))

    category = relationship("DetailedCategory")
    assignments = relationship("DetailedAssetAssignment", back_populates="asset", cascade="all, delete-orphan")
    history = relationship("DetailedAssetHistory", back_populates="asset", cascade="all, delete-orphan")
    workorders = relationship("WorkOrder", back_populates="asset", cascade="all, delete-orphan")


class Vendor(Base):
    __tablename__ = "Vendors"

    VendorId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Name = Column(String(150), nullable=False)
    ContactName = Column(String(120), nullable=True)
    Email = Column(String(120), nullable=True)
    Phone = Column(String(60), nullable=True)
    Address = Column(Text, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))


class WorkOrder(Base):
    __tablename__ = "WorkOrders"

    WorkOrderId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Reference = Column(String(64), unique=True, nullable=False)
    DetailedAssetId = Column(Integer, ForeignKey("DetailedAssets.DetailedAssetId"), nullable=False)
    ReportedByEmployeeId = Column(Integer, ForeignKey("EmployeeDetail.EmployeeId"), nullable=True)
    ReportedByName = Column(String(150), nullable=True)
    VendorId = Column(Integer, ForeignKey("Vendors.VendorId"), nullable=True)
    VendorName = Column(String(150), nullable=True)
    Status = Column(String(40), default="open")
    RepairCost = Column(Float, nullable=True)
    Notes = Column(Text, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    CompletedAt = Column(DateTime, nullable=True)

    asset = relationship("DetailedAsset", back_populates="workorders")
    vendor = relationship("Vendor")


class SubCategory(Base):
    __tablename__ = "SubCategories"

    SubCategoryId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    CategoryId = Column(Integer, ForeignKey("Categories.CategoryId"), nullable=False)
    SubCategoryName = Column(String, nullable=False)
    Description = Column(Text, nullable=True)
    IsDeleted = Column(Integer, default=0, server_default=text("0"))
    DeletedAt = Column(DateTime, nullable=True)

    category = relationship("Category", back_populates="subcategories")
    components = relationship("AssetComponent", back_populates="subcategory", cascade="all, delete-orphan")


class AssetStatus(Base):
    __tablename__ = "AssetStatus"

    StatusId = Column(Integer, primary_key=True, index=True)
    StatusName = Column(String, unique=True, nullable=False)
    IsDeleted = Column(Integer, default=0, server_default=text("0"))
    DeletedAt = Column(DateTime, nullable=True)

    assets = relationship("Asset", back_populates="status")


class Asset(Base):
    __tablename__ = "Assets"

    AssetId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    AssetCode = Column(String, unique=True, index=True, nullable=True)
    CategoryId = Column(Integer, ForeignKey("Categories.CategoryId"), nullable=True)
    SubCategoryId = Column(Integer, ForeignKey("SubCategories.SubCategoryId"), nullable=True)
    AssetName = Column(String, nullable=True)
    Brand = Column(String, nullable=True)
    Model = Column(String, nullable=True)
    SerialNumber = Column(String, unique=True, nullable=True)
    MacAddress = Column(String, unique=True, nullable=True)
    PurchaseDate = Column(Date, nullable=True)
    PurchasePrice = Column(Float, nullable=True)
    StatusId = Column(Integer, ForeignKey("AssetStatus.StatusId"), nullable=True)
    CurrentEmployeeId = Column(Integer, ForeignKey("EmployeeDetail.EmployeeId"), nullable=True)
    Remarks = Column(Text, nullable=True)
    IsAvailable = Column(Integer, default=1, server_default=text("1"))
    IsDeleted = Column(Integer, default=0, server_default=text("0"))
    DeletedAt = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    category = relationship("Category", back_populates="assets")
    status = relationship("AssetStatus", back_populates="assets")
    current_employee = relationship("EmployeeDetail", back_populates="assets")
    components = relationship("AssetComponent", back_populates="asset", cascade="all, delete-orphan")
    assignments = relationship("AssetAssignment", back_populates="asset", cascade="all, delete-orphan")
    history = relationship("AssetHistory", back_populates="asset", cascade="all, delete-orphan")


class AssetComponent(Base):
    __tablename__ = "AssetComponents"

    ComponentId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    AssetId = Column(Integer, ForeignKey("Assets.AssetId"), nullable=False)
    SubCategoryId = Column(Integer, ForeignKey("SubCategories.SubCategoryId"), nullable=True)
    ComponentCode = Column(String, unique=True, index=True, nullable=True)
    ComponentName = Column(String, nullable=True)
    Brand = Column(String, nullable=True)
    Model = Column(String, nullable=True)
    SerialNumber = Column(String, nullable=True)
    Quantity = Column(Integer, default=1, server_default=text("1"))
    Remarks = Column(Text, nullable=True)
    IsDeleted = Column(Integer, default=0, server_default=text("0"))
    DeletedAt = Column(DateTime, nullable=True)
    asset = relationship("Asset", back_populates="components")
    subcategory = relationship("SubCategory", back_populates="components")


class AssetAssignment(Base):
    __tablename__ = "AssetAssignments"

    AssignmentId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    AssetId = Column(Integer, ForeignKey("Assets.AssetId"), nullable=False)
    EmployeeId = Column(Integer, ForeignKey("EmployeeDetail.EmployeeId"), nullable=False)
    AssignedDate = Column(Date, nullable=True)
    ReturnedDate = Column(Date, nullable=True)
    AssignedBy = Column(String, nullable=True)
    Remarks = Column(Text, nullable=True)
    IsReturned = Column(Integer, default=0, server_default=text("0"))

    asset = relationship("Asset", back_populates="assignments")
    employee = relationship("EmployeeDetail", back_populates="assignments")


class DetailedAssetAssignment(Base):
    __tablename__ = "DetailedAssetAssignments"

    AssignmentId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    DetailedAssetId = Column(Integer, ForeignKey("DetailedAssets.DetailedAssetId"), nullable=False)
    EmployeeId = Column(Integer, ForeignKey("EmployeeDetail.EmployeeId"), nullable=False)
    AssignedDate = Column(Date, nullable=True)
    ReturnedDate = Column(Date, nullable=True)
    AssignedBy = Column(String, nullable=True)
    ReturnedBy = Column(String, nullable=True)
    Remarks = Column(Text, nullable=True)
    IsReturned = Column(Integer, default=0, server_default=text("0"))

    asset = relationship("DetailedAsset", back_populates="assignments")
    employee = relationship("EmployeeDetail", back_populates="detailed_assignments")


class DetailedAssetHistory(Base):
    __tablename__ = "DetailedAssetHistory"

    HistoryId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    DetailedAssetId = Column(Integer, ForeignKey("DetailedAssets.DetailedAssetId"), nullable=False)
    EmployeeId = Column(Integer, ForeignKey("EmployeeDetail.EmployeeId"), nullable=True)
    Action = Column(String, nullable=False)
    ActionDate = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    Notes = Column(Text, nullable=True)
    AssetTag = Column(String, nullable=True)
    AssetName = Column(String, nullable=True)
    EmployeeName = Column(String, nullable=True)
    
    # relationships
    asset = relationship("DetailedAsset", back_populates="history")
    employee = relationship("EmployeeDetail", back_populates="detailed_history")


class SoftwareLicense(Base):
    __tablename__ = "SoftwareLicenses"

    LicenseId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    SoftwareName = Column(String(200), nullable=False)
    Vendor = Column(String(200), nullable=True)
    LicenseKey = Column(String(255), nullable=True)
    Seats = Column(Integer, nullable=False, default=1)
    PurchaseDate = Column(Date, nullable=True)
    RenewalDate = Column(Date, nullable=True)
    Status = Column(String(40), nullable=False, default="Active")
    Notes = Column(Text, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    UpdatedAt = Column(DateTime, default=datetime.datetime.utcnow, onupdate=func.now())


class ProcurementRequest(Base):
    __tablename__ = "ProcurementRequests"

    ProcurementId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Reference = Column(String(32), unique=True, nullable=False)
    CategoryId = Column(Integer, ForeignKey("DetailedCategories.DetailedCategoryId"), nullable=True)
    SubCategoryId = Column(Integer, ForeignKey("DetailedCategories.DetailedCategoryId"), nullable=True)
    Item = Column(String(200), nullable=False)
    Quantity = Column(Integer, nullable=False, default=1)
    Status = Column(String(40), nullable=False, default="Pending")
    CreatedAt = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    # optional relationships (not strictly required for CRUD operations here)
    category = relationship("DetailedCategory", foreign_keys=[CategoryId])
    subcategory = relationship("DetailedCategory", foreign_keys=[SubCategoryId])


class AssetHistory(Base):
    __tablename__ = "AssetHistory"

    HistoryId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    AssetId = Column(Integer, ForeignKey("Assets.AssetId"), nullable=False)
    EmployeeId = Column(Integer, ForeignKey("EmployeeDetail.EmployeeId"), nullable=True)
    Action = Column(String, nullable=False)
    ActionDate = Column(DateTime, default=datetime.datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    Notes = Column(Text, nullable=True)
    AssetCode = Column(String, nullable=True)
    AssetName = Column(String, nullable=True)
    EmployeeName = Column(String, nullable=True)

    asset = relationship("Asset", back_populates="history")
    employee = relationship("EmployeeDetail", back_populates="history")
