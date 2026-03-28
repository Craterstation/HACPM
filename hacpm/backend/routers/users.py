"""User management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserUpdate, UserResponse
from ..services.points import get_user_total_points
from ..services.sync import broadcast_user_updated

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all users."""
    stmt = select(User).order_by(User.name)
    if active_only:
        stmt = stmt.where(User.is_active.is_(True))
    result = await db.execute(stmt)
    users = result.scalars().all()

    responses = []
    for user in users:
        total_pts = await get_user_total_points(db, user.id)
        resp = UserResponse.model_validate(user)
        resp.total_points = total_pts
        responses.append(resp)
    return responses


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single user by ID."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    total_pts = await get_user_total_points(db, user.id)
    resp = UserResponse.model_validate(user)
    resp.total_points = total_pts
    return resp


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user."""
    user = User(**data.model_dump())
    db.add(user)
    await db.flush()
    await db.refresh(user)
    resp = UserResponse.model_validate(user)
    await broadcast_user_updated(resp.model_dump(mode="json"))
    return resp


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update user details."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    total_pts = await get_user_total_points(db, user.id)
    resp = UserResponse.model_validate(user)
    resp.total_points = total_pts
    await broadcast_user_updated(resp.model_dump(mode="json"))
    return resp


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-delete a user (deactivate)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.flush()


@router.post("/{user_id}/verify-pin")
async def verify_pin(user_id: int, pin: str, db: AsyncSession = Depends(get_db)):
    """Verify a user's PIN (for kid account access)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.pin and user.pin != pin:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return {"valid": True}
