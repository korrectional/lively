"""
Gmail Integration for Lively.
Supports both Google OAuth 2.0 authorization links and Gmail App Passwords (SMTP).
"""

import json
import base64
import time
import smtplib
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
    BASE_DATA_DIR,
    ensure_directories
)
from lively.memory import memory

GMAIL_CONFIG_FILE = BASE_DATA_DIR / "gmail_config.json"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

class EmailService:
    """Manages Gmail authentication (OAuth2 & App Password) and outbound sending."""

    def __init__(self, token_path: Path = GMAIL_TOKEN_FILE, creds_path: Path = GMAIL_CREDENTIALS_FILE, config_path: Path = GMAIL_CONFIG_FILE):
        self.token_path = Path(token_path)
        self.creds_path = Path(creds_path)
        self.config_path = Path(config_path)
        ensure_directories()

    def get_settings(self) -> Dict[str, Any]:
        """Fetch current email configuration."""
        cfg = {
            "method": "oauth",  # "oauth" or "app_password"
            "user_email": USER_EMAIL,
            "client_id": "",
            "client_secret": "",
            "app_password": "",
            "authenticated": self.is_authenticated()
        }
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                cfg.update(data)
            except Exception:
                pass
        if self.creds_path.exists():
            try:
                cdata = json.loads(self.creds_path.read_text(encoding="utf-8"))
                installed = cdata.get("installed") or cdata.get("web") or cdata
                cfg["client_id"] = installed.get("client_id", cfg["client_id"])
                cfg["client_secret"] = installed.get("client_secret", cfg["client_secret"])
            except Exception:
                pass
        cfg["authenticated"] = self.is_authenticated()
        return cfg

    def save_settings(self, method: str, user_email: str, client_id: str = "", client_secret: str = "", app_password: str = "") -> Dict[str, Any]:
        """Save settings and credentials."""
        current = self.get_settings()
        current["method"] = method
        if user_email:
            current["user_email"] = user_email.strip()
        if client_id:
            current["client_id"] = client_id.strip()
        if client_secret:
            current["client_secret"] = client_secret.strip()
        if app_password:
            # Strip spaces commonly present in 16-char app passwords like 'xxxx yyyy zzzz wwww'
            current["app_password"] = app_password.replace(" ", "").strip()

        self.config_path.write_text(json.dumps(current, indent=2), encoding="utf-8")

        # Also write standard credentials file if OAuth client id/secret provided
        if client_id and client_secret:
            self.creds_path.write_text(json.dumps({
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            }, indent=2), encoding="utf-8")

        return self.get_settings()

    def is_authenticated(self) -> bool:
        """Check if email sending is configured and ready."""
        # 1. Check App Password mode
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                if data.get("method") == "app_password" and data.get("app_password") and data.get("user_email"):
                    return True
            except Exception:
                pass

        # 2. Check OAuth Token
        if self.token_path.exists():
            try:
                data = json.loads(self.token_path.read_text(encoding="utf-8"))
                return bool(data.get("refresh_token") or data.get("access_token"))
            except Exception:
                pass

        return False

    def get_authorization_url(self, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Generate Google OAuth 2.0 authorization URL."""
        cfg = self.get_settings()
        client_id = cfg.get("client_id")
        if not client_id:
            return {
                "success": False,
                "error": "Client ID is not configured yet. Paste your Client ID & Secret in the Connect tab or use an App Password.",
                "auth_url": None
            }

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
        return {
            "success": True,
            "auth_url": f"{AUTH_ENDPOINT}?{urlencode(params)}"
        }

    def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Exchange authorization code for OAuth tokens."""
        cfg = self.get_settings()
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
        """Return a valid OAuth access token, refreshing if necessary."""
        if not self.token_path.exists():
            return None

        try:
            token_data = json.loads(self.token_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        access_token = token_data.get("access_token")
        expires_at = token_data.get("expires_at", 0)
        refresh_token = token_data.get("refresh_token")

        if access_token and time.time() < (expires_at - 60):
            return access_token

        if not refresh_token:
            return access_token

        cfg = self.get_settings()
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
        except Exception as e:
            print(f"[EmailService] Refresh error: {e}")

        return access_token

    def send_email(self, subject: str, body: str, recipient: Optional[str] = None) -> Dict[str, Any]:
        """Send an email from Lively using OAuth or SMTP App Password."""
        cfg = self.get_settings()
        target_email = recipient or cfg.get("user_email") or USER_EMAIL

        # Method 1: App Password via SMTP SSL
        if cfg.get("method") == "app_password" and cfg.get("app_password"):
            sender = cfg.get("user_email") or USER_EMAIL
            pwd = cfg.get("app_password")
            try:
                msg = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = subject
                msg["From"] = f"Lively the Robot Squirrel <{sender}>"
                msg["To"] = target_email

                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12) as server:
                    server.login(sender, pwd)
                    server.sendmail(sender, [target_email], msg.as_string())

                memory.log_sent_email(target_email, subject, body)
                return {"success": True, "method": "smtp_app_password"}
            except Exception as e:
                print(f"[EmailService] SMTP error: {e}")
                return {"success": False, "error": str(e)}

        # Method 2: OAuth 2.0 via Gmail API
        access_token = self.get_valid_access_token()
        if access_token:
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
                return {"success": True, "message_id": resp.json().get("id"), "method": "oauth"}
            return {"success": False, "error": f"{resp.status_code} - {resp.text}"}

        return {
            "success": False,
            "error": "Gmail is not configured. Open the Connect tab in the web UI to set up an App Password or OAuth link."
        }

# Global singleton
email_service = EmailService()
