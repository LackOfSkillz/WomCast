"""
Tests for server-side audio capture module.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from voice.server_audio import AudioBuffer, ServerAudioCapture, get_server_audio


class TestAudioBuffer:
    """Test AudioBuffer class."""

    def test_init(self):
        """Test buffer initialization."""
        buffer = AudioBuffer(max_duration_seconds=10.0)
        assert buffer.max_duration == 10.0
        assert buffer.sample_rate == 16000
        assert buffer.channels == 1
        assert buffer.sample_width == 2
        assert len(buffer.chunks) == 0

    def test_add_chunk(self):
        """Test adding audio chunks."""
        buffer = AudioBuffer()
        chunk1 = b"\x00\x01" * 100
        chunk2 = b"\x02\x03" * 100

        buffer.add_chunk(chunk1)
        assert len(buffer.chunks) == 1
        assert buffer.chunks[0] == chunk1

        buffer.add_chunk(chunk2)
        assert len(buffer.chunks) == 2

    def test_add_chunk_max_duration(self):
        """Test buffer limits based on max_duration."""
        buffer = AudioBuffer(max_duration_seconds=0.001)  # 1ms = tiny buffer
        buffer.sample_rate = 16000

        # Each chunk is 200 bytes = 100 samples = 6.25ms @ 16kHz mono
        chunk = b"\x00\x01" * 100

        # Add chunks until we exceed max duration
        for _ in range(10):
            buffer.add_chunk(chunk)

        # Buffer should have limited chunks (oldest removed)
        total_bytes = sum(len(c) for c in buffer.chunks)
        max_bytes = int(buffer.sample_rate * buffer.channels * buffer.sample_width * 0.001)
        assert total_bytes <= max_bytes * 1.5  # Allow some overflow

    def test_get_audio_bytes(self):
        """Test getting concatenated audio."""
        buffer = AudioBuffer()
        chunk1 = b"\x00\x01"
        chunk2 = b"\x02\x03"

        buffer.add_chunk(chunk1)
        buffer.add_chunk(chunk2)

        audio = buffer.get_audio_bytes()
        assert audio == b"\x00\x01\x02\x03"

    def test_get_duration_seconds(self):
        """Test duration calculation."""
        buffer = AudioBuffer()
        buffer.sample_rate = 16000
        buffer.channels = 1
        buffer.sample_width = 2

        # Add 16000 samples (1 second @ 16kHz)
        chunk = b"\x00\x01" * 16000  # 32000 bytes = 16000 samples
        buffer.add_chunk(chunk)

        duration = buffer.get_duration_seconds()
        assert abs(duration - 1.0) < 0.01  # Within 10ms

    def test_clear(self):
        """Test buffer clearing."""
        buffer = AudioBuffer()
        buffer.add_chunk(b"\x00\x01")
        buffer.add_chunk(b"\x02\x03")

        buffer.clear()
        assert len(buffer.chunks) == 0
        assert buffer.get_audio_bytes() == b""

    def test_to_wav_bytes(self):
        """Test WAV conversion."""
        buffer = AudioBuffer()
        chunk = b"\x00\x01" * 100
        buffer.add_chunk(chunk)

        wav_bytes = buffer.to_wav_bytes()
        assert len(wav_bytes) > 200  # WAV header + data
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"

    def test_to_wav_bytes_empty(self):
        """Test WAV conversion with empty buffer."""
        buffer = AudioBuffer()
        wav_bytes = buffer.to_wav_bytes()
        assert wav_bytes == b""

    def test_save_wav(self, tmp_path: Path):
        """Test saving buffer to WAV file."""
        buffer = AudioBuffer()
        chunk = b"\x00\x01" * 1000
        buffer.add_chunk(chunk)

        output_file = tmp_path / "test.wav"
        buffer.save_wav(output_file)

        assert output_file.exists()
        assert output_file.stat().st_size > 2000  # Header + data

    def test_save_wav_empty(self, tmp_path: Path):
        """Test saving empty buffer (should not create file)."""
        buffer = AudioBuffer()
        output_file = tmp_path / "test.wav"
        buffer.save_wav(output_file)

        assert not output_file.exists()


class TestServerAudioCapture:
    """Test ServerAudioCapture class."""

    def test_init(self):
        """Test initialization."""
        capture = ServerAudioCapture(
            sample_rate=44100, channels=2, chunk_size=2048, device_index=1
        )
        assert capture.sample_rate == 44100
        assert capture.channels == 2
        assert capture.chunk_size == 2048
        assert capture.device_index == 1
        assert capture._pyaudio is None
        assert not capture._is_recording

    def test_is_available_success(self):
        """Test availability check when PyAudio available."""
        with patch("builtins.__import__") as mock_import:
            mock_pa = Mock()
            mock_pa.get_device_count.return_value = 5
            mock_pa.get_default_input_device_info.return_value = {"name": "Default"}

            def import_side_effect(name, *args, **kwargs):
                if name == "pyaudio":
                    mock_pyaudio = Mock()
                    mock_pyaudio.PyAudio.return_value = mock_pa
                    return mock_pyaudio
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            capture = ServerAudioCapture()
            assert capture.is_available()

    def test_is_available_no_devices(self):
        """Test availability when no input devices."""
        with patch("builtins.__import__") as mock_import:
            mock_pa = Mock()
            mock_pa.get_device_count.return_value = 0
            mock_pa.get_default_input_device_info.side_effect = Exception("No device")

            def import_side_effect(name, *args, **kwargs):
                if name == "pyaudio":
                    mock_pyaudio = Mock()
                    mock_pyaudio.PyAudio.return_value = mock_pa
                    return mock_pyaudio
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            capture = ServerAudioCapture()
            assert not capture.is_available()

    def test_is_available_no_pyaudio(self):
        """Test availability when PyAudio not installed."""
        with patch("builtins.__import__") as mock_import:

            def import_side_effect(name, *args, **kwargs):
                if name == "pyaudio":
                    raise ImportError("No module named pyaudio")
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            capture = ServerAudioCapture()
            assert not capture.is_available()

    def test_get_devices(self):
        """Test getting device list."""
        with patch("builtins.__import__") as mock_import:
            mock_pa = Mock()
            mock_pa.get_device_count.return_value = 2
            mock_pa.get_device_info_by_index.side_effect = [
                {
                    "name": "Mic 1",
                    "maxInputChannels": 1,
                    "defaultSampleRate": 48000,
                },
                {
                    "name": "Mic 2",
                    "maxInputChannels": 2,
                    "defaultSampleRate": 44100,
                },
            ]

            def import_side_effect(name, *args, **kwargs):
                if name == "pyaudio":
                    mock_pyaudio = Mock()
                    mock_pyaudio.PyAudio.return_value = mock_pa
                    return mock_pyaudio
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            capture = ServerAudioCapture()
            devices = capture.get_devices()

            assert len(devices) == 2
            assert devices[0]["name"] == "Mic 1"
            assert devices[0]["channels"] == 1
            assert devices[1]["name"] == "Mic 2"
            assert devices[1]["sample_rate"] == 44100

    async def test_start_recording(self):
        """Test starting recording."""
        with patch("builtins.__import__") as mock_import:
            mock_pa = Mock()
            mock_stream = Mock()
            mock_pa.open.return_value = mock_stream

            def import_side_effect(name, *args, **kwargs):
                if name == "pyaudio":
                    mock_pyaudio = Mock()
                    mock_pyaudio.PyAudio.return_value = mock_pa
                    mock_pyaudio.paInt16 = 8
                    return mock_pyaudio
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            capture = ServerAudioCapture()
            await capture.start_recording()

            assert capture._is_recording
            assert capture._stream is not None
            mock_pa.open.assert_called_once()

    async def test_start_recording_already_recording(self):
        """Test starting when already recording."""
        with patch("builtins.__import__") as mock_import:
            mock_pa = Mock()
            mock_stream = Mock()
            mock_pa.open.return_value = mock_stream

            def import_side_effect(name, *args, **kwargs):
                if name == "pyaudio":
                    mock_pyaudio = Mock()
                    mock_pyaudio.PyAudio.return_value = mock_pa
                    mock_pyaudio.paInt16 = 8
                    return mock_pyaudio
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            capture = ServerAudioCapture()
            await capture.start_recording()

            with pytest.raises(RuntimeError, match="Already recording"):
                await capture.start_recording()

    async def test_stop_recording(self):
        """Test stopping recording."""
        with patch("builtins.__import__") as mock_import:
            mock_pa = Mock()
            mock_stream = Mock()
            mock_stream.read.return_value = b"\x00\x01" * 100
            mock_pa.open.return_value = mock_stream

            def import_side_effect(name, *args, **kwargs):
                if name == "pyaudio":
                    mock_pyaudio = Mock()
                    mock_pyaudio.PyAudio.return_value = mock_pa
                    mock_pyaudio.paInt16 = 8
                    return mock_pyaudio
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            capture = ServerAudioCapture()
            await capture.start_recording()

            # Simulate some recording
            capture._audio_chunks = [b"\x00\x01" * 100]

            # Stop recording
            audio_data = await capture.stop_recording()

            assert not capture._is_recording
            assert len(audio_data) == 200
            mock_stream.stop_stream.assert_called_once()
            mock_stream.close.assert_called_once()

    async def test_stop_recording_not_recording(self):
        """Test stopping when not recording."""
        capture = ServerAudioCapture()

        with pytest.raises(RuntimeError, match="Not recording"):
            await capture.stop_recording()

    def test_to_wav_bytes(self):
        """Test WAV conversion."""
        capture = ServerAudioCapture()
        audio_data = b"\x00\x01" * 1000

        wav_bytes = capture.to_wav_bytes(audio_data)
        assert len(wav_bytes) > 2000
        assert wav_bytes[:4] == b"RIFF"

    def test_save_wav(self, tmp_path: Path):
        """Test saving WAV file."""
        capture = ServerAudioCapture()
        audio_data = b"\x00\x01" * 1000

        output_file = tmp_path / "output.wav"
        capture.save_wav(audio_data, output_file)

        assert output_file.exists()
        assert output_file.stat().st_size > 2000

    def test_cleanup(self):
        """Test cleanup."""
        with patch("builtins.__import__") as mock_import:
            mock_pa = Mock()
            mock_stream = Mock()
            mock_stream.is_active.return_value = False
            mock_pa.open.return_value = mock_stream

            def import_side_effect(name, *args, **kwargs):
                if name == "pyaudio":
                    mock_pyaudio = Mock()
                    mock_pyaudio.PyAudio.return_value = mock_pa
                    return mock_pyaudio
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            capture = ServerAudioCapture()
            capture._pyaudio = mock_pa
            capture._stream = mock_stream

            capture.cleanup()

            mock_stream.close.assert_called_once()
            mock_pa.terminate.assert_called_once()
            assert capture._stream is None
            assert capture._pyaudio is None


def test_get_server_audio_singleton():
    """Test global singleton."""
    audio1 = get_server_audio()
    audio2 = get_server_audio()
    assert audio1 is audio2
