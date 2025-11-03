"""
Tests for audio_relay module.
"""

import asyncio
from pathlib import Path

import pytest

from cast.audio_relay import AudioBuffer, AudioRelay


class TestAudioBuffer:
    """Test AudioBuffer class."""

    def test_init(self):
        """Test buffer initialization."""
        buffer = AudioBuffer()
        assert buffer.sample_rate == 16000
        assert buffer.channels == 1
        assert buffer.sample_width == 2
        assert buffer.max_duration == 30.0
        assert len(buffer.chunks) == 0

    def test_init_custom(self):
        """Test buffer with custom parameters."""
        buffer = AudioBuffer(max_duration_seconds=60.0)
        assert buffer.sample_rate == 16000  # Fixed at 16kHz
        assert buffer.max_duration == 60.0

    def test_add_chunk(self):
        """Test adding audio chunks."""
        buffer = AudioBuffer()
        chunk1 = b"\x00\x01" * 100  # 100 samples
        chunk2 = b"\x02\x03" * 100  # 100 samples

        buffer.add_chunk(chunk1)
        assert len(buffer.chunks) == 1
        assert buffer.chunks[0] == chunk1

        buffer.add_chunk(chunk2)
        assert len(buffer.chunks) == 2
        assert buffer.chunks[1] == chunk2

    def test_get_audio_bytes(self):
        """Test getting concatenated audio bytes."""
        buffer = AudioBuffer()
        chunk1 = b"\x00\x01\x02\x03"
        chunk2 = b"\x04\x05\x06\x07"

        buffer.add_chunk(chunk1)
        buffer.add_chunk(chunk2)

        audio_bytes = buffer.get_audio_bytes()
        assert audio_bytes == chunk1 + chunk2

    def test_get_audio_bytes_empty(self):
        """Test getting bytes from empty buffer."""
        buffer = AudioBuffer()
        assert buffer.get_audio_bytes() == b""

    def test_get_duration_seconds(self):
        """Test duration calculation."""
        buffer = AudioBuffer()
        # 16000 samples/sec * 1 channel * 2 bytes = 32000 bytes/sec
        # Add 1 second worth of data
        chunk = b"\x00\x01" * 16000  # 16000 samples = 1 second
        buffer.add_chunk(chunk)

        duration = buffer.get_duration_seconds()
        assert abs(duration - 1.0) < 0.01  # Within 10ms

    def test_get_duration_seconds_empty(self):
        """Test duration of empty buffer."""
        buffer = AudioBuffer()
        assert buffer.get_duration_seconds() == 0.0

    def test_max_duration_limiting(self):
        """Test that buffer respects max duration."""
        buffer = AudioBuffer(max_duration_seconds=2.0)
        # 1 second of audio
        one_second = b"\x00\x01" * 16000

        # Add 3 seconds of audio
        buffer.add_chunk(one_second)
        buffer.add_chunk(one_second)
        buffer.add_chunk(one_second)

        # Should only have ~2 seconds
        duration = buffer.get_duration_seconds()
        assert duration <= 2.1  # Allow small margin

    def test_clear(self):
        """Test clearing buffer."""
        buffer = AudioBuffer()
        buffer.add_chunk(b"\x00\x01" * 100)
        buffer.add_chunk(b"\x02\x03" * 100)

        buffer.clear()
        assert len(buffer.chunks) == 0
        assert buffer.get_duration_seconds() == 0.0
        assert buffer.get_audio_bytes() == b""

    def test_to_wav_bytes(self):
        """Test WAV conversion."""
        buffer = AudioBuffer()
        chunk = b"\x00\x01" * 1000  # 1000 samples
        buffer.add_chunk(chunk)

        wav_bytes = buffer.to_wav_bytes()
        assert len(wav_bytes) > len(chunk)  # WAV has header
        assert wav_bytes[:4] == b"RIFF"  # WAV signature
        assert wav_bytes[8:12] == b"WAVE"  # WAV format

    def test_to_wav_bytes_empty(self):
        """Test WAV conversion of empty buffer."""
        buffer = AudioBuffer()
        wav_bytes = buffer.to_wav_bytes()
        # Empty buffer returns empty bytes (no audio data to convert)
        assert wav_bytes == b""

    def test_save_wav(self, tmp_path: Path):
        """Test saving to WAV file."""
        buffer = AudioBuffer()
        chunk = b"\x00\x01" * 1000
        buffer.add_chunk(chunk)

        wav_file = tmp_path / "test.wav"
        buffer.save_wav(wav_file)

        assert wav_file.exists()
        assert wav_file.stat().st_size > len(chunk)

        # Verify WAV format
        with open(wav_file, "rb") as f:
            header = f.read(12)
            assert header[:4] == b"RIFF"
            assert header[8:12] == b"WAVE"


class TestAudioRelay:
    """Test AudioRelay class."""

    @pytest.mark.asyncio
    async def test_start_stream(self):
        """Test starting audio stream."""
        relay = AudioRelay()
        session_id = "test-session-1"

        buffer = relay.start_stream(session_id)
        assert buffer is not None
        assert session_id in relay.get_active_streams()

    @pytest.mark.asyncio
    async def test_start_stream_duplicate(self):
        """Test starting duplicate stream."""
        relay = AudioRelay()
        session_id = "test-session-1"

        buffer1 = relay.start_stream(session_id)
        buffer2 = relay.start_stream(session_id)

        # Should return same buffer
        assert buffer1 is buffer2

    @pytest.mark.asyncio
    async def test_stop_stream(self):
        """Test stopping audio stream."""
        relay = AudioRelay()
        session_id = "test-session-1"

        relay.start_stream(session_id)
        await relay.add_audio_chunk(session_id, b"\x00\x01" * 100)

        buffer = relay.stop_stream(session_id)
        assert buffer is not None
        assert session_id not in relay.get_active_streams()
        assert len(buffer.get_audio_bytes()) > 0

    @pytest.mark.asyncio
    async def test_stop_stream_nonexistent(self):
        """Test stopping non-existent stream."""
        relay = AudioRelay()
        buffer = relay.stop_stream("nonexistent")
        assert buffer is None

    @pytest.mark.asyncio
    async def test_add_audio_chunk(self):
        """Test adding audio chunk to stream."""
        relay = AudioRelay()
        session_id = "test-session-1"

        relay.start_stream(session_id)
        chunk = b"\x00\x01" * 100

        await relay.add_audio_chunk(session_id, chunk)

        buffer = relay.get_buffer(session_id)
        assert buffer is not None
        assert buffer.get_audio_bytes() == chunk

    @pytest.mark.asyncio
    async def test_add_audio_chunk_nonexistent(self):
        """Test adding chunk to non-existent stream."""
        relay = AudioRelay()
        # Should not raise exception
        await relay.add_audio_chunk("nonexistent", b"\x00\x01" * 100)

    @pytest.mark.asyncio
    async def test_add_audio_chunk_concurrent(self):
        """Test concurrent audio chunk additions."""
        relay = AudioRelay()
        session_id = "test-session-1"

        relay.start_stream(session_id)

        # Add multiple chunks concurrently
        chunks = [b"\x00\x01" * 100 for _ in range(10)]
        tasks = [relay.add_audio_chunk(session_id, chunk) for chunk in chunks]
        await asyncio.gather(*tasks)

        buffer = relay.get_buffer(session_id)
        assert buffer is not None
        # All chunks should be added
        assert len(buffer.chunks) == 10

    @pytest.mark.asyncio
    async def test_get_buffer(self):
        """Test getting active buffer."""
        relay = AudioRelay()
        session_id = "test-session-1"

        relay.start_stream(session_id)
        buffer = relay.get_buffer(session_id)

        assert buffer is not None
        assert buffer.sample_rate == 16000

    @pytest.mark.asyncio
    async def test_get_buffer_nonexistent(self):
        """Test getting non-existent buffer."""
        relay = AudioRelay()
        buffer = relay.get_buffer("nonexistent")
        assert buffer is None

    @pytest.mark.asyncio
    async def test_get_active_streams(self):
        """Test listing active streams."""
        relay = AudioRelay()

        assert len(relay.get_active_streams()) == 0

        relay.start_stream("session-1")
        relay.start_stream("session-2")

        streams = relay.get_active_streams()
        assert len(streams) == 2
        assert "session-1" in streams
        assert "session-2" in streams

        relay.stop_stream("session-1")
        streams = relay.get_active_streams()
        assert len(streams) == 1
        assert "session-2" in streams

    @pytest.mark.asyncio
    async def test_clear_stream(self):
        """Test clearing stream buffer."""
        relay = AudioRelay()
        session_id = "test-session-1"

        relay.start_stream(session_id)
        await relay.add_audio_chunk(session_id, b"\x00\x01" * 100)

        relay.clear_stream(session_id)

        buffer = relay.get_buffer(session_id)
        assert buffer is not None
        assert len(buffer.get_audio_bytes()) == 0
        # Stream should still be active
        assert session_id in relay.get_active_streams()

    @pytest.mark.asyncio
    async def test_clear_stream_nonexistent(self):
        """Test clearing non-existent stream."""
        relay = AudioRelay()
        # Should not raise exception
        relay.clear_stream("nonexistent")

    @pytest.mark.asyncio
    async def test_multi_session(self):
        """Test multiple concurrent sessions."""
        relay = AudioRelay()

        # Start multiple sessions
        relay.start_stream("session-1")
        relay.start_stream("session-2")
        relay.start_stream("session-3")

        # Add different data to each
        await relay.add_audio_chunk("session-1", b"\x01" * 100)
        await relay.add_audio_chunk("session-2", b"\x02" * 100)
        await relay.add_audio_chunk("session-3", b"\x03" * 100)

        # Verify each session has correct data
        buffer1 = relay.get_buffer("session-1")
        buffer2 = relay.get_buffer("session-2")
        buffer3 = relay.get_buffer("session-3")

        assert buffer1.get_audio_bytes() == b"\x01" * 100
        assert buffer2.get_audio_bytes() == b"\x02" * 100
        assert buffer3.get_audio_bytes() == b"\x03" * 100

        # Stop sessions independently
        relay.stop_stream("session-2")
        assert len(relay.get_active_streams()) == 2

        relay.stop_stream("session-1")
        relay.stop_stream("session-3")
        assert len(relay.get_active_streams()) == 0
