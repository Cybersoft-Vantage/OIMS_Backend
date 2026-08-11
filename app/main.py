import logging

from fastapi import FastAPI
from sqlalchemy import inspect, text
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, ensure_soft_delete_columns, SessionLocal
from . import models, crud, security
from .routes import auth, employees, assets, detailed_assets
from .routes import detailed_assignments, procurement, maintenance, licensing, employee_portal

app = FastAPI(title="OIMS Backend")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    try:
        ensure_soft_delete_columns()
        logging.info('ensure_soft_delete_columns completed successfully')
    except Exception:
        logging.exception('ensure_soft_delete_columns failed')

    logging.info('Database URL resolved: %s', str(engine.url))
    logging.info('Using DB dialect: %s', engine.dialect.name)

    # Seed default admin employee (EmployeeDetail-only auth)
    try:
        db = SessionLocal()
        try:
            existing_admin_employee = db.query(models.EmployeeDetail).filter(models.EmployeeDetail.UserId == "admin").first()
            if not existing_admin_employee:
                admin_employee = models.EmployeeDetail(
                    UserId="admin",
                    FullName="System Administrator",
                    Department="IT",
                    Designation="Administrator",
                    Email="admin@example.com",
                    Phone="000-000-0000",
                    Role="admin",
                    IsActive=1,
                    Verify=1,
                    PasswordHash=security.get_password_hash("adminpass123"),
                )
                db.add(admin_employee)
                db.commit()
                db.refresh(admin_employee)
            else:
                changed = False
                if existing_admin_employee.Email != "admin@example.com":
                    existing_admin_employee.Email = "admin@example.com"
                    changed = True
                if (existing_admin_employee.Role or "").lower() != "admin":
                    existing_admin_employee.Role = "admin"
                    changed = True
                if int(existing_admin_employee.Verify or 0) != 1:
                    existing_admin_employee.Verify = 1
                    changed = True
                if not existing_admin_employee.PasswordHash:
                    existing_admin_employee.PasswordHash = security.get_password_hash("adminpass123")
                    changed = True
                if changed:
                    db.commit()
        finally:
            db.close()
    except Exception:
        pass

    # Seed example DetailedCategories if none exist
    try:
        db = SessionLocal()
        try:
            existing = db.query(models.DetailedCategory).count()
            if existing == 0:
                examples = [
                    models.DetailedCategory(
                        Name="Hardware",
                        Description="Computer hardware",
                        CustomSchema='[]'
                    ),
                    models.DetailedCategory(
                        Name="Networking",
                        Description="Networking devices",
                        CustomSchema='[]'
                    )
                ]
                db.add_all(examples)
                db.commit()
                # add a sample child category
                hw = db.query(models.DetailedCategory).filter(models.DetailedCategory.Name == "Hardware").first()
                if hw:
                    laptop = models.DetailedCategory(
                        Name="Laptops",
                        ParentId=hw.DetailedCategoryId,
                        Description="Portable computers issued to staff",
                        CustomSchema='[]'
                    )
                    db.add(laptop)
                    db.commit()
        finally:
            db.close()
    except Exception:
        # non-fatal seed failure
        pass

    # Recreate ProcurementRequests if old FK schema still exists
    try:
        inspector = inspect(engine)
        if 'ProcurementRequests' in inspector.get_table_names():
            fks = inspector.get_foreign_keys('ProcurementRequests')
            category_fk = next((fk for fk in fks if 'CategoryId' in fk['constrained_columns']), None)
            if category_fk and category_fk.get('referred_table') == 'Categories':
                with engine.begin() as conn:
                    conn.execute(text('DROP TABLE IF EXISTS "ProcurementRequests"'))
                Base.metadata.create_all(bind=engine, tables=[models.ProcurementRequest.__table__])
    except Exception:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200", "http://169.58.61.53:8081", "http:///127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(assets.router)
app.include_router(detailed_assets.router)
app.include_router(detailed_assignments.router)
app.include_router(procurement.router)
app.include_router(maintenance.router)
app.include_router(licensing.router)
app.include_router(employee_portal.router)

# Backward compatibility for clients still using /api prefix.
app.include_router(auth.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(detailed_assets.router, prefix="/api")
app.include_router(detailed_assignments.router, prefix="/api")
app.include_router(procurement.router, prefix="/api")
app.include_router(maintenance.router, prefix="/api")
app.include_router(licensing.router, prefix="/api")
app.include_router(employee_portal.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
