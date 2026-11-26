from pathlib import Path
import pytest

from worker.wan22_engine import build_command, EngineNotReady, run_generation


def test_build_command_uses_official_ti2v_5b_cli(tmp_path):
    repo = tmp_path / "Wan2.2"
    checkpoint = tmp_path / "weights"
    output = tmp_path / "render.mp4"
    command = build_command("python", repo, checkpoint, "A cinematic aerial shot over a coastline", output, seed=42)
    assert command[:2] == ["python", str(repo / "generate.py")]
    assert "--task" in command and command[command.index("--task") + 1] == "ti2v-5B"
    assert "--offload_model" in command
    assert "--t5_cpu" in command
    assert command[command.index("--save_file") + 1] == str(output)
    assert command[command.index("--base_seed") + 1] == "42"


def test_build_command_rejects_invalid_prompt_and_size(tmp_path):
    with pytest.raises(ValueError, match="Prompt"):
        build_command("python", tmp_path, tmp_path, "   ", tmp_path / "x.mp4")
    with pytest.raises(ValueError, match="sizes"):
        build_command("python", tmp_path, tmp_path, "A cinematic scene", tmp_path / "x.mp4", size="1920*1080")


def test_build_command_rejects_out_of_range_seed(tmp_path):
    with pytest.raises(ValueError, match="Seed"):
        build_command("python", tmp_path, tmp_path, "A cinematic scene", tmp_path / "x.mp4", seed=-1)


def test_run_generation_fails_closed_when_gpu_or_weights_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("worker.wan22_engine.inspect_installation", lambda *args: {
        "ready": False, "reasons": ["NVIDIA GPU not detected."]
    })
    with pytest.raises(EngineNotReady, match="not ready"):
        run_generation("A cinematic scene", wan_repo=tmp_path, checkpoint=tmp_path)


def test_output_path_cannot_escape_private_render_root(monkeypatch, tmp_path):
    monkeypatch.setattr("worker.wan22_engine.inspect_installation", lambda *args: {"ready": True, "reasons": []})
    monkeypatch.setattr("worker.wan22_engine.DEFAULT_OUTPUT_ROOT", tmp_path / "renders")
    with pytest.raises(ValueError, match="inside"):
        run_generation("A cinematic scene", output=tmp_path / "outside.mp4",
                       wan_repo=tmp_path, checkpoint=tmp_path, dry_run=True)
