"""Image URL extraction and processing.

This module handles image URL extraction from text and image detection in messages.
"""

import re as _re
from typing import Any


def has_images(message: Any) -> bool:
    """Check if a message contains images.

    Args:
        message: Message object to check (ChatMessage or similar)

    Returns:
        True if message has image blocks or image attachments
    """
    blocks = getattr(message, "blocks", []) or []
    if blocks:
        return True
    additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
    images = additional_kwargs.get("images", [])
    return bool(images)


def extract_image_urls(text: str) -> tuple[str, list[dict]]:
    """Extract image URLs from text and return cleaned text with attachment list.

    Supports both markdown image syntax and raw image URLs.

    Args:
        text: Input text potentially containing image URLs

    Returns:
        Tuple of (cleaned_text, attachments) where attachments is a list of dicts
        with keys: type, url, name
    """
    attachments = []
    cleaned_text = text

    # Extract markdown-style images: ![alt](url)
    markdown_pattern = r'!\[([^\]]*)\]\((https?://[^\s<>"]+?\.(?:jpg|jpeg|png|gif|webp|bmp|svg)(?:\?[^\s<>"]*)?)\)'
    markdown_matches = _re.findall(markdown_pattern, cleaned_text, _re.IGNORECASE)

    for alt_text, url in markdown_matches:
        ext_match = _re.search(r'\.(\w+)(?:\?|$)', url)
        ext = ext_match.group(1) if ext_match else 'jpg'
        safe_name = f'image_{len(attachments) + 1}.{ext}' if attachments else f'product.{ext}'
        attachments.append({'type': 'image', 'url': url, 'name': safe_name})
        full_match = f'![{alt_text}]({url})'
        cleaned_text = cleaned_text.replace(full_match, '').strip()

    # Extract raw image URLs
    raw_image_pattern = r'https?://[^\s<>"]+?\.(?:jpg|jpeg|png|gif|webp|bmp|svg)(?:\?[^\s<>"]*)?'
    raw_matches = _re.findall(raw_image_pattern, cleaned_text, _re.IGNORECASE)

    for url in raw_matches:
        # Skip if already extracted as markdown
        if any(att['url'] == url for att in attachments):
            continue
        ext_match = _re.search(r'\.(\w+)(?:\?|$)', url)
        ext = ext_match.group(1) if ext_match else 'jpg'
        safe_name = f'image_{len(attachments) + 1}.{ext}' if attachments else f'product.{ext}'
        attachments.append({'type': 'image', 'url': url, 'name': safe_name})
        cleaned_text = cleaned_text.replace(url, '').strip()

    # Clean up whitespace
    cleaned_text = _re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)
    cleaned_text = _re.sub(r'[ \t]+', ' ', cleaned_text)
    cleaned_text = cleaned_text.strip()

    return cleaned_text, attachments
