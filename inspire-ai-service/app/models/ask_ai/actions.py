from typing import Dict, Optional, Type
from enum import Enum
from pydantic import BaseModel, create_model, Field
import httpx
import json
import time
import uuid

from llama_index.core.tools import FunctionTool

from app.models.ask_ai.variable import Variable, replace_variables
from app.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def _mask_sensitive_data(value: any, key: str = "") -> any:
    """Mask sensitive data in logs (tokens, passwords, etc.)"""
    if not isinstance(value, (str, dict, list)):
        return value

    sensitive_keys = {"authorization", "token", "password", "api_key", "secret", "bearer"}
    key_lower = key.lower()

    if isinstance(value, str):
        # Mask authorization headers
        if any(k in key_lower for k in sensitive_keys):
            if len(value) > 10:
                return f"{value[:4]}...{value[-4:]} ({len(value)} chars)"
            return "***"
        return value

    if isinstance(value, dict):
        return {k: _mask_sensitive_data(v, k) for k, v in value.items()}

    if isinstance(value, list):
        return [_mask_sensitive_data(item) for item in value]

    return value


class ActionTypeEnum(str, Enum):
    GUIDE_ANSWER = "Guide Answer"
    FETCH_API = "Fetch API"

class FetchApiTypeEnum(str, Enum):
    DEFAULT = "default"
    N8N = "n8n"
    VERTEX_AI = "vertex_ai"

class Action(BaseModel):
    """Base class for Topic Action, each Action is a FunctionTool"""
    name: str
    description: str
    condition: str

    def _action(self, **kwargs):
        pass

    def create_tool(self, tool_name: str | None = None, fn_schema: type[BaseModel] | None = None) ->  FunctionTool:
        if not tool_name:
            tool_name = self.name.lower().strip().replace(" ", "_")

        if fn_schema is None:
            fn_schema = create_model(tool_name)

        return FunctionTool.from_defaults(
            self._action,
            name=tool_name,
            description=self.description,
            fn_schema=fn_schema
        )


class GuideAnswerAction(Action):
    """Provides a brief guideline on how to respond in a specific customer conversation scenario"""
    guide: str = "Free"

    def _action(self, **kwargs):
        return (
            "Follow this guideline to generate a response:\n\n"
            f"{self.guide}\n\n"
            "Instructions for processing the guideline:\n"
            "- If the guideline is a direct answer (e.g., a list of items like 'Item 1, Item 2' or specific instructions like 'Explain politely and offer a refund'), use it as the core of your response, formatting it appropriately (e.g., as a bullet list for items).\n"
            "- If the guideline is a command (e.g., 'Give 5 random laptops'), interpret the command and generate a new response based on available knowledge or reasonable assumptions. For example, for 'Give X random [items]', select X items randomly from a relevant category and present them in a list.\n"
            "- Ensure the response is clear, concise, and formatted in Markdown for readability (e.g., use bullet points for lists, headings if needed).\n"
            "- If the guideline is unclear or cannot be processed, provide a polite response indicating the issue and suggest clarification."
        )


class FetchApiAction(Action):
    """Fetch an API endpoint"""
    endpoint: str
    method: str = "GET"
    parameters: dict = {}
    body: dict = {}
    header: dict = {}
    type: FetchApiTypeEnum = FetchApiTypeEnum.DEFAULT
    variables: list[Variable] = []
    user_id: str | None = None

    def _get_vertex_ai_token(self) -> str:
        """Get Vertex AI access token using service account"""
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            service_account_json = settings.infra.google_api.service_account_json

            if not service_account_json:
                print("Warning: service_account_json not configured in GoogleApiSettings")
                return ""

            service_account_info = json.loads(service_account_json)

            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )

            # Get access token with proper Request object
            request = Request()
            credentials.refresh(request)
            token = credentials.token
            return token

        except Exception as e:
            import traceback
            traceback.print_exc()
            return ""

    def _get_or_create_session(self, user_id: str, endpoint: str) -> str:
        """Get or create a session for Vertex AI reasoning engine"""
        try:
            import httpx
            import re

            # Extract base URL from endpoint
            # From: https://europe-west4-aiplatform.googleapis.com/v1/projects/533098803210/locations/europe-west4/reasoningEngines/4094546117465735168:streamQuery?alt=sse
            # To: https://europe-west4-aiplatform.googleapis.com/v1beta1/projects/533098803210/locations/europe-west4/reasoningEngines/4094546117465735168

            # Remove everything after the reasoning engine ID (including :streamQuery?alt=sse)
            base_url = re.sub(r':[^/]*\?.*$', '', endpoint)
            base_url = re.sub(r'/v1/', '/v1beta1/', base_url)
            sessions_url = f"{base_url}/sessions"
            # Get token for authentication
            token = self._get_vertex_ai_token()
            if not token:
                print("Warning: Could not get Vertex AI token for session management")
                return ""

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # First, try to get existing sessions for this user
            try:
                response = httpx.get(sessions_url, headers=headers, timeout=10)
                response.raise_for_status()

                sessions_data = response.json()
                sessions = sessions_data.get("sessions", [])

                # Filter sessions by userId
                user_sessions = [s for s in sessions if s.get("userId") == user_id]
                if user_sessions:
                    # Extract session ID from the 'name' field
                    # name format: "projects/.../sessions/SESSION_ID"
                    first_session = user_sessions[0]
                    session_name = first_session.get("name", "")
                    session_id = session_name.split("/sessions/")[-1] if "/sessions/" in session_name else ""
                    print('session_id created: ',session_id)
                    return session_id

            except httpx.HTTPStatusError as e:
                print(f"Error getting sessions: {e.response.status_code} - {e.response.text}")
                return ""
            except Exception as e:
                print(f"Error getting sessions: {e}")
                return ""

            # If no existing session, create a new one
            try:
                create_body = {"userId": user_id}
                response = httpx.post(sessions_url, json=create_body, headers=headers, timeout=10)
                response.raise_for_status()

                session_data = response.json()
                # Extract session ID from operation name
                # Format: projects/.../sessions/SESSION_ID/operations/OPERATION_ID
                operation_name = session_data.get("name", "")
                if "/sessions/" in operation_name and "/operations/" in operation_name:
                    # Extract the part between /sessions/ and /operations/
                    session_part = operation_name.split("/sessions/")[1]
                    session_id = session_part.split("/operations/")[0]
                    print('session_id from operation: ', session_id)
                    return session_id
                return ""

            except httpx.HTTPStatusError as e:
                print(f"Error creating session: {e.response.status_code} - {e.response.text}")
                return ""
            except Exception as e:
                print(f"Error creating session: {e}")
                return ""

        except Exception as e:
            print(f"Error in _get_or_create_session: {e}")
            return ""

    def _process_body_for_vertex_ai(self, body: dict, user_id: str, endpoint: str) -> dict:
        """Process body specifically for Vertex AI actions"""
        if not user_id:
            return body

        # Get or create session
        session_id = self._get_or_create_session(user_id, endpoint)
        if not session_id:
            print("Warning: Could not get or create session for Vertex AI")
            # Still add user_id even if session creation fails
            pass

        # Add user_id and session_id to input field if it exists
        if "input" in body and isinstance(body["input"], dict):
            body["input"]["user_id"] = user_id
            if session_id:
                body["input"]["session_id"] = session_id
        elif "input" not in body:
            # Create input field if it doesn't exist
            body["input"] = {"user_id": user_id}
            if session_id:
                body["input"]["session_id"] = session_id

        return body

    def _process_headers(self, headers: dict, kwargs: dict) -> dict:
        """Process headers based on type"""
        processed_headers = replace_variables(headers, self.variables, kwargs)
        if self.type == FetchApiTypeEnum.VERTEX_AI:
            token = self._get_vertex_ai_token()
            if token:
                processed_headers["Authorization"] = f"Bearer {token}"
            else:
                print("Warning: Could not get Vertex AI token")

        # For DEFAULT and N8N types, keep headers as is
        return processed_headers

    def _action(self, **kwargs):
        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        try:
            logger.info(f"[FetchApiAction:{correlation_id}] Received kwargs: {kwargs}")
            logger.info(f"[FetchApiAction:{correlation_id}] Body template: {self.body}")
            logger.info(f"[FetchApiAction:{correlation_id}] Variables: {[(v.name, v.default_value) for v in self.variables]}")

            processed_params = replace_variables(self.parameters, self.variables, kwargs, validate=False)
            processed_body = replace_variables(self.body, self.variables, kwargs, validate=False)
            processed_headers = self._process_headers(self.header, kwargs)

            logger.info(f"[FetchApiAction:{correlation_id}] Processed body AFTER replacement: {processed_body}")

            # Special processing for Vertex AI actions
            if self.type == FetchApiTypeEnum.VERTEX_AI and self.user_id:
                processed_body = self._process_body_for_vertex_ai(processed_body, self.user_id, self.endpoint)

            # Comprehensive request logging with masked sensitive data
            masked_headers = _mask_sensitive_data(processed_headers)
            masked_params = _mask_sensitive_data(processed_params)
            masked_body = _mask_sensitive_data(processed_body)

            logger.info(
                f"[FetchApiAction:{correlation_id}] REQUEST {self.method} {self.endpoint} | "
                f"headers={masked_headers} | params={masked_params} | body={masked_body}"
            )

            # Retry logic with exponential backoff
            max_retries = 3
            retry_delays = [1, 2, 4]  # seconds

            last_exception = None
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"[FetchApiAction:{correlation_id}] Retry attempt {attempt}/{max_retries-1}")

                    response = httpx.request(
                        method=self.method,
                        url=self.endpoint,
                        params=processed_params,
                        json=processed_body,
                        headers=processed_headers,
                        timeout=30,
                        follow_redirects=True
                    )

                    elapsed = time.time() - start_time

                    response_preview = response.text[:500] if len(response.text) <= 500 else f"{response.text[:500]}... (truncated, total {len(response.text)} chars)"
                    logger.info(
                        f"[FetchApiAction:{correlation_id}] RESPONSE {response.status_code} in {elapsed:.2f}s | "
                        f"content_length={len(response.content)} bytes"
                    )
                    logger.info(f"[FetchApiAction:{correlation_id}] Response body: {response_preview}")

                    # Handle specific status codes
                    if response.status_code == 429:  # Rate limit
                        if attempt < max_retries - 1:
                            delay = retry_delays[attempt]
                            logger.warning(f"[FetchApiAction:{correlation_id}] Rate limited (429), retrying in {delay}s")
                            time.sleep(delay)
                            continue
                        else:
                            response.raise_for_status()

                    # Don't retry 4xx errors (except 429)
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        response.raise_for_status()

                    # Retry 5xx errors
                    if response.status_code >= 500:
                        if attempt < max_retries - 1:
                            delay = retry_delays[attempt]
                            logger.warning(
                                f"[FetchApiAction:{correlation_id}] Server error ({response.status_code}), "
                                f"retrying in {delay}s"
                            )
                            time.sleep(delay)
                            continue
                        else:
                            response.raise_for_status()

                    # Success - process response
                    response.raise_for_status()

                    content_type = (response.headers.get("content-type") or "").lower()

                    # If declared as JSON, first attempt single-JSON parsing
                    if "application/json" in content_type:
                        try:
                            result = response.json()
                            logger.info(f"[FetchApiAction:{correlation_id}] Parsed JSON response successfully")
                            logger.info(f"[FetchApiAction:{correlation_id}] Returning to LLM: {result}")
                            return result
                        except ValueError:
                            # Body may contain concatenated JSON documents; try parsing sequentially
                            text = response.text
                            decoder = json.JSONDecoder()
                            index = 0
                            documents = []

                            while index < len(text):
                                # Skip whitespace between documents
                                while index < len(text) and text[index].isspace():
                                    index += 1
                                if index >= len(text):
                                    break
                                try:
                                    obj, end = decoder.raw_decode(text, index)
                                    documents.append(obj)
                                    index = end
                                except ValueError:
                                    # Not valid concatenated JSON; fall back to raw text
                                    documents = []
                                    break

                            if documents:
                                logger.info(
                                    f"[FetchApiAction:{correlation_id}] Parsed {len(documents)} concatenated JSON documents"
                                )
                                result = {
                                    "streaming": True,
                                    "chunks": documents,
                                    "final": documents[-1],
                                }
                                logger.info(f"[FetchApiAction:{correlation_id}] Returning to LLM: {result}")
                                return result

                            # Fallback: return raw text if JSON parsing fails
                            logger.warning(f"[FetchApiAction:{correlation_id}] JSON parsing failed, returning raw text")
                            result = {
                                "text": text,
                                "content_type": content_type,
                            }
                            logger.info(f"[FetchApiAction:{correlation_id}] Returning to LLM: {result}")
                            return result

                    # Not JSON content-type: return text for caller to handle
                    logger.info(f"[FetchApiAction:{correlation_id}] Non-JSON response, returning text")
                    result = {
                        "text": response.text,
                        "content_type": content_type,
                    }
                    logger.info(f"[FetchApiAction:{correlation_id}] Returning to LLM: {result}")
                    return result

                except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            f"[FetchApiAction:{correlation_id}] Network error: {type(e).__name__}, "
                            f"retrying in {delay}s"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise

            # If we exhausted retries
            if last_exception:
                raise last_exception

        except httpx.HTTPStatusError as e:
            elapsed = time.time() - start_time
            error_preview = e.response.text[:500] if hasattr(e.response, 'text') else str(e)
            logger.error(
                f"[FetchApiAction:{correlation_id}] HTTP ERROR {e.response.status_code} after {elapsed:.2f}s | "
                f"response: {error_preview}"
            )
            error_result = f"HTTP error: {e.response.status_code} - {e.response.text}"
            logger.error(f"[FetchApiAction:{correlation_id}] Returning error to LLM: {error_result}")
            return error_result
        except httpx.RequestError as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[FetchApiAction:{correlation_id}] REQUEST ERROR after {elapsed:.2f}s: {type(e).__name__} - {str(e)}"
            )
            error_result = f"Request error: {str(e)}"
            logger.error(f"[FetchApiAction:{correlation_id}] Returning error to LLM: {error_result}")
            return error_result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[FetchApiAction:{correlation_id}] UNEXPECTED ERROR after {elapsed:.2f}s: {type(e).__name__} - {str(e)}",
                exc_info=True
            )
            error_result = f"Unexpected error: {str(e)}"
            logger.error(f"[FetchApiAction:{correlation_id}] Returning error to LLM: {error_result}")
            return error_result

    def create_tool(self, fn_schema = None):
        fields = {
            var.name: (Optional[str] if var.default_value else str, Field(
                default=var.default_value,
                description=var.description
            ))
            for var in self.variables
        }

        fn_schema = create_model(self.name, **fields)

        return super().create_tool(fn_schema=fn_schema)


# Action classes dict, used for dynamic create subclass
ACTION_CLASSES: Dict[str, Type[Action]] = {
    ActionTypeEnum.GUIDE_ANSWER: GuideAnswerAction,
    ActionTypeEnum.FETCH_API: FetchApiAction,
}
