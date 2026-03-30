# Menace — Unified Tactical AI Decision-Making Report

**Game:** Menace  
**Platform:** Windows x64, Unity IL2CPP  
**Binary:** GameAssembly.dll  
**Image base:** `0x180000000`  
**Source investigations:** TacticalStateSettings (Agent / TileScore), Criterions (tile evaluation), Behaviors (skill / movement / action scoring)  
**Report type:** Synthesis — linear decision-making pipeline with modification guidance  

---

## Table of Contents

1. Purpose and Scope
2. The Complete Decision-Making Pipeline at a Glance
3. Phase 0 — Turn Start and Agent Initialisation
4. Phase 1 — Tile Candidate Collection
5. Phase 2 — Criterion Evaluation (Position Scoring)
6. Phase 3 — Post-Processing and Normalisation
7. Phase 4 — Behaviour Scoring (Action Selection)
8. Phase 5 — Final Behaviour and Agent Selection
9. Phase 6 — Execution
10. The Weight System — Where All Numbers Come From
11. Modification Guide — Achieving Different AI Personalities
    - 11.1 More Aggressive
    - 11.2 More Defensive / Cover-Seeking
    - 11.3 Better Inter-Agent Coordination
    - 11.4 More Mobile / Flanking
    - 11.5 Sniper / Long-Range Specialist
    - 11.6 Support-Oriented (Healing, Buffing, Resupply)
    - 11.7 Suicidal / Banzai
    - 11.8 Suppression-Focused
12. Modification Risk Map
13. Open Questions Relevant to Modification

---

## 1. Purpose and Scope

Three separate investigations reverse-engineered the tactical AI of Menace from the IL2CPP binary:

- **TacticalStateSettings investigation** — uncovered the `Agent` evaluation loop, the `TileScore` data model, the POW/Scale post-processing pipeline, and the `AIWeightsTemplate` weight asset structure.
- **Criterions investigation** — uncovered all 11 `Criterion` subclasses that score candidate tiles for movement.
- **Behaviors investigation** — uncovered the full `Behavior` class hierarchy: all scoring formulas for offensive skills, movement, deployment, buffing, resupply, and utility actions.

This report unifies those three investigations into a single coherent narrative, ordered by the sequence in which each system is invoked during an AI turn. It then provides a modification guide — a mapping from desired AI personality changes to specific data fields and code locations that must be altered to achieve them.

**What this report does NOT cover:**

- Pathfinding internals (`StrategyData.ComputeMoveCost`)
- Concrete `Condition.Evaluate` subclasses (interface is documented; implementations were out of scope)
- Unanalysed behavior classes: `GainBonusTurn`, `Reload`, `Scan`, `MovementSkill`, `RemoveStatusEffect`, `TurnArmorTowardsThreat`, `TransportEntity`
- `ConsiderSurroundings.Evaluate` — the one Criterion subclass not yet decompiled
- Network/multiplayer AI synchronisation
- Per-attack evaluator `FUN_181430ac0` (called from `GetOpportunityLevel`)

---

## 2. The Complete Decision-Making Pipeline at a Glance

```
TURN START
    │
    ▼
[Agent.Evaluate() — 0x180719860]
    │
    ├─ Liveness + sleep + motion guards
    ├─ Iteration budget check (MAX 16)
    │
    ▼
PHASE 1 — TILE COLLECTION
    │
    ├─ Behavior.Collect() calls (Move, Deploy, Attack, Assist subclasses)
    │     └─ Populates shared tile dictionary (m_Tiles / m_TilesToBeUsed)
    │
    ├─ Roam.Collect() — melee-only, bounding-box scan for targets
    ├─ WakeUp.Collect() — sets wakeupPending flag if sleeping ally nearby
    │
    ▼
PHASE 2 — CRITERION EVALUATION (PASS 1)
    │
    ├─ For each tile T in m_Tiles:
    │     For each Criterion C in S_CRITERIONS:
    │         C.IsValid(unit) → gate
    │         C.EvaluateTile(unit, T) → writes to TileScore fields
    │
    │   Active Criteria (by role):
    │   ├─ CoverAgainstOpponents  → ctx.accumulatedScore += cover quality
    │   ├─ ThreatFromOpponents    → ctx.accumulatedScore += threat (4 threads)
    │   ├─ ConsiderZones          → ctx.zoneInfluenceAccumulator + threshold bypass
    │   ├─ DistanceToCurrentTile  → ctx.reachabilityScore
    │   ├─ ExistingTileEffects    → ctx.accumulatedScore += tile effect value
    │   ├─ AvoidOpponents         → penalises tiles near enemies that can't target unit
    │   ├─ FleeFromOpponents      → penalises tiles near enemies that CAN target unit
    │   └─ ConsiderSurroundings   → [NOT YET ANALYSED]
    │
    ▼
PHASE 3 — POST-PROCESSING (NORMALISATION)
    │
    ├─ Agent.PostProcessTileScores() — 0x18071C450
    │     Per tile:
    │     UtilityScore = pow(UtilityByAttacksScore, UtilityPOW)
    │                  = pow(unitUtilityMult × UtilityScore × UtilityScale, UtilityPostPOW)
    │                  × UtilityPostScale
    │
    │     SafetyScore  = pow(SafetyScore, SafetyPOW)
    │                  = pow(unitSafetyMult × SafetyScore × SafetyScale, SafetyPostPOW)
    │                  = −SafetyScore × DistanceScale   ← NEGATED (stored as penalty)
    │
    │     Neighbor propagation (if m_Flags bit 0):
    │       Record HighestSafetyNeighbor and HighestUtilityNeighbor per tile
    │
    ├─ Criterion Pass 2 (PostEvaluate):
    │     C.PostProcess() — ConsiderZones overrides to promote objective tiles
    │     UtilityByAttacksScoreCandidate committed → UtilityByAttacksScore
    │
    ▼
PHASE 4 — BEHAVIOUR SCORING
    │
    ├─ For each Behavior B in Agent.m_Behaviors:
    │     B.Evaluate(actor):
    │       rawScore = B.OnEvaluate(actor)    ← subclass formula
    │       m_Score  = clamp(rawScore, 0, 21474)
    │       if 0 < m_Score < 5: m_Score = 5  ← viability floor
    │
    │   Behavior scoring formulas (summary):
    │   ├─ Deploy     → hardcoded 1000 (if unvisited deploy tile exists)
    │   ├─ Move       → f(movementScore, AP fraction, BehaviorWeights)
    │   ├─ Attack     → f(hitProbability, expectedKills, tagEffectiveness,
    │   │                  arcScaling, coFireBonus, TileUtilityMultiplier)
    │   ├─ Assist     → mirrors Attack on ally tiles
    │   ├─ Buff       → additive per-flag contributions × contextScale × globalScale
    │   ├─ SupplyAmmo → HPblend × AoE ally bonus × weapon setup weights
    │   ├─ TargetDesignator → observer coverage × proximity reach
    │   ├─ SpawnPhantom / SpawnHovermine → eligibility / proximity weighted
    │   └─ CreateLOSBlocker → geometry-aware LOS line score
    │
    ├─ GetUtilityThreshold() filters low-confidence behaviors:
    │     base × max(multA) × multB   (strategy-modulated gate)
    │
    ▼
PHASE 5 — FINAL SELECTION
    │
    ├─ Agent.PickBehavior() — 0x18071BD20
    │     Sort by m_Score (descending via TileScore.CompareScores)
    │     Apply GetUtilityThreshold filter
    │     Set m_ActiveBehavior
    │
    ├─ Agent priority scoring (for multi-agent scheduling):
    │     m_Score = max(1, (int)(GetScoreMultForPickingThisAgent() × activeBehavior.baseScore))
    │     GetScoreMultForPickingThisAgent:
    │       = pow(f(GetThreatLevel, GetOpportunityLevel, vehicle/stealth/fleeing checks),
    │             PickingScoreMultPOW)
    │
    ▼
PHASE 6 — EXECUTION
    │
    ├─ Agent.Execute() → m_ActiveBehavior.Execute(actor)
    │
    │   SkillBehavior state machine (Attack / Assist subclasses):
    │     Stage 1: Rotate    (fire m_RotationSkill, wait 2.0s)
    │     Stage 2: Deploy    (fire m_DeployedStanceSkill, wait animDuration + 0.1s)
    │     Stage 3: Setup     (fire m_SetupWeaponSkill, wait 3.0s)
    │     Stage 4: Fire      (wait m_WaitUntil, fire m_Skill on m_TargetTile)
    │
    │   Move state machine:
    │     Stage 1: rotate toward destination
    │     Stage 2: move along path
    │     Stage 3: resolve peek, chain, or marginal-move states
    │     Stage 4: done
    │
    └─ Turn ends. OnNewTurn() / OnReset() / OnClear() called.
```

---

## 3. Phase 0 — Turn Start and Agent Initialisation

At the start of each AI turn, `Agent.Evaluate()` is called. Before any scoring begins, the agent performs a series of pre-flight checks:

**State reset:** `m_Score = 0`, `m_ActiveBehavior = null`, `m_State = None`. The tile dictionary is double-buffer swapped (`m_Tiles → m_TilesToBeUsed`).

**Liveness gates:** The agent checks that its actor is alive, active, and not mid-deactivation. If any check fails, the agent exits immediately and contributes zero score to the faction scheduler.

**Iteration budget:** `m_Iterations` is incremented and compared against `MAX_ITERATIONS = 16`. If the budget is exhausted, the agent is forced to sleep (`FUN_1805e76f0`). This prevents a single unit from monopolising AI compute time over multiple frames. The cap is bypassed when `TacticalState.m_IsStandalone == true` (standalone/editor mode).

**Sleep and motion checks:** If `m_SleepUntil` has not elapsed (faction clock comparison), or if the actor is currently in motion, the agent yields without evaluating.

Only after all guards pass does the agent proceed to tile collection.

---

## 4. Phase 1 — Tile Candidate Collection

Before scoring any tile, the system must know which tiles to score. Collection is performed by two parallel mechanisms: `Behavior.Collect()` and `Criterion.Collect()`.

### Behavior collection

Each `Behavior` subclass calls its `OnCollect(actor, tileDict)` override. This is where the shared tile dictionary (`m_Tiles`) is populated with candidate positions. The key behaviors that populate tiles are:

**Move:** Enumerates reachable tiles within movement range and AP budget. Tiles are added with their AP cost, world-space path, and initial `movementScore` populated.

**Attack / Assist:** Performs a 2D grid search for valid origin tiles (where the unit could stand to fire) and target tiles (where enemies / allies are). The search radius expands if 3 or more allies are in range — a co-fire coverage heuristic. For each (origin, target) pair, `Skill.QueryTargetTiles` is called, which dispatches by `shotGroupMode`:

| Mode | Name | Behaviour |
|---|---|---|
| 0 | DirectFire | Adds target tile directly |
| 1 | ArcFire | Probabilistic arc check; fallback to AoE builder |
| 2 | RadialAoE | `FUN_1806e1fb0` computes AoE tile set |
| 3 | IndirectFire | `FUN_1806de1d0` trajectory builder |
| 4 | StoredGroup | Uses pre-built list from `Skill+0x60` |
| 5 | TeamScan | Iterates allies, adds living tile references |

After tile population, `ShotCandidate_PostProcess` is called to annotate each candidate with weapon line-of-sight validity.

**Deploy:** Collects candidate tiles of type 2 from `ProximityData`, applies a range-distance penalty and an ally proximity spread penalty, and stores them. Deploy is only active when `strategyMode == 0` (the first deployment phase).

### Criterion collection (special cases)

Two `Criterion` subclasses override `Collect` rather than `Evaluate`:

**Roam.Collect:** Active only for melee units with no active targets. Performs a bounding-box scan around the unit's current position and adds tiles to the candidate list. Hard-exits for ranged units — this is not a configuration option.

**WakeUp.Collect:** Does not add tiles. Instead sets `movePool.wakeupPending = 0` if a sleeping ally is detected nearby. This feeds a separate waking-behaviour dispatch system, not the tile-scoring pipeline.

---

## 5. Phase 2 — Criterion Evaluation (Position Scoring)

With the tile dictionary populated, `Agent.Evaluate()` enters its first criterion pass. For each tile `T` in `m_Tiles`, it iterates `S_CRITERIONS` — a static list of `Criterion` instances shared across all agents — and calls `C.EvaluateTile(actor, T)` on each applicable criterion.

Each criterion writes scores to specific fields of `EvaluationContext`, which accumulate across all criteria. The master formula for what happens with these fields is in `Criterion.Score` (detailed below), but the per-criterion contributions are:

### CoverAgainstOpponents

Evaluates how much protection a tile offers against every known enemy. Three phases:

1. **Occupied tile penalty:** If the tile is already occupied by an enemy that can target the unit, penalise based on that enemy's weapon range and ammo count.
2. **Cover quality per enemy:** For each enemy, classify cover type (full/partial/low/quarter/none), compute a directional penalty based on relative bearing, weight by proximity (inverse distance over 30 tiles), and accumulate `fBest` and `fSum`.
3. **Final write:** `total = fSum + fBest × bestCoverBonusWeight`. Applies choke-point bonus (+10.0 if not a choke), debuff penalty (×0.9 if unit has active debuff and tile is not objective), and writes to `ctx.accumulatedScore`.

The cover multipliers (`coverMult_Full` through `coverMult_None`) at `AIWeightsTemplate +0x8C` through `+0x9C` are the primary levers for how strongly the AI values different cover qualities.

### ThreatFromOpponents

The most expensive criterion. Requests 4 worker threads. Evaluates how dangerous each tile is based on enemy attack potential from that position:

- `Score (A)`: Iterates enemy weapon slots. For each weapon, checks range validity (`IsWithinRangeA`, `IsWithinRangeB`), calls `Criterion.Score`, and keeps the maximum. Applies phase/cover/flanking multipliers.
- `Score (B)`: Spatial scan around each enemy. If a tile is reachable by any enemy from their current position, it is flagged. Writes `ctx.isObjectiveTile` for tiles that enemies could reach a critical target from.
- `Evaluate`: Combines ally occupant contribution (weighted by ally HP ratio) with self-threat, writes to `ctx.accumulatedScore`.

`AIWeightsTemplate +0x74` (`ThreatFromOpponents`) is the master weight for this criterion.

### ConsiderZones

Evaluates strategic zone membership. Zone flags control behaviour via a bitmask system:

- Tiles in owned strategic zones have `ctx.thresholdAccumulator += 9999.0` — a bypass that guarantees the tile passes the utility threshold gate unconditionally.
- `ctx.zoneInfluenceAccumulator` is written with zone-scaled influence.
- `ConsiderZones.PostProcess` (Pass 2) promotes objective tiles above threshold after normalisation.

The `OccupyZoneValue` (+0x68) and `CaptureZoneValue` (+0x6C) weights on `AIWeightsTemplate` tune how aggressively the AI contests objectives.

### DistanceToCurrentTile

Accumulates a reachability score proportional to distance from the unit's current tile, modulated by zone scale and an out-of-range penalty. Writes to `ctx.reachabilityScore (+0x20)`. The `DistanceToCurrentTile` weight at `AIWeightsTemplate +0x54` scales the output.

### ExistingTileEffects

Scores tiles carrying active tile effects that match the evaluating unit's type (filtered by zone immunity mask). Writes to `ctx.accumulatedScore`. The `ThreatFromTileEffects` weight at `+0x78` governs magnitude.

### AvoidOpponents and FleeFromOpponents

A complementary pair modelling area denial and direct threat pressure:

- **AvoidOpponents:** Penalises tiles near enemies that *cannot* directly target the unit. Radius ~11 tiles. Uses `expf(AvoidOpponentsPOW)` as the decay curve. Weight at `AIWeightsTemplate +0xB4`.
- **FleeFromOpponents:** Penalises tiles near enemies that *can* directly target the unit. Radius ~16 tiles. Uses `expf(FleeFromOpponentsPOW)`. Weight at `AIWeightsTemplate +0xB8`.

Because these use `expf` on the weight constants, they are exponentially sensitive — a small change to `AvoidOpponentsPOW` or `FleeFromOpponentsPOW` has a large behavioural effect.

### The Criterion.Score master formula

After all criteria have written their individual contributions, `Criterion.Score` combines them into a final tile utility value:

```
rawScore   = GetTileScoreComponents(tile, ...)[0] × 0.01   // centiscale → float
moveData   = GetMoveRangeData(tile, unit)
rangeCost  = floor(min(rawScore × moveData.moveCostToTile, unit.movePool.maxMoves − 1))
adjScore   = GetReachabilityAdjustedScore(..., rangeCost) × 0.01

// Component A — Attack weight
rangeRatio = min((rawScore × moveData.attackRange) / unit.moveRange, 2.0)
fAtk       = W_attack × rangeRatio
if at maximum range:
    fAtk × = 2.0
    if health > 95%: fAtk × = 4.0     // near-full-health + max-range = 8× base
elif canAttackFromTile and rawScore > 0:
    fAtk × = 1.1
// + expf-scaled overwatch/suppression multipliers

// Component B — Ammo pressure
fAmmo      = (reloadChance × enemies − (ammoLeft / teamSize) × enemies)
             × ammoPressureWeight × enemies × 0.0001

// Component C — Deployment / positional bonus
combined   = min(adjScore × rawScore + adjScore, 2.0)
fDeploy    = combined × deployPositionWeight
if no enemy on tile:
    fDeploy × = (movementDepth × 0.25 + 1.5)
if combined ≥ 0.67: fDeploy × = 3.0

// Component D — Sniper bonus (only if unit has sniper-class weapon)
fSniper    = attackCount × rangeSteps × sniperAttackWeight × rawScore
             × max(healthRatio, 0.25)

// Final
movEff     = expf(movEffTable[movEffIdx] + 1.0)
Score      = movEff × (W_attack × fAtk + W_ammo × fAmmo + W_deploy × fDeploy + W_sniper × fSniper)
```

The four weights `W_attack`, `W_ammo`, `W_deploy`, `W_sniper` come from `AIWeightsTemplate` and represent the four independent tuning axes for positional scoring.

---

## 6. Phase 3 — Post-Processing and Normalisation

After criterion Pass 1 writes raw scores into each `TileScore`, `Agent.PostProcessTileScores()` normalises them through a configurable POW/Scale pipeline. This is where raw criterion outputs become the `SafetyScore` and `UtilityScore` fields used in the final tile ranking.

### UtilityScore normalisation

```
UtilityScore += UtilityByAttacksScore                          // merge attack utility candidate
UtilityScore  = pow(UtilityScore, UtilityPOW)                  // [AIWeightsTemplate +0x20]
UtilityScore  = pow(unitUtilityMult × UtilityScore × UtilityScale, UtilityPostPOW)
              × UtilityPostScale
```

`unitUtilityMult` comes from `role->0x14` — a per-actor role multiplier that allows different unit types to have different attack-opportunity sensitivity without changing the shared asset.

### SafetyScore normalisation

```
SafetyScore   = pow(SafetyScore, SafetyPOW)                    // [AIWeightsTemplate +0x30]
SafetyScore   = pow(unitSafetyMult × SafetyScore × SafetyScale, SafetyPostPOW)
SafetyScore   = −SafetyScore × DistanceScale                   // NEGATED — stored as penalty
```

**Critical convention:** `SafetyScore` is stored as a negative number after this step. In the composite formula `(SafetyScore + UtilityScore)`, a heavily threatened tile has a large negative `SafetyScore` that reduces the total. The AI seeks tiles where this penalty is minimised.

`DistanceScale` (+0x40) is used here as the negation multiplier and simultaneously as the distance penalty weight in `GetScore()`. Increasing `DistanceScale` simultaneously increases distance penalty and threat penalty — they are intentionally coupled.

### Neighbor propagation

If `m_Flags` bit 0 is set on the agent, `PostProcessTileScores` records the best adjacent tile for each tile:
- `HighestSafetyNeighbor`: the neighbor with safety score ≥ 2× current tile's safety
- `HighestUtilityNeighbor`: the neighbor with utility score ≥ 2× current tile's utility

This is a single-step lookahead used by movement scoring to reward positioning near good tiles even if the tile itself is not optimal.

### Criterion Pass 2 (PostEvaluate)

After normalisation, a second criterion pass runs `C.PostProcess()` on already-normalised scores. `ConsiderZones.PostProcess` uses this pass to promote objective tiles above threshold. The `UtilityByAttacksScoreCandidate` committed/discarded decision also happens here — the candidate from Pass 1 is validated against normalised values and either committed to `UtilityByAttacksScore` or discarded.

### Final tile score formula

```
TileScore.GetScore() = (SafetyScore + UtilityScore)
                     − (DistanceScore + DistanceToCurrentTile) × DistanceScale
```

Variants:
- `GetScaledScore()`: same formula but using scaled variants and `DistancePickScale` (+0x44). Used for heatmap display mode 2.
- `GetScoreWithoutDistance()`: `SafetyScore + UtilityScore` only. Used when scoring terminal destinations (`UltimateTile`) where AP cost is irrelevant.

---

## 7. Phase 4 — Behaviour Scoring (Action Selection)

With tiles scored, the system evaluates what the unit should *do*. Each `Behavior` subclass implements `OnEvaluate(actor)` to return an integer score. The `Agent` calls `B.Evaluate(actor)` on every behavior in `m_Behaviors`, applies the score floor and ceiling, then compares against `GetUtilityThreshold`.

### Score normalisation

```
rawScore     = OnEvaluate(actor)            // subclass formula
clampedScore = clamp(rawScore, 0, 21474)    // ceiling: 0x53E2
if GetOrder() != 99999 AND 0 < clampedScore < 5:
    clampedScore = 5                        // minimum viability floor
m_Score = clampedScore
```

Deployment gate: if `roundCount == 0` (deployment phase) and `m_IsUsedForDeploymentPhase == false`, the behavior scores zero and is skipped.

### Utility threshold gate

```
base      = WeightsConfig.utilityThreshold    // AIWeightsTemplate +0x13C
multA     = StrategyData.modifiers.thresholdMultA   // one-directional raise
multB     = StrategyData.modifiers.thresholdMultB   // bidirectional

threshold = max(base, base × multA) × multB
```

Behaviors scoring below this threshold are excluded from selection. Aggressive strategies lower `multB`, making it easier for risky behaviors to be selected. Defensive strategies raise it.

### Deploy behavior

Deploy always scores `1000` when an unvisited deploy tile exists and `strategyMode == 0`. This hardcoded priority guarantees Deploy wins over all other behaviors during the placement phase. Once `m_IsDone` is set (unit is at its optimal tile), Deploy returns 0 permanently.

Tile scoring for Deploy uses a two-penalty model against `rangeScore`:
```
rangeScore -= rangePenaltyScale × distanceToOptimalRange × secondaryMovementScore
for each set-up ally within 6 tiles:
    rangeScore -= (6.0 − distance) × allyProximityPenaltyScale
```
The proximity penalty is linear over 6 tiles and encourages units to spread out during deployment.

### Move behavior

```
movementScore = movementScoreWeight × (apCost / 20.0) × BehaviorWeights.movementWeight
fWeight       = BehaviorWeights.weightScale × MoveScoreMult × (currentAP / maxAP)
              × 0.9                             // if weapon not yet set up
FinalScore    = (int)(fWeight × MoveBaseScore)
```

Special modifiers:
- **Peek bonus:** When `m_IsAllowedToPeekInAndOutOfCover` and the actor is low on AP, movement score is multiplied by 4.0. This creates strong incentive to peek from cover under AP pressure.
- **Marginal move penalty:** When the destination tile is only marginally better than the current position, `fWeight` is multiplied by 0.25 and `m_HasDelayedMovementThisTurn` is set. This prevents jitter where a unit oscillates between near-equal tiles.
- **Chain bonus:** Available when previous movement can chain into a further move.

### Attack and Assist behaviors

The core targeting value formula (from `SkillBehavior.GetTargetValue`):

```
hitChance     = ComputeHitProbability(...)           // [0, 1]
expectedKills = ComputeDamageData(...).expectedKills
fDamage       = expectedDamage × 0.01                // normalised damage score
fKillPotential = (how completely this attack eliminates the target)
fProximity    = proximityBonus / allyPressureBonus   // varies by _forImmediateUse

// By goal type:
goalType 0 (attack):       total = fProximity × 0.5 + fKillPotential + fDamage
goalType 1 (assist-move):  total = (fKillPotential + fDamage) × 0.5 + fProximity
goalType 2 (assist-skill): total = (fKillPotential + fDamage) × 0.5 + fAbilityBonus
```

Pre-factor from `ConsiderSkillSpecifics()`:
```
armorMatchPenalty = 1.0 − clamp(TAG_ARMOR_MATCH, 0, 1.0)
ammoFactor        = (currentAmmo / maxAmmo) × 0.25 + 0.75   // range [0.75, 1.0]
multiplier        = armorMatchPenalty × ammoFactor
```

Final attack score:
```
FinalScore = (int)(BestCandidateScore × TileUtilityMultiplier)

TileUtilityMultiplier =
    GetUtilityFromTileMult()      // virtual, subclass-defined
    × blend(AoEReadiness, 0.5)    // if IsAoeSkill
    × 1.1                         // if weapon is set up
    × 0.25                        // if delayed move + AP constrained
```

Co-fire accumulation: for each ally with line-of-sight to the same target, `CoFireBonus` is added to the candidate score. This rewards attacking targets that allies can also engage.

### Concrete behavior scorers

| Behavior | Scoring mechanism |
|---|---|
| `InflictDamage` | Tag chain → delegate to base `GetTargetValue` (`skillEffectType = 1`) |
| `InflictSuppression` | Same as InflictDamage structurally (`skillEffectType = 1`) |
| `Stun` | Same as InflictSuppression |
| `Mindray` | Two-path: resistance gate + vulnerability dispatch |
| `Buff` | Six-branch additive (per buff flag): `contextScale × Σ(flag contributions) × globalScale` |
| `SupplyAmmo` | `(0.8 + 0.2 × hpFrac) × AoEAllyBonus × weaponSetupWeights` |
| `TargetDesignator` | Observer coverage + proximity reach float scorer |
| `SpawnPhantom` | Void eligibility scorer |
| `SpawnHovermine` | Void weighted proximity scorer |
| `CreateLOSBlocker` | `stackMult × aoeBase − (existingCoverage)` along geometric line |

---

## 8. Phase 5 — Final Behaviour and Agent Selection

### PickBehavior

`Agent.PickBehavior()` sorts behaviors by `m_Score` (descending), applies the `GetUtilityThreshold` filter, and sets `m_ActiveBehavior`. Ties are broken by `GetOrder()`. Behaviors with `m_DontActuallyExecute` set are excluded from execution dispatch.

### Agent priority scoring (multi-agent scheduling)

When multiple agents are ready to act, the faction scheduler uses `m_Score` to determine which agent goes next. This score is:

```
m_Score = max(1, (int)(GetScoreMultForPickingThisAgent() × activeBehavior.baseScore))
```

`GetScoreMultForPickingThisAgent()`:
```
combinedScore = f(GetThreatLevel(), GetOpportunityLevel(),
                  vehicle status, stealth flag, fleeing flag, Scout behavior)
return pow(combinedScore, PickingScoreMultPOW)
```

`GetThreatLevel()`:
```
for each threat source:
    threatValue  = clamp(rawThreat, 0, 3.0)
    sign         = +1.0 (forward-facing) / −1.0 (from behind)
    if suppressed: sign × = 0.8
    attenuation  = clamp(count × 0.0625, 0, 1.0)   // saturates at 16 sources
    accumulator += (1.0 − attenuation) × (threatValue + 1.0) × sign
return pow(accumulator, ThreatLevelPOW)
```

`GetOpportunityLevel()`:
```
for each skill, for each attack slot (0..2):
    bestScore = max(bestScore, FUN_181430ac0(attack, actor))
return pow(bestScore, OpportunityLevelPOW)
```

A unit under heavy threat with a high-value attack opportunity scores high and goes first. A unit in no danger with no good shots scores low and waits.

---

## 9. Phase 6 — Execution

Once `m_ActiveBehavior` is selected, `Agent.Execute()` dispatches to `m_ActiveBehavior.OnExecute(actor)`.

### SkillBehavior state machine

All skill-based behaviors (Attack, Assist subclasses) share a four-stage execution sequencer:

| Stage | Action | Wait condition |
|---|---|---|
| 1 — Rotate | Fire `m_RotationSkill` | 2.0 seconds |
| 2 — Deploy | Fire `m_DeployedStanceSkill` | `animDuration + 0.1s` |
| 3 — Setup | Fire `m_SetupWeaponSkill` | 3.0 seconds |
| 4 — Fire | Wait `m_WaitUntil`, fire `m_Skill` on `m_TargetTile` | skill completion |

Stages 1–3 are skipped if the corresponding skill is null. Each stage sets a wait condition before returning — the agent yields and resumes on the next `Execute()` call. This distributes skill execution across frames.

### Move state machine

Four stages: rotate toward destination → move along path → resolve peek / chain / marginal-move states → done. `m_IsAllowedToPeekInAndOutOfCover` and `m_HasDelayedMovementThisTurn` govern transitions between stages.

### Turn cleanup

At turn end:
- `OnNewTurn()` — called at the turn boundary; resets turn-specific state
- `OnReset()` — clears behaviour state (targets, tile references, done flags)
- `OnClear()` — called on agent destruction or round end; full teardown

---

## 10. The Weight System — Where All Numbers Come From

All numerical behaviour of the AI flows from a single `ScriptableObject` asset: `AIWeightsTemplate`. It is accessed globally via `DebugVisualization.WEIGHTS` (static field). In-engine it appears under `"Menace/Config/AI Weights"` in the asset menu.

Secondary weight sources:
- `BehaviorWeights` (held at `Strategy +0x310`): per-strategy movement weight and scale
- `WeightsConfig` (investigation-internal name): per-behavior utility threshold, score scales, and per-behavior base/mult values — maps closely to `AIWeightsTemplate` offsets above `+0xCC`
- Per-actor role multipliers (`role->0x14` UtilityMult, `role->0x1C` SafetyMult): override global weights per unit type
- `StrategyData.modifiers` (`thresholdMultA`, `thresholdMultB`): strategy-layer multipliers on the utility threshold

A complete summary of `AIWeightsTemplate` fields is provided in Section 6 of the TacticalStateSettings report and is not reproduced here in full. The fields most directly relevant to personality modification are called out in Section 11 below.

---

## 11. Modification Guide — Achieving Different AI Personalities

All modifications described here target data, not code. Every value below is a field on `AIWeightsTemplate` (the `ScriptableObject` asset) unless a code location is specified.

The modification approach has two tiers:
- **Tier 1 (data-only):** Modify `AIWeightsTemplate` field values. Safe, reversible, no recompile required. Works well for tuning within the existing AI design space.
- **Tier 2 (code):** Modify scoring formulas, branching logic, or the criterion/behavior list. Required for behaviours outside the design space. Involves patching IL2CPP binary or hooking at runtime.

---

### 11.1 More Aggressive

The AI is more aggressive when it prioritises attack opportunity over safety and position, acts earlier than other agents, and accepts higher risk.

**Tier 1 — data:**

| Field | Offset | Change | Effect |
|---|---|---|---|
| `ThreatFromOpponents` | `+0x74` | Decrease | Reduces penalty for standing in dangerous positions |
| `FleeFromOpponentsPOW` | `+0xB8` | Decrease | Weakens exponential flee-pressure curve |
| `AvoidOpponentsPOW` | `+0xB4` | Decrease | Reduces passive avoidance of enemy zones |
| `DistanceScale` | `+0x40` | Decrease | Reduces distance penalty; AI will move farther toward enemies |
| `CoverAgainstOpponents` | `+0x70` | Decrease | Cover matters less; AI takes exposed positions |
| `TargetValueDamageScale` | `+0xE4` | Increase | Attack behaviors score higher |
| `DamageScoreMult` | `+0x108` | Increase | `InflictDamage` behavior scores higher |
| `UtilityPOW` / `UtilityPostPOW` | `+0x20`, `+0x28` | Decrease toward 1.0 | More linear (less compressed) utility scoring; high-utility tiles stand out more |
| `SafetyPOW` / `SafetyPostPOW` | `+0x30`, `+0x38` | Decrease toward 0 | Flattens safety penalty; AI is less deterred by threats |
| `OpportunityLevelPOW` | `+0x4C` | Increase | Agents with high attack opportunities are scheduled first |

**Tier 2 — code:**

To make the AI fire even when movement would yield a better position, modify `Attack.OnEvaluate` to reduce the weight of `(1 - MoveCostFraction)` in the `BestCandidateScore` formula. Currently a unit that must move to attack receives a multiplicative penalty; reducing this to 0.8 or 0.9 will make the AI more willing to move-and-shoot.

---

### 11.2 More Defensive / Cover-Seeking

The AI prioritises survival, stays in cover, avoids exposure, and waits for the enemy to come to it.

**Tier 1 — data:**

| Field | Offset | Change | Effect |
|---|---|---|---|
| `CoverAgainstOpponents` | `+0x70` | Increase | Cover quality drives more of the positional score |
| `ThreatFromOpponents` | `+0x74` | Increase | Threats are penalised more heavily |
| `FleeFromOpponentsPOW` | `+0xB8` | Increase | Stronger flee-pressure from enemies that can target the unit |
| `ThreatFromPinnedDownOpponents` | `+0x8C` | Increase | Pinned enemies still perceived as threatening; AI stays behind cover longer |
| `ThreatFromOpponentsDamage` | `+0x7C` | Increase | Damage threat component weighted more heavily; high-damage enemies drive cover-seeking |
| `SafetyPOW` / `SafetyPostScale` | `+0x30`, `+0x3C` | Increase | Amplifies safety score; safe tiles dominate selection |
| `DistanceScale` | `+0x40` | Increase | Stronger distance penalty; AI prefers tiles close to current position |
| `UtilityThreshold` | `+0x13C` | Increase | Raises the bar for attacking; AI will wait for better shots |
| `MoveIfNewTileIsBetterBy` | `+0x150` | Increase | Requires a larger improvement before choosing to move |

---

### 11.3 Better Inter-Agent Coordination

Currently, coordination is implicit — agents are scheduled by priority score, and co-fire bonuses reward targeting enemies that allies can also attack. To improve active coordination:

**Tier 1 — data:**

| Field | Offset | Change | Effect |
|---|---|---|---|
| `IncludeAttacksAgainstAllOpponentsMult` | `+0xC0` | Increase | Increases weight of attacks that can hit multiple enemies; group tactics emerge |
| `AllyMetascoreAgainstThreshold` | `+0xAC` | Increase | Raises how much the system values ally proximity when approving behaviors |
| `DistanceToAlliesScore` | `+0xD0` | Increase (deployment) | Units deploy closer together, establishing tighter initial formations |
| `OccupyZoneValue` | `+0x68` | Increase | Multiple agents converge on the same objective zone |

**Tier 2 — code:**

The cleanest coordination improvement would be to add a shared-target memory to `AgentContext` — a list of enemies currently targeted by other agents this turn. `Attack.OnCollect` could then boost `CoFireBonus` by a multiplier when the target is already in the shared list. This is outside the existing design space and requires binary patching or a hook.

Alternatively, a simpler Tier 2 approach: modify `GetScoreMultForPickingThisAgent` to reduce the priority of agents whose `m_ActiveBehavior` targets a tile that a higher-priority agent is already moving toward. This prevents two agents from walking to the same tile independently.

---

### 11.4 More Mobile / Flanking

The AI moves more, repositions aggressively, and seeks flanking positions rather than holding cover.

**Tier 1 — data:**

| Field | Offset | Change | Effect |
|---|---|---|---|
| `MoveScoreMult` | `+0x12C` | Increase | Move behavior scores higher relative to attack |
| `MoveBaseScore` | `+0x128` | Increase | Direct scaling of move score |
| `DistanceToCurrentTile` (AIWeightsTemplate) | `+0x54` | Increase | `DistanceToCurrentTile` criterion accumulates more strongly; distant tiles are favoured |
| `TileScoreDifferenceMult` | `+0x134` | Increase | Larger score differences between tiles encourage movement |
| `MoveIfNewTileIsBetterBy` | `+0x150` | Decrease | Lower threshold to move; AI repositions more readily |
| `DistanceScale` | `+0x40` | Decrease | Distance penalty reduced; farther moves are cheaper |
| `PathfindingSafetyCostMult` | `+0x140` | Decrease | Pathfinder accepts less-safe routes; AI takes risks to flank |

**Tier 2 — code:**

The peek multiplier (`×4.0` in `Move.OnEvaluate` when `m_IsAllowedToPeekInAndOutOfCover`) is a hardcoded constant. Raising it further would make peek-and-shoot tactics much more dominant. The marginal move penalty (`×0.25`) prevents jitter; lowering it would make the AI more willing to make small positional adjustments each turn.

---

### 11.5 Sniper / Long-Range Specialist

The AI holds maximum range, avoids melee, and prioritises precision fire over volume.

**Tier 1 — data:**

| Field | Offset | Change | Effect |
|---|---|---|---|
| `FleeFromOpponentsPOW` | `+0xB8` | Increase | Strong flee-from-melee-range behaviour |
| `AvoidOpponentsPOW` | `+0xB4` | Increase | Avoids being adjacent to anything |
| `DistanceScale` | `+0x40` | Decrease | Reduces the penalty for being far from current position |

**Tier 2 — code:**

In `Criterion.Score`, when `rawScore × moveData.moveCostToTile ≥ unit.movePool.maxMoves` (i.e. the tile is at max range), `fAtk` is multiplied by 2.0, and if health > 95% it gets an additional ×4.0 (total 8×). These multipliers are hardcoded. To make range preference even stronger, raise the 2.0 and 4.0 constants. To lower the health threshold below 95%, modify the comparison.

---

### 11.6 Support-Oriented (Healing, Buffing, Resupply)

The AI prioritises ally support over direct combat, using Buff and SupplyAmmo behaviors more readily.

**Tier 1 — data:**

| Field | Offset | Change | Effect |
|---|---|---|---|
| `BuffBaseScore` | `+0x170` | Increase | Buff behavior is more likely to win against Attack |
| `BuffTargetValueMult` | `+0x174` | Increase | Individual buff contributions scale higher |
| `IncreaseMovementMult` | `+0x188` | Increase | Movement buffs are valued more |
| `IncreaseOffensiveStatsMult` | `+0x18C` | Increase | Offensive stat buffs are valued more |
| `SupplyAmmoBaseScore` | `+0x194` | Increase | Resupply behavior competes better |
| `SupplyAmmoTargetValueMult` | `+0x198` | Increase | Target value scales the resupply priority |
| `SupplyAmmoNoAmmoMult` | `+0x19C` | Increase | Urgency when allies are out of ammo |
| `SupplyAmmoSpecialWeaponMult` | `+0x1A0` | Increase | Prioritises resupplying units with special weapons |
| `DamageScoreMult` | `+0x108` | Decrease | Attack behavior scores less; support wins more often |
| `UtilityThreshold` | `+0x13C` | Decrease | Support behaviors more easily pass the approval gate |

**Note on SupplyAmmo HP blend:** The formula `0.8 + 0.2 × hpFrac` means healthy targets score *higher* for resupply. This is intentional — the AI prefers to resupply units that can immediately use the ammo. If you want wounded units prioritised for resupply, the blend formula itself needs to be inverted (Tier 2).

---

### 11.7 Suicidal / Banzai

The AI ignores self-preservation entirely and charges the enemy.

**Tier 1 — data:**

| Field | Offset | Change | Effect |
|---|---|---|---|
| `ThreatFromOpponents` | `+0x74` | Set to 0 | Threats are not penalised at all |
| `FleeFromOpponentsPOW` | `+0xB8` | Set to 0 | No flee pressure |
| `AvoidOpponentsPOW` | `+0xB4` | Set to 0 | No avoidance of enemy areas |
| `CoverAgainstOpponents` | `+0x70` | Set to 0 | Cover quality is irrelevant |
| `SafetyPOW` | `+0x30` | Set to 0 | Flattens safety score to 0 after POW(x, 0) = 1, then safety is muted |
| `SafetyScale` / `SafetyPostScale` | `+0x34`, `+0x3C` | Set to 0 | Safety score contributes nothing |
| `DistanceToCurrentTile` (criterion weight) | `+0x54` | Increase substantially | Strong pull toward distant tiles (toward the enemy) |
| `DamageScoreMult` | `+0x108` | Increase substantially | Attack behaviors dominate |
| `UtilityThreshold` | `+0x13C` | Set to 0 | All behaviors pass; AI always acts |

**Warning:** Setting POW fields to 0 yields `pow(x, 0) = 1` for all x. This does not suppress a score — it sets it to 1.0 regardless of input. To truly zero out a score component, set the corresponding `Scale` or `PostScale` field to 0.

---

### 11.8 Suppression-Focused

The AI prioritises suppressing enemies over killing them, trading lethality for area control.

**Tier 1 — data:**

| Field | Offset | Change | Effect |
|---|---|---|---|
| `SuppressionBaseScore` | `+0x110` | Increase substantially | `InflictSuppression` behavior competes with damage |
| `SuppressionScoreMult` | `+0x114` | Increase | Suppression tile value scales higher |
| `TargetValueSuppressionScale` | `+0xEC` | Increase | Suppression output factors more into targeting value |
| `DamageBaseScore` / `DamageScoreMult` | `+0x104`, `+0x108` | Decrease | InflictDamage yields to InflictSuppression |
| `ThreatFromSuppressedOpponents` | `+0x90` | Increase | Suppressed enemies are perceived as less threatening; positive feedback loop |
| `ThreatFromPinnedDownOpponents` | `+0x8C` | Increase | Pinned enemies are treated as neutralised |

---

## 12. Modification Risk Map

Not all modifications are equally safe. This table summarises which changes carry risk of breaking the AI or producing degenerate behaviour.

| Modification | Risk | Reason |
|---|---|---|
| Adjust `AIWeightsTemplate` float weights within their documented ranges | Low | These fields have documented ranges and were designed to be tuned |
| Change `UtilityPOW` / `SafetyPOW` values | Medium | POW fields interact multiplicatively; setting to 0 yields 1.0, not 0.0 |
| Set `DistanceScale` to 0 | Medium | Decouples distance penalty from safety penalty; may cause clustering |
| Set `FleeFromOpponentsPOW` to 0 via `expf` path | Medium | expf(0) = 1, not 0; the flee criterion still applies with a flat multiplier |
| Lower `UtilityThreshold` to 0 | Medium | All behaviors pass; agents may waste turns on trivially low-value actions |
| Raise `Deploy.allyProximityPenaltyScale` very high | High | Deploy scoring becomes dominated by spread penalty; units may refuse to deploy near each other |
| Modify hardcoded constants in `Criterion.Score` (8× health bonus, 4.0 peek multiplier) | High | These affect all units of the relevant type globally; unexpected interactions |
| Modify `GetScoreMultForPickingThisAgent` | High | Affects multi-agent scheduling; can cause all agents to act in the wrong order or starve certain units |
| Add behaviors to `S_CRITERIONS` without matching `IsApplicable` guard | High | Criteria run on every agent; a criterion without proper guards will affect all unit types |
| Modify `MAX_ITERATIONS` | High | Affects per-frame AI compute budget; raising it can cause frame hitches; lowering it causes premature sleep |

---

## 13. Open Questions Relevant to Modification

The following open questions from the source investigations are specifically relevant to modification efforts. Resolving them would improve modification precision.

**True class name of `WeightsConfig`** (NQ-4/5 from Behaviors report): The fields at `WeightsConfig +0x78`, `+0x148`, `+0x14C` are inferred. Until the class is identified in dump.cs, modifications to these fields must be made by offset rather than by name.

**`AgentContext +0x50` label conflict** (NQ-42): Offset +0x50 is labeled as `BehaviorConfig2*` in some contexts but receives a byte write of value 1 from `Deploy.OnEvaluate`. If this is a flag field, it has implications for deploy completion detection. Resolved by extracting the true class name of `AgentContext`.

**`ConsiderSurroundings.Evaluate`** (Criterions open question 4): The one `Evaluate` override not yet decompiled. It may contribute to `ctx.accumulatedScore` in ways that interact with modification targets above. VA: `0x18075C240`.

**Per-actor role multipliers** (`role->0x14` UtilityMult, `role->0x1C` SafetyMult): The class containing these fields has not been identified. These multipliers override global `AIWeightsTemplate` values per unit type. Without knowing the class, per-unit-type personality differentiation must be done via separate `AIWeightsTemplate` assets rather than role overrides.

**Co-fire bonus weight location**: The `CoFireBonus` scalar is referenced in Attack behavior scoring but its location in `WeightsConfig` / `AIWeightsTemplate` is not confirmed to a named field in the current reports. Identify this field before attempting coordination improvements via Section 11.3.

**`ConsiderZones.Collect`** (VA `0x18075C630`): Not yet decompiled. Zone-based tile collection may add candidate tiles that are not reachable by normal movement. This could affect the scope of tiles that receive objective-tile promotion in `ConsiderZones.PostProcess`.
