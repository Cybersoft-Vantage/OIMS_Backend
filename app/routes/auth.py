from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
import datetime
import hashlib
import secrets
from .. import models, schemas, crud, security
from scripts.emailservice import send_otp_email
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
OTP_RESEND_COOLDOWN_SECONDS = 30


def _issue_session_response(employee: models.EmployeeDetail):
    access_token = security.create_access_token(data={"sub": employee.UserId})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": employee.Role or "employee",
        "username": employee.UserId,
        "email": employee.Email,
        "full_name": employee.FullName,
        "profile_image": employee.ProfileImage,
        "verification_required": False,
    }


def _generate_otp() -> str:
    return f"{secrets.randbelow(10000):04d}"


def _hash_otp(otp: str) -> str:
    payload = str(otp).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _hash_otp_legacy(otp: str) -> str:
    payload = f"{otp}:{security.SECRET_KEY}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _prepare_verification(employee: models.EmployeeDetail, otp: str):
    employee.VerificationOtpHash = _hash_otp(otp)
    employee.VerificationOtpExpiresAt = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    employee.VerificationOtpAttempts = 0
    employee.VerificationOtpSentAt = datetime.datetime.utcnow()
    employee.Verify = 0


def _seconds_until_resend(employee: models.EmployeeDetail) -> int:
    if not employee.VerificationOtpSentAt:
        return 0
    elapsed = (datetime.datetime.utcnow() - employee.VerificationOtpSentAt).total_seconds()
    remaining = OTP_RESEND_COOLDOWN_SECONDS - int(elapsed)
    return max(0, remaining)


def _challenge_response(employee: models.EmployeeDetail):
    return {
        "access_token": None,
        "token_type": None,
        "role": employee.Role or "employee",
        "username": employee.UserId,
        "email": employee.Email,
        "full_name": employee.FullName,
        "profile_image": employee.ProfileImage,
        "verification_required": True,
        "verification_message": "Email verification required. Check your inbox for the OTP.",
        "verification_identifier": employee.UserId or employee.Email,
        "retry_after_seconds": _seconds_until_resend(employee),
    }


def _has_valid_pending_otp(employee: models.EmployeeDetail) -> bool:
    if not employee.VerificationOtpHash or not employee.VerificationOtpExpiresAt:
        return False
    return employee.VerificationOtpExpiresAt > datetime.datetime.utcnow()


def _send_and_store_otp(employee: models.EmployeeDetail, db: Session):
    otp = _generate_otp()
    _prepare_verification(employee, otp)
    db.commit()
    db.refresh(employee)

    sent = send_otp_email(employee.Email, otp, employee.FullName or employee.UserId)
    if not sent:
        employee.VerificationOtpHash = None
        employee.VerificationOtpExpiresAt = None
        employee.VerificationOtpAttempts = 0
        employee.VerificationOtpSentAt = None
        db.commit()
        raise HTTPException(status_code=500, detail="Unable to send verification OTP.")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    employee = crud.get_employee_detail_by_user_id(db, user_id)
    if employee is None:
        raise credentials_exception
    return employee


@router.post("/signup", response_model=schemas.UserOut)
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_employee_detail_by_user_id(db, user_in.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    employee = crud.create_employee_detail(
        db,
        schemas.EmployeeDetailCreate(
            UserId=user_in.username,
            FullName=user_in.full_name or user_in.username,
            Email=user_in.email,
            Password=user_in.password,
            Role="employee",
            IsActive=1,
        )
    )
    return {
        "id": employee.EmployeeId,
        "username": employee.UserId,
        "email": employee.Email,
        "full_name": employee.FullName,
        "role": employee.Role or "employee",
    }


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = await request.json()
        identifier = body.get("identifier") or body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        identifier = form.get("identifier") or form.get("username")
        password = form.get("password")

    if not identifier or not password:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    employee = crud.get_employee_detail_by_identifier(db, identifier)
    if not employee or not employee.PasswordHash or not security.verify_password(password, employee.PasswordHash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    try:
        db.refresh(employee)
    except ProgrammingError:
        db.rollback()

    if employee and int(employee.Verify or 0) != 1:
        if not employee.Email:
            raise HTTPException(status_code=400, detail="Employee email is required for verification.")

        if _has_valid_pending_otp(employee):
            response = _challenge_response(employee)
            response["verification_message"] = "OTP already sent. It is valid for 10 minutes."
            return response

        _send_and_store_otp(employee, db)
        return _challenge_response(employee)

    return _issue_session_response(employee)


@router.post("/verify-email", response_model=schemas.Token)
def verify_email_otp(payload: dict, db: Session = Depends(get_db)):
    identifier = payload.get("identifier") or payload.get("username")
    otp = payload.get("otp") or payload.get("code")
    if not identifier or not otp:
        raise HTTPException(status_code=400, detail="Identifier and OTP are required.")

    normalized_otp = "".join(ch for ch in str(otp).strip() if ch.isdigit())
    if len(normalized_otp) != 4:
        raise HTTPException(status_code=400, detail="Enter a valid 4-digit OTP.")

    employee = crud.get_employee_detail_by_identifier(db, identifier)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee record not found")

    if int(employee.Verify or 0) == 1:
        return _issue_session_response(employee)

    if not employee.VerificationOtpHash or not employee.VerificationOtpExpiresAt:
        raise HTTPException(status_code=400, detail="No pending verification code found.")

    if employee.VerificationOtpExpiresAt < datetime.datetime.utcnow():
        crud.invalidate_employee_verification(db, employee)
        raise HTTPException(status_code=400, detail="Verification code has expired. Please sign in again.")

    if employee.VerificationOtpAttempts is not None and employee.VerificationOtpAttempts >= 5:
        crud.invalidate_employee_verification(db, employee)
        raise HTTPException(status_code=429, detail="Too many invalid verification attempts. Please request a new code.")

    otp_hash = _hash_otp(normalized_otp)
    otp_hash_legacy = _hash_otp_legacy(normalized_otp)
    if otp_hash != employee.VerificationOtpHash and otp_hash_legacy != employee.VerificationOtpHash:
        employee.VerificationOtpAttempts = int(employee.VerificationOtpAttempts or 0) + 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    employee.Verify = 1
    employee.EmailVerifiedAt = datetime.datetime.utcnow()
    employee.VerificationOtpHash = None
    employee.VerificationOtpExpiresAt = None
    employee.VerificationOtpAttempts = 0
    employee.VerificationOtpSentAt = None
    db.commit()
    db.refresh(employee)

    return _issue_session_response(employee)


@router.post("/resend-otp")
def resend_email_otp(payload: dict, db: Session = Depends(get_db)):
    identifier = payload.get("identifier") or payload.get("username")
    if not identifier:
        raise HTTPException(status_code=400, detail="Identifier is required.")

    employee = crud.get_employee_detail_by_identifier(db, identifier)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee record not found")

    if int(employee.Verify or 0) == 1:
        return {"message": "Email already verified.", "retry_after_seconds": 0}

    if not employee.Email:
        raise HTTPException(status_code=400, detail="Employee email is required for verification.")

    remaining = _seconds_until_resend(employee)
    if remaining > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {remaining} seconds before requesting a new OTP.",
            headers={"Retry-After": str(remaining)},
        )

    _send_and_store_otp(employee, db)
    return {"message": "OTP sent successfully.", "retry_after_seconds": OTP_RESEND_COOLDOWN_SECONDS}


@router.get("/me", response_model=schemas.UserSessionOut)
def read_current_user(current_user: models.EmployeeDetail = Depends(get_current_user), db: Session = Depends(get_db)):
    employee = None
    try:
        employee = crud.get_employee_detail_by_user_id(db, current_user.UserId)
    except ProgrammingError:
        db.rollback()
    return {
        "id": current_user.EmployeeId,
        "username": current_user.UserId,
        "email": current_user.Email,
        "full_name": current_user.FullName,
        "role": current_user.Role or "employee",
        "profile_image": employee.ProfileImage if employee else None,
        "employee": employee,
    }
