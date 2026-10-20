"""Offline checks for the direct Work IQ experiment."""

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

import main as workmate

SETTINGS = {
    "FOUNDRY_PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/lab",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME": "test-model",
    "WORK_IQ_SEARCH_ENTRA_APP_ID": "test-app",
    "WORK_IQ_SEARCH_ENTRA_TENANT_ID": "test-tenant",
}


class UserAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_refreshes_delegated_token_on_each_request(self):
        app = MagicMock()
        account = {"home_account_id": "test-user"}
        app.get_accounts.return_value = [account]
        app.acquire_token_silent.side_effect = [
            {"access_token": "test-first-token"},
            {"access_token": "test-refreshed-token"},
        ]
        authorizations = []

        def handle(request):
            authorizations.append(request.headers["Authorization"])
            return httpx.Response(200)

        async with httpx.AsyncClient(
            auth=workmate.WorkIQUserAuth(app),
            transport=httpx.MockTransport(handle),
        ) as client:
            await client.post(workmate.WORK_IQ_MCP_URL)
            await client.post(workmate.WORK_IQ_MCP_URL)

        self.assertEqual(authorizations, ["Bearer test-first-token", "Bearer test-refreshed-token"])
        self.assertEqual(app.acquire_token_silent.call_count, 2)
        app.acquire_token_silent.assert_called_with([workmate.WORK_IQ_SCOPE], account=account)

    async def test_missing_token_fails_before_sending(self):
        for result in (None, {"error": "interaction_required"}, {"access_token": ""}):
            with self.subTest(result=result):
                app = MagicMock()
                app.get_accounts.return_value = [{"home_account_id": "test-user"}]
                app.acquire_token_silent.return_value = result
                handle = MagicMock(return_value=httpx.Response(200))
                async with httpx.AsyncClient(
                    auth=workmate.WorkIQUserAuth(app),
                    transport=httpx.MockTransport(handle),
                ) as client:
                    with self.assertRaisesRegex(RuntimeError, "Restart and sign in again"):
                        await client.post(workmate.WORK_IQ_MCP_URL)
                handle.assert_not_called()

    def test_requires_exactly_one_account(self):
        for accounts in ([], [{}, {}]):
            with self.subTest(accounts=accounts):
                app = MagicMock()
                app.get_accounts.return_value = accounts
                with self.assertRaisesRegex(RuntimeError, "Expected one signed-in"):
                    workmate.WorkIQUserAuth(app)


class DirectAgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, SETTINGS, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.app_factory = self.enterContext(patch.object(workmate, "PublicClientApplication"))
        self.app = self.app_factory.return_value
        self.app.get_accounts.return_value = [{"home_account_id": "test-user"}]
        self.app.acquire_token_interactive.return_value = {"access_token": "test-user-token"}
        self.credential = self.enterContext(patch.object(workmate, "AzureDeveloperCliCredential"))
        self.mcp = self.enterContext(patch.object(workmate, "MCPStreamableHTTPTool"))
        self.client = self.enterContext(patch.object(workmate, "FoundryChatClient"))
        self.agent = self.enterContext(patch.object(workmate, "Agent"))
        self.agent.return_value.run = AsyncMock(return_value=SimpleNamespace(text="Test answer [1]"))
        self.output = self.enterContext(redirect_stdout(io.StringIO()))

    async def test_browser_sign_in_and_direct_mcp_wiring(self):
        await workmate.main("Summarize my recent emails.")

        self.app_factory.assert_called_once_with(
            client_id="test-app",
            authority="https://login.microsoftonline.com/test-tenant",
        )
        self.app.acquire_token_interactive.assert_called_once_with([workmate.WORK_IQ_SCOPE])
        self.app.acquire_token_by_device_flow.assert_not_called()
        self.credential.assert_called_once_with(tenant_id="test-tenant", process_timeout=60)
        self.assertEqual(self.mcp.call_args.kwargs["url"], workmate.WORK_IQ_MCP_URL)
        self.assertEqual(self.mcp.call_args.kwargs["allowed_tools"], ["ask"])
        self.assertEqual(self.mcp.call_args.kwargs["request_timeout"], 180)
        self.assertFalse(self.mcp.call_args.kwargs["load_prompts"])
        http_client = self.mcp.call_args.kwargs["http_client"]
        self.assertIsInstance(http_client.auth, workmate.WorkIQUserAuth)
        self.assertTrue(http_client.is_closed)
        self.assertEqual(self.agent.call_args.kwargs["tools"], [self.mcp.return_value.__aenter__.return_value])
        self.assertEqual(self.agent.call_args.kwargs["default_options"], {"store": False})
        self.agent.return_value.run.assert_awaited_once_with("Summarize my recent emails.")
        self.assertEqual(self.output.getvalue().strip(), "Test answer [1]")

    async def test_codespaces_device_sign_in(self):
        os.environ["CODESPACES"] = "true"
        flow = {"user_code": "TEST-CODE", "message": "Use TEST-CODE to sign in."}
        self.app.initiate_device_flow.return_value = flow
        self.app.acquire_token_by_device_flow.return_value = {"access_token": "test-user-token"}

        await workmate.main("Summarize my recent emails.")

        self.app.initiate_device_flow.assert_called_once_with(scopes=[workmate.WORK_IQ_SCOPE])
        self.app.acquire_token_by_device_flow.assert_called_once_with(flow)
        self.app.acquire_token_interactive.assert_not_called()
        self.assertIn(flow["message"], self.output.getvalue())

    async def test_device_flow_failure_is_explicit(self):
        os.environ["CODESPACES"] = "true"
        self.app.initiate_device_flow.return_value = {"error_description": "Device sign-in disabled"}
        with self.assertRaisesRegex(RuntimeError, "Device sign-in disabled"):
            await workmate.main("Summarize my emails.")
        self.mcp.assert_not_called()

    async def test_browser_sign_in_failure_is_explicit(self):
        for result in (None, {"error_description": "Consent required"}, {"access_token": ""}):
            with self.subTest(result=result):
                self.app.acquire_token_interactive.return_value = result
                with self.assertRaisesRegex(RuntimeError, "Work IQ authentication failed"):
                    await workmate.main("Summarize my emails.")
        self.mcp.assert_not_called()
        self.agent.assert_not_called()

    async def test_missing_configuration_fails_before_sign_in(self):
        del os.environ["WORK_IQ_SEARCH_ENTRA_APP_ID"]
        with self.assertRaisesRegex(RuntimeError, "WORK_IQ_SEARCH_ENTRA_APP_ID"):
            await workmate.main("Summarize my emails.")
        self.app_factory.assert_not_called()

    async def test_refuses_hosted_execution_before_sign_in(self):
        os.environ["FOUNDRY_HOSTING_ENVIRONMENT"] = "test"
        with self.assertRaisesRegex(RuntimeError, "local-only"):
            await workmate.main("Summarize my emails.")
        self.app_factory.assert_not_called()
        self.mcp.assert_not_called()

    async def test_connection_failures_are_not_hidden(self):
        self.mcp.return_value.__aenter__.side_effect = RuntimeError("Work IQ connection failed")
        with self.assertRaisesRegex(RuntimeError, "Work IQ connection failed"):
            await workmate.main("Summarize my emails.")
        self.agent.assert_not_called()


class MCPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_mcp_handshake_discovery_and_ask_with_delegated_auth(self):
        app = MagicMock()
        app.get_accounts.return_value = [{"home_account_id": "test-user"}]
        app.acquire_token_silent.return_value = {"access_token": "test-user-token"}
        calls = []

        def handle(request):
            self.assertEqual(request.headers["Authorization"], "Bearer test-user-token")
            payload = json.loads(request.content)
            calls.append(payload)
            method = payload["method"]
            if method == "notifications/initialized":
                return httpx.Response(202)
            if method == "initialize":
                result = {
                    "protocolVersion": payload["params"]["protocolVersion"],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "offline-work-iq", "version": "1.0"},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": name,
                            "description": name,
                            "inputSchema": {
                                "type": "object",
                                "properties": {"question": {"type": "string"}},
                                "required": ["question"],
                            },
                        }
                        for name in ("ask", "delete_entity")
                    ]
                }
            elif method == "tools/call":
                self.assertEqual(payload["params"]["name"], "ask")
                self.assertEqual(payload["params"]["arguments"], {"question": "Summarize my emails."})
                result = {"content": [{"type": "text", "text": "Offline answer [1]"}], "isError": False}
            else:
                self.fail(f"Unexpected MCP method: {method}")
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})

        async with httpx.AsyncClient(
            auth=workmate.WorkIQUserAuth(app),
            transport=httpx.MockTransport(handle),
        ) as http_client:
            async with workmate.MCPStreamableHTTPTool(
                name="work_iq",
                url=workmate.WORK_IQ_MCP_URL,
                http_client=http_client,
                request_timeout=180,
                allowed_tools=["ask"],
                load_prompts=False,
            ) as work_iq:
                self.assertEqual([function.name for function in work_iq.functions], ["ask"])
                result = await work_iq.call_tool("ask", question="Summarize my emails.")
                text = result if isinstance(result, str) else "\n".join(content.text or "" for content in result)
                self.assertIn("Offline answer [1]", text)

        self.assertIn("tools/call", [call["method"] for call in calls])
        self.assertGreaterEqual(app.acquire_token_silent.call_count, 4)


if __name__ == "__main__":
    unittest.main()
