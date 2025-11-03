"""
Server-side audio capture for devices with built-in microphones.

Provides audio recording from local microphone (USB mic, built-in mic)
when phone relay is not available or user prefers local capture.
"""

import asyncio
import logging
import wave
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AudioBuffer:
    """Buffer for incoming audio chunks (shared with cast audio_relay)."""

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


class ServerAudioCapture:
    """Captures audio from server/device microphone."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        device_index: int | None = None,
    ):
        """Initialize server audio capture.

        Args:
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels (1=mono, 2=stereo)
            chunk_size: Size of audio chunks to read
            device_index: PyAudio device index (None for default)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        self._pyaudio = None
        self._stream = None
        self._is_recording = False
        self._audio_chunks: list[bytes] = []
        self._record_task: asyncio.Task | None = None

    def _init_pyaudio(self):
        """Lazy initialization of PyAudio."""
        if self._pyaudio is None:
            try:
                import pyaudio

                self._pyaudio = pyaudio.PyAudio()
                logger.info("PyAudio initialized")
            except ImportError as e:
                logger.error("PyAudio not installed: pip install pyaudio")
                raise RuntimeError(
                    "PyAudio required for server audio capture. "
                    "Install with: pip install pyaudio"
                ) from e

    def is_available(self) -> bool:
        """Check if server audio capture is available.

        Returns:
            True if PyAudio can be initialized and device found
        """
        try:
            self._init_pyaudio()
            device_count = self._pyaudio.get_device_count()
            if self.device_index is not None:
                return 0 <= self.device_index < device_count

            # Check for default input device
            try:
                default_info = self._pyaudio.get_default_input_device_info()
                return default_info is not None
            except Exception:
                return False

        except Exception as e:
            logger.warning(f"Server audio not available: {e}")
            return False

    def get_devices(self) -> list[dict[str, Any]]:
        """Get list of available audio input devices.

        Returns:
            List of device info dicts with name, index, channels, rate
        """
        self._init_pyaudio()
        devices = []

        for i in range(self._pyaudio.get_device_count()):
            try:
                info = self._pyaudio.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append(
                        {
                            "index": i,
                            "name": info.get("name", "Unknown"),
                            "channels": info.get("maxInputChannels", 0),
                            "sample_rate": int(info.get("defaultSampleRate", 0)),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to get device info for index {i}: {e}")

        return devices

    async def start_recording(self) -> None:
        """Start recording audio from microphone.

        Raises:
            RuntimeError: If PyAudio not available or already recording
        """
        if self._is_recording:
            raise RuntimeError("Already recording")

        self._init_pyaudio()

        # Open audio stream
        import pyaudio

        self._stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk_size,
        )

        self._is_recording = True
        self._audio_chunks = []

        # Start recording task
        self._record_task = asyncio.create_task(self._record_loop())
        logger.info(
            f"Started recording from device {self.device_index or 'default'} "
            f"at {self.sample_rate}Hz, {self.channels} channel(s)"
        )

    async def _record_loop(self) -> None:
        """Background task to continuously read from audio stream."""
        try:
            while self._is_recording and self._stream:
                # Read chunk (blocking I/O, run in executor)
                chunk = await asyncio.get_event_loop().run_in_executor(
                    None, self._stream.read, self.chunk_size, False
                )
                if chunk:
                    self._audio_chunks.append(chunk)

        except Exception as e:
            logger.error(f"Recording loop error: {e}")
            self._is_recording = False

    async def stop_recording(self) -> bytes:
        """Stop recording and return captured audio.

        Returns:
            Raw PCM audio bytes

        Raises:
            RuntimeError: If not currently recording
        """
        if not self._is_recording:
            raise RuntimeError("Not recording")

        self._is_recording = False

        # Wait for record task to finish
        if self._record_task:
            try:
                await asyncio.wait_for(self._record_task, timeout=1.0)
            except asyncio.TimeoutError:
                logger.warning("Record task timeout during stop")

        # Close stream
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        # Get audio data
        audio_data = b"".join(self._audio_chunks)
        duration = len(audio_data) / (self.sample_rate * self.channels * 2)

        logger.info(f"Stopped recording: {duration:.2f}s captured")

        return audio_data

    def to_wav_bytes(self, audio_data: bytes) -> bytes:
        """Convert raw PCM audio to WAV format.

        Args:
            audio_data: Raw PCM audio bytes

        Returns:
            WAV-formatted audio bytes
        """
        if not audio_data:
            return b""

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)

        return buffer.getvalue()

    def save_wav(self, audio_data: bytes, file_path: Path | str) -> None:
        """Save audio to WAV file.

        Args:
            audio_data: Raw PCM audio bytes
            file_path: Output file path
        """
        if not audio_data:
            logger.warning("No audio data to save")
            return

        with wave.open(str(file_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)

        duration = len(audio_data) / (self.sample_rate * self.channels * 2)
        logger.info(f"Saved {duration:.2f}s audio to {file_path}")

    def cleanup(self) -> None:
        """Cleanup PyAudio resources."""
        if self._stream:
            if self._stream.is_active():
                self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None

    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup()


# Global server audio capture instance
_server_audio: ServerAudioCapture | None = None


def get_server_audio() -> ServerAudioCapture:
    """Get global server audio capture instance.

    Returns:
        ServerAudioCapture singleton
    """
    global _server_audio
    if _server_audio is None:
        _server_audio = ServerAudioCapture()
    return _server_audio
