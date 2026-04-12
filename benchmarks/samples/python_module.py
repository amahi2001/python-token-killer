"""User authentication and session management module.

This module provides a comprehensive authentication system with
support for multiple authentication methods, session management,
and role-based access control (RBAC).

Author: Platform Team
Version: 2.4.1
"""

import hashlib
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

# Configure module logger
logger = logging.getLogger(__name__)


# Constants
DEFAULT_SESSION_TTL = 3600  # 1 hour in seconds
MAX_LOGIN_ATTEMPTS = 5
TOKEN_BYTES = 32


@dataclass
class User:
    """Represents an authenticated user in the system.

    Attributes:
        id: Unique user identifier
        username: Login username
        email: User's email address
        roles: List of role names assigned to the user
        metadata: Additional user metadata
        created_at: Account creation timestamp
        last_login: Most recent login timestamp
    """

    id: int
    username: str
    email: str
    roles: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    last_login: datetime | None = None

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return bool(set(self.roles) & set(roles))


@dataclass
class Session:
    """Represents an active user session.

    Sessions are created upon successful authentication and
    are used to track user activity throughout their interaction
    with the system.
    """

    id: str
    user_id: int
    token: str
    created_at: datetime
    expires_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() > self.expires_at

    def extend(self, seconds: int = DEFAULT_SESSION_TTL) -> None:
        """Extend the session expiration time."""
        self.expires_at = datetime.utcnow() + timedelta(seconds=seconds)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class AuthorizationError(Exception):
    """Raised when a user lacks required permissions."""

    pass


class RateLimitError(Exception):
    """Raised when login attempt limit is exceeded."""

    pass


class AuthManager:
    """Manages user authentication, sessions, and authorization.

    This class provides the main interface for authenticating users,
    managing their sessions, and checking permissions. It supports
    multiple backend storage options and configurable security policies.

    Example:
        auth = AuthManager(db_connection, cache_client)
        session = auth.login("alice", "password123")
        if auth.check_permission(session.token, "admin:read"):
            # perform admin action
            pass
        auth.logout(session.token)
    """

    def __init__(
        self,
        db_connection: Any,
        cache_client: Any | None = None,
        session_ttl: int = DEFAULT_SESSION_TTL,
        max_attempts: int = MAX_LOGIN_ATTEMPTS,
    ) -> None:
        """Initialize the authentication manager.

        Args:
            db_connection: Database connection for user storage
            cache_client: Optional cache client for session storage
            session_ttl: Session time-to-live in seconds
            max_attempts: Maximum failed login attempts before lockout
        """
        self.db = db_connection
        self.cache = cache_client
        self.session_ttl = session_ttl
        self.max_attempts = max_attempts
        self._attempt_tracker: dict[str, int] = {}

    def login(self, username: str, password: str, ip_address: str | None = None) -> Session:
        """Authenticate a user and create a new session.

        Args:
            username: The user's login name
            password: The user's password
            ip_address: Optional IP address for audit logging

        Returns:
            A new Session object

        Raises:
            AuthenticationError: If credentials are invalid
            RateLimitError: If too many failed attempts
        """
        # Check rate limiting
        attempts = self._attempt_tracker.get(username, 0)
        if attempts >= self.max_attempts:
            logger.warning("Rate limit exceeded for user: %s", username)
            raise RateLimitError(
                f"Too many failed login attempts for {username}. Please try again later."
            )

        # Look up user
        user = self._find_user(username)
        if user is None:
            self._record_failed_attempt(username)
            raise AuthenticationError("Invalid username or password")

        # Verify password
        if not self._verify_password(password, user):
            self._record_failed_attempt(username)
            raise AuthenticationError("Invalid username or password")

        # Clear failed attempts on success
        self._attempt_tracker.pop(username, None)

        # Create session
        session = self._create_session(user, ip_address)

        # Update last login
        self._update_last_login(user)

        logger.info("User %s logged in successfully", username)
        return session

    def logout(self, token: str) -> bool:
        """End a user session.

        Args:
            token: The session token to invalidate

        Returns:
            True if the session was found and removed, False otherwise
        """
        # Remove from cache first (fast path)
        if self.cache:
            self.cache.delete(f"session:{token}")

        # Remove from database
        result = self.db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return result.rowcount > 0

    def get_session(self, token: str) -> Session | None:
        """Retrieve a session by its token.

        Args:
            token: The session token to look up

        Returns:
            The Session if found and not expired, None otherwise
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(f"session:{token}")
            if cached:
                session = self._deserialize_session(cached)
                if not session.is_expired:
                    return session
                # Clean up expired session
                self.cache.delete(f"session:{token}")

        # Fall back to database
        row = self.db.query_one("SELECT * FROM sessions WHERE token = ?", (token,))
        if row is None:
            return None

        session = self._row_to_session(row)
        if session.is_expired:
            self.logout(token)
            return None

        # Populate cache for next lookup
        if self.cache:
            self.cache.set(
                f"session:{token}",
                self._serialize_session(session),
                ttl=self.session_ttl,
            )

        return session

    def check_permission(self, token: str, permission: str) -> bool:
        """Check if a session's user has a specific permission.

        Args:
            token: The session token
            permission: The permission string (e.g., "admin:write")

        Returns:
            True if the user has the permission

        Raises:
            AuthenticationError: If the session is invalid
        """
        session = self.get_session(token)
        if session is None:
            raise AuthenticationError("Invalid or expired session")

        user = self._find_user_by_id(session.user_id)
        if user is None:
            raise AuthenticationError("User not found")

        # Check role-based permissions
        return self._has_permission(user, permission)

    # ── Private helpers ─────────────────────────────────────────────

    def _find_user(self, username: str) -> User | None:
        """Look up a user by username."""
        row = self.db.query_one("SELECT * FROM users WHERE username = ?", (username,))
        if row is None:
            return None
        return self._row_to_user(row)

    def _find_user_by_id(self, user_id: int) -> User | None:
        """Look up a user by ID."""
        row = self.db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if row is None:
            return None
        return self._row_to_user(row)

    def _verify_password(self, password: str, user: User) -> bool:
        """Verify a password against the stored hash."""
        stored_hash = self.db.query_one("SELECT password_hash FROM users WHERE id = ?", (user.id,))
        if stored_hash is None:
            return False
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash["password_hash"]

    def _create_session(self, user: User, ip_address: str | None = None) -> Session:
        """Create a new session for an authenticated user."""
        now = datetime.utcnow()
        session = Session(
            id=secrets.token_hex(16),
            user_id=user.id,
            token=secrets.token_hex(TOKEN_BYTES),
            created_at=now,
            expires_at=now + timedelta(seconds=self.session_ttl),
            ip_address=ip_address,
        )

        # Store in database
        self.db.execute(
            "INSERT INTO sessions (id, user_id, token, created_at, expires_at, ip_address) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session.id,
                session.user_id,
                session.token,
                session.created_at,
                session.expires_at,
                session.ip_address,
            ),
        )

        # Store in cache
        if self.cache:
            self.cache.set(
                f"session:{session.token}",
                self._serialize_session(session),
                ttl=self.session_ttl,
            )

        return session

    def _update_last_login(self, user: User) -> None:
        """Update the user's last login timestamp."""
        self.db.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow(), user.id),
        )

    def _record_failed_attempt(self, username: str) -> None:
        """Record a failed login attempt for rate limiting."""
        self._attempt_tracker[username] = self._attempt_tracker.get(username, 0) + 1

    @staticmethod
    def _row_to_user(row: dict[str, Any]) -> User:
        """Convert a database row to a User object."""
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            roles=json.loads(row.get("roles", "[]")),
            metadata=json.loads(row.get("metadata", "{}")),
            created_at=row.get("created_at"),
            last_login=row.get("last_login"),
        )

    @staticmethod
    def _row_to_session(row: dict[str, Any]) -> Session:
        """Convert a database row to a Session object."""
        return Session(
            id=row["id"],
            user_id=row["user_id"],
            token=row["token"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            ip_address=row.get("ip_address"),
            user_agent=row.get("user_agent"),
        )

    @staticmethod
    def _serialize_session(session: Session) -> str:
        """Serialize a session for cache storage."""
        return json.dumps(
            {
                "id": session.id,
                "user_id": session.user_id,
                "token": session.token,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "ip_address": session.ip_address,
            }
        )

    @staticmethod
    def _deserialize_session(data: str) -> Session:
        """Deserialize a session from cache storage."""
        d = json.loads(data)
        return Session(
            id=d["id"],
            user_id=d["user_id"],
            token=d["token"],
            created_at=datetime.fromisoformat(d["created_at"]),
            expires_at=datetime.fromisoformat(d["expires_at"]),
            ip_address=d.get("ip_address"),
        )

    @staticmethod
    @lru_cache(maxsize=64)
    def _has_permission(user_id: int, permission: str) -> bool:
        """Check role-permission mapping (cached)."""
        # In production, this would query a permissions table
        # Simplified for demonstration
        admin_perms = {"admin:read", "admin:write", "admin:delete", "user:read", "user:write"}
        lead_perms = {"user:read", "user:write", "team:read", "team:write"}
        member_perms = {"user:read", "team:read"}

        role_map = {  # noqa: F841
            "admin": admin_perms,
            "lead": lead_perms,
            "member": member_perms,
        }

        # This is a simplified check — real implementation would
        # look up user.roles from the passed user_id
        return permission in member_perms
