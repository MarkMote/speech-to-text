import logging
from abc import ABC, abstractmethod

import numpy as np

from stt.config import ModelConfig

log = logging.getLogger(__name__)


class TranscriberBackend(ABC):
    @abstractmethod
    def load(self) -> None:
        ...

    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        ...

    @abstractmethod
    def unload(self) -> None:
        ...


class FasterWhisperBackend(TranscriberBackend):
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        log.info(
            "Loading faster-whisper model=%s device=%s compute=%s",
            self.config.name, self.config.device, self.config.compute_type,
        )
        self.model = WhisperModel(
            self.config.name,
            device=self.config.device,
            compute_type=self.config.compute_type,
        )
        log.info("Model loaded")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if self.model is None:
            raise RuntimeError("Model not loaded")

        segments, info = self.model.transcribe(
            audio,
            beam_size=5,
            vad_filter=True,
            language="en",
        )
        text = " ".join(s.text for s in segments).strip()
        log.info("Transcribed (%s, %.2f confidence): %s", info.language, info.language_probability, text)
        return text

    def unload(self) -> None:
        self.model = None
        log.info("Model unloaded")


def create_transcriber(config: ModelConfig) -> TranscriberBackend:
    if config.backend == "faster-whisper":
        return FasterWhisperBackend(config)
    raise ValueError(f"Unknown backend: {config.backend}")
