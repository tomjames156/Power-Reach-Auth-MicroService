from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import User, CustomerProfile, VendorProfile
from ..dependencies import get_current_user, require_admin, require_customer, require_vendor, require_staff
from ..schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Any authenticated user can fetch their own profile."""
    return current_user

@router.get("/admin/dashboard")
async def admin_dashboard(admin: User = Depends(require_admin)):
    return {"message": f"Welcome, admin {admin.email}", "department": admin.admin_profile.department}

@router.get("/customer/orders")
async def customer_orders(
    customer: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.execute(
        select(CustomerProfile).where(CustomerProfile.user_id == customer.id)
    )
    p = profile.scalar_one()
    return {"tier": p.tier, "orders": []}  # wire up your orders service here

@router.get("/vendor/products")
async def vendor_products(vendor: User = Depends(require_vendor)):
    return {"company": vendor.vendor_profile.company_name, "products": []}

@router.get("/staff/reports")
async def staff_reports(staff: User = Depends(require_staff)):
    """Accessible by both admins and vendors."""
    return {"user_type": staff.user_type, "reports": []}