from pathlib import Path

from knowmat.app_config import settings
from knowmat.nodes.paddleocrvl_parse_pdf import parse_pdf_with_paddleocrvl


def _write_sample_text(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "## Introduction",
                "Main body content.",
                "",
                "## References",
                "1. Ref A",
                "",
                "## Appendix A. Supplementary data",
                "Appendix content should be preserved when trimming is disabled.",
            ]
        ),
        encoding="utf-8",
    )


def test_txt_keeps_appendix_when_trim_references_disabled(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "trim_references_section", False)
    src = tmp_path / "paper.txt"
    _write_sample_text(src)

    result = parse_pdf_with_paddleocrvl(
        {
            "pdf_path": str(src),
            "output_dir": str(tmp_path),
            "save_intermediate": False,
        }
    )

    paper_text = result["paper_text"]
    assert "## Appendix A. Supplementary data" in paper_text
    assert "Appendix content should be preserved" in paper_text


def test_txt_trims_after_references_when_enabled(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "trim_references_section", True)
    monkeypatch.setattr(
        "knowmat.nodes.paddleocrvl_parse_pdf.strip_references_section",
        lambda text: "TRIMMED_BY_REFERENCES",
    )
    src = tmp_path / "paper.txt"
    _write_sample_text(src)

    result = parse_pdf_with_paddleocrvl(
        {
            "pdf_path": str(src),
            "output_dir": str(tmp_path),
            "save_intermediate": False,
        }
    )

    assert result["paper_text"] == "TRIMMED_BY_REFERENCES"
