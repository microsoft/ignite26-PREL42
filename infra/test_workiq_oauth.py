"""Offline checks for direct Work IQ MCP OAuth provisioning."""

import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import workiq_oauth


class WorkIQConnectionTests(unittest.TestCase):
    def test_direct_mcp_connection_uses_per_user_oauth_and_not_remote_a2a(self):
        with patch.object(workiq_oauth.requests, "put") as put:
            workiq_oauth.create_connection(
                "https://management.azure.com/test",
                {},
                "work-iq-mcp-connection",
                "test-tenant",
                "test-app",
                "test-secret",
                mcp_only=True,
            )
        properties = put.call_args.kwargs["json"]["properties"]
        self.assertEqual(properties["category"], "RemoteTool")
        self.assertEqual(properties["authType"], "OAuth2")
        self.assertEqual(properties["target"], "https://workiq.svc.cloud.microsoft/mcp")
        self.assertEqual(
            properties["Scopes"],
            ["api://workiq.svc.cloud.microsoft/WorkIQAgent.Ask", "offline_access"],
        )
        put.return_value.raise_for_status.assert_called_once()

    def test_legacy_toolbox_connection_keeps_remote_a2a_configuration(self):
        with patch.object(workiq_oauth.requests, "put") as put:
            workiq_oauth.create_connection(
                "https://management.azure.com/test",
                {},
                "work-iq-connection",
                "test-tenant",
                "test-app",
                "test-secret",
            )
        properties = put.call_args.kwargs["json"]["properties"]
        self.assertEqual(properties["category"], "RemoteA2A")
        self.assertEqual(properties["target"], workiq_oauth.WORK_IQ_TARGET)
        self.assertEqual(properties["authType"], "OAuth2")

    def test_mcp_setup_rejects_an_incompatible_existing_connection(self):
        with (
            patch.dict(
                os.environ,
                {"AZURE_TENANT_ID": "test", "FOUNDRY_PROJECT_ENDPOINT": "test", "AZURE_AI_PROJECT_ID": "test"},
                clear=True,
            ),
            patch.object(workiq_oauth, "get_management_headers", return_value={}),
            patch.object(workiq_oauth, "get_connection", return_value={"properties": {"authType": "ApiKey"}}),
            patch.object(workiq_oauth, "get_async_credential") as credential,
        ):
            with self.assertRaisesRegex(RuntimeError, "must use OAuth2"):
                asyncio.run(workiq_oauth.apply(mcp_only=True))
            credential.assert_not_called()

    def test_mcp_setup_reuses_app_and_registers_callback_without_creating_toolbox(self):
        settings = {
            "AZURE_TENANT_ID": "test-tenant",
            "FOUNDRY_PROJECT_ENDPOINT": "https://test.services.ai.azure.com/api/projects/lab",
            "AZURE_AI_PROJECT_ID": "/subscriptions/test/resourceGroups/lab/providers/test/projects/lab",
            "WORK_IQ_SEARCH_ENTRA_APP_ID": "test-app",
        }
        application = SimpleNamespace(id="test-object", app_id="test-app")
        connection = {
            "properties": {
                "authType": "OAuth2",
                "category": "RemoteTool",
                "target": workiq_oauth.WORK_IQ_MCP_TARGET,
                "redirectUrl": "https://consent.azure-apihub.net/redirect",
            }
        }
        credential = MagicMock()
        credential.__aenter__ = AsyncMock(return_value=credential)
        credential.__aexit__ = AsyncMock(return_value=False)
        with (
            patch.dict(os.environ, settings, clear=True),
            patch.object(workiq_oauth, "get_management_headers", return_value={}),
            patch.object(workiq_oauth, "get_connection", return_value=connection),
            patch.object(workiq_oauth, "get_async_credential", return_value=credential),
            patch.object(workiq_oauth, "GraphServiceClient"),
            patch.object(workiq_oauth, "get_or_create_work_iq_principal", new_callable=AsyncMock),
            patch.object(workiq_oauth, "get_work_iq_scope_id"),
            patch.object(workiq_oauth, "get_or_create_application", new_callable=AsyncMock) as get_app,
            patch.object(workiq_oauth, "grant_admin_consent", new_callable=AsyncMock),
            patch.object(workiq_oauth, "add_redirect_uri", new_callable=AsyncMock) as redirect,
            patch.object(workiq_oauth, "create_toolbox") as toolbox,
            patch.object(workiq_oauth, "add_client_secret", new_callable=AsyncMock) as secret,
        ):
            get_app.return_value = application
            asyncio.run(workiq_oauth.apply(mcp_only=True))
            self.assertEqual(get_app.call_args.args[1], "test-app")
            self.assertEqual(redirect.call_args.args[2], "https://consent.azure-apihub.net/redirect")
            toolbox.assert_not_called()
            secret.assert_not_called()


if __name__ == "__main__":
    unittest.main()
