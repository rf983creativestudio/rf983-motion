"""Provider-neutral contract for future video inference adapters.

Implementations must be isolated in the worker process. Importing this module never
loads model weights or heavyweight ML frameworks.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EngineCapabilities:
    model_id: str
    tasks: tuple[str, ...]
    resolutions: tuple[str, ...]
    aspect_ratios: tuple[str, ...]
    fps: tuple[int, ...]
    supports_seed: bool = True
    supports_audio: bool = False


@dataclass
class GenerationInput:
    prompt: str
    negative_prompt: str = ""
    task: str = "text-to-video"
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    duration_seconds: int = 5
    fps: int = 24
    seed: int | None = None
    reference_image_path: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationOutput:
    output_path: str
    mime_type: str = "video/mp4"
    metadata: dict[str, Any] = field(default_factory=dict)


class VideoEngine(ABC):
    """Every real adapter must pass readiness checks before accepting work."""

    @abstractmethod
    def capabilities(self) -> EngineCapabilities:
        raise NotImplementedError

    @abstractmethod
    def readiness(self) -> tuple[bool, str]:
        """Return ready only after weights, dependencies and device checks succeed."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: GenerationInput, output_dir: str) -> GenerationOutput:
        """Generate one result; raise a structured exception on any failure."""
        raise NotImplementedError
