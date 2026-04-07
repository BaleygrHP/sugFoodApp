from typing import Any, Dict, Optional
from llama_index.core.prompts import RichPromptTemplate


def safe_format_template(
    template: RichPromptTemplate,
    context: Dict[str, Any]
) -> str:
    """
    Safely format a prompt template with context variables.

    Args:
        template: The RichPromptTemplate to format
        context: Dictionary of context variables for formatting

    Returns:
        Formatted prompt string

    Raises:
        ValueError: If template formatting fails
    """
    try:
        # Convert RichPromptTemplate to string and format
        template_str = str(template)

        # Basic Jinja2-style variable substitution
        formatted = template_str

        # Handle simple variable substitution {{ variable }}
        for key, value in context.items():
            placeholder = f"{{{{ {key} }}}}"
            if placeholder in formatted:
                formatted = formatted.replace(placeholder, str(value))

        # Handle conditional blocks {% if condition %}...{% endif %}
        formatted = _process_conditionals(formatted, context)

        # Handle loops {% for item in collection %}...{% endfor %}
        formatted = _process_loops(formatted, context)

        return formatted

    except Exception as e:
        raise ValueError(f"Failed to format template: {str(e)}")


def _process_conditionals(template: str, context: Dict[str, Any]) -> str:
    """Process conditional blocks in the template."""
    # Simple conditional processing for common patterns
    # This is a basic implementation - for complex Jinja2, consider using jinja2 library

    # Handle {% if not query_engine_available %}...{% endif %}
    if "{% if not query_engine_available %}" in template:
        query_engine_available = context.get("query_engine_available", False)
        if query_engine_available:
            # Remove the conditional block content
            start = template.find("{% if not query_engine_available %}")
            end = template.find("{% endif %}", start)
            if end != -1:
                template = template[:start] + template[end + 9:]
        else:
            # Keep the conditional block content, remove the markers
            template = template.replace("{% if not query_engine_available %}", "")
            template = template.replace("{% endif %}", "")

    # Handle {% if response_template %}...{% endif %}
    if "{% if response_template %}" in template:
        response_template = context.get("response_template", "")
        if response_template:
            # Keep the conditional block content, remove the markers
            template = template.replace("{% if response_template %}", "")
            template = template.replace("{% endif %}", "")
        else:
            # Remove the conditional block content
            start = template.find("{% if response_template %}")
            end = template.find("{% endif %}", start)
            if end != -1:
                template = template[:start] + template[end + 9:]

    return template


def _process_loops(template: str, context: Dict[str, Any]) -> str:
    """Process loop blocks in the template."""
    # Handle {% for rule in rules %}...{% endfor %}
    if "{% for rule in rules %}" in template:
        rules = context.get("rules", [])
        start = template.find("{% for rule in rules %}")
        end = template.find("{% endfor %}", start)

        if start != -1 and end != -1:
            loop_content = template[start + 24:end].strip()
            loop_result = ""

            for rule in rules:
                loop_result += loop_content.replace("{{ rule }}", str(rule)) + "\n"

            template = template[:start] + loop_result + template[end + 9:]

    # Handle {% for instruction in instructions %}...{% endfor %}
    if "{% for instruction in instructions %}" in template:
        instructions = context.get("instructions", [])
        start = template.find("{% for instruction in instructions %}")
        end = template.find("{% endfor %}", start)

        if start != -1 and end != -1:
            loop_content = template[start + 33:end].strip()
            loop_result = ""

            for instruction in instructions:
                loop_result += loop_content.replace("{{ instruction }}", str(instruction)) + "\n"

            template = template[:start] + loop_result + template[end + 9:]

    # Handle {% for key, value in additional_context.items() %}...{% endfor %}
    if "{% for key, value in additional_context.items() %}" in template:
        additional_context = context.get("additional_context", {})
        start = template.find("{% for key, value in additional_context.items() %}")
        end = template.find("{% endfor %}", start)

        if start != -1 and end != -1:
            loop_content = template[start + 47:end].strip()
            loop_result = ""

            for key, value in additional_context.items():
                loop_result += loop_content.replace("{{ key }}", str(key)).replace("{{ value }}", str(value)) + "\n"

            template = template[:start] + loop_result + template[end + 9:]

    return template


def format_prompt_with_fallback(
    template: RichPromptTemplate,
    context: Dict[str, Any],
    fallback_template: Optional[str] = None
) -> str:
    """
    Format a prompt template with fallback handling.

    Args:
        template: The RichPromptTemplate to format
        context: Dictionary of context variables for formatting
        fallback_template: Optional fallback template if formatting fails

    Returns:
        Formatted prompt string or fallback
    """
    try:
        return safe_format_template(template, context)
    except Exception as e:
        if fallback_template:
            return fallback_template
        else:
            # Return a basic formatted version
            return f"Error formatting prompt: {str(e)}. Context: {context}"
