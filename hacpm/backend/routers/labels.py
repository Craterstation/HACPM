"""Label management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Label
from ..schemas import LabelCreate, LabelUpdate, LabelResponse

router = APIRouter(prefix="/api/labels", tags=["labels"])


@router.get("/", response_model=list[LabelResponse])
async def list_labels(db: AsyncSession = Depends(get_db)):
    """List all labels."""
    result = await db.execute(select(Label).order_by(Label.name))
    return result.scalars().all()


@router.get("/{label_id}", response_model=LabelResponse)
async def get_label(label_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single label."""
    label = await db.get(Label, label_id)
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    return label


@router.post("/", response_model=LabelResponse, status_code=201)
async def create_label(data: LabelCreate, db: AsyncSession = Depends(get_db)):
    """Create a new label."""
    # Check for duplicate name
    existing = await db.execute(select(Label).where(Label.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Label with this name already exists")
    label = Label(**data.model_dump())
    db.add(label)
    await db.flush()
    await db.refresh(label)
    return label


@router.put("/{label_id}", response_model=LabelResponse)
async def update_label(label_id: int, data: LabelUpdate, db: AsyncSession = Depends(get_db)):
    """Update a label."""
    label = await db.get(Label, label_id)
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(label, field, value)
    await db.flush()
    await db.refresh(label)
    return label


@router.delete("/{label_id}", status_code=204)
async def delete_label(label_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a label."""
    label = await db.get(Label, label_id)
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    await db.delete(label)
