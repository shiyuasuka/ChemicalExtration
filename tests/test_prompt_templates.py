from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_system_prompt_contains_core_extraction_guardrails():
    prompt = (ROOT / "prompts" / "extraction_system_template.txt").read_text(encoding="utf-8")

    assert "G4 ligand" in prompt or "G-quadruplex" in prompt
    assert "Do NOT extract or invent any other fields" in prompt
    assert "One record = one ligand" in prompt
    assert "Do not emit cited prior-work values" in prompt
    assert "g4_bindings" in prompt


def test_user_prompt_contains_extraction_instructions():
    prompt = (ROOT / "prompts" / "extraction_user_template.txt").read_text(encoding="utf-8")

    assert "{paper_text}" in prompt
    assert "g4_bindings" in prompt or "ligand_name" in prompt
    assert "Do not output any additional fields" in prompt
