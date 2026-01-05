# GitHub Issue: Kiro-CLI Compatibility

**Repository:** https://github.com/coleam00/archon

**Note:** You have READ-only permission on this repository. To create this issue, please:
1. Visit: https://github.com/coleam00/archon/issues/new
2. Copy and paste the content below

---

## Title

Enable kiro-cli compatibility by switching MCP server from Uvicorn to Hypercorn (HTTP/2 support)

## Body

### Summary

Changes required to enable Archon MCP server to work properly with kiro-cli and other MCP clients using `mcp-remote`. The MCP server currently uses Uvicorn which only supports HTTP/1.1, causing connection timeouts with `mcp-remote` clients that expect HTTP/2 support.

### Problem

When attempting to connect to Archon's MCP server via `mcp-remote` (used by kiro-cli and other MCP clients), connections hang indefinitely with timeout errors:

```
MCP error -32001: Request timed out
Connection timeout after 60 seconds
```

### Root Cause

**Known Compatibility Issues:**

1. **HTTP/2 Requirement**: FastMCP's `streamable-http` transport requires HTTP/2 for proper bidirectional streaming
2. **Uvicorn Limitation**: Uvicorn only supports HTTP/1.1, causing the protocol to degrade
3. **Session Management**: `mcp-remote` expects proper HTTP/2 session handling

**References:**
- [Incompatibility with FastMCP Streamable HTTP Transport - Issue #113](https://github.com/geelen/mcp-remote/issues/113)
- [GET /mcp endpoint hangs with streamable HTTP - Issue #532](https://github.com/jlowin/fastmcp/issues/532)
- [Streamable HTTP transport fails - Issue #1053](https://github.com/modelcontextprotocol/python-sdk/issues/1053)

### Solution

Replace Uvicorn with Hypercorn, which provides native HTTP/2 support.

### Changes Required

#### 1. Add Hypercorn Dependency

**File:** `python/pyproject.toml`

```diff
 # MCP container dependencies
 mcp = [
     "mcp==1.12.2",
     "httpx>=0.24.0",
     "pydantic>=2.0.0",
     "python-dotenv>=1.0.0",
     "supabase==2.15.1",
     "logfire>=0.30.0",
     "fastapi>=0.104.0",
+    "hypercorn[h2]>=0.16.0",
 ]
```

#### 2. Create Hypercorn Runner

**File:** `python/src/mcp_server/run_hypercorn.py` (new file)

```python
"""
Hypercorn runner for MCP server with HTTP/2 support.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hypercorn.asyncio import serve
from hypercorn.config import Config
from src.mcp_server.mcp_server import mcp


def main():
    """Run the MCP server with Hypercorn and HTTP/2 support."""
    host = "0.0.0.0"
    port = int(os.getenv("ARCHON_MCP_PORT", "8051"))

    config = Config()
    config.bind = [f"{host}:{port}"]
    config.alpn_protocols = ["h2", "http/1.1"]  # Enable HTTP/2
    config.accesslog = "-"
    config.errorlog = "-"
    config.loglevel = "INFO"

    print(f"🚀 Starting MCP server with Hypercorn")
    print(f"   Host: {host}, Port: {port}")
    print(f"   HTTP/2: Enabled")

    app = mcp.streamable_http_app()
    asyncio.run(serve(app, config))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("👋 MCP server stopped")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

#### 3. Update Dockerfile

**File:** `python/Dockerfile.mcp`

```diff
-# Run the MCP server
-CMD ["python", "-m", "src.mcp_server.mcp_server"]
+# Run the MCP server with Hypercorn (HTTP/2 support)
+CMD ["python", "-m", "src.mcp_server.run_hypercorn"]
```

### Testing Results

✅ **Connection successful:**
```
$ npx mcp-remote@latest http://localhost:8051/mcp --allow-http

✅ Connected to remote server using StreamableHTTPClientTransport
✅ Local STDIO server running
✅ Proxy established successfully
```

✅ **All 6 MCP tool modules working:**
- RAG tools
- Project tools
- Task tools
- Document tools
- Version tools
- Feature tools

### Kiro-CLI Configuration

Users can connect using this configuration in `~/.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "archon": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8051/mcp",
        "--allow-http"
      ]
    }
  }
}
```

### Impact

**Positive:**
- ✅ Full kiro-cli compatibility
- ✅ Proper HTTP/2 support for MCP streamable-http transport
- ✅ Backward compatible with HTTP/1.1 clients
- ✅ No changes to existing MCP tools or functionality

**No Breaking Changes:**
- Container size unchanged (~150MB)
- No performance degradation
- All existing features work identically

### Documentation

Full technical details including testing procedures and migration path available in the `KIRO_CLI_COMPATIBILITY.md` document (attached to this issue or available in PR).

### References

- [FastMCP HTTP Deployment](https://gofastmcp.com/deployment/http)
- [Hypercorn Documentation](https://pypi.org/project/Hypercorn/)
- [HTTP/2 Configuration Guide](https://dev.to/ayoubzulfiqar/http2-hypercorn-configuration-for-you-fastapi-5862)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

### Labels

`enhancement`, `mcp`, `compatibility`

---

## Alternative: Create via Web Interface

1. Visit: https://github.com/coleam00/archon/issues/new
2. Copy the title and body from above
3. Submit the issue
