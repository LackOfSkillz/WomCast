"""
WomCast Cast REST API
WebRTC signaling and session management for phone/tablet casting.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from cast.mdns import MDNSAdvertiser
from cast.sessions import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

__version__ = "0.3.0"


class CreateSessionRequest(BaseModel):
    """Request model for creating a casting session."""

    device_type: str = "phone"  # phone, tablet, browser
    user_agent: str | None = None


class CreateSessionResponse(BaseModel):
    """Response model for session creation."""

    session_id: str
    pin: str
    expires_in_seconds: int
    qr_data: str  # JSON data for QR code generation


class PairSessionRequest(BaseModel):
    """Request model for pairing a session."""

    pin: str
    device_info: dict[str, Any] | None = None


class PairSessionResponse(BaseModel):
    """Response model for session pairing."""

    session_id: str
    paired: bool
    message: str


class SessionInfoResponse(BaseModel):
    """Response model for session information."""

    session_id: str
    paired: bool
    device_info: dict[str, Any]
    signaling_state: str
    created_at: str
    expires_at: str
    is_active: bool


class WebRTCSignal(BaseModel):
    """WebRTC signaling message."""

    type: str  # offer, answer, candidate
    session_id: str
    data: dict[str, Any]


# Global session manager
session_manager: SessionManager | None = None
mdns_advertiser: MDNSAdvertiser | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize session manager and mDNS on startup."""
    global session_manager, mdns_advertiser
    session_manager = SessionManager(session_ttl=300, cleanup_interval=60)
    await session_manager.start()
    logger.info("SessionManager started")

    # Start mDNS advertisement
    mdns_advertiser = MDNSAdvertiser(
        service_name="WomCast",
        service_type="_womcast-cast._tcp.local.",
        port=3005,
        properties={"version": __version__, "features": "webrtc,pairing"},
    )
    mdns_advertiser.start()

    yield

    # Cleanup
    if mdns_advertiser:
        mdns_advertiser.stop()
    await session_manager.stop()
    logger.info("SessionManager stopped")


app = FastAPI(title="WomCast Cast API", version=__version__, lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/version")
async def version():
    """Version endpoint."""
    return {"version": __version__, "service": "cast"}


@app.post("/v1/cast/session", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new casting session with PIN.

    Args:
        request: Session creation request with device type

    Returns:
        Session ID, PIN, and QR data for pairing

    Raises:
        HTTPException: 500 if session manager not initialized
    """
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    session = session_manager.create_session()

    # QR data contains session ID for client to connect
    import json

    qr_data = json.dumps(
        {
            "session_id": session.id,
            "service": "womcast-cast",
            "version": __version__,
        }
    )

    return CreateSessionResponse(
        session_id=session.id,
        pin=session.pin,
        expires_in_seconds=300,
        qr_data=qr_data,
    )


@app.post("/v1/cast/session/pair", response_model=PairSessionResponse)
async def pair_session(request: PairSessionRequest):
    """
    Pair a session using PIN code.

    Args:
        request: Pairing request with PIN and device info

    Returns:
        Pairing result

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 500 if session manager not initialized
    """
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    session = session_manager.get_session_by_pin(request.pin)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    success = session_manager.pair_session(session.id, request.device_info)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to pair session")

    return PairSessionResponse(
        session_id=session.id, paired=True, message="Session paired successfully"
    )


@app.get("/v1/cast/session/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """
    Get session information.

    Args:
        session_id: Session ID

    Returns:
        Session details

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 500 if session manager not initialized
    """
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    return SessionInfoResponse(
        session_id=session.id,
        paired=session.paired,
        device_info=session.device_info,
        signaling_state=session.signaling_state,
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        is_active=session.is_active,
    )


@app.delete("/v1/cast/session/{session_id}")
async def unpair_session(session_id: str):
    """
    Unpair and remove a session.

    Args:
        session_id: Session ID

    Returns:
        Success message

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 500 if session manager not initialized
    """
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    success = session_manager.unpair_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "ok", "message": "Session unpaired"}


@app.get("/v1/cast/sessions")
async def list_sessions():
    """
    List all active sessions.

    Returns:
        List of active sessions

    Raises:
        HTTPException: 500 if session manager not initialized
    """
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    sessions = session_manager.get_all_sessions()
    return {"sessions": [s.to_dict() for s in sessions]}


@app.websocket("/v1/cast/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for WebRTC signaling.

    Args:
        websocket: WebSocket connection
        session_id: Session ID for this connection

    Note:
        This is a basic signaling server for WebRTC.
        Clients exchange SDP offers/answers and ICE candidates through this.
    """
    if session_manager is None:
        await websocket.close(code=1008, reason="Session manager not initialized")
        return

    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found or expired")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")

    try:
        while True:
            data = await websocket.receive_json()

            # Echo signaling messages (simple relay)
            # In production, you'd validate and route to specific peers
            await websocket.send_json(
                {"type": "ack", "message_type": data.get("type"), "timestamp": "now"}
            )

            logger.info(f"Received WebRTC signal: {data.get('type')} for {session_id}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.close(code=1011, reason="Internal error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3005)
