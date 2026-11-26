import pytest
from pathlib import Path
from worker.engine_contract import ArtifactValidationError, RenderArtifactValidator


def test_validator_rejects_path_outside_output_root(tmp_path):
    root = tmp_path / "renders"
    root.mkdir()
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"not a video")
    validator = RenderArtifactValidator(root)
    with pytest.raises(ArtifactValidationError, match="outside"):
        validator.validate(outside)


def test_validator_rejects_empty_mp4_before_ffprobe(tmp_path):
    root = tmp_path / "renders"
    root.mkdir()
    empty = root / "empty.mp4"
    empty.touch()
    validator = RenderArtifactValidator(root)
    with pytest.raises(ArtifactValidationError, match="empty"):
        validator.validate(empty)


def test_validator_rejects_wrong_extension(tmp_path):
    root = tmp_path / "renders"
    root.mkdir()
    artifact = root / "render.mov"
    artifact.write_bytes(b"fake")
    validator = RenderArtifactValidator(root)
    with pytest.raises(ArtifactValidationError, match="MP4"):
        validator.validate(artifact)


def test_validator_rejects_oversized_file(tmp_path):
    root = tmp_path / "renders"
    root.mkdir()
    artifact = root / "large.mp4"
    artifact.write_bytes(b"12345")
    validator = RenderArtifactValidator(root, max_bytes=4)
    with pytest.raises(ArtifactValidationError, match="size limit"):
        validator.validate(artifact)
