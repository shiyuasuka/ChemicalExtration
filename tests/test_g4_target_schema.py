from knowmat.extractors import G4BindingItem
from knowmat.schema_converter import SchemaConverter


def test_g4_binding_item_allows_missing_sequence_for_non_sequence_specific_records():
    item = G4BindingItem(
        ligand_name="RHPS4",
        method="Immunofluorescence (IF)",
        sequence=None,
        value="hTERT repression observed",
    )
    assert item.sequence is None


def test_schema_converter_flattens_runtime_g4_bindings_to_target_records():
    converter = SchemaConverter()
    runtime = {
        "g4_bindings": [
            {
                "ligand_name": "Adriamycin",
                "sequence": "TTAGGGTTTAGGGTTTAGGGTTTAGGGT",
                "sequence_name": "HTel7",
                "value": "Delta Tm2=6.4 ℃",
                "method": "Differential scanning calorimetry",
            }
        ]
    }

    out = converter.convert(runtime, "data/raw/28/28.md")

    assert out["paper_id"] == "28"
    assert out["record_count"] == 1
    record = out["records"][0]
    assert record["paper_id"] == "28"
    assert record["activity1"] == "Interaction"
    assert record["activity2"] == "Stabilization"
    assert record["method"] == "Differential Scanning Calorimetry (DSC)"
    assert record["value"] == "Delta Tm2=6.4 ℃"


def test_schema_converter_flattens_lab_items_without_dropping_null_sequence():
    converter = SchemaConverter()
    lab = {
        "Paper_Metadata": {"Paper_Title": "paper_19"},
        "items": [
            {
                "Ligand_Info": {"ligand_id": "G4L0108", "ligand_name": "RHPS4"},
                "Activity_Info": {
                    "activity1": "Activity at Molecular Level",
                    "activity2": "DNA Damage",
                    "value": "Activating a DNA damage response pathway",
                },
                "Experimental_Conditions": {"method": "Immunofluorescence (IF)"},
            }
        ],
    }

    out = converter.convert(lab, "paper_19.md")

    assert out["paper_id"] == "19"
    assert out["record_count"] == 1
    record = out["records"][0]
    assert record["sequence"] is None
    assert record["activity1"] == "Activity at Molecular Level"
    assert record["activity2"] == "DNA Damage"


def test_schema_converter_backfills_ligand_id_from_local_registry_for_global_alias():
    converter = SchemaConverter()
    runtime = {
        "g4_bindings": [
            {
                "ligand_name": "TMPyP4",
                "sequence_name": "HGQ-NV-L",
                "sequence": "UUUAAGGAGAACGGGAUGGUUAAGGAUGAG",
                "method": "Isothermal Titration Calorimetry (ITC)",
                "value": "Ka1=1E8 M−1; Ka2=7.41E4 M−1",
            }
        ]
    }

    out = converter.convert(runtime, "data/raw/55/55.md")

    assert out["records"][0]["ligand_id"] == "G4L0065"


def test_schema_converter_backfills_ligand_id_from_local_registry_for_paper_specific_alias():
    converter = SchemaConverter()
    runtime = {
        "g4_bindings": [
            {
                "ligand_name": "Adriamycin",
                "sequence": "TTAGGGTTTAGGGTTTAGGGTTTAGGGT",
                "method": "Surface Plasmon Resonance (SPR)",
                "value": "Kd = 2.3 µM",
            }
        ]
    }

    out = converter.convert(runtime, "data/raw/28/28.md")

    assert out["records"][0]["ligand_id"] == "G4L0244"
