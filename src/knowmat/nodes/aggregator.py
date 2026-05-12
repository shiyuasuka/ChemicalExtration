"""
Aggregation Agent (Stage 1 of Two-Stage Manager)

This agent's SOLE responsibility is to merge data from multiple extraction runs
into a single comprehensive dataset. It does NOT validate, check for hallucinations,
or generate review guides — that's Stage 2's job.

Responsibilities:
- Select base run by confidence score
- Merge G4 binding records from all runs
- Handle conflicts by preferring high-confidence values
- Preserve all data fields
- Simple, fast, rule-based merging

NOT responsible for:
- Hallucination detection/correction (Stage 2)
- ML-ready format validation (Stage 2)
- Review guide generation (Stage 2)
- Confidence scoring (Flagging Agent)
"""

import json
from typing import Dict, Any, List
from knowmat.states import KnowMatState, load_run_extraction


def _binding_signature(binding: dict) -> tuple:
    """Generate a deduplication key for a G4 binding record.

    ``value`` is intentionally included so that records sharing the same
    ligand + sequence + method + activity but with *different* measured
    endpoints (e.g. Delta Tm2, Delta Tm3, Delta Tm4, Delta Tm5 from a
    DSC table, or separate MD metrics such as Rise vs H-twist vs Docking
    Score) are **not** collapsed into a single record during aggregation.
    """
    ligand_id = binding.get("ligand_id") or ""
    ligand_name = binding.get("ligand_name") or ""
    sequence = binding.get("sequence") or ""
    sequence_name = binding.get("sequence_name") or ""
    activity1 = binding.get("activity1") or ""
    activity2 = binding.get("activity2") or ""
    method = binding.get("method") or ""
    # Normalise the value key: strip whitespace and lowercase so that minor
    # formatting differences between runs don't prevent true duplicates from
    # being merged while still preserving genuinely distinct endpoints.
    value = (binding.get("value") or "").strip().lower()
    return (
        ligand_id,
        ligand_name,
        sequence,
        sequence_name,
        activity1,
        activity2,
        method,
        value,
    )


def _non_empty_merge(existing: Any, incoming: Any) -> Any:
    """Prefer non-empty value over empty/None."""
    if not existing or existing == "" or existing == [] or existing is None:
        return incoming
    if not incoming or incoming == "" or incoming is None:
        return existing
    # Prefer longer string (more detail) for text fields
    if isinstance(existing, str) and isinstance(incoming, str):
        return existing if len(existing) >= len(incoming) else incoming
    # Prefer existing for other types
    return existing if existing else incoming


def _merge_binding(existing: dict, incoming: dict) -> dict:
    """Merge two binding records, preferring non-empty / more detailed values."""
    merged = dict(existing)
    for key in [
        "ligand_id", "ligand_name", "ligand_name_std", "ligand_synonyms",
        "counter_ion", "metal_ion",
        "sequence", "sequence_name", "sequence_type",
        "activity1", "activity2", "value",
        "method", "buffer", "sample_concentration", "instrument",
        "comments", "context",
    ]:
        existing_val = merged.get(key)
        incoming_val = incoming.get(key)
        merged[key] = _non_empty_merge(existing_val, incoming_val)
    return merged


def aggregate_runs(state: KnowMatState) -> Dict[str, Any]:
    """Merge multiple extraction runs into a single comprehensive dataset.

    Uses a simple, reliable strategy:
    1. Select the highest-confidence run as the base
    2. Deduplicate binding records across runs (by ligand_id + sequence + method + activity)
    3. For each duplicate, merge fields preferring non-empty / more detailed values
    4. Add unique records from all runs

    This is purely merging — no validation, no hallucination checks.
    Those happen in Stage 2 (Validation Agent).

    Parameters
    ----------
    state : KnowMatState
        Current workflow state containing run_results

    Returns
    -------
    dict
        Updates containing:
        - aggregated_data: Merged g4_bindings from all runs
        - aggregation_notes: Brief explanation of merge strategy
    """
    run_results = state.get("run_results", [])

    if not run_results:
        # No runs to aggregate — use latest extraction
        latest_data = state.get("latest_extracted_data", {})
        return {
            "aggregated_data": latest_data,
            "aggregation_notes": "No evaluation runs. Using latest extraction.",
        }

    if len(run_results) == 1:
        single_run = run_results[0]
        return {
            "aggregated_data": load_run_extraction(single_run),
            "aggregation_notes": (
                f"Single run (ID {single_run.get('run_id')}, "
                f"confidence {single_run.get('confidence_score', 0.0):.2f})."
            ),
        }

    # Sort runs by confidence (highest first)
    sorted_runs = sorted(
        run_results,
        key=lambda r: r.get("confidence_score", 0.0),
        reverse=True,
    )

    print(f"\nAggregation Stage 1:")
    print(f"  Merging {len(run_results)} extraction runs...")
    confidences = [f"{r.get('confidence_score', 0.0):.2f}" for r in sorted_runs]
    print(f"  Run confidences: {confidences}")

    base_run = sorted_runs[0]
    base_data = load_run_extraction(base_run)
    base_bindings = base_data.get("g4_bindings", [])

    print(f"  Base run: ID {base_run.get('run_id')} (confidence {base_run.get('confidence_score', 0.0):.2f})")
    print(f"  Base g4_bindings: {len(base_bindings)}")

    # Build a signature -> binding map, starting from base
    merged_map: Dict[tuple, dict] = {}
    for binding in base_bindings:
        if not isinstance(binding, dict):
            continue
        sig = _binding_signature(binding)
        merged_map[sig] = dict(binding)

    # Merge bindings from other runs
    bindings_added = 0
    bindings_merged = 0

    for run in sorted_runs[1:]:
        run_data = load_run_extraction(run)
        run_bindings = run_data.get("g4_bindings", [])

        for binding in run_bindings:
            if not isinstance(binding, dict):
                continue
            sig = _binding_signature(binding)

            if sig not in merged_map:
                merged_map[sig] = dict(binding)
                bindings_added += 1
            else:
                merged_map[sig] = _merge_binding(merged_map[sig], binding)
                bindings_merged += 1

    # Convert map back to list
    merged_bindings = list(merged_map.values())
    total_bindings = len(merged_bindings)

    merged_data = {"g4_bindings": merged_bindings}

    print(f"  Merged result: {total_bindings} g4_bindings")
    print(f"  Added from other runs: +{bindings_added} new bindings, merged {bindings_merged} duplicates")

    # Build aggregation notes
    notes = (
        f"Aggregation strategy: Used Run {base_run.get('run_id')} "
        f"(confidence {base_run.get('confidence_score', 0.0):.2f}) as base with "
        f"{len(base_bindings)} g4_bindings. "
        f"Merged data from {len(run_results) - 1} other runs, adding "
        f"{bindings_added} new bindings and merging {bindings_merged} duplicates. "
        f"Total final g4_bindings: {total_bindings}."
    )

    print(f"  ✓ Aggregation complete (no validation — rule-based)")

    return {
        "aggregated_data": merged_data,
        "aggregation_notes": notes,
    }
