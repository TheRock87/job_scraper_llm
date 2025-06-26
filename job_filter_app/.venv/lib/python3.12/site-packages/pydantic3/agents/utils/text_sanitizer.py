"""Utility functions for text sanitization to protect against HTML/JavaScript injection."""

from typing import Optional
import re
from bs4 import BeautifulSoup


def sanitize_text(text: Optional[str]) -> str:
    """
    Sanitizes input text by removing HTML tags and potential JavaScript code,
    while preserving all natural language characters (including non-Latin scripts)
    and punctuation.

    Args:
        text: The input string to sanitize.

    Returns:
        The sanitized plain text string.
    """
    if not text:
        return ""

    # Use BeautifulSoup to parse and extract text
    soup = BeautifulSoup(text, 'html.parser')

    # Get text content, which removes all HTML tags
    clean_text = soup.get_text()

    # Remove any remaining script-like patterns
    clean_text = re.sub(r'javascript:', '', clean_text, flags=re.IGNORECASE)

    # Remove only control characters but preserve all printable characters
    # This keeps Cyrillic, CJK characters, and other non-Latin scripts intact
    clean_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_text)

    return clean_text.strip()
