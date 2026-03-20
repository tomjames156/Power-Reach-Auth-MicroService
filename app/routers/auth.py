from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone, tzinfo
import hashlib
from ..database import get_db
from ..models import User, AdminProfile, CustomerProfile, VendorProfile, RefreshToken, UserType
from ..schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, DeactivateRequest
from ..security import hash_password, verify_password, create_access_token, create_refresh_token
from ..config import settings
from ..dependencies import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])

# add delete user account and deactivate account endpoint, add email verification flow, add password reset flow.

@router.post("/register", response_model=dict, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        user_type=payload.user_type,
    )
    db.add(user)
    await db.flush()  # get user.id without committing yet

    # Create type-specific profile
    if payload.user_type == UserType.customer:
        db.add(CustomerProfile(user_id=user.id, full_name=payload.full_name))
    elif payload.user_type == UserType.vendor:
        db.add(VendorProfile(user_id=user.id, company_name=payload.company_name))
    elif payload.user_type == UserType.admin:
        db.add(AdminProfile(user_id=user.id, department=payload.department))

    await db.commit()
    return {"message": "Registered successfully", "user_id": str(user.id)}


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

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
            RefreshToken.token_hash == token_hash,
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