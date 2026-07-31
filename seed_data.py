from app.database import SessionLocal, engine, Base
from app import models
import datetime


def seed():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed EmployeeDetail (4-5 fields each)
        if not db.query(models.EmployeeDetail).first():
            employees = [
                models.EmployeeDetail(UserId="U001", FullName="Alice Smith", Department="IT", Designation="Engineer", Email="alice.smith@example.com", Phone="555-0101"),
                models.EmployeeDetail(UserId="U002", FullName="Bob Jones", Department="HR", Designation="Manager", Email="bob.jones@example.com", Phone="555-0102"),
                models.EmployeeDetail(UserId="U003", FullName="Carol Lee", Department="Finance", Designation="Analyst", Email="carol.lee@example.com", Phone="555-0103"),
                models.EmployeeDetail(UserId="U004", FullName="David Park", Department="Operations", Designation="Coordinator", Email="david.park@example.com", Phone="555-0104"),
            ]
            db.add_all(employees)
            db.commit()

        # Seed Categories
        if not db.query(models.Category).first():
            categories = [
                models.Category(CategoryName="Laptops", Description="Portable computers"),
                models.Category(CategoryName="Monitors", Description="Display screens"),
                models.Category(CategoryName="Peripherals", Description="Keyboards, mice, etc."),
            ]
            db.add_all(categories)
            db.commit()

        # Seed SubCategories
        first_cat = db.query(models.Category).first()
        if first_cat and not db.query(models.SubCategory).first():
            subcategories = [
                models.SubCategory(CategoryId=first_cat.CategoryId, SubCategoryName="Ultrabooks", Description="Thin and light laptops"),
                models.SubCategory(CategoryId=first_cat.CategoryId, SubCategoryName="Gaming Laptops", Description="High performance laptops"),
            ]
            db.add_all(subcategories)
            db.commit()

        # Seed AssetStatus
        if not db.query(models.AssetStatus).first():
            statuses = [
                models.AssetStatus(StatusName="available"),
                models.AssetStatus(StatusName="in_use"),
                models.AssetStatus(StatusName="maintenance"),
            ]
            db.add_all(statuses)
            db.commit()

        # Seed Assets
        if not db.query(models.Asset).first():
            asset = models.Asset(
                AssetCode="A-1001",
                CategoryId=first_cat.CategoryId if first_cat else None,
                AssetName="Dell XPS 13",
                Brand="Dell",
                Model="XPS 13 9310",
                SerialNumber="SN123456",
                MacAddress="00:11:22:33:44:55",
                PurchaseDate=datetime.date(2022, 1, 15),
                PurchasePrice=1200.00,
                StatusId=db.query(models.AssetStatus).filter(models.AssetStatus.StatusName == "available").first().StatusId,
            )
            db.add(asset)
            db.commit()

        # Seed AssetComponent
        asset_rec = db.query(models.Asset).first()
        subcat = db.query(models.SubCategory).first()
        if asset_rec and subcat and not db.query(models.AssetComponent).first():
            comp = models.AssetComponent(
                AssetId=asset_rec.AssetId,
                SubCategoryId=subcat.SubCategoryId,
                ComponentName="Charger",
                Brand="Dell",
                Model="65W",
                SerialNumber="CHG-0001",
                Quantity=1,
            )
            db.add(comp)
            db.commit()

        # Seed AssetAssignment
        emp = db.query(models.EmployeeDetail).first()
        if asset_rec and emp and not db.query(models.AssetAssignment).first():
            assign = models.AssetAssignment(
                AssetId=asset_rec.AssetId,
                EmployeeId=emp.EmployeeId,
                AssignedDate=datetime.date.today(),
                AssignedBy="seed",
                Remarks="Initial seeded assignment",
            )
            db.add(assign)
            db.commit()

        # Seed AssetHistory
        if asset_rec and emp and not db.query(models.AssetHistory).first():
            history = models.AssetHistory(
                AssetId=asset_rec.AssetId,
                EmployeeId=emp.EmployeeId,
                Action="assigned",
                Notes="Seeded initial assignment",
            )
            db.add(history)
            db.commit()

        print("Seeding complete")
    finally:
        db.close()


if __name__ == '__main__':
    seed()
from app.database import SessionLocal, engine, Base
from app import crud, models, security
import datetime

Base.metadata.create_all(bind=engine)

def main():
    db = SessionLocal()
    try:
        admin = crud.get_user_by_username(db, 'admin')
        if not admin:
            admin = crud.create_user(db, username='admin', password='adminpass123', email='admin@oims.local', full_name='Admin User', role='admin')
            print('Created admin user')
        else:
            print('Admin user already exists')

        employee = crud.get_user_by_username(db, 'employee')
        if not employee:
            employee = crud.create_user(db, username='employee', password='userpass123', email='employee@oims.local', full_name='Employee User', role='employee')
            print('Created employee user')
        else:
            print('Employee user already exists')

        if not db.query(models.Employee).filter(models.Employee.user_id == employee.id).first():
            db_employee = models.Employee(user_id=employee.id, department='IT', position='Support Engineer')
            db.add(db_employee)
            db.commit()
            print('Created employee profile')
        else:
            print('Employee profile already exists')

        equipment_list = [
            {
                'asset_id': 'EQ-1001',
                'category': 'Laptop',
                'brand': 'Dell',
                'model': 'Latitude 5540',
                'serial_number': 'SN-DEL123456',
                'status': 'assigned',
                'remarks': 'Assigned to IT support'
            },
            {
                'asset_id': 'EQ-1002',
                'category': 'Monitor',
                'brand': 'Samsung',
                'model': 'Odyssey',
                'serial_number': 'SN-SAM987654',
                'status': 'available',
                'remarks': 'Ready for deployment'
            }
        ]

        for equipment_data in equipment_list:
            existing = db.query(models.Equipment).filter(models.Equipment.asset_id == equipment_data['asset_id']).first()
            if not existing:
                equipment = models.Equipment(**equipment_data)
                db.add(equipment)
                print(f"Created equipment {equipment_data['asset_id']}")
            else:
                print(f"Equipment {equipment_data['asset_id']} already exists")
        db.commit()

        equipment = db.query(models.Equipment).filter(models.Equipment.asset_id == 'EQ-1001').first()
        employee_profile = db.query(models.Employee).filter(models.Employee.user_id == employee.id).first()
        if equipment and employee_profile and not db.query(models.Assignment).filter(models.Assignment.equipment_id == equipment.id, models.Assignment.employee_id == employee_profile.id).first():
            assignment = models.Assignment(equipment_id=equipment.id, employee_id=employee_profile.id, assigned_at=datetime.datetime.utcnow())
            db.add(assignment)
            equipment.status = 'assigned'
            db.commit()
            print('Created assignment for employee')
        else:
            print('Assignment already exists or required records missing')

    finally:
        db.close()


if __name__ == '__main__':
    main()
