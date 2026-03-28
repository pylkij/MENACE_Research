# Menace — Reverse Engineering Notes

Ongoing reverse engineering of **Menace**, a Unity IL2CPP tactical strategy game. This repository documents internal game systems at the function and data-structure level — scoring models, AI pipelines, class layouts, and runtime behaviour — derived from Il2CppDumper output and Ghidra disassembly.

The goal is a permanent reference: complete enough that no one has to redo this work.

---

## Repository Structure

```
menace-re/
├── README.md
├── tools/
│   └── extract_rvas.py          # Il2CppDumper dump.cs parser (see Tools section)
├── investigations/
│   └── tactical-ai/
│       ├── REPORT.md            # Full findings: classes, fields, formulas, design notes
│       └── RECONSTRUCTIONS.md   # Annotated C reconstructions of all analysed functions
└── dumps/
    └── (dump.cs, targets.txt — not committed, see below)
```

Additional investigations will follow the same pattern: a folder under `investigations/` with a `REPORT.md` and `RECONSTRUCTIONS.md`.

---

## Current Investigations

### Tactical AI Scoring System

**Status:** Complete.

Covers the full tile-evaluation and agent-priority pipeline from raw criterion outputs through to the final composite score used for movement decisions.

**What is fully understood:**

- The composite tile scoring formula and all its weights
- The complete `PostProcessTileScores` pipeline (POW → Scale → PostPOW → PostScale, per utility and safety)
- The two-pass criterion evaluation pattern and what happens between passes
- Neighbor propagation logic (one-step lookahead, 2×/0.5× threshold)
- The `DrawHeatmap` normalization and color-lerp algorithm
- Agent turn-priority scoring (`GetThreatLevel`, `GetOpportunityLevel`, `GetScoreMultForPickingThisAgent`)
- Behavior selection (`PickBehavior` — weighted random lottery, 30% threshold, per-agent RNG)
- Threading model for tile evaluation
- All `AIWeightsTemplate` fields (70+ named floats/ints, fully offset-mapped)

**Primary files:**
- [`investigations/tactical-ai/REPORT.md`](investigations/tactical-ai/REPORT.md)
- [`investigations/tactical-ai/RECONSTRUCTIONS.md`](investigations/tactical-ai/RECONSTRUCTIONS.md)

**The scoring formula (short version):**
```
GetScore(tile) = (SafetyScore + UtilityScore)
               - (DistanceScore + DistanceToCurrentTile) × WEIGHTS.DistanceScale
```
`SafetyScore` is stored negative after post-processing. Both scores are shaped by per-unit role multipliers on top of the global `AIWeightsTemplate` asset.

**What is NOT yet covered:**
- Individual `Criterion` subclass implementations (the concrete evaluators that write raw `SafetyScore`/`UtilityScore` values per tile)
- `Behavior` subclass implementations
- `FUN_181430ac0` — the per-attack evaluator called from `GetOpportunityLevel`

---

## Tools

### `extract_rvas.py`

Parses a standard Il2CppDumper `dump.cs` file and extracts class metadata: field offsets, method RVAs, and Ghidra VAs. Output is JSON, CSV, and a human-readable report.

```bash
# Single class
python extract_rvas.py dump.cs --class Agent --namespace Menace.Tactical.AI --out ./output

# Multiple classes from a list file
python extract_rvas.py dump.cs --class-list targets.txt --out ./output
```

**`targets.txt` format** (namespace optional):
```
TacticalStateSettings   Menace.States
TileScore
Agent
AIWeightsTemplate
```

**Output files:**

| File | Contents |
|---|---|
| `<ClassName>_rvas.json` | Methods and fields with RVAs/offsets |
| `<ClassName>_rvas.csv` | Same, spreadsheet-friendly |
| `combined_rvas.json/csv` | All classes in one file |
| `extraction_report.txt` | Human-readable summary |

---

## Methodology

### Source material

- **`dump.cs`** from [Il2CppDumper](https://github.com/Perfare/Il2CppDumper) — the primary source for class layouts, field offsets, method RVAs, and namespace/TypeDefIndex data. Field offsets appear as inline comments (`// 0x20`). RVAs appear as `// RVA: 0xABCD Offset: 0x1234 VA: 0x180001234` above each method.
- **Ghidra** for disassembly and decompilation. The game binary uses image base `0x180000000`.

### RVA to Ghidra VA

```
VA = RVA + 0x180000000
```

The dump.cs `VA:` field on each method already has this applied. Use the VA directly in Ghidra's Go To Address (G key).

> ⚠️ Do not use RVAs from dummy DLL stubs — only RVAs from `dump.cs` are accurate.

### IL2CPP patterns to recognise

| Pattern | Meaning |
|---|---|
| `FUN_180427b00(&DAT_...)` | `il2cpp_runtime_class_init()` — lazy static init guard |
| `*(classStatic + 0xb8)` | Pointer to static field storage for that class |
| `*(fieldStorage + 0x00)` | First static field (often a singleton instance) |
| `*(classStatic + 0xe4) == 0` | Class not yet runtime-initialised; init needed |
| `FUN_180427d90()` | `NullReferenceException()` — does not return |
| `FUN_1804bad80(value, exp)` | `powf(value, exponent)` |
| `FUN_180426e50(ptr, val)` | IL2CPP write barrier (GC notification) |
| `FUN_18152f9b0(&iter, class)` | Dictionary/list enumerator `MoveNext()` |
| `FUN_180cbab80(&out, list, class)` | `GetEnumerator()` on a list |

### Dumps are not committed

`dump.cs` and the game binary are not stored in this repo. Place them locally and reference them with the tools. The extracted JSON/CSV outputs and human-readable reports are committed instead.

---

## Game Version

Investigations were performed against a specific build of Menace. Binary details are not documented here — check the investigation-specific `REPORT.md` for any version-relevant notes.

---

## Contributing / Adding an Investigation

1. Create a folder under `investigations/<system-name>/`.
2. Run `extract_rvas.py` for the relevant classes and commit the output JSON/CSV to the folder.
3. Document findings in `REPORT.md` — class layouts, field offsets, method VAs, inferences, open questions.
4. Document disassembled functions in `RECONSTRUCTIONS.md` — raw Ghidra output followed by annotated C reconstruction with all offsets resolved.
5. Update this README with a summary entry under **Current Investigations**.

The bar for "complete" is: someone with no prior context on this system should be able to read the report and understand exactly what the code does, without opening Ghidra.
