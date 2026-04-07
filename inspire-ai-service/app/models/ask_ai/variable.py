from typing import Any
from pydantic import BaseModel
import re
from app.core.logger import get_logger

logger = get_logger(__name__)

# Action variants
class Variable(BaseModel):
    name: str
    description: str = ""
    default_value: str = ""


def replace_variables(data, variables: list[Variable], kwargs, validate: bool = True) -> Any:
    """
    Replace variable placeholders in data with actual values.

    Args:
        data: Data structure with @variable placeholders
        variables: List of variable definitions
        kwargs: Actual values provided by LLM/caller
        validate: If True, raise error on unreplaced required variables

    Returns:
        Data with variables replaced

    Raises:
        ValueError: If required variables are not replaced and validate=True
    """
    if not data:
        return data

    var_map = {var.name: var.default_value for var in variables}
    var_descriptions = {var.name: var.description.lower() for var in variables}

    # Track which variables were successfully replaced
    replaced_vars = set()
    unreplaced_vars = set()

    def _auto_convert_comma_separated(value: Any, description: str) -> Any:
        if not isinstance(value, str):
            return value

        desc_lower = description.lower()
        if 'comma-separated' not in desc_lower and 'comma separated' not in desc_lower:
            return value

        if ',' not in value:
            if 'integer' in desc_lower or 'int' in desc_lower or 'id' in desc_lower:
                try:
                    return [int(value.strip())]
                except (ValueError, TypeError):
                    return value
            return value

        parts = [p.strip() for p in value.split(',')]

        if 'integer' in desc_lower or 'int' in desc_lower or 'id' in desc_lower:
            try:
                return [int(p) for p in parts if p]
            except (ValueError, TypeError):
                return value

        return parts

    def resolve_var(name: str) -> Any:
        if name in kwargs:
            replaced_vars.add(name)
            value = kwargs[name]
            logger.info(f"[VarReplace] Resolved @{name} from kwargs: {type(value).__name__} = {value}")

            description = var_descriptions.get(name, '')
            if description:
                converted = _auto_convert_comma_separated(value, description)
                if converted != value:
                    logger.info(f"[VarReplace] Auto-converted @{name} based on description: {value} → {converted}")
                    return converted

            return value
        if name in var_map and var_map[name] != "":
            replaced_vars.add(name)
            value = var_map[name]
            logger.info(f"[VarReplace] Resolved @{name} from default: {value}")
            return value

        unreplaced_vars.add(name)
        logger.warning(f"[VarReplace] Cannot resolve @{name} - not in kwargs or defaults")
        return None

    def replace_in_string(text: str) -> Any:
        # If the entire string is a single placeholder, return raw value
        full = re.fullmatch(r"@(\w+)", text)
        if full:
            value = resolve_var(full.group(1))
            return text if value is None else value

        # Otherwise interpolate within the string
        def sub_fn(m: re.Match) -> str:
            name = m.group(1)
            value = resolve_var(name)
            return m.group(0) if value is None else str(value)

        return re.sub(r"@(\w+)", sub_fn, text)

    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, str):
            return replace_in_string(value)
        return value

    result = walk(data)

    # Validation: Check for unreplaced required variables
    if validate and unreplaced_vars:
        # Find which variables are required (no default value)
        required_vars = {v.name for v in variables if not v.default_value}
        missing_required = unreplaced_vars & required_vars

        if missing_required:
            error_msg = (
                f"Required variables not replaced: {sorted(missing_required)}. "
                f"Available in kwargs: {sorted(kwargs.keys())}. "
                f"Variables defined: {sorted([v.name for v in variables])}"
            )
            logger.error(f"[VarReplace] VALIDATION FAILED: {error_msg}")
            raise ValueError(error_msg)

        # Only optional variables missing - log warning but don't fail
        logger.warning(
            f"[VarReplace] Optional variables not replaced: {sorted(unreplaced_vars)}"
        )

    # Log summary
    if replaced_vars:
        logger.info(f"[VarReplace] Successfully replaced: {sorted(replaced_vars)}")
    if unreplaced_vars and not validate:
        logger.info(f"[VarReplace] Unreplaced (validation disabled): {sorted(unreplaced_vars)}")

    return result


class ApiVariableParseOutput(BaseModel):
    parameters: dict[str, str] = {}
    body: dict[str, Any] = {}
    variables: list[Variable] = []
