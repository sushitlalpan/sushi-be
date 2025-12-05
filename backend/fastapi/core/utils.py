"""
Utility functions for data normalization and formatting.

This module provides reusable utility functions for normalizing usernames,
branch names, and other text fields across the application.
"""

import unicodedata


def normalize_username(username: str) -> str:
    """
    Normalize username by:
    1. Removing accents/diacritics (é -> e, ñ -> n, ü -> u)
    2. Removing spaces
    3. Converting to lowercase
    
    Examples:
        "Mike Storage" -> "mikestorage"
        "José García" -> "josegarcia"
        "María Fernández" -> "mariafernandez"
        "Peña" -> "pena"
    
    Args:
        username: Raw username string
        
    Returns:
        Normalized username
    """
    if not username:
        return ""
    
    # Normalize unicode characters (NFD = decomposed form)
    # This separates base characters from combining diacritical marks
    normalized = unicodedata.normalize('NFD', username)
    
    # Remove all combining diacritical marks (accents, tildes, etc.)
    # Category 'Mn' = Nonspacing_Mark (combining marks that don't take up space)
    without_accents = ''.join(
        char for char in normalized 
        if unicodedata.category(char) != 'Mn'
    )
    
    # Remove spaces and convert to lowercase
    return without_accents.strip().replace(" ", "").lower()


def normalize_branch_name(branch_name: str) -> str:
    """
    Normalize branch name by stripping whitespace and converting to lowercase.
    
    Args:
        branch_name: Raw branch name
        
    Returns:
        Normalized branch name
    """
    if not branch_name:
        return ""
    return branch_name.strip().lower()
