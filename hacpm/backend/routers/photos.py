"""Photo upload and management routes with thumbnail generation."""

import os
import uuid
import aiofiles
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Task, TaskPhoto

router = APIRouter(prefix="/api/photos", tags=["photos"])

PHOTOS_PATH = os.environ.get("HACPM_PHOTOS_PATH", "/data/photos")
THUMB_SIZE = (120, 120)


def _generate_thumbnail(image_bytes: bytes, output_path: str) -> bool:
    """Generate a cropped square thumbnail from image bytes."""
    try:
        from PIL import Image

        img = Image.open(BytesIO(image_bytes))

        # Convert to RGB if necessary (handles RGBA, palette, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Crop to center square
        width, height = img.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        img = img.crop((left, top, left + side, top + side))

        # Resize to thumbnail
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)

        img.save(output_path, "JPEG", quality=80)
        return True
    except Exception:
        return False


@router.post("/upload/{task_id}", status_code=201)
async def upload_photo(
    task_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a photo and attach it to a task. Generates a cropped thumbnail."""
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

    # Generate unique filenames
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    unique_id = uuid.uuid4().hex
    unique_name = f"{task_id}_{unique_id}{ext}"
    thumb_name = f"{task_id}_{unique_id}_thumb.jpg"
    file_path = os.path.join(PHOTOS_PATH, unique_name)
    thumb_path = os.path.join(PHOTOS_PATH, thumb_name)

    # Ensure directory exists
    os.makedirs(PHOTOS_PATH, exist_ok=True)

    # Read file content
    content = await file.read()

    # Save original file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Generate thumbnail
    thumb_ok = _generate_thumbnail(content, thumb_path)

    # Create DB record
    photo = TaskPhoto(
        task_id=task_id,
        file_path=file_path,
        thumbnail_path=thumb_path if thumb_ok else None,
        filename=file.filename or unique_name,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)

    return {
        "id": photo.id,
        "filename": photo.filename,
        "has_thumbnail": thumb_ok,
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


@router.get("/{photo_id}/thumbnail")
async def get_photo_thumbnail(photo_id: int, db: AsyncSession = Depends(get_db)):
    """Get the cropped thumbnail for a photo."""
    photo = await db.get(TaskPhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    if not photo.thumbnail_path or not os.path.exists(photo.thumbnail_path):
        # Fall back to original if no thumbnail
        if os.path.exists(photo.file_path):
            return FileResponse(photo.file_path)
        raise HTTPException(status_code=404, detail="Photo file not found on disk")
    return FileResponse(photo.thumbnail_path)


@router.delete("/{photo_id}", status_code=204)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a photo and its thumbnail."""
    photo = await db.get(TaskPhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Remove files from disk
    if os.path.exists(photo.file_path):
        os.remove(photo.file_path)
    if photo.thumbnail_path and os.path.exists(photo.thumbnail_path):
        os.remove(photo.thumbnail_path)

    await db.delete(photo)
