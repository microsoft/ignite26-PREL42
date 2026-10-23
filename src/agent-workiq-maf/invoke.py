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
    """Forward a fresh Work IQ token to the local server or the lab's hosted agent."""
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
    result = sign_in()
    headers = {WORK_IQ_TOKEN_HEADER: result["access_token"]}
    if remote:
        # MSAL validates this identity claim; never decode a downstream access token.
        user_id = result.get("id_token_claims", {}).get("oid")
        if not user_id:
            raise RuntimeError("Work IQ sign-in returned no user object ID for Foundry user isolation.")
        headers["x-ms-user-identity"] = user_id
        with AzureDeveloperCliCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID") or os.environ["WORK_IQ_SEARCH_ENTRA_TENANT_ID"],
            process_timeout=60,
        ) as credential:
            headers["Authorization"] = f"Bearer {credential.get_token('https://ai.azure.com/.default').token}"

    with httpx.Client(timeout=240, follow_redirects=False) as client:
        response = client.post(
            endpoint,
            headers=headers,
            json={"input": question, "stream": False, "background": False, "store": False},
        )
        response.raise_for_status()
    body = response.json()
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
    parser = argparse.ArgumentParser(description="Sign in to Work IQ and test the Workmate Responses server.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--local", action="store_true", help="Call the loopback Responses server on port 8088.")
    target.add_argument(
        "--remote", action="store_true", help="Call agent-workiq-maf in the configured Foundry project."
    )
    parser.add_argument("question")
    args = parser.parse_args()
    print(invoke(args.question, remote=args.remote))
