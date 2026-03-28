import hashlib, logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from smtplib import SMTPException, SMTPConnectError
from ..database import get_db
from ..models import (User, AdminProfile, CustomerProfile, ServiceAgentProfile, EngineerProfile, RefreshToken,
                      UserType)
from ..schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, DeactivateRequest, ResendVerificationRequest
from ..email import send_verification_email, send_already_verified_email
from ..security import (hash_password, verify_password, create_access_token, create_refresh_token,
                        create_verification_token, decode_verification_token)
from ..config import settings
from ..dependencies import require_admin

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


# add delete user account and deactivate account endpoint, add email verification flow, add password reset flow.
# add background tasks for email sending once this is successful
# TODO: update the query format everywhere
# TODO: do the name email thingy

# TODO - add checks to make sure only admins can register staff accounts

@router.post("/register", response_model=dict, status_code=201)
async def register(payload: RegisterRequest,
                   db: AsyncSession = Depends(get_db),
                   background_tasks: BackgroundTasks = BackgroundTasks()):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        user_type=payload.user_type,
        is_verified=False
    )
    db.add(user)
    await db.flush()  # get user.id without committing yet

    # Create type-specific profile
    if payload.user_type == UserType.customer:
        db.add(CustomerProfile(user_id=user.id, full_name=payload.full_name))
    elif payload.user_type == UserType.engineer:
        db.add(EngineerProfile(user_id=user.id, company_name=payload.company_name))
    elif payload.user_type == UserType.admin:
        db.add(AdminProfile(user_id=user.id, department=payload.department))
    elif payload.user_type == UserType.service_agent:
        db.add(CustomerProfile(user_id=user.id, full_name=payload.full_name))

    await db.commit()

    # Fire-and-forget: don't fail registration if email fails
    token = create_verification_token(str(user.id), user.email)
    try:
        background_tasks.add_task(send_verification_email, user.email, token)
    except (SMTPConnectError, ConnectionRefusedError) as e:
        # Service is down - log as CRITICAL
        logger.critical(f"Email server unreachable: {e}")
        # Next step: Queue this for a background retry task
    except SMTPException as e:
        # SMTP specific logic error (Auth, Refused, etc)
        logger.error(f"SMTP error sending to {user.email}: {e}")
    except Exception as e:
        # Catch-all for unexpected internal issues
        logger.error(f"Unexpected error in email flow: {e}")

    return {"message": "Registered successfully", "user_id": str(user.id)}


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Check your inbox or request a new verification email."
        )

    # Issue tokens
    access_token = create_access_token(str(user.id), user.user_type.value)
    raw_refresh, hashed_refresh = create_refresh_token()

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            days=settings.refresh_token_expire_days),
    ))
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Rotate: revoke old, issue new
    stored.revoked = True
    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one()

    access_token = create_access_token(str(user.id), user.user_type.value)
    raw_refresh, hashed_refresh = create_refresh_token()

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=settings.refresh_token_expire_days),
    ))
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/logout")
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash.is_(token_hash),
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )

    stored = result.scalar_one_or_none()
    if stored:
        stored.revoked = True
        await db.commit()
    else:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return {"message": "Logged out"}


@router.post("/deactivate")
async def deactivate_account(
        payload: DeactivateRequest,
        admin: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == payload.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.commit()
    return {"message": "Account deactivated"}


@router.post("/re-activate")
async def reactivate_account(
        payload: DeactivateRequest,
        admin: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == payload.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    await db.commit()
    return {"message": "Account re-activated"}


@router.get("/verify-email")
async def verify_email(token: str,
                       db: AsyncSession = Depends(get_db),
                       background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        payload = decode_verification_token(token)
    except ValueError as e:
        raise HTTPException(400, str(e))

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    if user.is_verified:
        # Idempotent — don't error, just notify
        background_tasks.add_task(send_already_verified_email, user.email)
        return {"message": "Already verified"}

    user.is_verified = True
    await db.commit()
    return {"message": "Email verified. You can now log in."}


@router.post("/resend-verification")
async def resend_verification(
    payload: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # Look up user by the provided email
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        # Keep current behavior: report not found
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        # Idempotent — notify and return
        background_tasks.add_task(send_already_verified_email, user.email)
        return {"message": "Already verified"}

    token = create_verification_token(str(user.id), user.email)
    try:
        background_tasks.add_task(send_verification_email, user.email, token)
    except (SMTPConnectError, ConnectionRefusedError) as e:
        logger.critical(f"Email server unreachable: {e}")
    except SMTPException as e:
        logger.error(f"SMTP error sending to {user.email}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in email flow: {e}")

    return {"message": "Verification email resent"}
