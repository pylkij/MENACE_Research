# Menace Tactical AI System — Reverse Engineering Report

**Game:** Menace (Unity, IL2CPP, HDRP)
**Binary:** Windows x64, image base `0x180000000`
**Source material:** Il2CppDumper `dump.cs` (32.6 MB, 885,863 lines), Ghidra disassembly
**Status:** Complete. The full scoring pipeline is understood end-to-end.

---

## Table of Contents

1. [Investigation Overview](#1-investigation-overview)
2. [Tooling](#2-tooling)
3. [Class Inventory](#3-class-inventory)
4. [The Scoring Formula](#4-the-scoring-formula)
5. [Full Pipeline — End to End](#5-full-pipeline--end-to-end)
6. [AIWeightsTemplate — Complete Field Reference](#6-aiweightstemplate--complete-field-reference)
7. [Class: TacticalStateSettings](#7-class-tacticalstatesettings)
8. [Class: TileScore](#8-class-tilescore)
9. [Class: Agent](#9-class-agent)
10. [Class: TacticalState](#10-class-tacticalstate)
11. [Class: AIWeightsTemplate](#11-class-aiweightstemplate)
12. [Class: DebugVisualization / DebugVisualizationFilter](#12-class-debugvisualization--debugvisualizationfilter)
13. [Class: MovementResult](#13-class-movementresult)
14. [Ghidra Address Reference](#14-ghidra-address-reference)
15. [Key Inferences and Design Notes](#15-key-inferences-and-design-notes)
16. [Open Questions](#16-open-questions)

---

## 1. Investigation Overview

The goal of this investigation was to reverse-engineer the tactical AI scoring system of the Unity IL2CPP game **Menace**, starting from a debug settings class (`TacticalStateSettings`) and following the call chain inward until the complete tile-scoring formula and weighting model were understood.

### What was achieved

- The complete tile scoring formula is known, including all weights, exponents, and per-actor multipliers.
- The full evaluation pipeline is reconstructed: criterion dispatch → per-tile scoring → post-processing (POW/Scale) → neighbor propagation → behavior selection → agent priority scoring.
- All relevant classes are extracted with field offsets, method RVAs, and Ghidra VAs.
- The threading model for tile evaluation is understood.
- The two-pass criterion evaluation pattern and its purpose are confirmed.
- All `AIWeightsTemplate` fields are named and offset-mapped.

### What was NOT investigated

- Individual `Criterion` subclass implementations (the concrete classes that write into `TileScore` fields). These are identifiable via vtable dispatch from `Agent.Evaluate()` and would be the next layer to reverse.
- `Behavior` subclass implementations (`PickBehavior`, `SortBehaviors`).
- `FUN_181430ac0` — the per-attack evaluator called from `GetOpportunityLevel()`.
- Network/multiplayer synchronisation of AI state.

---

## 2. Tooling

### extract_rvas.py

A Python script written during this investigation that extracts class metadata from a standard Il2CppDumper `dump.cs` file. Output includes per-class JSON/CSV with field offsets and method RVAs, a combined output, and a human-readable report.

**Usage:**
```bash
# Single class
python extract_rvas.py dump.cs --class TacticalStateSettings --namespace Menace.States --out ./output

# Multiple classes from list file
python extract_rvas.py dump.cs --class-list targets.txt --out ./output
```

**targets.txt format** (namespace is optional):
```
TacticalStateSettings   Menace.States
TileScore
Agent
AIWeightsTemplate
DebugVisualization
```

**Output files:**

| File | Contents |
|---|---|
| `<ClassName>_rvas.json` | Per-class methods + fields with RVAs |
| `<ClassName>_rvas.csv` | Same, spreadsheet-friendly |
| `combined_rvas.json/csv` | All extracted classes in one file |
| `extraction_report.txt` | Human-readable summary |

**Known parser behaviour:**

- Namespace comment may be separated from the class declaration by attribute lines (e.g. `[DisallowMultipleComponent]`). The parser scans upward past these correctly.
- Attribute lines between an `// RVA:` comment and the method declaration (e.g. `[UsedImplicitly]` before `// RVA: ...` before `private void AssignSkill()`) are handled correctly.
- Methods with `RVA: -1` are captured and flagged `[UNRESOLVED]`.
- `void` is intentionally excluded from the keyword blacklist — it is a valid return type.

**Bug history (fixed):** The initial version had `void` in `KEYWORD_BLACKLIST`, causing all `void`-returning methods to be silently dropped. A second bug checked the return type (not just the method name) against the blacklist. Both are fixed in the current version.

### Ghidra

Used for disassembly. The game binary uses image base `0x180000000`. All addresses in this report are **Virtual Addresses (VA)** in the form `0x180xxxxxx`, usable directly in Ghidra's Go To Address (G key).

**RVA to VA conversion:** `VA = RVA + 0x180000000`

**Do not use RVAs from the dummy DLL** (TacticalStateSettings.cs stub). Only use RVAs from `dump.cs`.

---

## 3. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| `TacticalStateSettings` | `Menace.States` | 1682 | Developer debug/inspector panel. Not production gameplay. |
| `TacticalState` | `Menace.States` | 1681 | Primary runtime game state singleton. |
| `TileScore` | `Menace.Tactical.AI.Data` | 3636 | Per-tile AI evaluation record. |
| `Agent` | `Menace.Tactical.AI` | 3616 | AI brain per unit. Owns the tile dictionary and drives evaluation. |
| `AIWeightsTemplate` | `Menace.Tactical.AI` | 3621 | ScriptableObject data asset holding all AI weight parameters. |
| `DebugVisualization` | `Menace.Tactical.AI` | 3610 | Enum: selects which TileScore field to display in the heatmap. |
| `DebugVisualizationFilter` | `Menace.Tactical.AI` | 3611 | Enum: filters which tiles the heatmap renders. |
| `MovementResult` | `Tactical` | 1400 | Stores the outcome of a movement action for an actor. |

---

## 4. The Scoring Formula

### Final composite score per tile

```
GetScore(TileScore ts) =
    (SafetyScore + UtilityScore)
    - (DistanceScore + DistanceToCurrentTile) × WEIGHTS.DistanceScale
```

### Scaled variant (used for heatmap display mode 2)

```
GetScaledScore(TileScore ts) =
    (SafetyScoreScaled + UtilityScoreScaled)
    - (DistanceScore + DistanceToCurrentTile) × WEIGHTS.DistancePickScale
```

### Without distance (used for UltimateTile/waypoint evaluation)

```
GetScoreWithoutDistance(TileScore ts) =
    SafetyScore + UtilityScore
```

### Important: SafetyScore sign convention

**SafetyScore is stored as a negative value** after `PostProcessTileScores`. The post-processing pipeline negates it:

```
ts.SafetyScore = -powf(...) × WEIGHTS.DistanceScale
```

This means in the composite formula, `SafetyScore + UtilityScore` naturally subtracts danger. A tile under heavy threat gets a large negative `SafetyScore`, reducing the total. The naming reflects the AI's goal (seek safety) but the stored value is a penalty.

### Weight source

All weights come from `AIWeightsTemplate`, accessed via `DebugVisualization.WEIGHTS` (static field at `+0x08` on the `DebugVisualization` class static storage). This is a `ScriptableObject` asset loaded at runtime.

```
DebugVisualization.WEIGHTS        → AIWeightsTemplate instance
    WEIGHTS + 0x40 = DistanceScale       (used in GetScore)
    WEIGHTS + 0x44 = DistancePickScale   (used in GetScaledScore)
```

---

## 5. Full Pipeline — End to End

```
┌─────────────────────────────────────────────────────────────────┐
│  Agent.Evaluate()  [0x180719860]                                │
│                                                                 │
│  1. Reset: m_Score=0, m_ActiveBehavior=null, m_State=None       │
│  2. Copy m_Tiles → m_TilesToBeUsed  (double-buffer swap)        │
│  3. Actor liveness check (active, not dead, not deactivating)   │
│  4. Iteration budget check (MAX_ITERATIONS=16, unless           │
│     TacticalState.IsStandalone)                                 │
│  5. Sleep check (m_SleepUntil vs faction clock)                 │
│  6. Moving check (yield if actor is in motion)                  │
│                                                                 │
│  ── STATE 1: EVALUATING ──────────────────────────────────────  │
│                                                                 │
│  7. Criterion Pass 1 — for each Criterion in S_CRITERIONS:      │
│       if c.IsApplicable(actor):                                 │
│           c.EvaluateTile(actor, tileScore)  [per tile]          │
│     → Writes raw scores into TileScore fields                   │
│     → Threaded if tileCount > tilesPerThread × 2               │
│     → Vehicles halve their tilesPerThread budget               │
│                                                                 │
│  8. PostProcessTileScores()  [0x18071C450]                      │
│     Per tile:                                                   │
│       UtilityScore += UtilityByAttacksScore                     │
│       UtilityScore = powf(UtilityScore, UtilityPOW)             │
│       UtilityScore = powf(unitUtilityMult                       │
│                           × UtilityScore                        │
│                           × UtilityScale, UtilityPostPOW)       │
│       UtilityScore ×= UtilityPostScale                          │
│                                                                 │
│       SafetyScore = powf(SafetyScore, SafetyPOW)               │
│       SafetyScore = powf(unitSafetyMult                         │
│                          × SafetyScore                          │
│                          × SafetyScale, SafetyPostPOW)          │
│       SafetyScore = −SafetyScore × DistanceScale  ← NEGATED    │
│                                                                 │
│     Neighbor propagation (if m_Flags bit 0 set):               │
│       For each tile, check 8 neighbors                          │
│       HighestSafetyNeighbor  → neighbor with ≥2× safety        │
│       HighestUtilityNeighbor → neighbor with ≥2× utility       │
│                                                                 │
│  9. Criterion Pass 2 — for each Criterion in S_CRITERIONS:      │
│       if c.IsApplicable(actor):                                 │
│           c.PostEvaluate(actor, m_Tiles)                        │
│     → Runs on already-normalized scores                         │
│     → UtilityByAttacksScoreCandidate → UtilityByAttacksScore   │
│        commit likely happens here                               │
│                                                                 │
│  ── STATE 2: SCORED ──────────────────────────────────────────  │
│                                                                 │
│  10. PickBehavior()  [0x18071BD20]                              │
│      → SortBehaviors() using TileScore.CompareScores()          │
│      → Selects m_ActiveBehavior                                 │
│                                                                 │
│  ── STATE 3: DONE ────────────────────────────────────────────  │
│                                                                 │
│  11. Compute m_Score:                                           │
│      fMult = GetScoreMultForPickingThisAgent()                  │
│      m_Score = max(1, (int)(fMult × activeBehavior.baseScore))  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  TileScore.GetScore()  [0x180740F20]                            │
│                                                                 │
│  return (SafetyScore + UtilityScore)                            │
│       - (DistanceScore + DistanceToCurrentTile)                 │
│         × WEIGHTS.DistanceScale                                 │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  TileScore.CompareScores()  [0x180740D40]                       │
│                                                                 │
│  Descending comparator on GetScore().                           │
│  Returns 0xFFFFFFFF if a > b, 1 if a < b, 0 if equal.          │
│  Used by PickBehavior sort to select highest-scoring tile.      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. AIWeightsTemplate — Complete Field Reference

`AIWeightsTemplate` is a `ScriptableObject` (`[CreateAssetMenu]` with path "Menace/Config/AI Weights"). It is accessed globally via `DebugVisualization.WEIGHTS` (static field offset `+0x08`).

**General section:**

| Offset | Field | Range | Role |
|---|---|---|---|
| `0x18` | `BehaviorScorePOW` | 0–4 | Exponent shaping the final agent behavior score curve |
| `0x1C` | `TTL_MAX` | 1–10 | Maximum time-to-live for an agent evaluation cycle |
| `0x20` | `UtilityPOW` | 0–4 | Exponent applied to raw UtilityScore before scaling |
| `0x24` | `UtilityScale` | 0–999 | Scale multiplier on UtilityScore after POW |
| `0x28` | `UtilityPostPOW` | 0–4 | Exponent applied to scaled UtilityScore |
| `0x2C` | `UtilityPostScale` | 0–999 | Final multiplier on UtilityScore |
| `0x30` | `SafetyPOW` | 0–4 | Exponent applied to raw SafetyScore before scaling |
| `0x34` | `SafetyScale` | 0–999 | Scale multiplier on SafetyScore after POW |
| `0x38` | `SafetyPostPOW` | 0–4 | Exponent applied to scaled SafetyScore |
| `0x3C` | `SafetyPostScale` | 0–999 | Final multiplier on SafetyScore (applied before negation) |
| `0x40` | `DistanceScale` | 0–999 | Distance penalty weight in `GetScore()`. Also used to negate SafetyScore in PostProcessTileScores. |
| `0x44` | `DistancePickScale` | 0–999 | Distance penalty weight in `GetScaledScore()` |
| `0x48` | `ThreatLevelPOW` | 0–2 | Exponent on threat level sum in `GetThreatLevel()` |
| `0x4C` | `OpportunityLevelPOW` | 0–2 | Exponent on opportunity score in `GetOpportunityLevel()` |
| `0x50` | `PickingScoreMultPOW` | 0–2 | Exponent in `GetScoreMultForPickingThisAgent()` |

**Position Criterions section** (inputs to SafetyScore / UtilityScore):

| Offset | Field | Range |
|---|---|---|
| `0x54` | `DistanceToCurrentTile` | 0–50 |
| `0x58` | `DistanceToZones` | 0–50 |
| `0x5C` | `DistanceToAdvanceZones` | 0–50 |
| `0x60` | `SafetyOutsideDefendZones` | 0–50 |
| `0x64` | `SafetyOutsideDefendZonesVehicles` | 0–50 |
| `0x68` | `OccupyZoneValue` | 0–50 |
| `0x6C` | `CaptureZoneValue` | 0–50 |
| `0x70` | `CoverAgainstOpponents` | 0–100 |
| `0x74` | `ThreatFromOpponents` | 0–50 |
| `0x78` | `ThreatFromTileEffects` | 0–500 |
| `0x7C` | `ThreatFromOpponentsDamage` | 0–5 |
| `0x80` | `ThreatFromOpponentsArmorDamage` | 0–5 |
| `0x84` | `ThreatFromOpponentsSuppression` | 0–5 |
| `0x88` | `ThreatFromOpponentsStun` | 0–5 |
| `0x8C` | `ThreatFromPinnedDownOpponents` | 0–5 |
| `0x90` | `ThreatFromSuppressedOpponents` | 0–5 |
| `0x94` | `ThreatFrom2xStunnedOpponents` | 0–5 |
| `0x98` | `ThreatFromFleeingOpponents` | 0–5 |
| `0x9C` | `ThreatFromOpponentsAlreadyActed` | 0–5 |
| `0xA0` | `ThreatFromOpponentsButAlliesInControl` | 0–5 |
| `0xA4` | `ThreatFromOpponentsAtHypotheticalPositionsMult` | 0–5 |
| `0xA8` | `ThreatFromOpponentsNextToVehicleMult` | 0–5 |
| `0xAC` | `AllyMetascoreAgainstThreshold` | 0–100 |
| `0xB0` | `AvoidAlliesPOW` | 0–10 |
| `0xB4` | `AvoidOpponentsPOW` | 0–10 |
| `0xB8` | `FleeFromOpponentsPOW` | 0–10 |
| `0xBC` | `ScalePositionWithTags` | 0–10 |
| `0xC0` | `IncludeAttacksAgainstAllOpponentsMult` | 0–10 |
| `0xC4` | `OppositeSideDistanceFromOpponentCap` | 0–99 (int) |
| `0xC8` | `CullTilesDistances` | 0–99 (int) |

**Deployment section:**

| Offset | Field | Range |
|---|---|---|
| `0xCC` | `DistanceToZoneDeployScore` | 0–50 |
| `0xD0` | `DistanceToAlliesScore` | 0–50 |
| `0xD4` | `CoverInEachDirectionBonus` | 0–50 |
| `0xD8` | `InsideBuildingDuringDeployment` | 0–500 |
| `0xDC` | `DeploymentConcealmentMult` | 0–100 |

**General Attack Behavior section:**

| Offset | Field | Range |
|---|---|---|
| `0xE0` | `InvisibleTargetValueMult` | 0–2 |
| `0xE4` | `TargetValueDamageScale` | 0–10 |
| `0xE8` | `TargetValueArmorScale` | 0–10 |
| `0xEC` | `TargetValueSuppressionScale` | 0–10 |
| `0xF0` | `TargetValueStunScale` | 0–10 |
| `0xF4` | `TargetValueThreatScale` | 0–10 |
| `0xF8` | `TargetValueMaxThreatSuppressScale` | 0–10 |
| `0xFC` | `ScoreThresholdWithLimitedUses` | 0–10 |
| `0x100` | `FriendlyFirePenalty` | 0–50 |

**Inflict Damage Behavior:**

| Offset | Field | Range |
|---|---|---|
| `0x104` | `DamageBaseScore` | — |
| `0x108` | `DamageScoreMult` | 0–50 |
| `0x10C` | `InflictDamageFromTile` | 0–200 |

**Inflict Suppression Behavior:**

| Offset | Field | Range |
|---|---|---|
| `0x110` | `SuppressionBaseScore` | — |
| `0x114` | `SuppressionScoreMult` | 0–50 |
| `0x118` | `InflictSuppressionFromTile` | 0–90 |

**Stun Behavior:**

| Offset | Field | Range |
|---|---|---|
| `0x11C` | `StunBaseScore` | — |
| `0x120` | `StunScoreMult` | 0–50 |
| `0x124` | `StunFromTile` | 0–90 |

**Move Behavior:**

| Offset | Field | Range |
|---|---|---|
| `0x128` | `MoveBaseScore` | — |
| `0x12C` | `MoveScoreMult` | 0–50 |
| `0x130` | `NearTileLimit` | 1–999 (int) |
| `0x134` | `TileScoreDifferenceMult` | 0–2 |
| `0x138` | `TileScoreDifferencePow` | 0–2 |
| `0x13C` | `UtilityThreshold` | 0–100 |
| `0x140` | `PathfindingSafetyCostMult` | 0–100 |
| `0x144` | `PathfindingUnknownTileSafety` | 0–1000 |
| `0x148` | `PathfindingHiddenFromOpponentsBonus` | 0–100 (int) |
| `0x14C` | `EntirePathScoreContribution` | 0–1 |
| `0x150` | `MoveIfNewTileIsBetterBy` | 0–10 |
| `0x154` | `GetUpIfNewTileIsBetterBy` | 0–10 |
| `0x158` | `DistanceTooFarForOneTurnMult` | 0–50 |
| `0x15C` | `ConsiderAlternativeIfBetterBy` | 1–2 |
| `0x160` | `ConsiderAlternativeToUltimateIfBetterBy` | 1–2 |
| `0x164` | `EnoughAPToPerformSkillAfterwards` | 1–2 |
| `0x168` | `EnoughAPToPerformOnlySkillAfterwards` | 1–2 |
| `0x16C` | `EnoughAPToDeployAfterwards` | 1–2 |

**Buff Behavior:**

| Offset | Field | Range |
|---|---|---|
| `0x170` | `BuffBaseScore` | — |
| `0x174` | `BuffTargetValueMult` | 0–10 |
| `0x178` | `BuffFromTile` | 0–200 |
| `0x17C` | `RemoveSuppressionMult` | 0–10 |
| `0x180` | `RemoveStunnedMult` | 0–10 |
| `0x184` | `RestoreMoraleMult` | 0–10 |
| `0x188` | `IncreaseMovementMult` | 0–10 |
| `0x18C` | `IncreaseOffensiveStatsMult` | 0–10 |
| `0x190` | `IncreaseDefensiveStatsMult` | 0–10 |

**Supply Ammo Behavior:**

| Offset | Field | Range |
|---|---|---|
| `0x194` | `SupplyAmmoBaseScore` | — |
| `0x198` | `SupplyAmmoTargetValueMult` | 0–10 |
| `0x19C` | `SupplyAmmoNoAmmoMult` | 0–10 |
| `0x1A0` | `SupplyAmmoSpecialWeaponMult` | 0–10 |
| `0x1A4` | `SupplyAmmoGoalThreshold` | 0–1 |
| `0x1A8` | `SupplyAmmoFromTile` | 0–200 |

**Target Designator Behavior:**

| Offset | Field | Range |
|---|---|---|
| `0x1AC` | `TargetDesignatorBaseScore` | — |
| `0x1B0` | `TargetDesignatorScoreMult` | 0–50 |
| `0x1B4` | `TargetDesignatorFromTile` | 0–90 |

**Gain Bonus Turn Behavior:**

| Offset | Field | Range |
|---|---|---|
| `0x1B8` | `GainBonusTurnBaseMult` | — |

---

## 7. Class: TacticalStateSettings

**Namespace:** `Menace.States`
**TypeDefIndex:** 1682
**Base:** `MonoBehaviour`
**Role:** Developer/debug inspector panel attached to a persistent scene object. Not a production gameplay class. Provides runtime toggles for fog of war, AI execution, heatmap visualization, and debug entity spawning/state injection. All functionality serves inspection and testing, not live gameplay.

### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| `0x020` | `bool` | `ShowFogOfWar` | Triggers `OnFogOfWarChanged()` |
| `0x021` | `bool` | `RunAI` | Enables/disables AI execution |
| `0x022` | `bool` | `DryrunOnly` | AI computes but does not commit decisions |
| `0x024` | `DebugVisualization` | `ShowHeatmap` | Selects score dimension to render |
| `0x028` | `DebugVisualizationFilter` | `Filter` | Filters which tiles are drawn |
| `0x030` | `GameObject` | `HeatmapParent` | Parent object for heatmap tokens (has `[Space(20)]`) |
| `0x038` | `GameObject` | `HeatmapToken` | Prefab instantiated per tile |
| `0x040` | `float` | `HeatmapExpectedMaxValue` | Normalization ceiling for color ramp |
| `0x048` | `List<Color>` | `HeatmapColors` | Color gradient for score visualization |
| `0x050` | `Dictionary<Tile, TileScore>` | `m_Tiles` | Runtime tile score cache (private) |
| `0x058` | `EntityTemplate` | `ActorToSpawn` | Debug entity spawn target |
| `0x060` | `FactionType` | `Faction` | Faction for spawned entity |
| `0x068` | `SkillTemplate` | `SkillToAssign` | Debug skill injection |
| `0x070` | `SuppressionState` | `SuppressionToAssign` | Debug suppression injection |
| `0x074` | `MoraleState` | `MoraleToAssign` | Debug morale injection |
| `0x078` | `TileEffectTemplate` | `TileEffectToSpawn` | Debug tile effect spawn |
| `0x080` | `DecalCollection` | `DecalToSpawn` | Debug decal spawn |

### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Start()` | `0x757530` | `0x180757530` | Registers `OnFogOfWarChanged`, handles `ShowHeatmap` change detection, calls `DrawHeatmap` |
| `OnFogOfWarChanged()` | `0x7570B0` | `0x1807570B0` | Pushes `ShowFogOfWar` to render system |
| `OnRunAIChanged()` | `0x757140` | `0x180757140` | Pushes `RunAI` to AI controller |
| `OnDryrunAIChanged()` | `0x757030` | `0x180757030` | Pushes `DryrunOnly` to AI controller |
| `OnAIHeatmapChanged()` | `0x756F00` | `0x180756F00` | Triggers heatmap redraw |
| `OnAIDestinationOnlyChanged()` | `0x756EA0` | `0x1807​56EA0` | Pushes `Filter` (offset `0x28`) to `DebugVisualization` static field `+0x4`. Despite the name, maps to the `Filter` field. |
| `DrawHeatmap()` | `0x756180` | `0x180756180` | Iterates `m_Tiles`, applies `Filter`, instantiates `HeatmapToken` per tile, colors by score |
| `GetScore()` | `0x756DE0` | `0x180756DE0` | Switch on `ShowHeatmap`, returns appropriate float field from `TileScore` |
| `SpawnEntity()` | `0x7572F0` | `0x1807572F0` | Uses `ActorToSpawn` + `Faction` + `TacticalState.m_CurrentTile` |
| `Delete()` | `0x755FE0` | `0x180755FE0` | Removes entity at current tile |
| `Destroy()` | `0x7560B0` | `0x1807560B0` | Destroys GameObject |
| `TakeControl()` | `0x757720` | `0x180757720` | Sets `TacticalState.m_CurrentAction` |
| `AssignSkill()` | `0x755D90` | `0x180755D90` | Calls `TacticalState.TrySelectSkill()` with `SkillToAssign` (`[UsedImplicitly]`) |
| `AssignSuppression()` | `0x755F00` | `0x180755F00` | Injects `SuppressionToAssign` (`[UsedImplicitly]`) |
| `AssignMorale()` | `0x755CB0` | `0x180755CB0` | Injects `MoraleToAssign` (`[UsedImplicitly]`) |
| `SpawnTileEffect()` | `0x757420` | `0x180757420` | Uses `TileEffectToSpawn` (`[UsedImplicitly]`) |
| `SpawnDecal()` | `0x7571D0` | `0x1807571D0` | Uses `DecalToSpawn` (`[UsedImplicitly]`) |
| `.ctor()` | `0x7577F0` | `0x1807577F0` | Constructor |

### `Start()` behaviour — summary

- Registers `OnFogOfWarChanged` callback with the render system via `FUN_180634b80`.
- Detects changes to `ShowHeatmap` (compares against a static copy on `DebugVisualization`).
- On change: destroys existing heatmap tokens under `HeatmapParent` (via `GetComponentsInChildren`-style call + `Destroy`), commits new value to static, then calls `DrawHeatmap` if `ShowHeatmap != None` and `m_Tiles` is non-empty.

### `GetScore()` dispatch table

| `ShowHeatmap` value | Enum name | Returns |
|---|---|---|
| 0 | `None` | 0.0 (default) |
| 1 | `TotalScore` | `TileScore.GetScore()` |
| 2 | `TotalScoreScaled` | `TileScore.GetScaledScore()` |
| 3 | `Utility` | `ts.UtilityScore` (`+0x30`) |
| 4 | `Safety` | `ts.SafetyScore` (`+0x28`) |
| 5 | `SafetyScaled` | `ts.SafetyScoreScaled` (`+0x2C`) |
| 6 | `Distance` | `ts.DistanceToCurrentTile × -100.0` (`+0x20 × -100`) |

Note: Case 6 multiplies by `-100.0` for display. Distance is a penalty (negative contribution to score); this inverts it to a positive display value and scales it to a human-readable range.

### `OnAIDestinationOnlyChanged()` — resolved

Despite the method name suggesting a "destination only" toggle, the implementation reads `self->Filter` (offset `0x28`, type `DebugVisualizationFilter`) and writes it to `DebugVisualization` static at offset `+0x4`. The method name is an artefact of an older naming convention — "DestinationOnly" was the old name for what became the `Destinations` enum value of `DebugVisualizationFilter`.

---

## 8. Class: TileScore

**Namespace:** `Menace.Tactical.AI.Data`
**TypeDefIndex:** 3636
**Role:** Per-tile AI evaluation record. One instance per candidate tile in the movement dictionary. Holds all scoring dimensions, pathfinding metadata, and neighbor references. Passed to `DrawHeatmap` for visualization.

### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| `0x010` | `Tile` | `Tile` | The candidate tile being scored |
| `0x018` | `Tile` | `UltimateTile` | Final destination if movement continues (waypoint scoring) |
| `0x020` | `float` | `DistanceToCurrentTile` | Raw AP distance from current position |
| `0x024` | `float` | `DistanceScore` | Scored distance → maps to `DebugVisualization.Distance` |
| `0x028` | `float` | `SafetyScore` | **Stored negative after PostProcessTileScores.** Threat penalty. |
| `0x02C` | `float` | `SafetyScoreScaled` | Normalized safety → `DebugVisualization.SafetyScaled` |
| `0x030` | `float` | `UtilityScore` | Attack opportunity value → `DebugVisualization.Utility` |
| `0x034` | `float` | `UtilityScoreScaled` | Normalized utility |
| `0x038` | `float` | `UtilityByAttacksScore` | Attack-opportunity component (committed value) |
| `0x03C` | `float` | `UtilityByAttacksScoreCandidate` | Proposed attack utility before commit — two-pass evaluation |
| `0x040` | `int` | `APCost` | AP cost to reach this tile |
| `0x044` | `int` | `MinimumUtilityAPCost` | AP threshold below which utility scoring applies |
| `0x048` | `List<Vector3>` | `Path` | World-space path to this tile |
| `0x050` | `TileScore` | `HighestSafetyNeighbor` | Best adjacent tile by SafetyScore (set in PostProcessTileScores) |
| `0x058` | `TileScore` | `HighestUtilityNeighbor` | Best adjacent tile by UtilityScore (set in PostProcessTileScores) |

### Key methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| `GetScore()` | `0x740F20` | `0x180740F20` | Composite score formula. Primary AI scoring target. |
| `GetScaledScore()` | `0x740E50` | `0x180740E50` | Same formula but using scaled variants + DistancePickScale |
| `GetScoreWithoutDistance()` | `0x740F10` | `0x180740F10` | `SafetyScore + UtilityScore` only. Used for UltimateTile evaluation. |
| `CompareScores()` | `0x740D40` | `0x180740D40` | Descending comparator on `GetScore()`. Used by sort/priority queue. |

### `UtilityByAttacksScoreCandidate` — two-pass pattern

The presence of both `UtilityByAttacksScore` (committed) and `UtilityByAttacksScoreCandidate` (proposed) confirms a two-pass evaluation system. During Criterion Pass 1, attack utility is written to `Candidate`. During `PostProcessTileScores`, `UtilityByAttacksScore` is added into `UtilityScore`. During Criterion Pass 2 (`PostEvaluate`), the candidate is validated and committed — or discarded — based on post-normalized scores.

### `HighestSafetyNeighbor` / `HighestUtilityNeighbor` — propagation

Set during `PostProcessTileScores` Pass 2. A neighbor qualifies only if:
- It is not the same tile as self.
- Its score is `≥ 2× current` (if current score is non-negative), or `≤ 0.5× current` (if current score is negative).

This is a **one-step lookahead**, not BFS or Dijkstra. The threshold is meaningful — a neighbor needs to be substantially better, not just marginally, to be recorded.

---

## 9. Class: Agent

**Namespace:** `Menace.Tactical.AI`
**TypeDefIndex:** 3616
**Role:** The AI brain for a single unit. Owns the tile evaluation dictionary, manages behaviors, drives the full evaluation loop. One `Agent` per AI-controlled actor.

### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| `0x00` | `List<Criterion>` | `S_CRITERIONS` | **Static.** Shared list of all criterion evaluators. |
| `0x10` | `AIFaction` | `m_Faction` | The AI faction this agent belongs to |
| `0x18` | `Actor` | `m_Actor` | The unit this agent controls (readonly) |
| `0x20` | `List<Behavior>` | `m_Behaviors` | Available behaviors (readonly) |
| `0x28` | `Behavior` | `m_ActiveBehavior` | Selected behavior for this evaluation cycle |
| `0x30` | `int` | `m_Score` | Final priority score for agent selection |
| `0x34` | `float` | `m_Priority` | Base priority |
| `0x38` | `int` | `m_NumThreatsFaced` | Number of threats the agent faces |
| `0x3C` | `Agent.State` | `m_State` | Evaluation state: 0=None, 1=Evaluating, 2=Scored, 3=Done |
| `0x40` | `PseudoRandom` | `m_Random` | Per-agent RNG (readonly) |
| `0x48` | `int` | `m_Iterations` | Evaluation iteration count (capped at MAX_ITERATIONS=16) |
| `0x4C` | `float` | `m_SleepUntil` | Game time until which this agent is sleeping |
| `0x50` | `bool` | `m_IsDeployed` | Whether the agent has been deployed |
| `0x51` | `bool` | `m_IsSleeping` | Sleep flag |
| `0x54` | `uint` | `m_Flags` | Bit flags. Bit 0: enables neighbor propagation in PostProcessTileScores. |
| `0x58` | `Dictionary<Tile, TileScore>` | `m_Tiles` | Primary tile evaluation dictionary (readonly). Read by `DrawHeatmap`. |
| `0x60` | `Dictionary<Tile, TileScore>` | `m_TilesToBeUsed` | Working copy during evaluation (double-buffer) |
| `0x68` | `List<Task>` | `m_Tasks` | Threaded evaluation tasks |
| `0x70` | `string` | `m_QueuedDebugString` | Debug log string |
| `0x78` | `bool` | `FlaggedForDeactivation` | Backing field (`[CompilerGenerated]`) |

**Constants:**
- `MAX_ITERATIONS = 16` — maximum evaluation cycles before forced sleep
- `MIN_TILES_PER_THREAD = 2` — minimum tiles per thread for threaded evaluation

### Key methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Evaluate()` | `0x719860` | `0x180719860` | Full evaluation loop. See Section 5 and RECONSTRUCTIONS.md. |
| `PostProcessTileScores()` | `0x71C450` | `0x18071C450` | POW/Scale pipeline + neighbor propagation. See RECONSTRUCTIONS.md. |
| `PickBehavior()` | `0x71BD20` | `0x18071BD20` | Selects best behavior from sorted list. |
| `GetThreatLevel()` | `0x71B240` | `0x18071B240` | Signed threat accumulator, clamped, POW-shaped. |
| `GetOpportunityLevel()` | `0x71ABC0` | `0x18071ABC0` | Best attack score across all skills/slots, POW-shaped. |
| `GetScoreMultForPickingThisAgent()` | `0x71AE50` | `0x18071AE50` | Combines threat + opportunity → agent turn priority. |
| `ScheduleCriterionEvaluation()` | `0x71CAD0` | `0x18071CAD0` | Creates a threaded task for a tile range. |
| `Execute()` | `0x71A9D0` | `0x18071A9D0` | Executes the selected behavior. |
| `Reset()` | `0x71CAA0` | `0x18071CAA0` | Resets evaluation state. |
| `GetTiles()` | `0x58AE00` | `0x18058AE00` | Returns `m_Tiles` dictionary. |
| `.cctor()` | `0x71CEC0` | `0x18071CEC0` | Static constructor — initialises `S_CRITERIONS`. |

### `Criterion` vtable interface

The `Criterion` class uses virtual dispatch. The four relevant vtable slots, confirmed from `Evaluate()` disassembly:

| Vtable offset | Method | Signature | When called |
|---|---|---|---|
| `+0x178` | `IsApplicable` | `bool(actor, defaultArg)` | Before both passes |
| `+0x198` | `Evaluate` | `void(actor, tiles)` | Pass 1 — populates raw TileScore fields |
| `+0x1a8` | `EvaluateTile` | `void(actor, tileScore)` | Per-tile, called by threaded + inline paths |
| `+0x1b8` | `PostEvaluate` | `void(actor, tiles)` | Pass 2 — after PostProcessTileScores |

### Threading model

```
if (tilesPerThread * 2 < tileCount):
    // Multi-threaded
    numThreads = tilesPerThread - 1
    for i in 0..numThreads:
        task = ScheduleCriterionEvaluation(self, i, tileCount/tilesPerThread, criterion)
        m_Tasks.Add(task)
    // Remainder tiles handled inline by calling EvaluateTile directly
    for i in (numThreads × tileCount/tilesPerThread)..tileCount:
        criterion.EvaluateTile(actor, m_Tiles[i])
    // Wait: spin on Task.IsComplete(), yield one frame (FUN_181bde4c0) while waiting
else:
    // Single-threaded: iterate m_Tiles and call EvaluateTile inline
```

Vehicles halve their `tilesPerThread` budget, meaning they require more tiles before threading is triggered and produce more threads when it is. Likely reflects that vehicle actors have fewer candidate tiles in most scenarios.

### `GetThreatLevel()` — detail

```
for each opponent threat source:
    threatValue = clamp(rawThreat, 0, 3.0)
    sign = +1.0 if threat is forward-facing, -1.0 if behind
    if actor.IsSuppressed: sign *= 0.8
    attenuation = clamp(threatCount * 0.0625, 0, 1.0)   // 0.0625 = 1/16
    accumulator += (1.0 - attenuation) * (threatValue + 1.0) * sign

return powf(accumulator, WEIGHTS.ThreatLevelPOW)
```

The attenuation term `(1.0 - clamp(count × 0.0625, 0, 1.0))` means additional threats beyond 16 contribute zero marginal threat. The `+1.0` ensures even zero-threat opponents contribute to the accumulator if their sign is relevant.

### `GetOpportunityLevel()` — detail

```
for each skill in actor.skills:
    for attackSlot in 0..2:
        score = FUN_181430ac0(skill.attacks[attackSlot], actor)  // per-attack evaluator
        bestScore = max(bestScore, score)

return powf(bestScore, WEIGHTS.OpportunityLevelPOW)
```

Only the single best attack score across all skills and all three attack slots contributes. This is an attack ceiling, not a sum.

### `GetScoreMultForPickingThisAgent()` — detail

```
// Early-out: player-controlled unit
if (TacticalState.singleton.m_DeployedUnitLeaders == self.m_Actor) return;

if (self.m_ActiveBehavior == null):
    GetOpportunityLevel(self)
GetThreatLevel(self)

// Checks: vehicle status, stealth, fleeing, Scout behavior
// Applies WEIGHTS.PickingScoreMultPOW

// Final: reads AIWeightsTemplate at offset 0x50
return powf(combinedScore, WEIGHTS.PickingScoreMultPOW)
```

The final `m_Score` written to the agent is:
```
m_Score = max(1, (int)(GetScoreMultForPickingThisAgent() × activeBehavior.baseScore))
```

---

## 10. Class: TacticalState

**Namespace:** `Menace.States`
**TypeDefIndex:** 1681
**Role:** Primary runtime game state. Singleton. Owns all tactical subsystems. Target of `TacticalStateSettings`'s `OnXChanged()` push methods.

### Selected fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| `0x000` | static | `s_Singleton` | Singleton instance — accessed via `TacticalState.Get()` |
| `0x020` | `UITactical` | `m_UI` | UI instance (instance offset; static `s_DefaultTimeScale` also at `0x020`) |
| `0x028` | `Tile` | `m_CurrentTile` | Active tile — `SpawnEntity()` spawn position |
| `0x030` | `Tile` | `m_TargetTile` | Target tile |
| `0x038` | `TacticalAction` | `m_CurrentAction` | Active action — mutated by `TakeControl()` |
| `0x048` | `bool` | `m_IsReady` | State readiness gate |
| `0x04A` | `bool` | `m_IsStandalone` | Whether state runs without strategy layer. If true, agent iteration budget is uncapped. |
| `0x050` | `List<UnitActor>` | `m_DeployedUnitLeaders` | Active unit leaders. Used in `GetScoreMultForPickingThisAgent` to identify player unit. |
| `0x0C8` | `MovementResult` | `m_QueuedSkill` | Populated by `AssignSkill()` via `TrySelectSkill()` |

**Note on duplicate offsets:** Static and instance fields share offset notation in the dump. `s_DefaultTimeScale` and `m_UI` both show `0x020`; `s_TooltipsEnabled` and `m_CurrentTile` both show `0x028`. This is correct — not a parser error.

### Selected methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Get()` | `0x648D90` | `0x180648D90` | Singleton accessor |
| `TrySelectSkill()` | `0x64ED50` | `0x18064ED50` | Called by `AssignSkill()` |
| `GetCurrentTile()` | `0x4F04B0` | `0x1804F04B0` | Used by `SpawnEntity()` |
| `IsReady()` | `0x616650` | `0x180616650` | Gate check |
| `GetDeployedUnitLeaders()` | `0x502E10` | `0x180502E10` | Returns active unit list |

---

## 11. Class: AIWeightsTemplate

**Namespace:** `Menace.Tactical.AI`
**TypeDefIndex:** 3621
**Base:** `ScriptableObject`
**Asset menu path:** `"Menace/Config/AI Weights"`
**Accessed via:** `DebugVisualization.WEIGHTS` (static field, offset `+0x08` on DebugVisualization class static storage)

See Section 6 for the complete field reference. Only the constructor is exposed as a method:

| Method | RVA | VA |
|---|---|---|
| `.ctor()` | `0x72E880` | `0x18072E880` |

### Critical offsets for scoring

| Offset | Field | Used in |
|---|---|---|
| `+0x20` | `UtilityPOW` | PostProcessTileScores — UtilityScore exponent step 1 |
| `+0x24` | `UtilityScale` | PostProcessTileScores — UtilityScore scale step 2 |
| `+0x28` | `UtilityPostPOW` | PostProcessTileScores — UtilityScore exponent step 3 |
| `+0x2C` | `UtilityPostScale` | PostProcessTileScores — UtilityScore final multiplier |
| `+0x30` | `SafetyPOW` | PostProcessTileScores — SafetyScore exponent step 1 |
| `+0x34` | `SafetyScale` | PostProcessTileScores — SafetyScore scale step 2 |
| `+0x38` | `SafetyPostPOW` | PostProcessTileScores — SafetyScore exponent step 3 |
| `+0x3C` | `SafetyPostScale` | PostProcessTileScores — SafetyScore multiplier before negation |
| `+0x40` | `DistanceScale` | GetScore distance penalty weight AND SafetyScore negation factor |
| `+0x44` | `DistancePickScale` | GetScaledScore distance penalty weight |
| `+0x48` | `ThreatLevelPOW` | GetThreatLevel final exponent |
| `+0x4C` | `OpportunityLevelPOW` | GetOpportunityLevel final exponent |
| `+0x50` | `PickingScoreMultPOW` | GetScoreMultForPickingThisAgent final exponent |

---

## 12. Class: DebugVisualization / DebugVisualizationFilter

### DebugVisualization (enum)

**Namespace:** `Menace.Tactical.AI` | **TypeDefIndex:** 3610

Controls which `TileScore` field `GetScore(TileScore)` returns for heatmap rendering.

| Value | Member | Maps to |
|---|---|---|
| 0 | `None` | Heatmap off |
| 1 | `TotalScore` | `TileScore.GetScore()` |
| 2 | `TotalScoreScaled` | `TileScore.GetScaledScore()` |
| 3 | `Utility` | `UtilityScore` |
| 4 | `Safety` | `SafetyScore` |
| 5 | `SafetyScaled` | `SafetyScoreScaled` |
| 6 | `Distance` | `DistanceToCurrentTile × -100.0` |

**Static fields:**
- `WEIGHTS` at static offset `+0x08` — the `AIWeightsTemplate` instance used globally.
- A static copy of the current `ShowHeatmap` enum value at static offset `+0x00` (used by `Start()` for change detection).
- `DebugVisualizationFilter` current value at static offset `+0x04` (written by `OnAIDestinationOnlyChanged()`).

### DebugVisualizationFilter (enum)

**Namespace:** `Menace.Tactical.AI` | **TypeDefIndex:** 3611

Controls which subset of tiles `DrawHeatmap` iterates. Applied before score lookup, not after.

| Value | Member | Interpretation |
|---|---|---|
| 0 | `None` | All tiles in `m_Tiles` |
| 1 | `Destinations` | Only tiles the AI is considering as move targets |
| 2 | `SelectedPath` | Only tiles on the AI's chosen path |

---

## 13. Class: MovementResult

**Namespace:** `Tactical` | **TypeDefIndex:** 1400

**Note:** Initially identified as the candidate for `TacticalState+0x40`. This was incorrect — `TacticalState+0x40` is `m_MovementResult` (an object reference), not a float. The actual distance weight float accessed in `GetScore()` is on `AIWeightsTemplate`, accessed indirectly via `DebugVisualization.WEIGHTS`.

### Fields

| Offset | Field | Type |
|---|---|---|
| `0x10` | `Success` | `bool` |
| `0x14` | `Reason` | `MovementFailedReason` |
| `0x18` | `Action` | `MovementAction` |
| `0x1C` | `HopBuildingSpecialCase` | `bool` |
| `0x20` | `StartTile` | `Tile` |
| `0x28` | `EndTile` | `Tile` |
| `0x30` | `Path` | `List<Vector3>` (readonly) |
| `0x38` | `Cost` | `int` |

---

## 14. Ghidra Address Reference

All addresses are VAs for direct use in Ghidra (Go To Address, G key). Image base: `0x180000000`.

### Priority targets (fully analysed)

| VA | Method | Class | Notes |
|---|---|---|---|
| `0x180740F20` | `GetScore()` | `TileScore` | **Master scoring formula** |
| `0x180740E50` | `GetScaledScore()` | `TileScore` | Scaled variant |
| `0x180740F10` | `GetScoreWithoutDistance()` | `TileScore` | SafetyScore + UtilityScore only |
| `0x180740D40` | `CompareScores()` | `TileScore` | Descending comparator |
| `0x180719860` | `Evaluate()` | `Agent` | Full evaluation loop |
| `0x18071C450` | `PostProcessTileScores()` | `Agent` | POW/Scale pipeline + neighbor propagation |
| `0x18071BD20` | `PickBehavior()` | `Agent` | Behavior selection |
| `0x18071B240` | `GetThreatLevel()` | `Agent` | Threat accumulator |
| `0x18071ABC0` | `GetOpportunityLevel()` | `Agent` | Attack ceiling |
| `0x18071AE50` | `GetScoreMultForPickingThisAgent()` | `Agent` | Agent turn priority |
| `0x180756180` | `DrawHeatmap()` | `TacticalStateSettings` | Heatmap tile iterator |
| `0x180756DE0` | `GetScore()` | `TacticalStateSettings` | Enum dispatch for heatmap |
| `0x180757530` | `Start()` | `TacticalStateSettings` | Unity lifecycle + callback registration |
| `0x1807​56EA0` | `OnAIDestinationOnlyChanged()` | `TacticalStateSettings` | Filter push to DebugVisualization static |
| `0x180648D90` | `Get()` | `TacticalState` | Singleton accessor |

### Secondary targets (not yet analysed)

| VA | Method | Class | Notes |
|---|---|---|---|
| `0x18071CAD0` | `ScheduleCriterionEvaluation()` | `Agent` | Thread task creation |
| `0x18071A9D0` | `Execute()` | `Agent` | Behavior execution |
| `0x18071CAA0` | `Reset()` | `Agent` | State reset |
| `0x18071CEC0` | `.cctor()` | `Agent` | S_CRITERIONS initialisation |
| `0x18071B660` | `HasFlag()` | `Agent` | Flag check |
| `0x18071CBF0` | `SetFlag()` | `Agent` | Flag mutation |
| `0x18071B670` | `IsDeploymentPhase()` | `Agent` | Deployment phase check |
| `0x18071BC00` | `OnTurnStart()` | `Agent` | Turn start handler |
| `0x18072E880` | `.ctor()` | `AIWeightsTemplate` | Constructor |
| `0x18064ED50` | `TrySelectSkill()` | `TacticalState` | Skill selection |
| `0x1804F04B0` | `GetCurrentTile()` | `TacticalState` | Current tile accessor |
| `0x180952F00` | `GetBehavior<object>()` | `Agent` | Generic behavior lookup |

---

## 15. Key Inferences and Design Notes

### SafetyScore is a penalty, not a reward

After `PostProcessTileScores`, `SafetyScore` is **negative**. The pipeline ends with `× -DistanceScale`. In the composite formula `SafetyScore + UtilityScore`, a tile under heavy threat has a large negative `SafetyScore` that reduces the total. The AI seeks tiles where this penalty is minimised (closest to zero), which corresponds to the safest tiles.

### `DistanceScale` serves double duty

`AIWeightsTemplate.DistanceScale` is used in two places:
1. As the distance penalty weight in `GetScore()`: `(DistanceScore + DistanceToCurrentTile) × DistanceScale`
2. As the final negation multiplier in `PostProcessTileScores` for `SafetyScore`: `-SafetyScore × DistanceScale`

This means increasing `DistanceScale` simultaneously increases distance penalty AND threat penalty — they are intentionally coupled.

### Per-actor role multipliers override global weights

`PostProcessTileScores` reads `role->0x14` (UtilityMult) and `role->0x1C` (SafetyMult) from each agent's role data object. These multiply the respective scores before the `Scale` step. Different unit types (infantry vs. vehicle vs. specialist) can have fundamentally different scoring sensitivities without modifying the shared `AIWeightsTemplate` asset.

### Two-pass criterion evaluation serves normalization

Criterion Pass 1 writes raw scores. `PostProcessTileScores` normalizes them (POW/Scale). Criterion Pass 2 (`PostEvaluate`) can then respond to normalized values — enabling relative comparisons across tiles that were not possible with raw data. This is where `UtilityByAttacksScoreCandidate` is committed or discarded.

### Iteration budget and standalone mode

`Agent.m_Iterations` is incremented each `Evaluate()` call and capped at 16 (`MAX_ITERATIONS`). Once exceeded, the agent is forced to sleep (`FUN_1805e76f0`). This prevents a single agent from monopolising the AI time budget across multiple frames. When `TacticalState.m_IsStandalone` is true (no strategy layer), this cap is bypassed — standalone mode is for testing/editor use.

### The heatmap is a direct window into the AI's working data

`TacticalStateSettings.DrawHeatmap()` reads directly from `Agent.m_Tiles` (passed as a parameter). The `Filter` and `ShowHeatmap` settings provide independent axes for viewing any score dimension on any subset of tiles. Case 6 (`Distance`) negates and scales by 100 for readability only — the raw value stored in `TileScore.DistanceToCurrentTile` is an AP cost.

### `UltimateTile` vs `Tile` distinction

`TileScore.UltimateTile` is the final destination if movement continues through this tile (waypoint scoring). `GetScoreWithoutDistance()` is applied specifically to `UltimateTile` evaluations — AP cost is irrelevant when scoring a terminal destination, only safety and utility matter.

---

## 16. Open Questions

These questions were not answered in this investigation and represent the next layer of work:

1. **Individual `Criterion` subclasses.** The `S_CRITERIONS` static list contains the concrete evaluators that write into `TileScore` fields. These implement specific position criteria from `AIWeightsTemplate` (cover, threat from opponents, zone distances, etc.). Their implementations are the final gap in understanding what inputs drive the raw scores. Access via `Agent..cctor()` at `0x18071CEC0` which initialises the list, or via vtable dispatch analysis from `Evaluate()`.

2. **`FUN_181430ac0` — per-attack evaluator.** Called from `GetOpportunityLevel()` with `(attack, actor)`. Returns a float score. Understanding this function would reveal how attack opportunities are quantified.

3. **`Behavior` subclass implementations.** `PickBehavior()` at `0x18071BD20` sorts behaviors and selects the best. The `Behavior` subclasses implement specific tactical actions (move, attack, buff, etc.) and their `baseScore` at `+0x18` drives `m_Score`.

4. **Role data offsets.** `role->0x14` and `role->0x1C` are per-actor utility and safety multipliers. The class containing these fields has not been identified or extracted.

5. **`Agent.m_Flags` bit meanings.** Only bit 0 is confirmed (enables neighbor propagation). The remaining bits are unknown.

6. **What populates `TileScore.SafetyScore` and `TileScore.UtilityScore` raw values.** The `Criterion` subclasses are responsible for this. The named fields in `AIWeightsTemplate`'s Position Criterions section (`CoverAgainstOpponents`, `ThreatFromOpponents`, etc.) are the per-criterion weights applied during `EvaluateTile`.
