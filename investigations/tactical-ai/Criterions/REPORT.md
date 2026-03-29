# Menace — Tactical AI Criterions — Investigation Report

| Field | Value |
|---|---|
| Game | Menace |
| Platform | PC (Windows x64) |
| Binary | GameAssembly.dll (Unity IL2CPP) |
| Image base | `0x180000000` |
| VA formula | `VA = RVA + 0x180000000` |
| Namespace | `Menace.Tactical.AI.Behaviors.Criterions` |
| Source material | Il2CppDumper dump.cs, Ghidra decompilation (25 VAs), extract_rvas.py extraction report |
| Investigation status | **Complete** (ConsiderSurroundings.Evaluate deferred; all other namespace members fully analysed) |

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. The Core Scoring Pipeline
5. The Master Formula (Criterion.Score)
6. Full Class Reference
   - 6.1 Criterion (base)
   - 6.2 CoverAgainstOpponents
   - 6.3 ThreatFromOpponents
   - 6.4 ConsiderZones
   - 6.5 DistanceToCurrentTile
   - 6.6 ExistingTileEffects
   - 6.7 AvoidOpponents
   - 6.8 FleeFromOpponents
   - 6.9 Roam
   - 6.10 WakeUp
   - 6.11 ConsiderSurroundings
7. Supporting Infrastructure
8. AIWeightsTemplate — Field Reference
9. EvaluationContext — Field Reference
10. Auxiliary Object Field Reference
11. Ghidra Address Reference
12. Key Inferences and Design Notes
13. Open Questions

---

## 1. Investigation Overview

This investigation reverse-engineered the complete tile-scoring subsystem of Menace's tactical AI, implemented in the `Menace.Tactical.AI.Behaviors.Criterions` namespace. The namespace contains 11 concrete `Criterion` subclasses that collectively determine where AI-controlled units choose to move on the tactical grid.

**Achieved:**

- All 11 `Criterion` subclasses enumerated and their roles confirmed.
- `Criterion.Score` — the master scoring formula — fully reconstructed. It is a four-component weighted utility score scaled by a movement effectiveness curve.
- `Criterion.GetUtilityThreshold` — threshold gate formula — fully reconstructed.
- `CoverAgainstOpponents.Evaluate` — three-phase cover-quality evaluator — fully reconstructed.
- `ThreatFromOpponents.Evaluate`, `Score (A)`, `Score (B)` — the most computationally expensive criterion, using 4 worker threads and a spatial scan — fully reconstructed.
- `ConsiderZones.Evaluate` and `ConsiderZones.PostProcess` — zone-flag bitmask system and objective-tile promotion logic — fully reconstructed.
- `DistanceToCurrentTile.Evaluate`, `ExistingTileEffects.Evaluate`, `AvoidOpponents.Evaluate`, `FleeFromOpponents.Evaluate` — all fully reconstructed.
- `Roam.Collect` and `WakeUp.Collect` — special-case collection passes — fully reconstructed.
- 5 infrastructure functions: `GetTileScoreComponents`, `GetMoveRangeData`, `GetTileZoneModifier`, `IsWithinRangeA`, `IsWithinRangeB` — fully reconstructed.
- `FUN_1804bad80` confirmed as an `expf`-equivalent monotone growth curve.
- `Criterion.IsDeploymentPhase`, `ThreatFromOpponents.GetThreads`, `WakeUp..ctor`, `CoverAgainstOpponents..cctor` — all confirmed.
- 30+ field offsets confirmed on `AIWeightsTemplate`, `EvaluationContext`, `Unit`, `MovePool`, `MoveRangeData`, `TileModifier`, `ScoringContext`, `Tile`, and auxiliary objects.

**Explicit scope boundary — what was NOT investigated:**

- `ConsiderSurroundings.Evaluate` (TDI 3672) — the one Evaluate override not yet decompiled.
- `ConsiderZones.Collect` (VA 0x18075C630) — deferred.
- All 10 `IsValid` implementations — interface documented; implementations structurally predictable and low priority.
- `IsInMeleeRange` (0x1806E3750) and `IsInAttackRange` (0x1806E60A0) — range-gate sub-calls; semantics partially understood from callers.
- `IsValidRangeType` (0x1806E3D50) — trivial gate.
- `AIWeightsTemplate` field offsets 0x100–0x140 — not extracted.
- Runtime values of `COVER_PENALTIES[4]` — not resolved.
- The behaviour selection layer consuming `Score` output — outside this namespace; explicitly deferred.

---

## 2. Tooling

`extract_rvas.py` was used prior to Ghidra analysis to enumerate all 11 classes, their method RVAs, and the one static field (`CoverAgainstOpponents.COVER_PENALTIES`). The extraction report identified the shared constructor RVA (`0x4EB570`) shared by 10 of 11 classes, and the shared virtual no-op stub (`0x4F7EE0`) used for base `Collect`, `Evaluate`, and `PostProcess` implementations. `WakeUp`'s divergent `.ctor` (RVA `0x518FA0`) was flagged and subsequently confirmed as a compiler artefact with no additional initialisation logic.

All field offsets were derived from Ghidra decompilation and cross-referenced against the extraction report. No additional `extract_rvas.py` runs were performed beyond the initial namespace extraction.

---

## 3. Class Inventory

| Class | TypeDefIndex | Role |
|---|---|---|
| `Criterion` | 3670 | Abstract base; defines the scoring pipeline interface (`Collect`, `Evaluate`, `PostProcess`, `Score`, `GetUtilityThreshold`, `IsValid`) |
| `AvoidOpponents` | 3671 | Penalises tiles near opponent groups that cannot directly target the unit (indirect threat area denial) |
| `ConsiderSurroundings` | 3672 | Not analysed — role unknown |
| `ConsiderZones` | 3673 | Scores tiles based on strategic zone membership and zone flag bitmasks; promotes objective tiles above threshold |
| `CoverAgainstOpponents` | 3674 | Scores tiles by cover quality against each known enemy; penalises occupied tiles with high-threat occupants |
| `DistanceToCurrentTile` | 3675 | Accumulates a reachability score proportional to distance from the unit's current position, modulated by zone scale and an out-of-range penalty |
| `ExistingTileEffects` | 3676 | Scores tiles that carry active tile effects matching the evaluating unit's type, filtered by zone immunity mask |
| `FleeFromOpponents` | 3677 | Penalises tiles near opponent groups that can directly target the unit; mirror of AvoidOpponents with larger radius |
| `Roam` | 3678 | Populates the candidate tile list for melee units with no active targets, using a bounding-box scan around the unit's current position |
| `ThreatFromOpponents` | 3679 | Scores tiles based on threat posed by enemy units; uses 4 worker threads and a spatial scan with direction and distance multipliers |
| `WakeUp` | 3680 | Determines if the unit should act to wake a sleeping ally; sets a `wakeupPending` flag on the move pool rather than populating a tile list |

---

## 4. The Core Scoring Pipeline

For each candidate tile `T` and each active `Criterion` `C`:

```
1. C.IsValid(unit, ctx)              → bool     gate; skip criterion if false
2. C.Collect(unit, ctx)              → void     populates candidate tile list (Roam, WakeUp override)
3. C.Evaluate(unit, ctx) × N         → void     writes delta to ctx.accumulatedScore and ctx.thresholdAccumulator
4. C.PostProcess(unit, dict, ...)    → void     second-pass scoring adjustment (ConsiderZones overrides)
5. Criterion.Score(unit, T, ctx, tileData) → float  final weighted scalar from accumulated scores
6. Compare Score against GetUtilityThreshold(unit, T) → keep tile if score > threshold
```

The `EvaluationContext` fields written across all `Evaluate` overrides:

| Offset | Field | Written by |
|---|---|---|
| `+0x20` | `reachabilityScore` | `DistanceToCurrentTile.Evaluate` |
| `+0x24` | `zoneInfluenceAccumulator` | `ConsiderZones.Evaluate` |
| `+0x28` | `accumulatedScore` | Most Evaluate overrides |
| `+0x30` | `thresholdAccumulator` | `CoverAgainstOpponents.Evaluate`, `ConsiderZones.Evaluate`, `Roam.Collect` |
| `+0x60` | `isObjectiveTile` (bool) | `ThreatFromOpponents.Score (B)` |

---

## 5. The Master Formula (Criterion.Score)

`Criterion.Score` is the final step of the pipeline. It combines four independent utility components with a movement-effectiveness curve multiplier.

```
rawScore   = GetTileScoreComponents(tile, ...)[0] × 0.01
moveData   = GetMoveRangeData(tile, unit)
rangeCost  = floor(min(rawScore × moveData.moveCostToTile, unit.movePool.maxMoves − 1))
adjScore   = GetReachabilityAdjustedScore(..., rangeCost) × 0.01

// Component A — Attack weight
rangeRatio = min((rawScore × moveData.attackRange) / unit.moveRange, 2.0)
fAtk       = settings.baseAttackWeight × rangeRatio
if rawScore × moveData.moveCostToTile ≥ unit.movePool.maxMoves:
    fAtk × = 2.0
    if GetHealthRatio(unit) > 0.95: fAtk × = 4.0     // near-full-health max-range = 8× base
elif moveData.canAttackFromTile and rawScore > 0:
    fAtk × = 1.1
// + overwatch suppression multipliers from response curve table (expf-scaled)

// Component B — Ammo pressure
if rawScore × moveData.ammoRange > 0:
    ammoLeft  = max(unit.currentAmmo − rawScore × moveData.ammoRange, 0)
    teamSize  = max(unit.squadCount, 1)
    enemies   = min(GetEnemyCountInRange(unit, 3), 200)
    fAmmo     = (GetReloadChance(unit) × enemies − (ammoLeft / teamSize) × enemies)
                × settings.ammoPressureWeight × enemies × 0.0001

// Component C — Deployment/positional bonus
if adjScore > 0:
    combined  = min(adjScore × rawScore + adjScore, 2.0)
    fDeploy   = combined × settings.deployPositionWeight
    if not tile.hasEnemy:
        fDeploy × = (GetMovementDepth(unit) × 0.25 + 1.5)
    if combined ≥ 0.67: fDeploy × = 3.0

// Component D — Sniper bonus (only if unit has sniper-class weapon)
if HasSniperWeapon(unit):
    fSniper   = GetAttackCountFromTile(tile) × rangeSteps × settings.sniperAttackWeight × rawScore
    if not tile.hasEnemy:
        fSniper × = (GetMovementDepth(unit) × 0.25 + 1.5)
    fSniper × = max(GetHealthRatio(unit), 0.25)

// Final combination
movEffIdx  = GetMovementEffectivenessIndex(tile, unit)
movEff     = expf(movEffTable[movEffIdx] + 1.0)
Score      = movEff × (settings.W_attack × fAtk
                     + settings.W_ammo   × fAmmo
                     + settings.W_deploy × fDeploy
                     + settings.W_sniper × fSniper)
```

**Key conventions:**

- Raw scores from `GetTileScoreComponents` are centiscale integers (0–100). All call sites multiply by `0.01` to convert to [0.0, 1.0].
- `FUN_1804bad80` (aliased `expf_approx`) is an `expf`-equivalent single-argument monotone growth curve. Wherever the formula says `expf(x)`, this function is being called.
- Movement effectiveness acts as a global scalar on the entire score. A tile the unit cannot efficiently reach is discounted proportionally, regardless of how good its cover or attack position is.
- The 4× health multiplier (`fAtk × = 4.0` when health > 95%) incentivises healthy units to hold optimal firing positions. A unit at maximum range with >95% health receives 8× the base attack component.

---

## 6. Full Class Reference

### 6.1 Criterion (base class)

**Namespace:** `Menace.Tactical.AI.Behaviors.Criterions` | **TypeDefIndex:** 3670 | **Base:** `object`

Abstract base. Carries no instance fields. All nine virtual methods are defined here; concrete subclasses override the ones relevant to their behaviour.

**Fields:**

| Offset | Type | Name | Status |
|---|---|---|---|
| — | — | *(no instance fields)* | confirmed |

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `.ctor` | `0x4EB570` | `0x1804EB570` | Pass-through to `object::.ctor`; shared by 10/11 subclasses |
| `Collect` | `0x4F7EE0` | `0x1804F7EE0` | Virtual no-op base; shared stub |
| `Evaluate` | `0x4F7EE0` | `0x1804F7EE0` | Virtual no-op base; shared stub |
| `PostProcess` | `0x4F7EE0` | `0x1804F7EE0` | Virtual no-op base; shared stub |
| `IsDeploymentPhase` | `0x71B670` | `0x18071B670` | Returns `ScoringContext.singleton.phase == 0` |
| `GetUtilityThreshold` | `0x760070` | `0x180760070` | Zone-scaled activation threshold |
| `Score` | `0x760140` | `0x180760140` | Master scoring function |
| `GetThreads` | `0x546260` | `0x180546260` | Default thread count; not decompiled |
| `IsValid` | NO_RVA | — | No base implementation; must be overridden |

**`GetUtilityThreshold` formula:**

```
modifier  = GetTileZoneModifier(tile.zoneDescriptor)
threshold = max(settings.baseThreshold, settings.baseThreshold × modifier.minThresholdScale)
return threshold × modifier.thresholdMultiplier
```

**`IsDeploymentPhase`:**

```c
return ScoringContext.singleton->phase == 0;   // phase: 0=deploy, 1=standard, 2=post-deploy
```

---

### 6.2 CoverAgainstOpponents

**TypeDefIndex:** 3674 | **Base:** Criterion

Evaluates how much cover a candidate tile provides against all known opponents. Writes a weighted cover quality score to `ctx.accumulatedScore`. Also penalises tiles occupied by threats.

**Fields:**

| Offset | Type | Name | Status |
|---|---|---|---|
| `0x000` (static) | `float[]` | `COVER_PENALTIES` | confirmed (dump.cs); length=4; values unknown |

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `.cctor` | `0x75EB00` | `0x18075EB00` | Allocates `COVER_PENALTIES float[4]`; values not written here |
| `Evaluate` | `0x75DAD0` | `0x18075DAD0` | Three-phase cover evaluator |
| `IsValid` | `0x75EAB0` | `0x18075EAB0` | Not decompiled |

**Evaluate algorithm:**

```
// Guard
if unit.opponentList is empty: return

// Phase 1 — Occupied tile penalties (only if tile ≠ current tile)
occupant = GetUnitOnTile(tile)
if occupant == allied unit: return
if occupant == enemy and CanTarget(occupant):
    ctx.accumulatedScore -= occupant.weapon.range × settings.rangeScorePenalty
    ctx.accumulatedScore -= occupant.weapon.ammo  × settings.ammoScorePenalty
ctx.thresholdAccumulator += GetUtilityThreshold(unit, tile)

// Phase 2 — Cover quality per enemy
fBest = 0.0;  fSum = 0.0
for each enemy in unit.opponentList:
    if not IsEnemy(enemy): continue
    coverMult  = settings.coverMultiplier[ClassifyCoverType(unit, enemy)]
    dirIdx     = GetDirectionIndex(tile, enemy.tile)    // 0–7
    penalty    = COVER_PENALTIES[dirIdx]
    proximity  = 1.0 - clamp(dist(tile, enemy.tile) / 30.0, 0.1, 1.0)
    tileScore  = rawScore × 0.5 × adjPenalty
               + rawScore × 0.5 × penalty_nextDir
               + rawScore × penalty
    fBest      = max(fBest, tileScore)
    fSum      += tileScore

// Phase 3 — Final write
total = fSum + fBest × settings.bestCoverBonusWeight
for each of 8 directions:
    if direction occupied: total -= settings.occupiedDirectionPenalty
if total ≠ 0 and tile not deployment-locked:
    if not IsChokePoint(tile): total += 10.0
if unit has active debuff and tile is not objective:
    total × = 0.9
ctx.accumulatedScore = total × settings.coverScoreWeight + ctx.accumulatedScore
```

**Cover type multiplier mapping** (from `AIWeightsTemplate`):

| Cover classification | AIWeightsTemplate offset | Label |
|---|---|---|
| Full cover | `+0x8c` | `coverMult_Full` |
| Partial cover | `+0x90` | `coverMult_Partial` |
| Low cover | `+0x94` | `coverMult_Low` |
| Quarter cover | `+0x98` | `coverMult_Quarter` |
| No cover | `+0x9c` | `coverMult_None` |

---

### 6.3 ThreatFromOpponents

**TypeDefIndex:** 3679 | **Base:** Criterion

Scores candidate tiles based on how threatening enemy units are from those positions. The most computationally expensive criterion; requests 4 worker threads. Uses two `Score` overloads: `Score (A)` evaluates a single tile against a single enemy with range gates and multipliers; `Score (B)` performs a spatial scan around each enemy to find the best tile.

**Fields:** None (all data read from unit and settings).

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `GetThreads` | `0x54E040` | `0x18054E040` | Returns hardcoded `4` |
| `Evaluate` | `0x76ACB0` | `0x18076ACB0` | Two-phase: ally occupant + self |
| `Score (A)` | `0x76AF90` | `0x18076AF90` | Per-weapon-per-tile threat; returns packed `(flag, float)` |
| `Score (B)` | `0x76B710` | `0x18076B710` | Spatial scan; writes `ctx.isObjectiveTile` |
| `IsValid` | `0x76AF00` | `0x18076AF00` | Not decompiled |

**Evaluate algorithm:**

```
Guard: enemy count > 1 (vtable +0x468)

Phase 1 — Ally occupant contribution (if tile ≠ current tile and tile occupied by ally):
    contribution = (2.0 - allyHealthRatio) × W_threat × (maxMoves / weaponCount) × Score_B(ally)
    ctx.accumulatedScore += contribution

Phase 2 — Self threat (always):
    ctx.accumulatedScore += Score_B(self) × W_threat
```

**Score (A) — per-tile threat evaluation:**

Iterates non-ranged weapon slots from `unit.movePool`. For each slot: both `IsWithinRangeA` and `IsWithinRangeB` must pass; calls `Criterion.Score` and keeps the maximum. After the loop, applies up to 6 conditional multipliers based on phase, cover type, enemy count, flanking, and weapon type. Returns packed `CONCAT44(weaponRef, maxScore)`.

**Post-loop multiplier table for Score (A):**

| Condition | Source offset |
|---|---|
| 1 enemy, not phase 2 | `settings +0x98` (coverMult_Quarter) |
| Not deployment, weapon not ranged | `settings +0x8c` (coverMult_Full) |
| Phase 2, weapon not ranged | `settings +0x94` (coverMult_Low) |
| Multiple enemies, not deployment | `settings +0x90` (coverMult_Partial) |
| isObjectiveTile | `settings +0x9c` (coverMult_None) |
| Weapon list distance < threshold | `settings +0xa0` (flankingBonusMultiplier) |

**Score (B) — spatial scan:**

```
For each opponent in opponent list:
    ctx.isObjectiveTile = CanReachTarget(unit, opponentTile)       // side effect
    halfWidth = weaponRange / (squadCapacity + 1) / 2
    For each tile in [opponent ± halfWidth] bounding box:
        score = Score_A(tile, opponent)
        if tile ≠ current:
            if flanking direction and path clear: score × = 1.2
            if moving away from enemy:            score × = 0.9
            if moving toward enemy:               score × = 1.2
            if leaving choke point and flank slots > 2: score × = 0.8
            if long-range weapon flag:            score × = 1.2
            score × = (1.0 - dist / (halfWidth × 3.0))   // distance falloff
        keep best score
```

---

### 6.4 ConsiderZones

**TypeDefIndex:** 3673 | **Base:** Criterion

Scores tiles based on their membership in strategic zones. Each zone tile carries a bitmask of flags that determines how the tile affects `ctx.thresholdAccumulator` and `ctx.zoneInfluenceAccumulator`. `PostProcess` then applies a zone score multiplier to all tiles that passed the threshold.

**Fields:** None.

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Collect` | `0x75C630` | `0x18075C630` | Not decompiled |
| `Evaluate` | `0x75CC20` | `0x18075CC20` | Zone flag bitmask processing |
| `PostProcess` | `0x75D3B0` | `0x18075D3B0` | Objective tile promotion and score scaling |
| `IsValid` | `0x75D2C0` | `0x18075D2C0` | Not decompiled |

**Zone flag bitmask system (tested by `TileHasZoneFlag`):**

| Flag bit | Meaning | Effect on EvaluationContext |
|---|---|---|
| `0x01` | Zone membership | `ctx.thresholdAccumulator += 9999.0` (forces tile above any threshold) |
| `0x04` | Team-ownership | Same team: `+= 9999.0`; enemy team: standard weight |
| `0x08` | Repulsion | Negates the sign of the `0x10` influence accumulation |
| `0x10` | Proximity influence | `ctx.zoneInfluenceAccumulator += settings.zoneInfluenceWeight × dist × tile.influenceValue × sign` |
| `0x20` | Outer boundary | Loop continue condition |

**PostProcess:**

Two-pass. Pass 1: scan for zone tiles with flag 3 (objective zone); set `isObjectiveFlag`. Pass 2: for each scored tile where `ctx.thresholdAccumulator >= threshold`, find the matching objective zone tile. Apply `zoneMultiplier` (from unit status: `+0x8c == 1` → `settings.zoneScoreMultiplier_A`; else `settings.zoneScoreMultiplier_B`) to `ctx.accumulatedScore`. For non-matching tiles where `isObjectiveFlag` is set: add `fVar6` to `ctx.thresholdAccumulator`.

**Note on 9999.0:** Writing `ctx.thresholdAccumulator += 9999.0` is a threshold bypass, not a real score. Tiles in owned zones are unconditionally promoted above any possible computed threshold value.

---

### 6.5 DistanceToCurrentTile

**TypeDefIndex:** 3675 | **Base:** Criterion

Accumulates a `reachabilityScore` on the tile context proportional to how far the candidate tile is from the unit's current position, scaled by the zone distance modifier and penalised when the tile is out of effective reach.

**Fields:** None.

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Evaluate` | `0x760CF0` | `0x180760CF0` | Populates `ctx.reachabilityScore` |
| `IsValid` | `0x760EC0` | `0x180760EC0` | Not decompiled |

**Evaluate formula:**

```
effectiveRange = max(weaponStats.baseRange + weaponList.bonusRange, 1)
dist           = GetTileDistance(ctx.tileRef, unit.currentTile)
modScale       = GetTileZoneModifier(unit.opponentList).distanceScaleFactor    // TileModifier +0x20
penalty        = (moveSpeed / effectiveRange < dist) ? settings.outOfRangePenalty : 1.0
ctx.reachabilityScore += (float)dist × modScale × penalty
```

---

### 6.6 ExistingTileEffects

**TypeDefIndex:** 3676 | **Base:** Criterion

Scores tiles that carry active tile effects whose type matches the evaluating unit. Uses a zone effect immunity mask to skip effects the zone neutralises.

**Fields:** None.

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Evaluate` | `0x760FB0` | `0x180760FB0` | Effect immunity filtering and scoring |
| `IsValid` | `0x761370` | `0x180761370` | Not decompiled |

**Evaluate algorithm:**

```
Guard: HasTileEffects(ctx.tileRef)
immunityMask = GetTileZoneModifier(unit.opponentList).effectImmunityMask    // TileModifier +0x44
for each effect in ctx.tileRef.effectList:
    flags = effect.descriptor.flags
    if flags != 0 and (flags & immunityMask) == flags: skip    // fully immune
    if not IL2CPP type match vs registered subtypes: skip      // [UNCERTAIN: truncated]
    if not CheckEffectFlag(slot, 0x0e): skip
    if tile.hasTileEffect:                                     // tile +0xf2
        score = Criterion.Score(unit, effectTile, ctx, ctx, 1)
        ctx.accumulatedScore += settings.tileEffectMultiplier × score × settings.tileEffectScoreWeight
```

---

### 6.7 AvoidOpponents

**TypeDefIndex:** 3671 | **Base:** Criterion

Penalises tiles near opponent groups that **cannot** directly target the evaluating unit. Models indirect area-denial threat. Accumulates an `expf`-scaled penalty for tiles within 11 tiles of such groups.

**Fields:** None.

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Evaluate` | `0x75BE10` | `0x18075BE10` | Indirect threat accumulation |
| `IsValid` | `0x75C1B0` | `0x18075C1B0` | Not decompiled |

**Evaluate algorithm:**

```
fAccum = 0.0
for each opponent group in ScoringContext.singleton.avoidGroups:
    if group.teamId == unit.teamId: skip
    for each tile in group.tileList:
        if not TileTeamMatches(tile, unit.teamId): skip
        dist = GetTileDistance(ctx.tileRef, tile.position)
        if dist < 11:
            if group cannot target unit.team:    fAccum += expf(settings.avoidIndirectThreatWeight)
            else:                                fAccum += expf(settings.avoidDirectThreatWeight)
ctx.accumulatedScore += fAccum
```

---

### 6.8 FleeFromOpponents

**TypeDefIndex:** 3677 | **Base:** Criterion

Structurally identical to `AvoidOpponents` but accumulates only for groups that **can** target the unit, within a larger radius of 16 tiles. Together, `AvoidOpponents` and `FleeFromOpponents` form a complementary pair: Avoid handles area-denial from groups that can't reach the unit; Flee handles direct pressure from groups that can.

**Fields:** None.

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Evaluate` | `0x7613A0` | `0x1807613A0` | Direct threat accumulation |
| `IsValid` | `0x7616D0` | `0x1807616D0` | Not decompiled |

**Evaluate algorithm:**

```
fAccum = 0.0
for each opponent group in ScoringContext.singleton.avoidGroups:
    if group.teamId == unit.teamId: skip
    for each tile in group.tileList:
        if not TileTeamMatches(tile, unit.teamId): skip
        dist = GetTileDistance(ctx.tileRef, tile.position)
        if dist < 16:                             // ← 16, not 11
            if group CAN target unit.team:        // ← polarity inverted vs AvoidOpponents
                fAccum += expf(settings.fleeWeight)
ctx.accumulatedScore += fAccum
```

**Differences from AvoidOpponents:**

| Property | AvoidOpponents | FleeFromOpponents |
|---|---|---|
| Target groups | Cannot target unit | Can target unit |
| Radius | 11 tiles | 16 tiles |
| Weight | `avoidDirectThreatWeight` / `avoidIndirectThreatWeight` | `fleeWeight` |

---

### 6.9 Roam

**TypeDefIndex:** 3678 | **Base:** Criterion

Populates the candidate tile list for melee units with no active targets. Selects from a bounding box around the unit's current position, filtered for passable and reachable tiles. Roam is melee-only by structural enforcement, not configuration.

**Fields:** None.

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Collect` | `0x768300` | `0x180768300` | Bounding-box tile selection |
| `IsValid` | `0x768870` | `0x180768870` | Not decompiled |

**Collect algorithm:**

```
Guard: if unit has ranged weapon: return           // melee-only — structural enforcement
Guard: if unit.opponentList.behaviorConfig lacks roam flag 0x21: return

effectiveRange = max(weaponStats.baseRange + weaponList.bonusRange, 1)
roamRadius     = moveSpeed / effectiveRange
if roamRadius < 1: return

Build bounding box: [currentTile ± roamRadius] clamped to grid
for each tile in bounding box:
    if tile.isBlocked (bit 0) or tile.isOccupied (bit 2): skip
    if not IsCurrentTile(tile): skip
    if HasTileEffects(tile): skip
    if GetTileDistance(tile, currentTile) > roamRadius: skip
    add to candidates

shuffle candidates; pick first
if no existing score entry: create with thresholdValue = GetUtilityThreshold × 100
else: existing.thresholdValue += GetUtilityThreshold × 100
add to global shared tile list
```

---

### 6.10 WakeUp

**TypeDefIndex:** 3680 | **Base:** Criterion

Determines whether the unit should act to wake a sleeping ally. Unlike other criteria, `Collect` does not populate a tile list; instead it sets a `wakeupPending` flag (`movePool +0x51`) when a wakeable ally is found. The divergent `.ctor` slot (RVA `0x518FA0`) is a compiler artefact with a body identical to the base constructor.

**Fields:** None beyond those inherited from Criterion.

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `.ctor` | `0x518FA0` | `0x180518FA0` | Delegates to `Criterion_ctor`; no extra init |
| `Collect` | `0x787DD0` | `0x180787DD0` | Sets `wakeupPending` flag on move pool |
| `IsValid` | `0x7880E0` | `0x1807880E0` | Not decompiled |

**Collect algorithm:**

```
Phase 1 — Ally scan:
Navigate to unit.movePool.zoneData.allyTileList
for each ally in list:
    if ally.isAwake != 0: skip       // already awake
    if ally.wakeCondition == null: skip   // no wake condition
    if ally.wakePriority < 1: skip   // below priority threshold
    if ally == self: break
    if CanReachTarget(unit, ally):
        pool.wakeupPending = 0; return    // wake resolved

Phase 2 — Fallback opponent proximity:
for each opponent tile in unit.movePool.zoneData.opponentTileList:
    if TileTeamMatches(tile, zoneTeamId) and CanReachTarget(unit, tile):
        pool.wakeupPending = 0; return
```

---

### 6.11 ConsiderSurroundings

**TypeDefIndex:** 3672 | **Base:** Criterion

**Not analysed.** Role unknown. Has a `Collect` override (VA `0x18075C240`) and an `IsValid` override (VA `0x18075C5B0`). Deferred.

---

## 7. Supporting Infrastructure

### GetTileZoneModifier — 0x18071AE10

Returns the `TileModifier` struct for a tile's zone. Called by `GetUtilityThreshold`, `DistanceToCurrentTile.Evaluate`, `ExistingTileEffects.Evaluate`, and `ConsiderZones.Evaluate`.

```c
TileModifier GetTileZoneModifier(OpponentList* opponentList) {
    ZoneDescriptor* zone = opponentList->zoneDescriptor;   // opponentList +0x18
    if (zone != null) {
        ZoneData* zoneData = zone->vtable->GetStatusEffects(zone);   // vtable +0x398
        if (zoneData != null) {
            return *(TileModifier*)(zoneData + 0x310);
        }
    }
    NullReferenceException();
}
```

The `TileModifier` struct is located at `zoneData +0x310`. The managed class name of `zoneData` is not confirmed (see Open Questions).

### GetTileScoreComponents — 0x1806E0AC0

Populates a 6-slot `float[]` with raw scoring data for a tile.

| Slot | Content |
|---|---|
| `[0]` | Raw score, centiscale [0–100], clamped, floored to `scoreObj.minScoreFloor` |
| `[1]` | Tile base value |
| `[2]` | Derived score component |
| `[3]` | Movement effectiveness index |
| `[4]` | `isObjective` byte (1 if `tile +0xf3` set) |
| `[5]` | Distance offset component (only when distance params non-null) |

Early exit: if `tile.isObjectiveTile` (`+0xf3`), returns `[0]=100.0, [4]=1` immediately. All callers multiply `[0]` by `0.01` after the call.

### GetMoveRangeData — 0x1806DF4E0

Populates a `MoveRangeData` object with movement and attack metrics for a unit→tile pair.

| Output field | Offset | Type | Content |
|---|---|---|---|
| `attackRange` | `+0x10` | float | Attack effectiveness score |
| `ammoRange` | `+0x14` | float | Ammo-adjusted range score |
| `moveCostNorm` | `+0x18` | float | Normalised move cost, floored to `squadCount` |
| `moveCostToTile` | `+0x1c` | float | Raw move cost ratio |
| `maxReachability` | `+0x20` | float | Maximum reachability metric |
| `canAttackFromTile` | `+0x24` | bool | Can unit attack from this tile |
| `canFullyReach` | `+0x25` | bool | Can unit fully reach this tile within move budget |
| `tileScorePtr` | `+0x28` | ptr | Write-barriered pointer to `TileScore` object |

Calls `expf` on `(1.0 - tile.accuracyDecay × 0.01)` to compute a range step penalty multiplier.

### IsWithinRangeA — 0x1806E3C50

Four-gate range check used by `ThreatFromOpponents.Score (A)`:

1. `IsValidRangeType(tile, rangeType)` — range type validity gate.
2. If `tile.tileData.hasRangeConstraint == false`: return true.
3. If `tile.tileData.hasContextRequirement != 0`: `TileMatchesContext(scoreObj, unit)` must pass.
4. Both `IsInMeleeRange(tile, unit, scoreObj, rangeType)` AND `IsInAttackRange(tile, scoreObj, unit, rangeType)` must return true.

### IsWithinRangeB — 0x1806E33A0

AND-gate across all weapon slots on the tile (`tile +0x48`). Every slot's `vtable +0x1d8` (`CheckRangeCondition(unit, target)`) must return true. Returns `false` immediately on any failure.

### expf_approx (FUN_1804bad80) — 0x1804BAD80

Confirmed as a single-argument `expf`-equivalent growth curve. Implements a full IEEE 754 `powf` kernel but is always called with a single computed float argument. All formula annotations using `expf(x)` refer to calls to this function. The overwatch response curve, `AvoidOpponents`, `FleeFromOpponents`, and `GetMoveRangeData` all use it.

---

## 8. AIWeightsTemplate — Field Reference

Singleton accessed via `*(*(DAT_18394C3D0 + 0xb8) + 8)`. All fields confirmed from Ghidra decompilation.

| Offset | Type | Field | Used in |
|---|---|---|---|
| `+0x58` | float | `zoneInfluenceWeight` | `ConsiderZones.Evaluate` |
| `+0x5c` | float | `zoneInfluenceSecondaryWeight` | `ConsiderZones.Evaluate` (no-zone-list path) |
| `+0x60` | float | `zoneScoreMultiplier_A` | `ConsiderZones.PostProcess` (non-status-1 path) |
| `+0x64` | float | `zoneScoreMultiplier_B` | `ConsiderZones.PostProcess` (status-1 path) |
| `+0x68` | float | `zoneThresholdWeight_A` | `ConsiderZones.Evaluate` (matching tile) |
| `+0x6c` | float | `zoneThresholdWeight_B` | `ConsiderZones.Evaluate` (non-matching tile) |
| `+0x70` | float | `coverScoreWeight` | `CoverAgainstOpponents.Evaluate` final write |
| `+0x74` | float | `W_threat` | `ThreatFromOpponents.Evaluate` |
| `+0x78` | float | `tileEffectScoreWeight` | `ExistingTileEffects.Evaluate` |
| `+0x7c` | float | `tileEffectMultiplier` | `ExistingTileEffects.Evaluate` |
| `+0x7c` | float | `W_attack` | `Criterion.Score` Phase 8 (NOTE: same offset as above — needs verification) |
| `+0x80` | float | `W_ammo` | `Criterion.Score` Phase 8 |
| `+0x84` | float | `W_deploy` | `Criterion.Score` Phase 8 |
| `+0x88` | float | `W_sniper` | `Criterion.Score` Phase 8 |
| `+0x8c` | float | `coverMult_Full` | `CoverAgainstOpponents.Evaluate`, `ThreatFromOpponents.Score (A)` |
| `+0x90` | float | `coverMult_Partial` | `CoverAgainstOpponents.Evaluate`, `ThreatFromOpponents.Score (A)` |
| `+0x94` | float | `coverMult_Low` | `CoverAgainstOpponents.Evaluate`, `ThreatFromOpponents.Score (A)` |
| `+0x98` | float | `coverMult_Quarter` | `CoverAgainstOpponents.Evaluate`, `ThreatFromOpponents.Score (A)` |
| `+0x9c` | float | `coverMult_None` | `CoverAgainstOpponents.Evaluate`, `ThreatFromOpponents.Score (A)` |
| `+0xa0` | float | `flankingBonusMultiplier` | `ThreatFromOpponents.Score (A)` |
| `+0xa4` | float | `bestCoverBonusWeight` | `CoverAgainstOpponents.Evaluate` Phase 3 |
| `+0xac` | float | `weaponListDistanceThreshold` | `ThreatFromOpponents.Score (A)` flanking check |
| `+0xb0` | float | `avoidDirectThreatWeight` | `AvoidOpponents.Evaluate` (can-target path) |
| `+0xb4` | float | `avoidIndirectThreatWeight` | `AvoidOpponents.Evaluate` (cannot-target path) |
| `+0xb8` | float | `fleeWeight` | `FleeFromOpponents.Evaluate` |
| `+0xd4` | float | `occupiedDirectionPenalty` | `CoverAgainstOpponents.Evaluate` Phase 3 |
| `+0xd8` | float | `rangeScorePenalty` | `CoverAgainstOpponents.Evaluate` Phase 1 |
| `+0xdc` | float | `ammoScorePenalty` | `CoverAgainstOpponents.Evaluate` Phase 1 |
| `+0xe4` | float | `baseAttackWeight` | `Criterion.Score` Component A |
| `+0xe8` | float | `ammoPressureWeight` | `Criterion.Score` Component B |
| `+0xec` | float | `deployPositionWeight` | `Criterion.Score` Component C |
| `+0xf0` | float | `sniperAttackWeight` | `Criterion.Score` Component D |
| `+0x13c` | float | `baseThreshold` | `Criterion.GetUtilityThreshold` |
| `+0x158` | float | `outOfRangePenalty` | `DistanceToCurrentTile.Evaluate` |

> **Verification needed:** `+0x7c` appears in Stage 1 as both `W_attack` (from `Criterion.Score`) and `tileEffectMultiplier` (from Stage 2 `ExistingTileEffects`). These are likely different fields with the same offset label reused across investigations — confirm by checking the Stage 2 decompilation context more carefully.

---

## 9. EvaluationContext — Field Reference

`param_3` in all `Evaluate` functions. Referred to as `TileScoreRecord` in some analyses.

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x10` | ptr | `tileRef` | confirmed |
| `+0x20` | float | `reachabilityScore` | confirmed |
| `+0x24` | float | `zoneInfluenceAccumulator` | confirmed |
| `+0x28` | float | `accumulatedScore` | confirmed |
| `+0x30` | float | `thresholdAccumulator` | confirmed |
| `+0x60` | bool | `isObjectiveTile` | confirmed |

---

## 10. Auxiliary Object Field Reference

### Unit

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x20` | ptr | `movePool` (`unit[4]`) | confirmed |
| `+0x4c` | int | `teamIndex` | confirmed |
| `+0x54` | int | `moveRange` | confirmed |
| `+0x5b` | int | `ammoSlotCount` | confirmed |
| `+0x5c` | int | `currentAmmo` | confirmed |
| `+0x60` | int | `squadCount` | confirmed |
| `+0x70` | int | `teamId` (`unit[0xe]`) | confirmed |
| `+0xc8` | ptr | `opponentList` (`unit[0x19]`) | confirmed |
| `+0x15c` | bool | `isDeployed` | confirmed |
| `+0x140` | int | `wakePriority` (ally) | confirmed |
| `+0x162` | bool | `isAwake` (ally; 0=sleeping) | confirmed |
| `+0x48` | ptr | `wakeCondition` (ally) | confirmed |

### MovePool

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x10` | ptr | `zoneData` | confirmed |
| `+0x18` | int | `maxMovePoints` | confirmed |
| `+0x51` | bool | `wakeupPending` | confirmed |

### MoveRangeData

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x10` | float | `attackRange` | confirmed |
| `+0x14` | float | `ammoRange` | confirmed |
| `+0x18` | float | `moveCostNorm` | confirmed |
| `+0x1c` | float | `moveCostToTile` | confirmed |
| `+0x20` | float | `maxReachability` | confirmed |
| `+0x24` | bool | `canAttackFromTile` | confirmed |
| `+0x25` | bool | `canFullyReach` | confirmed |
| `+0x28` | ptr | `tileScorePtr` | confirmed |

### TileModifier (struct at `zoneData +0x310`)

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x14` | float | `minThresholdScale` | confirmed |
| `+0x18` | float | `thresholdMultiplier` | confirmed |
| `+0x20` | float | `distanceScaleFactor` | confirmed |
| `+0x44` | uint | `effectImmunityMask` | confirmed |

### ScoringContext (singleton via `DAT_183981F50 +0xb8`)

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x28` | ptr | `tileGrid` | confirmed |
| `+0x60` | int | `phase` (0=deploy, 1=std, 2=post) | confirmed |
| `+0xa8` | array | `avoidGroups` | confirmed |

### Tile

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x10` | ptr | `tileData` | inferred |
| `+0x18` | ptr | `zoneDescriptor` | confirmed |
| `+0x1c` | byte | `flags` (bit 0=blocked, bit 2=occupied) | confirmed |
| `+0x48` | List | `weaponSlots` (tile-side) | confirmed |
| `+0x68` | List | `effectList` | confirmed |
| `+0xf2` | bool | `hasTileEffect` | confirmed |
| `+0xf3` | bool | `isObjectiveTile` | confirmed |
| `+0x244` | int | `accuracyDecay` | confirmed |

### ZoneData (`movePool.zoneData`)

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x14` | int | `zoneTeamId` | confirmed |
| `+0x20` | List | `allyTileList` | confirmed |
| `+0x48` | List | `opponentTileList` | confirmed |

### WeaponStatsBlock (`weaponData +0x2b0`)

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x118` | int | `baseRange` | confirmed |

### WeaponList (returned by `vtable +0x3d8`)

| Offset | Type | Field | Status |
|---|---|---|---|
| `+0x3c` | int | `bonusRange` | confirmed |
| `+0xec` | uint | `rangedWeaponTypeFlag` (bit 0) | confirmed |

---

## 11. Ghidra Address Reference

### Fully Analysed

| Stage | VA | Method | Notes |
|---|---|---|---|
| 1 | `0x1804EB570` | `Criterion..ctor` | Complete |
| 1 | `0x18075EB00` | `CoverAgainstOpponents..cctor` | Complete |
| 1 | `0x180760070` | `Criterion.GetUtilityThreshold` | Complete |
| 1 | `0x18075DAD0` | `CoverAgainstOpponents.Evaluate` | Complete |
| 1 | `0x180760140` | `Criterion.Score` | Complete |
| 2 | `0x18054E040` | `ThreatFromOpponents.GetThreads` | Complete — returns 4 |
| 2 | `0x18076ACB0` | `ThreatFromOpponents.Evaluate` | Complete |
| 2 | `0x18076AF90` | `ThreatFromOpponents.Score (A)` | Complete |
| 2 | `0x18076B710` | `ThreatFromOpponents.Score (B)` | Complete |
| 2 | `0x1806E0AC0` | `GetTileScoreComponents` | Complete |
| 2 | `0x1806DF4E0` | `GetMoveRangeData` | Complete |
| 2 | `0x1804BAD80` | `expf_approx` | Complete — confirmed expf-equivalent |
| 2 | `0x18071AE10` | `GetTileZoneModifier` | Complete |
| 2 | `0x18075CC20` | `ConsiderZones.Evaluate` | Complete |
| 2 | `0x18075D3B0` | `ConsiderZones.PostProcess` | Complete |
| 2 | `0x18075BE10` | `AvoidOpponents.Evaluate` | Complete |
| 2 | `0x18071B670` | `Criterion.IsDeploymentPhase` | Complete |
| 2 | `0x180518FA0` | `WakeUp..ctor` | Complete — compiler artefact, no extra fields |
| 2 | `0x180760CF0` | `DistanceToCurrentTile.Evaluate` | Complete |
| 2 | `0x180760FB0` | `ExistingTileEffects.Evaluate` | Complete (partial truncation noted) |
| 2 | `0x1807613A0` | `FleeFromOpponents.Evaluate` | Complete |
| 2 | `0x180768300` | `Roam.Collect` | Complete |
| 2 | `0x180787DD0` | `WakeUp.Collect` | Complete |
| 2 | `0x1806E3C50` | `IsWithinRangeA` | Complete |
| 2 | `0x1806E33A0` | `IsWithinRangeB` | Complete |

### Not Yet Analysed

| VA | Method | Notes |
|---|---|---|
| `0x18075C240` | `ConsiderSurroundings.Collect` | Deferred |
| `0x18075C5B0` | `ConsiderSurroundings.IsValid` | Deferred |
| `0x18075C630` | `ConsiderZones.Collect` | Deferred |
| `0x1806E3750` | `IsInMeleeRange` | Range gate sub-call; semantics partially known |
| `0x1806E60A0` | `IsInAttackRange` | Range gate sub-call |
| `0x1806E3D50` | `IsValidRangeType` | Trivial range type gate |
| All `IsValid` impls | 10 classes | Deferred — interface documented, predictable pattern |

---

## 12. Key Inferences and Design Notes

**The four-component decomposition is intentional and independently tunable.** `Criterion.Score` cleanly separates attack opportunity (W_attack), supply pressure (W_ammo), positional advancement (W_deploy), and precision fire support (W_sniper). Each weight in `AIWeightsTemplate` is independently configurable, making this a purely data-driven utility AI. There is no learned component.

**ThreatFromOpponents is the dominant criterion by computation budget.** It requests 4 threads while all other criteria are single-threaded. Its spatial scan with distance falloff and directional multipliers is the most complex scoring logic in the namespace.

**The phase system gates major behaviour differences.** `ScoringContext.singleton.phase` takes values 0 (deployment), 1 (standard), 2 (post-deployment). Cover multipliers, deployment bonuses, and flee weights all branch on this value. The AI evaluates tile desirability very differently depending on the game phase.

**`expf` is used as a score transform throughout, not linear multiplication.** `AvoidOpponents`, `FleeFromOpponents`, and `GetMoveRangeData` all call `expf_approx` on weight constants. This means the weights in `AIWeightsTemplate` at `+0xb0`, `+0xb4`, `+0xb8` are exponent inputs. Small changes to these values have exponential effects on AI behaviour.

**Zone threshold promotion via 9999.0 is a bypass, not a score.** `ConsiderZones.Evaluate` writes `ctx.thresholdAccumulator += 9999.0` to guarantee a tile passes the threshold gate unconditionally. Tiles in owned strategic zones are always promoted above the threshold regardless of their raw scoring.

**Two distinct "objective tile" flags exist at different levels.** `tile +0xf3` is a tile-side flag set in tile data, read by `GetTileScoreComponents` for an early exit to `[0]=100.0`. `ctx +0x60` is a per-evaluation context flag written by `ThreatFromOpponents.Score (B)` via `CanReachTarget`. These are not the same and are written by different systems for different purposes.

**Roam is melee-only by structural enforcement.** The first guard in `Roam.Collect` hard-exits for ranged units. This is not a configuration option.

**WakeUp writes a flag, not tiles.** It sets `movePool.wakeupPending = 0` rather than populating a candidate tile list. This is structurally different from every other `Collect` override and suggests `WakeUp` integrates with a separate waking-behaviour dispatch system, not the tile-scoring pipeline directly.

**`AvoidOpponents` and `FleeFromOpponents` are a complementary pair.** Same iteration structure, opposite polarity on the `CanTarget` check, different radius (11 vs 16), different weight constant. Together they model area denial (can't reach unit) and direct threat pressure (can reach unit).

**The 4× health bonus in `Criterion.Score` creates a strong incentive for healthy units to hold optimal positions.** A unit at maximum range with health > 95% scores 8× the base attack component. Damaged units receive no such bonus and are implicitly pushed toward conservative or cover-oriented positions.

**The centiscale convention (0–100 integers → 0.01 multiplier) serves designer ergonomics.** Raw scores from `GetTileScoreComponents` are stored as 0–100 integers; all callers multiply by `0.01` to convert to [0.0, 1.0]. Designers presumably tune and read scores in 0–100 space while the runtime operates in float space.

---

## 13. Open Questions

1. **What are the actual runtime values of `COVER_PENALTIES[4]`?**
   The static array is allocated in `.cctor` but the literal values are not written in the decompiled output. Memory dump `CoverAgainstOpponents.COVER_PENALTIES` at runtime, or view the `.cctor` assembly listing for four float push instructions after the array allocation.

2. **Offset conflict at `AIWeightsTemplate +0x7c`.**
   Stage 1 assigns `W_attack` here; Stage 2 assigns `tileEffectMultiplier`. These may be a labelling error or a genuine overlap. Verify by re-reading the raw decompilation for `ExistingTileEffects.Evaluate` and confirming which offset is `+0x7c` and which is `+0x78`.

3. **What is the managed class name of `zoneData` (returned by `vtable +0x398` on `ZoneDescriptor`)?**
   Search `dump.cs` for a class with a member struct at offset 0x310, or run `extract_rvas.py` on the type referenced by the vtable slot.

4. **What does `ConsiderSurroundings.Evaluate` do?**
   The one `Evaluate` override not yet analysed. Extract RVAs and request Ghidra output for VA `0x18075C240`.

5. **What does `ConsiderZones.Collect` do?**
   VA `0x18075C630`. Batch with `ConsiderSurroundings` analysis.

6. **Full `AIWeightsTemplate` field layout for offsets `0x100`–`0x140`.**
   Run `extract_rvas.py` on `AIWeightsTemplate`.

7. **Exact semantics of `IsInMeleeRange` (0x1806E3750) and `IsInAttackRange` (0x1806E60A0).**
   Sub-calls of `IsWithinRangeA`. Decompile if range gate detail is needed for a downstream investigation.

8. **Behaviour selection layer consuming `Score` output.**
   Outside this namespace. Requires operator acknowledgement before investigation.
