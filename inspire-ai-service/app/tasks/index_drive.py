from app.lib.constants.source_type import SourceStatusEnum
from app.schemas.datasource import GoogleDriveData
from app.services.ai_service import AIService
from app.services.datasource.google_drive import GoogleDriveClient, GoogleDriveService
from app.settings import settings

from . import celery, logger
import os


@celery.task(name="index_google_drive")
def index_google_drive(google_drive_data: dict):
    """Index content from Google Drive"""
    drive_service = GoogleDriveService()

    # Add credentials from environment if not provided
    if "credentials" not in google_drive_data:
        google_drive_data["credentials"] = {}
    if not google_drive_data["credentials"].get("client_id"):
        google_drive_data["credentials"]["client_id"] = os.getenv("GOOGLE_API__CLIENT_ID")
    if not google_drive_data["credentials"].get("client_secret"):
        google_drive_data["credentials"]["client_secret"] = os.getenv("GOOGLE_API__CLIENT_SECRET")

    logger.info(f"Using credentials from task: "
               f"has_refresh_token={bool(google_drive_data.get('credentials', {}).get('refresh_token'))}, "
               f"has_client_id={bool(google_drive_data.get('credentials', {}).get('client_id'))}, "
               f"has_client_secret={bool(google_drive_data.get('credentials', {}).get('client_secret'))}, "
               f"has_access_token={bool(google_drive_data.get('credentials', {}).get('access_token'))}")

    drive_data = GoogleDriveData(**google_drive_data)

    try:
        result = drive_service.import_google_drive(drive_data)

        if result["status"] == "FAILED":
            # Callback to AI service removed - no longer needed
            return {
                "status": SourceStatusEnum.INDEXED_FAILED,
                "error": result.get("errors", ["Unknown error"]),
                "refDocIds": [],
            }

        # Callback to AI service removed - no longer needed

        return {
            "status": SourceStatusEnum.INDEXED,
            "refDocIds": result["ref_doc_ids"],
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error indexing Google Drive: {str(e)}")
        # Callback to AI service removed - no longer needed
        return {
            "status": SourceStatusEnum.INDEXED_FAILED,
            "error": str(e),
            "refDocIds": [],
        }


@celery.task(name="refresh_google_drive_channels")
def refresh_all_channels():
    """Refresh all active Google Drive watch channels"""
    try:
        # Get channels from AI service
        channels = AIService.get_google_drive_channels()

        if not channels:
            logger.info("No active Google Drive channels found")
            return

        drive_service = GoogleDriveService()
        webhook_url = f"{settings.infra.google_api.webhook_url}"

        for channel in channels:
            try:
                drive_client = drive_service.drive_client
                channel_info = drive_client.create_watch_channel(
                    channel_id=channel["channelId"],
                    webhook_url=webhook_url,
                    file_id=channel["fileId"]
                )

                logger.info(f"Refreshed watch channel {channel_info['id']} for source {channel['id']}")

            except Exception as e:
                logger.error(f"Failed to refresh channel for source {channel['id']}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in refresh_all_channels task: {str(e)}")
