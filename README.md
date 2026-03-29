# Menace — Reverse Engineering Notes

Ongoing reverse engineering of **Menace**, a Unity IL2CPP tactical strategy game. This repository documents internal game systems at the function and data-structure level — scoring models, AI pipelines, class layouts, and runtime behaviour — derived from Il2CppDumper output and Ghidra disassembly.

The goal is a permanent reference.

---

## Repository Structure

```
menace-re/
├── README.md
├── tools/
│   ├── extract_rvas.py                  # Il2CppDumper dump.cs parser (see Tools section)
│   └── (dump.cs, targets.txt — not committed, see below)
├── skills/
└── investigations/
    └── tactical-ai/
        ├── TacticalStateSettings/       # Legacy — produced before the stage model
        │   ├── REPORT.md                # Legacy — produced before the stage model
        │   └── RECONSTRUCTIONS.md       # Legacy — produced before the stage model            
        └── Criterions/                  # Namespace-level investigation folder
            ├── decompiled-functions/
            │   └── (decompiled-functions-1.txt, etc.)
            ├── stage-1/
            │   ├── REPORT.md            # Stage artefact — this stage's findings only
            │   └── RECONSTRUCTIONS.md   # Stage artefact — this stage's reconstructions only
            ├── stage-2/
            │   ├── REPORT.md
            │   └── RECONSTRUCTIONS.md
            ├── REPORT.md                # Final collated report — produced at investigation close
            └── RECONSTRUCTIONS.md       # Final collated reconstructions
```

Each investigation targets a specific namespace within a system. Stage artefacts are saved per-stage and collated into a final pair at the namespace root when the investigation closes. Additional namespaces follow the same pattern under their system folder.

---

## Current Investigations

This section is for open investigations only. This includes components of a larger investigation not yet completed. Once an investigation is complete, and most open questions have been answered, move this summary to a new file in preperation for the next investigation target.

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
- `Behavior` subclass implementations
- `FUN_181430ac0` — the per-attack evaluator called from `GetOpportunityLevel`

### Criterion subclasses

**Status:** Complete (one `Evaluate` override deferred; all other namespace members fully analysed).

Covers the full `Menace.Tactical.AI.Behaviors.Criterions` namespace — the concrete tile evaluators that write raw `SafetyScore`/`UtilityScore` values per tile.

**What is fully understood:**

- All 11 `Criterion` subclasses enumerated and their roles confirmed
- `Criterion.Score` — the master four-component weighted utility formula, scaled by a movement effectiveness curve — fully reconstructed
- `Criterion.GetUtilityThreshold` — the threshold gate formula — fully reconstructed
- `CoverAgainstOpponents.Evaluate` — three-phase cover-quality evaluator — fully reconstructed
- `ThreatFromOpponents.Evaluate`, `Score (A)`, `Score (B)` — the dominant criterion by computation budget; 4 worker threads, spatial scan with direction and distance multipliers — fully reconstructed
- `ConsiderZones.Evaluate` and `ConsiderZones.PostProcess` — zone-flag bitmask system; objective-tile promotion via threshold bypass — fully reconstructed
- `DistanceToCurrentTile.Evaluate`, `ExistingTileEffects.Evaluate`, `AvoidOpponents.Evaluate`, `FleeFromOpponents.Evaluate` — all fully reconstructed
- `Roam.Collect` and `WakeUp.Collect` — special-case collection passes (melee-only bounding-box scan; wakeup flag dispatch respectively) — fully reconstructed
- 5 infrastructure functions: `GetTileScoreComponents`, `GetMoveRangeData`, `GetTileZoneModifier`, `IsWithinRangeA`, `IsWithinRangeB` — fully reconstructed
- 30+ field offsets confirmed across `TacticalAISettings`, `EvaluationContext`, `Unit`, `MovePool`, `MoveRangeData`, `TileModifier`, `ScoringContext`, `Tile`, and auxiliary objects

**Primary files:**
- [`investigations/tactical-ai/Criterions/REPORT.md`](investigations/tactical-ai/Criterions/REPORT.md)
- [`investigations/tactical-ai/Criterions/RECONSTRUCTIONS.md`](investigations/tactical-ai/Criterions/RECONSTRUCTIONS.md)

**The scoring pipeline (short version):**
```
For each tile T and active Criterion C:
  1. C.IsValid()      → gate; skip if false
  2. C.Collect()      → populate candidate tile list (Roam, WakeUp override)
  3. C.Evaluate() ×N  → write delta to ctx.accumulatedScore / ctx.thresholdAccumulator
  4. C.PostProcess()  → second-pass adjustment (ConsiderZones overrides)
  5. Criterion.Score(tile) = (W_attack × attackScore × healthBonus × rangeBonus
                            + W_ammo × ammoScore
                            + W_deploy × deployScore
                            + W_sniper × sniperScore) × moveEffectiveness
  6. Keep tile if Score > GetUtilityThreshold()
```

**What is NOT yet covered:**
- `ConsiderSurroundings.Evaluate` — the one `Evaluate` override not yet decompiled
- `ConsiderZones.Collect` — deferred alongside the above
- All 10 `IsValid` implementations — interface documented; structurally predictable, low priority
- `TacticalAISettings` field offsets `0x100`–`0x140`
- Runtime values of the `COVER_PENALTIES[4]` static array

### Behavior subclasses

This section will be rewritten upon investigation completion.

Preliminary investigation opened
- Extraction Report: done
- Stage 1: tbd
- Collation: Waiting on prior stage completion

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

### Setup

1. Create a folder under `investigations/<system-name>/<Namespace>/`.
2. Run `enumerate_namespace.py` example:`python enumerate_namespace.py dump.cs --namespace Menace.Tactical.AI.Behaviors.Criterions --out targets.txt`
3. Run `extract_rvas.py` for the target namespace and commit the output JSON/CSV to that folder.
4. Update this README with a summary entry under **Current Investigations**.

### Session open

Provide the agent with:
- `Research-AI.md` — attached
- **First Session Only:** The extraction report for the target namespace — attached
- The handoff prompt from the previous stage — pasted as the opening message (Stage 1 only: omit, the agent will establish the entry point from the extraction report)

Do not attach any stage artefact files. These remain on disk and are not loaded into active sessions.

### At a stage boundary

Provide the agent with `Handoff-AI.md` — attached. The agent will invoke the `research-handoff` skill and produce, in order:

1. **Stage REPORT.md** — save to `investigations/<system-name>/<Namespace>/stage-<N>/REPORT.md`
2. **Stage RECONSTRUCTIONS.md** — save to `investigations/<system-name>/<Namespace>/stage-<N>/RECONSTRUCTIONS.md`
3. **Handoff prompt** — copy this block. Open a new conversation and provide it as the opening message alongside the files listed under Session open above.

### At investigation close

When the final stage is complete, open a collation session and provide:
- `Research-AI.md` and `Handoff-AI.md` — attached
- All stage `REPORT.md` files — attached
- All stage `RECONSTRUCTIONS.md` files — attached
- The extraction report — attached

The agent will produce the final collated `REPORT.md` and `RECONSTRUCTIONS.md`. Save these to the namespace root:
- `investigations/<system-name>/<Namespace>/REPORT.md`
- `investigations/<system-name>/<Namespace>/RECONSTRUCTIONS.md`

The bar for "complete" is: someone with no prior context on this system should be able to read the report and understand exactly what the code does, without opening Ghidra.
