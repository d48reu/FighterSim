"""Deterministic fighter portrait assignment helpers."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from models.models import Fighter

ROOT = Path(__file__).resolve().parent.parent
PORTRAIT_ROOT = ROOT / "frontend" / "static" / "assets" / "portraits"
MANIFEST_PATH = PORTRAIT_ROOT / "manifest.json"

_REGION_BUCKETS = {
    "American": "global",
    "Canadian": "global",
    "Mexican": "global",
    "Brazilian": "global",
    "Argentinian": "global",
    "Colombian": "global",
    "Peruvian": "global",
    "Chilean": "global",
    "British": "global",
    "Irish": "global",
    "French": "global",
    "German": "global",
    "Spanish": "global",
    "Italian": "global",
    "Dutch": "global",
    "Polish": "global",
    "Croatian": "global",
    "Serbian": "global",
    "Russian": "global",
    "Dagestani": "global",
    "Georgian": "global",
    "Kazakh": "global",
    "Uzbek": "global",
    "Kyrgyz": "global",
    "Japanese": "global",
    "Korean": "global",
    "Chinese": "global",
    "Thai": "global",
    "Filipino": "global",
    "Australian": "global",
    "New Zealander": "global",
    "Nigerian": "global",
    "Cameroonian": "global",
    "South African": "global",
    "Moroccan": "global",
}


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"version": 1, "buckets": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def available_portrait_keys() -> dict[str, list[str]]:
    manifest = load_manifest()
    buckets = manifest.get("buckets", {})
    return {bucket: list(paths) for bucket, paths in buckets.items()}


def age_band_for_fighter(fighter: Fighter) -> str:
    if fighter.age <= 24:
        return "prospect"
    if fighter.age >= 32:
        return "veteran"
    return "prime"


def style_bucket(style: str) -> str:
    value = style.value if hasattr(style, "value") else str(style)
    normalized = value.strip().lower()
    if normalized == "wrestler":
        return "wrestler"
    if normalized == "grappler":
        return "grappler"
    return "striker"


def region_bucket_for_nationality(nationality: str | None) -> str:
    if not nationality:
        return "global"
    return _REGION_BUCKETS.get(nationality, "global")


def portrait_bucket_for_fighter(fighter: Fighter) -> str:
    return "/".join(
        [
            age_band_for_fighter(fighter),
            style_bucket(fighter.style),
            region_bucket_for_nationality(getattr(fighter, "nationality", None)),
        ]
    )


def assign_portrait_key(fighter: Fighter) -> str:
    buckets = available_portrait_keys()
    bucket = portrait_bucket_for_fighter(fighter)
    candidates = buckets.get(bucket)
    if not candidates:
        fallback_bucket = (
            f"{age_band_for_fighter(fighter)}/{style_bucket(fighter.style)}/global"
        )
        candidates = buckets.get(fallback_bucket)
    if not candidates:
        candidates = buckets.get("prime/striker/global") or []
    if not candidates:
        raise ValueError("No portrait assets available in manifest")

    seed_material = "|".join(
        [
            fighter.name or "unknown",
            str(getattr(fighter, "age", "")),
            str(getattr(fighter, "nationality", "")),
            str(getattr(fighter, "style", "")),
            str(getattr(fighter, "archetype", "")),
        ]
    )
    digest = hashlib.sha256(seed_material.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(candidates)
    return candidates[idx]
