# G4 Extraction Scoring Report

**生成时间**: 2026-04-15T18:35:39.791343

- Groundtruth dir: `/Users/zhangziyu02/Desktop/四川大学化学学院/KnowMat/学校工程结果`
- Output dir: `/Users/zhangziyu02/Desktop/四川大学化学学院/KnowMat/data/processed`
- Match max cost: `16.0`
- JSON report: `/Users/zhangziyu02/Desktop/四川大学化学学院/KnowMat/evaluation/scoring_report.json`

## Overall

### Record Detection

- GT / Pred / Matched: `151` / `96` / `64`
- TP / FP / FN: `64` / `32` / `87`
- Precision / Recall / F1: `0.6667` / `0.4238` / `0.5182`

### Full Record Hit

- Exact matched records: `0` / `64`
- Exact hit rate on matched pairs: `0.0`

### Field Accuracy On Matched Pairs

| Field | Pair Exact Rate | GT-Cover Exact Rate | Pred Fill Rate | Exact / Pairs |
|---|---:|---:|---:|---:|
| ligand_id | 0.8750 | 0.8750 | 0.9062 | 56/64 |
| ligand_name | 0.1562 | 0.1562 | 1.0000 | 10/64 |
| ligand_name_std | 0.3125 | 0.1905 | 0.8125 | 20/64 |
| ligand_synonyms | 0.0625 | 0.0000 | 0.8906 | 4/64 |
| sequence | 0.3750 | 0.0294 | 0.1250 | 24/64 |
| sequence_name | 0.4375 | 0.8750 | 0.8906 | 28/64 |
| sequence_type | 0.8125 | 0.8529 | 0.6406 | 52/64 |
| activity1 | 1.0000 | 1.0000 | 1.0000 | 64/64 |
| activity2 | 1.0000 | 1.0000 | 1.0000 | 64/64 |
| method | 0.9531 | 0.9531 | 1.0000 | 61/64 |
| value | 0.3906 | 0.3906 | 1.0000 | 25/64 |
| buffer | 0.5781 | None | 0.4219 | 37/64 |
| sample_concentration | 0.5156 | 0.0000 | 0.4688 | 33/64 |
| instrument | 0.6094 | 0.0000 | 0.3594 | 39/64 |
| comments | 0.0000 | 0.0000 | 1.0000 | 0/64 |
| counter_ion | 0.7500 | None | 0.2500 | 48/64 |
| metal_ion | 0.7188 | None | 0.2812 | 46/64 |
| context | 0.0000 | None | 1.0000 | 0/64 |

## By Activity2

| Activity2 | TP | FP | FN | F1 |
|---|---:|---:|---:|---:|
| binding | 14 | 5 | 79 | 0.2500 |
| cytotoxicity | 16 | 0 | 2 | 0.9412 |
| dnadamage | 4 | 6 | 0 | 0.5714 |
| enzyme | 7 | 15 | 0 | 0.4828 |
| geneexpression | 3 | 3 | 0 | 0.6667 |
| recognition | 1 | 0 | 5 | 0.2857 |
| stabilization | 19 | 3 | 1 | 0.9048 |

## By Method

| Method | TP | FP | FN | F1 |
|---|---:|---:|---:|---:|
| chromatinimmunoprecipitationchip | 2 | 2 | 0 | 0.6667 |
| circulardichroismcd | 10 | 3 | 1 | 0.8333 |
| differentialscanningcalorimetrydsc | 8 | 0 | 0 | 1.0000 |
| fluorescencespectroscopyfl | 1 | 1 | 13 | 0.1250 |
| fluorescentinsituhybridizationfish | 1 | 0 | 0 | 1.0000 |
| immunofluorescenceif | 1 | 4 | 0 | 0.3333 |
| isothermaltitrationcalorimetryitc | 2 | 0 | 12 | 0.2500 |
| markovstatemodelmsmanalysis | 1 | 0 | 0 | 1.0000 |
| moleculardockingcalculation | 0 | 0 | 16 | 0.0000 |
| molecularmechanicspoissonboltzmannsurfaceareamm-pbsa | 3 | 0 | 0 | 1.0000 |
| moleculedynamicsmdsimulation | 6 | 1 | 42 | 0.2182 |
| nuclearmagneticresonancenmr | 2 | 0 | 0 | 1.0000 |
| receptorinhibitionstudy | 3 | 3 | 0 | 0.6667 |
| sulforhodaminebassaysrb | 16 | 0 | 2 | 0.9412 |
| surfaceplasmonresonancespr | 0 | 3 | 1 | 0.0000 |
| telomericrepeatamplificationprotocoltrapassay | 7 | 15 | 0 | 0.4828 |
| uv-visabsorptionspectroscopy | 1 | 0 | 0 | 1.0000 |

## Per Article

### Paper `6`

- GT / Pred / Matched: `25` / `38` / `23`
- TP / FP / FN: `23` / `15` / `2`
- Precision / Recall / F1: `0.6053` / `0.9200` / `0.7302`
- Full record hit: `0/23` (rate=0.0)
- Worst fields: `buffer=-1.0000, context=-1.0000, counter_ion=-1.0000, instrument=-1.0000, metal_ion=-1.0000`
- Missing examples:
  - `{"ligand_id": "G4L0082", "ligand_name": "2,7-disubstituted fluorenone derivative 16a", "sequence_name": null, "sequence": null, "activity1": "Activity at Cellular Level", "activity2": "Cytotoxicity", "method": "Sulforhodamine B assay (SRB)", "value": "IC50>20 μM"}`
  - `{"ligand_id": "G4L0087", "ligand_name": "2,7-disubstituted fluorenone derivative 21a", "sequence_name": null, "sequence": null, "activity1": "Activity at Cellular Level", "activity2": "Cytotoxicity", "method": "Sulforhodamine B assay (SRB)", "value": "IC50=2.4 μM"}`
- Extra examples:
  - `{"ligand_id": "G4L0073", "ligand_name": "7a", "sequence_name": "telomeric DNA", "sequence": "TTAGGGTTAGGGTTAGGGTTAGGG", "activity1": "Activity at Molecular Level", "activity2": "Enzyme", "method": "Telomeric Repeat Amplification Protocol (TRAP) Assay", "value": "IC50=15.5 μM"}`
  - `{"ligand_id": null, "ligand_name": "8a", "sequence_name": "telomeric DNA", "sequence": "TTAGGGTTAGGGTTAGGGTTAGGG", "activity1": "Activity at Molecular Level", "activity2": "Enzyme", "method": "Telomeric Repeat Amplification Protocol (TRAP) Assay", "value": "IC50>>50 μM"}`
  - `{"ligand_id": "G4L0090", "ligand_name": "8b", "sequence_name": "telomeric DNA", "sequence": "TTAGGGTTAGGGTTAGGGTTAGGG", "activity1": "Activity at Molecular Level", "activity2": "Enzyme", "method": "Telomeric Repeat Amplification Protocol (TRAP) Assay", "value": "IC50=27.3 μM"}`

### Paper `19`

- GT / Pred / Matched: `9` / `22` / `8`
- TP / FP / FN: `8` / `14` / `1`
- Precision / Recall / F1: `0.3636` / `0.8889` / `0.5161`
- Full record hit: `0/8` (rate=0.0)
- Worst fields: `buffer=-1.0000, context=-1.0000, counter_ion=-1.0000, instrument=-1.0000, metal_ion=-1.0000`
- Missing examples:
  - `{"ligand_id": "G4L1613", "ligand_name": "3", "sequence_name": null, "sequence": "AGGGTTAGGGTTAGGGTTAGGG", "activity1": "Interaction", "activity2": "Binding", "method": "Surface Plasmon Resonance (SPR)", "value": "KD=0.8×10e-7 M-1"}`
- Extra examples:
  - `{"ligand_id": "G4L0108", "ligand_name": "RHPS4 (1)", "sequence_name": "h-Tel", "sequence": "AGGGTTAGGGTTAGGGTTAGGG", "activity1": "Interaction", "activity2": "Binding", "method": "Surface Plasmon Resonance (SPR)", "value": "K=0.83×10^7 M−1"}`
  - `{"ligand_id": "G4L0108", "ligand_name": "Compound 2", "sequence_name": "h-Tel", "sequence": "AGGGTTAGGGTTAGGGTTAGGG", "activity1": "Interaction", "activity2": "Binding", "method": "Surface Plasmon Resonance (SPR)", "value": "K=1.5×10^7 M−1"}`
  - `{"ligand_id": "G4L0108", "ligand_name": "Compound 3", "sequence_name": "h-Tel", "sequence": "AGGGTTAGGGTTAGGGTTAGGG", "activity1": "Interaction", "activity2": "Binding", "method": "Surface Plasmon Resonance (SPR)", "value": "K=0.8×10^7 M−1"}`

### Paper `21`

- GT / Pred / Matched: `51` / `11` / `10`
- TP / FP / FN: `10` / `1` / `41`
- Precision / Recall / F1: `0.9091` / `0.1961` / `0.3226`
- Full record hit: `0/10` (rate=0.0)
- Worst fields: `buffer=-1.0000, context=-1.0000, counter_ion=-1.0000, ligand_name_std=-1.0000, ligand_synonyms=-1.0000`
- Missing examples:
  - `{"ligand_id": "G4L0226", "ligand_name": "42", "sequence_name": "Pu24; PDB ID: 2MGN", "sequence": "TGAGGGTGGTGAGGGTGGGGAAGG", "activity1": "Interaction", "activity2": "Binding", "method": "Molecule Dynamics (MD) Simulation", "value": "Docking Score=-9.236 kcal/mol"}`
  - `{"ligand_id": "G4L0207", "ligand_name": "23", "sequence_name": "Pu24; PDB ID: 2MGN", "sequence": "TGAGGGTGGTGAGGGTGGGGAAGG", "activity1": "Interaction", "activity2": "Binding", "method": "Molecule Dynamics (MD) Simulation", "value": "Docking Score=-9.146 kcal/mol"}`
  - `{"ligand_id": "G4L0204", "ligand_name": "20", "sequence_name": "Pu24; PDB ID: 2MGN", "sequence": "TGAGGGTGGTGAGGGTGGGGAAGG", "activity1": "Interaction", "activity2": "Binding", "method": "Molecule Dynamics (MD) Simulation", "value": "Docking Score change=-0.275 kcal/mol"}`
- Extra examples:
  - `{"ligand_id": "G4L0108", "ligand_name": "Ligand 2", "sequence_name": "Pu24;PDB ID: 2MGN", "sequence": null, "activity1": "Interaction", "activity2": "Binding", "method": "Molecule Dynamics (MD) Simulation", "value": "Docking Score=-9.255 kcal/mol"}`

### Paper `28`

- GT / Pred / Matched: `11` / `11` / `10`
- TP / FP / FN: `10` / `1` / `1`
- Precision / Recall / F1: `0.9091` / `0.9091` / `0.9091`
- Full record hit: `0/10` (rate=0.0)
- Worst fields: `buffer=-1.0000, context=-1.0000, counter_ion=-1.0000, instrument=-1.0000, ligand_name_std=-1.0000`
- Missing examples:
  - `{"ligand_id": "G4L0244", "ligand_name": "Adriamycin ", "sequence_name": "PDB ID: 1NP9", "sequence": "TTAGGGTTTAGGGTTTAGGGTTTAGGGT", "activity1": "Interaction", "activity2": "Binding", "method": "Molecule Dynamics (MD) Simulation", "value": "Binding mode: intercalation"}`
- Extra examples:
  - `{"ligand_id": "G4L0244", "ligand_name": "adriamycin", "sequence_name": "HTel7", "sequence": null, "activity1": "Interaction", "activity2": "Binding", "method": "Fluorescence Spectroscopy (Fl)", "value": "Kb2=6.7×10^5 M^-1"}`

### Paper `55`

- GT / Pred / Matched: `9` / `6` / `5`
- TP / FP / FN: `5` / `1` / `4`
- Precision / Recall / F1: `0.8333` / `0.5556` / `0.6667`
- Full record hit: `0/5` (rate=0.0)
- Worst fields: `buffer=-1.0000, context=-1.0000, counter_ion=-1.0000, instrument=-1.0000, metal_ion=-1.0000`
- Missing examples:
  - `{"ligand_id": "G4L0140", "ligand_name": "3,6,9-trisubstituted acridine derivative 3; BRACO-19; 1; (N-{9-[4-(dimethylamino) anilino]-6-(3-pyrrolidin-1-ylpropanoylamino)acridin-3-yl}-3-pyrrolidin-1ylpropanamide;N,N'-(9-((4-(dimethylamino)phenyl)amino)acridine-3,6-diyl)bis(3-(pyrrolidin-1-yl)propanamide)", "sequence_name": "HGQ-NV-L", "sequence": "UUUAAGGAGAACGGGAUGGUUAAGGAUGAG", "activity1": "Interaction", "activity2": "Binding", "method": "Isothermal Titration Calorimetry (ITC)", "value": "Ka1=3.52E6 M−1"}`
  - `{"ligand_id": "G4L0140", "ligand_name": "3,6,9-trisubstituted acridine derivative 3; BRACO-19; 1; (N-{9-[4-(dimethylamino) anilino]-6-(3-pyrrolidin-1-ylpropanoylamino)acridin-3-yl}-3-pyrrolidin-1ylpropanamide;N,N'-(9-((4-(dimethylamino)phenyl)amino)acridine-3,6-diyl)bis(3-(pyrrolidin-1-yl)propanamide)", "sequence_name": "HGQ-NV-L", "sequence": "UUUAAGGAGAACGGGAUGGUUAAGGAUGAG", "activity1": "Interaction", "activity2": "Binding", "method": "Isothermal Titration Calorimetry (ITC)", "value": "Ka2=4.58E4 M−1"}`
  - `{"ligand_id": "G4L0140", "ligand_name": "3,6,9-trisubstituted acridine derivative 3; BRACO-19; 1; (N-{9-[4-(dimethylamino) anilino]-6-(3-pyrrolidin-1-ylpropanoylamino)acridin-3-yl}-3-pyrrolidin-1ylpropanamide;N,N'-(9-((4-(dimethylamino)phenyl)amino)acridine-3,6-diyl)bis(3-(pyrrolidin-1-yl)propanamide)", "sequence_name": "HGQ-NV-G", "sequence": "ACAGUGGUAAACGGUGUUUGGAUUUGGUGGGGUCCAG", "activity1": "Interaction", "activity2": "Binding", "method": "Isothermal Titration Calorimetry (ITC)", "value": "Ka=2.77E6 M−1"}`
- Extra examples:
  - `{"ligand_id": "G4L0065", "ligand_name": "TMPyP4", "sequence_name": "HGQ-NV-L", "sequence": null, "activity1": "Interaction", "activity2": "Stabilization", "method": "Circular Dichroism (CD)", "value": "Delta Tm2=3.9 ℃"}`

### Paper `59`

- GT / Pred / Matched: `46` / `8` / `8`
- TP / FP / FN: `8` / `0` / `38`
- Precision / Recall / F1: `1.0000` / `0.1739` / `0.2963`
- Full record hit: `0/8` (rate=0.0)
- Worst fields: `buffer=-1.0000, comments=-1.0000, context=-1.0000, counter_ion=-1.0000, metal_ion=-1.0000`
- Missing examples:
  - `{"ligand_id": "G4L0140", "ligand_name": "3,6,9-trisubstituted acridine derivative 3; BRACO-19; 1; (N-{9-[4-(dimethylamino) anilino]-6-(3-pyrrolidin-1-ylpropanoylamino)acridin-3-yl}-3-pyrrolidin-1ylpropanamide;N,N'-(9-((4-(dimethylamino)phenyl)amino)acridine-3,6-diyl)bis(3-(pyrrolidin-1-yl)propanamide)", "sequence_name": "ZNS5B", "sequence": "GGAUGUGGCAGAGGGGGCUGG", "activity1": "Interaction", "activity2": "Recognition", "method": "Fluorescence Spectroscopy (Fl)", "value": "Showed higher binding affinity (>100 fold higher) comparison to the duplex control RNA sequence"}`
  - `{"ligand_id": "G4L0140", "ligand_name": "3,6,9-trisubstituted acridine derivative 3; BRACO-19; 1; (N-{9-[4-(dimethylamino) anilino]-6-(3-pyrrolidin-1-ylpropanoylamino)acridin-3-yl}-3-pyrrolidin-1ylpropanamide;N,N'-(9-((4-(dimethylamino)phenyl)amino)acridine-3,6-diyl)bis(3-(pyrrolidin-1-yl)propanamide)", "sequence_name": "ZGQ2", "sequence": "GGACCGCCUGGGGGUGGGGGGAGG", "activity1": "Interaction", "activity2": "Recognition", "method": "Fluorescence Spectroscopy (Fl)", "value": "Showed higher binding affinity (>100 fold higher) comparison to the duplex control RNA sequence"}`
  - `{"ligand_id": "G4L0140", "ligand_name": "3,6,9-trisubstituted acridine derivative 3; BRACO-19; 1; (N-{9-[4-(dimethylamino) anilino]-6-(3-pyrrolidin-1-ylpropanoylamino)acridin-3-yl}-3-pyrrolidin-1ylpropanamide;N,N'-(9-((4-(dimethylamino)phenyl)amino)acridine-3,6-diyl)bis(3-(pyrrolidin-1-yl)propanamide)", "sequence_name": "ZNS3", "sequence": "GGUGGAAGAGUGAUAGGACUCUAUGGCAAUGGGGUU", "activity1": "Interaction", "activity2": "Recognition", "method": "Fluorescence Spectroscopy (Fl)", "value": "Showed higher binding affinity (>100 fold higher) comparison to the duplex control RNA sequence"}`
