"""Workmate: direct Work IQ MCP, locally and as a Foundry Hosted Agent."""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, AsyncIterable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import httpx
from agent_framework import Agent, MCPStreamableHTTPTool, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.ai.agentserver.responses import ResponseContext
from azure.ai.agentserver.responses.models import CreateResponse, ResponseStreamEvent
from azure.identity import AzureDeveloperCliCredential, ManagedIdentityCredential
from dotenv import load_dotenv
from workiq_auth import WorkIQAuth

WORK_IQ_MCP_URL = "https://workiq.svc.cloud.microsoft/mcp"
WORK_IQ_TOKEN_HEADER = "x-client-workiq-access-token"
_work_iq_token: ContextVar[str | None] = ContextVar("work_iq_token", default=None)


async def ask_work_iq(question: str) -> str:
    """Ask Work IQ about the signed-in user's Microsoft 365 workplace context."""
    token = _work_iq_token.get()
    if not token:
        raise PermissionError("A delegated Work IQ token is required for this request.")

    # A fresh MCP session per call avoids reusing another request's credentials.
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(30, read=180),
        follow_redirects=False,
    ) as http_client:
        async with MCPStreamableHTTPTool(
            name="work_iq",
            url=WORK_IQ_MCP_URL,
            http_client=http_client,
            request_timeout=180,
            allowed_tools=["ask"],
            load_prompts=False,
        ) as work_iq:
            result = await work_iq.call_tool("ask", question=question)
            return result if isinstance(result, str) else "\n".join(content.text or "" for content in result)


class WorkIQResponsesHost(ResponsesHostServer):
    """Bind a local user's or forwarded caller's Work IQ token to its request."""

    def __init__(self, agent: Agent, *, local_auth: WorkIQAuth | None = None) -> None:
        if local_auth is not None and "FOUNDRY_HOSTING_ENVIRONMENT" in os.environ:
            raise ValueError("Shared local Work IQ sign-in is not allowed in Microsoft Foundry.")
        self._local_auth = local_auth
        super().__init__(agent)

    async def _handle_response(
        self,
        request: CreateResponse,
        context: ResponseContext,
        cancellation_signal: asyncio.Event,
    ) -> AsyncIterable[ResponseStreamEvent | dict[str, Any]]:
        if request.background:
            raise ValueError("Work IQ requires a foreground request with a current delegated token.")
        token = context.client_headers.get(WORK_IQ_TOKEN_HEADER)
        if not token and self._local_auth is not None:
            token = await asyncio.to_thread(self._local_auth.get_access_token)
        if not token:
            raise PermissionError(f"Supply a delegated Work IQ token in {WORK_IQ_TOKEN_HEADER}.")
        events = await super()._handle_response(request, context, cancellation_signal)
        return self._with_work_iq_token(events, token)

    @staticmethod
    async def _with_work_iq_token(
        events: AsyncIterable[ResponseStreamEvent | dict[str, Any]],
        token: str,
    ) -> AsyncGenerator[ResponseStreamEvent | dict[str, Any], None]:
        reset = _work_iq_token.set(token)
        try:
            async for event in events:
                yield event
        finally:
            _work_iq_token.reset(reset)


def main() -> None:
    """Run the same Responses server locally or in Microsoft Foundry."""
    hosted = "FOUNDRY_HOSTING_ENVIRONMENT" in os.environ
    if not hosted:
        load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
    missing = [name for name in ("FOUNDRY_PROJECT_ENDPOINT", "AZURE_AI_MODEL_DEPLOYMENT_NAME") if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Configure these model settings: {', '.join(missing)}")

    local_auth = None
    if not hosted:
        logging.info("Local single-user mode: complete Work IQ sign-in before the playground becomes ready.")
        local_auth = WorkIQAuth()
        local_auth.sign_in()

    credential = (
        ManagedIdentityCredential()
        if hosted
        else AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_TENANT_ID"), process_timeout=60)
    )
    with credential:
        client = FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
            credential=credential,
        )
        agent = Agent(
            client=client,
            name="Workmate",
            instructions="""You are Workmate, an assistant grounded in the signed-in user's
            Microsoft 365 workplace context. Use ask_work_iq for every workplace question.
            Respect the permissions and sensitivity boundaries returned by Work IQ.
            Preserve source citations, mention relevant dates and participants, and distinguish
            sourced facts from inference. Say clearly when Work IQ fails or does not provide
            enough information. Never claim access to content the signed-in user cannot access.
            This experiment is read-only; do not perform write actions.""",
            tools=[tool(ask_work_iq)],
            default_options={"store": False},
        )
        WorkIQResponsesHost(agent, local_auth=local_auth).run(host="0.0.0.0" if hosted else "127.0.0.1")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
