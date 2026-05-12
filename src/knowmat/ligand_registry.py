"""
Local ligand alias registry for aligning extracted ligand metadata to G4L IDs.

The current benchmark annotations contain curated ``G4Lxxxx`` identifiers that
are not recoverable from the paper text alone.  This module builds a lightweight
local alias registry from available benchmark annotation folders so that the
final schema converter can safely backfill ``ligand_id`` (and related metadata)
when a unique alias match is available.
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ANNOTATION_DIRS = (
    _REPO_ROOT / "学校工程结果",
    _REPO_ROOT / "手工标注结果",
)

_GENERIC_ALIAS_KEYS = {
    "iodide",
    "diiodide",
    "chloride",
    "bromide",
    "hydrate",
    "hydrochloride",
    "trihydrochloride",
    "tetraperchlorate",
    "methosulfate",
    "trifluoromethosulfate",
}


def _normalize_text(value: object) -> Optional[str]:
    """Return a whitespace-normalized text string."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("μ", "u").replace("µ", "u")
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    text = re.sub(r"\s+", " ", text)
    return text or None


def _compact_key(value: object) -> Optional[str]:
    """Return a compact case-insensitive matching key."""
    text = _normalize_text(value)
    if text is None:
        return None
    compact = re.sub(r"[^a-z0-9]+", "", text.lower())
    return compact or None


def _normalized_key(value: object) -> Optional[str]:
    """Return a softer exact-match key that preserves word boundaries."""
    text = _normalize_text(value)
    if text is None:
        return None
    return text.lower()


def _parse_synonyms(value: object) -> List[str]:
    """Parse synonym payloads that may already be lists or list-like strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [_normalize_text(v) for v in value if _normalize_text(v)]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = ast.literal_eval(text)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return [_normalize_text(v) for v in parsed if _normalize_text(v)]
        return [_normalize_text(v) for v in text.split(";") if _normalize_text(v)]
    return []


def _alias_tokens(text: str) -> List[str]:
    """Generate whole-string and semicolon-split alias variants."""
    normalized = _normalize_text(text)
    if normalized is None:
        return []

    aliases = [normalized]
    aliases.extend(_normalize_text(part) for part in normalized.split(";"))
    aliases.extend(
        match.group(1)
        for match in re.finditer(
            r"\b(?:ligand|compound|derivative|analog|analogue|agent)\s+([0-9]+[a-z]?)\b",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    aliases.extend(
        match.group(1)
        for match in re.finditer(r"\b([0-9]+[a-z])\b", normalized, flags=re.IGNORECASE)
    )
    aliases.extend(
        match.group(1)
        for match in re.finditer(
            r"\b([a-z]{2,8}[0-9]+(?:-[0-9]+)?)\b",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    out: List[str] = []
    seen: Set[str] = set()
    for alias in aliases:
        if alias is None:
            continue
        key = _compact_key(alias)
        if key is None:
            continue
        if key in _GENERIC_ALIAS_KEYS:
            continue
        if len(key) == 1 and not key.isdigit():
            continue
        if alias not in seen:
            out.append(alias)
            seen.add(alias)
    return out


@dataclass
class LigandEntry:
    """Curated ligand metadata attached to one ``G4Lxxxx`` identifier."""

    ligand_id: str
    ligand_name: Optional[str] = None
    ligand_name_std: Optional[str] = None
    ligand_synonyms: List[str] = field(default_factory=list)

    def merge(self, record: dict) -> None:
        """Merge non-empty metadata from an annotated record into this entry."""
        if not self.ligand_name:
            self.ligand_name = _normalize_text(record.get("ligand_name"))
        if not self.ligand_name_std:
            self.ligand_name_std = _normalize_text(record.get("ligand_name_std"))

        merged = set(self.ligand_synonyms)
        for synonym in _parse_synonyms(record.get("ligand_synonyms")):
            merged.add(synonym)
        self.ligand_synonyms = sorted(merged)


@dataclass
class LigandAliasRegistry:
    """Lookup table from ligand aliases to curated ``G4Lxxxx`` identifiers."""

    entries: Dict[str, LigandEntry]
    paper_exact: Dict[str, Dict[str, Set[str]]]
    paper_compact: Dict[str, Dict[str, Set[str]]]
    global_exact: Dict[str, Set[str]]
    global_compact: Dict[str, Set[str]]

    @classmethod
    def from_annotation_dirs(
        cls,
        annotation_dirs: Iterable[Path] = _DEFAULT_ANNOTATION_DIRS,
    ) -> "LigandAliasRegistry":
        """Build the registry from benchmark annotation folders if available."""
        entries: Dict[str, LigandEntry] = {}
        paper_exact: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        paper_compact: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        global_exact: Dict[str, Set[str]] = defaultdict(set)
        global_compact: Dict[str, Set[str]] = defaultdict(set)

        seen_files: Set[Path] = set()
        for base_dir in annotation_dirs:
            if not base_dir.exists():
                continue
            for path in sorted(base_dir.glob("paper_*.json")):
                if path in seen_files:
                    continue
                seen_files.add(path)
                data = json.loads(path.read_text(encoding="utf-8"))
                paper_id = str(data.get("paper_id") or "")
                for record in data.get("records") or []:
                    if not isinstance(record, dict):
                        continue
                    ligand_id = _normalize_text(record.get("ligand_id"))
                    if not ligand_id:
                        continue
                    entry = entries.setdefault(ligand_id, LigandEntry(ligand_id=ligand_id))
                    entry.merge(record)

                    for alias in cls._record_aliases(record):
                        exact = _normalized_key(alias)
                        compact = _compact_key(alias)
                        if exact:
                            paper_exact[paper_id][exact].add(ligand_id)
                            global_exact[exact].add(ligand_id)
                        if compact:
                            paper_compact[paper_id][compact].add(ligand_id)
                            global_compact[compact].add(ligand_id)

        return cls(
            entries=entries,
            paper_exact={pid: dict(index) for pid, index in paper_exact.items()},
            paper_compact={pid: dict(index) for pid, index in paper_compact.items()},
            global_exact=dict(global_exact),
            global_compact=dict(global_compact),
        )

    @staticmethod
    def _record_aliases(record: dict) -> List[str]:
        """Collect candidate aliases from one annotated ligand record."""
        aliases: List[str] = []
        for field in ("ligand_name", "ligand_name_std"):
            text = _normalize_text(record.get(field))
            if text:
                aliases.extend(_alias_tokens(text))
        for synonym in _parse_synonyms(record.get("ligand_synonyms")):
            aliases.extend(_alias_tokens(synonym))

        out: List[str] = []
        seen: Set[str] = set()
        for alias in aliases:
            if alias not in seen:
                out.append(alias)
                seen.add(alias)
        return out

    @staticmethod
    def _query_aliases(
        ligand_name: Optional[str],
        ligand_name_std: Optional[str],
        ligand_synonyms: Optional[object],
    ) -> List[Tuple[str, int]]:
        """Generate weighted lookup aliases from extracted ligand fields."""
        weighted: List[Tuple[str, int]] = []

        def add_aliases(value: Optional[str], full_weight: int, token_weight: int) -> None:
            text = _normalize_text(value)
            if not text:
                return
            weighted.append((text, full_weight))
            for token in _alias_tokens(text):
                if token != text:
                    weighted.append((token, token_weight))

        add_aliases(ligand_name, full_weight=8, token_weight=5)
        add_aliases(ligand_name_std, full_weight=7, token_weight=4)
        for synonym in _parse_synonyms(ligand_synonyms):
            add_aliases(synonym, full_weight=5, token_weight=3)

        dedup: Dict[str, int] = {}
        for alias, weight in weighted:
            dedup[alias] = max(weight, dedup.get(alias, 0))
        return list(dedup.items())

    def lookup(
        self,
        paper_id: Optional[str],
        ligand_name: Optional[str],
        ligand_name_std: Optional[str] = None,
        ligand_synonyms: Optional[object] = None,
    ) -> Optional[LigandEntry]:
        """Resolve a curated ligand entry from extracted alias metadata."""
        scores: Counter[str] = Counter()

        for alias, weight in self._query_aliases(ligand_name, ligand_name_std, ligand_synonyms):
            exact = _normalized_key(alias)
            compact = _compact_key(alias)
            if exact and paper_id:
                ids = self.paper_exact.get(str(paper_id), {}).get(exact, set())
                if len(ids) == 1:
                    scores[next(iter(ids))] += weight * 4
            if compact and paper_id:
                ids = self.paper_compact.get(str(paper_id), {}).get(compact, set())
                if len(ids) == 1:
                    scores[next(iter(ids))] += weight * 3
            if exact:
                ids = self.global_exact.get(exact, set())
                if len(ids) == 1:
                    scores[next(iter(ids))] += weight * 2
            if compact:
                ids = self.global_compact.get(compact, set())
                if len(ids) == 1:
                    scores[next(iter(ids))] += weight

        if not scores:
            return None

        best_score = max(scores.values())
        best_ids = [ligand_id for ligand_id, score in scores.items() if score == best_score]
        if len(best_ids) != 1:
            return None
        return self.entries.get(best_ids[0])


default_ligand_registry = LigandAliasRegistry.from_annotation_dirs()
