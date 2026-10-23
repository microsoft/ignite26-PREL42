"""Notebook-style Work IQ sign-in with an in-memory MSAL cache."""

import os
from threading import Lock

from msal import PublicClientApplication

WORK_IQ_SCOPE = "api://workiq.svc.cloud.microsoft/WorkIQAgent.Ask"


class WorkIQAuth:
    """Acquire delegated tokens for one local user, without persisting credentials."""

    def __init__(self) -> None:
        missing = [
            name for name in ("WORK_IQ_SEARCH_ENTRA_APP_ID", "WORK_IQ_SEARCH_ENTRA_TENANT_ID") if not os.getenv(name)
        ]
        if missing:
            raise RuntimeError(f"Set these values in the repository .env: {', '.join(missing)}")
        self.app = PublicClientApplication(
            client_id=os.environ["WORK_IQ_SEARCH_ENTRA_APP_ID"],
            authority=f"https://login.microsoftonline.com/{os.environ['WORK_IQ_SEARCH_ENTRA_TENANT_ID']}",
        )
        self._lock = Lock()

    def sign_in(self) -> dict:
        """Sign in interactively before starting the local server or invoking remotely."""
        if os.getenv("CODESPACES") == "true":
            flow = self.app.initiate_device_flow(scopes=[WORK_IQ_SCOPE])
            if "user_code" not in flow:
                raise RuntimeError(f"Work IQ device sign-in failed: {flow.get('error_description', 'No user code')}")
            print(flow["message"], flush=True)
            result = self.app.acquire_token_by_device_flow(flow)
        else:
            print("Sign in to Work IQ in the browser with your lab user account.", flush=True)
            result = self.app.acquire_token_interactive([WORK_IQ_SCOPE])
        if not result or not result.get("access_token"):
            description = result.get("error_description", "No access token returned") if result else "Sign-in cancelled"
            raise RuntimeError(f"Work IQ authentication failed: {description}")
        return result

    def get_access_token(self) -> str:
        """Read or silently renew the signed-in user's token; never switch identities."""
        with self._lock:
            accounts = self.app.get_accounts()
            if len(accounts) != 1:
                raise PermissionError("Restart the local agent and sign in to Work IQ with one lab user account.")
            result = self.app.acquire_token_silent_with_error([WORK_IQ_SCOPE], account=accounts[0])
            if not result or not result.get("access_token"):
                raise PermissionError(
                    "Work IQ sign-in expired or was revoked. Restart the local agent and sign in again."
                )
            return result["access_token"]


def sign_in() -> dict:
    """Acquire a delegated token for the optional invocation client."""
    return WorkIQAuth().sign_in()
