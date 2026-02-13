# -*- coding: utf-8 -*-
"""
Local skill loader for prompt augmentation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


DEFAULT_SKILL_PATHS = ["./skills"]
DEFAULT_SKILL_GLOBS = ["*.md", "*.txt", "*.rst", "*.yaml", "*.yml"]


def _normalize_paths(paths: List[str] | None) -> List[Path]:
    raw_paths = paths or DEFAULT_SKILL_PATHS
    return [Path(p).expanduser().resolve() for p in raw_paths if str(p).strip()]


def _collect_skill_files(paths: List[Path], include_globs: List[str]) -> List[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for base in paths:
        if not base.exists():
            continue
        if base.is_file():
            if base not in seen:
                files.append(base)
                seen.add(base)
            continue
        for pattern in include_globs:
            for p in base.rglob(pattern):
                if p.is_file() and p not in seen:
                    files.append(p)
                    seen.add(p)
    files.sort()
    return files


def _split_frontmatter(text: str) -> Tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, flags=re.DOTALL)
    if not match:
        return {}, text

    meta_raw, body = match.groups()
    if yaml is None:
        return {}, body
    try:
        parsed = yaml.safe_load(meta_raw)
    except Exception:
        return {}, body
    if not isinstance(parsed, dict):
        return {}, body
    return parsed, body


def _normalize_agent_selector(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        parts = re.split(r"[,\s;|]+", value)
    elif isinstance(value, (list, tuple, set)):
        parts = [str(v) for v in value]
    else:
        parts = [str(value)]
    return {part.strip().lower() for part in parts if part and part.strip()}


def _extract_priority(metadata: dict[str, Any]) -> int:
    raw = metadata.get("priority", 0)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _skill_applies_to_agent(metadata: dict[str, Any], agent_name: str) -> bool:
    if not agent_name:
        return True

    agent = agent_name.strip().lower()
    include = set()
    for key in ("apply_to", "agents", "agent", "include_agents"):
        include |= _normalize_agent_selector(metadata.get(key))

    exclude = set()
    for key in ("exclude_agents", "except_agents"):
        exclude |= _normalize_agent_selector(metadata.get(key))

    if agent in exclude or "*" in exclude:
        return False
    if include and agent not in include and "*" not in include and "all" not in include:
        return False
    return True


def _skill_title(metadata: dict[str, Any], file_path: Path) -> str:
    raw_title = metadata.get("title")
    if isinstance(raw_title, str) and raw_title.strip():
        return raw_title.strip()
    return file_path.name


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path.resolve())


def build_local_skill_context(api_config: object, agent_name: str = "") -> str:
    enabled = bool(getattr(api_config, "skill_enabled", True))
    if not enabled:
        return ""

    max_chars = int(getattr(api_config, "skill_max_context_chars", 4000) or 4000)
    max_files = int(getattr(api_config, "skill_max_files", 8) or 8)
    max_file_size_kb = int(getattr(api_config, "skill_max_file_size_kb", 256) or 256)
    if max_chars <= 0 or max_files <= 0:
        return ""

    include_globs = getattr(api_config, "skill_include_globs", None) or DEFAULT_SKILL_GLOBS
    paths = _normalize_paths(getattr(api_config, "skill_paths", None))
    files = _collect_skill_files(paths, include_globs)
    if not files:
        return ""

    candidates: list[tuple[int, str, Path, str]] = []
    agent = (agent_name or "").strip().lower()
    for file_path in files:
        try:
            if file_path.stat().st_size > max_file_size_kb * 1024:
                continue
            raw = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        if not raw.strip():
            continue

        metadata, content = _split_frontmatter(raw)
        if not _skill_applies_to_agent(metadata, agent):
            continue

        body = content.strip()
        if not body:
            continue

        candidates.append((
            _extract_priority(metadata),
            _skill_title(metadata, file_path),
            file_path,
            body,
        ))

    if not candidates:
        return ""

    candidates.sort(key=lambda item: (-item[0], str(item[2]).lower()))
    selected = candidates[:max_files]

    remaining = max_chars
    sections: list[str] = []
    for _, title, file_path, content in selected:
        if remaining <= 0:
            break

        header = f"[skill:{title}]"
        block = f"{header}\nsource: {_rel_path(file_path)}\n{content}"
        if len(block) > remaining:
            block = block[:remaining]
        if block:
            sections.append(block)
            remaining -= len(block)

    if not sections:
        return ""

    joined = "\n\n".join(sections)
    if agent_name:
        return f"Applicable local skills for agent '{agent_name}':\n{joined}"
    return joined
