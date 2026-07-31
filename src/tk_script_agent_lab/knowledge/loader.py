from pathlib import Path

import yaml
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.knowledge.models import CreativeKnowledgePack

_REPO_ROOT = Path(__file__).resolve().parents[3]
_KNOWLEDGE_PACKS = {
    "tiktok_car_cleaning_v1": _REPO_ROOT
    / "knowledge"
    / "creative"
    / "tiktok_car_cleaning_v1.yaml",
}


class KnowledgePackError(ValueError):
    code = "KNOWLEDGE_PACK_INVALID"


class KnowledgePackNotFound(KnowledgePackError):
    code = "KNOWLEDGE_PACK_NOT_FOUND"


def load_creative_knowledge_pack(pack_id: str) -> CreativeKnowledgePack:
    if _looks_like_path_or_url(pack_id):
        raise KnowledgePackNotFound("unknown creative knowledge pack")
    pack_path = _KNOWLEDGE_PACKS.get(pack_id)
    if pack_path is None or not pack_path.exists():
        raise KnowledgePackNotFound("unknown creative knowledge pack")
    if not _is_relative_to(pack_path.resolve(), (_REPO_ROOT / "knowledge").resolve()):
        raise KnowledgePackNotFound("knowledge pack path is outside the knowledge directory")
    try:
        with pack_path.open(encoding="utf-8") as file:
            payload = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise KnowledgePackError("creative knowledge pack YAML is invalid") from exc
    if not isinstance(payload, dict):
        raise KnowledgePackError("creative knowledge pack must contain a mapping")
    try:
        pack = CreativeKnowledgePack.model_validate(payload)
    except PydanticValidationError as exc:
        raise KnowledgePackError("creative knowledge pack schema is invalid") from exc
    if pack.pack_id != pack_id:
        raise KnowledgePackError("creative knowledge pack id does not match requested pack")
    return pack


def _looks_like_path_or_url(pack_id: str) -> bool:
    return (
        not pack_id.strip()
        or "/" in pack_id
        or "\\" in pack_id
        or ".." in pack_id
        or ":" in pack_id
        or pack_id.startswith(("http://", "https://"))
        or Path(pack_id).is_absolute()
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
