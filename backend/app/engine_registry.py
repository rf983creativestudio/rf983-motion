"""Provider-neutral cloud engine registry.

This module advertises connection types only. It never calls providers,
stores credentials, or claims that an engine is usable.
"""
from __future__ import annotations

ENGINE_CATALOG = [
    {
        "id": "replicate",
        "name": "Replicate",
        "kind": "hosted-inference",
        "connection": "provider-api",
        "credential_env": "RF983_REPLICATE_API_TOKEN",
        "billing": "usage-based; provider pricing applies",
        "data_handling": "Prompts and any submitted assets are sent to the provider",
        "status": "not_configured",
        "enabled": False,
        "verified": False,
        "generation_supported": False,
        "notes": "Candidate connector only. No API requests are made by this release.",
    },
    {
        "id": "fal",
        "name": "fal.ai",
        "kind": "hosted-inference",
        "connection": "provider-api",
        "credential_env": "RF983_FAL_API_KEY",
        "billing": "usage-based; provider pricing applies",
        "data_handling": "Prompts and any submitted assets are sent to the provider",
        "status": "not_configured",
        "enabled": False,
        "verified": False,
        "generation_supported": False,
        "notes": "Candidate connector only. No API requests are made by this release.",
    },
    {
        "id": "runpod",
        "name": "RunPod",
        "kind": "cloud-gpu-infrastructure",
        "connection": "managed-endpoint",
        "credential_env": "RF983_RUNPOD_API_KEY",
        "billing": "GPU and storage charges may apply",
        "data_handling": "Workloads and assets are sent to configured infrastructure",
        "status": "not_configured",
        "enabled": False,
        "verified": False,
        "generation_supported": False,
        "notes": "Infrastructure connector candidate; requires a compatible deployed model worker.",
    },
    {
        "id": "custom-https",
        "name": "Custom HTTPS engine",
        "kind": "self-managed-inference",
        "connection": "https-api",
        "credential_env": "RF983_CUSTOM_ENGINE_TOKEN",
        "billing": "depends on the endpoint operator",
        "data_handling": "Prompts and assets are sent to the configured endpoint",
        "status": "not_configured",
        "enabled": False,
        "verified": False,
        "generation_supported": False,
        "notes": "For a compatible private endpoint implementing the RF983 adapter contract.",
    },
]

def list_engines() -> list[dict]:
    """Return a copy so API callers cannot mutate the process catalog."""
    return [dict(item) for item in ENGINE_CATALOG]

def get_engine(engine_id: str) -> dict | None:
    for item in ENGINE_CATALOG:
        if item["id"] == engine_id:
            return dict(item)
    return None
