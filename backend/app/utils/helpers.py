"""
Utility helper functions.
Common operations used across the application.
"""
from datetime import datetime
from typing import Optional


def format_date(date_obj: datetime, format_str: str = "%Y-%m-%d") -> str:
    """
    Format datetime object to string.
    
    Args:
        date_obj: Datetime object
        format_str: Date format string
    
    Returns:
        Formatted date string
    """
    return date_obj.strftime(format_str)


def truncate_text(text: str, max_length: int = 1500, suffix: str = "...") -> str:
    """
    Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + suffix


def calculate_word_count(text: str) -> int:
    """
    Calculate word count in text.
    
    Args:
        text: Input text
    
    Returns:
        Number of words
    """
    return len(text.split())


def clean_html_text(text: str) -> str:
    """
    Remove HTML tags and clean text.
    
    Args:
        text: Text potentially containing HTML
    
    Returns:
        Cleaned text
    """
    import re
    # Remove HTML tags
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text.strip()


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL.
    
    Args:
        url: Full URL
    
    Returns:
        Domain name or None
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None
