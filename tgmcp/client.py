"""
Telegram Client Setup and Configuration

This module handles the setup and initialization of the Telegram client.
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Load tool configuration environment variables
# This ensures they're loaded before any tool imports

# Setup logging first
logger = logging.getLogger("telegram_mcp")
logger.disabled = True  # Disable all logging

# Telegram API credentials (prefer os.environ for MCP process environment)
TELEGRAM_API_ID_RAW = os.environ.get("TELEGRAM_API_ID", os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH_RAW = os.environ.get("TELEGRAM_API_HASH", os.getenv("TELEGRAM_API_HASH", ""))
TELEGRAM_SESSION_NAME = os.environ.get("TELEGRAM_SESSION_NAME", os.getenv("TELEGRAM_SESSION_NAME", "tgmcp_session"))
SESSION_STRING = os.environ.get("TELEGRAM_SESSION_STRING", os.getenv("TELEGRAM_SESSION_STRING"))


def _create_client():
    """Create a real Telethon client only when first used.

    This avoids import-time failures if credentials are missing and lets the MCP
    server start to expose tools. Tools will raise a clear error on first use if
    credentials are not provided.
    """

    try:
        api_id = int(TELEGRAM_API_ID_RAW)
    except Exception:
        raise RuntimeError("TELEGRAM_API_ID is missing or invalid. Set it in your MCP server env.")

    api_hash = (TELEGRAM_API_HASH_RAW or "").strip()
    if not api_hash:
        raise RuntimeError("TELEGRAM_API_HASH is missing. Set it in your MCP server env.")

    if SESSION_STRING:
        return TelegramClient(StringSession(SESSION_STRING), api_id, api_hash)
    return TelegramClient(TELEGRAM_SESSION_NAME, api_id, api_hash)


class _LazyClient:
    """Proxy that constructs Telethon client on first attribute access and ensures connection."""

    def __init__(self):
        self._real = None
        self._connected = False
        self._lock = asyncio.Lock()

    def _ensure_sync(self):
        """Synchronously create the client (but don't connect)."""
        if self._real is None:
            self._real = _create_client()
        return self._real

    async def _ensure_connected(self):
        """Ensure the client is created and connected."""
        async with self._lock:
            if self._real is None:
                self._real = _create_client()
            
            if not self._connected:
                # Connect to Telegram
                await self._real.connect()
                
                # Check if we're authorized, if not try to start
                if not await self._real.is_user_authorized():
                    # If we have a session string, we should be authorized
                    # Otherwise, this will fail - user needs to authenticate separately
                    if SESSION_STRING:
                        raise RuntimeError(
                            "Session string is invalid or expired. Please regenerate your session string."
                        )
                    else:
                        raise RuntimeError(
                            "Not authenticated. Please set TELEGRAM_SESSION_STRING environment variable "
                            "with a valid session string. You can generate one using the session generator script."
                        )
                
                self._connected = True
            
            return self._real

    def __getattr__(self, name):
        # For synchronous attributes, use _ensure_sync
        client = self._ensure_sync()
        attr = getattr(client, name)
        
        # If the attribute is a coroutine function, wrap it to ensure connection first
        if asyncio.iscoroutinefunction(attr):
            async def connected_wrapper(*args, **kwargs):
                await self._ensure_connected()
                return await attr(*args, **kwargs)
            return connected_wrapper
        
        return attr

    def __call__(self, *args, **kwargs):
        """Handle direct calls to client() for Telethon function requests."""
        async def call_wrapper():
            await self._ensure_connected()
            return await self._real(*args, **kwargs)
        return call_wrapper()

    def __await__(self):
        async def _aw():
            return await self._ensure_connected()

        return _aw().__await__()


# Exported lazy client
client = _LazyClient()

# Initialize the MCP server
mcp = FastMCP("telegram")

