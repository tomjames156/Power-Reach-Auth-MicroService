import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from .database import Base

# update the display id to use a sequence to handle race conditions

class UserType(str, enum.Enum):
    admin    = "admin"
    customer = "customer"
    service_agent = "service_agent"
    engineer = "engineer"

class User(Base):
    __tablename__ = "users"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email            = Column(String, unique=True, nullable=False, index=True)
    hashed_password  = Column(String, nullable=False)
    user_type        = Column(Enum(UserType), nullable=False)
    is_active        = Column(Boolean, default=True)
    is_verified      = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=datetime.now(timezone.utc).replace(tzinfo=None))

    admin_profile    = relationship("AdminProfile",    back_populates="user", uselist=False)
    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False)
    service_agent_profile   = relationship("ServiceAgentProfile",   back_populates="user",
                                           uselist=False)
    engineer_profile = relationship("EngineerProfile",  back_populates="user", uselist=False)
    refresh_tokens   = relationship("RefreshToken",    back_populates="user")

class AdminProfile(Base):
    __tablename__ = "admin_profiles"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    display_id = Column(String(20), unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    profile_picture_url = Column(String)
    branch = Column(String, nullable=False)
    last_updated_at = Column(DateTime, default=datetime.now(timezone.utc).replace(tzinfo=None),
                             onupdate=datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship("User", back_populates="admin_profile")

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    display_id = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    meter_number = Column(String, unique=True, index=True)
    address = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    profile_picture_url = Column(String)
    last_updated_at = Column(DateTime, default=datetime.now(timezone.utc).replace(tzinfo=None),
                             onupdate=datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship("User", back_populates="customer_profile")

class ServiceAgentProfile(Base):
    __tablename__ = "service_agent_profiles"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    display_id = Column(String(20), unique=True, index=True, nullable=False)
    full_name   = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    profile_picture_url = Column(String)
    last_updated_at = Column(DateTime, default=datetime.now(timezone.utc).replace(tzinfo=None),
                             onupdate=datetime.now(timezone.utc).replace(tzinfo=None))

    registered_by = relationship("AdminProfile", backref="registered_service_agents")
    user        = relationship("User", back_populates="service_agent_profile")

class EngineerProfile(Base):
    __tablename__ = "engineer_profiles"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    display_id = Column(String(20), unique=True, index=True, nullable=False)
    branch = Column(String, nullable=False)
    specialisation = Column(String, nullable=False)
    profile_picture_url = Column(String)
    last_updated_at = Column(DateTime, default=datetime.now(timezone.utc).replace(tzinfo=None),
                             onupdate=datetime.now(timezone.utc).replace(tzinfo=None))

    registered_by = relationship("AdminProfile", backref="registered_engineers")
    user = relationship("User", back_populates="engineer_profile")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked    = Column(Boolean, default=False)
    user       = relationship("User", back_populates="refresh_tokens")