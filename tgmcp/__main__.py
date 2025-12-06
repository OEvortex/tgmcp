"""
Main entry point for the Telegram MCP package.

This module provides the main entry point for running the Telegram MCP package.
"""

import sys
import asyncio
from .client import mcp

# Import tool modules to register tools with the MCP server
# The @mcp.tool() decorators in these modules will register the tools
from .tool_config import get_enabled_tool_modules

# Import enabled tool modules based on configuration
enabled_modules = get_enabled_tool_modules()
if 'chat' in enabled_modules:
    from .tools import chat
if 'contacts' in enabled_modules:
    from .tools import contacts
if 'messages' in enabled_modules:
    from .tools import messages
if 'groups' in enabled_modules:
    from .tools import groups
if 'media' in enabled_modules:
    from .tools import media
if 'profile' in enabled_modules:
    from .tools import profile
if 'admin' in enabled_modules:
    from .tools import admin

def main():
    """Main entry point for the Telegram MCP package."""
    
    async def async_main() -> int:
        try:
            # Use the asynchronous entrypoint
            await mcp.run_stdio_async()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        
    exit_code = asyncio.run(async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
