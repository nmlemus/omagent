# omagent/tools/builtin/_path_guard.py
"""Path traversal guard for file tools."""
import os
from pathlib import Path

# Sensitive paths that should never be accessed by the LLM
_SENSITIVE_PATTERNS = (
    ".ssh",
    ".gnupg",
    ".aws/credentials",
    ".config/gcloud",
    ".env",
)


def check_path(resolved: Path) -> str | None:
    """Return an error string if the path touches a sensitive location, else None.

    Strategy: block known-sensitive paths rather than allowlist directories.
    This prevents the LLM from reading SSH keys, cloud credentials, etc.
    while still allowing normal file operations in project trees, temp dirs,
    and home directory subtrees.
    """
    path_str = str(resolved)
    for pattern in _SENSITIVE_PATTERNS:
        if f"/{pattern}" in path_str or path_str.endswith(pattern):
            return f"Access denied: {pattern} is a sensitive path"
    return None
