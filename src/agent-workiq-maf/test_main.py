"""Offline checks for the local-to-hosted Work IQ path."""

import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import invoke as test_client
import main as workmate
from agent_framework import ChatResponse, Message
from agent_framework.exceptions import ToolExecutionException

SETTINGS = {
    "FOUNDRY_PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/lab",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME": "test-model",
    "WORK_IQ_SEARCH_ENTRA_APP_ID": "test-app",
    "WORK_IQ_SEARCH_ENTRA_TENANT_ID": "test-tenant",
}
COMPLETED = {
    "status": "completed",
    "output": [{"type": "message", "content": [{"type": "output_text", "text": "Test answer [1]"}]}],
}


class HostAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_requests_do_not_share_tokens(self):
        async def run_for_user(token):
            async def events():
                await asyncio.sleep(0)
                self.assertEqual(workmate._work_iq_token.get(), token)
                yield {"type": "test"}
                await asyncio.sleep(0)
                self.assertEqual(workmate._work_iq_token.get(), token)

            async for _ in workmate.WorkIQResponsesHost._with_work_iq_token(events(), token):
                self.assertEqual(workmate._work_iq_token.get(), token)
            self.assertIsNone(workmate._work_iq_token.get())

        await asyncio.gather(run_for_user("test-user-a"), run_for_user("test-user-b"))
        self.assertIsNone(workmate._work_iq_token.get())

    async def test_token_is_cleared_after_failure(self):
        async def events():
            self.assertEqual(workmate._work_iq_token.get(), "test-user-a")
            raise RuntimeError("Test failure")
            yield  # pragma: no cover

        with self.assertRaisesRegex(RuntimeError, "Test failure"):
            async for _ in workmate.WorkIQResponsesHost._with_work_iq_token(events(), "test-user-a"):
                pass
        self.assertIsNone(workmate._work_iq_token.get())

    async def test_token_is_cleared_when_stream_is_closed_early(self):
        async def events():
            yield {"type": "test"}
            yield {"type": "test"}

        stream = workmate.WorkIQResponsesHost._with_work_iq_token(events(), "test-user-a")
        await anext(stream)
        self.assertEqual(workmate._work_iq_token.get(), "test-user-a")
        await stream.aclose()
        self.assertIsNone(workmate._work_iq_token.get())

    async def test_missing_token_fails_before_mcp(self):
        with patch.object(workmate, "MCPStreamableHTTPTool") as mcp:
            with self.assertRaisesRegex(PermissionError, "delegated Work IQ token"):
                await workmate.ask_work_iq("Summarize my emails.")
            mcp.assert_not_called()

    async def test_host_rejects_background_and_missing_header(self):
        host = object.__new__(workmate.WorkIQResponsesHost)
        context = SimpleNamespace(client_headers={})
        with self.assertRaisesRegex(PermissionError, workmate.WORK_IQ_TOKEN_HEADER):
            await host._handle_response(SimpleNamespace(background=False), context, asyncio.Event())
        with self.assertRaisesRegex(ValueError, "foreground"):
            await host._handle_response(SimpleNamespace(background=True), context, asyncio.Event())

    async def test_native_responses_http_request_binds_and_clears_token(self):
        seen_tokens = []

        class RecordingAgent:
            context_providers = []

            async def run(self, **kwargs):
                token = workmate._work_iq_token.get()
                seen_tokens.append(token)
                if token and token in str(kwargs):
                    raise AssertionError("A delegated token reached model inputs.")
                return ChatResponse(messages=Message("assistant", ["Test answer [1]"]))

        with patch.dict(os.environ, {"OTEL_SDK_DISABLED": "true"}, clear=True):
            host = workmate.WorkIQResponsesHost(RecordingAgent())
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=host),
                base_url="http://localhost",
            ) as client:
                for token in ("test-user-a", "test-user-b"):
                    response = await client.post(
                        "/responses",
                        headers={workmate.WORK_IQ_TOKEN_HEADER: token},
                        json={"input": "Summarize my emails.", "stream": False, "store": False},
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["status"], "completed", response.text)
                    self.assertNotIn(token, response.text)
                response = await client.post(
                    "/responses",
                    json={"input": "Summarize my emails.", "stream": False, "store": False},
                )
                self.assertTrue(response.status_code >= 400 or response.json().get("status") == "failed", response.text)
            await host._cleanup_agent()
        self.assertEqual(seen_tokens, ["test-user-a", "test-user-b"])
        self.assertIsNone(workmate._work_iq_token.get())


class MCPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def call_with_mock_transport(self, *, error=False):
        authorizations = []
        calls = []

        def handle(request):
            authorizations.append(request.headers["Authorization"])
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
                result = {
                    "content": [{"type": "text", "text": "Work IQ denied access" if error else "Offline answer [1]"}],
                    "isError": error,
                }
            else:
                self.fail(f"Unexpected MCP method: {method}")
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})

        real_client = httpx.AsyncClient

        def create_client(**kwargs):
            self.assertFalse(kwargs["follow_redirects"])
            return real_client(transport=httpx.MockTransport(handle), **kwargs)

        with patch.object(workmate.httpx, "AsyncClient", side_effect=create_client):
            for token in ("test-user-a", "test-user-b"):
                reset = workmate._work_iq_token.set(token)
                try:
                    if error:
                        with self.assertRaisesRegex(ToolExecutionException, "Work IQ denied access"):
                            await workmate.ask_work_iq("Summarize my emails.")
                    else:
                        self.assertEqual(await workmate.ask_work_iq("Summarize my emails."), "Offline answer [1]")
                finally:
                    workmate._work_iq_token.reset(reset)
        self.assertEqual([call["method"] for call in calls].count("initialize"), 2)
        self.assertEqual([call["method"] for call in calls].count("tools/call"), 2)
        self.assertIn("Bearer test-user-a", authorizations)
        self.assertIn("Bearer test-user-b", authorizations)

    async def test_native_mcp_sessions_are_separate_per_user(self):
        await self.call_with_mock_transport()

    async def test_work_iq_errors_are_not_successful_results(self):
        await self.call_with_mock_transport(error=True)


class StartupTests(unittest.TestCase):
    def test_local_and_hosted_use_the_same_server(self):
        for hosted in (False, True):
            with self.subTest(hosted=hosted):
                settings = {
                    name: SETTINGS[name] for name in ("FOUNDRY_PROJECT_ENDPOINT", "AZURE_AI_MODEL_DEPLOYMENT_NAME")
                }
                if hosted:
                    settings["FOUNDRY_HOSTING_ENVIRONMENT"] = "test"
                with (
                    patch.dict(os.environ, settings, clear=True),
                    patch.object(workmate, "load_dotenv") as dotenv,
                    patch.object(workmate, "AzureDeveloperCliCredential") as local_credential,
                    patch.object(workmate, "ManagedIdentityCredential") as hosted_credential,
                    patch.object(workmate, "FoundryChatClient") as model,
                    patch.object(workmate, "Agent") as agent,
                    patch.object(workmate, "WorkIQResponsesHost") as host,
                ):
                    workmate.main()
                    selected = hosted_credential if hosted else local_credential
                    other = local_credential if hosted else hosted_credential
                    selected.assert_called_once()
                    other.assert_not_called()
                    self.assertEqual(model.call_args.kwargs["credential"], selected.return_value)
                    self.assertEqual(agent.call_args.kwargs["tools"][0].name, "ask_work_iq")
                    host.assert_called_once_with(agent.return_value)
                    host.return_value.run.assert_called_once_with(host="0.0.0.0" if hosted else "127.0.0.1")
                    self.assertEqual(dotenv.call_count, 0 if hosted else 1)


class InvokeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, SETTINGS, clear=True))
        self.app_factory = self.enterContext(patch.object(test_client, "PublicClientApplication"))
        self.app = self.app_factory.return_value
        self.auth_result = {"access_token": "test-user-token", "id_token_claims": {"oid": "test-user-oid"}}
        self.app.acquire_token_interactive.return_value = self.auth_result
        self.http_factory = self.enterContext(patch.object(test_client.httpx, "Client"))
        self.post = self.http_factory.return_value.__enter__.return_value.post
        self.post.return_value.json.return_value = COMPLETED
        self.credential = self.enterContext(patch.object(test_client, "AzureDeveloperCliCredential"))
        self.credential.return_value.__enter__.return_value.get_token.return_value.token = "test-foundry-token"

    def test_local_client_forwards_only_work_iq_token_outside_body(self):
        self.assertEqual(test_client.invoke("Summarize my emails.", remote=False), "Test answer [1]")
        self.app.acquire_token_interactive.assert_called_once_with([test_client.WORK_IQ_SCOPE])
        self.assertEqual(self.post.call_args.args[0], test_client.LOCAL_RESPONSES_URL)
        self.assertEqual(self.post.call_args.kwargs["headers"], {test_client.WORK_IQ_TOKEN_HEADER: "test-user-token"})
        self.assertNotIn("test-user-token", json.dumps(self.post.call_args.kwargs["json"]))
        self.credential.assert_not_called()

    def test_remote_client_separates_foundry_auth_from_work_iq_and_user_identity(self):
        self.assertEqual(test_client.invoke("Summarize my emails.", remote=True), "Test answer [1]")
        headers = self.post.call_args.kwargs["headers"]
        self.assertEqual(headers[test_client.WORK_IQ_TOKEN_HEADER], "test-user-token")
        self.assertEqual(headers["Authorization"], "Bearer test-foundry-token")
        self.assertEqual(headers["x-ms-user-identity"], "test-user-oid")
        self.assertEqual(
            self.post.call_args.args[0],
            f"{SETTINGS['FOUNDRY_PROJECT_ENDPOINT']}/agents/agent-workiq-maf"
            "/endpoint/protocols/openai/responses?api-version=v1",
        )
        self.assertEqual(self.post.call_args.kwargs["json"]["store"], False)
        self.assertEqual(self.post.call_args.kwargs["json"]["background"], False)

    def test_remote_requires_authenticated_user_identity(self):
        self.app.acquire_token_interactive.return_value = {"access_token": "test-user-token"}
        with self.assertRaisesRegex(RuntimeError, "user object ID"):
            test_client.invoke("Summarize my emails.", remote=True)
        self.post.assert_not_called()

    def test_device_code_sign_in_uses_the_notebook_scope(self):
        os.environ["CODESPACES"] = "true"
        flow = {"user_code": "TEST", "message": "Test device sign-in"}
        self.app.initiate_device_flow.return_value = flow
        self.app.acquire_token_by_device_flow.return_value = self.auth_result
        with patch("builtins.print"):
            self.assertEqual(test_client.sign_in(), self.auth_result)
        self.app.initiate_device_flow.assert_called_once_with(scopes=[test_client.WORK_IQ_SCOPE])
        self.app.acquire_token_by_device_flow.assert_called_once_with(flow)
        self.app.acquire_token_interactive.assert_not_called()

    def test_authentication_failures_do_not_send_requests(self):
        for result in (None, {"error_description": "Consent required"}, {"access_token": ""}):
            with self.subTest(result=result):
                self.app.acquire_token_interactive.return_value = result
                with self.assertRaisesRegex(RuntimeError, "authentication failed"):
                    test_client.invoke("Summarize my emails.", remote=False)
        self.post.assert_not_called()

    def test_remote_target_must_be_foundry_https_before_sign_in(self):
        for endpoint in ("http://example.services.ai.azure.com", "https://example.invalid/api/projects/lab"):
            with self.subTest(endpoint=endpoint):
                os.environ["FOUNDRY_PROJECT_ENDPOINT"] = endpoint
                with self.assertRaisesRegex(ValueError, "HTTPS Microsoft Foundry"):
                    test_client.invoke("Summarize my emails.", remote=True)
        self.app.acquire_token_interactive.assert_not_called()

    def test_failed_responses_are_not_printed_as_answers(self):
        self.post.return_value.json.return_value = {"status": "failed", "error": {"message": "Work IQ rejected token"}}
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            test_client.invoke("Summarize my emails.", remote=False)

    def test_remote_http_authentication_error_is_not_retried(self):
        request = httpx.Request("POST", "https://example.services.ai.azure.com")
        response = httpx.Response(403, request=request)
        self.post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Caller permission denied", request=request, response=response
        )
        with self.assertRaisesRegex(httpx.HTTPStatusError, "Caller permission denied"):
            test_client.invoke("Summarize my emails.", remote=True)
        self.assertEqual(self.post.call_count, 1)

    def test_completed_response_requires_an_answer(self):
        self.post.return_value.json.return_value = {"status": "completed", "output": []}
        with self.assertRaisesRegex(RuntimeError, "without a text answer"):
            test_client.invoke("Summarize my emails.", remote=False)


if __name__ == "__main__":
    unittest.main()
