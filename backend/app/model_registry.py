"""Explicit model catalog. A catalog entry is not an installed or runnable model."""
from copy import deepcopy

_MODELS = [
    {
        "id": "wan-ti2v-5b",
        "name": "Wan 2.2 TI2V 5B",
        "tasks": ["text-to-video", "image-to-video"],
        "target": "720p",
        "fps": 24,
        "audio": False,
        "status": "candidate",
        "adapter_installed": False,
        "weights_present": False,
        "license_review_required": True,
        "notes": "Practical first hardware-validation candidate; requires compatible CUDA GPU, exact weights and dependencies.",
        "source": "https://github.com/Wan-Video/Wan2.2",
    },
    {
        "id": "wan-i2v-14b",
        "name": "Wan 2.2 I2V 14B",
        "tasks": ["image-to-video"],
        "target": "high-resolution",
        "fps": 24,
        "audio": False,
        "status": "candidate",
        "adapter_installed": False,
        "weights_present": False,
        "license_review_required": True,
        "notes": "Higher resource demand; do not schedule until hardware and checkpoint are verified.",
        "source": "https://github.com/Wan-Video/Wan2.2",
    },
    {
        "id": "ltx-2.5",
        "name": "LTX-2.5",
        "tasks": ["text-to-video", "image-to-video", "audio-video"],
        "target": "pipeline-dependent",
        "fps": None,
        "audio": True,
        "status": "candidate",
        "adapter_installed": False,
        "weights_present": False,
        "license_review_required": True,
        "notes": "Advanced audio/video candidate; checkpoint license, VRAM and runtime must be checked separately.",
        "source": "https://github.com/Lightricks/LTX-2",
    },
]


def list_models():
    """Return safe copies so callers cannot mutate the catalog."""
    return deepcopy(_MODELS)


def get_model(model_id: str):
    for model in _MODELS:
        if model["id"] == model_id:
            return deepcopy(model)
    return None
