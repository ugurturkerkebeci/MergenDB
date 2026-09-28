"""
MergenDB Authentication & User Management Subsystem.
Provides root user authentication, secure salt+SHA-256 password hashing,
session tokens, and Basic Auth verification.
Strictly zero external dependencies. Pure standard library.
"""

import os
import json
import hashlib
import secrets
import time
from typing import Optional, Dict, Any, Tuple, List

AUTH_FILE_NAME = "mergen_auth.json"


class AuthManager:
    """
    Manages users, passwords, and session tokens for MergenDB server.
    Default user: 'root'
    Default password: '' (empty string)
    """

    def __init__(self, data_dir: Optional[str] = None, auth_file: Optional[str] = None):
        if auth_file:
            self.auth_file_path = os.path.abspath(auth_file)
            self.data_dir = os.path.dirname(self.auth_file_path)
        else:
            self.data_dir = data_dir or os.getcwd()
            self.auth_file_path = os.path.join(self.data_dir, AUTH_FILE_NAME)
        self._tokens: Dict[str, Dict[str, Any]] = {}  # token -> {user, expires_at}
        self._load_or_init()

    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        if salt is None:
            salt = secrets.token_hex(16)
        salted = f"{salt}:{password}".encode("utf-8")
        hash_val = hashlib.sha256(salted).hexdigest()
        return hash_val, salt

    def _load_or_init(self):
        if os.path.exists(self.auth_file_path):
            try:
                with open(self.auth_file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                    if "users" not in self.data or "root" not in self.data["users"]:
                        self._init_defaults()
                    return
            except Exception:
                pass

        self._init_defaults()

    def _init_defaults(self):
        # Default root user with empty password ""
        pw_hash, salt = self._hash_password("")
        self.data = {
            "version": 1,
            "auth_required": True,
            "users": {
                "root": {
                    "hash": pw_hash,
                    "salt": salt,
                    "created_at": int(time.time()),
                    "roles": ["admin"]
                }
            }
        }
        self._save()

    def _save(self):
        try:
            with open(self.auth_file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def authenticate(self, username: str, password: str) -> bool:
        """Verifies username and password."""
        user_info = self.data.get("users", {}).get(username)
        if not user_info:
            return False
        expected_hash = user_info.get("hash")
        salt = user_info.get("salt")
        test_hash, _ = self._hash_password(password, salt=salt)
        return secrets.compare_digest(expected_hash, test_hash)

    def set_password(self, username: str, new_password: str) -> bool:
        """Updates the password for an existing user or creates user if not exists."""
        pw_hash, salt = self._hash_password(new_password)
        if "users" not in self.data:
            self.data["users"] = {}

        if username in self.data["users"]:
            self.data["users"][username]["hash"] = pw_hash
            self.data["users"][username]["salt"] = salt
            self.data["users"][username]["updated_at"] = int(time.time())
        else:
            self.data["users"][username] = {
                "hash": pw_hash,
                "salt": salt,
                "created_at": int(time.time()),
                "roles": ["user"]
            }
        self._save()
        return True

    def create_token(self, username: str, ttl_seconds: int = 86400) -> str:
        """Generates a secure bearer token for an authenticated user."""
        token = secrets.token_hex(24)
        self._tokens[token] = {
            "username": username,
            "expires_at": time.time() + ttl_seconds
        }
        return token

    def verify_token(self, token: str) -> Optional[str]:
        """Validates a bearer token. Returns username if valid, None if invalid/expired."""
        info = self._tokens.get(token)
        if not info:
            return None
        if time.time() > info["expires_at"]:
            del self._tokens[token]
            return None
        return info["username"]

    def verify_request_auth(
        self,
        headers: Dict[str, str],
        query_params: Optional[Dict[str, List[str]]] = None,
        body_dict: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Extracts credentials from Authorization header (Basic or Bearer),
        body_dict (username/password/token), or query params.
        Returns (is_authenticated, username).
        """
        # 1. Authorization header: Bearer <token>
        auth_hdr = headers.get("authorization", headers.get("Authorization", "")).strip()
        if auth_hdr.lower().startswith("bearer "):
            token = auth_hdr[7:].strip()
            user = self.verify_token(token)
            if user:
                return True, user

        # 2. Authorization header: Basic <base64>
        if auth_hdr.lower().startswith("basic "):
            import base64
            try:
                b64_str = auth_hdr[6:].strip()
                decoded = base64.b64decode(b64_str).decode("utf-8")
                parts = decoded.split(":", 1)
                u = parts[0]
                p = parts[1] if len(parts) > 1 else ""
                if self.authenticate(u, p):
                    return True, u
            except Exception:
                pass

        # 3. Custom headers: X-Mergen-User / X-Mergen-Password / X-Mergen-Token
        user_hdr = headers.get("x-mergen-user", headers.get("X-Mergen-User"))
        pass_hdr = headers.get("x-mergen-password", headers.get("X-Mergen-Password", ""))
        token_hdr = headers.get("x-mergen-token", headers.get("X-Mergen-Token"))
        if token_hdr:
            u = self.verify_token(token_hdr)
            if u:
                return True, u
        if user_hdr is not None:
            if self.authenticate(user_hdr, pass_hdr or ""):
                return True, user_hdr

        # 4. Check body_dict if provided
        if body_dict and isinstance(body_dict, dict):
            if "token" in body_dict:
                u = self.verify_token(str(body_dict["token"]))
                if u:
                    return True, u
            if "username" in body_dict or "user" in body_dict:
                u = str(body_dict.get("username") or body_dict.get("user"))
                p = str(body_dict.get("password") or "")
                if self.authenticate(u, p):
                    return True, u

        # 5. Check query_params if provided
        if query_params:
            if "token" in query_params and query_params["token"]:
                u = self.verify_token(query_params["token"][0])
                if u:
                    return True, u
            user_param = query_params.get("username", query_params.get("user", [""]))[0]
            if user_param:
                pass_param = query_params.get("password", [""])[0]
                if self.authenticate(user_param, pass_param):
                    return True, user_param

        return False, None

    def list_users(self) -> List[str]:
        return list(self.data.get("users", {}).keys())

    def delete_user(self, username: str) -> bool:
        if username == "root":
            return False  # Root user cannot be deleted
        if username in self.data.get("users", {}):
            del self.data["users"][username]
            self._save()
            return True
        return False


_global_auth_manager: Optional[AuthManager] = None

def get_auth_manager(data_dir: Optional[str] = None) -> AuthManager:
    global _global_auth_manager
    if _global_auth_manager is None or (data_dir and _global_auth_manager.data_dir != data_dir):
        _global_auth_manager = AuthManager(data_dir=data_dir)
    return _global_auth_manager
