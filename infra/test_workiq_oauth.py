"""Offline checks for direct Work IQ MCP OAuth provisioning."""

import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import workiq_oauth


class WorkIQConnectionTests(unittest.TestCase):
    def test_direct_mcp_connection_uses_per_user_oauth(self):
        with patch.object(workiq_oauth.requests, "put") as put:
            workiq_oauth.create_connection(
                "https://management.azure.com/test",
                {},
                "work-iq-mcp-connection",
                "test-tenant",
                "test-app",
                "test-secret",
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

    def test_dry_run_needs_only_the_direct_connection_settings(self):
        with (
            patch.dict(os.environ, {"AZURE_TENANT_ID": "test", "AZURE_AI_PROJECT_ID": "test"}, clear=True),
            patch("builtins.print"),
            patch.object(workiq_oauth, "get_management_headers") as headers,
        ):
            workiq_oauth.dry_run()
            headers.assert_not_called()

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
                asyncio.run(workiq_oauth.apply())
            credential.assert_not_called()

    def test_mcp_setup_creates_or_reuses_connection_and_registers_callback(self):
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
                "Credentials": {"ClientId": "test-app"},
            }
        }
        credential = MagicMock()
        credential.__aenter__ = AsyncMock(return_value=credential)
        credential.__aexit__ = AsyncMock(return_value=False)
        for reuse in (False, True):
            with (
                self.subTest(reuse=reuse),
                patch.dict(os.environ, settings, clear=True),
                patch.object(workiq_oauth, "get_management_headers", return_value={}),
                patch.object(workiq_oauth, "get_connection", return_value=connection if reuse else None),
                patch.object(workiq_oauth, "get_async_credential", return_value=credential),
                patch.object(workiq_oauth, "GraphServiceClient"),
                patch.object(workiq_oauth, "get_or_create_work_iq_principal", new_callable=AsyncMock),
                patch.object(workiq_oauth, "get_work_iq_scope_id"),
                patch.object(workiq_oauth, "get_or_create_application", new_callable=AsyncMock) as get_app,
                patch.object(workiq_oauth, "grant_admin_consent", new_callable=AsyncMock),
                patch.object(workiq_oauth, "add_redirect_uri", new_callable=AsyncMock) as redirect,
                patch.object(workiq_oauth, "create_connection", return_value=connection) as create,
                patch.object(
                    workiq_oauth, "add_client_secret", new_callable=AsyncMock, return_value="test-secret"
                ) as secret,
            ):
                get_app.return_value = application
                asyncio.run(workiq_oauth.apply())
                self.assertEqual(get_app.call_args.args[1], "test-app")
                self.assertEqual(redirect.call_args.args[2], "https://consent.azure-apihub.net/redirect")
                if reuse:
                    secret.assert_not_called()
                    create.assert_not_called()
                else:
                    secret.assert_awaited_once()
                    create.assert_called_once_with(
                        workiq_oauth.connection_url(settings["AZURE_AI_PROJECT_ID"], "work-iq-mcp-connection"),
                        {},
                        "work-iq-mcp-connection",
                        "test-tenant",
                        "test-app",
                        "test-secret",
                    )


if __name__ == "__main__":
    unittest.main()
