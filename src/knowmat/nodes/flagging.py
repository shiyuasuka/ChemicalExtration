"""
LLM-based node for assessing final extraction quality and determining review needs.

The flagging agent evaluates the manager's aggregation result, considers the
complexity of issues, quality of corrections made, and assigns a confidence
score with review recommendations.
"""

from typing import Dict, Any

from knowmat.extractors import flagging_extractor, FlaggingFeedback
from knowmat.prompt_loader import load_yaml_templates_required
from knowmat.states import KnowMatState

_FLAGGING_TEMPLATES = load_yaml_templates_required(
    "flagging.yaml",
    (
        "intro",
        "run_stats_header",
        "manager_header",
        "review_header",
        "completeness_header",
        "task_header",
        "output_requirements",
    ),
)


def assess_final_quality(state: KnowMatState) -> Dict[str, Any]:
    """Use LLM to assess the final aggregated extraction quality.

    Parameters
    ----------
    state: KnowMatState
        The current workflow state containing aggregation results and run data.

    Returns
    -------
    dict
        Updates containing ``final_confidence_score``, ``confidence_rationale``,
        ``needs_human_review``, and ``flag``.
    """
    run_results = state.get("run_results", [])
    aggregation_rationale = state.get("aggregation_rationale", "")
    human_review_guide = state.get("human_review_guide", "")
    final_data = state.get("final_data", {})

    if not run_results:
        return {
            "final_confidence_score": 0.5,
            "confidence_rationale": "No evaluation runs available for assessment.",
            "needs_human_review": True,
            "flag": True,
        }

    t = _FLAGGING_TEMPLATES
    flagging_prompt = t.get("intro", "") + "\n\n"

    # Add run summary statistics WITH CORRECTION CONTEXT
    flagging_prompt += t.get("run_stats_header", "")

    if run_results:
        scores = [run.get("confidence_score", 0.0) for run in run_results]
        avg_confidence = sum(scores) / len(scores)
        min_confidence = min(scores)
        max_confidence = max(scores)

        flagging_prompt += f"Number of Runs: {len(run_results)}\n"
        flagging_prompt += f"Average Run Confidence: {avg_confidence:.2f}\n"
        flagging_prompt += f"Confidence Range: {min_confidence:.2f} - {max_confidence:.2f}\n"
        flagging_prompt += (
            f"Confidence Spread: {max_confidence - min_confidence:.2f} (consistency indicator)\n\n"
        )

        total_missing = sum(len(run.get("missing_fields") or []) for run in run_results)
        total_hallucinated = sum(len(run.get("hallucinated_fields") or []) for run in run_results)

        flagging_prompt += "ORIGINAL EXTRACTION ISSUES (Before Manager Corrections):\n"
        flagging_prompt += f"- Total missing fields across runs: {total_missing}\n"
        flagging_prompt += f"- Total hallucinated fields across runs: {total_hallucinated}\n"

        flagging_prompt += "\nHallucination Breakdown by Run:\n"
        for i, run in enumerate(run_results, 1):
            h_fields = run.get("hallucinated_fields") or []
            if h_fields:
                flagging_prompt += f"  Run {i}: {len(h_fields)} hallucinations\n"
                for j, h in enumerate(h_fields[:3], 1):
                    flagging_prompt += f"    {j}. {h[:100]}{'...' if len(h) > 100 else ''}\n"
                if len(h_fields) > 3:
                    flagging_prompt += f"    ... and {len(h_fields) - 3} more\n"
        flagging_prompt += "\n"

    # Add manager's assessment WITH CORRECTION ANALYSIS
    flagging_prompt += t.get("manager_header", "")

    flagging_prompt += f"Manager's Aggregation Rationale:\n"
    flagging_prompt += f"{'-' * 40}\n{aggregation_rationale}\n\n"

    # Add human review guide ANALYSIS
    flagging_prompt += t.get("review_header", "")

    flagging_prompt += f"Human Review Guide:\n"
    flagging_prompt += f"{'-' * 40}\n{human_review_guide}\n\n"

    # Add final data completeness METRICS (G4 ligand domain)
    flagging_prompt += t.get("completeness_header", "")

    g4_bindings = final_data.get("g4_bindings", [])
    flagging_prompt += f"Number of G4 Binding Records: {len(g4_bindings)}\n"

    if g4_bindings:
        total_ligand_names = sum(1 for b in g4_bindings if b.get("ligand_name"))
        total_sequences = sum(1 for b in g4_bindings if b.get("sequence"))
        total_sequence_names = sum(1 for b in g4_bindings if b.get("sequence_name"))
        total_values = sum(1 for b in g4_bindings if b.get("value"))
        total_methods = sum(1 for b in g4_bindings if b.get("method"))

        flagging_prompt += f"Records with ligand_name: {total_ligand_names}/{len(g4_bindings)}\n"
        flagging_prompt += f"Records with sequence: {total_sequences}/{len(g4_bindings)}\n"
        flagging_prompt += f"Records with sequence_name: {total_sequence_names}/{len(g4_bindings)}\n"
        flagging_prompt += f"Records with measurement value: {total_values}/{len(g4_bindings)}\n"
        flagging_prompt += f"Records with method: {total_methods}/{len(g4_bindings)}\n"
        flagging_prompt += "\n"

        flagging_prompt += "COMPLETENESS INTERPRETATION:\n"
        flagging_prompt += "- This stage intentionally focuses on five core fields only\n"
        flagging_prompt += "- Missing derived fields should not reduce confidence by themselves\n\n"

        # Sample binding record for richness check
        if g4_bindings:
            sample = g4_bindings[0]
            sample_ligand = sample.get("ligand_name") or sample.get("ligand_id") or "Unknown"
            sample_seq = sample.get("sequence_name") or sample.get("sequence", "Unknown")[:20]
            flagging_prompt += f"Sample Binding Record ({sample_ligand} / {sample_seq}):\n"
            flagging_prompt += f"  value: {'Present' if sample.get('value') else 'Missing'}\n"
            flagging_prompt += f"  method: {'Present' if sample.get('method') else 'Missing'}\n"
            flagging_prompt += f"  sequence_name: {'Present' if sample.get('sequence_name') else 'Missing'}\n"
    else:
        flagging_prompt += "WARNING: No g4_bindings extracted! This indicates major failure.\n"

    flagging_prompt += "\n"

    # Final instructions
    flagging_prompt += t.get("task_header", "")
    flagging_prompt += t.get("output_requirements", "")

    # Invoke the flagging extractor
    result = flagging_extractor.invoke(flagging_prompt)
    response = result.get("responses", [None])[0]

    if response is None:
        avg_confidence = (
            sum(run.get("confidence_score", 0.0) for run in run_results) / len(run_results)
            if run_results
            else 0.0
        )
        return {
            "final_confidence_score": avg_confidence,
            "confidence_rationale": "Fallback assessment: averaged run confidence scores.",
            "needs_human_review": avg_confidence < 0.8,
            "flag": avg_confidence < 0.8,
        }

    if isinstance(response, FlaggingFeedback):
        flagging_dict = response.model_dump()
    else:
        flagging_dict = dict(response)

    final_confidence = flagging_dict.get("final_confidence_score", 0.0)
    confidence_rationale = flagging_dict.get("confidence_rationale", "")
    needs_review = flagging_dict.get("needs_human_review", False)

    return {
        "final_confidence_score": final_confidence,
        "confidence_rationale": confidence_rationale,
        "needs_human_review": needs_review,
        "flag": needs_review,
    }
