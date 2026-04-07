from app.lib.constants.source_type import SourceType
from app.services.ai_service import AIService
from app.tasks.index_web import index_single_page
from .index_database_query import index_database_query

from . import celery, logger


@celery.task(name="reindex_all_datasources")
def reindex_all_datasources():
    try:
        jobs = AIService.get_jobs_need_run()
    except Exception as e:
        logger.error(f"Failed to fetch jobs: {e}")
        return

    for job in jobs:
        try:
            source = job.get("source")
            next_run_raw = job.get("nextRun")
            interval = job.get("interval")

            if not source or not next_run_raw:
                logger.warning(f"Skipping job {job.get('id')} due to missing source or nextRun.")
                continue

            source_id = source.get("id")
            source_type = source.get("type")
            source_doc_ids = source.get("docRefIds")
            source_path = source.get("path")
            source_metadata = source.get("metadata")

            # Call task according to source type
            if source_type == SourceType.WEB:
                logger.info(f"Delaying web index task for source {source_id}")
                index_single_page.delay(web_url=source_path, docIds=source_doc_ids)
            elif source_type == SourceType.DATABASE_QUERY:
                query = source_path
                uri = source_metadata.get("uri")
                logger.info(f"Delaying database query index task for source {source_id}")
                index_database_query.delay(query=query, uri=uri, metadata=source_metadata, docIds=source_doc_ids)
            elif source_type == SourceType.GOOGLE_DRIVE:
                # Extract credentials and paths from metadata
                access_token = source_metadata.get("accessToken")
                refresh_token = source_metadata.get("refreshToken")
                include_paths = source_metadata.get("includePaths", [])

                logger.info(
                    f"Delaying Google Drive index task for source {source_id}, "
                    f"paths count: {len(include_paths) if isinstance(include_paths, list) else 1}, "
                    f"interval: {interval}"
                )

                from .index_drive import index_google_drive
                index_google_drive.delay({
                    "sourceId": source_id,
                    "credentials": {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    },
                    "includePaths": include_paths,
                    "metadata": {"sourceId": source_id},
                    "interval": interval,  # Pass interval from job to preserve it during reindex
                })

        except Exception as e:
            logger.error(f"Error processing job {job.get('id')}: {e}")
