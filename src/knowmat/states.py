"""
Definition of the shared state used by the KnowMat 2.0 LangGraph workflow.

The state is a TypedDict with optional fields that are progressively
populated as the pipeline advances.  Each node in the LangGraph will
receive a copy of the state and return a dictionary of updates.  The
graph merges these updates into the existing state.

Important fields
----------------

* ``pdf_path``: The path to the PDF file being processed.  Set at the
  beginning of the run.
* ``paper_text``: The extracted plain text of the paper. By default, the
  full text is preserved; references trimming is optional via config.
* ``sub_field``: The detected sub‑field of materials science (e.g.
  experimental, computational, simulation, machine learning, hybrid).
* ``updated_prompt``: The extraction prompt with adjustments suggested by
  the sub‑field detection and evaluation agents.
* ``latest_extracted_data``: The most recent extraction result as a
  JSON‑serialisable dictionary.
* ``run_results``: A list of dictionaries summarising each evaluation run.
  Each entry contains at least ``run_id``, ``confidence_score``,
  ``rationale``, ``suggested_prompt`` and ``extracted_data_path``.
* ``run_count``: The number of extraction/evaluation cycles that have
  occurred so far.  Used by the orchestrator to limit retries.
* ``max_runs``: The maximum number of extraction/evaluation cycles to
  perform.  Default is 3 and set by the orchestrator.
* ``needs_rerun``: Set by the evaluation agent to indicate whether another
  extraction is required.
* ``final_data``: The final aggregated extraction output produced by the
  manager agent.
* ``rationale``: A human‑readable summary of how the final result was
  obtained.
* ``flag``: Indicates whether a human review is recommended for this
  extraction.
"""

import json
from pathlib import Path
from typing import TypedDict, List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# OCR / document metadata types
# ---------------------------------------------------------------------------

class OcrItem(TypedDict, total=False):
    """Structure representing a single OCR-processed block.
    
    This type represents the output of the OCR pipeline for individual
    content blocks (paragraphs, tables, formulas, images).
    """
    
    typer: str  # Block type: "paragraph", "table", "formula", "image"
    text: str  # Extracted text content (for paragraphs/formulas)
    data: Dict[str, Any]  # Structured data (for tables/images)
    page: int  # 1-based page number
    bbox: List[float]  # Bounding box [x0, y0, x1, y1] in 72-DPI coordinates
    confidence: float  # OCR confidence score (0.0 to 1.0)
    block_label: str  # Layout label from PP-DocLayout (e.g., "text", "table", "formula")
    is_layout_noise: bool  # True if block is header/footer/aside
    reocr_source: str  # Source of re-OCR if applicable (e.g., "ppstructurev3_replace")


class OcrPageMeta(TypedDict):
    """Per-page metadata produced by the OCR stage."""

    page_number: int
    text_length: int
    has_tables: bool
    has_figures: bool


class DocumentMetadata(TypedDict, total=False):
    """Structured metadata extracted from a parsed PDF/TXT document."""

    doi: Optional[str]
    title: Optional[str]
    total_pages: int
    page_meta: List[OcrPageMeta]
    ocr_engine: str
    ocr_items: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Target-schema types (output of SchemaConverter)
# ---------------------------------------------------------------------------

class LigandInfo(TypedDict, total=False):
    """Ligand-level information for one G4 binding record."""

    ligand_id: str
    ligand_name: Optional[str]
    ligand_name_std: Optional[str]
    ligand_synonyms: Optional[List[str]]
    counter_ion: Optional[str]
    metal_ion: Optional[str]


class SequenceInfo(TypedDict, total=False):
    """Nucleic acid sequence information."""

    sequence: str
    sequence_name: Optional[str]
    sequence_type: Optional[str]


class ActivityInfo(TypedDict, total=False):
    """Binding activity measurement."""

    activity1: Optional[str]
    activity2: Optional[str]
    value: Optional[str]  # raw measurement string (Kd, IC50, ΔTm, etc.)


class ExperimentalConditions(TypedDict, total=False):
    """Experimental conditions for the measurement."""

    method: Optional[str]
    buffer: Optional[str]
    sample_concentration: Optional[str]
    instrument: Optional[str]
    comments: Optional[str]


class G4BindingItem(TypedDict, total=False):
    """One lab-style G4 ligand binding record."""

    Ligand_Info: LigandInfo
    Sequence_Info: SequenceInfo
    Activity_Info: ActivityInfo
    Experimental_Conditions: ExperimentalConditions
    context: Optional[str]


class FlatG4Record(TypedDict, total=False):
    """One flattened benchmark record in the final user-facing output."""

    ligand_id: Optional[str]
    ligand_name: Optional[str]
    ligand_name_std: Optional[str]
    ligand_synonyms: Optional[List[str]]
    sequence: Optional[str]
    sequence_name: Optional[str]
    sequence_type: Optional[str]
    activity1: Optional[str]
    activity2: Optional[str]
    method: Optional[str]
    value: Optional[str]
    buffer: Optional[str]
    sample_concentration: Optional[str]
    instrument: Optional[str]
    comments: Optional[str]
    counter_ion: Optional[str]
    metal_ion: Optional[str]
    paper_id: str
    context: Optional[str]


class TargetSchema(TypedDict, total=False):
    """Top-level final schema produced by SchemaConverter."""

    paper_id: str
    record_count: int
    records: List[FlatG4Record]


# ---------------------------------------------------------------------------
# Pipeline state types
# ---------------------------------------------------------------------------

class EvaluationRun(TypedDict, total=False):
    """Structure used to record the outcome of an individual evaluation run.

    ``extracted_data_path`` holds a filesystem path to the JSON file
    containing the full extraction for this run, keeping the in-memory
    state lightweight.  Use :func:`load_run_extraction` to read it back.
    """

    run_id: int
    confidence_score: float
    rationale: str
    missing_fields: Optional[List[str]]
    hallucinated_fields: Optional[List[str]]
    suggested_prompt: Optional[str]
    extracted_data_path: str


class KnowMatState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    # Initial inputs
    pdf_path: str
    output_dir: Optional[str]
    # OCR options (optional; used by parse_pdf_with_paddleocrvl)
    ocr_pages: Optional[str]
    ocr_skip_cached: bool
    
    # PDF parsing results
    paper_text: str
    paper_text_path: Optional[str]
    figure_dir: Optional[str]
    ocr_items: Optional[List[Dict[str, Any]]]
    document_metadata: Optional[DocumentMetadata]
    
    # Sub-field detection results
    sub_field: Optional[str]
    updated_prompt: Optional[str]
    
    # Extraction and evaluation results
    latest_extracted_data: Dict[str, Any]
    run_results: List[EvaluationRun]
    run_count: int
    max_runs: int
    needs_rerun: bool
    
    # Manager aggregation results
    aggregated_data: Optional[Dict[str, Any]]  # Stage 1: Merged data from all runs
    aggregation_notes: Optional[str]  # Stage 1: Merge strategy notes
    final_data: Optional[Dict[str, Any]]  # Stage 2: Validated and corrected data
    aggregation_rationale: Optional[str]
    human_review_guide: Optional[str]
    
    # Flagging agent results
    final_confidence_score: Optional[float]
    confidence_rationale: Optional[str]
    needs_human_review: Optional[bool]
    flag: bool

    # Post-processing controls
    enable_property_standardization: bool
    qa_report: Optional[Dict[str, Any]]


def load_run_extraction(run: "EvaluationRun") -> Dict[str, Any]:
    """Load the full extraction dict for an evaluation run from disk.

    Falls back to an empty dict if the file cannot be read.
    """
    path_str = run.get("extracted_data_path", "")
    if not path_str:
        return {}
    p = Path(path_str)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
