"""
Schema converter for KnowMat 2.0 — G4 Ligand Binding domain.

Transforms the internal LLM extraction format into the final flat target schema
rooted at ``paper_id`` / ``record_count`` / ``records``.
All domain heuristics (method inference, activity classification, buffer
parsing, etc.) are driven by :class:`~knowmat.domain_rules.DomainRules`
so that domain experts can adjust behaviour via ``domain_rules.yaml``.
"""

from __future__ import annotations

import json
import logging
import os
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional

from knowmat.domain_rules import DomainRules, default_rules
from knowmat.ligand_registry import LigandAliasRegistry, default_ligand_registry
from knowmat.states import TargetSchema

logger = logging.getLogger(__name__)

# Valid sequence types for the G4 ligand domain.
VALID_SEQUENCE_TYPES = {
    "DNA",
    "RNA",
    "DNA/RNA hybrid",
    "PNA",
    "LNA",
    "Modified oligonucleotide",
    "Unknown",
}

# Valid primary activity labels.
VALID_ACTIVITY1 = {
    "Interaction",
    "Activity at Molecular Level",
    "Activity at Cellular Level",
    # Backward-compatible runtime labels that are normalized into the dataset's
    # flatter top-level activity taxonomy during final conversion.
    "Binding",
    "Stabilization",
    "Selectivity",
    "Inhibition",
    "Cleavage",
    "Fluorescence response",
    "Unfolding",
    "Folding",
    "Thermal stabilization",
    "Competition",
    "Displacement",
    "Cellular activity",
    "Cytotoxicity",
}


class SchemaConverter:
    """Convert LLM-extracted G4 binding data to the final flat target schema."""

    def __init__(
        self,
        rules: DomainRules | None = None,
        ligand_registry: LigandAliasRegistry | None = None,
    ) -> None:
        self.rules = rules or default_rules
        self.ligand_registry = ligand_registry or default_ligand_registry

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def convert(
        self,
        data: dict,
        source_path: str,
        paper_text: Optional[str] = None,
        document_metadata: Optional[dict] = None,
    ) -> TargetSchema:
        """Convert extraction dict to the final flat schema.

        Supported input envelopes:
        - strict schema: ``{"Paper_Metadata": ..., "items": [...]}``
        - runtime schema: ``{"g4_bindings": [...]}``

        Output is always flat:
        ``{"paper_id": "...", "record_count": 0, "records": [...]}``
        """
        lab_schema = self._to_lab_schema(
            data=data,
            source_path=source_path,
            paper_text=paper_text,
            document_metadata=document_metadata,
        )
        return self._lab_schema_to_target_schema(lab_schema, source_path)

    def _to_lab_schema(
        self,
        data: dict,
        source_path: str,
        paper_text: Optional[str] = None,
        document_metadata: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Convert extraction dict to the intermediate lab-style schema."""
        paper_metadata = self._resolve_paper_metadata(
            source_path=source_path,
            paper_text=paper_text,
            document_metadata=document_metadata,
            existing_metadata=(data or {}).get("Paper_Metadata") if isinstance(data, dict) else None,
        )
        if not isinstance(data, dict):
            return self._empty_lab_schema(paper_metadata)

        # Preferred path: already in strict lab schema.
        if isinstance(data.get("items"), list):
            repaired = self._repair_existing_lab_items(data.get("items", []) or [])
            return {
                "Paper_Metadata": paper_metadata,
                "items": repaired,
            }

        # Runtime compatibility path: convert g4_bindings -> lab items.
        g4_bindings = data.get("g4_bindings")
        if isinstance(g4_bindings, list):
            return {
                "Paper_Metadata": paper_metadata,
                "items": self._convert_runtime_g4_bindings_to_lab_items(
                    bindings=g4_bindings,
                    paper_text=paper_text,
                ),
            }

        logger.warning(
            "Unsupported extraction envelope keys: %s. Returning empty strict schema.",
            sorted(data.keys()),
        )
        return self._empty_lab_schema(paper_metadata)

    def _lab_schema_to_target_schema(
        self,
        lab_schema: Dict[str, Any],
        source_path: str,
    ) -> TargetSchema:
        """Flatten the lab-style schema into the benchmark target schema."""
        paper_id = self._resolve_paper_id(
            source_path=source_path,
            paper_metadata=lab_schema.get("Paper_Metadata") or {},
        )
        records: List[Dict[str, Any]] = []
        for item in lab_schema.get("items", []) or []:
            new_records = self._lab_item_to_target_records(item, paper_id)
            records.extend(new_records)
        # Deduplicate records that are identical except for sequence_name alias
        records = self._deduplicate_sequence_aliases(records)
        return {
            "paper_id": paper_id,
            "record_count": len(records),
            "records": records,
        }

    # ------------------------------------------------------------------
    # Runtime → Lab item conversion
    # ------------------------------------------------------------------

    def _convert_runtime_g4_bindings_to_lab_items(
        self,
        bindings: List[dict],
        paper_text: Optional[str] = None,
    ) -> List[dict]:
        """Convert runtime ``g4_bindings`` envelope into strict ``items``."""
        items: List[dict] = []
        for idx, binding in enumerate(bindings, start=1):
            if not isinstance(binding, dict):
                continue
            item = self._binding_to_lab_item(binding, idx)
            items.append(item)
        return self._repair_existing_lab_items(items)

    def _binding_to_lab_item(self, binding: dict, idx: int) -> dict:
        """Transform a single runtime g4_binding dict into a lab item."""
        # Ligand_Info
        ligand_info: Dict[str, Any] = {}
        ligand_id = self._clean_optional_str(binding.get("ligand_id"))
        if ligand_id:
            ligand_info["ligand_id"] = ligand_id
        ligand_name = self._clean_optional_str(binding.get("ligand_name"))
        if ligand_name:
            ligand_info["ligand_name"] = ligand_name
        ligand_name_std = self._clean_optional_str(binding.get("ligand_name_std"))
        if ligand_name_std:
            ligand_info["ligand_name_std"] = ligand_name_std

        synonyms_raw = binding.get("ligand_synonyms")
        if isinstance(synonyms_raw, list) and synonyms_raw:
            synonyms = [self._clean_optional_str(s) for s in synonyms_raw if s]
            synonyms = [s for s in synonyms if s]
            if synonyms:
                ligand_info["ligand_synonyms"] = synonyms
        elif isinstance(synonyms_raw, str) and synonyms_raw.strip():
            # Split semicolon-separated synonyms
            parsed = [s.strip() for s in synonyms_raw.split(";") if s.strip()]
            if parsed:
                ligand_info["ligand_synonyms"] = parsed

        counter_ion = self._clean_optional_str(binding.get("counter_ion"))
        if counter_ion:
            ligand_info["counter_ion"] = counter_ion
        metal_ion = self._clean_optional_str(binding.get("metal_ion"))
        if metal_ion:
            ligand_info["metal_ion"] = metal_ion

        # Sequence_Info
        sequence_info: Dict[str, Any] = {}
        sequence = self._clean_optional_str(binding.get("sequence"))
        sequence_name = self._clean_optional_str(binding.get("sequence_name"))

        # Guard: if the model stored a sequence alias (non-nucleotide string) in
        # the ``sequence`` field, move it to ``sequence_name`` and null sequence.
        if sequence and not self._looks_like_nucleotide_sequence(sequence):
            # Prefer the dedicated sequence_name if already populated; otherwise
            # promote the mis-placed alias into sequence_name.
            if not sequence_name:
                sequence_name = sequence
            sequence = None

        if sequence:
            sequence_info["sequence"] = sequence
        if sequence_name:
            sequence_info["sequence_name"] = sequence_name
        sequence_type = self._normalize_sequence_type(binding.get("sequence_type"))
        if sequence_type:
            sequence_info["sequence_type"] = sequence_type

        # Activity_Info
        activity_info: Dict[str, Any] = {}
        activity1 = self._normalize_activity1(binding.get("activity1"))
        if activity1:
            activity_info["activity1"] = activity1
        activity2 = self._clean_optional_str(binding.get("activity2"))
        method = self._normalize_method(binding.get("method"))
        if activity2:
            activity_info["activity2"] = activity2
        value = self._clean_optional_str(binding.get("value"))
        signal_text = " ".join(part for part in (method, value) if part)
        if not activity_info.get("activity2") and signal_text:
            inferred_activity2 = self.rules.classify_activity2(signal_text)
            if inferred_activity2:
                activity_info["activity2"] = inferred_activity2
        if not activity_info.get("activity1") and signal_text:
            inferred_activity1 = self._rules_classify_activity1(signal_text)
            if inferred_activity1:
                activity_info["activity1"] = inferred_activity1
        if value:
            activity_info["value"] = value

        # Experimental_Conditions
        exp_conditions: Dict[str, Any] = {}
        if method:
            exp_conditions["method"] = method
        buffer = self._clean_optional_str(binding.get("buffer"))
        if buffer:
            exp_conditions["buffer"] = buffer
        sample_conc = self._clean_optional_str(binding.get("sample_concentration"))
        if sample_conc:
            exp_conditions["sample_concentration"] = sample_conc
        instrument = self._clean_optional_str(binding.get("instrument"))
        if instrument:
            exp_conditions["instrument"] = instrument
        comments = self._clean_optional_str(binding.get("comments"))
        if comments:
            exp_conditions["comments"] = comments

        # Context
        context = self._clean_optional_str(binding.get("context"))

        item: Dict[str, Any] = {}
        if ligand_info:
            item["Ligand_Info"] = ligand_info
        if sequence_info:
            item["Sequence_Info"] = sequence_info
        if activity_info:
            item["Activity_Info"] = activity_info
        if exp_conditions:
            item["Experimental_Conditions"] = exp_conditions
        if context:
            item["context"] = context

        return item

    def _lab_item_to_target_records(
        self,
        item: Dict[str, Any],
        paper_id: str,
    ) -> List[Dict[str, Any]]:
        """Flatten one lab item into one or more final benchmark records.

        Handles per-sequence disaggregation: if ``sequence_name`` contains
        semicolons or commas separating multiple sequence names, the item is
        split into one record per sequence name.
        """
        record = self._lab_item_to_target_record(item, paper_id)
        if record is None:
            return []

        # ── Per-sequence disaggregation ──
        seq_name = record.get("sequence_name") or ""
        # Check for semicolon- or comma-delimited multiple sequence names
        # but don't split legitimate composite names like "Pu24; PDB ID: 2MGN"
        separators = [";", ","]
        parts: List[str] = []
        for sep in separators:
            if sep in seq_name:
                candidate_parts = [p.strip() for p in seq_name.split(sep) if p.strip()]
                # Only split if parts look like distinct sequence names
                # (not composite labels like "PDB ID: 2MGN")
                if len(candidate_parts) >= 2 and all(
                    not p.lower().startswith("pdb") and
                    not p.lower().startswith("doi") and
                    len(p) > 1
                    for p in candidate_parts
                ):
                    parts = candidate_parts
                    break

        if len(parts) >= 2:
            records = []
            for part in parts:
                split_record = dict(record)
                split_record["sequence_name"] = part
                # If the original record has a sequence field, we can't
                # reliably split it, so null it out for the split records
                # unless there's only one sequence
                if record.get("sequence") and len(parts) > 1:
                    split_record["sequence"] = None
                records.append(split_record)
            return records

        return [record]

    def _lab_item_to_target_record(
        self,
        item: Dict[str, Any],
        paper_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Flatten one lab item into one final benchmark record."""
        if not isinstance(item, dict):
            return None

        ligand_info = dict(item.get("Ligand_Info") or {})
        sequence_info = dict(item.get("Sequence_Info") or {})
        activity_info = dict(item.get("Activity_Info") or {})
        experimental = dict(item.get("Experimental_Conditions") or {})
        ligand_info = self._enrich_ligand_info(ligand_info, paper_id)

        record = {
            "ligand_id": self._clean_optional_str(ligand_info.get("ligand_id")),
            "ligand_name": self._clean_optional_str(ligand_info.get("ligand_name")),
            "ligand_name_std": self._clean_optional_str(ligand_info.get("ligand_name_std")),
            "ligand_synonyms": self._normalize_output_synonyms(ligand_info.get("ligand_synonyms")),
            "sequence": self._clean_optional_str(sequence_info.get("sequence")),
            "sequence_name": self._clean_optional_str(sequence_info.get("sequence_name")),
            "sequence_type": self._normalize_sequence_type(sequence_info.get("sequence_type")),
            "activity1": self._normalize_activity1(activity_info.get("activity1")),
            "activity2": self._normalize_activity2(activity_info.get("activity2")),
            "method": self._normalize_method(experimental.get("method")),
            "value": self._clean_optional_str(activity_info.get("value")),
            "buffer": self._clean_optional_str(experimental.get("buffer")),
            "sample_concentration": self._clean_optional_str(
                experimental.get("sample_concentration")
            ),
            "instrument": self._clean_optional_str(experimental.get("instrument")),
            "comments": self._clean_optional_str(experimental.get("comments")),
            "counter_ion": self._clean_optional_str(ligand_info.get("counter_ion")),
            "metal_ion": self._clean_optional_str(ligand_info.get("metal_ion")),
            "paper_id": paper_id,
            "context": self._clean_optional_str(item.get("context")),
        }

        # Drop items that contain no meaningful scientific payload.
        payload_keys = (
            "ligand_id",
            "ligand_name",
            "sequence",
            "sequence_name",
            "activity2",
            "value",
            "method",
        )
        if not any(record.get(key) for key in payload_keys):
            return None

        # ── Post-normalization MSM auto-correction ──
        method_val = (record.get("method") or "").lower()
        value_val = (record.get("value") or "").lower()
        msm_kws = [
            "first passage time", "pathway flux", "interstate flux",
            "binding pathway", "msm", "markov", "conformational selection",
            "binding mode population", "state transition",
        ]
        if "mass spectr" in method_val and any(kw in value_val for kw in msm_kws):
            record["method"] = "Markov State Model (MSM) analysis"

        # ── Vague value filter at flat-record level ──
        if record.get("value") and self._is_vague_or_pointer_value(record["value"]):
            return None

        # ── Normalize "telIC50" → "IC50" for TRAP assay values ──
        if record.get("value"):
            record["value"] = re.sub(
                r'\btelIC50\b', 'IC50', record["value"], flags=re.IGNORECASE,
            )

        # ── Absolute Tm filter for Stabilization records ──
        # Drop Stabilization records that contain absolute Tm values instead
        # of Delta Tm (ΔTm). The benchmark requires Delta Tm only.
        if record.get("value") and self._is_absolute_tm_value(record["value"], record.get("activity2")):
            logger.debug(
                "Dropping absolute Tm record (not Delta Tm): %s",
                record.get("value"),
            )
            return None

        # ── Non-G4 method filter ──
        # Drop records for methods that are not G4 ligand–nucleic acid endpoints.
        if self._is_non_g4_method(record.get("method"), record.get("value")):
            logger.debug(
                "Dropping non-G4 method record: method=%s value=%s",
                record.get("method"), record.get("value"),
            )
            return None

        # ── Supportive observable filter ──
        # Drop records whose value is a supportive observable, not a final endpoint.
        if self._is_supportive_observable(record.get("value")):
            logger.debug(
                "Dropping supportive observable record: %s",
                record.get("value"),
            )
            return None

        # ── Null-method filter for non-biophysical records ──
        # Cytotoxicity and Gene Expression records without a method are likely
        # not properly characterised assay results; drop them.
        if not record.get("method"):
            a2 = (record.get("activity2") or "").lower()
            if a2 in ("cytotoxicity", "gene expression"):
                logger.debug(
                    "Dropping null-method %s record: %s",
                    a2, record.get("value"),
                )
                return None

        # ── Duplex control SPR filter ──
        # Drop binding records whose value explicitly references duplex DNA
        # (control measurements, not G4 endpoints).
        if self._is_duplex_control_record(record):
            logger.debug(
                "Dropping duplex control record: %s",
                record.get("value"),
            )
            return None

        # ── Q/D ratio and selectivity ratio filter ──
        # Q/D ratio, selectivity index, and fold-selectivity values are derived
        # metrics, not primary binding endpoints.
        if self._is_derived_ratio_value(record.get("value")):
            logger.debug(
                "Dropping derived ratio record: %s",
                record.get("value"),
            )
            return None

        return record

    def _enrich_ligand_info(self, ligand_info: Dict[str, Any], paper_id: str) -> Dict[str, Any]:
        """Backfill ligand metadata from the local alias registry when possible."""
        enriched = dict(ligand_info or {})
        ligand_id = self._clean_optional_str(enriched.get("ligand_id"))
        if ligand_id:
            return enriched

        entry = self.ligand_registry.lookup(
            paper_id=paper_id,
            ligand_name=self._clean_optional_str(enriched.get("ligand_name")),
            ligand_name_std=self._clean_optional_str(enriched.get("ligand_name_std")),
            ligand_synonyms=enriched.get("ligand_synonyms"),
        )
        if entry is None:
            return enriched

        enriched["ligand_id"] = entry.ligand_id
        if not self._clean_optional_str(enriched.get("ligand_name")) and entry.ligand_name:
            enriched["ligand_name"] = entry.ligand_name
        if not self._clean_optional_str(enriched.get("ligand_name_std")) and entry.ligand_name_std:
            enriched["ligand_name_std"] = entry.ligand_name_std

        existing_synonyms = self._normalize_output_synonyms(enriched.get("ligand_synonyms")) or []
        merged_synonyms = set(existing_synonyms)
        merged_synonyms.update(entry.ligand_synonyms or [])
        if merged_synonyms:
            enriched["ligand_synonyms"] = sorted(merged_synonyms)

        return enriched

    # ------------------------------------------------------------------
    # Deduplication helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_sequence_aliases(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate records where the same measurement is duplicated under
        different sequence aliases (e.g., "HTel7" vs "[d-(TTAGGGT)]4").

        Two records are considered duplicates when they share the same
        ligand_name, method, activity2, and value, and differ only in
        sequence_name. When duplicates are found, keep the one with the
        shorter / more canonical sequence_name (typically the alias).
        """
        if not records:
            return records

        def _dedup_key(rec: Dict[str, Any]) -> tuple:
            return (
                (rec.get("ligand_id") or "").lower(),
                (rec.get("ligand_name") or "").lower(),
                (rec.get("method") or "").lower(),
                (rec.get("activity2") or "").lower(),
                (rec.get("value") or "").lower(),
            )

        seen: Dict[tuple, Dict[str, Any]] = {}
        deduped: List[Dict[str, Any]] = []

        for rec in records:
            key = _dedup_key(rec)
            # Only consider dedup when key has actual content
            if not any(key):
                deduped.append(rec)
                continue

            if key in seen:
                existing = seen[key]
                existing_sn = existing.get("sequence_name") or ""
                current_sn = rec.get("sequence_name") or ""
                # Keep the record with the shorter sequence_name (more canonical alias)
                # but prefer the one that has the actual nucleotide sequence populated
                if len(current_sn) < len(existing_sn) and current_sn:
                    # Replace existing with current (shorter alias)
                    for i, d in enumerate(deduped):
                        if d is existing:
                            deduped[i] = rec
                            seen[key] = rec
                            break
                # Otherwise keep the existing one
                logger.debug(
                    "Dedup: dropping sequence alias duplicate: %s (kept %s)",
                    current_sn, (seen[key].get("sequence_name") or ""),
                )
            else:
                seen[key] = rec
                deduped.append(rec)

        if len(deduped) < len(records):
            logger.info(
                "Sequence alias dedup: %d -> %d records",
                len(records), len(deduped),
            )
        return deduped

    # ------------------------------------------------------------------
    # Repair / normalization helpers
    # ------------------------------------------------------------------

    def _repair_existing_lab_items(self, items: List[dict]) -> List[dict]:
        """Normalize and repair existing lab items."""
        repaired: List[dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            repaired_item = self._repair_lab_item(deepcopy(item))
            if repaired_item:
                repaired.append(repaired_item)
        return repaired

    def _repair_lab_item(self, item: dict) -> Optional[dict]:
        """Repair and normalize a single lab item."""
        # Ligand_Info
        ligand_info = dict(item.get("Ligand_Info") or {})
        ligand_info = {k: v for k, v in ligand_info.items() if v}
        if not ligand_info:
            return None
        item["Ligand_Info"] = ligand_info

        # Sequence_Info
        seq_info = dict(item.get("Sequence_Info") or {})
        seq_info = {k: v for k, v in seq_info.items() if v}
        if seq_info:
            # Guard: if an alias was stored in the sequence field, relocate it.
            raw_seq = seq_info.get("sequence")
            if raw_seq and not self._looks_like_nucleotide_sequence(raw_seq):
                if not seq_info.get("sequence_name"):
                    seq_info["sequence_name"] = raw_seq
                del seq_info["sequence"]
            if "sequence" in seq_info and not seq_info.get("sequence_type"):
                seq_info["sequence_type"] = self._infer_sequence_type(seq_info.get("sequence", ""))
            item["Sequence_Info"] = seq_info

        # Activity_Info
        act_info = dict(item.get("Activity_Info") or {})
        act_info = {k: v for k, v in act_info.items() if v}
        exp_info = dict(item.get("Experimental_Conditions") or {})
        exp_info = {k: v for k, v in exp_info.items() if v}
        if act_info:
            signal_text = " ".join(
                part
                for part in (
                    exp_info.get("method", ""),
                    act_info.get("value", ""),
                )
                if part
            )
            if "activity2" not in act_info and signal_text:
                inferred_activity2 = self.rules.classify_activity2(signal_text)
                if inferred_activity2:
                    act_info["activity2"] = inferred_activity2
            if "activity1" not in act_info and signal_text:
                act_info["activity1"] = self._rules_classify_activity1(
                    signal_text
                ) or "Binding"
            # ── Vague value filter ──
            # Drop records whose value is a pointer/reference or purely qualitative
            value = act_info.get("value", "")
            if value and self._is_vague_or_pointer_value(value):
                return None
            item["Activity_Info"] = act_info

        # Experimental_Conditions
        if "method" in exp_info and not exp_info.get("method"):
            del exp_info["method"]
        # ── MSM auto-correction ──
        # If the value contains MSM-indicative keywords but method says
        # Mass spectrometry, auto-correct to MSM.
        method = exp_info.get("method", "")
        value_text = (act_info.get("value", "") or "").lower() if act_info else ""
        msm_keywords = [
            "first passage time", "pathway flux", "interstate flux",
            "binding pathway", "msm", "markov", "conformational selection",
            "binding mode population", "state transition", "k-means cluster",
        ]
        if method and "mass spectr" in method.lower():
            if any(kw in value_text for kw in msm_keywords):
                exp_info["method"] = "Markov State Model (MSM) analysis"
        if exp_info:
            item["Experimental_Conditions"] = exp_info

        return item

    @staticmethod
    def _is_vague_or_pointer_value(value: str) -> bool:
        """Return True if value is a table-reference or vague qualitative string."""
        if not value:
            return False
        lower = value.lower().strip()
        # Pointer / reference strings
        pointer_phrases = [
            "see table", "see supplementary", "detailed in",
            "listed in table", "reported in si", "as shown in figure",
            "values detailed in", "detailed values",
        ]
        if any(p in lower for p in pointer_phrases):
            return True
        # Vague qualitative strings without any number
        vague_phrases = [
            "higher affinity for gq sequences",
            "higher affinity than",
            "showed higher affinity",
            "preferentially binds",
            "binds g4 with higher",
            "binds preferentially",
        ]
        # Only filter if the string is vague AND contains no numeric measurement
        import re as _re
        # Look for numbers that aren't just part of "G4" or similar abbreviations
        has_measurement_number = bool(_re.search(
            r"(?<![gG])\d+\.?\d*\s*(?:µ[mM]|[mnp]M|kcal|°C|℃|fold|%|\s*M\b)",
            lower
        ))
        if not has_measurement_number and any(p in lower for p in vague_phrases):
            return True
        return False

    @staticmethod
    def _is_absolute_tm_value(value: str, activity2: Optional[str] = None) -> bool:
        """Return True if value is an absolute Tm (not Delta Tm) for Stabilization,
        or if it's a qualitative Stabilization value without any numeric data.

        Absolute Tm values like "Tm=63.7 ℃" or "Tm1=78.2 ℃" are raw melting
        temperatures. The benchmark expects only Delta Tm (ΔTm) values which
        represent the shift caused by ligand binding. This filter drops absolute
        Tm records while preserving Delta Tm records.
        """
        if not value:
            return False
        # Only apply to Stabilization-like activities
        if activity2 and activity2.lower() not in ("stabilization",):
            return False
        lower = value.lower().strip()
        # Check for Delta Tm patterns — these should be KEPT (if they have numbers)
        delta_patterns = [
            r"delta\s*t\s*m", r"δ\s*t\s*m", r"Δ\s*t\s*m",
            r"δtm", r"Δtm", r"dtm",
        ]
        has_delta = False
        for pat in delta_patterns:
            if re.search(pat, lower, re.IGNORECASE):
                has_delta = True
                break
        # If it's a Delta Tm but has no numeric value, drop it
        # (e.g., "Delta Tm (higher than TMPyP4)" is qualitative)
        if has_delta:
            if not re.search(r'\d+\.?\d*', value):
                return True  # Qualitative Delta Tm — drop
            return False  # Quantitative Delta Tm — keep
        # Check for absolute Tm patterns — these should be DROPPED
        # Match "Tm=63.7", "Tm1=78.2", "Tm 2 = 65.3" but not "Delta Tm"
        abs_tm_pattern = r'\btm\s*\d*\s*[=:]\s*\d+'
        if re.search(abs_tm_pattern, lower):
            return True
        return False

    @staticmethod
    def _is_non_g4_method(method: Optional[str], value: Optional[str] = None) -> bool:
        """Return True if the method is not a G4 ligand–nucleic acid endpoint.

        Filters out antiviral assays, electrophysiology, and other off-target
        methods that should not appear in the G4 binding database.
        """
        if not method:
            return False
        lower = method.lower()
        non_g4_methods = [
            "plaque assay", "plaque",
            "western blot", "western",
            "qrt-pcr", "rt-pcr", "real-time pcr",
            "patch clamp", "voltage clamp", "electrophysiol",
            "confocal microscop",
            "primer extension",
            "reporter assay",
            "cell proliferation",          # MTT / SRB proxy without specific assay name
        ]
        for term in non_g4_methods:
            if term in lower:
                return True
        # Also filter by value content for antiviral endpoints
        if value:
            val_lower = value.lower()
            antiviral_kws = [
                "virus yield", "viral replication", "infectious virus",
                "plaque forming", "tcid50", "viral genome copies",
                "antiviral", "e protein expression",
            ]
            for kw in antiviral_kws:
                if kw in val_lower:
                    return True
        return False

    @staticmethod
    def _is_supportive_observable(value: Optional[str]) -> bool:
        """Return True if the value is a supportive observable, not a final endpoint.

        NOE contact counts, rMSD/RMSD simulation quality metrics, and similar
        low-level observables are supporting evidence, not database-worthy records.
        """
        if not value:
            return False
        lower = value.lower().strip()
        supportive_patterns = [
            r'\bnoe\b.*(?:contacts?|restraints?|distance)',  # NOE contacts/restraints
            r'\brmsd?\s*=\s*\d',              # rMSD=0.35 or RMSD=0.35
            r'\brmsf\s*=\s*\d',               # RMSF=...
            r'\bdiffusion\s+coefficient\s*=',  # Diffusion coefficient=...
            r'\bdt?\s*=\s*[\d.]+.*m\^?2/s',   # Dt = 1.45 × 10^-10 m^2/s (DOSY)
            r'\banaphase\s+bridge',            # Anaphase bridges — supporting for DNA Damage
            r'\btotal\s+energy\s*=',           # Total energy from MD — not a benchmark endpoint
            r'\bpotential\s+energy\s*=',       # Potential energy from docking — not benchmark
            r'\brise\s*=\s*[\d.]+',            # Rise=3.43 Å (MD structural param)
            r'\bh[- ]?rise\s*=\s*[\d.]+',      # H-Rise=3.48 Å
            r'\bh[- ]?twist\s*=\s*[\d.]+',     # H-Twist=24.2°
            r'\btwist\s*=\s*[\d.]+',           # Twist=...°
            r'\bstoichiometr',                 # Binding stoichiometries
            r'\bno\s+intercalation',           # 31P NMR rules out intercalation
            r'\brules?\s+out\b.*intercalat',   # rules out intercalation
            r'31p\s+nmr',                      # 31P NMR observations
            r'^population\s*=\s*[\d.]+\s*%$',  # Standalone population % (not combined with binding mode)
            r'\binterstate\s+flux\s+ratio',    # MSM interstate flux ratios (too granular)
            r'\bpathway\s+flux\s*[=:]\s*\d',   # MSM pathway flux percentages
            r'\bmfpt\b',                        # Mean first passage time (MSM detail)
            r'\bmean\s+first\s+passage',        # Mean first passage time
            r'\bbinding\s+mode\s*:\s*\w',       # Qualitative "Binding mode: top stacking" etc.
            r'\bvan\s+der\s+waals\s+energy',    # MM-PBSA VdW decomposition
            r'\bvdw\s+energy\s*=',              # VdW energy component
            r'\bpbtot\b',                       # MM-PBSA PBTOT component
            r'\brelative\s+binding\s+energy',   # Relative (comparison) binding energy
            r'\belectrostatic\s+energy\s*=',    # Electrostatic decomposition
            r'\bsolvation\s+energy\s*=',        # Solvation decomposition
            r'\banti[- ]?proliferative\s+effect', # Qualitative anti-proliferative (no IC50)
            r'\bconformational\s+selection\s+mechanism', # MSM mechanistic description
            r'\bconformational\s+selection\s*\(\d', # "Conformational selection (100%)"
        ]
        for pat in supportive_patterns:
            if re.search(pat, lower):
                return True
        return False

    @staticmethod
    def _is_duplex_control_record(record: Dict[str, Any]) -> bool:
        """Return True if the record is a duplex-control binding measurement.

        SPR and other binding assays often include duplex DNA controls to
        demonstrate G4 selectivity. These are NOT primary G4 endpoints.
        """
        value = (record.get("value") or "").lower()
        # Check for explicit duplex markers in value
        duplex_kws = ["duplex dna", "duplex rna", "(duplex)", "ds-dna", "dsdna"]
        if any(kw in value for kw in duplex_kws):
            return True
        return False

    @staticmethod
    def _is_derived_ratio_value(value: Optional[str]) -> bool:
        """Return True if the value is a derived selectivity ratio, not a primary endpoint.

        Q/D ratios, selectivity indices, and fold-selectivity metrics are derived
        from primary binding constants and should not be separate records.
        """
        if not value:
            return False
        lower = value.lower().strip()
        derived_patterns = [
            r'\bq/d\s+ratio\s*=',            # Q/D ratio=13.8
            r'\bselectivity\s+index\s*=',     # Selectivity index=...
            r'\bselectivity\s+ratio\s*=',     # Selectivity ratio=...
            r'\bfold[\s-]+selectivity\s*=',    # fold-selectivity=...
        ]
        for pat in derived_patterns:
            if re.search(pat, lower):
                return True
        return False

    def _normalize_sequence_type(self, seq_type: Any) -> Optional[str]:
        """Normalize sequence type to valid enum values."""
        if seq_type is None:
            return None
        txt = str(seq_type).strip()
        for valid in VALID_SEQUENCE_TYPES:
            if txt.lower() == valid.lower():
                return valid
        return txt if txt else None

    def _normalize_activity1(self, activity: Any) -> Optional[str]:
        """Normalize primary activity to valid enum values."""
        if activity is None:
            return None
        txt = str(activity).strip()
        canonical_map = {
            "binding": "Interaction",
            "stabilization": "Interaction",
            "selectivity": "Interaction",
            "fluorescence response": "Interaction",
            "unfolding": "Interaction",
            "folding": "Interaction",
            "thermal stabilization": "Interaction",
            "competition": "Interaction",
            "displacement": "Interaction",
            "cellular activity": "Activity at Cellular Level",
            "cytotoxicity": "Activity at Cellular Level",
            "inhibition": "Activity at Molecular Level",
            "cleavage": "Activity at Molecular Level",
        }
        mapped = canonical_map.get(txt.lower())
        if mapped:
            return mapped
        for valid in VALID_ACTIVITY1:
            if txt.lower() == valid.lower():
                return valid
        return txt if txt else None

    @staticmethod
    def _normalize_activity2(activity: Any) -> Optional[str]:
        """Normalize endpoint label to the benchmark's flatter activity2 space."""
        if activity is None:
            return None
        txt = str(activity).strip()
        if not txt:
            return None
        canonical_map = {
            "kd": "Binding",
            "ka": "Binding",
            "kb": "Binding",
            "affinity": "Binding",
            "δtm": "Stabilization",
            "Δtm": "Stabilization",
            "thermal stabilization": "Stabilization",
            # Receptor-inhibition / hERG-style panels → Gene Expression
            "receptor inhibition": "Gene Expression",
            "herg inhibition": "Gene Expression",
            "herg": "Gene Expression",
            "gene expression": "Gene Expression",
            "inhibition": "Gene Expression",
            # Telomere-damage readouts → DNA Damage
            "dna damage": "DNA Damage",
            "telomere damage": "DNA Damage",
            "telomere dysfunction": "DNA Damage",
            # Cellular viability → Cytotoxicity
            "cell viability": "Cytotoxicity",
            "cytotoxic": "Cytotoxicity",
            "growth inhibition": "Cytotoxicity",
        }
        return canonical_map.get(txt.lower(), txt)

    def _normalize_method(self, method: Any) -> Optional[str]:
        """Normalize experimental method using domain rules."""
        if method is None:
            return None
        txt = str(method).strip()
        if not txt:
            return None
        classified = self.rules.classify_method(txt)
        return classified or txt

    def _infer_sequence_type(self, sequence: str) -> Optional[str]:
        """Infer sequence type from the sequence string itself."""
        if not sequence:
            return None
        upper = sequence.upper()
        if "U" in upper:
            return "RNA"
        if re.search(r"\b[AGCT]+\b", upper):
            return "DNA"
        return "Unknown"

    def _rules_classify_activity1(self, text: str) -> Optional[str]:
        """Use domain rules to classify activity1 from free text."""
        return self.rules.classify_activity1(text)

    # ------------------------------------------------------------------
    # Paper metadata
    # ------------------------------------------------------------------

    def _resolve_paper_metadata(
        self,
        source_path: str,
        paper_text: Optional[str],
        document_metadata: Optional[dict],
        existing_metadata: Optional[dict],
    ) -> Dict[str, Any]:
        """Resolve paper metadata from all available sources."""
        meta: Dict[str, Any] = {}

        if isinstance(existing_metadata, dict):
            title = existing_metadata.get("Paper_Title")
            if title:
                meta["Paper_Title"] = str(title).strip()
            doi = existing_metadata.get("DOI")
            if doi:
                meta["DOI"] = str(doi).strip()

        if not meta and document_metadata:
            title = document_metadata.get("title")
            if title:
                meta["Paper_Title"] = str(title).strip()
            doi = document_metadata.get("doi")
            if doi:
                meta["DOI"] = str(doi).strip()

        if not meta:
            title = self._extract_title_from_paper_text(paper_text)
            if title:
                meta["Paper_Title"] = title

        if not meta.get("DOI"):
            doi = self._extract_doi_from_text(paper_text) if paper_text else None
            if doi:
                meta["DOI"] = doi

        if not meta.get("Paper_Title") and source_path:
            meta["Paper_Title"] = os.path.splitext(os.path.basename(source_path))[0]

        return meta

    @staticmethod
    def _resolve_paper_id(source_path: str, paper_metadata: Dict[str, Any]) -> str:
        """Resolve benchmark paper_id from source path or metadata."""
        candidates = [
            os.path.splitext(os.path.basename(source_path or ""))[0],
            os.path.basename(os.path.dirname(source_path or "")),
            str((paper_metadata or {}).get("Paper_Title") or ""),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            match = re.search(r"(\d+)", candidate)
            if match:
                return match.group(1)
        return os.path.splitext(os.path.basename(source_path or ""))[0] or "unknown"

    @staticmethod
    def _extract_title_from_paper_text(paper_text: Optional[str]) -> Optional[str]:
        """Extract title from paper text (first non-empty line heuristics)."""
        if not paper_text:
            return None
        lines = [
            line.strip()
            for line in paper_text.splitlines()
            if line.strip() and len(line.strip()) > 10
        ]
        for line in lines[:5]:
            if re.match(r"^[A-Z][A-Za-z0-9 ,:;'\-()&%§]+$", line):
                if len(line) < 200:
                    return line
        return None

    @staticmethod
    def _extract_doi_from_text(text: str) -> Optional[str]:
        """Extract first DOI from text using common patterns."""
        if not text:
            return None
        patterns = [
            r"10\.\d{4,}/[^\s\"\'<>]+",
            r"doi[:\s]+(10\.\d{4,}/[^\s\"\'<>]+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                doi = m.group(1) if m.lastindex else m.group(0)
                doi = re.sub(r"[.,;)\]]+$", "", doi)
                if 10 <= len(doi) <= 100:
                    return doi
        return None

    @staticmethod
    def _empty_lab_schema(paper_metadata: Optional[Dict[str, Any]] = None) -> dict:
        meta = paper_metadata or {}
        return {
            "Paper_Metadata": {
                "Paper_Title": meta.get("Paper_Title"),
                "DOI": meta.get("DOI"),
            },
            "items": [],
        }

    # ------------------------------------------------------------------
    # String helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_nucleotide_sequence(text: str) -> bool:
        """Return True if *text* appears to be an actual nucleotide string.

        A string is treated as a nucleotide sequence when it consists
        predominantly of A, T, G, C, U characters (allowing common
        modification prefixes like 'd', 'r', brackets, hyphens, and
        spaces used in repeat notation such as '[d-(TTAGGGT)]4').
        Short purely-alphabetic strings that look like aliases (≤ 8 chars
        and not matching the nucleotide charset) are rejected.
        """
        if not text:
            return False
        # Strip common notational noise before testing the core characters.
        stripped = re.sub(r"[^A-Za-z]", "", text).upper()
        if not stripped:
            return False
        nucleotides = set("ATGCU")
        non_nuc = [ch for ch in stripped if ch not in nucleotides]
        # Allow up to 10% non-nucleotide characters to tolerate modification
        # markers (e.g. 'd' prefix in 'd(TTAGGGT)').
        ratio = len(non_nuc) / len(stripped)
        if ratio > 0.10:
            return False
        # Require a minimum length so single-letter or very short strings
        # (like 'G', 'AT') are not mistakenly treated as sequences when they
        # could be labels.
        return len(stripped) >= 4

    @staticmethod
    def _normalize_output_synonyms(value: Any) -> Optional[List[str]]:
        """Normalize ligand synonyms for final output."""
        if value is None:
            return None
        if isinstance(value, list):
            cleaned = [str(v).strip() for v in value if str(v).strip()]
            return cleaned or None
        text = str(value).strip()
        if not text:
            return None
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text.replace("'", '"'))
                if isinstance(parsed, list):
                    cleaned = [str(v).strip() for v in parsed if str(v).strip()]
                    return cleaned or None
            except Exception:
                pass
        parts = [part.strip() for part in text.split(";") if part.strip()]
        return parts or [text]

    @staticmethod
    def _clean_optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
