from typing import Any, Dict, List, Optional
from llama_index.core.prompts import RichPromptTemplate


def validate_prompt_template(
    template: RichPromptTemplate,
    required_variables: Optional[List[str]] = None,
    optional_variables: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Validate a prompt template for required variables and structure.

    Args:
        template: The RichPromptTemplate to validate
        required_variables: List of required template variables
        optional_variables: List of optional template variables

    Returns:
        Dictionary with validation results
    """
    template_str = str(template)
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "found_variables": [],
        "missing_required": [],
        "unexpected_variables": []
    }

    # Extract variables from template
    found_variables = _extract_template_variables(template_str)
    validation_result["found_variables"] = found_variables

    # Check required variables
    if required_variables:
        for var in required_variables:
            if var not in found_variables:
                validation_result["missing_required"].append(var)
                validation_result["is_valid"] = False

    # Check for unexpected variables
    if required_variables or optional_variables:
        allowed_variables = set(required_variables or []) | set(optional_variables or [])
        for var in found_variables:
            if var not in allowed_variables:
                validation_result["unexpected_variables"].append(var)
                validation_result["warnings"].append(f"Unexpected variable: {var}")

    # Check template structure
    structure_issues = _validate_template_structure(template_str)
    if structure_issues:
        validation_result["errors"].extend(structure_issues)
        validation_result["is_valid"] = False

    return validation_result


def _extract_template_variables(template_str: str) -> List[str]:
    """Extract variable names from template string."""
    variables = []

    # Find {{ variable }} patterns
    import re
    pattern = r'\{\{\s*(\w+)\s*\}\}'  # Matches {{ variable }}
    matches = re.findall(pattern, template_str)
    variables.extend(matches)

    # Find {% for item in collection %} patterns
    for_pattern = r'\{\%\s*for\s+(\w+)\s+in\s+(\w+)\s*\%\}'
    for_matches = re.findall(for_pattern, template_str)
    for match in for_matches:
        variables.extend(match)

    return list(set(variables))  # Remove duplicates


def _validate_template_structure(template_str: str) -> List[str]:
    """Validate basic template structure."""
    issues = []

    # Check for balanced {% %} blocks
    if template_str.count('{%') != template_str.count('%}'):
        issues.append("Unbalanced {% %} blocks detected")

    # Check for balanced {{ }} blocks
    if template_str.count('{{') != template_str.count('}}'):
        issues.append("Unbalanced {{ }} blocks detected")

    # Check for proper chat role structure
    if '{% chat role="system" %}' not in template_str:
        issues.append("Missing system role declaration")

    if '{% endchat %}' not in template_str:
        issues.append("Missing endchat tag")

    # Check for proper workflow structure
    if '## Workflow' not in template_str and '# Workflow' not in template_str:
        issues.append("Missing workflow section")

    return issues


def validate_prompt_context(
    template: RichPromptTemplate,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate that context contains all required variables for template.

    Args:
        template: The RichPromptTemplate to validate against
        context: The context dictionary to validate

    Returns:
        Dictionary with validation results
    """
    template_str = str(template)
    required_vars = _extract_template_variables(template_str)

    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "missing_variables": [],
        "extra_variables": []
    }

    # Check for missing variables
    for var in required_vars:
        if var not in context:
            validation_result["missing_variables"].append(var)
            validation_result["is_valid"] = False

    # Check for extra variables in context
    for var in context.keys():
        if var not in required_vars:
            validation_result["extra_variables"].append(var)
            validation_result["warnings"].append(f"Extra variable in context: {var}")

    return validation_result


def get_template_metadata(template: RichPromptTemplate) -> Dict[str, Any]:
    """
    Extract metadata from a prompt template.

    Args:
        template: The RichPromptTemplate to analyze

    Returns:
        Dictionary with template metadata
    """
    template_str = str(template)

    metadata = {
        "total_length": len(template_str),
        "variable_count": len(_extract_template_variables(template_str)),
        "has_workflow": "## Workflow" in template_str or "# Workflow" in template_str,
        "has_examples": "## Example" in template_str or "# Example" in template_str,
        "has_constraints": "## Constraints" in template_str or "# Constraints" in template_str,
        "has_rules": "## Rules" in template_str or "# Rules" in template_str,
        "estimated_tokens": len(template_str.split()) * 1.3,  # Rough estimate
    }

    return metadata
