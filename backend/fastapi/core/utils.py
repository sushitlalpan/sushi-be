"""
Utility functions for data normalization and formatting.

This module provides reusable utility functions for normalizing usernames,
branch names, and other text fields across the application.
"""

import unicodedata
from datetime import datetime, timezone


def audit_user_label(actor) -> str:
    """
    Build a role-qualified audit label for an authenticated Admin or User.

    Examples: "superadmin:carol", "admin:alice", "user:bob"
    """
    from backend.fastapi.models.admin import Admin

    if isinstance(actor, Admin):
        role = "superadmin" if actor.is_super_admin else "admin"
    else:
        role = "user"
    return f"{role}:{actor.username}"


def stamp_created(record, actor) -> None:
    """Set create/last-updated audit fields on a new record."""
    label = audit_user_label(actor)
    now = datetime.now(timezone.utc)
    record.create_user = label
    record.last_updated_user = label
    record.last_updated_at = now


def stamp_updated(record, actor) -> None:
    """Set last-updated audit fields on a modified record."""
    record.last_updated_user = audit_user_label(actor)
    record.last_updated_at = datetime.now(timezone.utc)


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
