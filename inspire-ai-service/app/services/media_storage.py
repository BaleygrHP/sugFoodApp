"""Service for storing and managing media files (images from Google Docs, etc.)"""
import uuid
from pathlib import Path
from typing import Optional
from PIL import Image
import io

from app.core.logger import get_logger
from app.settings import settings

logger = get_logger(__name__)


class MediaStorageService:
    """Service for managing media file storage"""

    def __init__(self):
        """
        Initialize media storage service

        Args:
            None
        """
        self.data_dir = settings.infra.file_storage.data_dir

    def _get_storage_dir(self, subdirectory: str = "google_drive") -> Path:
        """
        Get the storage directory path for images

        Args:
            subdirectory: Subdirectory within media folder (e.g., 'google_drive', 'uploads')

        Returns:
            Path object for the storage directory
        """
        base_path = Path(self.data_dir) / "media"
        storage_path = base_path
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    def save_image(
        self,
        image_bytes: bytes,
        page_num: Optional[int] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Save an image to local storage and return the preview URL

        Args:
            image_bytes: Raw image bytes (PNG, JPEG, etc.)
            page_num: Optional page number in source document (not used, kept for compatibility)
            description: Optional LLM-generated description (not used, kept for compatibility)

        Returns:
            String URL for accessing the image via API
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size
            image_format = image.format.lower() if image.format else "png"

            ext = image_format if image_format in ["png", "jpeg", "jpg", "gif"] else "png"
            # Keep jpg as jpg for filename, but normalize to jpeg for mime type if needed
            filename = f"{uuid.uuid4()}.{ext}"

            # Get storage directory
            storage_dir = self._get_storage_dir()
            
            # Save file locally
            file_path = storage_dir / filename
            with open(file_path, "wb") as f:
                f.write(image_bytes)

            logger.info(f"Saved image locally: {file_path}")

            # Create relative path from data_dir
            relative_path = file_path.relative_to(Path(self.data_dir))
            relative_path_str = str(relative_path).replace("\\", "/")

            # Return preview URL
            preview_url = f"/api/v1/media/preview/{relative_path_str}"

            logger.info(f"Image preview URL: {preview_url}")

            return preview_url

        except Exception as e:
            logger.error(f"Error saving image to local storage: {str(e)}")
            raise

    def delete_image(self, image_path: str) -> bool:
        """
        Delete an image from storage

        Args:
            image_path: Relative path to the image file

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            file_path = Path.cwd() / image_path
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error deleting image {image_path}: {str(e)}")
            return False

    def image_exists(self, image_path: str) -> bool:
        """
        Check if an image exists in storage

        Args:
            image_path: Relative path to the image file

        Returns:
            True if the image exists, False otherwise
        """
        file_path = Path.cwd() / image_path
        return file_path.exists() and file_path.is_file()

    def get_full_path(self, image_path: str) -> str:
        """
        Get the full absolute path for an image

        Args:
            image_path: Relative path to the image file

        Returns:
            Absolute path to the image
        """
        return str(Path.cwd() / image_path)
