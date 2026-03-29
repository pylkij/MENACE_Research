# Menace — Tactical AI Criterions — Stage 2 Report

**Game:** Menace  
**Platform:** PC x64, Unity IL2CPP  
**Binary:** GameAssembly.dll  
**Image base:** 0x180000000  
**Namespace:** Menace.Tactical.AI.Behaviors.Criterions  
**Investigation status:** In Progress — Stage 2 of ~3  
**Source material:** Ghidra decompilation, Il2CppDumper dump.cs, extract_rvas.py output  

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. Core Scoring Pipeline (updated)
5. ThreatFromOpponents
6. ConsiderZones
7. DistanceToCurrentTile
8. ExistingTileEffects
9. AvoidOpponents
10. FleeFromOpponents
11. Roam
12. WakeUp
13. Supporting Infrastructure: GetTileScoreComponents, GetMoveRangeData, Range Gates
14. Supporting Infrastructure: GetTileZoneModifier, FUN_1804bad80 (MathCurve resolved)
15. Ghidra Address Reference
16. Key Inferences and Design Notes
17. Open Questions

---

## 1. Investigation Overview

Stage 2 extended Stage 1's confirmed scoring pipeline by analysing all remaining Evaluate/Collect/Score overrides in the Criterions namespace, plus five infrastructure functions (GetTileScoreComponents, GetMoveRangeData, GetTileZoneModifier, IsWithinRangeA, IsWithinRangeB) and MathCurve resolution.

**Achieved this stage:**
- Full reconstruction of `ThreatFromOpponents.Evaluate`, `Score (A)`, `Score (B)` — the most complex evaluator in the namespace
- Full reconstruction of `ConsiderZones.Evaluate` and `ConsiderZones.PostProcess` — reveals zone flag bitmask system and dual threshold/score write paths
- Full reconstruction of `DistanceToCurrentTile.Evaluate`, `ExistingTileEffects.Evaluate`, `AvoidOpponents.Evaluate`, `FleeFromOpponents.Evaluate`
- Full reconstruction of `Roam.Collect` and `WakeUp.Collect`
- `WakeUp..ctor` confirmed as body-less base delegation (Q8 resolved)
- `Criterion.IsDeploymentPhase` confirmed: reads `ScoringContext.singleton +0x60 == 0`
- `ThreatFromOpponents.GetThreads` confirmed: hardcodes return value 4
- `GetTileScoreComponents`: confirmed 6-slot float[] layout; centiscale confirmed; objective tile early-exit confirmed
- `GetMoveRangeData`: all six output fields confirmed at exact offsets; exposes a deep TileScore field map
- `GetTileZoneModifier`: single-pass vtable dispatch returning `zoneData +0x310`
- `FUN_1804bad80` resolved as `expf`-equivalent single-argument growth curve (Q2 resolved)
- `IsWithinRangeA` / `IsWithinRangeB`: two-stage range gate system fully understood
- `ctx +0x60 = isObjectiveTile` confirmed (Q4 resolved)
- `WakeUp..ctor` no additional fields (Q8 resolved)
- 19 new `AIWeightsTemplate` field offsets confirmed
- 4 new `EvaluationContext` field offsets confirmed
- 3 new `TileModifier` field offsets confirmed
- Numerous new unit, tile, movePool, and ally field offsets

**Not investigated this stage:**
- `IsInMeleeRange` (0x1806e3750) — range gate A sub-call; semantics partially understood from callers
- `IsInAttackRange` (0x1806e60a0) — range gate A sub-call; semantics partially understood
- `IsValidRangeType` (0x1806e3d50) — guard for range gate A
- Behaviour selection layer consuming Score output (outside Criterions namespace — scoped out)
- All `IsValid` implementations (10 classes, deferred from Stage 1)
- `AIWeightsTemplate` offsets 0x100–0x140 (full layout not yet extracted)

---

## 2. Tooling

`extract_rvas.py` was used in Stage 1 to produce the extraction report for the Criterions namespace. No additional extractions were run this stage. All field offsets were derived from Ghidra decompilation cross-referenced against the Stage 1 extraction report and the cumulative field tables.

---

## 3. Class Inventory

| Class | TDI | Role |
|---|---|---|
| Criterion | 3670 | Abstract base; defines pipeline interface |
| AvoidOpponents | 3671 | Penalises tiles near groups that cannot directly target unit |
| ConsiderSurroundings | 3672 | Not analysed this stage |
| ConsiderZones | 3673 | Scores tiles based on zone membership and zone flag bitmasks |
| CoverAgainstOpponents | 3674 | Scores tiles based on cover quality vs. opponents (Stage 1) |
| DistanceToCurrentTile | 3675 | Penalises tiles based on distance from unit's current position |
| ExistingTileEffects | 3676 | Scores tiles that carry active tile effects matching unit's type |
| FleeFromOpponents | 3677 | Penalises tiles near groups that CAN target unit |
| Roam | 3678 | Populates candidate tile list for melee units without active targets |
| ThreatFromOpponents | 3679 | Scores tiles based on threat posed by enemy units; uses 4 threads |
| WakeUp | 3680 | Populates Collect list when a sleeping ally can be woken |

---

## 4. Core Scoring Pipeline (updated)

The full pipeline, confirmed across both stages:
````
IsValid(unit, ctx)
  └─ Collect(unit, ctx)           — populates candidate tile list (Roam, WakeUp override)
       └─ Evaluate(unit, ctx) × N — writes to ctx.accumulatedScore, ctx.thresholdAccumulator, ctx.zoneInfluenceAccumulator, ctx.reachabilityScore
            └─ PostProcess(unit, ctx)  — second-pass scoring adjustment (ConsiderZones overrides)
                 └─ Score(unit, tile) → float
                      └─ GetUtilityThreshold(unit, tile) → float
                           └─ GetTileZoneModifier(tile) → TileModifier
````

**EvaluationContext fields written by Evaluate overrides:**

| Offset | Name | Written by |
|---|---|---|
| +0x20 | reachabilityScore | DistanceToCurrentTile |
| +0x24 | zoneInfluenceAccumulator | ConsiderZones |
| +0x28 | accumulatedScore | Most Evaluate overrides |
| +0x30 | thresholdAccumulator | ConsiderZones, CoverAgainstOpponents |
| +0x60 | isObjectiveTile (bool) | ThreatFromOpponents.Score B |

**Score formula (from Stage 1, confirmed):**
````
Score = expf(movEffTable[GetMovementEffectivenessIndex(tile, unit)] + 1.0)
        × (W_attack × fAtk + W_ammo × fAmmo + W_deploy × fDeploy + W_sniper × fSniper)
````

---

## 5. ThreatFromOpponents

### Role
Scores candidate tiles based on how threatening enemy units are from those positions. Requests 4 worker threads (`GetThreads` = 4), making it the most computationally expensive criterion.

### ThreatFromOpponents.GetThreads — 0x18054E040
Returns hardcoded `4`. All other criteria use the default (inherited, value unknown but presumed 1).

### ThreatFromOpponents.Evaluate — 0x18076ACB0

**Guard:** requires enemy count > 1 (vtable +0x468).

**Phase 1 — Ally tile occupant threat (conditional):**
If the candidate tile is NOT the unit's current tile, and the tile is occupied by an ally:
````
ctx.accumulatedScore += (2.0 - allyHealthRatio) * W_threat * (maxMoves / weaponCount) * Score_B(allyOccupant)
````
- `(2.0 - healthRatio)` = wounded allies contribute more threat weight (motivates protecting them)
- `W_threat` = `AIWeightsTemplate +0x74`

**Phase 2 — Self threat (always):**
````
ctx.accumulatedScore += Score_B(self) * W_threat
````

### ThreatFromOpponents.Score (A) — 0x18076AF90

Per-weapon-per-tile threat evaluator. Returns `CONCAT44(flag, score)` — a composite 64-bit value packing a float score and an int metadata flag.

**Weapon loop:**
- Iterates non-ranged weapon slots from `unit.movePool +0x48`
- For each slot: applies range gates A and B (`IsWithinRangeA`, `IsWithinRangeB`)
- If both pass: calls `Criterion.Score` and keeps the maximum

**Post-loop multiplier cascade** (applied to max score):

| Condition | Multiplier source |
|---|---|
| 1 enemy, not deployment phase 2 | `settings +0x98` (coverMult_Quarter) |
| Not deployment, weapon not ranged | `settings +0x8c` (coverMult_Full) |
| Deployment phase 2, weapon not ranged | `settings +0x94` (coverMult_Low) |
| Multiple enemies, not deployment | `settings +0x90` (coverMult_Partial) |
| isObjectiveTile | `settings +0x9c` (coverMult_None) |
| Weapon list distance < threshold | `settings +0xa0` (flanking bonus) |

Threshold gate at `settings +0xac`. If the weapon-list distance score exceeds this, the flanking bonus is skipped.

### ThreatFromOpponents.Score (B) — 0x18076B710

Spatial threat scorer. Scans a bounding box of tiles around each enemy and finds the highest-scoring candidate using Score (A) with spatial modifiers.

**Radius calculation:**
````
local_138 = (weaponStats.baseRange / (squadCapacity_field + 1)) / 2
````

**Spatial modifiers applied to Score A result:**

| Condition | Multiplier |
|---|---|
| Flanking direction (facing toward unit) AND path clear | × 1.2 |
| Moving away from enemy (direction decreasing) | × 0.9 |
| Moving toward enemy (direction increasing) | × 1.2 |
| Leaving choke point, flanking slot count > 2 | × 0.8 |
| Long-range weapon flag (`weaponData +0xc8 > 0x7fffffff`) | × 1.2 |

**Distance falloff:**
````
score *= (1.0 - dist / (halfWidth × 3.0))
````

**Side effect:** writes `ctx.isObjectiveTile` (`ctx +0x60`) via `FUN_1805df360` during opponent iteration.

### Methods table

| Method | RVA | VA |
|---|---|---|
| GetThreads | 0x54E040 | 0x18054E040 |
| Evaluate | 0x76ACB0 | 0x18076ACB0 |
| Score (A) | 0x76AF90 | 0x18076AF90 |
| Score (B) | 0x76B710 | 0x18076B710 |
| GetThreads (non-default) | 0x54E040 | 0x18054E040 |

### ThreatFromOpponents — new field confirmations

**AIWeightsTemplate:**
- `+0x74` = `W_threat` (float, confirmed)
- `+0x98` = `coverMult_Quarter` (float, confirmed)
- `+0xa0` = `flankingBonusMultiplier` (float, confirmed)
- `+0xac` = `weaponListDistanceThreshold` (float, confirmed)

**EvaluationContext:**
- `+0x60` = `isObjectiveTile` (bool, confirmed — written by Score B)

---

## 6. ConsiderZones

### Role
Evaluates tiles based on their membership in strategic zones. Each zone carries a bitmask of flags that determine how tiles within it affect the scoring context.

### ConsiderZones.Evaluate — 0x18075CC20

**Guard:** unit must have at least 2 move range; zone list must be non-empty.

Iterates the zone tile list from `unit.opponentList` → zone list → tile list.

**Zone flag bitmask system** (tested via `TileHasZoneFlag(tile, bit)`):

| Flag bit | Meaning | Effect |
|---|---|---|
| 0x01 | Zone membership | `ctx.thresholdAccumulator += 9999.0` (forces tile above threshold) |
| 0x04 | Team-ownership | If same team: `ctx.thresholdAccumulator += 9999.0`; if enemy: apply standard weight |
| 0x08 | Repulsion | Negates the influence sign for flag 0x10 |
| 0x10 | Proximity influence | `ctx.zoneInfluenceAccumulator += settings.zoneInfluenceWeight × dist × tileData.+0x24 × sign` |
| 0x20 | Outer boundary | Loop skip condition; used as terminator |

**Post-loop zone weight writes (ctx.thresholdAccumulator):**
- `ctx.thresholdAccumulator += tileData.+0x24 × threshold × settings.zoneThresholdWeight_A` (for matching tile)
- `ctx.thresholdAccumulator += tileData.+0x24 × threshold × settings.zoneThresholdWeight_B` (for non-matching)
- Both writes enforce a floor of `threshold` (min value is the raw threshold, never below)

### ConsiderZones.PostProcess — 0x18075D3B0

Two-pass function.

**Pass 1:** Scans zone list for any tile with `TileHasZoneFlag(tile, 3)` (flags 1+2 combined = objective zone tile). If found, sets `isObjectiveFlag = true`.

**Pass 2:** Iterates the full tile score dictionary. For each tile whose `thresholdAccumulator >= threshold`:
- Checks if a matching zone tile (flag 3) exists at the same coordinates.
- Gets unit status via `vtable +0x398 → +0x8c`:
  - If `statusField == 1`: `zoneMultiplier = settings +0x64`
  - Else: `zoneMultiplier = settings +0x60`
- For tiles at the matching zone position: `ctx.accumulatedScore *= zoneMultiplier`
- For other tiles where `isObjectiveFlag = true`: `ctx.thresholdAccumulator += fVar6`

### Methods table

| Method | RVA | VA |
|---|---|---|
| Collect | 0x75C630 | 0x18075C630 |
| Evaluate | 0x75CC20 | 0x18075CC20 |
| PostProcess | 0x75D3B0 | 0x18075D3B0 |

### New AIWeightsTemplate fields (ConsiderZones)

| Offset | Name | Confirmed |
|---|---|---|
| +0x58 | zoneInfluenceWeight | confirmed |
| +0x5c | zoneInfluenceSecondaryWeight | confirmed |
| +0x60 | zoneScoreMultiplier_A | confirmed |
| +0x64 | zoneScoreMultiplier_B | confirmed |
| +0x68 | zoneThresholdWeight_A | confirmed |
| +0x6c | zoneThresholdWeight_B | confirmed |

### New ctx fields (ConsiderZones)

| Offset | Name | Confirmed |
|---|---|---|
| +0x24 | zoneInfluenceAccumulator | confirmed |

---

## 7. DistanceToCurrentTile

### Role
Accumulates a `reachabilityScore` on the tile context proportional to how far the candidate tile is from the unit's current position, modulated by the zone modifier and penalised when the tile is beyond the unit's effective reach.

### DistanceToCurrentTile.Evaluate — 0x180760CF0
````
effectiveRange = max(weaponStats.baseRange + weaponList.bonusRange, 1)
dist           = GetTileDistance(ctx.tileRef, unit.currentTile)
modScale       = TileModifier.distanceScaleFactor   // +0x20
penalty        = (moveSpeed / effectiveRange < dist) ? settings.outOfRangePenalty : 1.0
ctx.reachabilityScore += (float)dist × modScale × penalty
````

**New confirmed fields:**
- `ctx +0x20` = `reachabilityScore`
- `TileModifier +0x20` = `distanceScaleFactor`
- `AIWeightsTemplate +0x158` = `outOfRangePenalty`
- `vtable +0x458` / `+0x460` = `GetMoveSpeed()` → int
- `weaponStatsBlock +0x118` = weapon base range (int)
- `WeaponList +0x3c` = bonus range modifier (int)

### Methods table

| Method | RVA | VA |
|---|---|---|
| Evaluate | 0x760CF0 | 0x180760CF0 |

---

## 8. ExistingTileEffects

### Role
Scores tiles that carry active tile effects whose type matches the evaluating unit. Uses a two-level type-check system and an effect immunity bitmask from TileModifier.

### ExistingTileEffects.Evaluate — 0x180760FB0

**Guard:** `ctx.tileRef` must exist; `HasTileEffects(tile)` must return true.

Reads `TileModifier.effectImmunityMask` (`mod +0x44` — uint bitmask). Iterates the tile's effect list (`tile +0x68`). For each effect:
- Gets effect flags via `vtable +0x178 → +0x88`.
- **Immunity check:** skips if `(flags != 0) && ((flags & immunityMask) == flags)` — effect is fully covered by zone immunity.
- Type-checks the effect object against two class descriptors (`DAT_183952b10`, `DAT_183952a58`).
- Calls `CheckEffectFlag(effectSlot, 0xe)` and `CheckEffectFlag(effectSlot, 0xa0)`.
- If `tile +0xf2 != 0` (hasTileEffect flag): calls `Criterion.Score` and writes:
````
ctx.accumulatedScore += settings.tileEffectMultiplier × Score(unit, effectTile, ctx, ctx, 1)
                        × settings.tileEffectScoreWeight
````

**New confirmed fields:**
- `tile +0xf2` = `hasTileEffect` (bool — distinct from `+0xf3` = isObjectiveTile)
- `tile +0x68` = tile effects list
- `TileModifier +0x44` = `effectImmunityMask` (uint)
- `AIWeightsTemplate +0x78` = `tileEffectScoreWeight`
- `AIWeightsTemplate +0x7c` = `tileEffectMultiplier`

### Methods table

| Method | RVA | VA |
|---|---|---|
| Evaluate | 0x760FB0 | 0x180760FB0 |

---

## 9. AvoidOpponents

### Role
Accumulates a penalty to `ctx.accumulatedScore` for tiles near opponent groups that **cannot** directly target the evaluating unit. Represents indirect/area threat.

### AvoidOpponents.Evaluate — 0x18075BE10

Iterates `ScoringContext.singleton.avoidGroups` (`singleton +0xa8`). For each group:
- Skips if `group.teamId == unit.teamId` (same team, not a threat).
- Skips if `group.teamId == unit.teamId` (already covered by team filter).
- For each tile in the group's tile list:
  - Skips if `TileTeamMatches(tile, unit.teamId)` returns false (tile not relevant to this unit's team).
  - Gets tile position; measures distance from `ctx.tileRef`.
  - If `dist < 11`:
    - If the group **cannot target** unit's team (`vtable +0x188 == false`): `fAccum += expf(settings.avoidIndirectThreatWeight)` (+0xb4)
    - If the group **can target** unit's team: `fAccum += expf(settings.avoidDirectThreatWeight)` (+0xb0)
- `ctx.accumulatedScore += fAccum`

**New confirmed fields:**
- `AIWeightsTemplate +0xb0` = `avoidDirectThreatWeight`
- `AIWeightsTemplate +0xb4` = `avoidIndirectThreatWeight`
- `ScoringContext.singleton +0xa8` = `avoidGroups` (array of opponent group objects)
- `unit +0x4c` = `teamIndex` (int, used for group/tile team matching)

### Methods table

| Method | RVA | VA |
|---|---|---|
| Evaluate | 0x75BE10 | 0x18075BE10 |

---

## 10. FleeFromOpponents

### Role
Identical structure to AvoidOpponents but inverted polarity and larger radius. Accumulates a penalty for tiles near groups that **can** directly target the unit, within a range of 16 tiles.

### FleeFromOpponents.Evaluate — 0x1807613A0

Identical group-iteration structure to AvoidOpponents. Key differences:
- **Range threshold:** `dist < 16` (vs. 11 for AvoidOpponents)
- **Polarity:** only accumulates for groups that **CAN** target unit's team (`vtable +0x188 == true`) — opposite of AvoidOpponents
- **Weight:** `expf(settings.fleeWeight)` where `settings +0xb8`
````
for each opponent group:
    skip if same team
    skip if group CANNOT target unit (opposite of AvoidOpponents)
    for each matching tile within dist < 16:
        fAccum += expf(settings.fleeWeight)
ctx.accumulatedScore += fAccum
````

**New confirmed field:**
- `AIWeightsTemplate +0xb8` = `fleeWeight`

### Methods table

| Method | RVA | VA |
|---|---|---|
| Evaluate | 0x7613A0 | 0x1807613A0 |

---

## 11. Roam

### Role
Populate the candidate tile list for melee units that have no active targets. Selects from a bounding box around the unit's current position filtered for passable, unoccupied, reachable tiles.

### Roam.Collect — 0x180768300

**Guards:**
- Returns if unit's weapon is ranged (`IsRangedWeapon` check). Roam is melee-only.
- Returns if `unit.opponentList +0x40` does not have roam flag 0x21 (`HasRoamFlag` check).

**Core logic:**
````
effectiveRange = max(weaponStats.baseRange + weaponList.bonusRange, 1)
roamRadius     = moveSpeed / effectiveRange
if roamRadius < 1: return  // can't roam

// Build bounding box around currentTile ± roamRadius, clamped to grid
for each tile in bounding box:
    if tile.isBlocked (bit 0 of +0x1c) or tile.isOccupied (bit 2 of +0x1c): skip
    if !IsCurrentTile(tile): skip
    if HasTileEffects(tile): skip
    if GetTileDistance(tile, currentTile) > roamRadius: skip
    add to candidate list

shuffle candidate list
pick first candidate

if no existing score entry: create new entry with thresholdAccumulator = GetUtilityThreshold × 100
else: update existing entry += GetUtilityThreshold × 100
add tile to global shared tile list
````

**New confirmed fields:**
- `unit.opponentList +0x40` = `behaviorConfig` (object holding roam flag 0x21 and other behavior flags)
- `tile +0x1c` bit 0 = `isBlocked`; bit 2 = `isOccupied`
- `ScoringContext.singleton +0x28` = `tileGrid` (confirmed)
- `TileScoreObject +0x30` = `thresholdValue` (written as `GetUtilityThreshold × 100`)

### Methods table

| Method | RVA | VA |
|---|---|---|
| Collect | 0x768300 | 0x180768300 |

---

## 12. WakeUp

### Role
Determines whether the unit should act to wake a sleeping ally. `Collect` scans nearby allies for sleeping units that meet wake conditions. `.ctor` delegates to base with no extra field init.

### WakeUp..ctor — 0x180518FA0

**Resolved:** Calls `Criterion_ctor` (base constructor) and returns. No additional field initialisation. Divergent `.ctor` slot is a compiler artefact.

### WakeUp.Collect — 0x180787DD0

**Phase 1 — Ally scan:**
Iterates `unit.movePool +0xc8 → +0x10 → +0x20` (ally tile list). For each ally:
- Skips if `ally +0x162 != 0` (ally is already awake).
- Skips if `ally +0x48 == 0` (ally has no wake condition object).
- Skips if `ally +0x140 < 1` (ally wake priority below threshold).
- If `ally == self`: break.
- If unit can reach ally (`FUN_1805df360`): set `movePool +0x51 = 0` and return. (Wake resolved.)

**Phase 2 — Opponent proximity:**
If no ally found in Phase 1, iterates `unit.movePool +0x10 → +0x48` (opponent tile list). If any opponent tile is in range and team-matched: sets `movePool +0x51 = 0` and returns.

**New confirmed fields:**
- `ally +0x162` = `isAwake` (bool; 0 = sleeping)
- `ally +0x48` = `wakeCondition` (ptr; null = no condition)
- `ally +0x140` = `wakePriority` (int; must be ≥ 1 to be a wake target)
- `movePool +0x51` = `wakeupPending` flag (bool)
- `unit.movePool +0x10 +0x20` = ally tile list
- `unit.movePool +0x10 +0x48` = opponent tile list
- `unit.movePool +0x10 +0x14` = zoneTeamId

### Methods table

| Method | RVA | VA |
|---|---|---|
| .ctor | 0x518FA0 | 0x180518FA0 |
| Collect | 0x787DD0 | 0x180787DD0 |

---

## 13. Supporting Infrastructure

### GetTileScoreComponents — 0x1806E0AC0

Populates a 6-slot `float[]` passed as `param_1`. Slot layout:

| Index | Content |
|---|---|
| [0] | Raw score (0–100, centiscale, clamped, floored to param_5+0x78 minimum) |
| [1] | Tile base value (`GetTileBaseValue`) |
| [2] | Derived score component (`GetDerivedScoreComponent`) |
| [3] | Movement effectiveness index (via `FUN_180531700`) |
| [4] | isObjective flag byte (1 if tile +0xf3 set, else 0) |
| [5] | Distance offset component (only when param_7 != 0 and param_3 != 0) |

**Early exit:** If `tile +0xf3 != 0` (objective tile), returns `[0]=100.0`, `[4]=1` immediately.

**Centiscale confirmed:** The raw score is stored 0–100 in component [0]. All call sites multiply by 0.01 to convert to [0,1] range. The `× 0.01` is at the call site, not inside this function.

**New tile fields:**
- `tile +0xf3` = `isObjectiveTile` (tile-side flag — distinct from `ctx +0x60`)
- `tile +0x78` (via param_5 +0x78) = minimum score floor (int)

### GetMoveRangeData — 0x1806DF4E0

Populates a `MoveRangeData` object (`param_9`). All output fields confirmed:

| Offset | Field | Type | Notes |
|---|---|---|---|
| +0x10 | attackRange | float | Attack effectiveness score |
| +0x14 | ammoRange | float | Ammo-adjusted range score |
| +0x18 | moveCostNorm | float | Normalised move cost, floored to squadCount |
| +0x1c | moveCostToTile | float | Raw move cost ratio |
| +0x20 | maxReachability | float | Maximum reachability metric |
| +0x24 | canAttackFromTile | bool | Can unit attack from this tile |
| +0x25 | canFullyReach | bool | Can unit fully reach this tile within move budget |
| +0x28 | tileScorePtr | ptr | Write-barriered pointer to TileScore object |

**TileScore object fields accessed (at param_6):**

| Offset | Content |
|---|---|
| +0x110 | secondary movement cost multiplier |
| +0x128 | per-step movement cost multiplier |
| +0x13c | tertiary cost multiplier |
| +0x140 | primary weight multiplier |
| +0x144 / +0x148 | attack range scalers (vs unit.moveRange) |
| +0x14c / +0x150 | ammo range scalers (vs ammoSlotCount) |
| +0x16c / +0x170 | ammo count adjustment parameters |
| +0x8c | overwatch/status field (used as ScoredTileData multiplier) |

**New unit field:**
- `unit +0x5b` = `ammoSlotCount` (int)

**New tile field:**
- `tile +0x244` = `accuracyDecay` (int, scaled × 0.01 for range degradation)

### GetTileZoneModifier — 0x18071AE10
````c
TileModifier GetTileZoneModifier(opponentList) {
    ZoneDescriptor* zone = opponentList->zoneDescriptor;  // opponentList +0x18
    if (zone != null) {
        object* zoneData = zone->vtable->GetStatusEffects(zone);  // vtable +0x398
        if (zoneData != null) {
            return *(TileModifier*)(zoneData + 0x310);
        }
    }
    NullReferenceException();
}
````

`TileModifier` is an 8-byte struct returned by value, located at `zoneData +0x310`. The class name of `zoneData` requires a `dump.cs` lookup on the return type of `vtable +0x398`.

**Confirmed TileModifier fields (cumulative):**

| Offset | Field | Type | Confirmed |
|---|---|---|---|
| +0x14 | minThresholdScale | float | confirmed (Stage 1) |
| +0x18 | thresholdMultiplier | float | confirmed (Stage 1) |
| +0x20 | distanceScaleFactor | float | confirmed (Stage 2) |
| +0x44 | effectImmunityMask | uint | confirmed (Stage 2) |

### FUN_1804bad80 — MathCurve Resolved

**Q2 resolved.** `FUN_1804bad80` is a **single-argument exponential growth curve** equivalent to `expf(x)`. The function body implements a full IEEE 754 `powf` kernel but is called at all observed call sites with a single computed float argument, with the "exponent" parameter being a second field from the same struct. The net effect is a monotonic growth/decay transform applied to [0,1] fractions.

All Stage 1 formula entries using `MathCurve(x)` should be read as `expf(x)`.

### IsWithinRangeA — 0x1806E3C50

Two-stage range check:
1. `IsValidRangeType(tile, rangeType)` — range type gate
2. If tile has no range constraint (`tile +0xe4 == 0`): return true
3. If tile has context requirement (`tile +0xf1 != 0`): `TileMatchesContext(scoreObj, unit)` must pass
4. `IsInMeleeRange(tile, unit, scoreObj, rangeTypeLow)` AND `IsInAttackRange(tile, scoreObj, unit, rangeType)` must both return true

### IsWithinRangeB — 0x1806E33A0

AND-gate across all weapon slots on the tile (`tile +0x48`). Each slot's `vtable +0x1d8` (`CheckRangeCondition(unit, target)`) must return true. Returns true if all slots pass; false immediately on any failure.

**New tile field:**
- `tile +0x48` = `weaponSlots` list (tile-side weapon slot list — distinct from unit's weapon list)

---

## 14. Criterion.IsDeploymentPhase — 0x18071B670
````c
bool Criterion_IsDeploymentPhase() {
    ScoringContext* ctx = ScoringContext.singleton;
    return ctx->phase == 0;   // ctx +0x60
}
````

**New ScoringContext.singleton field:**
- `ScoringContext.singleton +0x60` = `phase` (int; 0 = deployment phase, 1 = standard, 2 = post-deployment)

The phase system has at least 3 states. `vtable +0x478` returns the current phase as an int. Criterion.IsDeploymentPhase checks for phase 0. Score (A) gates on phase 2.

---

## 15. Ghidra Address Reference

### Fully Analysed

| Stage | VA | Method | Notes |
|---|---|---|---|
| 1 | 0x1804EB570 | Criterion..ctor | Complete |
| 1 | 0x18075EB00 | CoverAgainstOpponents..cctor | Complete |
| 1 | 0x180760070 | Criterion.GetUtilityThreshold | Complete |
| 1 | 0x18075DAD0 | CoverAgainstOpponents.Evaluate | Complete |
| 1 | 0x180760140 | Criterion.Score | Complete |
| 2 | 0x18054E040 | ThreatFromOpponents.GetThreads | Complete — returns 4 |
| 2 | 0x18076ACB0 | ThreatFromOpponents.Evaluate | Complete |
| 2 | 0x18076AF90 | ThreatFromOpponents.Score (A) | Complete |
| 2 | 0x18076B710 | ThreatFromOpponents.Score (B) | Complete |
| 2 | 0x1806E0AC0 | GetTileScoreComponents | Complete |
| 2 | 0x1806DF4E0 | GetMoveRangeData | Complete |
| 2 | 0x1804BAD80 | MathCurve (expf) | Complete — resolved as expf-equivalent |
| 2 | 0x18071AE10 | GetTileZoneModifier | Complete |
| 2 | 0x18075CC20 | ConsiderZones.Evaluate | Complete |
| 2 | 0x18075D3B0 | ConsiderZones.PostProcess | Complete |
| 2 | 0x18075BE10 | AvoidOpponents.Evaluate | Complete |
| 2 | 0x18071B670 | Criterion.IsDeploymentPhase | Complete |
| 2 | 0x180518FA0 | WakeUp..ctor | Complete — no additional fields |
| 2 | 0x180760CF0 | DistanceToCurrentTile.Evaluate | Complete |
| 2 | 0x180760FB0 | ExistingTileEffects.Evaluate | Complete |
| 2 | 0x1807613A0 | FleeFromOpponents.Evaluate | Complete |
| 2 | 0x180768300 | Roam.Collect | Complete |
| 2 | 0x180787DD0 | WakeUp.Collect | Complete |
| 2 | 0x1806E3C50 | IsWithinRangeA | Complete |
| 2 | 0x1806E33A0 | IsWithinRangeB | Complete |

### Not Yet Analysed

| VA | Method | Notes |
|---|---|---|
| 0x18075C630 | ConsiderZones.Collect | Deferred |
| 0x18071B670 dep: 0x1806E3750 | IsInMeleeRange | Range gate sub-call |
| 0x1806E60A0 | IsInAttackRange | Range gate sub-call |
| 0x1806E3D50 | IsValidRangeType | Range type gate |
| 0x18071B670 | Criterion.IsDeploymentPhase | Complete (listed above) |
| All IsValid impls | 10 classes | Deferred — low priority |

---

## 16. Key Inferences and Design Notes

1. **ThreatFromOpponents is the dominant criterion.** It requests 4 threads and has by far the most complex scoring logic (three functions, spatial scan, multi-layer multipliers). Every other criterion is single-threaded and much simpler.

2. **The phase system gates significant behaviour.** Cover multipliers, deployment bonuses, and flee weights all branch on `ScoringContext.phase` (0/1/2). Phase 0 = deployment, phase 2 = post-deployment. This means the AI evaluates tile desirability very differently during deployment vs. combat.

3. **`expf` is used extensively as a score transform.** `AvoidOpponents`, `FleeFromOpponents`, and `GetMoveRangeData` all call `expf` on weight constants rather than multiplying directly. This means the weights in `AIWeightsTemplate` are exponent inputs, not linear multipliers. Small changes to e.g. `avoidDirectThreatWeight` have exponential effect.

4. **Two distinct "objective tile" flags exist.** `tile +0xf3` is a tile-side flag set in tile data. `ctx +0x60` is a per-evaluation flag written by ThreatFromOpponents.Score B via `FUN_1805df360`. These are not the same and are written by different systems.

5. **Zone threshold manipulation via 9999.0.** ConsiderZones writes `ctx.thresholdAccumulator += 9999.0` to guarantee a tile passes the threshold gate — it is not a real score, it is a bypass. Tiles in owned zones are unconditionally promoted above any possible threshold.

6. **Roam is melee-only by design.** The first guard in `Roam.Collect` hard-exits for ranged units. This is not a configuration option — it is structurally enforced in the code.

7. **WakeUp uses a two-phase Collect.** Phase 1 looks for sleeping allies to wake. Phase 2 falls back to opponent proximity to determine if waking is urgent. The output is a flag (`movePool +0x51`) not a tile list, which suggests WakeUp may work differently from other Collect overrides.

8. **FleeFromOpponents and AvoidOpponents are mirror images.** Same structure, opposite polarity on the `CanTarget` check, different distance threshold (16 vs 11), different weight constant. This pair together models both direct threat pressure (flee) and area denial (avoid).

---

## 17. Open Questions

**Q1.** What are the actual runtime values of `COVER_PENALTIES[4]`?  
→ Memory dump `CoverAgainstOpponents.COVER_PENALTIES` at runtime, or view `.cctor` assembly listing for the four literal float pushes.

**Q3.** What is the managed class name for `zoneData` (returned by `vtable +0x398`)?  
→ Run `extract_rvas.py` on the class returned by vtable slot +0x398 on the ZoneDescriptor type; alternatively search `dump.cs` for a class with a field at offset 0x310.

**Q5-new.** What is the full field layout of the TileScore object (param_6 in GetMoveRangeData)?  
→ Run `extract_rvas.py` on the class assigned to `DAT_183981fc8` (ScoringContext_class); it holds the TileScore type.

**Q9.** Full `AIWeightsTemplate` field layout for offsets 0x100–0x140.  
→ Run `extract_rvas.py` on `AIWeightsTemplate` class.

**Q10.** Behaviour selection layer consuming Score output.  
→ Scoped out — outside Criterions namespace. Requires operator acknowledgement before pursuing.

**Q-new-A.** Exact semantics of `IsInMeleeRange` and `IsInAttackRange` (sub-calls of IsWithinRangeA).  
→ Analyse 0x1806E3750 and 0x1806E60A0.

**Q-new-B.** `ConsiderSurroundings.Evaluate` not yet analysed (TDI 3672).  
→ Extract RVAs and analyse.

**Q-new-C.** `ConsiderZones.Collect` (0x18075C630) not yet analysed.  
→ Batch with ConsiderSurroundings.