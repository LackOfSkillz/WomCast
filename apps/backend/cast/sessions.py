"""
Session management for casting service.

Handles WebRTC signaling, PIN-based pairing, and session lifecycle.
"""

import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Casting session with PIN-based pairing."""

    id: str
    pin: str
    created_at: datetime
    expires_at: datetime
    paired: bool = False
    paired_at: datetime | None = None
    device_info: dict[str, Any] = field(default_factory=dict)
    signaling_state: str = "new"  # new, connecting, connected, closed

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if session is active (paired and not expired)."""
        return self.paired and not self.is_expired

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "pin": self.pin if not self.paired else None,  # Hide PIN after pairing
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "paired": self.paired,
            "paired_at": self.paired_at.isoformat() if self.paired_at else None,
            "device_info": self.device_info,
            "signaling_state": self.signaling_state,
            "is_expired": self.is_expired,
            "is_active": self.is_active,
        }


class SessionManager:
    """Manages casting sessions and PIN-based pairing."""

    def __init__(self, session_ttl: int = 300, cleanup_interval: int = 60):
        """Initialize session manager.

        Args:
            session_ttl: Session time-to-live in seconds (default 5 minutes)
            cleanup_interval: Cleanup interval in seconds (default 1 minute)
        """
        self._sessions: dict[str, Session] = {}
        self._session_ttl = session_ttl
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start session manager background tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session manager started")

    async def stop(self) -> None:
        """Stop session manager background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Session manager stopped")

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired sessions."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        now = datetime.now(UTC)
        expired_ids = [
            session_id
            for session_id, session in self._sessions.items()
            if session.expires_at < now
        ]

        for session_id in expired_ids:
            del self._sessions[session_id]
            logger.info(f"Cleaned up expired session {session_id}")

    def create_session(self) -> Session:
        """Create new casting session with PIN.

        Returns:
            New session with unique ID and PIN
        """
        session_id = secrets.token_urlsafe(16)
        pin = "".join(str(secrets.randbelow(10)) for _ in range(6))
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._session_ttl)

        session = Session(
            id=session_id, pin=pin, created_at=now, expires_at=expires_at
        )

        self._sessions[session_id] = session
        logger.info(f"Created session {session_id} with PIN {pin}")

        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session if found and not expired, None otherwise
        """
        session = self._sessions.get(session_id)
        if session and not session.is_expired:
            return session
        return None

    def get_session_by_pin(self, pin: str) -> Session | None:
        """Get session by PIN.

        Args:
            pin: 6-digit PIN

        Returns:
            Session if found and not expired, None otherwise
        """
        for session in self._sessions.values():
            if session.pin == pin and not session.is_expired:
                return session
        return None

    def pair_session(
        self, session_id: str, device_info: dict[str, Any] | None = None
    ) -> bool:
        """Mark session as paired.

        Args:
            session_id: Session ID
            device_info: Optional device information

        Returns:
            True if session was paired, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.paired = True
        session.paired_at = datetime.now(UTC)
        if device_info:
            session.device_info = device_info

        logger.info(f"Session {session_id} paired")
        return True

    def unpair_session(self, session_id: str) -> bool:
        """Unpair session and remove it.

        Args:
            session_id: Session ID

        Returns:
            True if session was unpaired, False otherwise
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Session {session_id} unpaired and removed")
            return True
        return False

    def get_all_sessions(self) -> list[Session]:
        """Get all active sessions.

        Returns:
            List of active sessions (not expired)
        """
        return [
            session for session in self._sessions.values() if not session.is_expired
        ]

    def get_paired_sessions(self) -> list[Session]:
        """Get all paired sessions.

        Returns:
            List of paired sessions (not expired)
        """
        return [
            session
            for session in self._sessions.values()
            if session.is_active
        ]
