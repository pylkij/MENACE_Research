# Menace — Tactical AI System: Unified Investigation Report

**Game:** Menace  
**Platform:** Windows x64, Unity IL2CPP  
**Binary:** GameAssembly.dll  
**Image base:** `0x180000000` (VA = RVA + 0x180000000)  
**Source material:** Il2CppDumper `dump.cs` (~885,000 lines), Ghidra decompilation, `extract_rvas.py` class dumps  
**Investigation status:** Complete — 77+ VAs analysed across all investigations. Three namespace investigations merged.

---

## Table of Contents

1. How to Read This Report
2. System Architecture at a Glance
3. The Complete Decision Pipeline — End to End
4. Layer 1 — Tile Scoring (Position Evaluation)
   - 4.1 The Agent and its Evaluation Loop
   - 4.2 The Criterion System
   - 4.3 The Eleven Criterions
   - 4.4 PostProcessTileScores — Normalisation Pipeline
   - 4.5 The Composite Tile Score Formula
5. Layer 2 — Behaviour Scoring (Action Selection)
   - 5.1 The Behavior Base Class
   - 5.2 Move Behavior
   - 5.3 Deploy Behavior
   - 5.4 SkillBehavior — Shared Targeting Formula
   - 5.5 Attack and Assist
   - 5.6 Concrete Skill Behaviors
6. Layer 3 — Agent Priority (Turn Ordering)
7. Configuration — AIWeightsTemplate
8. Class Reference
9. Key Inferences and Design Notes
10. Open Questions
11. Scope Boundaries

---

## 1. How to Read This Report

This report is the collation of three separate investigations into the tactical AI decision-making system of Menace. The three source investigations each focused on one architectural layer:

- **TacticalStateSettings investigation** — established the top-level `Agent` evaluation loop, the `TileScore` data model, the normalisation pipeline, and `AIWeightsTemplate` as the root configuration asset.
- **Criterions investigation** — reverse-engineered all 11 `Criterion` subclasses that determine how individual tiles receive safety and utility scores.
- **Behaviors investigation** — reverse-engineered all `Behavior` subclasses: `Move`, `Deploy`, `Attack`, `Assist`, and 9 concrete skill behaviors. These consume tile scores and produce the final integer action score that determines what the AI actually does each turn.

The three layers feed each other in strict order: Criterions write tile scores → Agent normalises them → Behaviors read them to score possible actions → Agent ranks behaviors and executes the winner. The report below presents them in that order, from lowest level to highest, so a reader can follow the full chain without forward references.

---

## 2. System Architecture at a Glance

```
┌───────────────────────────────────────────────────────────────────────┐
│  AIWeightsTemplate (ScriptableObject)                                 │
│  Designer-authored data asset. Every weight, exponent, scale,         │
│  and threshold in the entire AI is a field on this object.            │
│  Accessed globally via DebugVisualization.WEIGHTS (static +0x08).     │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ supplies weights to all layers
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — TILE SCORING                                               │
│  11 Criterion subclasses evaluate every reachable tile.               │
│  Each criterion writes into EvaluationContext fields                  │
│  (accumulatedScore, reachabilityScore, zoneInfluenceAccumulator, ...) │
│  Agent.PostProcessTileScores() then applies POW/Scale curves,         │
│  negates SafetyScore, and propagates neighbor bonuses.                │
│  Result: every tile in Agent.m_Tiles has a TileScore record           │
│  with SafetyScore, UtilityScore, DistanceScore, DistanceToCurrentTile.│
└──────────────────────────────┬────────────────────────────────────────┘
                               │ TileScore per tile
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — BEHAVIOUR SCORING                                          │
│  Each Behavior subclass reads the TileScore dictionary and            │
│  its own skill/weapon data to produce a single integer m_Score.       │
│  Move reads tile movementScores. Attack/Assist score shot             │
│  candidates with hit probability, kill potential, co-fire, and        │
│  a movement cost integration step. Deploy uses a range + spacing      │
│  penalty model. Concrete skill behaviors (InflictDamage, Buff, etc.)  │
│  apply their own GetTargetValue override on top of the shared         │
│  SkillBehavior targeting formula.                                     │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ m_Score per Behavior
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — AGENT PRIORITY                                             │
│  Agent.PickBehavior() sorts all behaviors by m_Score.                 │
│  Agent.GetScoreMultForPickingThisAgent() applies a per-agent          │
│  priority multiplier: threat level and opportunity level determine     │
│  whose turn it is most urgent to take.                                │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. The Complete Decision Pipeline — End to End

One complete turn for an AI-controlled unit proceeds through the following steps in order. Each step is detailed in subsequent sections.

```
TURN START
│
├─ 1. Agent.Evaluate() called
│       Reset: m_Score=0, m_ActiveBehavior=null, m_State=None
│       Copy m_Tiles → m_TilesToBeUsed (double-buffer swap)
│       Liveness checks: actor must be active, alive, not deactivating
│       Budget check: m_Iterations < MAX_ITERATIONS(16), or IsStandalone
│       Sleep check: m_SleepUntil vs faction clock
│       Motion yield: skip if actor still in motion
│
├─ 2. Criterion Pass 1 — Tile scoring
│       For each Criterion C in Agent.S_CRITERIONS:
│           if C.IsValid(unit, ctx): continue
│           C.Collect(unit, ctx)        ← populates candidate list (Roam, WakeUp only)
│           C.Evaluate(unit, ctx)       ← writes raw scores into EvaluationContext
│                                          per candidate tile
│       Threading: if tileCount > tilesPerThread × 2, run multi-threaded
│                  Vehicles halve their tilesPerThread budget
│                  ThreatFromOpponents always requests 4 threads
│
├─ 3. Agent.PostProcessTileScores()
│       Per tile, for each TileScore ts:
│           ts.UtilityScore += ts.UtilityByAttacksScore
│           ts.UtilityScore  = powf(ts.UtilityScore, UtilityPOW)
│           ts.UtilityScore  = powf(unitUtilityMult × ts.UtilityScore × UtilityScale,
│                                   UtilityPostPOW) × UtilityPostScale
│           ts.SafetyScore   = powf(ts.SafetyScore, SafetyPOW)
│           ts.SafetyScore   = powf(unitSafetyMult × ts.SafetyScore × SafetyScale,
│                                   SafetyPostPOW) × SafetyPostScale
│           ts.SafetyScore   = −ts.SafetyScore × DistanceScale   ← NEGATED
│       Neighbor propagation (if m_Flags bit 0 set):
│           For each tile, check 8 neighbors
│           HighestSafetyNeighbor  → neighbor with ≥2× safety boost
│           HighestUtilityNeighbor → neighbor with ≥2× utility boost
│
├─ 4. Criterion Pass 2 — PostEvaluate
│       For each Criterion C in S_CRITERIONS:
│           C.PostProcess(unit, m_Tiles)
│       Runs on already-normalised scores.
│       ConsiderZones.PostProcess promotes objective zone tiles.
│       UtilityByAttacksScoreCandidate → UtilityByAttacksScore commit happens here.
│
├─ 5. Behavior.Collect() for each registered Behavior
│       Deployment gate: if !m_IsUsedForDeploymentPhase AND roundCount==0 → skip
│       OnCollect(actor, agentTileDict) — subclass populates shot candidates / tile list
│
├─ 6. Behavior.Evaluate() for each registered Behavior
│       Deployment gate (same)
│       rawScore = OnEvaluate(actor)    ← subclass scoring formula
│       m_Score  = clamp(rawScore, 0, 21474)
│       if GetOrder() ≠ 99999 AND 0 < m_Score < 5: m_Score = 5
│
├─ 7. Agent.PickBehavior()
│       SortBehaviors() using TileScore.CompareScores()
│       Applies GetUtilityThreshold() filter per tile
│       Resolves ties via GetOrder()
│       Checks m_DontActuallyExecute before dispatching
│       m_ActiveBehavior = winner
│
├─ 8. Agent.GetScoreMultForPickingThisAgent()
│       fMult = threatLevel × opportunityLevel  (both exponent-scaled from AIWeightsTemplate)
│       m_Score = max(1, (int)(fMult × activeBehavior.baseScore))
│
└─ 9. Agent.Execute()
        OnExecute(actor) — state machine, returns bool (true=done)
        SkillBehavior stages: Rotate → Deploy → Setup → Fire
        Move stages: UseSkillBefore → StartMove → UseSkillAfter → ContainerExit
```

---

## 4. Layer 1 — Tile Scoring (Position Evaluation)

### 4.1 The Agent and its Evaluation Loop

**Class:** `Agent`  
**Namespace:** `Menace.Tactical.AI` | **TypeDefIndex:** 3616

The `Agent` is the AI brain for a single unit. It owns the tile dictionary (`m_Tiles: Dictionary<Tile, TileScore>`), drives criterion evaluation, and manages all registered `Behavior` instances. It is also the class that determines whose turn is most urgent via `GetScoreMultForPickingThisAgent`.

**Key fields:**

| Offset | Type | Name | Notes |
|---|---|---|---|
| `+0x18` | `int` | `m_State` | 0=None, 1=Evaluating, 2=Scored, 3=Done |
| `+0x20` | `float` | `m_SleepUntil` | Agent sleeps until faction clock exceeds this |
| `+0x28` | `Actor*` | `m_Actor` | Controlled unit |
| `+0x38` | `int` | `m_Flags` | Bit 0: enable neighbor propagation. Other bits: unknown |
| `+0x40` | `Behavior*` | `m_ActiveBehavior` | Selected this evaluation cycle |
| `+0x50` | `int` | `m_Score` | Agent-level priority score (Layer 3 output) |
| `+0x58` | `int` | `m_Iterations` | Evaluation call count. Capped at `MAX_ITERATIONS=16`. |
| `+0x60` | `Dict<Tile, TileScore>*` | `m_Tiles` | Per-tile score records (double-buffered) |
| `+0x80` | `List<Behavior>*` | `m_Behaviors` | All registered behaviors for this unit |
| `+0xA8` | `bool` | `m_IsStandalone` | When true, iteration cap bypassed (editor/test mode) |

**Key methods:**

| Method | VA | Notes |
|---|---|---|
| `Evaluate()` | `0x180719860` | Full evaluation loop. Entry point for the turn. |
| `PostProcessTileScores()` | `0x18071C450` | POW/Scale normalisation pipeline. |
| `PickBehavior()` | `0x18071BD20` | Sorts and selects the winning behavior. |
| `GetThreatLevel()` | `0x18071B240` | Accumulates threat from all tiles. |
| `GetOpportunityLevel()` | `0x18071ABC0` | Attack ceiling score. |
| `GetScoreMultForPickingThisAgent()` | `0x18071AE50` | Agent priority multiplier (Layer 3). |

The static list `Agent.S_CRITERIONS` (initialised by `.cctor` at `0x18071CEC0`) contains all 11 `Criterion` instances that are evaluated in Passes 1 and 2. Every `Agent` evaluates the same criterion list, but criteria gate themselves using `IsValid` and `IsDeploymentPhase` to handle unit-specific and phase-specific behaviour.

---

### 4.2 The Criterion System

The `Criterion` class hierarchy defines how tiles receive raw scores. Each concrete subclass overrides some or all of: `IsValid`, `Collect`, `Evaluate`, `PostProcess`, `Score`, and `GetThreads`.

**Class:** `Criterion`  
**TypeDefIndex:** 3670 | **No instance fields.**

The two shared methods that all subclasses inherit:

**`GetUtilityThreshold`:**
```
modifier  = GetTileZoneModifier(tile.zoneDescriptor)
threshold = max(settings.baseThreshold, settings.baseThreshold × modifier.minThresholdScale)
return threshold × modifier.thresholdMultiplier
```

**`Score` — the master tile scoring formula:**
```
rawScore   = GetTileScoreComponents(tile, ...)[0] × 0.01      // centiscale → float
moveData   = GetMoveRangeData(tile, unit)
rangeCost  = floor(min(rawScore × moveData.moveCostToTile, unit.movePool.maxMoves − 1))
adjScore   = GetReachabilityAdjustedScore(..., rangeCost) × 0.01

// Component A — Attack weight
rangeRatio = min((rawScore × moveData.attackRange) / unit.moveRange, 2.0)
fAtk       = settings.baseAttackWeight × rangeRatio
if rawScore × moveData.moveCostToTile ≥ unit.movePool.maxMoves:
    fAtk ×= 2.0
    if GetHealthRatio(unit) > 0.95: fAtk ×= 4.0    // near-full-health, max-range = 8× base
elif moveData.canAttackFromTile and rawScore > 0:
    fAtk ×= 1.1
// + overwatch/suppression multipliers from expf-scaled response curve table

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
        fDeploy ×= (GetMovementDepth(unit) × 0.25 + 1.5)
    if combined ≥ 0.67: fDeploy ×= 3.0

// Component D — Sniper bonus (only if unit has sniper-class weapon)
if HasSniperWeapon(unit):
    fSniper   = GetAttackCountFromTile(tile) × rangeSteps × settings.sniperAttackWeight × rawScore
    if not tile.hasEnemy:
        fSniper ×= (GetMovementDepth(unit) × 0.25 + 1.5)
    fSniper ×= max(GetHealthRatio(unit), 0.25)

// Final combination — movement-effectiveness multiplier gates the whole score
movEffIdx  = GetMovementEffectivenessIndex(tile, unit)
movEff     = expf(movEffTable[movEffIdx] + 1.0)
Score      = movEff × (settings.W_attack × fAtk
                     + settings.W_ammo   × fAmmo
                     + settings.W_deploy × fDeploy
                     + settings.W_sniper × fSniper)
```

**Design note on the movement-effectiveness multiplier:** `movEff` is computed from a table using `expf`, which means a tile the unit cannot efficiently reach receives an exponentially discounted score — not just a flat penalty. A tile that scores well on all four components but is two turns away may score lower than a mediocre adjacent tile. The AI always prefers reachable good tiles over unreachable great ones.

---

### 4.3 The Eleven Criterions

The 11 concrete `Criterion` subclasses are evaluated in series during Pass 1. Each writes into `EvaluationContext` fields. All share the same `Criterion.Score` formula as their terminal step, after their `Evaluate` override has populated the context.

**`EvaluationContext` fields written across all `Evaluate` overrides:**

| Offset | Field | Written by |
|---|---|---|
| `+0x20` | `reachabilityScore` | `DistanceToCurrentTile.Evaluate` |
| `+0x24` | `zoneInfluenceAccumulator` | `ConsiderZones.Evaluate` |
| `+0x28` | `accumulatedScore` | Most Evaluate overrides |
| `+0x30` | `thresholdAccumulator` | `CoverAgainstOpponents`, `ConsiderZones`, `Roam.Collect` |
| `+0x60` | `isObjectiveTile` (bool) | `ThreatFromOpponents.Score (B)` |

#### CoverAgainstOpponents (TDI 3674)

Evaluates how much cover a candidate tile provides against all known opponents. Also penalises tiles occupied by enemies in range.

```
// Guard
if unit.opponentList is empty: return

// Phase 1 — Occupied tile penalties
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
    penalty    = COVER_PENALTIES[dirIdx]                // static float[4], values unknown
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
if total ≠ 0 and not deployment-locked:
    if not IsChokePoint(tile): total += 10.0
if unit has active debuff and tile is not objective: total ×= 0.9
ctx.accumulatedScore = total × settings.coverScoreWeight + ctx.accumulatedScore
```

#### ThreatFromOpponents (TDI 3679)

The most computationally expensive criterion. Requests 4 worker threads. Scores tiles by the threat posed by enemy units, using a spatial scan with directional and distance multipliers.

```
// Evaluate — two phases
Guard: enemy count > 1

Phase 1 — Ally occupant contribution (tile occupied by ally, tile ≠ current):
    contribution = (2.0 - allyHealthRatio) × W_threat × (maxMoves / weaponCount) × Score_B(ally)
    ctx.accumulatedScore += contribution

Phase 2 — Self threat (always):
    ctx.accumulatedScore += Score_B(self) × W_threat
```

`Score (B)` — spatial scan around each opponent:
```
For each opponent in opponent list:
    ctx.isObjectiveTile = CanReachTarget(unit, opponentTile)    // side effect
    halfWidth = weaponRange / (squadCapacity + 1) / 2
    For each tile in [opponent ± halfWidth] bounding box:
        score = Score_A(tile, opponent)
        if tile ≠ current:
            flanking and path clear:          score ×= 1.2
            moving away from enemy:           score ×= 0.9
            moving toward enemy:              score ×= 1.2
            leaving choke point, flank slots > 2: score ×= 0.8
            long-range weapon flag:           score ×= 1.2
            score ×= (1.0 - dist / (halfWidth × 3.0))   // distance falloff
        keep best score
```

#### ConsiderZones (TDI 3673)

Scores tiles based on strategic zone membership. Uses a bitmask system to unconditionally promote tiles in owned zones above the threshold gate.

```
Zone flag bitmask processed per tile:
  Bit 0x01 — Zone membership:      ctx.thresholdAccumulator += 9999.0 (forces above threshold)
  Bit 0x04 — Team-ownership:       same team → += 9999.0; enemy team → standard weight
  Bit 0x08 — Repulsion:            negates the 0x10 influence accumulation sign
  Bit 0x10 — Proximity influence:  ctx.zoneInfluenceAccumulator += weight × dist × influenceValue × sign
  Bit 0x20 — Outer boundary:       loop continue condition

PostProcess (Pass 2):
  Pass 1: scan for objective zone tiles (flag 3). Set isObjectiveFlag.
  Pass 2: for each scored tile where thresholdAccumulator ≥ threshold,
          apply zoneMultiplier to ctx.accumulatedScore.
          unit status +0x8c == 1 → zoneScoreMultiplier_A; else → zoneScoreMultiplier_B
```

The `9999.0` write is a threshold bypass: any tile in an owned strategic zone always passes the threshold gate, regardless of raw score.

#### DistanceToCurrentTile (TDI 3675)

Accumulates a reachability score proportional to distance from the unit's current position, modulated by zone distance scale and an out-of-range penalty.

```
effectiveRange = max(weaponStats.baseRange + weaponList.bonusRange, 1)
dist           = GetTileDistance(ctx.tileRef, unit.currentTile)
modScale       = GetTileZoneModifier(unit.opponentList).distanceScaleFactor    // TileModifier +0x20
penalty        = (moveSpeed / effectiveRange < dist) ? settings.outOfRangePenalty : 1.0
ctx.reachabilityScore += (float)dist × modScale × penalty
```

#### ExistingTileEffects (TDI 3676)

Scores tiles that carry active tile effects whose type matches the evaluating unit. Uses a zone effect immunity mask to skip effects the zone neutralises.

The evaluate guard checks `hasTileEffect` at `tile +0xf2`. If the flag is clear, the criterion exits immediately. Otherwise it iterates the tile's effect list, skips effects neutralised by the zone immunity mask, and accumulates a score weighted by `settings.ThreatFromTileEffects` (`AIWeightsTemplate +0x78`).

#### AvoidOpponents (TDI 3671)

Penalises tiles near opponent groups that **cannot** directly target the unit (indirect threat / area denial). Same iteration structure as `FleeFromOpponents` but uses the opposite polarity on the `CanTarget` check. Radius: 11 tiles. Weight constant: `AIWeightsTemplate +0xb0`, applied via `expf` (exponential scaling).

#### FleeFromOpponents (TDI 3677)

Penalises tiles near opponent groups that **can** directly target the unit. Mirror of `AvoidOpponents` with larger radius (16 tiles) and different weight constant (`AIWeightsTemplate +0xb4`). Both criteria model threat independently: `AvoidOpponents` handles area denial pressure; `FleeFromOpponents` handles direct fire pressure.

#### Roam (TDI 3678)

Melee-only. Populates the candidate tile list for melee units with no active targets. Uses a bounding-box scan around the unit's current position. The first guard hard-exits for any ranged unit — this is structural, not configurable. Also writes `ctx.thresholdAccumulator += GetUtilityThreshold(unit, tile)` to anchor the threshold baseline.

#### WakeUp (TDI 3680)

Structurally unlike all other criterions. Rather than populating a tile list, `WakeUp.Collect` checks if there is a sleeping ally within range and sets `movePool.wakeupPending = 0` as a flag. This integrates with a separate waking-behaviour dispatch system — `WakeUp` does not produce tile scores directly.

#### AvoidOpponents and FleeFromOpponents — complementary pair

Together, these two criteria cover the full threat landscape: `AvoidOpponents` penalises tiles near enemies that can't reach the unit (blocking approach routes), while `FleeFromOpponents` penalises tiles near enemies that can reach the unit (direct fire threat). The pair is designed to push units toward positions that are neither a direct target nor within indirect-fire denial zones.

#### ConsiderSurroundings (TDI 3672)

**Not analysed.** Role unknown. `Evaluate` at VA `0x18075C240` was not decompiled. See Open Questions.

---

### 4.4 PostProcessTileScores — Normalisation Pipeline

After all 11 criteria have written raw scores, `Agent.PostProcessTileScores()` (`0x18071C450`) normalises them. This is the step that transforms criterion output into the final `TileScore` values used by behaviors.

```
Per tile ts:
    // Utility normalisation
    ts.UtilityScore += ts.UtilityByAttacksScore
    ts.UtilityScore  = powf(ts.UtilityScore, UtilityPOW)
    ts.UtilityScore  = powf(unitUtilityMult × ts.UtilityScore × UtilityScale, UtilityPostPOW)
    ts.UtilityScore ×= UtilityPostScale

    // Safety normalisation
    ts.SafetyScore   = powf(ts.SafetyScore, SafetyPOW)
    ts.SafetyScore   = powf(unitSafetyMult × ts.SafetyScore × SafetyScale, SafetyPostPOW)
    ts.SafetyScore  ×= SafetyPostScale
    ts.SafetyScore   = −ts.SafetyScore × DistanceScale    ← NEGATED HERE

    // Per-unit role multipliers (override global weights)
    unitUtilityMult = role +0x14
    unitSafetyMult  = role +0x1C
```

**Two-pass design rationale:** Pass 1 writes raw scores. `PostProcessTileScores` normalises them. Pass 2 (`PostEvaluate` / `PostProcess`) can then make relative comparisons across tiles that were impossible with raw data. `ConsiderZones.PostProcess` uses this to promote tiles to objective status only after the full score landscape is visible.

**SafetyScore negation:** SafetyScore is stored as a negative value after this pipeline. In the composite formula `SafetyScore + UtilityScore`, a heavily threatened tile has a large negative SafetyScore that reduces the total. The AI seeks tiles where this penalty is minimised — i.e., the safest positions. The naming `SafetyScore` reflects the AI's goal (seek safety), not the stored value's sign.

**Neighbor propagation** (when `m_Flags bit 0` is set): Each tile checks all 8 neighbors. A neighbor with at least 2× the tile's safety score promotes the tile's `HighestSafetyNeighbor`. Similarly for utility. This propagates strategic value into adjacent tiles — tiles next to excellent cover inherit some of that cover's value.

---

### 4.5 The Composite Tile Score Formula

After normalisation, `TileScore.GetScore()` (`0x180740F20`) computes the final float used for comparison:

```
GetScore(ts) = (ts.SafetyScore + ts.UtilityScore)
             - (ts.DistanceScore + ts.DistanceToCurrentTile) × WEIGHTS.DistanceScale
```

Variants:
- `GetScaledScore()` — uses `WEIGHTS.DistancePickScale` instead of `DistanceScale`
- `GetScoreWithoutDistance()` — returns `SafetyScore + UtilityScore` only; used for terminal destination (UltimateTile) evaluation where AP cost is irrelevant

`TileScore.CompareScores()` is a descending comparator on `GetScore()`, used by `PickBehavior` to sort tiles.

---

## 5. Layer 2 — Behaviour Scoring (Action Selection)

### 5.1 The Behavior Base Class

**Class:** `Behavior`  
**Namespace:** `Menace.Tactical.AI` | **TypeDefIndex:** 3623

The abstract root of all tactical actions. It owns the lifecycle contract, score storage, deployment phase gate, utility threshold, and strategy-modulated weight access.

**Fields:**

| Offset | Type | Name | Notes |
|---|---|---|---|
| `+0x10` | `Agent*` | `m_Agent` | Owning AI agent |
| `+0x18` | `int` | `m_Score` | Utility score from last Evaluate. Range: [0, 21474], floor at 5. |
| `+0x1C` | `bool` | `m_IsFirstEvaluated` | True: evaluated since last execution |
| `+0x1D` | `bool` | `m_IsFirstExecuted` | Same write as m_IsFirstEvaluated |
| `+0x1E` | `bool` | `m_IsUsedForDeploymentPhase` | When false, gated out during roundCount==0 |

**Score pipeline per behavior:**
```
rawScore     = OnEvaluate(actor)          // subclass-defined; returns int
clampedScore = clamp(rawScore, 0, 21474)
if GetOrder() ≠ 99999 AND 0 < clampedScore < 5:
    clampedScore = 5                      // minimum viable floor
m_Score = clampedScore
```

**Utility threshold formula** (from `GetUtilityThreshold`):
```
base      = AIWeightsTemplate.UtilityThreshold    (+0x13C)
multA     = StrategyData.modifiers.thresholdMultA  (+0x14) — one-directional raise only
multB     = StrategyData.modifiers.thresholdMultB  (+0x18) — bidirectional

scaled    = max(base, base × multA)
threshold = scaled × multB
```
`multA` can only raise the threshold (aggressive strategies). `multB` is unconstrained (can raise or lower). Defensive strategies raise it; aggressive strategies lower it, causing the AI to take actions it would normally skip.

---

### 5.2 Move Behavior

**Class:** `Move`  
**TypeDefIndex:** 3650 | **Base:** `Behavior` (not SkillBehavior — Move does not activate a Skill)

`Move` uses the tile score model built by the Criterion layer. It reads pre-scored tiles from the agent tile dictionary and selects the best destination.

**Key fields:**

| Offset | Name | Notes |
|---|---|---|
| `+0x020` | `m_IsMovementDone` | Early-out guard |
| `+0x021` | `m_HasMovedThisTurn` | Affects weight scaling |
| `+0x022` | `m_HasDelayedMovementThisTurn` | Set when marginal move penalty (×0.25) applied |
| `+0x024` | `m_IsAllowedToPeekInAndOutOfCover` | Enables ×4.0 peek bonus at low AP |
| `+0x028` | `m_TargetTile` | Chosen destination (TileScore) |
| `+0x030` | `m_ReservedTile` | Tile whose entity is currently claimed |

**Move tile score formula:**
```
TileScore.movementScore =
    AIWeightsTemplate.DistanceToCurrentTile (+0x54)
    × (apCost / 20.0)
    × BehaviorWeights.movementWeight (+0x20)

fWeight = BehaviorWeights.weightScale
          × AIWeightsTemplate.MoveScoreMult (+0x12C)
          × (currentAP / maxAP)          // if not yet moved this turn
          × 0.9                           // if weapon not yet set up

FinalScore = (int)(fWeight × AIWeightsTemplate.MoveBaseScore (+0x128))
```

**Modifier stack:**
- `m_ReservedTile.movementScore` is halved (less attractive to move there) but `utilityScore` is doubled (good to stay near it). This asymmetry makes reserved tiles serve as staging areas rather than destinations.
- **Peek bonus:** When `m_IsAllowedToPeekInAndOutOfCover` is set and AP is low, the movement score is multiplied by `4.0`. Extreme incentive to peek-fire from cover.
- **Marginal move penalty:** When the best destination is only marginally better than the current tile, `fWeight` is multiplied by `0.25` and `m_HasDelayedMovementThisTurn` is set. Prevents jitter (oscillating between nearly-equal tiles each turn).

**Forced vs voluntary movement:** Forced movement is triggered when: (1) actor is prone (stance == 1), (2) both `BehaviorConfig2.configFlagA` and `configFlagB` are set, or (3) `HasUtility()` returns false (no tile meets the utility threshold). When forced, the minimum-improvement filter is bypassed.

**`OnExecute` state machine:**
- Stage 0: Re-routes entity claims
- Stage 1: Fires `m_UseSkillBefore` skills one per tick
- Stage 2: Waits for timer, calls `Actor.StartMove(targetTile, flags)` with bitmask encoding goal-entity / can-deploy / is-peek
- Stage 3: Fires `m_UseSkillAfter` skills
- Stage 4: Handles container exit; fires `Skill.Activate`. If `m_PreviousContainerActor` is set, broadcasts container-exit event.

---

### 5.3 Deploy Behavior

**Class:** `Deploy`  
**TypeDefIndex:** 3645 | **Base:** `Behavior`

`Deploy` handles the pre-combat positioning phase. It scores destination tiles using a two-penalty model to spread units optimally across the deployment area.

**Scoring model:**
```
// Penalty 1 — range distance from deployment zone center
rangeScore -= AIWeightsTemplate.DistanceToZoneDeployScore (+0xCC)
              × distanceResult × tileScore.secondaryMovementScore

// Penalty 2 — proximity to set-up allies (spreads the unit line)
for each set-up ally within 6 tiles:
    rangeScore -= (6.0 - distance) × AIWeightsTemplate.DistanceToAlliesScore (+0xD0)
```

Only allies where `Actor +0x50 != 0` (i.e., already set-up) trigger the proximity penalty. Still-mobile allies are not counted — this prevents the AI from spreading away from units that may still be moving.

**Evaluation:**
```
Deploy.OnEvaluate(actor) → int
    GUARD: strategyMode ≠ 0 → return 0
    GUARD: m_IsDone → return 0
    bestTile = GetHighestTileScore()
    if bestTile.tile ≠ actor.currentTile:
        m_TargetTile = bestTile.tile
        return 1000                        // fixed priority — always beats combat behaviors
    else (already at best tile):
        agentContext.field_0x50 = 1        // signal deploy-complete
        m_IsDone = true
        return 0
```

The hardcoded return of `1000` means Deploy always wins over lower-scored combat behaviors while it has an unvisited target tile. `m_IsDone` is the gate that prevents re-evaluation once the unit is positioned.

---

### 5.4 SkillBehavior — Shared Targeting Formula

**Class:** `SkillBehavior`  
**TypeDefIndex:** 3627 | **Base:** `Behavior`

`SkillBehavior` is the abstract intermediary for all skill-based actions. It adds pre-execution sequencing (rotate → deploy → setup → fire) and the complete five-section targeting value formula used by all attack and assist subclasses.

**Key fields:**

| Offset | Name | Notes |
|---|---|---|
| `+0x20` | `m_Skill` | Primary skill this behavior executes |
| `+0x30` | `m_DeployedStanceSkill` | Activated before main skill when m_DeployBeforeExecuting is set |
| `+0x38` | `m_RotationSkill` | Activated when m_RotateBeforeExecuting is set |
| `+0x40` | `m_SetupWeaponSkill` | Activated when m_SetupBeforeExecuting is set |
| `+0x4D` | `m_DeployBeforeExecuting` | Set by HandleDeployAndSetup |
| `+0x4E` | `m_SetupBeforeExecuting` | Set by HandleDeployAndSetup |
| `+0x4F` | `m_RotateBeforeExecuting` | Set by HandleDeployAndSetup |
| `+0x50` | `m_DontActuallyExecute` | Plans deploy/setup but does not fire this turn |
| `+0x54` | `m_WaitUntil` | Game-time timestamp; OnExecute returns false while Time.time < this |
| `+0x58` | `m_TargetTile` | Chosen target tile |

**`HandleDeployAndSetup`** runs during Collect/Evaluate — not Execute. By the time `OnExecute` fires, all pre-execution flags are already committed. `m_DontActuallyExecute` is never read inside `OnExecute`; it is checked by the Agent before dispatching Execute.

**`GetTargetValue` (public wrapper):** Makes two calls to the private scoring overload when the target tile contains a living entity — once for the container and once for the occupant (with `_attackContainedEntity = true`). The higher value is kept.

**`GetTargetValue` (private — the targeting formula):**

```
// Pre-factor from ConsiderSkillSpecifics:
armorMatchPenalty = 1.0 - clamp(TAG_ARMOR_MATCH.value, 0, 1.0)
ammoFactor        = (currentAmmo / maxAmmo) × 0.25 + 0.75    // range [0.75, 1.0]
multiplier        = armorMatchPenalty × ammoFactor

// Section 1 — Hit probability
hitChance    = ComputeHitProbability(...) / 100.0    // [0, 100] → [0.0, 1.0]

// Section 2 — Kill potential and expected damage
expectedKills = ComputeDamageData(...).expectedKills
fVar27       = expectedDamage × 0.01                // normalised expected damage score
fVar30       = killPotential                         // how completely this attack eliminates the target

// Section 3 — Range preference / overkill scaling
fVar32       = proximityBonus / allyPressureBonus    // varies by _forImmediateUse

// Section 4 — Tag effectiveness
bonus = TagEffectivenessTable[tagIndex] × AIWeightsTemplate.ScalePositionWithTags + 1.0
// ScalePositionWithTags replaced with 1.0 when forImmediateUse == true
// +1.0 ensures no-match returns 1.0 (neutral); strong match returns ~2.0 (doubles score)

// Section 5 — Goal-type assembly
if goalType == 0 (attack):       total = fVar32 × 0.5 + fVar30 + fVar27
if goalType == 1 (assist-move):  total = (fVar30 + fVar27) × 0.5 + fVar32
if goalType == 2 (assist-skill): total = (fVar30 + fVar27) × 0.5 + fVar31

return multiplier × bonus × total
```

**OnExecute state machine:**
- Stage 1 — Rotate: fire `m_RotationSkill`, wait 2.0s
- Stage 2 — Deploy: fire `m_DeployedStanceSkill`, wait `animDuration + 0.1s`
- Stage 3 — Setup: fire `m_SetupWeaponSkill`, wait 3.0s
- Stage 4 — Fire: wait `m_WaitUntil`, activate `m_Skill` on `m_TargetTile`

---

### 5.5 Attack and Assist

**Attack** (TDI 3643) and **Assist** (TDI 3641) are the two abstract intermediaries for offensive and ally-targeting skills respectively. Both share the shot candidate collection pipeline; they differ in which tile list they search (opponent tiles vs. ally tiles).

**Shot collection — six `shotGroupMode` values:**

| Value | Name | Behaviour |
|---|---|---|
| 0 | DirectFire | Add target tile directly |
| 1 | ArcFire | Probabilistic arc check; fallback to AoE builder |
| 2 | RadialAoE | `FUN_1806e1fb0` computes AoE tile set |
| 3 | IndirectFire | `FUN_1806de1d0` trajectory builder (separate system) |
| 4 | StoredGroup | Use pre-built list at `Skill +0x60` |
| 5 | TeamScan | Iterate allies; add living tile references |

**Attack.OnEvaluate scoring formula:**

```
FinalScore = (int)(BestCandidateScore × TileUtilityMultiplier)

BestCandidateScore = max over all (originTile, targetTile) pairs of:
    Σ over shot candidates c:
        RawTargetValue(c)
        × ArcScaling(c)             // if shotGroupMode == 1
        / CandidateCount            // if shotGroupMode == 2 (AoE — divides to prevent double-counting)
        × HPRatioScalar             // if origin ≠ actor.currentTile
        × FriendlyFirePenalty(c)    // if target is friendly tile
        × (1 - MoveCostFraction)    // if movement required to reach origin
        + CoFireBonus(c)            // per ally with LoS to c (co-fire accumulation)
    + 1.05 bonus if attacking from current position (no move required)

TileUtilityMultiplier =
    GetUtilityFromTileMult()        // virtual, subclass-defined
    × blend(AoEReadiness, 0.5)      // if IsAoeSkill
    × 1.1                           // if weapon is set up
    × 0.25                          // if delayed move and AP constrained
```

After computing `BestCandidateScore`, the result is gated by `AIWeightsTemplate.ScoreThresholdWithLimitedUses (+0xFC)` — AoE skills with limited uses must exceed a higher threshold before the AI will spend them.

---

### 5.6 Concrete Skill Behaviors

Each concrete subclass overrides `GetTargetValue` to compute its specific contribution. Three structural archetypes appear:

**Archetype 1 — Tag-chain-delegate (InflictDamage, InflictSuppression, Stun):** Builds a tag chain, applies `TagEffectivenessTable` via `GetTagValueAgainst`, then delegates entirely to the base `SkillBehavior.GetTargetValue`. The subclass provides no additional numeric logic.

**Archetype 2 — Float scorer (Mindray, TargetDesignator, SpawnHovermine, Buff, SupplyAmmo):** Computes a float score via its own conditional logic, then multiplies by `AIWeightsTemplate.[BehaviorName]TargetValueMult` and the `contextScale`. Returns an int-cast result.

**Archetype 3 — Void geometry scorer (SpawnPhantom, CreateLOSBlocker):** Performs geometric or eligibility checks, writes a side-effect score into the evaluation context, then returns. No direct float return path.

Key scoring formulas per subclass:

**InflictDamage / InflictSuppression / Stun:** Tag chain → `TagEffectivenessTable[tagIndex] × ScalePositionWithTags + 1.0` → delegate to base formula.

**Mindray:** Two-path scoring.
```
if target lacks mindray vulnerability (EntityInfo +0xA8 bit 0x100):
    return contextScale × AIWeightsTemplate.MindrayNoVulnerabilityMult × base
else:
    return contextScale × AIWeightsTemplate.MindrayVulnerabilityMult × base
```

**Buff:** Six-branch additive scoring. Each bit in the skill effect mask activates one branch:
```
total = 0
if HasSuppression:       total += RemoveSuppressionMult × suppressionMagnitude
if HasStun:              total += RemoveStunnedMult × stunMagnitude
if HasLowMorale:         total += RestoreMoraleMult × moraleMagnitude
if HasMovementPenalty:   total += IncreaseMovementMult × movementDelta
if HasOffensiveDebuff:   total += IncreaseOffensiveStatsMult × offensiveDelta
if HasDefensiveDebuff:   total += IncreaseDefensiveStatsMult × defensiveDelta
return contextScale × total × AIWeightsTemplate.BuffTargetValueMult
```
AoE branches in Buff iterate the caster's team tile list, not a fixed radius — the question asked is "how many of my team members would benefit?", using the target as a range reference.

**SupplyAmmo:**
```
hpFrac  = GetHPFraction(target)
base    = 0.8 + 0.2 × hpFrac           // higher-HP targets score slightly higher
ammoMul = (ammoEmpty ? SupplyAmmoNoAmmoMult : 1.0)
            × (hasSpecialWeapon ? SupplyAmmoSpecialWeaponMult : 1.0)
aoeBonus = AoE_PerMemberScorer() over nearby allies
return contextScale × (base × ammoMul + aoeBonus) × SupplyAmmoTargetValueMult
```
Counter-intuitive: the HP blend `0.8 + 0.2 × hpFrac` means higher-HP targets score slightly higher. The AI prefers to supply ammo to healthy units that can immediately use it effectively.

**TargetDesignator:**
```
if alreadyDesignated (EntityInfo flags bit 11): return 0
observerCount = CountObserversWithLoS(target)
distScore     = GetProximityReachScore(target, unit)
return contextScale × (observerCount + distScore) × TargetDesignatorScoreMult
```

**SpawnPhantom:** Checks eligibility conditions only. Returns a fixed score if the spawn location is valid; 0 otherwise. No geometric computation.

**CreateLOSBlocker:** Most geometrically complex subclass. Scores based on how many allied and enemy units are on either side of a line drawn through the target tile, minus existing AoE zone coverage.
```
// Line geometry: tile is scored by its position relative to a line between unit and enemies
// 5.656854 = 4√2 threshold (diagonal of 4×4 grid square — max distance to be "on" the line)
aoeBase = ComputeBlockerBaseValue(tile)
stackMult = GetStackMultiplier(tile)
z0, z1, z2 = ExistingAoECoverage(tile, zones 0–2)
score = stackMult × aoeBase - (z0 + z1 + z2)   // subtracts existing coverage → anti-redundancy
```
The subtraction of existing coverage means a tile that is already fully covered by AoE zones contributes nothing — preventing the AI from wasting LOS-blocking skills on already-covered positions.

---

## 6. Layer 3 — Agent Priority (Turn Ordering)

Once behaviors are scored, the final question is: **whose turn should be taken first?** The Agent computes a priority multiplier that the turn manager uses to order agents.

```
GetScoreMultForPickingThisAgent():
    threatLevel      = GetThreatLevel()         // sum of threat across all tiles
    opportunityLevel = GetOpportunityLevel()    // attack ceiling score

    fMult = powf(threatLevel, ThreatLevelPOW)
            × powf(opportunityLevel, OpportunityLevelPOW)

    // Raised to PickingScoreMultPOW
    agent.m_Score = max(1, (int)(powf(fMult, PickingScoreMultPOW) × activeBehavior.baseScore))
```

`GetThreatLevel()` accumulates from all tiles in `m_Tiles`. `GetOpportunityLevel()` calls an inner evaluator (`FUN_181430ac0`) for each attack candidate. Both are exponent-scaled by their respective `POW` weights in `AIWeightsTemplate`. A unit that is both under heavy threat and has strong attack opportunities will get its turn allocated before units in less critical situations.

---

## 7. Configuration — AIWeightsTemplate

`AIWeightsTemplate` (`ScriptableObject`, TypeDefIndex 3621) is the single source of truth for all AI tuning. It is accessed globally via `DebugVisualization.WEIGHTS` (static field at `+0x08`). Designers edit this asset; the runtime never modifies it.

**General / normalisation:**

| Offset | Field | Role |
|---|---|---|
| `+0x18` | `BehaviorScorePOW` | Exponent shaping the final agent behavior score curve |
| `+0x20` | `UtilityPOW` | Exponent on raw UtilityScore |
| `+0x24` | `UtilityScale` | Scale after UtilityPOW |
| `+0x28` | `UtilityPostPOW` | Exponent on scaled UtilityScore |
| `+0x2C` | `UtilityPostScale` | Final multiplier on UtilityScore |
| `+0x30` | `SafetyPOW` | Exponent on raw SafetyScore |
| `+0x34` | `SafetyScale` | Scale after SafetyPOW |
| `+0x38` | `SafetyPostPOW` | Exponent on scaled SafetyScore |
| `+0x3C` | `SafetyPostScale` | Final multiplier (before negation) |
| `+0x40` | `DistanceScale` | Distance penalty weight. Also used to negate SafetyScore. |
| `+0x44` | `DistancePickScale` | Distance penalty for GetScaledScore |
| `+0x48` | `ThreatLevelPOW` | Exponent on threat level sum |
| `+0x4C` | `OpportunityLevelPOW` | Exponent on opportunity score |
| `+0x50` | `PickingScoreMultPOW` | Exponent in agent priority formula |

**Position criterions (SafetyScore / UtilityScore inputs):**

| Offset | Field |
|---|---|
| `+0x54` | `DistanceToCurrentTile` |
| `+0x58` | `DistanceToZones` |
| `+0x5C` | `DistanceToAdvanceZones` |
| `+0x60` | `SafetyOutsideDefendZones` |
| `+0x64` | `SafetyOutsideDefendZonesVehicles` |
| `+0x68` | `OccupyZoneValue` |
| `+0x6C` | `CaptureZoneValue` |
| `+0x70` | `CoverAgainstOpponents` |
| `+0x74` | `ThreatFromOpponents` |
| `+0x78` | `ThreatFromTileEffects` |
| `+0x7C` | `ThreatFromOpponentsDamage` |
| `+0x80` | `ThreatFromOpponentsArmorDamage` |
| `+0x84` | `ThreatFromOpponentsSuppression` |
| `+0x88` | `ThreatFromOpponentsStun` |
| `+0x8C` | `ThreatFromPinnedDownOpponents` / `coverMult_Full` |
| `+0x90` | `coverMult_Partial` |
| `+0x94` | `coverMult_Low` |
| `+0x98` | `coverMult_Quarter` |
| `+0x9C` | `coverMult_None` |
| `+0xA0` | `flankingBonusMultiplier` |
| `+0xB0` | `AvoidOpponents weight` (expf exponent) |
| `+0xB4` | `FleeFromOpponents weight` (expf exponent) |
| `+0xB8` | `GetMoveRangeData weight` (expf exponent) |
| `+0xCC` | `DistanceToZoneDeployScore` |
| `+0xD0` | `DistanceToAlliesScore` |
| `+0xFC` | `ScoreThresholdWithLimitedUses` |

**Skill behavior weights:**

| Offset | Field |
|---|---|
| `+0x128` | `MoveBaseScore` |
| `+0x12C` | `MoveScoreMult` |
| `+0x13C` | `UtilityThreshold` |
| `+0x148` | `PathfindingHiddenFromOpponentsBonus` (int) |
| `+0x14C` | `EntirePathScoreContribution` |
| `+0x170` | `BuffBaseScore` |
| `+0x174` | `BuffTargetValueMult` |
| `+0x17C` | `RemoveSuppressionMult` |
| `+0x180` | `RemoveStunnedMult` |
| `+0x184` | `RestoreMoraleMult` |
| `+0x188` | `IncreaseMovementMult` |
| `+0x18C` | `IncreaseOffensiveStatsMult` |
| `+0x190` | `IncreaseDefensiveStatsMult` |
| `+0x194` | `SupplyAmmoBaseScore` |
| `+0x198` | `SupplyAmmoTargetValueMult` |
| `+0x1AC` | `TargetDesignatorBaseScore` |
| `+0x1B0` | `TargetDesignatorScoreMult` |
| `+0x1B8` | `GainBonusTurnBaseMult` |

---

## 8. Class Reference

### TileScore

**Namespace:** `Menace.Tactical.AI.Data` | **TypeDefIndex:** 3636

The per-tile record in `Agent.m_Tiles`. Written by criterions; read by behaviors.

| Offset | Type | Name | Notes |
|---|---|---|---|
| `+0x18` | `Tile*` | `Tile` | Reference to the game tile |
| `+0x1C` | `Tile*` | `UltimateTile` | Terminal destination if path continues through |
| `+0x20` | `float` | `DistanceToCurrentTile` | AP cost from unit's position to this tile |
| `+0x24` | `float` | `DistanceScore` | Raw distance score (from criterion) |
| `+0x28` | `float` | `SafetyScore` | Stored negative after PostProcessTileScores |
| `+0x2C` | `float` | `SafetyScoreScaled` | Scaled variant |
| `+0x30` | `float` | `UtilityScore` | Positive; higher = more tactically valuable |
| `+0x34` | `float` | `UtilityByAttacksScore` | Attack opportunity bonus; committed in PostProcess |
| `+0x38` | `float` | `UtilityByAttacksScoreCandidate` | Staging value before PostProcess commit |
| `+0x3C` | `float` | `movementScore` | Used by Move behavior |
| `+0x40` | `float` | `rangeScore` | Used by Deploy behavior |
| `+0x44` | `float` | `secondaryMovementScore` | Used by Deploy range penalty |

### Tile (partial)

| Offset | Type | Field |
|---|---|---|
| `+0x1C` | byte | `flags` (bit 0=blocked, bit 2=occupied) |
| `+0x48` | List | `weaponSlots` |
| `+0x68` | List | `effectList` |
| `+0xF2` | bool | `hasTileEffect` |
| `+0xF3` | bool | `isObjectiveTile` |
| `+0x244` | int | `accuracyDecay` |

### EvaluationContext (partial)

| Offset | Type | Field | Written by |
|---|---|---|---|
| `+0x20` | float | `reachabilityScore` | DistanceToCurrentTile.Evaluate |
| `+0x24` | float | `zoneInfluenceAccumulator` | ConsiderZones.Evaluate |
| `+0x28` | float | `accumulatedScore` | Most Evaluate overrides |
| `+0x30` | float | `thresholdAccumulator` | CoverAgainstOpponents, ConsiderZones, Roam |
| `+0x60` | bool | `isObjectiveTile` | ThreatFromOpponents.Score (B) |

---

## 9. Key Inferences and Design Notes

**The system is a three-tier utility AI with no learned component.** All weights are static designer-authored values in `AIWeightsTemplate`. There is no reinforcement learning, no memory across matches, and no adaptation to opponent play. Behaviour is entirely determined by the configuration asset and the current game state.

**SafetyScore is a penalty, not a reward, by convention.** After `PostProcessTileScores`, `SafetyScore` is negative. The AI seeks tiles where this penalty is minimised (closest to zero), which corresponds to the safest positions. This naming convention must be kept in mind when reading any formula involving SafetyScore.

**`DistanceScale` serves double duty** — it is both the distance penalty weight in `GetScore()` and the final negation multiplier for SafetyScore in `PostProcessTileScores`. Increasing this single value simultaneously raises the distance penalty and the threat penalty. They are intentionally coupled.

**The `expf` convention means weight constants are exponents, not linear scalars.** Wherever `FUN_1804bad80` (the `expf` approximation) is called on an `AIWeightsTemplate` constant — particularly `+0xB0`, `+0xB4`, `+0xB8` — small changes to the weight have exponential effects on behaviour. A weight of 2.0 vs. 2.5 is not a 25% difference in influence.

**Zone threshold promotion via `9999.0` is a bypass, not a score.** `ConsiderZones.Evaluate` writes `ctx.thresholdAccumulator += 9999.0` for tiles in owned strategic zones. This guarantees those tiles always pass the threshold gate unconditionally. Owned zones are always considered; score still determines which tile within the zone is chosen.

**Two distinct "objective tile" flags exist at different levels.** `tile +0xF3` is tile-side data, read by `GetTileScoreComponents` for an early exit to `[0] = 100.0`. `ctx +0x60` (`isObjectiveTile`) is a per-evaluation context flag written by `ThreatFromOpponents.Score (B)` via `CanReachTarget`. These are different systems for different purposes.

**Healthy units hold better positions.** The 4× health bonus in `Criterion.Score` (applied when health > 95% and at maximum range) creates a strong incentive for undamaged units to hold optimal firing positions. Damaged units receive no bonus and are implicitly pushed toward cover-first evaluations.

**`DistanceScale` coupling makes SafetyScore and distance pressure inseparable.** A designer tuning threat sensitivity is also tuning movement reach, and vice versa. This appears intentional — units under heavy threat should also prefer shorter moves to stay in cover.

**The two-pass criterion evaluation enables post-normalisation decisions.** Pass 1 writes raw scores; `PostProcessTileScores` normalises across all tiles; Pass 2 allows relative comparisons that were impossible with raw data. `ConsiderZones.PostProcess` uses this to identify and promote tiles in objective zones only after the full score landscape is visible.

**Deploy is a hard override, not a competing behavior.** Its fixed score of `1000` means it always wins while `m_IsDone` is false. No other behavior in the investigated set scores above 21474 in practice (that ceiling is for safety), but Deploy's 1000 reliably beats typical movement and attack scores. The deployment phase is an unconditional priority, not a weighted preference.

**Buff scoring is fully additive with no cap.** A skill with all six buff flags set accumulates all six contributions simultaneously. There is no normalisation or ceiling before the final `contextScale × total × BuffTargetValueMult` multiplication.

**SupplyAmmo prefers healthy targets.** `0.8 + 0.2 × hpFrac` scores healthy targets slightly higher. The rationale is that full-HP units can immediately use the ammo effectively, while damaged units may be about to die or take cover.

**`CreateLOSBlocker`'s anti-redundancy mechanism prevents waste.** The subtraction `stackMult × aoeBase - (z0 + z1 + z2)` means if existing AoE zone coverage already equals the base value, the blocker contributes nothing. The AI will not use LOS-blocking skills on already-covered positions.

**Roam is melee-only by structural enforcement.** The `Roam.Collect` first guard hard-exits for ranged units. This is not a tunable parameter.

**WakeUp is structurally unlike all other criterions.** It writes a flag (`movePool.wakeupPending`), not tiles. It integrates with a separate waking-behavior dispatch system outside the tile-scoring pipeline.

**The centiscale convention serves designer ergonomics.** Raw scores from `GetTileScoreComponents` are 0–100 integers. All callers multiply by `0.01` to convert to [0.0, 1.0]. Designers read and tune in 0–100 space; runtime operates in float space.

---

## 10. Open Questions

These questions were unresolved at the close of all investigations. Each carries a concrete next step.

**Q1 — `ConsiderSurroundings.Evaluate` (VA `0x18075C240`) not analysed.**  
The one Criterion `Evaluate` override not yet decompiled. Its role is unknown; it may implement proximity bonuses or flanking logic not covered by the investigated criteria.  
→ Analyse `0x18075C240`. Batch with `ConsiderZones.Collect` at `0x18075C630`.

**Q2 — `AgentContext +0x50` label conflict.**  
Initially identified as a `BehaviorConfig2*` pointer. However, `Deploy.OnCollect` and `Deploy.OnExecute` both write byte value `1` directly to the address stored at this offset — inconsistent with it being a pointer.  
→ Extract true class name for `AgentContext`; re-examine field at `+0x50`.

**Q3 — True class names for `AgentContext`, `EntityInfo`, `Strategy`, `BehaviorConfig2`, `BehaviorWeights`, `StrategyData`.**  
All are accessed through opaque `DAT_` metadata pointers. Field offsets are confirmed; IL2CPP class names are unresolved.  
→ Search `dump.cs` for a class with `EntityInfo`-type field at `+0x10` (AgentContext); class with `List<Actor>` at `+0x20` (EntityInfo); `GetBehaviorWeights` or `GetBehaviorConfig2` as method names (Strategy).

**Q4 — `ConsiderZones.Collect` (VA `0x18075C630`) not analysed.**  
Deferred alongside `ConsiderSurroundings`. May populate the zone tile candidate list.  
→ Batch with Q1.

**Q5 — Actual runtime values of `CoverAgainstOpponents.COVER_PENALTIES[4]`.**  
The static array is allocated in `.cctor` but literal values are not written in the decompiled output.  
→ Memory dump `CoverAgainstOpponents.COVER_PENALTIES` at runtime, or view the `.cctor` assembly listing for four float push instructions.

**Q6 — `GetAoETierForMember` (`FUN_181423600`) internals.**  
Called from `AoE_PerMemberScorer`. Determines how much AoE bonus a given ally receives. Medium priority.  
→ Analyse `0x181423600`.

**Q7 — Concrete `Condition.Evaluate` subclasses.**  
Interface documented (four vtable slots); all implementations deferred. Relevant only if `CanApplyBuff` condition detail is required.  
→ Low priority. Identify subclasses via vtable dispatch from `CanApplyBuff` calls.

**Q8 — `EntityInfo +0x18` weapon/tag object class name.**  
Dereferenced in `InflictDamage.GetTargetValue`. Type confirmed as an object with a tag-index vtable method at `+0x458`, but the class is unresolved.  
→ Resolve EntityInfo true class name; run `extract_rvas.py` to confirm field at `+0x18`.

**Q9 — `FUN_181430ac0` — per-attack evaluator called from `GetOpportunityLevel()`.**  
Returns a float score for an `(attack, actor)` pair. Its internals determine how the AI quantifies attack opportunities.  
→ Analyse `0x181430ac0`.

**Q10 — Role data class at `role +0x14` and `role +0x1C`.**  
Per-actor utility and safety multipliers. The class containing these fields has not been identified.  
→ Search `dump.cs` for a class with float fields at `+0x14` and `+0x1C` that is referenced from `Agent` or `Actor`.

**Q11 — `Agent.m_Flags` bit meanings beyond bit 0.**  
Bit 0 enables neighbor propagation. All other bits are unknown.  
→ Analyse `Agent.HasFlag()` (`0x18071B660`) and `Agent.SetFlag()` (`0x18071CBF0`).

**Q12 — Untouched Behavior subclasses.**  
`GainBonusTurn`, `Reload`, `Scan`, `MovementSkill`, `RemoveStatusEffect`, `TurnArmorTowardsThreat`, `TransportEntity` — full classes not investigated. Each likely follows one of the three archetype patterns but their specific scoring logic is unknown.  
→ Extract each class; identify which archetype applies; analyse `OnEvaluate` and `GetTargetValue`.

---

## 11. Scope Boundaries

The following were explicitly not investigated and should not be derived from this report:

- `GainBonusTurn`, `Reload`, `Scan`, `MovementSkill`, `RemoveStatusEffect`, `TurnArmorTowardsThreat`, `TransportEntity` — entire Behavior subclasses untouched
- `Deploy.OnReset` — bookkeeping only
- `Attack.OnExecute`, `Assist.OnExecute` — execution mechanics; scoring pipelines are complete
- `FUN_1806DE1D0` — indirect fire trajectory builder (shotGroupMode 3); separate system
- `FUN_1806E1FB0` — AoE target set builder; separate system
- `StrategyData.ComputeMoveCost` — pathfinding internals; warrants own investigation
- Concrete `Condition.Evaluate` subclasses — interface documented; implementations deferred
- Network/multiplayer synchronisation of AI state
- `ConsiderSurroundings.Evaluate` — not decompiled
- All `.ctor`, `OnReset`, property accessors throughout (unless material to scoring model)
- `AIWeightsTemplate` field offsets `+0x100–0x140` — not extracted (except those resolved via behavior analysis)
