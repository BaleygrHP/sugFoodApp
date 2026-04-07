import datetime
import os
import shutil
from abc import ABC, abstractmethod

from fastapi import UploadFile

from app.core.logger import get_logger
from app.settings import settings
from app.settings.infra.file_storage import FileStorageSettings, FileStorageType

logger = get_logger(__name__)


class FileStorage(ABC):
    @abstractmethod
    async def save_file(self, file: UploadFile, directory: str = None, custom_filename: str = None) -> str:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def get_file_path(self, file_path: str) -> str:
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        pass


class LocalFileStorage(FileStorage):
    """Implementation of FileStorage for local file system"""

    def __init__(self):
        self.data_dir = settings.infra.file_storage.data_dir
        self.static_dir = settings.infra.file_storage.static_dir

        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.static_dir, exist_ok=True)

    async def save_file(self, file: UploadFile, directory: str = None, custom_filename: str = None) -> str:
        """
        Save an uploaded file to the local file system

        Args:
            file: The uploaded file
            directory: Optional subdirectory within data_dir
            custom_filename: Optional custom filename

        Returns:
            The relative file path (for storage in the database)
        """
        try:
            if custom_filename:
                filename = custom_filename
            else:
                file_name = os.path.splitext(os.path.basename(file.filename))[0] if file.filename else ""
                file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
                filename = f"{file_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{file_extension}"

            target_dir = self.data_dir
            if directory:
                target_dir = os.path.join(target_dir, directory)
                os.makedirs(target_dir, exist_ok=True)

            file_path = os.path.join(target_dir, filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            return os.path.relpath(file_path, start=os.getcwd())

        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise

    def delete_file(self, file_path: str) -> bool:
        """Delete a file from the local file system"""
        try:
            if self.file_exists(file_path):
                full_path = self.get_file_path(file_path)
                os.remove(full_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            return False

    def get_file_path(self, file_path: str) -> str:
        """Get the full file path for a stored file"""
        if os.path.isabs(file_path):
            return file_path

        return os.path.join(os.getcwd(), file_path)

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        full_path = self.get_file_path(file_path)
        return os.path.exists(full_path) and os.path.isfile(full_path)


def get_file_storage(settings: FileStorageSettings) -> FileStorage:
    """Get the file storage implementation"""

    if settings.type == FileStorageType.LOCAL:
        return LocalFileStorage()
    else:
        logger.error(f"Unsupported file storage type: {settings.type}")

    return LocalFileStorage()
