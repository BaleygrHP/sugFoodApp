def camel_to_snake(name):
    """Convert camelCase to snake_case."""
    return ''.join(['_' + c.lower() if c.isupper() else c for c in name]).lstrip('_')

def language_map(code: str):
    """Map language codes to their full names."""
    language_mapping = {
        "en": "English",
        "vi": "Vietnamese",
        "fr": "French",
        "es": "Spanish",
        "de": "German",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        # Add more mappings as needed
    }

    return language_mapping.get(code, code)
