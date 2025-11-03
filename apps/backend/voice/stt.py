"""
Speech-to-text using OpenAI Whisper.

Provides transcription from audio (WAV, PCM) to text with configurable models.
Optimized for Raspberry Pi 5 with quantization support.
"""

import asyncio
import logging
import tempfile
import time
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ModelSize(str, Enum):
    """Whisper model sizes."""

    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class WhisperSTT:
    """Speech-to-text using Whisper."""

    def __init__(
        self,
        model_size: ModelSize = ModelSize.SMALL,
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        """Initialize Whisper STT.

        Args:
            model_size: Size of Whisper model to use
            device: Device to run on ('cpu' or 'cuda')
            compute_type: Quantization type ('int8', 'float16', 'float32')
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model: Any = None
        self._model_load_lock = asyncio.Lock()

        logger.info(
            f"WhisperSTT initialized: model={model_size}, device={device}, compute_type={compute_type}"
        )

    async def load_model(self) -> None:
        """Load Whisper model (lazy loading)."""
        if self.model is not None:
            return

        async with self._model_load_lock:
            if self.model is not None:
                return

            logger.info(f"Loading Whisper model: {self.model_size}")
            start_time = time.perf_counter()

            try:
                # Import faster-whisper for quantized inference
                from faster_whisper import WhisperModel

                # Load model in executor to avoid blocking
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None,
                    lambda: WhisperModel(
                        self.model_size.value,
                        device=self.device,
                        compute_type=self.compute_type,
                    ),
                )

                load_time = time.perf_counter() - start_time
                logger.info(f"Whisper model loaded in {load_time:.2f}s")

            except ImportError as e:
                logger.error(f"faster-whisper not installed: {e}")
                raise RuntimeError(
                    "faster-whisper required for STT. Install with: pip install faster-whisper"
                ) from e

    async def transcribe_file(self, audio_path: Path) -> dict[str, str | float]:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)

        Returns:
            Dict with 'text' (transcript) and 'duration' (seconds)

        Raises:
            RuntimeError: If model loading fails
        """
        await self.load_model()

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing audio file: {audio_path}")
        start_time = time.perf_counter()

        try:
            # Run transcription in executor
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None, lambda: self.model.transcribe(str(audio_path), language="en")
            )

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            transcript = " ".join(text_parts).strip()
            duration = time.perf_counter() - start_time

            logger.info(f"Transcription complete in {duration:.2f}s: '{transcript[:50]}'")

            return {
                "text": transcript,
                "duration": duration,
                "language": info.language,
                "language_probability": info.language_probability,
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription error: {e}") from e

    async def transcribe_bytes(self, audio_bytes: bytes) -> dict[str, str | float]:
        """Transcribe audio from bytes to text.

        Args:
            audio_bytes: Audio data (WAV format with header)

        Returns:
            Dict with 'text' (transcript) and 'duration' (seconds)

        Raises:
            RuntimeError: If model loading fails
        """
        # Write to temp file for faster-whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(audio_bytes)

        try:
            result = await self.transcribe_file(tmp_path)
            return result
        finally:
            # Cleanup temp file
            try:
                tmp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp_path}: {e}")

    async def transcribe_pcm(
        self,
        pcm_data: bytes,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
    ) -> dict[str, str | float]:
        """Transcribe raw PCM audio to text.

        Args:
            pcm_data: Raw PCM audio data
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            sample_width: Sample width in bytes

        Returns:
            Dict with 'text' (transcript) and 'duration' (seconds)

        Raises:
            RuntimeError: If model loading fails
        """
        # Convert PCM to WAV format
        import wave
        from io import BytesIO

        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)

        wav_bytes = wav_buffer.getvalue()
        return await self.transcribe_bytes(wav_bytes)
