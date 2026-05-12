"""
Loader for domain-specific rules used by the G4 Ligand schema converter.

Rules are stored in ``domain_rules.yaml`` so that biochemistry / chemistry
domain experts can adjust extraction heuristics without touching Python code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

import yaml


_DEFAULT_YAML = Path(__file__).parent / "domain_rules.yaml"


@dataclass
class DomainRules:
    """Immutable container for all G4 Ligand domain extraction rules."""

    # Ligand ID validation
    ligand_id_prefixes: List[str] = field(default_factory=list)

    # Sequence classification
    sequence_type_keywords: Dict[str, List[str]] = field(default_factory=dict)

    # Activity classification
    activity1_keywords: Dict[str, List[str]] = field(default_factory=dict)
    activity2_keywords: Dict[str, List[str]] = field(default_factory=dict)

    # Method classification
    method_keywords: Dict[str, List[str]] = field(default_factory=dict)

    # Buffer composition patterns
    buffer_components: Dict[str, List[str]] = field(default_factory=dict)

    # Counter-ion patterns
    counter_ion_patterns: Dict[str, List[str]] = field(default_factory=dict)

    # Metal ion patterns
    metal_ion_patterns: Dict[str, List[str]] = field(default_factory=dict)

    # Synonym type keywords
    synonym_type_keywords: Dict[str, List[str]] = field(default_factory=dict)

    # Pre-compiled regexes (populated by _compile)
    _compiled_activity1: Dict[str, List[re.Pattern]] = field(
        default_factory=dict, repr=False
    )
    _compiled_activity2: Dict[str, List[re.Pattern]] = field(
        default_factory=dict, repr=False
    )
    _compiled_method: Dict[str, List[re.Pattern]] = field(
        default_factory=dict, repr=False
    )
    _compiled_buffer: Dict[str, List[re.Pattern]] = field(
        default_factory=dict, repr=False
    )
    _compiled_counter_ion: Dict[str, List[re.Pattern]] = field(
        default_factory=dict, repr=False
    )
    _compiled_metal_ion: Dict[str, List[re.Pattern]] = field(
        default_factory=dict, repr=False
    )

    def _compile(self) -> None:
        """Pre-compile regex patterns for classification matching."""
        for category, patterns in [
            ("activity1", self.activity1_keywords),
            ("activity2", self.activity2_keywords),
            ("method", self.method_keywords),
            ("buffer", self.buffer_components),
            ("counter_ion", self.counter_ion_patterns),
            ("metal_ion", self.metal_ion_patterns),
        ]:
            attr = f"_compiled_{category}"
            compiled_dict = {}
            for key, kw_list in patterns.items():
                compiled_dict[key] = [
                    re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
                    for kw in kw_list
                ]
            setattr(self, attr, compiled_dict)

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> DomainRules:
        """Load rules from a YAML file.

        Parameters
        ----------
        path : Path, optional
            Path to the YAML file.  Defaults to ``domain_rules.yaml`` next to
            this module.
        """
        if path is None:
            path = _DEFAULT_YAML
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        rules = cls(
            ligand_id_prefixes=raw.get("ligand_id_prefixes", []),
            sequence_type_keywords=raw.get("sequence_type_keywords", {}),
            activity1_keywords=raw.get("activity1_keywords", {}),
            activity2_keywords=raw.get("activity2_keywords", {}),
            method_keywords=raw.get("method_keywords", {}),
            buffer_components=raw.get("buffer_components", {}),
            counter_ion_patterns=raw.get("counter_ion_patterns", {}),
            metal_ion_patterns=raw.get("metal_ion_patterns", {}),
            synonym_type_keywords=raw.get("synonym_type_keywords", {}),
        )
        rules._compile()
        return rules

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def classify_sequence_type(self, text: str) -> str | None:
        """Return the best-matching sequence type for ``text``."""
        text_lower = text.lower()
        best_match = None
        for seq_type, patterns in self.sequence_type_keywords.items():
            for kw in patterns:
                if kw.lower() in text_lower:
                    best_match = seq_type
                    break
        return best_match

    def classify_activity1(self, text: str) -> str | None:
        """Return the best-matching primary activity for ``text``."""
        text_lower = text.lower()
        best_match = None
        for activity, patterns in self.activity1_keywords.items():
            for kw in patterns:
                if kw.lower() in text_lower:
                    best_match = activity
                    break
        return best_match

    def classify_activity2(self, text: str) -> str | None:
        """Return the best-matching secondary activity for ``text``."""
        text_lower = text.lower()
        best_match = None
        for activity, patterns in self.activity2_keywords.items():
            for kw in patterns:
                if kw.lower() in text_lower:
                    best_match = activity
                    break
        return best_match

    def classify_method(self, text: str) -> str | None:
        """Return the best-matching experimental method for ``text``."""
        text_lower = text.lower()
        best_match = None
        for method, patterns in self.method_keywords.items():
            for kw in patterns:
                if kw.lower() in text_lower:
                    best_match = method
                    break
        return best_match


# Module-level singleton so callers can ``from knowmat.domain_rules import default_rules``.
default_rules = DomainRules.from_yaml()
