import logging
from typing import Literal
import re


logger = logging.getLogger("uvicorn")


class FileUtils:
    @staticmethod
    def get_document_type(
        mime_type: str,
    ) -> Literal["audio", "image", "video", "document", "other"]:
        """
        Get the category of a file based on its MIME type.
        """
        if mime_type.startswith("audio/"):
            return "audio"
        elif mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("video/"):
            return "video"

        # TODO: Implement a fine-grained document type classification
        # elif mime_type.startswith("application/") and any(
        #     doc_type in mime_type
        #     for doc_type in [
        #         "pdf",
        #         "msword",
        #         "vnd.openxmlformats-officedocument",
        #         "vnd.ms-excel",
        #         "vnd.ms-powerpoint",
        #         "rtf",
        #         "text/plain",
        #     ]
        # ):
        #     return "document"
        # return "other"

        return "document"

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to remove invalid characters"""
    sanitized = re.sub(r'[\\/:\*\?"<>\|\x00-\x1F\x7F\n\r\t]', '_', filename)
    sanitized = sanitized.strip().strip('.')

    if not sanitized:
        sanitized = "unnamed_file"

    return sanitized

def get_export_mime_type(mime_type: str, file_name: str) -> str:
    """Get export MIME type for Google Workspace documents"""
    if mime_type == "application/vnd.google-apps.document":
        return "application/pdf"
    elif mime_type == "application/vnd.google-apps.spreadsheet":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif mime_type == "application/vnd.google-apps.presentation":
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    else:
        return "application/pdf"

def update_file_extension(file_name: str, mime_type: str) -> str:
    """Update file extension based on MIME type"""
    if mime_type == "application/pdf" and not file_name.lower().endswith(".pdf"):
        return file_name + ".pdf"
    elif mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" and not file_name.lower().endswith(".xlsx"):
        return file_name + ".xlsx"
    elif mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation" and not file_name.lower().endswith(".pptx"):
        return file_name + ".pptx"
    return file_name
