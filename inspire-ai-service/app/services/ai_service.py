import requests

from app.core.logger import get_logger
from app.settings import settings

logger = get_logger(__name__)

class AIService:
    @staticmethod
    def get_jobs_need_run():
        """Fetch jobs that need to be run from the AI service"""
        headers = {
            "Content-Type": "application/json",
            "X-Is-Internal": "true"
        }

        url = f"{settings.ai_service.url}/api/v1/jobs/need-run"
        logger.info(f"Fetching jobs from: {url}")

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def send_indexing_callback(
        source_id: str,
        doc_ids: list[str],
        interval: str | None = None,
        status: str = "active",
        metadata: dict | None = None
    ):
        """Send callback to AI service for file indexing status"""
        headers = {
            "Content-Type": "application/json",
            "X-Is-Internal": "true"
        }

        payload = {
            "interval": interval,
            "sourceId": source_id,
            "status": status,
            "docIds": doc_ids,
            "metadata": metadata
        }

        logger.info(f"Sending callback to AI service: {payload}")
        return requests.post(
            settings.ai_service.url + "/api/v1/knowledges/callback",
            json=payload,
            headers=headers,
            timeout=30
        )

    @staticmethod
    def send_whole_sites_indexing_callback(
        tenant_id: str,
        url: str,
        doc_ids: list[str],
        interval: str | None = None,
        status: str = "active",
        metadata: dict | None = None
    ):
        """Send callback to AI service for whole sites indexing status"""
        headers = {
            "Content-Type": "application/json",
            "X-Is-Internal": "true"
        }

        payload = {
            "tenantId": tenant_id,
            "url": url,
            "status": status,
            "docIds": doc_ids,
            "metadata": metadata,
            "interval": interval,
        }

        logger.info(f"Sending callback to AI service: {payload}")
        return requests.post(
            settings.ai_service.url + "/api/v1/knowledges/callback/whole-sites",
            json=payload,
            headers=headers,
            timeout=30
        )


    @staticmethod
    def get_google_drive_channels() -> list[dict[str, any]]:
        """Get list of active Google Drive channels from AI service

        Returns:
            List[Dict[str, Any]]: List of channel information including:
                - id: Source ID
                - channelId: Google Drive channel ID
                - accessToken: Google Drive access token
                - refreshToken: Google Drive refresh token
                - tenantId: Tenant ID
                - fileId: Google Drive file ID
        """
        try:
            headers = {
                "X-Is-Internal": "true"
            }

            response = requests.get(
                f"{settings.ai_service.url}/api/v1/knowledges/channels/google-drive",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException:
            logger.exception("Failed to get Google Drive channels")
            return []

    @staticmethod
    def get_tickets(
        tenant_id: str,
        offset: int = 0,
        limit: int = 1000,
        message_limit: int = 100,
        include_messages: bool = True,
    ) -> list[dict[str, any]]:
        """Get list of tickets for a specific tenant from AI service"""
        try:
            headers = {
                "X-Is-Internal": "true"
            }

            params = {
                "messageLimit": message_limit
            }

            response = requests.get(
                f"{settings.ai_service.url}/api/v1/tickets/messages-with-extraction-data/{tenant_id}",
                headers=headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException:
            logger.exception(f"Failed to get tickets for tenant {tenant_id}")
            return []

    @staticmethod
    def send_extraction_status(
        extraction_session_id: str,
        status: str,
        metadata: dict | None = None,
    ) -> requests.Response:
        """Send extraction status to AI service"""
        headers = {
            "Content-Type": "application/json",
            "X-Is-Internal": "true"
        }

        payload = {
            "status": status,
            "metadata": metadata or {}
        }

        logger.info(f"Sending extraction status: {payload}")
        return requests.patch(
            f"{settings.ai_service.url}/api/v1/extraction-sessions/{extraction_session_id}/status",
            json=payload,
            headers=headers,
            timeout=30,
        )

    @staticmethod
    def create_ticket_rules(
        extraction_session_id: str,
        ticket_rules: list[dict],
    ) -> requests.Response:
        """Send ticket summaries to AI service"""
        headers = {
            "Content-Type": "application/json",
            "X-Is-Internal": "true"
        }

        payload = {
            "ticketRules": [
                {
                    "ticketID": ticket.get("ticket_id"),
                    "rules": ticket.get("rules", []),
                    "firstMessageID": ticket.get("first_message_id"),
                    "lastMessageID": ticket.get("last_message_id"),
                }
                for ticket in ticket_rules
            ]
        }

        logger.info(f"Sending ticket summaries: {payload}")
        return requests.post(
            f"{settings.ai_service.url}/api/v1/extraction-sessions/{extraction_session_id}/ticket-rules",
            json=payload,
            headers=headers,
            timeout=30,
        )

    @staticmethod
    def create_extracted_rules(
        extraction_session_id: str,
        extracted_rules: list[dict],
    ) -> requests.Response:
        """Send extracted rules to AI service"""
        headers = {
            "Content-Type": "application/json",
            "X-Is-Internal": "true"
        }

        payload = {
            "extractedRules": [
                {
                    "content": rule.get("rule"),
                    "fromTicketIDs": rule.get("source_tickets", []),
                }
                for rule in extracted_rules
            ]
        }

        logger.info(f"Sending extracted rules: {payload}")
        return requests.post(
            f"{settings.ai_service.url}/api/v1/extraction-sessions/{extraction_session_id}/extracted-rules",
            json=payload,
            headers=headers,
            timeout=30,
        )

    @staticmethod
    def get_current_rules_instructions(
        tenant_id: str
    ) -> dict:
        """Get current rules instructions for a tenant from AI service"""
        try:
            headers = {
                "X-Is-Internal": "true"
            }

            response = requests.get(
                f"{settings.ai_service.url}/api/v1/extraction-sessions/tenant/{tenant_id}/rules/current",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException:
            logger.exception(f"Failed to get current rules instructions for tenant {tenant_id}")
            return {}

    @staticmethod
    def send_draft_response_callback(
        task_id: str,
        tenant_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ):
        """Send draft response status update to AI-service via SSE

        Args:
            task_id: Unique identifier for the draft response task
            tenant_id: Tenant ID for the request
            status: Task status (processing, completed, failed)
            result: Draft response result data (optional)
            error: Error message if task failed (optional)
        """
        headers = {
            "Content-Type": "application/json",
            "X-Is-Internal": "true"
        }

        payload = {
            "taskId": task_id,
            "tenantId": tenant_id,
            "status": status,
            "result": result,
            "error": error,
        }

        try:
            response = requests.post(
                f"{settings.ai_service.url}/api/v1/jobs/draft-response/callback",
                json=payload,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Draft response callback sent for task {task_id}: {status}")
        except requests.exceptions.RequestException:
            logger.exception(f"Failed to send draft response callback for task {task_id}")
