"""
Audio relay module for phone microphone to backend streaming.

Handles WebRTC audio streaming from phone/tablet microphones for voice input.
Supports multiple audio formats and buffering for speech recognition.
"""

import asyncio
import logging
import wave
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioBuffer:
    """Buffer for incoming audio chunks."""

    def __init__(self, max_duration_seconds: float = 30.0):
        """Initialize audio buffer.

        Args:
            max_duration_seconds: Maximum audio duration to buffer
        """
        self.chunks: list[bytes] = []
        self.max_duration = max_duration_seconds
        self.sample_rate = 16000  # 16kHz for Whisper
        self.channels = 1  # Mono
        self.sample_width = 2  # 16-bit PCM
        self.created_at = datetime.now(UTC)

    def add_chunk(self, chunk: bytes) -> None:
        """Add audio chunk to buffer.

        Args:
            chunk: Raw PCM audio data
        """
        self.chunks.append(chunk)

        # Limit buffer size
        total_bytes = sum(len(c) for c in self.chunks)
        bytes_per_second = self.sample_rate * self.channels * self.sample_width
        max_bytes = int(bytes_per_second * self.max_duration)

        if total_bytes > max_bytes:
            # Remove oldest chunks
            while total_bytes > max_bytes and self.chunks:
                removed = self.chunks.pop(0)
                total_bytes -= len(removed)

    def get_audio_bytes(self) -> bytes:
        """Get concatenated audio data.

        Returns:
            Raw PCM audio bytes
        """
        return b"".join(self.chunks)

    def get_duration_seconds(self) -> float:
        """Get current buffer duration.

        Returns:
            Duration in seconds
        """
        total_bytes = sum(len(c) for c in self.chunks)
        bytes_per_second = self.sample_rate * self.channels * self.sample_width
        return total_bytes / bytes_per_second if bytes_per_second > 0 else 0.0

    def clear(self) -> None:
        """Clear buffer."""
        self.chunks.clear()
        self.created_at = datetime.now(UTC)

    def save_wav(self, file_path: Path | str) -> None:
        """Save buffer contents as WAV file.

        Args:
            file_path: Output file path
        """
        audio_data = self.get_audio_bytes()
        if not audio_data:
            logger.warning("No audio data to save")
            return

        with wave.open(str(file_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)

        logger.info(
            f"Saved {self.get_duration_seconds():.2f}s audio to {file_path}"
        )

    def to_wav_bytes(self) -> bytes:
        """Convert buffer to WAV format in memory.

        Returns:
            WAV-formatted audio bytes
        """
        audio_data = self.get_audio_bytes()
        if not audio_data:
            return b""

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)

        return buffer.getvalue()


class AudioRelay:
    """Manages audio streaming from phone microphones."""

    def __init__(self):
        """Initialize audio relay."""
        self._active_streams: dict[str, AudioBuffer] = {}
        self._stream_locks: dict[str, asyncio.Lock] = {}

    def start_stream(self, session_id: str) -> AudioBuffer:
        """Start audio stream for session.

        Args:
            session_id: Session ID

        Returns:
            Audio buffer for this stream
        """
        if session_id not in self._active_streams:
            self._active_streams[session_id] = AudioBuffer()
            self._stream_locks[session_id] = asyncio.Lock()
            logger.info(f"Started audio stream for session {session_id}")

        return self._active_streams[session_id]

    def stop_stream(self, session_id: str) -> AudioBuffer | None:
        """Stop audio stream and return buffer.

        Args:
            session_id: Session ID

        Returns:
            Final audio buffer or None if stream not found
        """
        buffer = self._active_streams.pop(session_id, None)
        self._stream_locks.pop(session_id, None)

        if buffer:
            logger.info(
                f"Stopped audio stream for session {session_id} "
                f"({buffer.get_duration_seconds():.2f}s recorded)"
            )

        return buffer

    async def add_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        """Add audio chunk to stream.

        Args:
            session_id: Session ID
            chunk: Raw PCM audio data
        """
        if session_id not in self._active_streams:
            logger.warning(f"No active stream for session {session_id}")
            return

        lock = self._stream_locks.get(session_id)
        if lock:
            async with lock:
                self._active_streams[session_id].add_chunk(chunk)

    def get_buffer(self, session_id: str) -> AudioBuffer | None:
        """Get audio buffer for session.

        Args:
            session_id: Session ID

        Returns:
            Audio buffer or None if not found
        """
        return self._active_streams.get(session_id)

    def get_active_streams(self) -> list[str]:
        """Get list of active stream session IDs.

        Returns:
            List of session IDs with active audio streams
        """
        return list(self._active_streams.keys())

    def clear_stream(self, session_id: str) -> bool:
        """Clear audio buffer for session without stopping stream.

        Args:
            session_id: Session ID

        Returns:
            True if buffer was cleared, False if stream not found
        """
        buffer = self._active_streams.get(session_id)
        if buffer:
            buffer.clear()
            logger.info(f"Cleared audio buffer for session {session_id}")
            return True
        return False
