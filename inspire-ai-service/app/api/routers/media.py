from typing import List
import os
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from starlette.responses import JSONResponse

from app.services.file_storage import get_file_storage, LocalFileStorage
from app.settings import settings
from app.core.logger import get_logger

media_router = router = APIRouter(prefix="/media")

logger = get_logger(__name__)

def get_media_file_storage() -> LocalFileStorage:
    """Get file storage instance for media files"""
    return get_file_storage(settings.infra.file_storage)


@router.post("/save-files", response_model=dict)
async def save_files(
    files: List[UploadFile] = File(...),
    file_storage: LocalFileStorage = Depends(get_media_file_storage)
):
    """
    Save uploaded files to the media directory.

    This endpoint allows you to upload multiple files and save them
    to the media directory for later retrieval.

    Args:
        files: List of files to upload

    Returns:
        Dictionary containing the saved file paths and metadata
    """
    try:
        saved_files = []

        for file in files:
            if not file.filename:
                continue

            # Save file to media directory
            file_path = await file_storage.save_file(
                file=file,
                directory="media"
            )

            saved_files.append({
                "filename": file.filename,
                "path": file_path,
                "size": file.size if hasattr(file, 'size') else None,
                "content_type": file.content_type
            })

        return {
            "message": f"Successfully saved {len(saved_files)} files",
            "files": saved_files
        }

    except Exception as e:
        logger.error(f"Error saving media files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving files: {str(e)}")


@router.get("/preview/{path:path}")
async def preview_file(
    path: str,
    file_storage: LocalFileStorage = Depends(get_media_file_storage)
):
    """
    Serve a file from the media directory based on the given path.

    This endpoint allows you to retrieve and preview files that were
    previously uploaded to the media directory.

    Args:
        path: The relative path to the file within the media directory

    Returns:
        FileResponse containing the requested file
    """
    try:
        normalized_path = path.replace("\\", "/")

        data_dir = file_storage.data_dir.rstrip("/\\")
        media_prefix_in_data = f"{data_dir}/media/"

        if normalized_path.startswith(media_prefix_in_data):
            full_relative_path = normalized_path
        elif normalized_path.startswith("media/"):
            full_relative_path = f"{data_dir}/{normalized_path}"
        else:
            full_relative_path = f"{media_prefix_in_data}{normalized_path}"

        full_path = file_storage.get_file_path(full_relative_path)

        # Security check: ensure the path is within the configured media directory under data_dir
        expected_base = os.path.abspath(os.path.join(os.getcwd(), data_dir, "media"))

        if not os.path.abspath(full_path).startswith(expected_base):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Path is outside expected directory."
            )

        if not file_storage.file_exists(full_relative_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {path}"
            )

        file_stat = os.stat(full_path)
        file_size = file_stat.st_size

        filename = os.path.basename(full_path)

        return FileResponse(
            path=full_path,
            filename=filename,
            headers={
                "Content-Length": str(file_size),
                "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error serving media file {path}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error serving file: {str(e)}"
        )


@router.get("/list", response_model=dict)
async def list_media_files(
    file_storage: LocalFileStorage = Depends(get_media_file_storage)
):
    """
    List all files in the media directory.

    This endpoint provides a way to see all available media files
    that can be accessed via the preview endpoint.

    Returns:
        Dictionary containing list of available files with metadata
    """
    try:
        media_dir = os.path.join(file_storage.data_dir, "media")

        if not os.path.exists(media_dir):
            return {
                "message": "Media directory not found",
                "files": []
            }

        files = []
        for root, dirs, filenames in os.walk(media_dir):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, file_storage.data_dir)

                # Get file stats
                stat = os.stat(full_path)

                files.append({
                    "filename": filename,
                    "path": relative_path.replace("\\", "/"),  # Normalize path separators
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })

        return {
            "message": f"Found {len(files)} files in media directory",
            "files": files
        }

    except Exception as e:
        logger.error(f"Error listing media files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing files: {str(e)}"
        )
