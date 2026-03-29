# REPORT.md — Menace.Tactical.AI.Behaviors.Criterions

---

## 1. Header Block

| Field | Value |
|---|---|
| Game | Menace |
| Platform | PC (Windows x64) |
| Binary | GameAssembly.dll |
| Image Base | `0x180000000` |
| VA formula | `VA = RVA + 0x180000000` |
| Source material | Il2CppDumper dump.cs + Ghidra decompilation (5 functions, batch 1) |
| Investigation date | Batch 1 complete |
| Status | **IN PROGRESS** — core formula resolved; call-chain dependencies outstanding |

---

## 2. Table of Contents

1. Header Block
2. Table of Contents
3. Investigation Overview
4. Class Field Offset Tables
5. Method Reference Table
6. Core Algorithm / Scoring Formula
7. Design Notes
8. Open Questions

---

## 3. Investigation Overview

### What was achieved

- All 11 classes in `Menace.Tactical.AI.Behaviors.Criterions` enumerated and extracted from `dump.cs`.
- Full method RVA/VA table constructed and priority-ordered for Ghidra analysis.
- Batch 1 (5 functions) decompiled and fully annotated:
  - `Criterion..ctor` — confirmed stateless base constructor.
  - `CoverAgainstOpponents..cctor` — confirmed static `COVER_PENALTIES float[4]` allocation; values not yet resolved.
  - `Criterion.GetUtilityThreshold` — formula resolved; tile threshold = `max(base, base × zoneMin) × zoneMultiplier`.
  - `CoverAgainstOpponents.Evaluate` — full three-phase algorithm reconstructed; cover quality iteration, penalty application, and score write confirmed.
  - `Criterion.Score` — master scoring formula resolved; four weighted components combined with a movement-effectiveness curve multiplier.
- `AIWeightsTemplate` singleton confirmed as the central configuration object for all weight and threshold constants. Its field layout is partially mapped (see §4).
- `param_3->field_0x28` confirmed as the **mutable tile score accumulator** written by all `Evaluate` calls.
- `param_3->field_0x30` confirmed as the **threshold accumulator** written by `Evaluate`.

### Explicit scope boundary — what was NOT investigated

- `ThreatFromOpponents.Evaluate` and its two `Score` overloads — next priority batch.
- `AvoidOpponents.Evaluate`, `FleeFromOpponents.Evaluate`, `DistanceToCurrentTile.Evaluate`, `ExistingTileEffects.Evaluate` — not yet decompiled.
- `ConsiderZones.Evaluate`, `ConsiderZones.PostProcess`, `ConsiderZones.Collect` — two-phase zone evaluation not yet understood.
- `WakeUp.Collect` and `WakeUp..ctor` — divergent constructor not yet investigated.
- `Roam.Collect`, `ConsiderSurroundings.Collect` — collection passes not yet decompiled.
- All `IsValid` implementations — not yet decompiled (low priority, structurally predictable).
- `Criterion.IsDeploymentPhase` — utility guard, not yet decompiled.
- `AIWeightsTemplate` class — field layout partially inferred from usage; full extraction not performed.
- The behaviour selection layer that consumes `Criterion.Score` output — **out of scope** (separate system; flag raised).
- The threading system (`GetThreads` returns non-default for `ThreatFromOpponents`) — out of scope.

---

## 4. Class Field Offset Tables

### 4.1 `Criterion` (base class)
TypeDefIndex: 3670 | Base: object

| Offset | Type | Name | Status |
|---|---|---|---|
| — | — | *(no instance fields confirmed)* | confirmed |

### 4.2 `CoverAgainstOpponents`
TypeDefIndex: 3674 | Base: Criterion

| Offset | Type | Name | Status |
|---|---|---|---|
| `0x000` (static) | `float[]` | `COVER_PENALTIES` | confirmed (dump.cs) |

> **Note:** `COVER_PENALTIES` is a static field at the class level, not an instance field. Length = 4 (confirmed from `.cctor`). Values not yet resolved — see §8.

### 4.3 `AIWeightsTemplate` (singleton, `DAT_18394c3d0`)
Accessed via `*(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8)` in all scoring functions.
This is a singleton instance read from the class's static field slot.

| Offset | Type | Name | Source function | Status |
|---|---|---|---|---|
| `+0x13c` | `float` | `baseThreshold` | `GetUtilityThreshold` | confirmed |
| `+0x70` | `float` | `coverScoreWeight` (W_cover) | `CoverAgainstOpponents.Evaluate` final write | confirmed |
| `+0x7c` | `float` | `W_attack` | `Criterion.Score` phase 8 | confirmed |
| `+0x80` | `float` | `W_ammo` | `Criterion.Score` phase 8 | confirmed |
| `+0x84` | `float` | `W_deploy` | `Criterion.Score` phase 8 | confirmed |
| `+0x88` | `float` | `W_sniper` | `Criterion.Score` phase 8 | confirmed |
| `+0x8c` | `float` | `coverMultiplier_Full` | `CoverAgainstOpponents.Evaluate` cover type | confirmed |
| `+0x90` | `float` | `coverMultiplier_Partial` | `CoverAgainstOpponents.Evaluate` cover type | confirmed |
| `+0x94` | `float` | `coverMultiplier_Low` | `CoverAgainstOpponents.Evaluate` cover type | confirmed |
| `+0x98` | `float` | `coverMultiplier_Quarter` | `CoverAgainstOpponents.Evaluate` cover type | confirmed |
| `+0x9c` | `float` | `coverMultiplier_None` | `CoverAgainstOpponents.Evaluate` cover type | confirmed |
| `+0xa4` | `float` | `bestCoverBonusWeight` | `CoverAgainstOpponents.Evaluate` final accumulation | confirmed |
| `+0xd4` | `float` | `occupiedDirectionPenalty` | `CoverAgainstOpponents.Evaluate` direction loop | confirmed |
| `+0xd8` | `float` | `rangeScorePenalty` | `CoverAgainstOpponents.Evaluate` phase 1 | confirmed |
| `+0xdc` | `float` | `ammoScorePenalty` | `CoverAgainstOpponents.Evaluate` phase 1 | confirmed |
| `+0xe4` | `float` | `baseAttackWeight` | `Criterion.Score` phase 4 | confirmed |
| `+0xe8` | `float` | `ammoPressureWeight` | `Criterion.Score` ammo formula | confirmed |
| `+0xec` | `float` | `deployPositionWeight` | `Criterion.Score` phase 6 | confirmed |
| `+0xf0` | `float` | `sniperAttackWeight` | `Criterion.Score` phase 7 | confirmed |

### 4.4 `TileModifier` (returned by `FUN_18071ae10`, accessed via `tile->zoneDescriptor`)
Accessed as result of zone modifier lookup in `GetUtilityThreshold`.

| Offset | Type | Name | Source function | Status |
|---|---|---|---|---|
| `+0x14` | `float` | `minThresholdScale` | `GetUtilityThreshold` | confirmed |
| `+0x18` | `float` | `thresholdMultiplier` | `GetUtilityThreshold` | confirmed |

### 4.5 Unit object (`param_1` in `Criterion.Score` / `param_2` in `CoverAgainstOpponents.Evaluate`)

| Offset | Type | Name | Source function | Status |
|---|---|---|---|---|
| `+0x54` (0x54) | `int` | `moveRange` (movement points available) | `Criterion.Score` range ratio | confirmed |
| `+0x5c` (0x5c) | `int` | `currentAmmo` | `Criterion.Score` ammo formula | confirmed |
| `+0x60` (0x60) | `int` | `teamSize` (or squad count) | `Criterion.Score` ammo formula | confirmed |
| `+0x70` (0xe * 8) | `int` | `teamId` | `CoverAgainstOpponents.Evaluate` faction check | confirmed |
| `+0xC8` (0x19 * 8) | `ptr` | `opponentList` | `CoverAgainstOpponents.Evaluate` guard | confirmed |
| `+0x60` (param_1[0xc]) | `int` | `squadCount` (or groupSize) | `Criterion.Score` ammo | inferred |
| `+0x20` (param_1[4]) | `ptr` | `movePool` (movement resource) | `Criterion.Score` range gate | confirmed |
| vtable `+0x3d8/0x3e0` | method | `GetWeaponList()` | `Criterion.Score` phase 4 | inferred |
| vtable `+0x398/0x3a0` | method | `GetStatusEffects()` | `Criterion.Score` phase 7 | inferred |
| vtable `+1000 (0x3e8)` | method | `GetEnemyList()` | `Criterion.Score` phase 1 | inferred |

### 4.6 MovePool object (`unit->movePool`, `param_1[4]`)

| Offset | Type | Name | Source function | Status |
|---|---|---|---|---|
| `+0x18` | `int` | `maxMovePoints` | `Criterion.Score` phase 3 + phase 4 | confirmed |

### 4.7 MoveRangeData object (returned by `FUN_1806df4e0`)

| Offset | Type | Name | Source function | Status |
|---|---|---|---|---|
| `+0x10` | `float` | `weaponAttackRange` | `Criterion.Score` range formula | confirmed |
| `+0x14` | `float` | `weaponMinRange` | `Criterion.Score` ammo formula | confirmed |
| `+0x1c` | `float` | `moveCostToTile` | `Criterion.Score` gating | confirmed |
| `+0x25` | `bool` | `canAttackFromTile` | `Criterion.Score` minor bonus | confirmed |

### 4.8 EvaluationContext / TileScoreRecord (`param_3` in Evaluate functions)

| Offset | Type | Name | Source function | Status |
|---|---|---|---|---|
| `+0x10` | `ptr` | `tileRef` (pointer to tile object) | `CoverAgainstOpponents.Evaluate` throughout | confirmed |
| `+0x28` | `float` | `accumulatedScore` (written by Evaluate) | `CoverAgainstOpponents.Evaluate` final write | confirmed |
| `+0x30` | `float` | `thresholdAccumulator` (written by Evaluate) | `CoverAgainstOpponents.Evaluate` phase 1 | confirmed |
| `+0x60` | `bool` | `isObjectiveTile` (or special tile flag) | `CoverAgainstOpponents.Evaluate` phase 3 | inferred |

---

## 5. Method Reference Table

| RVA | VA | Class | Method | Purpose |
|---|---|---|---|---|
| `0x4EB570` | `0x1804EB570` | Criterion | `.ctor` | Pass-through to object::.ctor; no-op for subclasses |
| `0x4F7EE0` | `0x1804F7EE0` | Criterion | `Collect/Evaluate/PostProcess` (shared stub) | Virtual no-op base implementations |
| `0x546260` | `0x180546260` | Criterion | `GetThreads` | Returns default thread count (likely 1); not yet decompiled |
| `0x71B670` | `0x18071B670` | Criterion | `IsDeploymentPhase` | Reads game-phase flag; not yet decompiled |
| `0x760070` | `0x180760070` | Criterion | `GetUtilityThreshold` | Returns zone-scaled activation threshold for this tile |
| `0x760140` | `0x180760140` | Criterion | `Score` | Master scoring function; 4-component weighted formula × movement curve |
| `0x75BE10` | `0x18075BE10` | AvoidOpponents | `Evaluate` | Not yet decompiled |
| `0x75C1B0` | `0x18075C1B0` | AvoidOpponents | `IsValid` | Not yet decompiled |
| `0x75C240` | `0x18075C240` | ConsiderSurroundings | `Collect` | Not yet decompiled |
| `0x75C5B0` | `0x18075C5B0` | ConsiderSurroundings | `IsValid` | Not yet decompiled |
| `0x75C630` | `0x18075C630` | ConsiderZones | `Collect` | Not yet decompiled |
| `0x75CC20` | `0x18075CC20` | ConsiderZones | `Evaluate` | Not yet decompiled |
| `0x75D2C0` | `0x18075D2C0` | ConsiderZones | `IsValid` | Not yet decompiled |
| `0x75D3B0` | `0x18075D3B0` | ConsiderZones | `PostProcess` | Not yet decompiled |
| `0x75DAD0` | `0x18075DAD0` | CoverAgainstOpponents | `Evaluate` | Cover quality scoring: iterates enemies, classifies cover direction, accumulates weighted score |
| `0x75EAB0` | `0x18075EAB0` | CoverAgainstOpponents | `IsValid` | Not yet decompiled |
| `0x75EB00` | `0x18075EB00` | CoverAgainstOpponents | `.cctor` | Allocates COVER_PENALTIES float[4]; values TBD |
| `0x760CF0` | `0x180760CF0` | DistanceToCurrentTile | `Evaluate` | Not yet decompiled |
| `0x760EC0` | `0x180760EC0` | DistanceToCurrentTile | `IsValid` | Not yet decompiled |
| `0x760FB0` | `0x180760FB0` | ExistingTileEffects | `Evaluate` | Not yet decompiled |
| `0x761370` | `0x180761370` | ExistingTileEffects | `IsValid` | Not yet decompiled |
| `0x7613A0` | `0x1807613A0` | FleeFromOpponents | `Evaluate` | Not yet decompiled |
| `0x7616D0` | `0x1807616D0` | FleeFromOpponents | `IsValid` | Not yet decompiled |
| `0x768300` | `0x180768300` | Roam | `Collect` | Not yet decompiled |
| `0x768870` | `0x180768870` | Roam | `IsValid` | Not yet decompiled |
| `0x76ACB0` | `0x18076ACB0` | ThreatFromOpponents | `Evaluate` | Not yet decompiled |
| `0x76AF00` | `0x18076AF00` | ThreatFromOpponents | `IsValid` | Not yet decompiled |
| `0x76AF90` | `0x18076AF90` | ThreatFromOpponents | `Score` (overload A) | Not yet decompiled |
| `0x76B710` | `0x18076B710` | ThreatFromOpponents | `Score` (overload B) | Not yet decompiled |
| `0x54E040` | `0x18054E040` | ThreatFromOpponents | `GetThreads` | Non-default thread count; not yet decompiled |
| `0x787DD0` | `0x180787DD0` | WakeUp | `Collect` | Not yet decompiled |
| `0x7880E0` | `0x1807880E0` | WakeUp | `IsValid` | Not yet decompiled |
| `0x518FA0` | `0x180518FA0` | WakeUp | `.ctor` | Divergent constructor; not yet decompiled |

**Helper functions resolved from batch 1:**

| VA | Alias | Summary |
|---|---|---|
| `0x180427b00` | `IL2CPP_TypeInit` | Lazy type initialiser trigger |
| `0x180427d90` | `IL2CPP_NullRefAbort` | Throws NullReferenceException |
| `0x180427d80` | `IL2CPP_IndexOutOfRangeAbort` | Throws IndexOutOfRangeException |
| `0x1804f7ee0` | `object::.ctor` | Managed object base constructor |
| `0x180426ed0` | `Array.CreateInstance` | Allocates managed array of given type and length |
| `0x181a8f520` | `Array.SetElementType` | Sets element type on a newly created array |
| `0x180426e50` | `IL2CPP_WriteBarrier` | GC write barrier; no logical effect |
| `0x18071ae10` | `GetTileZoneModifier` | Returns zone modifier object for a tile's zone descriptor |
| `0x1806e0ac0` | `GetTileScoreComponents` | Returns float* to raw score components for a tile |
| `0x1806df4e0` | `GetMoveRangeData` | Returns movement range/cost data for a unit→tile pair |
| `0x1806e0300` | `GetReachabilityAdjustedScore` | Applies movement cost gating to raw score |
| `0x1806e2400` | `GetMovementEffectivenessIndex` | Returns index into movement effectiveness lookup table |
| `0x1804bad80` | `MathCurve` | Applied to `(table[i] + 1.0)`; likely `expf` or custom curve — **UNCONFIRMED** |
| `0x1806155c0` | `GetHealthRatio` | Returns unit health as float [0,1] |
| `0x180614b30` | `GetReloadChance` | Returns unit reload probability or ammo efficiency |
| `0x180614d30` | `GetMovementDepth` | Returns unit movement depth metric; returns -2 for deployment-locked tiles |
| `0x1806f2460` | `GetThreadedTileScore` | Retrieves tile score from threaded scoring pipeline |
| `0x1806d5040` | `GetThreadScoreIndex` | Returns thread-local tile score index |
| `0x1806f2230` | `GetScoredTileData` | Retrieves TileScore object from thread-local storage |
| `0x1806283c0` | `GetEnemyCountInRange` | Returns count of enemies within range (param: range=3) |
| `0x180687590` | `TileHasEnemyUnit` | Returns non-zero if tile is occupied by an enemy |
| `0x1806888b0` | `TileMatchesContext` | Checks if a tile matches the evaluation context |
| `0x1806889c0` | `IsCurrentTile` | Returns true if tile is the unit's current position |
| `0x180688600` | `GetUnitOnTile` | Returns the unit currently occupying a tile |
| `0x1806169a0` | `CanTargetUnit` | Returns true if unit A can target unit B |
| `0x1806d7700` | `GetWeaponRange` | Returns weapon range stat |
| `0x180717870` | `IsListNonEmpty` | Returns true if collection is non-empty |
| `0x180722ed0` | `IsEnemy` | Returns true if entity is hostile |
| `0x180687660` | `GetDirectionIndex` | Returns 0–7 directional index for a tile relationship |
| `0x1805ca990` | `IsChokePoint` | Returns true if tile is a choke point |
| `0x180cbab80` | `GetEnumerator` | IL2CPP enumerator factory |
| `0x1814f4770` | `MoveNext` | IL2CPP enumerator MoveNext |
| `0x18052a570` | `Abs` | Integer absolute value |
| `0x18073bcf0` | `RangeContains` | Returns true if a range object contains a given value |
| `0x1829a9340` | `IsRangedWeapon` | Returns true if weapon is ranged type |
| `0x1810c1fc0` | `GetAdjacentTile` | Returns tile adjacent in a given direction |
| `0x1805ca7a0` | `GetTileDistance` | Returns distance between two tiles |
| `0x1805ca720` | `GetTileDirectionIndex` | Returns directional index between two tiles |
| `0x180687660` | `GetDirectionIndexForTile` | Returns 0–7 direction from context tile to candidate |
| `0x1806defc0` | `GetRangeStepCount` | Returns number of range steps for weapon at tile |
| `0x1806de960` | `GetAttackCountFromTile` | Returns viable attack count from a tile position |

---

## 6. Core Algorithm / Scoring Formula

### 6.1 Pipeline overview

```
For each candidate tile T:
    1. IsValid(unit, T)            → bool     gate; skip if false
    2. Collect(unit, T, ctx)       → void     populates ctx with pre-computed data
    3. Evaluate(unit, T, ctx)      → void     writes score delta to ctx.accumulatedScore
       [repeated for each active Criterion]
    4. PostProcess(unit, T, ctx)   → void     optional second pass (ConsiderZones only)
    5. Score(unit, T, ctx, tile)   → float    final weighted scalar from accumulated score
    6. Compare against GetUtilityThreshold(unit, T) → keep tile if score > threshold
```

### 6.2 `GetUtilityThreshold(unit, tile)` — confirmed

```
modifier  = GetTileZoneModifier(tile.zoneDescriptor)
threshold = max(settings.baseThreshold,
                settings.baseThreshold × modifier.minThresholdScale)
return threshold × modifier.thresholdMultiplier
```

### 6.3 `CoverAgainstOpponents.Evaluate(unit, tile, ctx)` — confirmed

```
// Guard
if unit.opponentList is empty: return

// Phase 1 — Occupied tile penalties (only if tile ≠ current tile)
if tile is occupied by allied unit: return
if tile is occupied by enemy unit and CanTarget(enemy):
    ctx.accumulatedScore -= enemy.weapon.range × settings.rangeScorePenalty
    ctx.accumulatedScore -= enemy.weapon.ammo  × settings.ammoScorePenalty
ctx.thresholdAccumulator += GetUtilityThreshold(unit, tile)

// Phase 2 — Cover quality per enemy
fBest = 0.0; fSum = 0.0
for each enemy in unit.opponentList:
    if not IsEnemy(enemy): continue
    dirIdx    = GetDirectionIndex(tile, enemy.tile)     // 0–7
    penalty   = COVER_PENALTIES[dirIdx]
    coverMult = settings.coverMultiplier[ClassifyCoverType(unit, enemy)]
    // [0x8c=Full, 0x90=Partial, 0x94=Low, 0x98=Quarter, 0x9c=None]
    proximity = 1.0 - clamp(dist(tile, enemy.tile) / 30.0, 0.1, 1.0)
    tileScore = proximity × coverMult × (coverStrength/maxCover × 0.5 + 0.5)
    fBest     = max(fBest, tileScore)
    fSum     += tileScore

// Phase 3 — Final write
total = fSum + fBest × settings.bestCoverBonusWeight    // +0xa4
for each of 8 directions:
    if direction is occupied: total -= settings.occupiedDirectionPenalty   // +0xd4
if total ≠ 0 and tile not deployment-locked:
    if tile is not a choke point: total += 10.0
if unit has debuff status and tile ≠ objective tile:
    total *= 0.9
ctx.accumulatedScore = total × settings.coverScoreWeight + ctx.accumulatedScore  // +0x70
```

### 6.4 `Criterion.Score(unit, tile, ctx, tileData)` — confirmed

```
rawScore      = GetTileScoreComponents(tile, ...) × 0.01
moveData      = GetMoveRangeData(tile, unit)
rangeCost     = floor(min(rawScore × moveData.moveCost, unit.movePool.maxMoves - 1))
adjScore      = GetReachabilityAdjustedScore(..., rangeCost) × 0.01

// Component A — Attack weight
rangeRatio    = min((rawScore × moveData.attackRange) / unit.moveRange, 2.0)
W_atk         = settings.baseAttackWeight × rangeRatio
if rawScore × moveData.moveCost ≥ unit.movePool.maxMoves:
    W_atk    *= 2.0
    if GetHealthRatio(unit) > 0.95: W_atk *= 4.0
elif moveData.canAttack and rawScore > 0:
    W_atk    *= 1.1
// + overwatch suppression loop multipliers from response curve table

// Component B — Ammo pressure
if rawScore × moveData.minRange > 0:
    ammoLeft  = unit.currentAmmo - rawScore × moveData.minRange
    ammoLeft  = max(ammoLeft, 0)
    teamSize  = max(unit.teamSize, 1)
    enemies   = min(GetEnemyCountInRange(unit, 3), 200)
    fAmmo     = (reloadChance × enemies - (ammoLeft / teamSize) × enemies)
                × settings.ammoPressureWeight × enemies × 0.0001

// Component C — Deployment position
if adjScore > 0:
    fDeploy   = min(adjScore × rawScore + adjScore, 2.0)
               × settings.deployPositionWeight
    if not tile.hasEnemy:
        fDeploy *= (GetMovementDepth(unit) × 0.25 + 1.5)
    if adjScore × rawScore + adjScore ≥ 0.67: fDeploy *= 3.0

// Component D — Sniper bonus (only if unit has sniper-class weapon)
if HasSniperWeapon(unit):
    fSniper   = GetAttackCount(tile, weapon) × rangeSteps × attackCount
                × settings.sniperAttackWeight × rawScore
    if not tile.hasEnemy:
        fSniper *= (GetMovementDepth(unit) × 0.25 + 1.5)
    fSniper   *= max(GetHealthRatio(unit), 0.25)

// Final combination
movEffIdx     = GetMovementEffectivenessIndex(tile, unit)
movEff        = MathCurve(movementEffTable[movEffIdx] + 1.0)
return movEff × (settings.W_attack × W_atk
               + settings.W_ammo   × fAmmo
               + settings.W_deploy × fDeploy
               + settings.W_sniper × fSniper)
```

---

## 7. Design Notes

> *Labelled as opinion; separate from confirmed findings.*

**On the four-component decomposition:** The scoring formula cleanly separates four strategic concerns — raw attack opportunity (W_attack), supply pressure (W_ammo), positional advancement (W_deploy), and precision fire support (W_sniper). This is a textbook utility AI design with additive weighted components, not a neural or learned system. Each weight in `AIWeightsTemplate` is independently tunable, making the AI behaviour highly data-driven.

**On the 0.01 normalisation:** Raw scores from `Evaluate` are deposited as integer centiscale values (i.e., a score of "50" in the accumulator = 0.5 after normalisation). This suggests designers work in 0–100 integer space for tuning ergonomics while the runtime works in [0,1] float space.

**On cover penalties vs. cover bonus:** `CoverAgainstOpponents` simultaneously penalises occupied tiles (Phase 1) and rewards good cover positions (Phase 2–3). A tile occupied by an enemy with high range and ammo will score negatively, while a tile with full cover against multiple enemies will score positively. This creates a natural "don't walk into a firing line, do find cover" emergent behaviour without explicit pathfinding.

**On the overwatch loop:** The suppression response curve table (`DAT_18396a5e8 + 0xb8 + 0xd8/0xe0`) appears to implement a soft penalty that increases as a tile falls within the enemy's effective overwatch envelope. This discourages AI from moving through choke points that an overwatch enemy covers well.

**On `COVER_PENALTIES float[4]`:** The array length of 4 is curious given the 8-directional cover system. It likely maps to four cover quality tiers (Full/Partial/Low/None) rather than directions, with directionality handled separately by `GetDirectionIndex`. The name "COVER_PENALTIES" in dump.cs suggests it penalises scores for low-cover directions.

**On the 4× health bonus:** A unit at >95% health in a max-range position scores 8× the base attack weight (2× range full + 4× health bonus). This strongly incentivises healthy units to seek and hold optimal firing positions, while damaged units are implicitly pushed toward conservative/defensive tiles.

---

## 8. Open Questions

| # | Question | Next step |
|---|---|---|
| Q1 | What are the four float values in `COVER_PENALTIES[]`? | Dump memory at `CoverAgainstOpponents.COVER_PENALTIES` at runtime, or find the element-by-element write in `.cctor` assembly listing |
| Q2 | What does `FUN_1804bad80` (MathCurve) compute exactly? Is it `expf`? | Navigate to VA in Ghidra; if it resolves to a thunk over `expf` or a CRT import, confirm. Check if it matches the IL2CPP `Math.Exp` wrapper |
| Q3 | What are `TileModifier.field_0x14` and `field_0x18` named in full? (`minThresholdScale` / `thresholdMultiplier`) | Extract `TileModifier` or equivalent class from dump.cs; cross-ref with `FUN_18071ae10` |
| Q4 | What is `param_3->field_0x60` (`isObjectiveTile`)? | Check `EvaluationContext` or equivalent class in dump.cs; look for bool field at offset 0x60 |
| Q5 | What does `ThreatFromOpponents.Evaluate` contribute to `rawScore`? | Decompile `0x18076ACB0`; compare score write pattern against `CoverAgainstOpponents.Evaluate` |
| Q6 | Why does `ThreatFromOpponents` have two `Score` overloads? | Decompile both `0x18076AF90` and `0x18076B710`; determine if one is per-enemy and one is aggregate |
| Q7 | What does `ConsiderZones.PostProcess` do differently from `Evaluate`? | Decompile `0x18075D3B0`; determine if it normalises or re-weights zone scores |
| Q8 | Why does `WakeUp` have a divergent constructor (`0x180518FA0`)? | Decompile WakeUp..ctor; identify what field it initialises that other criteria do not |
| Q9 | Full `AIWeightsTemplate` field layout — what are fields `0x100`–`0x140`? | Extract `AIWeightsTemplate` class from dump.cs with `extract_rvas.py` |
| Q10 | What is the behaviour selection layer that consumes `Score` output? | **Scope note:** this is outside `Menace.Tactical.AI.Behaviors.Criterions`. Requires operator acknowledgement before investigation. |
