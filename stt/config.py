import os
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class HotkeyConfig:
    device_name: str
    key_code: str


@dataclass
class ModelConfig:
    backend: str = "faster-whisper"
    name: str = "small.en"
    device: str = "cuda"
    compute_type: str = "int8_float16"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    device_index: Optional[int] = None


@dataclass
class IndicatorConfig:
    enabled: bool = True
    position: str = "top-right"
    size: int = 16
    colors: dict = field(default_factory=lambda: {
        "recording": "#ff4444",
        "transcribing": "#ffaa00",
    })


@dataclass
class OutputConfig:
    method: str = "paste"
    restore_clipboard: bool = True


@dataclass
class SttConfig:
    hotkeys: list[HotkeyConfig] = field(default_factory=list)
    model: ModelConfig = field(default_factory=ModelConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    indicator: IndicatorConfig = field(default_factory=IndicatorConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def load_config(path: str) -> SttConfig:
    if not os.path.exists(path):
        return SttConfig()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    config = SttConfig()

    if "hotkeys" in raw:
        config.hotkeys = [
            HotkeyConfig(device_name=h["device_name"], key_code=h["key_code"])
            for h in raw["hotkeys"]
        ]

    if "model" in raw:
        m = raw["model"]
        config.model = ModelConfig(
            backend=m.get("backend", "faster-whisper"),
            name=m.get("name", "small.en"),
            device=m.get("device", "cuda"),
            compute_type=m.get("compute_type", "int8_float16"),
        )

    if "audio" in raw:
        a = raw["audio"]
        config.audio = AudioConfig(
            sample_rate=a.get("sample_rate", 16000),
            channels=a.get("channels", 1),
            device_index=a.get("device_index"),
        )

    if "indicator" in raw:
        i = raw["indicator"]
        config.indicator = IndicatorConfig(
            enabled=i.get("enabled", True),
            position=i.get("position", "top-right"),
            size=i.get("size", 16),
            colors=i.get("colors", config.indicator.colors),
        )

    if "output" in raw:
        o = raw["output"]
        config.output = OutputConfig(
            method=o.get("method", "paste"),
            restore_clipboard=o.get("restore_clipboard", True),
        )

    return config
