from app.model_registry import get_model, list_models
from app.worker_preflight import inspect_worker


def test_catalog_models_are_candidates_not_ready():
    models = list_models()
    assert {m["id"] for m in models} == {"wan-ti2v-5b", "wan-i2v-14b", "ltx-2.5"}
    assert all(m["status"] == "candidate" for m in models)
    assert all(m["adapter_installed"] is False for m in models)
    assert all(m["weights_present"] is False for m in models)


def test_model_lookup_returns_independent_copy():
    model = get_model("wan-ti2v-5b")
    assert model is not None
    model["status"] = "verified"
    assert get_model("wan-ti2v-5b")["status"] == "candidate"


def test_unknown_model_is_none():
    assert get_model("made-up-model") is None


def test_preflight_never_claims_generation_ready():
    report = inspect_worker()
    assert report["generation_ready"] is False
    assert report["gpu"]["detected"] in (True, False)
