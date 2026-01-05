"""
Hypercorn runner for MCP server with HTTP/2 support.
This script wraps the FastMCP ASGI app with Hypercorn to enable HTTP/2.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hypercorn.asyncio import serve
from hypercorn.config import Config

# Import the configured MCP server
from src.mcp_server.mcp_server import mcp


def main():
    """Run the MCP server with Hypercorn and HTTP/2 support."""
    # Get configuration from environment
    host = "0.0.0.0"
    port = int(os.getenv("ARCHON_MCP_PORT", "8051"))

    # Create Hypercorn config
    config = Config()
    config.bind = [f"{host}:{port}"]

    # Enable HTTP/2
    config.alpn_protocols = ["h2", "http/1.1"]

    # Set worker and connection settings
    config.workers = 1
    config.worker_class = "asyncio"

    # Logging
    config.accesslog = "-"
    config.errorlog = "-"
    config.loglevel = "INFO"

    print(f"🚀 Starting MCP server with Hypercorn")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   HTTP/2: Enabled")
    print(f"   URL: http://{host}:{port}/mcp")

    # Get the ASGI app from FastMCP for streamable HTTP transport
    app = mcp.streamable_http_app()

    # Run the server
    asyncio.run(serve(app, config))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("👋 MCP server stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
