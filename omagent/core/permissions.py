import os
from enum import Enum
from typing import Any


class Permission(str, Enum):
    AUTO = "auto"      # Execute automatically without user confirmation
    PROMPT = "prompt"  # Ask the user before executing
    DENY = "deny"      # Always refuse


DEFAULT_PERMISSION = Permission(os.getenv("OMAGENT_DEFAULT_PERMISSION", "prompt"))

# Sensible defaults for builtin tools
BUILTIN_DEFAULTS: dict[str, Permission] = {
    "read_file": Permission.AUTO,
    "list_dir": Permission.AUTO,
    "write_file": Permission.PROMPT,
    "bash": Permission.PROMPT,
}


class PermissionPolicy:
    """
    Determines whether a tool call is allowed, needs user confirmation, or is denied.

    Priority (highest to lowest):
    1. Per-tool override set at runtime (e.g. from domain pack YAML)
    2. BUILTIN_DEFAULTS
    3. DEFAULT_PERMISSION (env or prompt)
    """

    def __init__(self, overrides: dict[str, Permission] | None = None):
        self._overrides: dict[str, Permission] = overrides or {}

    def set(self, tool_name: str, permission: Permission | str) -> None:
        """Set a per-tool permission override."""
        self._overrides[tool_name] = Permission(permission)

    def load_pack_permissions(self, permissions: dict[str, str]) -> None:
        """Load permissions from a domain pack YAML permissions block."""
        for tool_name, perm_str in permissions.items():
            self.set(tool_name, perm_str)

    def check(self, tool_name: str, input: dict[str, Any] | None = None) -> Permission:
        """Return the effective permission for this tool call."""
        if tool_name in self._overrides:
            return self._overrides[tool_name]
        if tool_name in BUILTIN_DEFAULTS:
            return BUILTIN_DEFAULTS[tool_name]
        return DEFAULT_PERMISSION

    def __repr__(self) -> str:
        return f"PermissionPolicy(overrides={self._overrides})"
