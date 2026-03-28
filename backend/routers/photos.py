"""Photo upload and management routes."""

import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Task, TaskPhoto

router = APIRouter(prefix="/api/photos", tags=["photos"])

PHOTOS_PATH = os.environ.get("HACPM_PHOTOS_PATH", "/data/photos")


@router.post("/upload/{task_id}", status_code=201)
async def upload_photo(
    task_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a photo and attach it to a task."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Use JPEG, PNG, GIF, or WebP.",
        )

    # Generate unique filename
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    unique_name = f"{task_id}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(PHOTOS_PATH, unique_name)

    # Ensure directory exists
    os.makedirs(PHOTOS_PATH, exist_ok=True)

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Create DB record
    photo = TaskPhoto(
        task_id=task_id,
        file_path=file_path,
        filename=file.filename or unique_name,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)

    return {
        "id": photo.id,
        "filename": photo.filename,
        "uploaded_at": photo.uploaded_at.isoformat(),
    }


@router.get("/{photo_id}")
async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    """Download/view a photo by ID."""
    photo = await db.get(TaskPhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    if not os.path.exists(photo.file_path):
        raise HTTPException(status_code=404, detail="Photo file not found on disk")
    return FileResponse(photo.file_path)


@router.delete("/{photo_id}", status_code=204)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a photo."""
    photo = await db.get(TaskPhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Remove file from disk
    if os.path.exists(photo.file_path):
        os.remove(photo.file_path)

    await db.delete(photo)
