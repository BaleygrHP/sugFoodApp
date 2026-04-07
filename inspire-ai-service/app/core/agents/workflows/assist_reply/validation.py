"""Tool result validation for AssistReply workflow.

This module provides validation functions for tool execution results to ensure
data integrity before downstream processing.
"""

from typing import Any, Dict
import json

from app.core.logger import get_logger

logger = get_logger(__name__)


class ToolValidationError(Exception):
    """Raised when tool result doesn't match expected schema.

    Attributes:
        tool_name: Name of the tool that failed validation
        expected: Expected schema or structure
        actual: Actual result received
    """

    def __init__(self, tool_name: str, expected: dict, actual: Any):
        self.tool_name = tool_name
        self.expected = expected
        self.actual = actual
        super().__init__(f"Tool '{tool_name}' result validation failed")


def validate_tool_result(tool_name: str, result: Any, schema: dict | None = None) -> bool:
    """Validate tool execution result against expected schema.

    Args:
        tool_name: Name of the tool
        result: Tool execution result
        schema: Optional expected schema (dict with required keys)

    Returns:
        True if validation passes

    Raises:
        ToolValidationError: If validation fails
    """
    # Basic validation: result should not be None
    if result is None:
        logger.error(
            f"[ToolValidation] Tool '{tool_name}' returned None"
        )
        raise ToolValidationError(
            tool_name=tool_name,
            expected={"result": "non-null value"},
            actual=None
        )

    # If no schema provided, basic check passed
    if schema is None:
        logger.debug(f"[ToolValidation] Tool '{tool_name}' basic validation passed")
        return True

    # Validate against schema
    try:
        if isinstance(schema, dict):
            required_keys = schema.get("required_keys", [])
            if required_keys and isinstance(result, dict):
                missing_keys = [key for key in required_keys if key not in result]
                if missing_keys:
                    logger.error(
                        f"[ToolValidation] Tool '{tool_name}' missing required keys: {missing_keys}"
                    )
                    raise ToolValidationError(
                        tool_name=tool_name,
                        expected=schema,
                        actual=result
                    )

            # Validate types if specified
            expected_type = schema.get("type")
            if expected_type:
                type_map = {
                    "dict": dict,
                    "list": list,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                }
                expected_py_type = type_map.get(expected_type)
                if expected_py_type and not isinstance(result, expected_py_type):
                    logger.error(
                        f"[ToolValidation] Tool '{tool_name}' expected type '{expected_type}', "
                        f"got '{type(result).__name__}'"
                    )
                    raise ToolValidationError(
                        tool_name=tool_name,
                        expected=schema,
                        actual=result
                    )

        logger.debug(f"[ToolValidation] Tool '{tool_name}' schema validation passed")
        return True

    except ToolValidationError:
        raise
    except Exception as e:
        logger.error(
            f"[ToolValidation] Tool '{tool_name}' validation error: {type(e).__name__}: {str(e)[:100]}"
        )
        raise ToolValidationError(
            tool_name=tool_name,
            expected=schema or {},
            actual=result
        )


def validate_id_list(tool_name: str, id_list: Any, allow_empty: bool = False) -> bool:
    """Validate that result contains valid ID list.

    Common validation for tools that extract IDs from knowledge base.

    Args:
        tool_name: Name of the tool
        id_list: Result to validate (should be list or comma-separated string)
        allow_empty: Whether empty list is valid

    Returns:
        True if validation passes

    Raises:
        ToolValidationError: If validation fails
    """
    if id_list is None:
        raise ToolValidationError(
            tool_name=tool_name,
            expected={"type": "list or comma-separated string"},
            actual=None
        )

    # Convert to list if string
    if isinstance(id_list, str):
        if not id_list.strip():
            if not allow_empty:
                raise ToolValidationError(
                    tool_name=tool_name,
                    expected={"type": "non-empty string"},
                    actual=id_list
                )
            return True
        # Check for comma-separated format
        ids = [id.strip() for id in id_list.split(",")]
    elif isinstance(id_list, list):
        ids = id_list
    else:
        raise ToolValidationError(
            tool_name=tool_name,
            expected={"type": "list or comma-separated string"},
            actual=type(id_list).__name__
        )

    # Validate non-empty if required
    if not allow_empty and not ids:
        raise ToolValidationError(
            tool_name=tool_name,
            expected={"type": "non-empty list"},
            actual=ids
        )

    # Validate each ID is non-empty string
    for idx, id_val in enumerate(ids):
        if not isinstance(id_val, (str, int)):
            raise ToolValidationError(
                tool_name=tool_name,
                expected={"type": "string or int for each ID"},
                actual=f"ID[{idx}]={type(id_val).__name__}"
            )
        if isinstance(id_val, str) and not id_val.strip():
            raise ToolValidationError(
                tool_name=tool_name,
                expected={"type": "non-empty string for each ID"},
                actual=f"ID[{idx}]=empty string"
            )

    logger.debug(f"[ToolValidation] Tool '{tool_name}' ID list validation passed: {len(ids)} IDs")
    return True


def validate_api_response(tool_name: str, response: Any, expected_status: int = 200) -> bool:
    """Validate API tool response.

    Args:
        tool_name: Name of the API tool
        response: Response object (should have status_code or status)
        expected_status: Expected HTTP status code

    Returns:
        True if validation passes

    Raises:
        ToolValidationError: If validation fails
    """
    if response is None:
        raise ToolValidationError(
            tool_name=tool_name,
            expected={"status": expected_status},
            actual=None
        )

    # Check for status code
    status = None
    if isinstance(response, dict):
        status = response.get("status_code") or response.get("status")
    elif hasattr(response, "status_code"):
        status = response.status_code
    elif hasattr(response, "status"):
        status = response.status

    if status is None:
        logger.warning(
            f"[ToolValidation] Tool '{tool_name}' response has no status code"
        )
        return True  # Assume success if no status

    if status != expected_status:
        raise ToolValidationError(
            tool_name=tool_name,
            expected={"status": expected_status},
            actual={"status": status}
        )

    logger.debug(f"[ToolValidation] Tool '{tool_name}' API response validation passed (status={status})")
    return True
