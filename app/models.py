import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from .database import Base

class UserType(str, enum.Enum):
    admin    = "admin"
    customer = "customer"
    vendor   = "vendor"

class User(Base):
    __tablename__ = "users"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email            = Column(String, unique=True, nullable=False, index=True)
    hashed_password  = Column(String, nullable=False)
    user_type        = Column(Enum(UserType), nullable=False)
    is_active        = Column(Boolean, default=True)
    is_verified      = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    admin_profile    = relationship("AdminProfile",    back_populates="user", uselist=False)
    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False)
    vendor_profile   = relationship("VendorProfile",   back_populates="user", uselist=False)
    refresh_tokens   = relationship("RefreshToken",    back_populates="user")

class AdminProfile(Base):
    __tablename__ = "admin_profiles"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    department  = Column(String)
    permissions = Column(ARRAY(String), default=[])
    user        = relationship("User", back_populates="admin_profile")

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    full_name = Column(String)
    phone     = Column(String)
    tier      = Column(String, default="free")  # free, pro, enterprise
    user      = relationship("User", back_populates="customer_profile")

class VendorProfile(Base):
    __tablename__ = "vendor_profiles"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    company_name = Column(String)
    tax_id       = Column(String)
    is_approved  = Column(Boolean, default=False)
    user         = relationship("User", back_populates="vendor_profile")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked    = Column(Boolean, default=False)
    user       = relationship("User", back_populates="refresh_tokens")