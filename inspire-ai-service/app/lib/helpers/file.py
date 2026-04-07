import os
import tempfile

from fastapi import UploadFile

from app.settings import settings



def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return filename.split(".")[-1] if filename else ""


def delete_file_from_disk(file_path: str):
    """Delete file in disk"""
    if os.path.exists(file_path):
        os.remove(file_path)


async def save_upload_file_to_disk(file: UploadFile) -> str:
    """Save uploaded file to disk and return file path"""
    if not os.path.exists(settings.infra.file_storage.data_dir):
        os.makedirs(settings.infra.file_storage.data_dir)

    file_path = os.path.joinsettings.infra.file_storage.data_dir, file.filename

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return file_path

async def create_temp_file(
    content: bytes | None = None
) -> str:
    """
    Create a temporary file from a URL.
    """
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(content)
    return f.name
