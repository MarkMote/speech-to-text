import logging
import threading

import numpy as np
import sounddevice as sd

from stt.config import AudioConfig

log = logging.getLogger(__name__)

CHUNK_SIZE = 1024


class Recorder:
    def __init__(self, config: AudioConfig):
        self.config = config
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._recording = False
        self._stream = None

    def start(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True

        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype="float32",
            blocksize=CHUNK_SIZE,
            device=self.config.device_index,
            callback=self._callback,
        )
        self._stream.start()
        log.info("Recording started")

    def _callback(self, indata, frames, time_info, status):
        if status:
            log.warning("Audio status: %s", status)
        with self._lock:
            if self._recording:
                self._frames.append(indata.copy())

    def stop(self) -> np.ndarray | None:
        with self._lock:
            self._recording = False
            frames = list(self._frames)
            self._frames = []

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not frames:
            return None

        audio = np.concatenate(frames, axis=0).flatten()
        duration = len(audio) / self.config.sample_rate
        log.info("Recording stopped: %.1fs, max_amp=%.3f", duration, np.max(np.abs(audio)))
        return audio

    def cleanup(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
