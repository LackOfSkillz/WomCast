"""
Tests for Whisper STT module.
"""

import asyncio
import wave
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voice.stt import ModelSize, WhisperSTT


class TestWhisperSTT:
    """Test WhisperSTT class."""

    def test_init(self):
        """Test STT initialization."""
        stt = WhisperSTT()
        assert stt.model_size == ModelSize.SMALL
        assert stt.device == "cpu"
        assert stt.compute_type == "int8"
        assert stt.model is None

    def test_init_custom(self):
        """Test STT with custom parameters."""
        stt = WhisperSTT(model_size=ModelSize.TINY, device="cuda", compute_type="float16")
        assert stt.model_size == ModelSize.TINY
        assert stt.device == "cuda"
        assert stt.compute_type == "float16"

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_load_model(self, mock_model_class):
        """Test model loading."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        stt = WhisperSTT(model_size=ModelSize.TINY)
        await stt.load_model()

        assert stt.model is not None
        mock_model_class.assert_called_once_with(
            "tiny", device="cpu", compute_type="int8"
        )

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_load_model_once(self, mock_model_class):
        """Test model loads only once."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        stt = WhisperSTT(model_size=ModelSize.TINY)

        # Load twice
        await stt.load_model()
        await stt.load_model()

        # Should only call once
        mock_model_class.assert_called_once()

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_load_model_concurrent(self, mock_model_class):
        """Test concurrent model loading."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        stt = WhisperSTT(model_size=ModelSize.TINY)

        # Load concurrently
        await asyncio.gather(stt.load_model(), stt.load_model(), stt.load_model())

        # Should only call once
        mock_model_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_model_import_error(self):
        """Test model loading with import error."""
        with patch("builtins.__import__", side_effect=ImportError("Not installed")):
            stt = WhisperSTT()

            with pytest.raises(RuntimeError, match="faster-whisper required"):
                await stt.load_model()

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_transcribe_file(self, mock_model_class, tmp_path: Path):
        """Test file transcription."""
        # Create mock model
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Test transcript"
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_model_class.return_value = mock_model

        # Create test audio file
        audio_file = tmp_path / "test.wav"
        with wave.open(str(audio_file), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x01" * 1000)

        stt = WhisperSTT(model_size=ModelSize.TINY)
        result = await stt.transcribe_file(audio_file)

        assert result["text"] == "Test transcript"
        assert result["duration"] > 0
        assert result["language"] == "en"
        assert result["language_probability"] == 0.95

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_transcribe_file_not_found(self, mock_model_class):
        """Test transcription with non-existent file."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        stt = WhisperSTT(model_size=ModelSize.TINY)
        await stt.load_model()

        with pytest.raises(FileNotFoundError):
            await stt.transcribe_file(Path("/nonexistent/file.wav"))

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_transcribe_file_multi_segment(self, mock_model_class, tmp_path: Path):
        """Test transcription with multiple segments."""
        mock_model = MagicMock()
        mock_seg1 = MagicMock()
        mock_seg1.text = " Hello "
        mock_seg2 = MagicMock()
        mock_seg2.text = " world"
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99
        mock_model.transcribe.return_value = ([mock_seg1, mock_seg2], mock_info)
        mock_model_class.return_value = mock_model

        audio_file = tmp_path / "test.wav"
        with wave.open(str(audio_file), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x01" * 1000)

        stt = WhisperSTT(model_size=ModelSize.TINY)
        result = await stt.transcribe_file(audio_file)

        assert result["text"] == "Hello   world"

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_transcribe_bytes(self, mock_model_class):
        """Test transcription from bytes."""
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Test"
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.9
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_model_class.return_value = mock_model

        # Create WAV bytes
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x01" * 1000)

        stt = WhisperSTT(model_size=ModelSize.TINY)
        result = await stt.transcribe_bytes(wav_buffer.getvalue())

        assert result["text"] == "Test"
        assert result["duration"] > 0

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_transcribe_pcm(self, mock_model_class):
        """Test transcription from PCM data."""
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "PCM test"
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.85
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_model_class.return_value = mock_model

        pcm_data = b"\x00\x01" * 16000  # 1 second of audio

        stt = WhisperSTT(model_size=ModelSize.TINY)
        result = await stt.transcribe_pcm(
            pcm_data, sample_rate=16000, channels=1, sample_width=2
        )

        assert result["text"] == "PCM test"
        assert result["duration"] > 0

    @pytest.mark.asyncio
    @patch("faster_whisper.WhisperModel")
    async def test_transcribe_error(self, mock_model_class, tmp_path: Path):
        """Test transcription error handling."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("Transcription failed")
        mock_model_class.return_value = mock_model

        audio_file = tmp_path / "test.wav"
        with wave.open(str(audio_file), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x01" * 1000)

        stt = WhisperSTT(model_size=ModelSize.TINY)

        with pytest.raises(RuntimeError, match="Transcription error"):
            await stt.transcribe_file(audio_file)
