# -*- coding: utf-8 -*-
"""
Lightweight local RAG utilities.

Design goals:
- No third-party retrieval dependencies.
- Works with local project files (docs/prompts/readme).
- Cached in-memory index with cheap staleness checks.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from logger_config import get_logger

logger = get_logger(__name__)

DEFAULT_INCLUDE_GLOBS: Tuple[str, ...] = (
    "*.md",
    "*.txt",
    "*.rst",
    "*.yaml",
    "*.yml",
    "*.tex",
    "*.json",
    "*.py",
)

DEFAULT_EXCLUDE_PARTS: Tuple[str, ...] = (
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "output",
    "autocontrol_scientist.egg-info",
)


@dataclass(frozen=True)
class RAGSettings:
    enabled: bool = True
    top_k: int = 4
    min_score: float = 0.08
    max_chunks_per_file: int = 2
    chunk_size: int = 1200
    chunk_overlap: int = 200
    max_context_chars: int = 5000
    max_file_size_kb: int = 512
    include_globs: Tuple[str, ...] = DEFAULT_INCLUDE_GLOBS
    source_paths: Tuple[str, ...] = (
        "./README.md",
        "./docs",
        "./prompts/control_systems",
    )


@dataclass
class ChunkRecord:
    path: str
    chunk_id: int
    text: str
    tf: Counter
    norm: float


def _tokenize(text: str) -> List[str]:
    # Keep ASCII words + digits + contiguous CJK spans for mixed-language queries.
    return re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower())


def _split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if chunk_size <= 0:
        return [text]
    overlap = max(0, min(overlap, chunk_size - 1))
    step = chunk_size - overlap
    chunks: List[str] = []
    start = 0
    while start < len(text):
        part = text[start:start + chunk_size].strip()
        if part:
            chunks.append(part)
        start += step
    return chunks


def _safe_read_text(path: Path, max_file_size_kb: int) -> Optional[str]:
    try:
        if path.stat().st_size > max_file_size_kb * 1024:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _is_excluded(path: Path) -> bool:
    lowered_parts = {p.lower() for p in path.parts}
    return any(part in lowered_parts for part in DEFAULT_EXCLUDE_PARTS)


def _collect_files(source_paths: Sequence[str], include_globs: Sequence[str]) -> List[Path]:
    files: List[Path] = []
    seen: set[str] = set()
    for raw in source_paths:
        p = Path(raw).resolve()
        if not p.exists():
            continue
        if p.is_file():
            key = str(p)
            if key not in seen and not _is_excluded(p):
                files.append(p)
                seen.add(key)
            continue
        for pattern in include_globs:
            for file in p.rglob(pattern):
                if not file.is_file() or _is_excluded(file):
                    continue
                key = str(file.resolve())
                if key in seen:
                    continue
                files.append(file.resolve())
                seen.add(key)
    return files


class LocalRAGEngine:
    def __init__(self, settings: RAGSettings):
        self.settings = settings
        self._idf: Dict[str, float] = {}
        self._chunks: List[ChunkRecord] = []
        self._signature: Optional[Tuple[Tuple[str, float], ...]] = None
        self._lock = Lock()

    def _current_signature(self) -> Tuple[Tuple[str, float], ...]:
        signature: List[Tuple[str, float]] = []
        files = _collect_files(self.settings.source_paths, self.settings.include_globs)
        for file in files:
            try:
                signature.append((str(file), file.stat().st_mtime))
            except OSError:
                continue
        signature.sort()
        return tuple(signature)

    def _rebuild_index(self) -> None:
        files = _collect_files(self.settings.source_paths, self.settings.include_globs)
        chunks: List[ChunkRecord] = []
        df: Counter = Counter()

        for file in files:
            text = _safe_read_text(file, self.settings.max_file_size_kb)
            if not text:
                continue
            parts = _split_text(text, self.settings.chunk_size, self.settings.chunk_overlap)
            for idx, part in enumerate(parts):
                tokens = _tokenize(part)
                if not tokens:
                    continue
                tf = Counter(tokens)
                norm = math.sqrt(sum(v * v for v in tf.values())) or 1.0
                chunks.append(
                    ChunkRecord(path=str(file), chunk_id=idx, text=part, tf=tf, norm=norm)
                )
                for token in tf.keys():
                    df[token] += 1

        total = max(1, len(chunks))
        idf: Dict[str, float] = {}
        for token, count in df.items():
            idf[token] = math.log((1 + total) / (1 + count)) + 1.0

        self._chunks = chunks
        self._idf = idf
        self._signature = self._current_signature()
        logger.info("RAG index rebuilt: files=%d chunks=%d", len(files), len(chunks))

    def ensure_index(self) -> None:
        if not self.settings.enabled:
            return
        with self._lock:
            current = self._current_signature()
            if self._signature != current:
                self._rebuild_index()

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[ChunkRecord]:
        if not self.settings.enabled:
            return []
        self.ensure_index()
        if not self._chunks:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        q_tf = Counter(query_tokens)
        q_weights: Dict[str, float] = {
            token: freq * self._idf.get(token, 1.0) for token, freq in q_tf.items()
        }
        q_norm = math.sqrt(sum(v * v for v in q_weights.values())) or 1.0

        scored: List[Tuple[float, ChunkRecord]] = []
        for chunk in self._chunks:
            dot = 0.0
            for token, q_val in q_weights.items():
                c_tf = chunk.tf.get(token)
                if not c_tf:
                    continue
                dot += q_val * (c_tf * self._idf.get(token, 1.0))
            if dot <= 0:
                continue
            score = dot / (q_norm * chunk.norm)
            scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        k = max(1, top_k if top_k is not None else self.settings.top_k)
        min_score = max(0.0, float(self.settings.min_score))
        max_chunks_per_file = max(1, int(self.settings.max_chunks_per_file))

        selected: List[ChunkRecord] = []
        by_path: Counter[str] = Counter()
        for score, chunk in scored:
            if score < min_score:
                continue
            if by_path[chunk.path] >= max_chunks_per_file:
                continue
            selected.append(chunk)
            by_path[chunk.path] += 1
            if len(selected) >= k:
                break

        if selected:
            return selected

        # Fallback for overly strict thresholds: still return diversified top-k.
        by_path.clear()
        for _, chunk in scored:
            if by_path[chunk.path] >= max_chunks_per_file:
                continue
            selected.append(chunk)
            by_path[chunk.path] += 1
            if len(selected) >= k:
                break
        return selected

    def build_context(self, query: str) -> str:
        results = self.retrieve(query)
        if not results:
            return ""

        lines: List[str] = []
        used = 0
        max_chars = max(500, self.settings.max_context_chars)

        for idx, chunk in enumerate(results, start=1):
            try:
                rel = os.path.relpath(chunk.path, Path.cwd())
            except ValueError:
                # Windows may raise for different drive letters.
                rel = chunk.path
            snippet = chunk.text.strip()
            block = f"[{idx}] source: {rel}\n{snippet}\n"
            if used + len(block) > max_chars and lines:
                break
            lines.append(block)
            used += len(block)

        if not lines:
            return ""
        return "\n".join(lines).strip()


_ENGINE_CACHE: Dict[RAGSettings, LocalRAGEngine] = {}
_ENGINE_LOCK = Lock()


def settings_from_api_config(api_config: object) -> RAGSettings:
    if api_config is None:
        return RAGSettings(enabled=False)

    enabled = bool(getattr(api_config, "rag_enabled", True))
    top_k = int(getattr(api_config, "rag_top_k", 4) or 4)
    min_score = float(getattr(api_config, "rag_min_score", 0.08) or 0.08)
    max_chunks_per_file = int(getattr(api_config, "rag_max_chunks_per_file", 2) or 2)
    chunk_size = int(getattr(api_config, "rag_chunk_size", 1200) or 1200)
    chunk_overlap = int(getattr(api_config, "rag_chunk_overlap", 200) or 200)
    max_ctx = int(getattr(api_config, "rag_max_context_chars", 5000) or 5000)
    max_file_size_kb = int(getattr(api_config, "rag_max_file_size_kb", 512) or 512)

    paths = getattr(api_config, "rag_paths", None)
    if not paths:
        env_paths = os.getenv("AUTOCONTROL_RAG_PATHS", "").strip()
        if env_paths:
            paths = [p.strip() for p in env_paths.split(";") if p.strip()]
    source_paths = tuple(paths) if paths else RAGSettings.source_paths

    include_globs = getattr(api_config, "rag_include_globs", None)
    if include_globs:
        include = tuple(include_globs)
    else:
        include = DEFAULT_INCLUDE_GLOBS

    return RAGSettings(
        enabled=enabled,
        top_k=top_k,
        min_score=min_score,
        max_chunks_per_file=max_chunks_per_file,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        max_context_chars=max_ctx,
        max_file_size_kb=max_file_size_kb,
        include_globs=include,
        source_paths=source_paths,
    )


def get_engine(settings: RAGSettings) -> LocalRAGEngine:
    with _ENGINE_LOCK:
        engine = _ENGINE_CACHE.get(settings)
        if engine is None:
            engine = LocalRAGEngine(settings)
            _ENGINE_CACHE[settings] = engine
        return engine


def build_rag_context(query: str, api_config: object) -> str:
    settings = settings_from_api_config(api_config)
    if not settings.enabled:
        return ""
    engine = get_engine(settings)
    return engine.build_context(query)
