"""Utility functions and constants for the Share To Mirror skill."""

from __future__ import annotations

import re
from typing import Optional

# Constants
DEFAULT_BASE_URL = "http://localhost:8570"
DEFAULT_TIMEOUT = 6
DEFAULT_SEEK_SECONDS = 10

# Pre-compiled regex patterns for performance
URL_REGEX = re.compile(r"(https?://\S+)")
NUMBER_REGEX = re.compile(r"\b(\d+)\b")


def extract_number_from_text(text: str) -> Optional[float]:
    """Extract a number from text using regex pattern matching.
    
    Args:
        text: The input text to search for numbers.
        
    Returns:
        The first number found as a float, or None if no number is found.
        
    Examples:
        >>> extract_number_from_text("rewind 30 seconds")
        30.0
        >>> extract_number_from_text("no numbers here")
        None
    """
    match = NUMBER_REGEX.search(text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def extract_url_from_text(text: str) -> Optional[str]:
    """Extract the first URL found in text.
    
    Args:
        text: Text that may contain URLs
        
    Returns:
        First URL found, or None if no URL is present
        
    Examples:
        >>> extract_url_from_text("Play https://youtube.com/watch?v=123")
        "https://youtube.com/watch?v=123"
        >>> extract_url_from_text("No URL here")
        None
    """
    matches = URL_REGEX.findall(text)
    return matches[0] if matches else None


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL.
    
    Args:
        url: String to validate
        
    Returns:
        True if string starts with http:// or https://
        
    Examples:
        >>> is_valid_url("https://youtube.com")
        True
        >>> is_valid_url("not a url")
        False
    """
    return url.startswith(("http://", "https://"))


def normalize_base_url(url: str) -> str:
    """Normalize and validate a base URL for API requests.
    
    Args:
        url: Raw URL string from configuration
        
    Returns:
        Normalized URL with proper protocol and no trailing slash
        
    Examples:
        >>> normalize_base_url("192.168.1.100:8570")
        "http://192.168.1.100:8570"
        >>> normalize_base_url("https://mirror.local:8570/")
        "https://mirror.local:8570"
        >>> normalize_base_url("")
        "http://localhost:8570"
    """
    url = url.strip()
    if not url:
        return DEFAULT_BASE_URL
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url.rstrip("/")


def build_channel_search_query(channel_name: str) -> str:
    """Build a search query for finding latest videos from a channel.
    
    Args:
        channel_name: Name of the YouTube channel
        
    Returns:
        Optimized search query for channel content
        
    Examples:
        >>> build_channel_search_query("TED Talks")
        "TED Talks channel latest"
    """
    return f"{channel_name} channel latest"
