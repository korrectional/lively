"""
Gmail Integration for Lively.
Handles Google OAuth 2.0 authorization links, token storage, and sending messages.
"""

import json
import base64
import time
from urllib.parse import urlencode
from email.mime.text import MIMEText
from typing import Optional, Dict, Any
from pathlib import Path
import requests

from lively.config import (
    GMAIL_TOKEN_FILE,
    GMAIL_CREDENTIALS_FILE,
    USER_EMAIL,
    TAILSCALE_BASE_URL,
    ensure_directories
)
from lively.memory import memory

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

class EmailService:
    """Manages Gmail authentication and outbound email sending."""

    def __init__(self, token_path: Path = GMAIL_TOKEN_FILE, creds_path: Path = GMAIL_CREDENTIALS_FILE):
        self.token_path = Path(token_path)
        self.creds_path = Path(creds_path)
        ensure_directories()

    def get_client_config(self) -> Dict[str, str]:
        """Fetch client_id and client_secret from file or environment."""
        import os
        client_id = os.getenv("GMAIL_CLIENT_ID", "")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET", "")

        if self.creds_path.exists():
            try:
                data = json.loads(self.creds_path.read_text(encoding="utf-8"))
                # Support both raw {client_id, client_secret} and Google console downloaded json format {installed: {...}}
                installed = data.get("installed") or data.get("web") or data
                client_id = installed.get("client_id", client_id)
                client_secret = installed.get("client_secret", client_secret)
            except Exception as e:
                print(f"[EmailService] Error reading credentials file: {e}")

        return {"client_id": client_id, "client_secret": client_secret}

    def is_authenticated(self) -> bool:
        """Check if an active token or refresh token is saved."""
        if not self.token_path.exists():
            return False
        try:
            data = json.loads(self.token_path.read_text(encoding="utf-8"))
            return bool(data.get("refresh_token") or data.get("access_token"))
        except Exception:
            return False

    def get_authorization_url(self, redirect_uri: Optional[str] = None) -> str:
        """
        Generate Google OAuth 2.0 authorization URL.
        User visits this link on any browser to authorize Lively.
        """
        cfg = self.get_client_config()
        client_id = cfg.get("client_id")
        if not client_id:
            # Informative placeholder if user hasn't created OAuth client ID yet
            return (
                f"# GMAIL_CLIENT_ID not configured.\n"
                f"# Please place your Google OAuth client secret JSON at: {self.creds_path}\n"
                f"# or export GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET."
            )

        if not redirect_uri:
            redirect_uri = f"{TAILSCALE_BASE_URL}/auth/gmail/callback"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GMAIL_SEND_SCOPE,
            "access_type": "offline",
            "prompt": "consent"
        }
        return f"{AUTH_ENDPOINT}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Exchange the authorization code for access & refresh tokens."""
        cfg = self.get_client_config()
        if not redirect_uri:
            redirect_uri = f"{TAILSCALE_BASE_URL}/auth/gmail/callback"

        payload = {
            "code": code,
            "client_id": cfg.get("client_id"),
            "client_secret": cfg.get("client_secret"),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        resp = requests.post(TOKEN_ENDPOINT, data=payload, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to exchange code: {resp.status_code} {resp.text}")

        token_data = resp.json()
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
        self.token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        return token_data

    def get_valid_access_token(self) -> Optional[str]:
        """Return a valid access token, refreshing if necessary."""
        if not self.token_path.exists():
            return None

        try:
            token_data = json.loads(self.token_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        access_token = token_data.get("access_token")
        expires_at = token_data.get("expires_at", 0)
        refresh_token = token_data.get("refresh_token")

        # If token is still valid (with 60s margin)
        if access_token and time.time() < (expires_at - 60):
            return access_token

        # Needs refresh
        if not refresh_token:
            return access_token

        cfg = self.get_client_config()
        payload = {
            "client_id": cfg.get("client_id"),
            "client_secret": cfg.get("client_secret"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        try:
            resp = requests.post(TOKEN_ENDPOINT, data=payload, timeout=10)
            if resp.status_code == 200:
                new_data = resp.json()
                token_data["access_token"] = new_data["access_token"]
                token_data["expires_at"] = time.time() + new_data.get("expires_in", 3600)
                self.token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
                return token_data["access_token"]
            else:
                print(f"[EmailService] Refresh error: {resp.text}")
        except Exception as e:
            print(f"[EmailService] Refresh exception: {e}")

        return access_token

    def send_email(self, subject: str, body: str, recipient: Optional[str] = None) -> Dict[str, Any]:
        """Send an email from Lively via Gmail API."""
        target_email = recipient or USER_EMAIL
        access_token = self.get_valid_access_token()

        if not access_token:
            error_msg = "Gmail is not authenticated yet. Run 'lively auth-gmail' to link your account."
            print(f"[EmailService] {error_msg}")
            return {"success": False, "error": error_msg}

        # Build raw MIME message
        message = MIMEText(body, "plain", "utf-8")
        message["to"] = target_email
        message["from"] = f"Lively the Robot Squirrel <{target_email}>"
        message["subject"] = subject

        raw_b64 = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        resp = requests.post(url, headers=headers, json={"raw": raw_b64}, timeout=15)

        if resp.status_code in (200, 201):
            memory.log_sent_email(target_email, subject, body)
            return {"success": True, "message_id": resp.json().get("id")}
        else:
            return {"success": False, "error": f"{resp.status_code} - {resp.text}"}

# Global singleton
email_service = EmailService()
