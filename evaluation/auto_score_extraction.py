#!/usr/bin/env python3
"""
Detailed auto scoring for flat G4 extraction results vs manual annotations.

This scorer compares:
- predicted files under ``data/processed/<paper_id>/<paper_id>_extraction.json``
- ground-truth files under ``学校工程结果/paper_<paper_id>.json``

Both sides are expected to follow the flat schema:
{
  "paper_id": "...",
  "record_count": 0,
  "records": [...]
}

Outputs:
- evaluation/scoring_report.json
- evaluation/scoring_summary.md
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


FIELD_NAMES = [
    "ligand_id",
    "ligand_name",
    "ligand_name_std",
    "ligand_synonyms",
    "sequence",
    "sequence_name",
    "sequence_type",
    "activity1",
    "activity2",
    "method",
    "value",
    "buffer",
    "sample_concentration",
    "instrument",
    "comments",
    "counter_ion",
    "metal_ion",
    "context",
]

CORE_FIELDS = [
    "ligand_id",
    "ligand_name",
    "sequence",
    "sequence_name",
    "activity1",
    "activity2",
    "method",
    "value",
]

METHOD_ALIASES = {
    "differentialscanningcalorimetrydsc": "differentialscanningcalorimetrydsc",
    "differentialscanningcalorimetry": "differentialscanningcalorimetrydsc",
    "dsc": "differentialscanningcalorimetrydsc",
    "nuclearmagneticresonancenmr": "nuclearmagneticresonancenmr",
    "nmrspectroscopy": "nuclearmagneticresonancenmr",
    "nmr": "nuclearmagneticresonancenmr",
    "moleculedynamicsmdsimulation": "moleculedynamicsmdsimulation",
    "moleculardynamicssimulation": "moleculedynamicsmdsimulation",
    "mdsimulation": "moleculedynamicsmdsimulation",
    "moleculardynamicsmd": "moleculedynamicsmdsimulation",
    "moleculardynamics": "moleculedynamicsmdsimulation",
    "surfaceplasmonresonancespr": "surfaceplasmonresonancespr",
    "spr": "surfaceplasmonresonancespr",
    "circulardichroismcd": "circulardichroismcd",
    "cd": "circulardichroismcd",
    "fluorescencespectroscopyfl": "fluorescencespectroscopyfl",
    "fluorescencespectroscopy": "fluorescencespectroscopyfl",
    "fluorescencetitration": "fluorescencespectroscopyfl",
    "fluorimetry": "fluorescencespectroscopyfl",
    "uvvisabsorptionspectroscopy": "uvvisabsorptionspectroscopy",
    "uvvisabsorption": "uvvisabsorptionspectroscopy",
    "uvvis": "uvvisabsorptionspectroscopy",
    "markovstatemodelmsmanalysis": "markovstatemodelmsmanalysis",
    "markovstatemodel": "markovstatemodelmsmanalysis",
    "msm": "markovstatemodelmsmanalysis",
    "moleculedockingcalculation": "moleculedockingcalculation",
    "moleculardocking": "moleculedockingcalculation",
    "docking": "moleculedockingcalculation",
    "glidexpdocking": "moleculedockingcalculation",
    "molecularmechanicspoissonboltzmannsurfaceareamm-pbsa": "molecularmechanicspoissonboltzmannsurfaceareamm-pbsa",
    "mmpbsa": "molecularmechanicspoissonboltzmannsurfaceareamm-pbsa",
    "mm-pbsa": "molecularmechanicspoissonboltzmannsurfaceareamm-pbsa",
    "isothermaltitrationcalorimetryitc": "isothermaltitrationcalorimetryitc",
    "isothermaltitrationcalorimetry": "isothermaltitrationcalorimetryitc",
    "itc": "isothermaltitrationcalorimetryitc",
    "telomericrepeatamplificationprotocoltrapassay": "telomericrepeatamplificationprotocoltrapassay",
    "trapassay": "telomericrepeatamplificationprotocoltrapassay",
    "trap": "telomericrepeatamplificationprotocoltrapassay",
    "sulforhodaminebassaysrb": "sulforhodaminebassaysrb",
    "srb": "sulforhodaminebassaysrb",
    "sulforhodamineb": "sulforhodaminebassaysrb",
    "chromatinimmunoprecipitationchip": "chromatinimmunoprecipitationchip",
    "chip": "chromatinimmunoprecipitationchip",
    "immunofluorescenceif": "immunofluorescenceif",
    "immunofluorescence": "immunofluorescenceif",
    "fluorescentinsituhybridizationfish": "fluorescentinsituhybridizationfish",
    "fish": "fluorescentinsituhybridizationfish",
    "receptorinhibitionstudy": "receptorinhibitionstudy",
    "receptorinhibition": "receptorinhibitionstudy",
}

ACTIVITY1_ALIASES = {
    "interaction": "interaction",
    "activityatmolecularlevel": "activityatmolecularlevel",
    "activityatcellularlevel": "activityatcellularlevel",
    "binding": "interaction",
    "stabilization": "interaction",
    "cytotoxicity": "activityatcellularlevel",
}

ACTIVITY2_ALIASES = {
    "δtm": "stabilization",
    "Δtm": "stabilization",
    "deltatm": "stabilization",
    "binding": "binding",
    "stabilization": "stabilization",
    "recognition": "recognition",
    "enzyme": "enzyme",
    "geneexpression": "geneexpression",
    "dnadamage": "dnadamage",
    "cytotoxicity": "cytotoxicity",
    "kb": "binding",
    "kd": "binding",
}


@dataclass
class FlatRecord:
    paper_id: str
    index: int
    raw: Dict[str, Any]

    def get(self, field: str) -> Any:
        return self.raw.get(field)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def canonical_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, list):
        parts = [canonical_text(v) for v in value]
        parts = [p for p in parts if p]
        return "|".join(sorted(parts)) if parts else None
    text = normalize_whitespace(str(value))
    if not text:
        return None
    text = text.replace("μ", "u").replace("µ", "u")
    text = text.replace("–", "-").replace("—", "-")
    return text


def compact_token(value: Any) -> Optional[str]:
    text = canonical_text(value)
    if text is None:
        return None
    cleaned = re.sub(r"[^a-zA-Z0-9+\-]+", "", text.lower())
    return cleaned or None


def normalize_method(value: Any) -> Optional[str]:
    token = compact_token(value)
    if token is None:
        return None
    return METHOD_ALIASES.get(token, token)


def normalize_activity1(value: Any) -> Optional[str]:
    token = compact_token(value)
    if token is None:
        return None
    return ACTIVITY1_ALIASES.get(token, token)


def normalize_activity2(value: Any) -> Optional[str]:
    token = compact_token(value)
    if token is None:
        return None
    return ACTIVITY2_ALIASES.get(token, token)


def normalize_sequence(value: Any) -> Optional[str]:
    text = canonical_text(value)
    if text is None:
        return None
    return re.sub(r"[^A-Za-z0-9]", "", text).upper() or None


def normalize_value(value: Any) -> Optional[str]:
    text = canonical_text(value)
    if text is None:
        return None
    # Normalize Greek / Unicode symbols
    text = text.replace("Delta", "delta").replace("DELTA", "delta")
    text = text.replace("Δ", "delta").replace("δ", "delta")
    text = text.replace("°C", "C").replace("℃", "C").replace("°c", "C")
    # Normalize exponent notation: 10e7 / 10^7 / 10E7 -> e7
    text = re.sub(r"10[\^eE]([+-]?\d+)", r"e\1", text)
    text = re.sub(r"x\s*10\s*[\^]?\s*([+-]?\d+)", r"e\1", text, flags=re.IGNORECASE)
    # Normalise common IC50 / Kd prefixes: IC50= / Kd = / KD= / Ka= / Kb=
    text = re.sub(r"\b(IC50|Kd|KD|Ka|Kb|KA|KB|kd|ka)\s*=\s*", r"\1=", text, flags=re.IGNORECASE)
    # Collapse whitespace last
    return re.sub(r"\s+", "", text.lower()) or None


def _value_tokens(value: Any) -> List[str]:
    """Return all numeric tokens from a value string, handling semicolon-separated entries."""
    text = canonical_text(value)
    if text is None:
        return []
    return re.findall(r"[<>]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?", text)


def normalize_field(field: str, value: Any) -> Optional[str]:
    if field == "method":
        return normalize_method(value)
    if field == "activity1":
        return normalize_activity1(value)
    if field == "activity2":
        return normalize_activity2(value)
    if field == "sequence":
        return normalize_sequence(value)
    if field == "ligand_synonyms":
        return canonical_text(value)
    if field == "value":
        return normalize_value(value)
    return compact_token(value)


def field_exact(field: str, gt_value: Any, pred_value: Any) -> bool:
    gt_norm = normalize_field(field, gt_value)
    pred_norm = normalize_field(field, pred_value)
    if gt_norm == pred_norm:
        return True
    # Treat computational simulation methods as equivalent for field accuracy
    if field == "method" and gt_norm and pred_norm:
        if gt_norm in COMPUTATIONAL_METHOD_GROUP and pred_norm in COMPUTATIONAL_METHOD_GROUP:
            return True
    return False


def nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return any(nonempty(v) for v in value)
    return bool(str(value).strip())


def soft_value_match(gt_value: Any, pred_value: Any) -> bool:
    gt_norm = normalize_value(gt_value)
    pred_norm = normalize_value(pred_value)
    if gt_norm == pred_norm:
        return True
    # Numeric token overlap: all GT numbers appear in pred (handles partial matches
    # when GT merges multiple values with ';' but pred splits them into separate records)
    gt_nums = _value_tokens(gt_value)
    pred_nums = _value_tokens(pred_value)
    if gt_nums and pred_nums:
        # Exact list equality
        if gt_nums == pred_nums:
            return True
        # Pred's numbers are a subset of GT's (GT has multi-value, pred split one out)
        pred_set = set(pred_nums)
        if pred_set and pred_set.issubset(set(gt_nums)):
            return True
    return False


def _sequence_match(gt: FlatRecord, pred: FlatRecord) -> bool:
    """Return True when sequences are considered equivalent.

    Handles the common case where a pipeline record stores the sequence *name*
    (e.g. 'ZGQ1') in the ``sequence`` field instead of the nucleotide string,
    but the GT record carries the full nucleotide sequence.  In that case we
    fall back to comparing ``sequence_name`` on both sides.
    """
    gt_seq = normalize_sequence(gt.get("sequence"))
    pred_seq = normalize_sequence(pred.get("sequence"))
    if gt_seq and pred_seq:
        if gt_seq == pred_seq:
            return True
        # Fallback: if pred_seq looks like a name (no U/T bases typical of
        # nucleotide strings, or ≤8 chars), compare via sequence_name instead.
        nucleotide_re = re.compile(r"^[ATGCU]+$", re.IGNORECASE)
        pred_is_name = not nucleotide_re.match(pred_seq) or len(pred_seq) <= 8
        if pred_is_name:
            gt_name = compact_token(gt.get("sequence_name"))
            pred_name = compact_token(pred.get("sequence_name"))
            if gt_name and pred_name and gt_name == pred_name:
                return True
        return False
    # Both null → equal; one null → mismatch handled outside
    return gt_seq == pred_seq


COMPUTATIONAL_METHOD_GROUP = {
    "moleculedynamicsmdsimulation",
    "moleculedockingcalculation",
    "molecularmechanicspoissonboltzmannsurfaceareamm-pbsa",
    "markovstatemodelmsmanalysis",
}


def record_cost(gt: FlatRecord, pred: FlatRecord) -> float:
    cost = 0.0

    gt_ligand_id = normalize_field("ligand_id", gt.get("ligand_id"))
    pred_ligand_id = normalize_field("ligand_id", pred.get("ligand_id"))
    if gt_ligand_id and pred_ligand_id:
        cost += 0.0 if gt_ligand_id == pred_ligand_id else 10.0
    else:
        cost += 0.0 if field_exact("ligand_name", gt.get("ligand_name"), pred.get("ligand_name")) else 3.0

    # Sequence field — use smarter matching with name-based fallback
    gt_seq_has = nonempty(gt.get("sequence"))
    pred_seq_has = nonempty(pred.get("sequence"))
    if gt_seq_has and pred_seq_has:
        if not _sequence_match(gt, pred):
            cost += 7.0
    elif gt_seq_has != pred_seq_has:
        cost += 2.0

    for field, mismatch_penalty, missing_penalty in [
        ("sequence_name", 4.0, 1.0),
        ("activity1", 6.0, 2.0),
        ("activity2", 6.0, 2.0),
        ("method", 5.0, 1.5),
    ]:
        gt_has = nonempty(gt.get(field))
        pred_has = nonempty(pred.get(field))
        if gt_has and pred_has:
            if not field_exact(field, gt.get(field), pred.get(field)):
                # Reduce penalty when both methods are computational simulations
                # (GT labels docking/MD/MM-PBSA interchangeably across papers)
                if field == "method":
                    gt_method = normalize_method(gt.get("method"))
                    pred_method = normalize_method(pred.get("method"))
                    if gt_method in COMPUTATIONAL_METHOD_GROUP and pred_method in COMPUTATIONAL_METHOD_GROUP:
                        cost += 1.0  # small penalty to still prefer exact match
                        continue
                cost += mismatch_penalty
        elif gt_has != pred_has:
            cost += missing_penalty

    gt_value_has = nonempty(gt.get("value"))
    pred_value_has = nonempty(pred.get("value"))
    if gt_value_has and pred_value_has:
        if soft_value_match(gt.get("value"), pred.get("value")):
            cost += 0.0
        else:
            cost += 5.0  # reduced from 7.0: value format diverges often between GT and pred
    elif gt_value_has != pred_value_has:
        cost += 2.5

    # Small penalties on supportive fields help choose the better alignment when
    # core fields tie, but they should not dominate matching.
    for field in ["buffer", "sample_concentration", "instrument"]:
        gt_has = nonempty(gt.get(field))
        pred_has = nonempty(pred.get(field))
        if gt_has and pred_has:
            if not field_exact(field, gt.get(field), pred.get(field)):
                cost += 0.5
        elif gt_has != pred_has:
            cost += 0.25

    return cost


def greedy_match_records(
    gt_records: List[FlatRecord],
    pred_records: List[FlatRecord],
    max_cost: float,
) -> Tuple[List[Tuple[int, int, float]], List[int], List[int]]:
    candidates: List[Tuple[float, int, int]] = []
    for gi, gt in enumerate(gt_records):
        for pi, pred in enumerate(pred_records):
            cost = record_cost(gt, pred)
            if cost <= max_cost:
                candidates.append((cost, gi, pi))

    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    matched_gt = set()
    matched_pred = set()
    pairs: List[Tuple[int, int, float]] = []
    for cost, gi, pi in candidates:
        if gi in matched_gt or pi in matched_pred:
            continue
        matched_gt.add(gi)
        matched_pred.add(pi)
        pairs.append((gi, pi, cost))

    unmatched_gt = [i for i in range(len(gt_records)) if i not in matched_gt]
    unmatched_pred = [i for i in range(len(pred_records)) if i not in matched_pred]
    return pairs, unmatched_gt, unmatched_pred


def update_detection(stats: Dict[str, int], tp: int, fp: int, fn: int) -> None:
    stats["tp"] += tp
    stats["fp"] += fp
    stats["fn"] += fn


def finalize_detection(stats: Dict[str, int]) -> Dict[str, float]:
    tp = stats["tp"]
    fp = stats["fp"]
    fn = stats["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def new_field_stats() -> Dict[str, int]:
    return {
        "pairs": 0,
        "gt_nonempty": 0,
        "pred_nonempty": 0,
        "exact": 0,
        "exact_when_gt_nonempty": 0,
    }


def update_field_stats(stats: Dict[str, int], field: str, gt_record: FlatRecord, pred_record: FlatRecord) -> None:
    gt_value = gt_record.get(field)
    pred_value = pred_record.get(field)
    stats["pairs"] += 1
    if nonempty(gt_value):
        stats["gt_nonempty"] += 1
    if nonempty(pred_value):
        stats["pred_nonempty"] += 1
    exact = field_exact(field, gt_value, pred_value)
    if exact:
        stats["exact"] += 1
        if nonempty(gt_value):
            stats["exact_when_gt_nonempty"] += 1


def finalize_field_stats(stats: Dict[str, int]) -> Dict[str, Optional[float]]:
    pairs = stats["pairs"]
    gt_nonempty = stats["gt_nonempty"]
    pred_nonempty = stats["pred_nonempty"]
    return {
        "pairs": pairs,
        "gt_nonempty": gt_nonempty,
        "pred_nonempty": pred_nonempty,
        "exact": stats["exact"],
        "pair_exact_rate": (stats["exact"] / pairs) if pairs else None,
        "gt_cover_exact_rate": (stats["exact_when_gt_nonempty"] / gt_nonempty) if gt_nonempty else None,
        "pred_fill_rate": (pred_nonempty / pairs) if pairs else None,
    }


def round_floats(obj: Any, ndigits: int = 6) -> Any:
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, list):
        return [round_floats(v, ndigits) for v in obj]
    if isinstance(obj, dict):
        return {k: round_floats(v, ndigits) for k, v in obj.items()}
    return obj


def load_flat_records(path: Path) -> Tuple[str, List[FlatRecord]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    paper_id = str(data.get("paper_id") or path.stem)
    records = data.get("records") or []
    if not isinstance(records, list):
        records = []
    out = [FlatRecord(paper_id=paper_id, index=i, raw=r) for i, r in enumerate(records) if isinstance(r, dict)]
    return paper_id, out


def discover_pairs(gt_dir: Path, out_dir: Path) -> List[Tuple[str, Path, Optional[Path]]]:
    pairs: List[Tuple[str, Path, Optional[Path]]] = []
    gt_files = sorted(gt_dir.glob("paper_*.json"), key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)))
    for gt_path in gt_files:
        match = re.search(r"(\d+)", gt_path.stem)
        if not match:
            continue
        paper_id = match.group(1)
        out_path = out_dir / paper_id / f"{paper_id}_extraction.json"
        pairs.append((paper_id, gt_path, out_path if out_path.exists() else None))
    return pairs


def example_record(record: FlatRecord) -> Dict[str, Any]:
    return {
        "ligand_id": record.get("ligand_id"),
        "ligand_name": record.get("ligand_name"),
        "sequence_name": record.get("sequence_name"),
        "sequence": record.get("sequence"),
        "activity1": record.get("activity1"),
        "activity2": record.get("activity2"),
        "method": record.get("method"),
        "value": record.get("value"),
    }


def top_field_errors(field_stats: Dict[str, Dict[str, int]]) -> List[Tuple[str, float]]:
    ranked = []
    for field, stats in field_stats.items():
        final = finalize_field_stats(stats)
        rate = final["gt_cover_exact_rate"]
        ranked.append((field, -1.0 if rate is None else rate))
    ranked.sort(key=lambda x: (x[1], x[0]))
    return ranked


def build_markdown_report(report: Dict[str, Any], output_json_path: Path) -> str:
    lines: List[str] = []
    lines.append("# G4 Extraction Scoring Report")
    lines.append("")
    lines.append(f"**生成时间**: {report['generated_at']}")
    lines.append("")
    lines.append(f"- Groundtruth dir: `{report['config']['groundtruth_dir']}`")
    lines.append(f"- Output dir: `{report['config']['output_dir']}`")
    lines.append(f"- Match max cost: `{report['config']['match_max_cost']}`")
    lines.append(f"- JSON report: `{output_json_path}`")
    lines.append("")

    overall = report["overall"]
    det = overall["record_detection"]
    full = overall["full_record_hit"]
    lines.append("## Overall")
    lines.append("")
    lines.append("### Record Detection")
    lines.append("")
    lines.append(f"- GT / Pred / Matched: `{overall['gt_records']}` / `{overall['pred_records']}` / `{det['tp']}`")
    lines.append(f"- TP / FP / FN: `{det['tp']}` / `{det['fp']}` / `{det['fn']}`")
    lines.append(f"- Precision / Recall / F1: `{det['precision']:.4f}` / `{det['recall']:.4f}` / `{det['f1']:.4f}`")
    lines.append("")
    lines.append("### Full Record Hit")
    lines.append("")
    lines.append(f"- Exact matched records: `{full['full_hit']}` / `{full['total_matched']}`")
    lines.append(f"- Exact hit rate on matched pairs: `{full['hit_rate']}`")
    lines.append("")

    lines.append("### Field Accuracy On Matched Pairs")
    lines.append("")
    lines.append("| Field | Pair Exact Rate | GT-Cover Exact Rate | Pred Fill Rate | Exact / Pairs |")
    lines.append("|---|---:|---:|---:|---:|")
    for field in FIELD_NAMES:
        stats = overall["field_accuracy"][field]
        pair_rate = stats["pair_exact_rate"]
        cover_rate = stats["gt_cover_exact_rate"]
        fill_rate = stats["pred_fill_rate"]
        lines.append(
            "| {field} | {pair} | {cover} | {fill} | {exact}/{pairs} |".format(
                field=field,
                pair="None" if pair_rate is None else f"{pair_rate:.4f}",
                cover="None" if cover_rate is None else f"{cover_rate:.4f}",
                fill="None" if fill_rate is None else f"{fill_rate:.4f}",
                exact=stats["exact"],
                pairs=stats["pairs"],
            )
        )
    lines.append("")

    lines.append("## By Activity2")
    lines.append("")
    lines.append("| Activity2 | TP | FP | FN | F1 |")
    lines.append("|---|---:|---:|---:|---:|")
    for key in sorted(report["by_activity2"]):
        item = report["by_activity2"][key]
        lines.append(f"| {key} | {item['tp']} | {item['fp']} | {item['fn']} | {item['f1']:.4f} |")
    lines.append("")

    lines.append("## By Method")
    lines.append("")
    lines.append("| Method | TP | FP | FN | F1 |")
    lines.append("|---|---:|---:|---:|---:|")
    for key in sorted(report["by_method"]):
        item = report["by_method"][key]
        lines.append(f"| {key} | {item['tp']} | {item['fp']} | {item['fn']} | {item['f1']:.4f} |")
    lines.append("")

    lines.append("## Per Article")
    lines.append("")
    for article in report["articles"]:
        lines.append(f"### Paper `{article['paper_id']}`")
        lines.append("")
        if article.get("status") == "missing_output":
            lines.append("- Missing predicted extraction file.")
            lines.append("")
            continue

        det = article["record_detection"]
        full = article["full_record_hit"]
        lines.append(f"- GT / Pred / Matched: `{article['gt_records']}` / `{article['pred_records']}` / `{det['tp']}`")
        lines.append(f"- TP / FP / FN: `{det['tp']}` / `{det['fp']}` / `{det['fn']}`")
        lines.append(f"- Precision / Recall / F1: `{det['precision']:.4f}` / `{det['recall']:.4f}` / `{det['f1']:.4f}`")
        lines.append(f"- Full record hit: `{full['full_hit']}/{full['total_matched']}` (rate={full['hit_rate']})")

        ranked = article.get("field_ranking") or []
        if ranked:
            worst = ", ".join(f"{field}={score:.4f}" for field, score in ranked[:5])
            lines.append(f"- Worst fields: `{worst}`")

        missing_examples = article.get("missing_examples") or []
        extra_examples = article.get("extra_examples") or []
        if missing_examples:
            lines.append("- Missing examples:")
            for ex in missing_examples[:3]:
                lines.append(f"  - `{json.dumps(ex, ensure_ascii=False)}`")
        if extra_examples:
            lines.append("- Extra examples:")
            for ex in extra_examples[:3]:
                lines.append(f"  - `{json.dumps(ex, ensure_ascii=False)}`")
        lines.append("")

    return "\n".join(lines)


def resolve_input_path(raw_path: str, base_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    base_candidate = (base_dir / path).resolve()
    if base_candidate.exists():
        return base_candidate
    return path.resolve()


def resolve_output_path(raw_path: str, base_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Detailed scoring for flat G4 extraction results.")
    parser.add_argument(
        "--groundtruth-dir",
        default="../学校工程结果",
        help="Groundtruth directory path.",
    )
    parser.add_argument(
        "--output-dir",
        default="../data/processed",
        help="Predicted extraction directory path.",
    )
    parser.add_argument(
        "--report-json",
        default="scoring_report.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default="scoring_summary.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--match-max-cost",
        type=float,
        default=16.0,
        help="Maximum allowed pair cost when matching GT and predicted records.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    gt_dir = resolve_input_path(args.groundtruth_dir, script_dir)
    out_dir = resolve_input_path(args.output_dir, script_dir)
    report_json = resolve_output_path(args.report_json, script_dir)
    report_md = resolve_output_path(args.report_md, script_dir)

    pairs_to_score = discover_pairs(gt_dir, out_dir)
    if not pairs_to_score:
        raise SystemExit(f"No groundtruth files found in: {gt_dir}")

    overall_det = {"tp": 0, "fp": 0, "fn": 0}
    overall_field_stats = {field: new_field_stats() for field in FIELD_NAMES}
    overall_full_hit = {"full_hit": 0, "total_matched": 0}
    overall_gt_records = 0
    overall_pred_records = 0

    by_activity2 = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    by_method = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    article_reports: List[Dict[str, Any]] = []

    for paper_id, gt_path, pred_path in pairs_to_score:
        if pred_path is None:
            article_reports.append(
                {
                    "paper_id": paper_id,
                    "status": "missing_output",
                    "groundtruth_file": str(gt_path),
                }
            )
            continue

        _, gt_records = load_flat_records(gt_path)
        _, pred_records = load_flat_records(pred_path)
        overall_gt_records += len(gt_records)
        overall_pred_records += len(pred_records)

        pairs, unmatched_gt, unmatched_pred = greedy_match_records(
            gt_records,
            pred_records,
            max_cost=args.match_max_cost,
        )

        art_det = {"tp": len(pairs), "fp": len(unmatched_pred), "fn": len(unmatched_gt)}
        update_detection(overall_det, art_det["tp"], art_det["fp"], art_det["fn"])

        art_field_stats = {field: new_field_stats() for field in FIELD_NAMES}
        art_full_hit = {"full_hit": 0, "total_matched": len(pairs)}

        for gi, pi, _ in pairs:
            gt_record = gt_records[gi]
            pred_record = pred_records[pi]
            full_hit = True
            for field in FIELD_NAMES:
                update_field_stats(art_field_stats[field], field, gt_record, pred_record)
                update_field_stats(overall_field_stats[field], field, gt_record, pred_record)
            for field in CORE_FIELDS:
                if field == "value":
                    if not soft_value_match(gt_record.get(field), pred_record.get(field)):
                        full_hit = False
                        break
                elif not field_exact(field, gt_record.get(field), pred_record.get(field)):
                    full_hit = False
                    break
            if full_hit:
                art_full_hit["full_hit"] += 1
                overall_full_hit["full_hit"] += 1
            overall_full_hit["total_matched"] += 1

            act_key = normalize_activity2(gt_record.get("activity2")) or "unknown"
            method_key = normalize_method(gt_record.get("method")) or "unknown"
            update_detection(by_activity2[act_key], 1, 0, 0)
            update_detection(by_method[method_key], 1, 0, 0)

        for gi in unmatched_gt:
            gt_record = gt_records[gi]
            act_key = normalize_activity2(gt_record.get("activity2")) or "unknown"
            method_key = normalize_method(gt_record.get("method")) or "unknown"
            update_detection(by_activity2[act_key], 0, 0, 1)
            update_detection(by_method[method_key], 0, 0, 1)

        for pi in unmatched_pred:
            pred_record = pred_records[pi]
            act_key = normalize_activity2(pred_record.get("activity2")) or "unknown"
            method_key = normalize_method(pred_record.get("method")) or "unknown"
            update_detection(by_activity2[act_key], 0, 1, 0)
            update_detection(by_method[method_key], 0, 1, 0)

        article_reports.append(
            {
                "paper_id": paper_id,
                "groundtruth_file": str(gt_path),
                "predicted_file": str(pred_path),
                "gt_records": len(gt_records),
                "pred_records": len(pred_records),
                "record_detection": finalize_detection(art_det),
                "full_record_hit": {
                    "full_hit": art_full_hit["full_hit"],
                    "total_matched": art_full_hit["total_matched"],
                    "hit_rate": (
                        art_full_hit["full_hit"] / art_full_hit["total_matched"]
                        if art_full_hit["total_matched"]
                        else None
                    ),
                },
                "field_accuracy": {
                    field: finalize_field_stats(stats) for field, stats in art_field_stats.items()
                },
                "field_ranking": top_field_errors(art_field_stats),
                "missing_examples": [example_record(gt_records[i]) for i in unmatched_gt[:5]],
                "extra_examples": [example_record(pred_records[i]) for i in unmatched_pred[:5]],
                "matched_pairs": [
                    {
                        "gt_index": gi,
                        "pred_index": pi,
                        "cost": cost,
                    }
                    for gi, pi, cost in pairs
                ],
            }
        )

    report = {
        "generated_at": datetime.now().isoformat(),
        "config": {
            "groundtruth_dir": str(gt_dir),
            "output_dir": str(out_dir),
            "match_max_cost": args.match_max_cost,
        },
        "overall": {
            "gt_records": overall_gt_records,
            "pred_records": overall_pred_records,
            "record_detection": finalize_detection(overall_det),
            "full_record_hit": {
                "full_hit": overall_full_hit["full_hit"],
                "total_matched": overall_full_hit["total_matched"],
                "hit_rate": (
                    overall_full_hit["full_hit"] / overall_full_hit["total_matched"]
                    if overall_full_hit["total_matched"]
                    else None
                ),
            },
            "field_accuracy": {
                field: finalize_field_stats(stats) for field, stats in overall_field_stats.items()
            },
        },
        "by_activity2": {
            key: finalize_detection(stats) for key, stats in sorted(by_activity2.items())
        },
        "by_method": {
            key: finalize_detection(stats) for key, stats in sorted(by_method.items())
        },
        "articles": sorted(article_reports, key=lambda x: int(x["paper_id"])),
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(round_floats(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md.write_text(build_markdown_report(report, report_json), encoding="utf-8")

    print(f"Saved JSON report to: {report_json}")
    print(f"Saved Markdown report to: {report_md}")


if __name__ == "__main__":
    main()
