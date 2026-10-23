"""Offline checks for the local-to-hosted Work IQ path."""

import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import invoke as test_client
import main as workmate
import workiq_auth
from agent_framework import Agent, AgentResponse, AgentResponseUpdate, Content, ResponseStream
from agent_framework.exceptions import ToolExecutionException
from agent_framework.foundry import FoundryChatClient

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
        host._local_auth = None
        context = SimpleNamespace(client_headers={})
        with self.assertRaisesRegex(PermissionError, workmate.WORK_IQ_TOKEN_HEADER):
            async for _ in host._handle_response({"background": False}, context, asyncio.Event()):
                pass
        with self.assertRaisesRegex(ValueError, "foreground"):
            async for _ in host._handle_response({"background": True}, context, asyncio.Event()):
                pass

    async def test_native_responses_http_request_binds_and_clears_token(self):
        seen_tokens = []

        class RecordingAgent(Agent):
            def __init__(self):
                super().__init__(
                    client=MagicMock(spec=FoundryChatClient, STORES_BY_DEFAULT=True), name="RecordingAgent"
                )

            def run(self, **kwargs):
                async def updates():
                    token = workmate._work_iq_token.get()
                    seen_tokens.append(token)
                    if token and token in str(kwargs):
                        raise AssertionError("A delegated token reached model inputs.")
                    yield AgentResponseUpdate(role="assistant", contents=[Content.from_text("Test answer [1]")])

                return ResponseStream(updates(), finalizer=AgentResponse.from_updates)

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
        self.assertEqual(seen_tokens, ["test-user-a", "test-user-b"])
        self.assertIsNone(workmate._work_iq_token.get())

    async def test_local_playground_requests_need_no_token_header(self):
        seen_tokens = []

        class RecordingAgent(Agent):
            def __init__(self):
                super().__init__(
                    client=MagicMock(spec=FoundryChatClient, STORES_BY_DEFAULT=True), name="RecordingAgent"
                )

            def run(self, *, stream, **kwargs):
                def record_token():
                    token = workmate._work_iq_token.get()
                    seen_tokens.append(token)
                    if token in str(kwargs):
                        raise AssertionError("A delegated token reached model inputs.")

                async def updates():
                    record_token()
                    yield AgentResponseUpdate(role="assistant", contents=[Content.from_text("Local playground answer")])

                return ResponseStream(updates(), finalizer=AgentResponse.from_updates)

        with (
            patch.dict(os.environ, {"OTEL_SDK_DISABLED": "true"}, clear=True),
            patch.object(workiq_auth, "WorkIQAuth") as auth_factory,
        ):
            auth = auth_factory.return_value
            auth.get_access_token.side_effect = [
                "local-token-1",
                "local-token-2",
                "local-stream-token",
                PermissionError("Sign in again"),
            ]
            host = workmate.WorkIQResponsesHost(RecordingAgent(), local_auth=auth)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=host),
                base_url="http://localhost",
            ) as client:
                for _ in range(2):
                    response = await client.post(
                        "/responses",
                        json={"input": "Summarize my emails.", "stream": False, "store": True},
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["status"], "completed", response.text)
                    self.assertNotIn("local-token", response.text)
                response = await client.post(
                    "/responses",
                    json={"input": "Summarize my emails.", "stream": True, "background": False, "store": True},
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn("event: response.completed", response.text)
                self.assertIn("Local playground answer", response.text)
                self.assertNotIn("local-stream-token", response.text)
                response = await client.post(
                    "/responses",
                    headers={workmate.WORK_IQ_TOKEN_HEADER: "explicit-user-token"},
                    json={"input": "Summarize my emails.", "stream": False, "store": False},
                )
                self.assertEqual(response.json()["status"], "completed", response.text)
                response = await client.post(
                    "/responses",
                    json={"input": "Summarize my emails.", "stream": False, "store": False},
                )
                self.assertTrue(response.status_code >= 400 or response.json().get("status") == "failed", response.text)
        self.assertEqual(seen_tokens, ["local-token-1", "local-token-2", "local-stream-token", "explicit-user-token"])
        self.assertEqual(auth.get_access_token.call_count, 4)
        self.assertIsNone(workmate._work_iq_token.get())

    async def test_hosted_server_cannot_enable_shared_local_sign_in(self):
        with patch.dict(os.environ, {"FOUNDRY_HOSTING_ENVIRONMENT": "test"}):
            with self.assertRaisesRegex(ValueError, "not allowed in Microsoft Foundry"):
                workmate.WorkIQResponsesHost(None, local_auth=object())


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


class HostedMCPTests(unittest.IsolatedAsyncioTestCase):
    def test_direct_mcp_factory_uses_oauth_connection_and_request_scoped_headers(self):
        with (
            patch.dict(os.environ, SETTINGS, clear=True),
            patch.object(workmate, "get_request_context") as context,
            patch.object(workmate, "HostedFoundryChatClient") as client,
            patch.object(workmate, "Agent") as agent,
            patch.object(workmate, "WorkIQAuth") as local_auth,
        ):
            client.return_value.get_mcp_tool.side_effect = FoundryChatClient.get_mcp_tool
            for call_id in ("caller-a", "caller-b"):
                context.return_value.platform_headers.return_value = {"x-agent-foundry-call-id": call_id}
                workmate.create_hosted_agent(MagicMock())
                self.assertEqual(client.call_args.kwargs["default_headers"], {"x-agent-foundry-call-id": call_id})
                mcp = agent.call_args.kwargs["tools"][0]
                self.assertEqual(mcp["type"], "mcp")
                self.assertEqual(mcp["project_connection_id"], "work-iq-mcp-connection")
                self.assertEqual(mcp["server_url"], workmate.WORK_IQ_MCP_URL)
                self.assertEqual(mcp["allowed_tools"], ["ask"])
                self.assertNotIn("headers", mcp)
            self.assertEqual(client.call_count, 2)
            local_auth.assert_not_called()

    def test_hosted_factory_rejects_missing_trusted_caller_context(self):
        with (
            patch.object(workmate, "get_request_context") as context,
            patch.object(workmate, "HostedFoundryChatClient") as client,
        ):
            context.return_value.platform_headers.return_value = {}
            with self.assertRaisesRegex(PermissionError, "trusted Microsoft Foundry caller context"):
                workmate.create_hosted_agent(MagicMock())
            client.assert_not_called()

    async def test_real_hosted_client_preserves_caller_header_and_closes_transports(self):
        with (
            patch.dict(os.environ, {**SETTINGS, "OTEL_SDK_DISABLED": "true"}, clear=True),
            patch.object(workmate, "get_request_context") as context,
        ):
            context.return_value.platform_headers.return_value = {"x-agent-foundry-call-id": "caller-a"}
            agent = workmate.create_hosted_agent(MagicMock())
            workmate.ResponsesHostServer(agent=agent)
            model = agent.client
            self.assertEqual(model.client.default_headers["x-agent-foundry-call-id"], "caller-a")
            with patch.object(model.project_client, "close", new_callable=AsyncMock) as close_project:
                async with agent:
                    self.assertFalse(model.client.is_closed())
                self.assertTrue(model.client.is_closed())
                close_project.assert_awaited_once()
            await model.project_client.close()

    async def test_native_host_emits_oauth_consent_and_answers_after_consent(self):
        consent_link = "https://logic-test.consent.azure-apihub.net/login?data=offline"
        consented = False
        created = []
        closed = []

        class ConsentAgent(Agent):
            def __init__(self):
                super().__init__(client=MagicMock(spec=FoundryChatClient, STORES_BY_DEFAULT=True), name="Workmate")
                created.append(self)

            async def __aexit__(self, *args):
                await super().__aexit__(*args)
                closed.append(self)

            def run(self, *, stream, **kwargs):
                async def updates():
                    content = (
                        Content.from_text("Work IQ mailbox answer [1]")
                        if consented
                        else Content.from_oauth_consent_request(
                            consent_link,
                            additional_properties={"server_label": "work_iq"},
                        )
                    )
                    yield AgentResponseUpdate(role="assistant", contents=[content])

                return ResponseStream(updates(), finalizer=AgentResponse.from_updates)

        with patch.dict(os.environ, {"OTEL_SDK_DISABLED": "true"}, clear=True):
            host = workmate.ResponsesHostServer(agent=ConsentAgent)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=host),
                base_url="http://localhost",
            ) as client:
                response = await client.post(
                    "/responses",
                    json={"input": "Summarize my emails.", "stream": True, "store": True},
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn('"type":"oauth_consent_request"', response.text.replace(" ", ""))
                self.assertIn(consent_link, response.text)
                self.assertIn("event: response.incomplete", response.text)
                self.assertNotIn("x-client-workiq-access-token", response.text)
                events = [
                    json.loads(line.removeprefix("data: "))
                    for line in response.text.splitlines()
                    if line.startswith("data: ")
                ]
                previous_response_id = next(
                    event["response"]["id"] for event in events if event["type"] == "response.incomplete"
                )
                consented = True
                response = await client.post(
                    "/responses",
                    json={
                        "input": "Summarize my emails.",
                        "stream": True,
                        "store": True,
                        "previous_response_id": previous_response_id,
                    },
                )
                self.assertIn("event: response.completed", response.text)
                self.assertIn("Work IQ mailbox answer [1]", response.text)
        self.assertEqual(len(created), 2)
        self.assertEqual(closed, created)


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
                    patch.object(workmate, "WorkIQAuth") as auth_factory,
                    patch.object(workmate, "ResponsesHostServer") as hosted_host,
                ):
                    workmate.main()
                    selected = hosted_credential if hosted else local_credential
                    other = local_credential if hosted else hosted_credential
                    selected.assert_called_once()
                    other.assert_not_called()
                    if hosted:
                        model.assert_not_called()
                        host.assert_not_called()
                        hosted_host.assert_called_once()
                        self.assertTrue(callable(hosted_host.call_args.kwargs["agent"]))
                        hosted_host.return_value.run.assert_called_once_with(host="0.0.0.0")
                        auth_factory.assert_not_called()
                        dotenv.assert_not_called()
                        continue
                    self.assertEqual(model.call_args.kwargs["credential"], selected.return_value)
                    self.assertEqual(agent.call_args.kwargs["tools"][0].name, "ask_work_iq")
                    local_auth = None if hosted else auth_factory.return_value
                    host.assert_called_once_with(agent.return_value, local_auth=local_auth)
                    if hosted:
                        auth_factory.assert_not_called()
                    else:
                        auth_factory.assert_called_once_with()
                        local_auth.sign_in.assert_called_once_with()
                    host.return_value.run.assert_called_once_with(host="0.0.0.0" if hosted else "127.0.0.1")
                    self.assertEqual(dotenv.call_count, 0 if hosted else 1)

    def test_failed_local_sign_in_does_not_start_server(self):
        with (
            patch.dict(os.environ, SETTINGS, clear=True),
            patch.object(workmate, "load_dotenv"),
            patch.object(workmate, "WorkIQAuth") as auth,
            patch.object(workmate, "WorkIQResponsesHost") as host,
        ):
            auth.return_value.sign_in.side_effect = RuntimeError("Work IQ authentication failed")
            with self.assertRaisesRegex(RuntimeError, "authentication failed"):
                workmate.main()
            host.assert_not_called()


class LocalTokenTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, SETTINGS, clear=True))
        self.app_factory = self.enterContext(patch.object(workiq_auth, "PublicClientApplication"))
        self.auth = workiq_auth.WorkIQAuth()
        self.app = self.app_factory.return_value

    def test_silent_token_acquisition_uses_only_signed_in_account(self):
        account = {"home_account_id": "test-user"}
        self.app.get_accounts.return_value = [account]
        for token in ("cached-token", "renewed-token"):
            self.app.acquire_token_silent_with_error.return_value = {"access_token": token}
            self.assertEqual(self.auth.get_access_token(), token)
        self.app.acquire_token_silent_with_error.assert_called_with([workiq_auth.WORK_IQ_SCOPE], account=account)
        self.app.acquire_token_interactive.assert_not_called()

    def test_missing_or_ambiguous_account_is_rejected(self):
        for accounts in ([], [{"home_account_id": "a"}, {"home_account_id": "b"}]):
            self.app.get_accounts.return_value = accounts
            with self.assertRaisesRegex(PermissionError, "one lab user"):
                self.auth.get_access_token()
        self.app.acquire_token_silent_with_error.assert_not_called()

    def test_expired_or_revoked_auth_requires_restart_without_another_browser(self):
        self.app.get_accounts.return_value = [{"home_account_id": "test-user"}]
        for result in (None, {"error": "interaction_required"}, {"access_token": ""}):
            self.app.acquire_token_silent_with_error.return_value = result
            with self.assertRaisesRegex(PermissionError, "Restart the local agent"):
                self.auth.get_access_token()
        self.app.acquire_token_interactive.assert_not_called()

    def test_missing_app_settings_fail_before_authentication(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "WORK_IQ_SEARCH_ENTRA_APP_ID"):
                workiq_auth.WorkIQAuth()
        self.assertEqual(self.app_factory.call_count, 1)


class InvokeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, SETTINGS, clear=True))
        self.app_factory = self.enterContext(patch.object(workiq_auth, "PublicClientApplication"))
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
        self.app.acquire_token_interactive.assert_called_once_with([workiq_auth.WORK_IQ_SCOPE])
        self.assertEqual(self.post.call_args.args[0], test_client.LOCAL_RESPONSES_URL)
        self.assertEqual(self.post.call_args.kwargs["headers"], {test_client.WORK_IQ_TOKEN_HEADER: "test-user-token"})
        self.assertNotIn("test-user-token", json.dumps(self.post.call_args.kwargs["json"]))
        self.credential.assert_not_called()

    def test_remote_client_uses_foundry_auth_without_custom_work_iq_headers(self):
        self.assertEqual(test_client.invoke("Summarize my emails.", remote=True), "Test answer [1]")
        headers = self.post.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer test-foundry-token")
        self.assertNotIn(test_client.WORK_IQ_TOKEN_HEADER, headers)
        self.assertNotIn("x-ms-user-identity", headers)
        self.app.acquire_token_interactive.assert_not_called()
        self.assertEqual(
            self.post.call_args.args[0],
            f"{SETTINGS['FOUNDRY_PROJECT_ENDPOINT']}/agents/agent-workiq-maf"
            "/endpoint/protocols/openai/responses?api-version=v1",
        )
        self.assertEqual(self.post.call_args.kwargs["json"]["store"], False)
        self.assertEqual(self.post.call_args.kwargs["json"]["background"], False)

    def test_remote_consent_is_not_printed_as_an_empty_success(self):
        self.post.return_value.json.return_value = {
            "status": "incomplete",
            "output": [{"type": "oauth_consent_request", "consent_link": "https://consent.azure-apihub.net/login"}],
        }
        with self.assertRaisesRegex(PermissionError, "Authorize the Work IQ MCP connection"):
            test_client.invoke("Summarize my emails.", remote=True)

    def test_device_code_sign_in_uses_the_notebook_scope(self):
        os.environ["CODESPACES"] = "true"
        flow = {"user_code": "TEST", "message": "Test device sign-in"}
        self.app.initiate_device_flow.return_value = flow
        self.app.acquire_token_by_device_flow.return_value = self.auth_result
        with patch("builtins.print"):
            self.assertEqual(test_client.sign_in(), self.auth_result)
        self.app.initiate_device_flow.assert_called_once_with(scopes=[workiq_auth.WORK_IQ_SCOPE])
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
