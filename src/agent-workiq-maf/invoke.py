"""Test the same Workmate Responses server locally, then in Microsoft Foundry."""

import argparse
import os
from pathlib import Path

import httpx
from azure.identity import AzureDeveloperCliCredential
from dotenv import load_dotenv
from workiq_auth import sign_in

WORK_IQ_TOKEN_HEADER = "x-client-workiq-access-token"
LOCAL_RESPONSES_URL = "http://127.0.0.1:8088/responses"


def invoke(question: str, *, remote: bool) -> str:
    """Call locally with a Work IQ token, or remotely with Microsoft Foundry auth."""
    endpoint = LOCAL_RESPONSES_URL
    if remote:
        project = httpx.URL(os.environ["FOUNDRY_PROJECT_ENDPOINT"])
        if (
            project.scheme != "https"
            or not project.host.endswith(".services.ai.azure.com")
            or project.username
            or project.password
            or project.query
            or project.fragment
        ):
            raise ValueError("The remote project must be an HTTPS Microsoft Foundry project endpoint.")
        endpoint = (
            f"{str(project).rstrip('/')}/agents/agent-workiq-maf/endpoint/protocols/openai/responses?api-version=v1"
        )
    headers = {}
    if remote:
        with AzureDeveloperCliCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID") or os.environ["WORK_IQ_SEARCH_ENTRA_TENANT_ID"],
            process_timeout=60,
        ) as credential:
            headers["Authorization"] = f"Bearer {credential.get_token('https://ai.azure.com/.default').token}"
    else:
        headers[WORK_IQ_TOKEN_HEADER] = sign_in()["access_token"]

    with httpx.Client(timeout=240, follow_redirects=False) as client:
        response = client.post(
            endpoint,
            headers=headers,
            json={"input": question, "stream": False, "background": False, "store": False},
        )
        response.raise_for_status()
    body = response.json()
    if any(item.get("type") == "oauth_consent_request" for item in body.get("output", [])):
        raise PermissionError("Authorize the Work IQ MCP connection in the Microsoft Foundry playground, then retry.")
    if body.get("status") != "completed":
        raise RuntimeError(f"Agent response did not complete: {body.get('status')}; {body.get('error')}")
    text = "\n".join(
        content["text"]
        for item in body.get("output", [])
        for content in item.get("content", [])
        if content.get("type") == "output_text"
    )
    if not text:
        raise RuntimeError("The agent completed without a text answer.")
    return text


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
    parser = argparse.ArgumentParser(description="Test Workmate locally or in Microsoft Foundry.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--local", action="store_true", help="Call the loopback Responses server on port 8088.")
    target.add_argument(
        "--remote", action="store_true", help="Call agent-workiq-maf in the configured Foundry project."
    )
    parser.add_argument("question")
    args = parser.parse_args()
    print(invoke(args.question, remote=args.remote))
