"""Strict adapter and render-artifact contract for future RF983 engines.

This module does not load a model or start inference. It defines the boundary
that a reviewed model adapter must satisfy before outputs can be accepted.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import json
import subprocess


@dataclass(frozen=True)
class RenderRequest:
    prompt: str
    negative_prompt: str = ""
    mode: str = "text"
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    duration_seconds: int = 5
    fps: int = 24
    seed: int | None = None


@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    model_id: str
    duration_seconds: float
    width: int
    height: int
    fps: float


class EngineAdapter(Protocol):
    """A concrete, reviewed adapter implements this method in a later release."""

    @property
    def model_id(self) -> str: ...

    def is_available(self) -> tuple[bool, str]: ...

    def render(self, request: RenderRequest, output_dir: Path) -> RenderResult: ...


class ArtifactValidationError(ValueError):
    pass


class RenderArtifactValidator:
    """Accept only non-empty MP4 files inside a configured private output root."""

    def __init__(self, output_root: Path, max_bytes: int = 2 * 1024 * 1024 * 1024):
        self.output_root = output_root.resolve()
        self.max_bytes = max_bytes

    def validate(self, candidate: Path) -> dict:
        try:
            path = candidate.resolve(strict=True)
            path.relative_to(self.output_root)
        except (OSError, ValueError):
            raise ArtifactValidationError("Output path is missing or outside the configured render directory.")
        if not path.is_file():
            raise ArtifactValidationError("Render output is not a regular file.")
        if path.suffix.lower() != ".mp4":
            raise ArtifactValidationError("Only MP4 render artifacts are accepted by this contract.")
        size = path.stat().st_size
        if size <= 0:
            raise ArtifactValidationError("Render output is empty.")
        if size > self.max_bytes:
            raise ArtifactValidationError("Render output exceeds the configured size limit.")
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=codec_type,width,height,r_frame_rate",
                 "-show_entries", "format=duration", "-of", "json", str(path)],
                check=True, capture_output=True, text=True, timeout=12,
            )
            metadata = json.loads(result.stdout)
            stream = (metadata.get("streams") or [])[0]
            duration = float((metadata.get("format") or {}).get("duration", 0))
            width, height = int(stream["width"]), int(stream["height"])
            if stream.get("codec_type") != "video" or duration <= 0 or width <= 0 or height <= 0:
                raise ValueError("Missing video stream metadata")
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ArtifactValidationError("ffprobe could not verify a playable video stream.") from exc
        rate = str(stream.get("r_frame_rate", "0/1")).split("/")
        try:
            fps = float(rate[0]) / float(rate[1])
        except (ValueError, ZeroDivisionError, IndexError):
            fps = 0.0
        return {
            "path": str(path), "bytes": size, "duration_seconds": duration,
            "width": width, "height": height, "fps": fps,
            "verified_by": "ffprobe",
        }
