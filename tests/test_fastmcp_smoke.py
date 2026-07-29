"""Verify WordPress tools register with FastMCP without starting a server."""

import inspect
import os
import unittest

from fastmcp import Client

os.environ.setdefault("WORDPRESS_SITE", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "test-user")
os.environ.setdefault("WORDPRESS_PASSWORD", "test-password")

from src.server import mcp

# Import tool modules so their @mcp.tool decorators register each tool.
from src.tools import categories, media, posts, site, tags, users


EXPECTED_TOOL_NAMES = {
    "list_posts",
    "retrieve_post",
    "create_post",
    "update_post",
    "delete_post",
    "list_users",
    "get_me",
    "validate_credential",
    "list_media",
    "update_media",
    "delete_media",
    "list_categories",
    "create_category",
    "update_category",
    "delete_category",
    "list_tags",
    "create_tag",
    "update_tag",
    "delete_tag",
    "get_site_settings",
}


class FastMCPSmokeTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_wordpress_tools_register(self):
        self.assertFalse(inspect.iscoroutinefunction(mcp.run))

        async with Client(mcp) as client:
            tools = await client.list_tools()

        tools_by_name = {tool.name: tool for tool in tools}

        self.assertEqual(set(tools_by_name), EXPECTED_TOOL_NAMES)
        self.assertTrue(all(tool.description for tool in tools))
        self.assertEqual(
            tools_by_name["retrieve_post"].inputSchema["required"], ["post_id"]
        )
        self.assertIn("title", tools_by_name["create_post"].inputSchema["properties"])
        self.assertIn("post_id", tools_by_name["delete_post"].inputSchema["properties"])
