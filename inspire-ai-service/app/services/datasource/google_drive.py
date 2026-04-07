import os
import tempfile
import io
import uuid
import socket
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta

from fastapi import HTTPException

from app.core.index_manager import get_index_manager
from app.services.datasource.document import DocumentService
from app.core.logger import get_logger
from app.schemas.datasource import GoogleDriveData
from app.services.file_storage import get_file_storage
from app.settings import settings

logger = get_logger(__name__)

SOCKET_TIMEOUT = 300
socket.setdefaulttimeout(SOCKET_TIMEOUT)

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to remove invalid characters"""
    sanitized = re.sub(r'[\\/:\*\?"<>\|\x00-\x1F\x7F\n\r\t]', '_', filename)
    sanitized = sanitized.strip().strip('.')

    if not sanitized:
        sanitized = "unnamed_file"

    if sanitized != filename:
        logger.debug(f"Sanitized filename: '{filename}' -> '{sanitized}'")

    return sanitized


class GoogleDriveClient:
    """Client for interacting with Google Drive API"""

    SUPPORTED_MIME_TYPES = {
        'application/pdf': 'pdf',
        'application/vnd.google-apps.document': 'google-doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        'text/plain': 'txt',
        'text/csv': 'csv',
        'application/vnd.google-apps.spreadsheet': 'google-sheet',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.google-apps.presentation': 'google-slides',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        'application/vnd.ms-powerpoint': 'ppt',
        'text/markdown': 'md',
        'text/html': 'html',
        'application/rtf': 'rtf',
        'application/json': 'json',
    }

    FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'

    def __init__(self, credentials: Dict[str, Any]):
        """Initialize Google Drive client"""
        self.access_token = credentials.get("access_token")
        self.refresh_token = credentials.get("refresh_token")

        self.client_id = credentials.get("client_id") or os.getenv("GOOGLE_API__CLIENT_ID")
        self.client_secret = credentials.get("client_secret") or os.getenv("GOOGLE_API__CLIENT_SECRET")

        if not credentials.get("client_id") and settings.infra.google_api.client_id:
            logger.debug(f"Using client_id from environment variables")
        if not credentials.get("client_secret") and settings.infra.google_api.client_secret:
            logger.debug(f"Using client_secret from environment variables")

        self.drive_service = None

    def authenticate(self) -> bool:
        """Authenticate with Google Drive API"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials

            creds = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            self.drive_service = build('drive', 'v3', credentials=creds)
            return True

        except Exception as e:
            logger.error(f"Error authenticating with Google Drive: {str(e)}")
            return False

    def _execute_with_retry(self, api_call, max_retries: int = 3) -> Any:
        """Execute a Google Drive API call with retry logic"""
        if not self.drive_service:
            if not self.authenticate():
                raise Exception("Failed to authenticate with Google Drive")

        retry_count = 0
        while retry_count < max_retries:
            try:
                return api_call()
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise e
                logger.debug(f"Retry {retry_count}/{max_retries} - {str(e)}")

        raise Exception("Failed to execute API call after retries")

    def list_files(self, file_ids: List[str]) -> List[Dict[str, Any]]:
        """Get metadata for specific file IDs"""
        files = []

        for file_id in file_ids:
            try:
                get_file = lambda: self.drive_service.files().get(
                    fileId=file_id,
                    fields="id, name, mimeType, version"
                ).execute(num_retries=3)

                file = self._execute_with_retry(get_file)

                # Get all revisions for this file
                list_revisions = lambda: self.drive_service.revisions().list(
                    fileId=file_id,
                    fields="revisions(id,modifiedTime,lastModifyingUser,originalFilename)"
                ).execute()

                revisions = self._execute_with_retry(list_revisions)
                revision_list = revisions.get('revisions', [])

                logger.info(
                    f"Found file: {file.get('name')} "
                    f"(ID: {file.get('id')}, "
                    f"version: {file.get('version')})"
                )
                logger.info(f"Revisions for file {file.get('name')}:")
                for rev in revision_list:
                    logger.info(
                        f"  - Revision ID: {rev.get('id')}, "
                        f"Modified: {rev.get('modifiedTime')}, "
                        f"By: {rev.get('lastModifyingUser', {}).get('displayName', 'Unknown')}"
                    )

                files.append(file)
            except Exception as e:
                logger.warning(f"Error retrieving file {file_id}: {str(e)}")

        return files

    def is_folder(self, file_id: str) -> bool:
        """Check if a Google Drive ID is a folder"""
        try:
            get_file = lambda: self.drive_service.files().get(
                fileId=file_id,
                fields="mimeType,name"
            ).execute(num_retries=3)

            file = self._execute_with_retry(get_file)
            mime_type = file.get("mimeType", "")
            name = file.get("name", "unknown")
            is_folder = mime_type == self.FOLDER_MIME_TYPE

            logger.debug(f"ID {file_id} ({name}) is {'folder' if is_folder else 'file'}")
            return is_folder
        except Exception as e:
            logger.warning(f"Error checking if {file_id} is a folder: {str(e)}")
            return False

    def list_folder_contents(self, folder_id: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """List all files in a Google Drive folder"""
        all_files = []
        page_token = None

        try:
            query = f"'{folder_id}' in parents and trashed = false"

            while True:
                list_files = lambda: self.drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType)',
                    pageToken=page_token
                ).execute()

                response = self._execute_with_retry(list_files)
                items = response.get('files', [])

                for item in items:
                    if item.get('mimeType') == self.FOLDER_MIME_TYPE and recursive:
                        logger.debug(f"Processing subfolder: {item.get('name')} ({item.get('id')})")
                        subfolder_files = self.list_folder_contents(item.get('id'), recursive)
                        all_files.extend(subfolder_files)
                    else:
                        all_files.append(item)

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            return all_files

        except Exception as e:
            logger.error(f"Error listing folder contents for {folder_id}: {str(e)}")
            raise Exception(f"Failed to list folder contents: {str(e)}")

    def is_supported_file(self, mime_type: str) -> bool:
        """Check if a file is supported based on MIME type"""
        return mime_type in self.SUPPORTED_MIME_TYPES

    def download_file(self, file_id: str, file_name: str) -> Tuple[str, bytes]:
        """Download a file from Google Drive"""
        from googleapiclient.http import MediaIoBaseDownload

        try:
            get_metadata = lambda: self.drive_service.files().get(
                fileId=file_id,
                fields="mimeType, name"
            ).execute(num_retries=3)

            file_metadata = self._execute_with_retry(get_metadata)
            mime_type = file_metadata.get("mimeType", "")

            if not file_name:
                file_name = file_metadata.get("name", f"untitled-{file_id}")

            file_name = sanitize_filename(file_name)

            file_content = io.BytesIO()

            if mime_type.startswith("application/vnd.google-apps"):
                export_mime_type = self._get_export_mime_type(mime_type, file_name)
                file_name = self._update_file_extension(file_name, export_mime_type)
                request = self.drive_service.files().export_media(
                    fileId=file_id,
                    mimeType=export_mime_type
                )
            else:
                request = self.drive_service.files().get_media(fileId=file_id)

            downloader = MediaIoBaseDownload(file_content, request, chunksize=1024*1024*10)

            done = False
            retry_count = 0
            while not done:
                try:
                    status, done = downloader.next_chunk()
                    if status and status.progress() == 1.0:
                        logger.info(f"Downloaded file: {file_name}")
                except Exception as e:
                    retry_count += 1
                    if retry_count >= 3:
                        raise Exception(f"Failed to download after 3 retries: {str(e)}")
                    logger.warning(f"Download chunk failed, retrying {retry_count}/3: {str(e)}")

            return file_name, file_content.getvalue()

        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            raise Exception(f"Failed to download file: {str(e)}")

    def _get_export_mime_type(self, mime_type: str, file_name: str) -> str:
        """Get export MIME type for Google Workspace documents"""
        if mime_type == "application/vnd.google-apps.document":
            return "application/pdf"
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif mime_type == "application/vnd.google-apps.presentation":
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        else:
            return "application/pdf"

    def _update_file_extension(self, file_name: str, mime_type: str) -> str:
        """Update file extension based on MIME type"""
        if mime_type == "application/pdf" and not file_name.lower().endswith(".pdf"):
            return file_name + ".pdf"
        elif mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" and not file_name.lower().endswith(".xlsx"):
            return file_name + ".xlsx"
        elif mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation" and not file_name.lower().endswith(".pptx"):
            return file_name + ".pptx"
        return file_name

    def create_watch_channel(self, channel_id: str, webhook_url: str, file_id: str) -> Dict[str, Any]:
        """Create a watch channel for a specific Google Drive file

        Args:
            channel_id (str): Unique identifier for the channel
            webhook_url (str): URL to receive notifications
            file_id (str): The ID of the file to watch

        Returns:
            Dict[str, Any]: Channel information including:
                - id: Channel ID
                - resourceId: Resource ID for the channel
                - expiration: Channel expiration timestamp
        """
        try:
            # Log credentials info (without sensitive values)
            logger.info(f"Creating watch channel with credentials: "
                       f"has_refresh_token={bool(self.refresh_token)}, "
                       f"has_client_id={bool(self.client_id)}, "
                       f"has_client_secret={bool(self.client_secret)}, "
                       f"has_access_token={bool(self.access_token)}")

            # Ensure we have all required credentials
            if not all([self.refresh_token, self.client_id, self.client_secret]):
                missing = []
                if not self.refresh_token:
                    missing.append("refresh_token")
                if not self.client_id:
                    missing.append("client_id")
                if not self.client_secret:
                    missing.append("client_secret")
                raise Exception(f"Missing required credentials: {', '.join(missing)}")

            # Re-authenticate to ensure fresh token
            if not self.authenticate():
                raise Exception("Failed to authenticate for watch channel creation")

            channel = {
                'id': channel_id,
                'type': 'web_hook',
                'address': webhook_url,
                'expiration': int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
            }

            create_channel = lambda: self.drive_service.files().watch(
                fileId=file_id,
                body=channel
            ).execute()

            response = self._execute_with_retry(create_channel)

            logger.info(f"Created watch channel {channel_id} for file {file_id} with expiration {response.get('expiration')}")
            logger.info(f"Channel: {channel}")
            return response

        except Exception as e:
            logger.error(f"Error creating watch channel: {str(e)}")
            raise Exception(f"Failed to create watch channel: {str(e)}")

    def get_file_revisions(self, file_id: str) -> List[Dict[str, Any]]:
        """Get revision history for a specific file

        Args:
            file_id (str): The ID of the file to get revisions for
            max_results (int, optional): Maximum number of revisions to return. Defaults to 10.

        Returns:
            List[Dict[str, Any]]: List of revision objects containing:
                - id: Revision ID
                - modifiedTime: When the revision was made
                - lastModifyingUser: User who made the revision
                - originalFilename: Original file name
        """
        try:
            list_revisions = lambda: self.drive_service.revisions().list(
                fileId=file_id,
                fields="revisions(id,modifiedTime,lastModifyingUser,originalFilename)",
            ).execute()

            response = self._execute_with_retry(list_revisions)
            revisions = response.get('revisions', [])

            logger.debug(f"Found {len(revisions)} revisions for file {file_id}")
            return revisions[-1]

        except Exception as e:
            logger.error(f"Error getting revisions for file {file_id}: {str(e)}")
            raise Exception(f"Failed to get file revisions: {str(e)}")

class GoogleDriveService:
    """Service for handling Google Drive operations"""

    def __init__(self):
        self.file_storage = get_file_storage(settings.infra.file_storage)
        self.index_manager = get_index_manager()
        self._drive_client = None

    @property
    def drive_client(self) -> GoogleDriveClient:
        """Get or create Google Drive client"""
        if not self._drive_client:
            self._drive_client = GoogleDriveClient({})
        return self._drive_client

    def import_google_drive(self, google_drive: GoogleDriveData):
        """Import documents from Google Drive"""
        try:
            result = self._create_result_structure()

            drive_client = GoogleDriveClient(google_drive.credentials.model_dump())
            if not drive_client.authenticate():
                return self._handle_auth_failure(result)

            path_ids = google_drive.config.include_paths
            if not path_ids:
                return self._handle_no_paths(result)

            logger.info(f"Processing {len(path_ids)} input IDs with config: process_folders={google_drive.config.process_folders}, recursive={google_drive.config.recursive}")

            files_to_process = self._collect_files_to_process(
                drive_client,
                path_ids,
                google_drive.config.process_folders,
                google_drive.config.recursive
            )

            if not files_to_process:
                result["status"] = "COMPLETED"
                result["message"] = "No files found in Google Drive"
                return result

            # Get latest revision for each file
            latest_revision_id = None
            for file in files_to_process:
                try:
                    revisions = drive_client.get_file_revisions(file["id"])
                    if revisions:
                        latest_revision_id = revisions[-1]["id"]
                        break  # Only need the first file's revision
                except Exception as e:
                    logger.warning(f"Failed to get revision for file {file['id']}: {str(e)}")

            result["latest_revision_id"] = latest_revision_id

            # Create watch channel if channelId is provided
            channel_info = None
            if google_drive.metadata and google_drive.metadata.get("channelId"):
                try:
                    webhook_url = os.getenv("AI_SERVICE__URL") + "/api/v1/webhooks/google-drive"

                    channel_info = drive_client.create_watch_channel(
                        channel_id=google_drive.metadata["channelId"],
                        webhook_url=webhook_url,
                        file_id=google_drive.config.include_paths[0]
                    )

                    logger.info(f"Created watch channel {channel_info['id']} for file {google_drive.config.include_paths[0]} with expiration {channel_info['expiration']}")
                    result["channel_info"] = channel_info
                except Exception as e:
                    logger.error(f"Failed to create watch channel: {str(e)}")
                    # Continue with indexing even if watch channel creation fails

            return self._process_files(
                drive_client,
                files_to_process,
                result,
                google_drive
            )

        except Exception as e:
            logger.error(f"Error importing from Google Drive: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error importing from Google Drive: {str(e)}")

    def _create_result_structure(self) -> Dict[str, Any]:
        """Create the initial result structure for import operation"""
        return {
            "datasource_id": str(uuid.uuid4()),
            "type": "google_drive",
            "status": "IMPORTED",
            "items_processed": 0,
            "items_imported": 0,
            "ref_doc_ids": [],
            "errors": []
        }

    def _handle_auth_failure(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authentication failure"""
        result["status"] = "FAILED"
        result["errors"].append("Failed to authenticate with Google Drive")
        return result

    def _handle_no_paths(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case with no paths specified"""
        result["status"] = "FAILED"
        result["errors"].append("No file or folder IDs provided for import")
        return result

    def _collect_files_to_process(
        self,
        drive_client: GoogleDriveClient,
        path_ids: List[str],
        process_folders: bool,
        recursive: bool
    ) -> List[Dict[str, Any]]:
        """Collect all files to process from input IDs"""
        files_to_process = []

        for path_id in path_ids:
            is_folder = drive_client.is_folder(path_id)

            if is_folder:
                if not process_folders:
                    logger.info(f"Skipping folder ID: {path_id} (folder processing disabled)")
                    continue

                logger.info(f"Processing folder ID: {path_id}")
                folder_files = drive_client.list_folder_contents(path_id, recursive=recursive)
                logger.info(f"Found {len(folder_files)} files in folder {path_id}")
                files_to_process.extend(folder_files)
            else:
                logger.info(f"Processing single file ID: {path_id}")
                file_metadata = drive_client.list_files([path_id])
                if file_metadata:
                    files_to_process.extend(file_metadata)

        return files_to_process

    def _process_files(
        self,
        drive_client: GoogleDriveClient,
        files_to_process: List[Dict[str, Any]],
        result: Dict[str, Any],
        google_drive: GoogleDriveData
    ) -> Dict[str, Any]:
        """Process the collected files"""
        result["items_processed"] = len(files_to_process)
        all_doc_ids = []
        successful_imports = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            for file in files_to_process:
                file_id = file["id"]
                file_name = file["name"]
                mime_type = file.get("mimeType", "")

                if not self._should_process_file(drive_client, file_name, file_id, mime_type, result):
                    continue

                doc_ids = self._process_single_file(
                    drive_client,
                    file_id,
                    file_name,
                    temp_dir,
                    google_drive,
                    result
                )

                if doc_ids:
                    all_doc_ids.extend(doc_ids)
                    successful_imports += 1

        result["items_imported"] = successful_imports
        result["ref_doc_ids"] = all_doc_ids

        if successful_imports == 0 and result["items_processed"] > 0:
            result["status"] = "FAILED"
            result["errors"].append("No documents were imported")

        return result

    def _should_process_file(
        self,
        drive_client: GoogleDriveClient,
        file_name: str,
        file_id: str,
        mime_type: str,
        result: Dict[str, Any]
    ) -> bool:
        """Determine if file should be processed"""
        if mime_type == drive_client.FOLDER_MIME_TYPE:
            logger.debug(f"Skipping folder entry: {file_name} ({file_id})")
            return False

        if not drive_client.is_supported_file(mime_type):
            logger.warning(f"Skipping unsupported file type: {file_name} ({mime_type})")
            result["errors"].append(f"Skipped unsupported file type: {file_name} ({mime_type})")
            return False

        return True

    def _process_single_file(
        self,
        drive_client: GoogleDriveClient,
        file_id: str,
        file_name: str,
        temp_dir: str,
        google_drive: GoogleDriveData,
        result: Dict[str, Any]
    ) -> Optional[List[str]]:
        """Process a single file"""
        try:
            file_name, file_content = drive_client.download_file(file_id, file_name)
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            result["errors"].append(f"Failed to download {file_name}: {str(e)}")
            return None

        safe_file_name = sanitize_filename(file_name)

        temp_file_path = os.path.join(temp_dir, safe_file_name)
        try:
            with open(temp_file_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            logger.error(f"Error saving file {safe_file_name}: {str(e)}")
            result["errors"].append(f"Failed to save {safe_file_name}: {str(e)}")
            return None

        try:
            return self._index_document(
                temp_file_path,
                file_id,
                safe_file_name,
                google_drive,
                result
            )
        except Exception as e:
            logger.error(f"Error indexing file {safe_file_name}: {str(e)}")
            result["errors"].append(f"Failed to index {safe_file_name}: {str(e)}")
            return None

    def _index_document(
        self,
        file_path: str,
        file_id: str,
        file_name: str,
        google_drive: GoogleDriveData,
        result: Dict[str, Any]
    ) -> Optional[List[str]]:
        """Extract content and index a document"""
        documents = DocumentService.convert_file_to_documents(file_path=file_path, file_name=file_name)

        if not documents:
            logger.warning(f"No content extracted from file: {file_name}")
            result["errors"].append(f"No content extracted from file: {file_name}")
            return None

        metadata = {
            "source": f"google_drive:{file_id}",
            "file_name": file_name,
            "datasource_id": result["datasource_id"],
            **(google_drive.metadata or {})
        }

        for doc in documents:
            if doc.metadata:
                doc.metadata.update(metadata)
            else:
                doc.metadata = metadata

        self._create_index(documents, google_drive.config)

        doc_ids = [doc.id_ for doc in documents]
        logger.info(f"Successfully indexed file: {file_name} ({len(doc_ids)} chunks)")

        return doc_ids

    def _create_index(self, documents: List[Any], config: Any) -> None:
        """Create index with appropriate chunking settings"""
        chunk_size = config.chunk_size
        chunk_overlap = config.chunk_overlap

        if chunk_size or chunk_overlap:
            chunk_size = chunk_size or settings.llm.index.chunk_size
            chunk_overlap = chunk_overlap or settings.llm.index.chunk_overlap
            self.index_manager.create_index_with_custom_chunking(
                documents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        else:
            self.index_manager.create_index(documents)
