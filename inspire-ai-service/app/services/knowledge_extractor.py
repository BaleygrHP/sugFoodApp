from app.core.logger import get_logger
from app.tasks.extract_rules import extract_rules_from_histories

logger = get_logger(__name__)


class KnowledgeExtractorService:
    def extract_rules_from_histories(self, extraction_session_id: str, tenant_id: str, language: str) -> dict[str, any]:
        """
        Trigger rules extraction based on tenant configuration.
        """
        try:
            task = extract_rules_from_histories.delay(extraction_session_id, tenant_id, language)

            return {
                "tenant_id": tenant_id,
                "task_id": task.id,
                "message": "Rules extraction has been triggered successfully.",
            }
        except Exception as e:
            logger.exception(f"Failed to start rules extraction for tenant {tenant_id}")
            return {
                "status": "Error",
                "tenant_id": tenant_id,
                "message": f"Failed to start rules extraction: {e!s}",
            }
