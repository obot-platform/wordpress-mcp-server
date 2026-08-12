"""Verify WordPress tools register with FastMCP without starting a server."""

import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

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
    "upload_media",
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
        self.assertIn("file_path", tools_by_name["upload_media"].inputSchema["properties"])


class MediaUploadTest(unittest.TestCase):
    def test_upload_media_posts_multipart_file_and_metadata(self):
        response = Mock()
        response.status_code = 201
        response.json.return_value = {
            "id": 123,
            "title": {"rendered": "Hero image"},
            "alt_text": "Alt text",
            "caption": {"rendered": "Caption"},
            "description": {"rendered": "Description"},
            "source_url": "https://example.com/wp-content/uploads/hero.jpg",
            "mime_type": "image/jpeg",
        }

        session = Mock()
        session.headers = {"Content-Type": "application/json"}
        session.post.return_value = response

        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "hero.jpg"
            image_path.write_bytes(b"fake image")

            with patch.object(media.config, "create_session", return_value=session):
                result = media.upload_media(
                    str(image_path),
                    title="Hero image",
                    alt_text="Alt text",
                    caption="Caption",
                    description="Description",
                    post_id=42,
                )

        self.assertNotIn("Content-Type", session.headers)
        session.post.assert_called_once()
        _, kwargs = session.post.call_args
        self.assertEqual(kwargs["data"]["title"], "Hero image")
        self.assertEqual(kwargs["data"]["alt_text"], "Alt text")
        self.assertEqual(kwargs["data"]["caption"], "Caption")
        self.assertEqual(kwargs["data"]["description"], "Description")
        self.assertEqual(kwargs["data"]["post"], 42)
        self.assertEqual(kwargs["files"]["file"][0], "hero.jpg")
        self.assertEqual(kwargs["files"]["file"][2], "image/jpeg")
        self.assertEqual(result["id"], 123)
        self.assertEqual(result["alt_text"], "Alt text")

    def test_upload_media_rejects_missing_file(self):
        with self.assertRaisesRegex(ValueError, "Media file does not exist"):
            media.upload_media("/tmp/does-not-exist.jpg")
