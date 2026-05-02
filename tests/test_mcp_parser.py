"""
Tests for mcp_parser.py — MCP server configuration parsing.

All network calls mocked. Fast and offline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from mcp_parser import MCPMetadata, parse_mcp_json, is_mcp_server_py, _extract_transport, _infer_install_command


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MCP_JSON_STDIO = {
    "name": "memory",
    "version": "1.0.0",
    "description": "In-memory data store",
    "transport": "stdio",
    "capabilities": {"tools": True, "resources": False, "prompts": False},
}

MCP_JSON_NPM = {
    "name": "web-search",
    "version": "2.1.0",
    "description": "Web search via Google",
    "transport": "stdio",
    "command": "npx @modelcontextprotocol/server-web-search",
    "package": {"type": "npm"},
    "permissions": ["search:query"],
}

MCP_JSON_PYTHON = {
    "name": "github-manager",
    "version": "1.5.0",
    "description": "GitHub repository management",
    "command": "uvx mcp-server-github",
    "package": {"type": "python"},
    "capabilities": {"tools": True, "resources": True, "prompts": False},
}

MCP_JSON_NESTED = {
    "server": {
        "transport": "sse",
        "command": "python -m mcp.server",
    },
    "name": "advanced-server",
}


# ---------------------------------------------------------------------------
# Tests for parse_mcp_json
# ---------------------------------------------------------------------------

class TestParseMCPJson:
    def test_parses_valid_stdio_mcp(self):
        content = json.dumps(MCP_JSON_STDIO)
        meta = parse_mcp_json(content)
        assert meta is not None
        assert meta.name == "memory"
        assert meta.version == "1.0.0"
        assert meta.transport_type == "stdio"
        assert meta.has_tools is True
        assert meta.has_resources is False

    def test_parses_npm_package(self):
        content = json.dumps(MCP_JSON_NPM)
        meta = parse_mcp_json(content)
        assert meta.name == "web-search"
        assert "search:query" in meta.declared_permissions
        assert "npx" in meta.install_command

    def test_parses_python_package(self):
        content = json.dumps(MCP_JSON_PYTHON)
        meta = parse_mcp_json(content)
        assert meta.name == "github-manager"
        assert "uvx" in meta.install_command or "python" in meta.install_command
        assert meta.has_tools is True
        assert meta.has_resources is True

    def test_parses_nested_transport(self):
        content = json.dumps(MCP_JSON_NESTED)
        meta = parse_mcp_json(content)
        assert meta.transport_type == "sse"

    def test_invalid_json_returns_none(self):
        assert parse_mcp_json("NOT VALID JSON {{{") is None

    def test_empty_content_returns_none(self):
        assert parse_mcp_json("") is None
        assert parse_mcp_json("   ") is None

    def test_non_dict_json_returns_none(self):
        assert parse_mcp_json('["array", "list"]') is None

    def test_missing_name_returns_none(self):
        data = {"version": "1.0.0", "description": "No name"}
        assert parse_mcp_json(json.dumps(data)) is None

    def test_capabilities_list_extracted(self):
        content = json.dumps(MCP_JSON_STDIO)
        meta = parse_mcp_json(content)
        assert "tools" in meta.capabilities
        assert "resources" not in meta.capabilities

    def test_post_init_capabilities_initialized(self):
        data = {"name": "test", "version": "1.0.0"}
        meta = parse_mcp_json(json.dumps(data))
        assert isinstance(meta.capabilities, list)


# ---------------------------------------------------------------------------
# Tests for _extract_transport
# ---------------------------------------------------------------------------

class TestExtractTransport:
    def test_direct_transport_field(self):
        data = {"name": "test", "transport": "stdio"}
        assert _extract_transport(data) == "stdio"

    def test_nested_transport_in_server(self):
        data = {"name": "test", "server": {"transport": "sse"}}
        assert _extract_transport(data) == "sse"

    def test_invalid_transport_ignored(self):
        data = {"transport": "invalid-type"}
        assert _extract_transport(data) is None

    def test_infer_from_npx_command(self):
        data = {"command": "npx @mcp/server"}
        assert _extract_transport(data) == "stdio"

    def test_infer_from_uvx_command(self):
        data = {"command": "uvx mcp-server"}
        assert _extract_transport(data) == "stdio"

    def test_infer_from_python_command(self):
        data = {"command": "python -m mcp"}
        assert _extract_transport(data) == "stdio"

    def test_no_transport_returns_none(self):
        data = {"name": "test", "version": "1.0.0"}
        assert _extract_transport(data) is None


# ---------------------------------------------------------------------------
# Tests for _infer_install_command
# ---------------------------------------------------------------------------

class TestInferInstallCommand:
    def test_uses_explicit_command(self):
        data = {"command": "custom-install-cmd"}
        cmd = _infer_install_command(data, "test")
        assert cmd == "custom-install-cmd"

    def test_infers_npm_from_package_type(self):
        data = {"package": {"type": "npm"}}
        cmd = _infer_install_command(data, "web-search")
        assert "npx" in cmd
        assert "web-search" in cmd

    def test_infers_python_from_package_type(self):
        data = {"package": {"type": "python"}}
        cmd = _infer_install_command(data, "github")
        assert "uvx" in cmd or "python" in cmd
        assert "github" in cmd

    def test_defaults_to_npm_pattern(self):
        data = {}
        cmd = _infer_install_command(data, "memory")
        assert "npx" in cmd
        assert "memory" in cmd

    def test_empty_name_returns_none(self):
        cmd = _infer_install_command({}, "")
        assert cmd is None

    def test_slugifies_name(self):
        cmd = _infer_install_command({}, "Web Search Tool")
        assert "web-search-tool" in cmd.lower()


# ---------------------------------------------------------------------------
# Tests for is_mcp_server_py
# ---------------------------------------------------------------------------

class TestIsMcpServerPy:
    def test_detects_mcp_import(self):
        content = "from mcp import Server\napp = Server()"
        assert is_mcp_server_py(content) is True

    def test_detects_import_mcp(self):
        content = "import mcp\nserver = mcp.Server()"
        assert is_mcp_server_py(content) is True

    def test_detects_mcp_server_reference(self):
        content = "config = mcp.Server(name='test')"
        assert is_mcp_server_py(content) is True

    def test_detects_mcp_server_class(self):
        content = "class Handler(MCPServer):\n    pass"
        assert is_mcp_server_py(content) is True

    def test_non_mcp_server_returns_false(self):
        content = "import os\nprint('hello')"
        assert is_mcp_server_py(content) is False

    def test_empty_content_returns_false(self):
        assert is_mcp_server_py("") is False

    def test_none_content_returns_false(self):
        assert is_mcp_server_py(None) is False


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestMCPIntegration:
    def test_full_parse_workflow(self):
        """End-to-end parsing of real MCP config."""
        config = {
            "name": "git-manager",
            "version": "1.0.0",
            "description": "Git repository operations",
            "transport": "stdio",
            "command": "npx @modelcontextprotocol/server-git",
            "package": {"type": "npm"},
            "permissions": ["repo:read", "repo:write"],
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": True,
            },
        }
        meta = parse_mcp_json(json.dumps(config))
        assert meta.name == "git-manager"
        assert meta.transport_type == "stdio"
        assert meta.install_command == "npx @modelcontextprotocol/server-git"
        assert "repo:read" in meta.declared_permissions
        assert "tools" in meta.capabilities
        assert "resources" not in meta.capabilities

    def test_minimal_mcp_config(self):
        """Minimal valid MCP config."""
        config = {"name": "minimal"}
        meta = parse_mcp_json(json.dumps(config))
        assert meta.name == "minimal"
        assert meta.transport_type == "unknown"
        assert meta.install_command == "npx @modelcontextprotocol/server-minimal"
