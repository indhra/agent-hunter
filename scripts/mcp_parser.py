"""
mcp_parser.py — Parse MCP server configurations from mcp.json files.

Responsibility:
    Extract MCP-specific metadata (transport type, permissions, install command)
    from mcp.json files. Handle missing/malformed JSON gracefully.

No LLM calls. Parse JSON only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class MCPMetadata:
    """Parsed metadata from an mcp.json file."""

    name: str = ""
    version: str = ""
    description: str = ""
    transport_type: str = "unknown"  # "stdio", "sse", "http"
    install_command: str = ""
    declared_permissions: list[str] = None
    has_resources: bool = False
    has_tools: bool = False
    has_prompts: bool = False

    def __post_init__(self) -> None:
        if self.declared_permissions is None:
            self.declared_permissions = []

    @property
    def capabilities(self) -> list[str]:
        """Return list of declared capabilities."""
        caps = []
        if self.has_resources:
            caps.append("resources")
        if self.has_tools:
            caps.append("tools")
        if self.has_prompts:
            caps.append("prompts")
        return caps


def parse_mcp_json(content: str) -> Optional[MCPMetadata]:
    """Parse mcp.json content and extract metadata.

    Args:
        content: Raw JSON content from mcp.json file.

    Returns:
        MCPMetadata object, or None if parsing fails.
    """
    if not content or not content.strip():
        return None

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    meta = MCPMetadata()

    # Top-level fields
    meta.name = data.get("name", "")
    meta.version = data.get("version", "")
    meta.description = data.get("description", "")

    # Transport detection — can be in different structures
    transport = _extract_transport(data)
    if transport:
        meta.transport_type = transport

    # Permissions (declared capabilities user must accept)
    perms = data.get("permissions", data.get("declared_permissions", []))
    if isinstance(perms, list):
        meta.declared_permissions = [str(p) for p in perms]

    # Capabilities (what the server offers)
    capabilities = data.get("capabilities", {})
    if isinstance(capabilities, dict):
        meta.has_resources = bool(capabilities.get("resources"))
        meta.has_tools = bool(capabilities.get("tools"))
        meta.has_prompts = bool(capabilities.get("prompts"))

    # Install command inference (based on package.json patterns)
    install_cmd = _infer_install_command(data, meta.name)
    if install_cmd:
        meta.install_command = install_cmd

    return meta if meta.name else None


def _extract_transport(data: dict) -> Optional[str]:
    """Infer transport type from mcp.json structure.

    Checks common patterns:
    - data['transport'] (direct)
    - data['server']['transport'] (nested)
    - Infers from command patterns (npx → stdio, uvx → stdio, etc.)
    """
    # Direct field
    transport = data.get("transport")
    if isinstance(transport, str) and transport in ("stdio", "sse", "http"):
        return transport

    # Nested under 'server'
    server = data.get("server", {})
    if isinstance(server, dict):
        transport = server.get("transport")
        if isinstance(transport, str) and transport in ("stdio", "sse", "http"):
            return transport

    # Infer from command — if using 'command' field, likely stdio-based
    command = data.get("command") or server.get("command")
    if isinstance(command, str):
        if "npx" in command or "uvx" in command or "python" in command:
            return "stdio"  # CLI-based tools are stdio

    return None


def _infer_install_command(data: dict, name: str) -> Optional[str]:
    """Infer the install/run command for the MCP server.

    Common patterns:
    - npm: `npx @modelcontextprotocol/server-<name>`
    - python: `uvx mcp-server-<name>` or `pip install mcp-server-<name>`
    """
    # Check if explicit command is provided
    command = data.get("command") or data.get("server", {}).get("command")
    if isinstance(command, str) and command.strip():
        return command

    if not name:
        return None

    # Infer based on common patterns
    name_slug = name.lower().replace(" ", "-")

    # Check package.json hint
    pkg = data.get("package", {})
    if isinstance(pkg, dict):
        pkg_type = pkg.get("type", "").lower()
        if "python" in pkg_type:
            return f"uvx mcp-server-{name_slug}"
        elif "npm" in pkg_type or "node" in pkg_type:
            return f"npx @modelcontextprotocol/server-{name_slug}"

    # Default to npm pattern (most common in MCP ecosystem)
    return f"npx @modelcontextprotocol/server-{name_slug}"


# ---------------------------------------------------------------------------
# Server.py detection
# ---------------------------------------------------------------------------


def is_mcp_server_py(content: str) -> bool:
    """Quick heuristic check if a server.py file is an MCP server.

    Looks for import patterns like:
    - `from mcp import ...`
    - `import mcp`
    - `mcp.Server`
    """
    if not content:
        return False

    # Quick pattern checks
    return (
        "from mcp import" in content
        or "import mcp" in content
        or "mcp.Server" in content
        or "MCPServer" in content
    )
