"""Tests for casting session management."""

from datetime import UTC, datetime, timedelta

import pytest

from cast.sessions import Session, SessionManager


@pytest.fixture
def session_manager():
    """Create session manager instance."""
    return SessionManager(session_ttl=300, cleanup_interval=60)


def test_session_creation():
    """Test Session dataclass creation."""
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=5)

    session = Session(
        id="test123",
        pin="123456",
        created_at=now,
        expires_at=expires,
    )

    assert session.id == "test123"
    assert session.pin == "123456"
    assert session.paired is False
    assert session.signaling_state == "new"
    assert session.is_expired is False


def test_session_expiration():
    """Test session expiration logic."""
    now = datetime.now(UTC)
    expired_time = now - timedelta(minutes=1)

    session = Session(
        id="test123",
        pin="123456",
        created_at=expired_time,
        expires_at=expired_time,
    )

    assert session.is_expired is True
    assert session.is_active is False


def test_session_active_state():
    """Test session active state (paired and not expired)."""
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=5)

    session = Session(
        id="test123",
        pin="123456",
        created_at=now,
        expires_at=expires,
        paired=True,
        paired_at=now,
    )

    assert session.is_expired is False
    assert session.is_active is True


def test_session_to_dict():
    """Test Session serialization."""
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=5)

    session = Session(
        id="test123",
        pin="123456",
        created_at=now,
        expires_at=expires,
    )

    data = session.to_dict()
    assert data["id"] == "test123"
    assert data["pin"] == "123456"  # PIN visible before pairing
    assert data["paired"] is False
    assert "created_at" in data
    assert "expires_at" in data


def test_session_to_dict_hides_pin_after_pairing():
    """Test that PIN is hidden after pairing."""
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=5)

    session = Session(
        id="test123",
        pin="123456",
        created_at=now,
        expires_at=expires,
        paired=True,
    )

    data = session.to_dict()
    assert data["pin"] is None  # PIN hidden after pairing
    assert data["paired"] is True


def test_create_session(session_manager):
    """Test creating a new session."""
    session = session_manager.create_session()

    assert session.id is not None
    assert len(session.pin) == 6
    assert session.pin.isdigit()
    assert session.paired is False
    assert session.is_expired is False


def test_get_session(session_manager):
    """Test retrieving a session by ID."""
    session = session_manager.create_session()
    retrieved = session_manager.get_session(session.id)

    assert retrieved is not None
    assert retrieved.id == session.id
    assert retrieved.pin == session.pin


def test_get_nonexistent_session(session_manager):
    """Test retrieving a nonexistent session."""
    retrieved = session_manager.get_session("nonexistent")
    assert retrieved is None


def test_get_session_by_pin(session_manager):
    """Test retrieving a session by PIN."""
    session = session_manager.create_session()
    retrieved = session_manager.get_session_by_pin(session.pin)

    assert retrieved is not None
    assert retrieved.id == session.id


def test_get_session_by_invalid_pin(session_manager):
    """Test retrieving a session with invalid PIN."""
    retrieved = session_manager.get_session_by_pin("000000")
    assert retrieved is None


def test_pair_session(session_manager):
    """Test pairing a session."""
    session = session_manager.create_session()
    device_info = {"device_type": "phone", "os": "iOS"}

    success = session_manager.pair_session(session.id, device_info)

    assert success is True

    retrieved = session_manager.get_session(session.id)
    assert retrieved is not None
    assert retrieved.paired is True
    assert retrieved.paired_at is not None
    assert retrieved.device_info == device_info


def test_pair_nonexistent_session(session_manager):
    """Test pairing a nonexistent session."""
    success = session_manager.pair_session("nonexistent", {})
    assert success is False


def test_unpair_session(session_manager):
    """Test unpairing and removing a session."""
    session = session_manager.create_session()
    success = session_manager.unpair_session(session.id)

    assert success is True

    retrieved = session_manager.get_session(session.id)
    assert retrieved is None


def test_unpair_nonexistent_session(session_manager):
    """Test unpairing a nonexistent session."""
    success = session_manager.unpair_session("nonexistent")
    assert success is False


def test_get_all_sessions(session_manager):
    """Test getting all active sessions."""
    session1 = session_manager.create_session()
    session2 = session_manager.create_session()

    sessions = session_manager.get_all_sessions()
    assert len(sessions) == 2
    assert session1.id in [s.id for s in sessions]
    assert session2.id in [s.id for s in sessions]


def test_get_paired_sessions(session_manager):
    """Test getting only paired sessions."""
    session1 = session_manager.create_session()
    _session2 = session_manager.create_session()  # Create but don't pair

    # Pair only session1
    session_manager.pair_session(session1.id)

    paired_sessions = session_manager.get_paired_sessions()
    assert len(paired_sessions) == 1
    assert paired_sessions[0].id == session1.id


@pytest.mark.asyncio
async def test_session_manager_start_stop(session_manager):
    """Test session manager lifecycle."""
    await session_manager.start()
    assert session_manager._cleanup_task is not None

    await session_manager.stop()
    assert session_manager._cleanup_task is None


@pytest.mark.asyncio
async def test_cleanup_expired_sessions():
    """Test automatic cleanup of expired sessions."""
    manager = SessionManager(session_ttl=1, cleanup_interval=1)
    await manager.start()

    # Create session with 1 second TTL
    session = manager.create_session()

    # Wait for expiration and cleanup
    import asyncio

    await asyncio.sleep(2)

    # Session should be cleaned up
    retrieved = manager.get_session(session.id)
    assert retrieved is None

    await manager.stop()


def test_unique_session_ids(session_manager):
    """Test that session IDs are unique."""
    session1 = session_manager.create_session()
    session2 = session_manager.create_session()

    assert session1.id != session2.id


def test_unique_pins(session_manager):
    """Test that PINs are unique (probabilistically)."""
    pins = set()
    for _ in range(10):
        session = session_manager.create_session()
        pins.add(session.pin)

    # With 6 digits (000000-999999), 10 PINs should be unique
    assert len(pins) == 10
