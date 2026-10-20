"""Run a local, single-user Agent Framework assistant with direct Work IQ MCP."""

import argparse
import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureDeveloperCliCredential
from dotenv import load_dotenv
from msal import PublicClientApplication

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

logger = logging.getLogger("workmate-agent")
WORK_IQ_SCOPE = "api://workiq.svc.cloud.microsoft/WorkIQAgent.Ask"
WORK_IQ_MCP_URL = "https://workiq.svc.cloud.microsoft/mcp"


class WorkIQUserAuth(httpx.Auth):
    """Refresh the signed-in user's delegated token from MSAL's in-memory cache."""

    def __init__(self, app: PublicClientApplication) -> None:
        self.app = app
        accounts = app.get_accounts()
        if len(accounts) != 1:
            raise RuntimeError("Expected one signed-in Work IQ account. Restart and sign in again.")
        self.account = accounts[0]

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        result = await asyncio.to_thread(
            self.app.acquire_token_silent,
            [WORK_IQ_SCOPE],
            account=self.account,
        )
        if not result or not result.get("access_token"):
            raise RuntimeError("Work IQ sign-in expired or requires interaction. Restart and sign in again.")
        request.headers["Authorization"] = f"Bearer {result['access_token']}"
        yield request


async def main(question: str) -> None:
    """Sign in like the notebooks, then answer one question without Toolbox or OBO."""
    if "FOUNDRY_HOSTING_ENVIRONMENT" in os.environ:
        raise RuntimeError(
            "This direct Work IQ experiment is local-only and signs in one user interactively. "
            "It does not implement per-caller authentication for a Foundry Hosted Agent."
        )

    required = (
        "FOUNDRY_PROJECT_ENDPOINT",
        "AZURE_AI_MODEL_DEPLOYMENT_NAME",
        "WORK_IQ_SEARCH_ENTRA_APP_ID",
        "WORK_IQ_SEARCH_ENTRA_TENANT_ID",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Set these values in the repository .env: {', '.join(missing)}")

    app = PublicClientApplication(
        client_id=os.environ["WORK_IQ_SEARCH_ENTRA_APP_ID"],
        authority=(f"https://login.microsoftonline.com/{os.environ['WORK_IQ_SEARCH_ENTRA_TENANT_ID']}"),
    )
    if os.getenv("CODESPACES") == "true":
        flow = app.initiate_device_flow(scopes=[WORK_IQ_SCOPE])
        if "user_code" not in flow:
            raise RuntimeError(f"Work IQ device sign-in failed: {flow.get('error_description', 'No user code')}")
        print(flow["message"], flush=True)
        result = app.acquire_token_by_device_flow(flow)
    else:
        result = app.acquire_token_interactive([WORK_IQ_SCOPE])
    if not result or not result.get("access_token"):
        description = result.get("error_description", "No access token returned") if result else "Sign-in cancelled"
        raise RuntimeError(f"Work IQ authentication failed: {description}")

    logger.info("Signed in to Work IQ; connecting directly to %s", WORK_IQ_MCP_URL)
    with AzureDeveloperCliCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID") or os.environ["WORK_IQ_SEARCH_ENTRA_TENANT_ID"],
        process_timeout=60,
    ) as credential:
        async with httpx.AsyncClient(
            auth=WorkIQUserAuth(app),
            timeout=httpx.Timeout(30, read=180),
        ) as http_client:
            async with MCPStreamableHTTPTool(
                name="work_iq",
                url=WORK_IQ_MCP_URL,
                http_client=http_client,
                request_timeout=180,
                allowed_tools=["ask"],
                load_prompts=False,
            ) as work_iq:
                client = FoundryChatClient(
                    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                    model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
                    credential=credential,
                )
                agent = Agent(
                    client=client,
                    name="Workmate",
                    instructions="""You are Workmate, an assistant grounded in the signed-in user's
                    Microsoft 365 workplace context. Use the Work IQ ask tool for every question.
                    Respect the permissions and sensitivity boundaries returned by Work IQ.
                    Preserve source citations, mention relevant dates and participants, and
                    distinguish sourced facts from inference. Say clearly when Work IQ does not
                    provide enough information. Never claim access to content that the signed-in
                    user cannot access. This experiment is read-only; do not perform write actions.""",
                    tools=[work_iq],
                    default_options={"store": False},
                )
                response = await agent.run(question)
                print(response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ask Work IQ through a local Microsoft Agent Framework agent, without Toolbox."
    )
    parser.add_argument("question", help="A read-only question about your Microsoft 365 work context.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(args.question))
