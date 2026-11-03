"""Exercise a built image when WORDPRESS_TEST_IMAGE is set (requires Docker)."""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import time
import unittest
import uuid

import requests
from fastmcp import Client

from test_fastmcp_smoke import EXPECTED_TOOL_NAMES, mcp


IMAGE = os.environ.get("WORDPRESS_TEST_IMAGE")
TEST_ENV = {
    "WORDPRESS_SITE": "http://wordpress:8080",
    "WORDPRESS_USERNAME": "test-user",
    "WORDPRESS_PASSWORD": "test password ${literal}",
}


def docker(*args, timeout=60):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout
    )
    if result.returncode:
        raise RuntimeError(f"docker {args[0]} failed: {result.stderr}")
    return (result.stdout + (result.stderr if args[0] == "logs" else "")).strip()


@unittest.skipUnless(IMAGE, "set WORDPRESS_TEST_IMAGE to test the container")
class ContainerTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = "wordpress-mcp-test-" + uuid.uuid4().hex[:12]
        docker("network", "create", cls.network)
        cls.addClassCleanup(docker, "network", "rm", cls.network)
        fixture = Path(__file__).parent / "fixtures" / "wordpress.py"
        mock = docker(
            "run", "-d", "--network", cls.network, "--network-alias", "wordpress",
            "--mount", f"type=bind,src={fixture.resolve()},dst=/fixture.py,readonly",
            "--entrypoint", "/app/.venv/bin/python", IMAGE, "/fixture.py",
        )
        cls.addClassCleanup(docker, "rm", "-fv", mock)
        cls.container, cls.url = cls.start_server()

    @classmethod
    def start_server(cls, env=None, ready=True):
        args = ["run", "-d", "--network", cls.network, "-p", "127.0.0.1::8099"]
        for key, value in (TEST_ENV if env is None else env).items():
            args.extend(["-e", f"{key}={value}"])
        container = docker(*args, IMAGE)
        cls.addClassCleanup(docker, "rm", "-fv", container)
        if not ready:
            return container, None
        port = docker("port", container, "8099/tcp").rsplit(":", 1)[1]
        url = f"http://127.0.0.1:{port}/"
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                if requests.get(url + "readyz", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            if docker("inspect", "-f", "{{.State.Running}}", container) != "true":
                raise AssertionError(docker("logs", container))
            time.sleep(0.2)
        else:
            raise AssertionError("Server did not become ready: " + docker("logs", container))
        return container, url

    def rpc(self, url, method, params=None, session=None):
        version = "2025-11-25" if session or method == "initialize" else "2026-07-28"
        headers = {
            "Accept": "application/json, text/event-stream",
            "Mcp-Protocol-Version": version,
            "Mcp-Method": method,
        }
        params = dict(params or {})
        if session:
            headers["Mcp-Session-Id"] = session
        elif version == "2026-07-28":
            params["_meta"] = {
                "io.modelcontextprotocol/protocolVersion": version,
                "io.modelcontextprotocol/clientCapabilities": {},
            }
            if "name" in params:
                headers["Mcp-Name"] = params["name"]
        response = requests.post(
            url, headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=30,
        )
        self.assertEqual(response.status_code, 200, response.text)
        if response.headers.get("Content-Type", "").startswith("text/event-stream"):
            payload = json.loads(next(
                line[6:] for line in response.text.splitlines() if line.startswith("data: ")
            ))
        else:
            payload = response.json()
        self.assertNotIn("error", payload, payload)
        return payload["result"], response.headers

    async def test_catalog_matches_fastmcp(self):
        async with Client(mcp) as direct, Client(self.url) as proxy:
            expected = {tool.name: tool for tool in await direct.list_tools()}
            actual = {tool.name: tool for tool in await proxy.list_tools()}
            self.assertEqual(set(actual), EXPECTED_TOOL_NAMES)
            for name in expected:
                with self.subTest(tool=name):
                    self.assertEqual(actual[name].description, expected[name].description)
                    self.assertEqual(actual[name].inputSchema, expected[name].inputSchema)
                    self.assertEqual(actual[name].outputSchema, expected[name].outputSchema)

    async def test_http_calls_and_errors(self):
        async with Client(self.url) as client:
            result = await client.call_tool("get_me")
            self.assertEqual(result.data["id"], 7)
            result = await client.call_tool("list_posts")
            self.assertEqual(result.data["posts"][0]["id"], 42)
            result = await client.call_tool("validate_credential")
            self.assertTrue(result.data["valid"])
            result = await client.call_tool("list_users", raise_on_error=False)
            self.assertTrue(result.is_error)
            self.assertIn("Permission denied", result.content[0].text)
            result = await client.call_tool("retrieve_post", {}, raise_on_error=False)
            self.assertTrue(result.is_error)

    def test_stateless_calls(self):
        catalog, _ = self.rpc(self.url, "tools/list")
        self.assertEqual({tool["name"] for tool in catalog["tools"]}, EXPECTED_TOOL_NAMES)
        for _ in range(2):
            result, _ = self.rpc(self.url, "tools/call", {"name": "get_me", "arguments": {}})
            self.assertFalse(result.get("isError", False), result)
            self.assertEqual(result["structuredContent"]["id"], 7)

    def test_nonroot_storage_and_probes(self):
        for path in ("healthz", "readyz"):
            self.assertEqual(requests.get(self.url + path, timeout=5).status_code, 200)
        result = docker(
            "exec", self.container, "/app/.venv/bin/python", "-c",
            "import os, pathlib, shutil; "
            "assert (os.getuid(), os.getgid()) == (1000, 1000); "
            "p = pathlib.Path('/var/lib/mmmcp/mmmcp.db'); "
            "assert p.is_file() and os.access(p, os.W_OK); "
            "assert shutil.which('uv') is None; print('ok')",
        )
        self.assertEqual(result, "ok")

    def test_missing_credentials_fail_startup(self):
        for missing in TEST_ENV:
            with self.subTest(missing=missing):
                env = {key: value for key, value in TEST_ENV.items() if key != missing}
                container, _ = self.start_server(env, ready=False)
                self.assertNotEqual(docker("wait", container, timeout=30), "0")
                self.assertIn(missing, docker("logs", container))

    async def test_invalid_credentials(self):
        _, url = await asyncio.to_thread(
            self.start_server, {**TEST_ENV, "WORDPRESS_PASSWORD": "incorrect"}
        )
        async with Client(url) as client:
            result = await client.call_tool("validate_credential")
            self.assertFalse(result.data["valid"])
            result = await client.call_tool("get_me", raise_on_error=False)
            self.assertTrue(result.is_error)
            self.assertIn("401", result.content[0].text)

    def child_pids(self, container):
        return docker(
            "exec", container, "/app/.venv/bin/python", "-c",
            "from pathlib import Path\n"
            "for path in Path('/proc').glob('[0-9]*/cmdline'):\n"
            "    try:\n"
            "        command = path.read_bytes().split(b'\\0')\n"
            "    except FileNotFoundError:\n"
            "        continue\n"
            "    if b'/app/main.py' in command:\n"
            "        print(path.parent.name)\n",
        )

    def test_idle_restart_and_sigterm(self):
        container, url = self.start_server()
        _, headers = self.rpc(url, "initialize", {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "container-test", "version": "1"},
        })
        session = headers["Mcp-Session-Id"]
        response = requests.post(url, headers={
            "Accept": "application/json, text/event-stream",
            "Mcp-Protocol-Version": "2025-11-25", "Mcp-Session-Id": session,
        }, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, timeout=5)
        self.assertEqual(response.status_code, 202, response.text)
        params = {"name": "get_me", "arguments": {}}
        result, _ = self.rpc(url, "tools/call", params, session)
        self.assertFalse(result.get("isError", False), result)
        first_pid = self.child_pids(container)
        self.assertTrue(first_pid)
        deadline = time.monotonic() + 45
        while self.child_pids(container) and time.monotonic() < deadline:
            time.sleep(0.5)
        self.assertFalse(self.child_pids(container), "Child did not retire after idle timeout")
        result, _ = self.rpc(url, "tools/call", params, session)
        self.assertFalse(result.get("isError", False), result)
        self.assertTrue(self.child_pids(container))
        self.assertNotEqual(self.child_pids(container), first_pid)
        docker("stop", "--timeout", "15", container, timeout=20)
        self.assertEqual(docker("inspect", "-f", "{{.State.ExitCode}}", container), "0")
