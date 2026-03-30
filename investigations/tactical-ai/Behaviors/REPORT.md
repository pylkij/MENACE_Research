# Menace — Tactical AI Behavior System
## Final Investigation Report

**Game:** Menace  
**Platform:** Windows x64, Unity IL2CPP  
**Binary:** GameAssembly.dll  
**Image base:** `0x180000000` (VA = RVA + 0x180000000)  
**Source material:** Il2CppDumper dump.cs (~885,000 lines), Ghidra decompilation, `extract_rvas.py` class dumps, `extraction_report_master.txt`  
**Investigation status:** Complete — 52 VAs analysed across all stages

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. The Core Finding — The Behaviour Lifecycle and Scoring Model
5. The Full System Pipeline
6. Class: `Behavior`
7. Class: `SkillBehavior`
8. Class: `Move`
9. Class: `Attack`
10. Class: `Assist`
11. Class: `Deploy`
12. Concrete Scoring Subclasses
    - 12.1 InflictDamage
    - 12.2 InflictSuppression
    - 12.3 Stun
    - 12.4 Mindray
    - 12.5 Buff
    - 12.6 SupplyAmmo
    - 12.7 TargetDesignator
    - 12.8 SpawnPhantom
    - 12.9 SpawnHovermine
    - 12.10 CreateLOSBlocker
13. Supporting Utility Functions
    - 13.1 ComputeHitProbability
    - 13.2 ComputeDamageData
    - 13.3 TagEffectiveness_Apply
    - 13.4 AoE_PerMemberScorer
    - 13.5 CanApplyBuff
    - 13.6 ShotPath_ActorCast
    - 13.7 Skill.QueryTargetTiles
    - 13.8 ShotCandidate_PostProcess
14. Supporting Data Classes
    - 14.1 ProximityData / ProximityEntry
    - 14.2 TileScore
    - 14.3 BehaviorWeights / BehaviorConfig2
    - 14.4 TagEffectivenessTable
15. Configuration Classes
    - 15.1 WeightsConfig
    - 15.2 Strategy / StrategyData
    - 15.3 AgentContext / EntityInfo
16. Ghidra Address Reference
17. Key Inferences and Design Notes
18. Open Questions
19. Scope Boundaries
20. Unresolved Class Names

---

## 1. Investigation Overview

### What was investigated

The complete tactical AI behaviour system of Menace — all classes in the `Menace.Tactical.AI` and `Menace.Tactical.AI.Behaviors` namespaces that govern per-turn decision-making. This covers the abstract base infrastructure (`Behavior`, `SkillBehavior`), the movement system (`Move`, `Deploy`), the offensive and ally-targeting pipelines (`Attack`, `Assist`), every concrete scoring subclass (`InflictDamage`, `InflictSuppression`, `Stun`, `Mindray`, `Buff`, `SupplyAmmo`, `TargetDesignator`, `SpawnPhantom`, `SpawnHovermine`, `CreateLOSBlocker`), and all utility functions those subclasses call.

### What was achieved

- Complete field layouts confirmed for all 15+ classes with offsets, types, and confirmation status
- `Behavior` base class: scoring pipeline (`Evaluate` → score clamping, floor, deployment gate), `Collect` dispatch, `Execute` wrapper, `GetUtilityThreshold` strategy-modulated formula, `HandleDeployAndSetup` AP-sufficiency decision — all fully reconstructed
- `SkillBehavior`: four-stage execution state machine (rotate → deploy → setup → fire), complete five-section `GetTargetValue` formula including hit probability, kill potential, overkill scaling, range preference, adjacency bonus, and goal-type assembly — fully reconstructed
- `Move`: full tile scoring pipeline (~1,500 lines of Ghidra), forced/voluntary movement distinction, peek bonus, marginal move penalty, chain bonus, four-stage `OnExecute` state machine — fully reconstructed
- `Attack` and `Assist`: geometry collection, candidate scoring, arc/AoE/indirect fire dispatch (6 shotGroupModes), co-fire accumulation, movement integration — fully reconstructed
- `Deploy`: two-penalty scoring model (range distance + ally proximity spread), fixed-priority 1000 scoring, done-state management — fully reconstructed
- All 9 concrete `GetTargetValue` overrides fully reconstructed, including the three scorer archetypes (tag-chain-delegate, float scorer, void side-effect scorer)
- `ComputeHitProbability`, `ComputeDamageData`, `TagEffectiveness_Apply`, `AoE_PerMemberScorer`, `CanApplyBuff`, `ShotPath_ActorCast`, `Skill.QueryTargetTiles`, `ShotCandidate_PostProcess` — all fully reconstructed
- 40+ `WeightsConfig` float fields confirmed and named
- Complete `skillEffectType` enum established (values 0, 1, 2 with associated subclasses)
- The six `shotGroupMode` values fully resolved

### What was NOT investigated

The following are explicitly out of scope:

- `GainBonusTurn`, `Reload`, `Scan`, `MovementSkill`, `RemoveStatusEffect`, `TurnArmorTowardsThreat`, `TransportEntity` — entire classes untouched
- `Deploy.OnReset` — bookkeeping reset; not material to scoring model
- `FUN_1806DE1D0` — indirect fire trajectory builder — separate system
- `FUN_1806E1FB0` — AoE target set builder — separate system
- `StrategyData.ComputeMoveCost` (`FUN_1806361F0`) — pathfinding internals; large, separate system
- Concrete `Condition.Evaluate` subclasses — interface documented; implementations deferred
- `GetAoETierForMember` (`FUN_181423600`) — deferred; medium priority
- `Attack.OnExecute`, `Assist.OnExecute` — execution mechanics; scoring pipelines are complete
- True IL2CPP class names for: `WeightsConfig`, `AgentContext`, `EntityInfo`, `Strategy`, `BehaviorConfig2`, `BehaviorWeights`, `StrategyData` — all accessed via opaque `DAT_` pointers; see Section 20

---

## 2. Tooling

`extract_rvas.py` was run against the `Menace.Tactical.AI.Behaviors` namespace to produce `extraction_report_master.txt`, covering all behavior subclasses. The report was used throughout to cross-reference field offsets and method RVAs against Ghidra decompilation output. `dump.cs` (~885,000 lines) was queried throughout for field names, offsets, and class relationships.

No tool errors were encountered. Several large functions (`SupplyAmmo.GetTargetValue`, `CreateLOSBlocker.GetTargetValue`, `Move.OnEvaluate`) required individual Ghidra exports due to truncation when batched; all were ultimately obtained in full.

The extraction report confirmed `NO_RVA` entries for `GetTargetValue` and `GetUtilityFromTileMult` on the base `Attack` and `Assist` classes — expected, as these methods are abstract with no base-class body.

---

## 3. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| `Behavior` | `Menace.Tactical.AI` | 3623 | Abstract root. Lifecycle, score storage, deployment gate, utility threshold. |
| `SkillBehavior` | `Menace.Tactical.AI` | 3627 | Abstract intermediary. Pre-execution sequencing, targeting value formula. |
| `Move` | `Menace.Tactical.AI.Behaviors` | 3650 | Tile-based movement. Full scoring + execution pipeline. |
| `Attack` | `Menace.Tactical.AI.Behaviors` | 3643 | Offensive skill base. Geometry collection, candidate scoring, co-fire. |
| `Assist` | `Menace.Tactical.AI.Behaviors` | 3641 | Ally-targeting skill base. Mirrors Attack on ally tiles. |
| `Deploy` | `Menace.Tactical.AI.Behaviors` | 3645 | Positioning pre-requisite. Places unit on optimal deploy tile. |
| `InflictDamage` | `Menace.Tactical.AI.Behaviors` | 3647 | Attack subclass. Tag chain → delegate to base scorer. |
| `InflictSuppression` | `Menace.Tactical.AI.Behaviors` | 3648 | Attack subclass. Suppression damage; structurally identical to InflictDamage. |
| `Stun` | `Menace.Tactical.AI.Behaviors` | 3667 | Attack subclass. Stun effect; structurally identical to InflictSuppression. |
| `Mindray` | `Menace.Tactical.AI.Behaviors` | 3657 | Attack subclass. Two-path: resistance gate + vulnerability dispatch. |
| `Buff` | `Menace.Tactical.AI.Behaviors` | 3644 | Assist subclass. Six-branch additive flag-driven scorer. |
| `SupplyAmmo` | `Menace.Tactical.AI.Behaviors` | 3664 | Assist subclass. HP-blend + AoE ally bonus + weapon setup weights. |
| `TargetDesignator` | `Menace.Tactical.AI.Behaviors` | 3665 | Attack subclass. Observer coverage + proximity reach float scorer. |
| `SpawnPhantom` | `Menace.Tactical.AI.Behaviors` | 3661 | Attack subclass. Void eligibility scorer. |
| `SpawnHovermine` | `Menace.Tactical.AI.Behaviors` | 3660 | Attack subclass. Void weighted proximity scorer. |
| `CreateLOSBlocker` | `Menace.Tactical.AI.Behaviors` | 3655 | Assist subclass. Void geometry-aware LOS line scorer. |

---

## 4. The Core Finding — The Behaviour Lifecycle and Scoring Model

Every tactical AI action in Menace is implemented as a subclass of `Behavior`. Each turn, the `Agent` drives all registered behaviors through a fixed pipeline. The integer score produced by `Evaluate` determines which behaviour executes.

### Score formula

```
rawScore     = OnEvaluate(actor)          // subclass-defined; returns int
clampedScore = clamp(rawScore, 0, 21474)
if GetOrder() != 99999 AND clampedScore > 0 AND clampedScore < 5:
    clampedScore = 5                      // minimum viable floor
m_Score = clampedScore
```

**Score ceiling:** `21474` (0x53E2). All subclass scoring is bounded by this.  
**Minimum floor:** `5`. Any positive score below 5 is raised to 5, preventing very-low-confidence behaviours from being discarded due to rounding. The floor is bypassed when `GetOrder() == 99999` (a sentinel value for behaviours that opt out).  
**Deployment gate:** When `roundCount == 0` (deployment phase) and `m_IsUsedForDeploymentPhase == false`, `Evaluate` returns immediately with `m_Score = 0`.

### Utility threshold formula

```
base      = WeightsConfig.utilityThreshold    // +0x13C
multA     = StrategyData.modifiers.thresholdMultA   // +0x14 — one-directional raise only
multB     = StrategyData.modifiers.thresholdMultB   // +0x18 — bidirectional

scaled    = max(base, base * multA)
threshold = scaled * multB
```

`multA` can only raise the threshold (via `max`). `multB` is unconstrained — aggressive strategies lower it, defensive strategies raise it.

### The targeting value formula (SkillBehavior)

For all skill-based behaviours, `OnEvaluate` delegates to `GetTargetValue`, which computes:

```
hitChance    = ComputeHitProbability(...)  // [0, 100], normalised to [0.0, 1.0]
expectedKills = ComputeDamageData(...)    // DamageData.expectedKills
fVar27       = expectedDamage * 0.01     // normalised expected damage score
fVar30       = killPotential             // how completely this attack kills the target
fVar32       = proximityBonus / allyPressureBonus  // varies by _forImmediateUse

// Final assembly by goal type:
if goalType == 0 (attack):       total = fVar32 * 0.5 + fVar30 + fVar27
if goalType == 1 (assist-move):  total = (fVar30 + fVar27) * 0.5 + fVar32
if goalType == 2 (assist-skill): total = (fVar30 + fVar27) * 0.5 + fVar31
```

`ConsiderSkillSpecifics()` provides a multiplicative pre-factor:

```
armorMatchPenalty = 1.0 - clamp(TAG_ARMOR_MATCH.value, 0, 1.0)
ammoFactor        = (currentAmmo / maxAmmo) * 0.25 + 0.75   // range [0.75, 1.0]
multiplier        = armorMatchPenalty * ammoFactor
```

### The tag effectiveness formula

```
bonus = TagEffectivenessTable[tagIndex] * WeightsConfig.tagValueScale + 1.0
```

`tagValueScale` is replaced with `1.0` when `forImmediateUse == true`. The `+ 1.0` ensures a no-match returns 1.0 (neutral). A strong match returns ~2.0 (doubles the score).

### The attack final score formula

```
FinalScore = (int)(BestCandidateScore × TileUtilityMultiplier)

BestCandidateScore = max over all (originTile, targetTile) pairs of:
    Σ over shot candidates c:
        RawTargetValue(c)
        × ArcScaling(c)            // if shotGroupMode == 1
        / CandidateCount           // if shotGroupMode == 2 (AoE)
        × HPRatioScalar            // if origin ≠ actor.currentTile
        × FriendlyFirePenalty(c)   // if target is friendly tile
        × (1 - MoveCostFraction)   // if movement required
        + CoFireBonus(c)           // per ally with LoS to c

TileUtilityMultiplier =
    GetUtilityFromTileMult()
    × blend(AoEReadiness, 0.5)     // if IsAoeSkill
    × 1.1                          // if weapon is set up
    × 0.25                         // if delayed move and AP constrained
```

### The movement tile score formula (Move)

```
TileScore.movementScore =
    WeightsConfig.movementScoreWeight (+0x54)
    × (apCost / 20.0)
    × BehaviorWeights.movementWeight (+0x20)

fWeight = BehaviorWeights.weightScale × WeightsConfig.movementWeightScale (+0x12C)
          × (currentAP / maxAP)           // if not yet moved this turn
          × 0.9                           // if weapon not yet set up

FinalScore = (int)(fWeight × WeightsConfig.finalMovementScoreScale (+0x128))
```

### The deploy scoring model

Deploy uses a two-penalty model against `TileScore.rangeScore`:

```
// Penalty 1 — range distance
rangeScore -= WeightsConfig.rangePenaltyScale (+0xcc)
              × distanceResult × tileScore.secondaryMovementScore

// Penalty 2 — ally proximity spread
for each set-up ally within 6 tiles:
    rangeScore -= (6.0 - distance) × WeightsConfig.allyProximityPenaltyScale (+0xd0)
```

Deploy scores a fixed `1000` when it has an unvisited target tile; returns `0` once done.

---

## 5. The Full System Pipeline

```
Agent drives per-turn loop over all registered Behavior instances:

1.  OnBeforeProcessing()
        Called on every Collect AND every Evaluate call.
        Default: no-op. Subclasses override for per-call setup.

2.  Collect(actor)
        Deployment gate: if !m_IsUsedForDeploymentPhase AND roundCount == 0 → skip
        OnCollect(actor, agentTileDict)
            Subclasses populate/modify the shared tile dictionary.
            Default: returns false (no-op).

3.  Evaluate(actor)
        OnBeforeProcessing()
        Deployment gate (same as Collect)
        rawScore = OnEvaluate(actor)              ← subclass scoring formula
        m_Score  = clamp(rawScore, 0, 21474)
        if GetOrder() != 99999 AND 0 < m_Score < 5: m_Score = 5
        m_IsFirstEvaluated = m_IsFirstExecuted = true

4.  Agent ranks behaviours by m_Score.
    Applies GetUtilityThreshold() filter.
    GetOrder() resolves ties.
    Checks m_DontActuallyExecute before dispatching Execute.

5.  Execute(actor)
        OnExecute(actor)      ← state machine, returns bool (true=done)
        SkillBehavior state machine:
            Stage 1 — Rotate:   fire m_RotationSkill, wait 2.0s
            Stage 2 — Deploy:   fire m_DeployedStanceSkill, wait animDuration+0.1s
            Stage 3 — Setup:    fire m_SetupWeaponSkill, wait 3.0s
            Stage 4 — Fire:     wait m_WaitUntil, fire m_Skill on m_TargetTile
        m_IsFirstEvaluated = m_IsFirstExecuted = false

6.  OnNewTurn()  — called at turn boundary.
    OnReset()    — clears behaviour state.
    OnClear()    — called on agent destruction / round end.
```

### Attack/Assist collection sub-pipeline

```
Attack.OnCollect(actor, tileDict)
    Count allies in range → expand search radius if ≥3 allies
    2D grid search → populate m_PossibleOriginTiles, m_PossibleTargetTiles
    For each (origin, target) pair:
        Skill.QueryTargetTiles(skill, origin, target, candidates, immobileFlag)
            switch(shotGroupMode):
                0 → DirectFire: add targetTile directly
                1 → ArcFire:    probabilistic arc check; fallback to AoE builder
                2 → RadialAoE:  FUN_1806e1fb0 computes AoE tile set
                3 → IndirectFire: FUN_1806de1d0 trajectory builder
                4 → StoredGroup:  use pre-built list at Skill+0x60
                5 → TeamScan:     iterate allies, add living tile references
        After population: ShotCandidate_PostProcess(skill, candidates)

Attack.OnEvaluate(actor)
    Pre-flight guards (AP, weapon type, setup, readiness)
    ConsiderSkillSpecifics() → multiplier
    TileUtilityMultiplier = GetUtilityFromTileMult() [virtual, subclass-defined]
    AoE readiness blend (if IsAoeSkill)
    Iterate origin tiles → score per target via GetTargetValue dispatch (+vtable 0x248)
    Arc scaling (mode 1), AoE division (mode 2)
    Ally co-fire accumulation (HasAllyLineOfSight → CoFireBonus)
    +1.05 bonus for attacking from current position
    GetHighestScoredTarget() → (bestTarget, bestScore)
    AoE threshold gate (WeightsConfig +0xFC)
    AP clamping, secondary skill checks
    Movement score integration from tileDict
    Weapon setup bonus ×1.1, delayed-move penalty ×0.25
    return (int)(bestScore × TileUtilityMultiplier)
```

### Deploy lifecycle sub-pipeline

```
Deploy.OnCollect(actor, strategy)
    GUARD: strategyMode != 0 → return false
    Collect candidates of type 2 from ProximityData
    GUARD: no candidates → return false
    For each candidateOriginTile:
        FUN_1806343a0(entityInfo, tileCoords, pathList, ...) → fills pathList with TileScore entries
    For each tileScore in tileDict:
        Apply range distance penalty to tileScore.rangeScore
        For each set-up ally within 6 tiles: apply ally proximity penalty

Deploy.OnEvaluate(actor, strategy) → int
    GUARD: strategyMode != 0 → return 0
    GUARD: m_IsDone → return 0
    bestTile = GetHighestTileScore()
    IF bestTile.tile != actor.currentTile:
        self.m_TargetTile = bestTile.tile
        return 1000
    ELSE (already at best tile):
        agentContext.field_0x50 = 1   // signal deploy-complete
        m_IsDone = true
        return 0
```

---

## 6. Class: `Behavior`

**Namespace:** `Menace.Tactical.AI` | **TypeDefIndex:** 3623 | **Base:** none (abstract root)

This class defines the complete lifecycle interface for all tactical AI behaviours. It owns the score, the agent reference, and the deployment phase gate. All abstract methods resolve through the vtable; the concrete `Evaluate`, `Execute`, and `Collect` entry points are non-virtual wrappers that apply common logic before dispatching to abstract implementations.

### Fields

| Offset | Type | Name | Status | Notes |
|---|---|---|---|---|
| +0x10 | Agent* | m_Agent | confirmed | Owning AI agent. Set via SetAgent. |
| +0x18 | int | m_Score | confirmed | Utility score from last Evaluate. Clamped [0, 21474], floored at 5. |
| +0x1C | bool | m_IsFirstEvaluated | confirmed | Set true every Evaluate, cleared every Execute. "Evaluated since last execution." |
| +0x1D | bool | m_IsFirstExecuted | confirmed | Set in same 2-byte write as m_IsFirstEvaluated. Semantics identical. |
| +0x1E | bool | m_IsUsedForDeploymentPhase | confirmed | When false, behaviour is gated out during deployment phase (roundCount == 0). |

### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| Collect | 0x738D10 | 0x180738D10 | Fully analysed. Deployment gate + OnCollect dispatch. Tile dict at Agent+0x60. |
| Evaluate(Actor) | 0x738E60 | 0x180738E60 | Fully analysed. Score-writing entry point. Clamping, floor, gate. |
| Execute | 0x738F40 | 0x180738F40 | Fully analysed. Calls OnExecute, clears flags. |
| GetUtilityThreshold | 0x739050 | 0x180739050 | Fully analysed. Strategy-modulated float. |
| GetBehaviorWeights | 0x738FE0 | 0x180738FE0 | Fully analysed. Returns BehaviorWeights via Strategy+0x310. |
| GetBehaviorConfig2 | 0x739020 | 0x180739020 | Fully analysed. Returns BehaviorConfig2 via AgentContext+0x50. |
| GetID | — | — | Abstract, Slot 4. |
| GetOrder | — | — | Abstract, Slot 6. Returns execution priority. 99999 = opt-out of score floor. |
| OnBeforeProcessing | 0x4F7EE0 | 0x1804F7EE0 | Virtual, Slot 7. Default no-op (shared stub). |
| OnCollect(Actor, Dict) | 0x5128B0 | 0x1805128B0 | Virtual, Slot 8. Default returns false. |
| OnEvaluate(Actor, Dict) | 0x5128B0 | 0x1805128B0 | Virtual, Slot 9. Default returns false. |
| OnEvaluate(Actor) | — | — | Abstract, Slot 10. Returns int score. |
| OnExecute | — | — | Abstract, Slot 11. Returns bool (true=done). |
| OnNewTurn | 0x4F7EE0 | 0x1804F7EE0 | Virtual, Slot 12. Default no-op. |
| OnReset | — | — | Abstract, Slot 13. |
| OnClear | 0x4F7EE0 | 0x1804F7EE0 | Virtual, Slot 14. Default no-op. |
| IsDeploymentPhase | 0x71B670 | 0x18071B670 | Protected. Reads global round state. Not decompiled. |

### Behavioural notes

The no-op stub `0x4F7EE0` is shared among `OnBeforeProcessing`, `OnNewTurn`, `OnClear`, and when used as `OnReset` on stateless subclasses. `m_IsFirstEvaluated` and `m_IsFirstExecuted` are not "first-ever" flags — they are "evaluated since last execution" flags. Both are set on every `Evaluate` call and cleared on every `Execute`. `OnBeforeProcessing` fires on every `Collect` and every `Evaluate` call, not once per turn. The deployment phase gate reads `RoundManager + 0x60` (integer round count); when it is `0`, all non-deployment behaviours skip silently.

---

## 7. Class: `SkillBehavior`

**Namespace:** `Menace.Tactical.AI` | **TypeDefIndex:** 3627 | **Base:** `Behavior`

`SkillBehavior` is the abstract intermediary for all behaviours that activate a `Skill`. It adds a pre-execution sequencing system (rotate → deploy → setup) with AP-sufficiency checking, a timing wait mechanism, and the complete targeting value formula.

### Fields

| Offset | Type | Name | Status | Notes |
|---|---|---|---|---|
| +0x20 | Skill* | m_Skill | confirmed | Primary skill this behaviour executes. |
| +0x28 | int | m_SkillIDHash | confirmed | Cached hash of skill ID. |
| +0x30 | Skill* | m_DeployedStanceSkill | confirmed | Activated before main skill when m_DeployBeforeExecuting is true. |
| +0x38 | Skill* | m_RotationSkill | confirmed | Activated when m_RotateBeforeExecuting is true. |
| +0x40 | Skill* | m_SetupWeaponSkill | confirmed | Activated when m_SetupBeforeExecuting is true. |
| +0x48 | int | m_AdditionalRadius | inferred | Extra radius added to skill range. Note: param_1+0x48 in ComputeDamageData refers to the Skill object (Skill+0x48 = shot group list), not SkillBehavior. See NQ-6. |
| +0x4C | bool | m_IsRotationTowardsTargetRequired | confirmed | When true, rotation precedes execution. |
| +0x4D | bool | m_DeployBeforeExecuting | confirmed | Set by HandleDeployAndSetup. |
| +0x4E | bool | m_SetupBeforeExecuting | confirmed | Set by HandleDeployAndSetup. |
| +0x4F | bool | m_RotateBeforeExecuting | confirmed | Set by HandleDeployAndSetup. |
| +0x50 | bool | m_DontActuallyExecute | confirmed | Plans deploy/setup but does not fire this turn. Checked upstream; not read by OnExecute itself. |
| +0x51 | bool | m_IsExecuted | confirmed | Set after skill fires. Guards against double-execution. |
| +0x54 | float | m_WaitUntil | confirmed | Game-time timestamp. OnExecute returns false while Time.time < m_WaitUntil. |
| +0x58 | Tile* | m_TargetTile | confirmed | Chosen target tile for skill activation. |

All leaf subclasses begin their own fields at `+0x60`, confirming this layout exactly fills `0x20–0x5F`.

### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| OnExecute | 0x73E300 | 0x18073E300 | Fully analysed. Four-stage state machine. |
| HandleDeployAndSetup | 0x73DF70 | 0x18073DF70 | Fully analysed. AP-sufficiency decision; pre-execution flags. |
| GetTargetValue (public) | 0x73DD90 | 0x18073DD90 | Fully analysed. Routing wrapper; contained-entity double-pass. |
| GetTargetValue (private) | 0x73C130 | 0x18073C130 | Fully analysed. Full five-section targeting formula. |
| ConsiderSkillSpecifics | 0x73BDD0 | 0x18073BDD0 | Fully analysed. Armour-match + ammo-count penalty. |
| GetTagValueAgainst | 0x73BFA0 | 0x18073BFA0 | Fully analysed. Tag effectiveness multiplier. |

### Behavioural notes

`HandleDeployAndSetup` runs during Collect/Evaluate, not during Execute. By the time `OnExecute` is called, all pre-execution flags are already set. `m_DontActuallyExecute` is never read inside `OnExecute` — it is checked by the `Agent` before dispatching `Execute`. `GetTargetValue` (public) makes two calls to the private overload when the target tile contains a living entity — once for the container and once for the occupant with `_attackContainedEntity = true`. The `_forImmediateUse` parameter is a planning-mode switch: when `false`, scoring values future positioning; when `true`, it scores for execution now.

---

## 8. Class: `Move`

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3650 | **Base:** `Behavior` (not SkillBehavior)

`Move` is the only non-SkillBehavior in the combat-phase set. It uses a tile scoring model rather than the shot pipeline. It operates on a pre-populated tile dictionary and a list of candidate destinations.

### Fields

| Offset | Type | Name | Status | Notes |
|---|---|---|---|---|
| +0x020 | bool | m_IsMovementDone | confirmed | Early-out guard; set true on completion. |
| +0x021 | bool | m_HasMovedThisTurn | confirmed | Affects weight scaling. |
| +0x022 | bool | m_HasDelayedMovementThisTurn | confirmed | Set when marginal move penalty applied (×0.25). |
| +0x024 | bool | m_IsAllowedToPeekInAndOutOfCover | confirmed | Enables ×4.0 peek bonus in low-AP states. |
| +0x028 | TileScore* | m_TargetTile | confirmed | Chosen destination (TileScore). |
| +0x030 | Tile* | m_ReservedTile | confirmed | Tile whose entity is currently claimed. |
| +0x038 | int | m_TurnsBelowUtilityThreshold | confirmed | Counter: rounds below threshold. Incremented at most once per round. |
| +0x03C | int | m_TurnsBelowUtilityThresholdLastTurn | confirmed | Last round index when counter was incremented. |
| +0x040 | List\<TileScore\>* | m_Destinations | confirmed | Pre-scored candidate tiles from OnCollect. |
| +0x048 | List\<Vector3\>* | m_Path | confirmed | Primary movement path. |
| +0x050 | List\<Vector3\>* | m_AlternativePath | confirmed | Fallback path. |
| +0x058 | Skill* | m_DeployedStanceSkill | confirmed | AP cost subtracted if usable and prone. |
| +0x060 | Skill* | m_DefaultStanceSkill | confirmed | Triggers stanceSkillBonus if affordable. |
| +0x068 | Skill* | m_SetupWeaponSkill | confirmed | Weapon setup skill. |
| +0x070 | List\<Skill\>* | m_UseSkillBefore | confirmed | Skills activated before moving. Consumed in OnExecute Stage 1. |
| +0x078 | int | m_UseSkillBeforeIndex | confirmed | Current index into m_UseSkillBefore. |
| +0x080 | List\<Skill\>* | m_UseSkillAfter | confirmed | Skills activated after moving. Consumed in OnExecute Stage 3. |
| +0x088 | int | m_UseSkillAfterIndex | confirmed | Current index into m_UseSkillAfter. |
| +0x08C | bool | m_IsExecuted | confirmed | True after StartMove has been called. |
| +0x090 | float | m_WaitUntil | confirmed | Game-time threshold; movement triggers once Time.time exceeds this. |
| +0x094 | bool | m_IsInsideContainerAndInert | confirmed | Early-out guard. |
| +0x098 | Actor* | m_PreviousContainerActor | confirmed | Set in OnExecute Stage 0; used in Stage 4 container-exit logic. |

### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| OnEvaluate | 0x7635C0 | 0x1807635C0 | Fully analysed. Full scoring pipeline. ~1,500 lines raw. |
| OnExecute | 0x766370 | 0x180766370 | Fully analysed. Four-stage state machine. |
| GetHighestTileScore | 0x762EB0 | 0x180762EB0 | Fully analysed. Max-scan on composite score. |
| GetHighestTileScoreScaled | 0x762D60 | 0x180762D60 | Fully analysed. Identical to GetHighestTileScore. |
| GetAddedScoreForPath | 0x7629F0 | 0x1807629F0 | Fully analysed. Path quality float accumulator. |
| HasUtility | 0x7632F0 | 0x1807632F0 | Fully analysed. Forced/voluntary movement gate. |
| GetOrder | 0x546260 | 0x180546260 | Returns int. Not yet decompiled. |

### Behavioural notes

**Forced movement** is triggered when: (1) actor is prone (stance == 1), or (2) both `BehaviorConfig2.configFlagA` and `configFlagB` are set, or (3) `HasUtility()` returns false — no tile in the map meets the utility threshold. When forced, the minimum-improvement filter is bypassed. `GetHighestTileScoreScaled` and `GetHighestTileScore` are identical functions; the "Scaled" name describes the caller's intent (it has already applied multipliers), not any behaviour in the callee. The `m_TurnsBelowUtilityThreshold` counter increments at most once per round due to the `currentRound != lastTurn` guard.

The `OnExecute` state machine has four stages: Stage 0 re-routes entity claims; Stage 1 fires `m_UseSkillBefore` skills one per tick; Stage 2 waits for the timer then calls `Actor.StartMove(targetTile, flags)` with a bitmask encoding goal-entity, can-deploy, and is-peek; Stage 3 fires `m_UseSkillAfter` skills; Stage 4 handles container exit and fires `Skill.Activate`. When `m_PreviousContainerActor` is set, a container-exit event (`FUN_1819c8600`) is broadcast and `ContainerActor.Notify(1)` is called before completion.

---

## 9. Class: `Attack`

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3643 | **Base:** `SkillBehavior`

Manages the complete offensive scoring cycle. Owns geometry collection, candidate scoring, winner selection, and movement integration. Subclasses override `GetTargetValue` and `GetUtilityFromTileMult`.

### Fields

| Offset | Type | Name | Status | Notes |
|---|---|---|---|---|
| +0x60 | Goal | m_Goal | confirmed | Attack goal reference. |
| +0x68 | List\<Attack.Data\>* | m_Candidates | confirmed | All scored (tile, score) entries. |
| +0x70 | List\<Tile\>* | m_TargetTiles | confirmed | Shot-group source; iterated in OnEvaluate. |
| +0x78 | HashSet\<Tile\>* | m_PossibleOriginTiles | confirmed | Tiles actor can fire from. |
| +0x80 | HashSet\<Tile\>* | m_PossibleTargetTiles | confirmed | Tiles actor can fire at. |
| +0x88 | int | m_MinRangeToOpponents | confirmed | Minimum AP range; encodes reserved AP for range calc. |

**Attack.Data fields:**

| Offset | Type | Name | Status |
|---|---|---|---|
| +0x00 | Tile* | targetTile | confirmed |
| +0x30 | float | secondaryScore | confirmed |
| +0x3C | float | primaryScore | confirmed — argmax in GetHighestScoredTarget |
| +0x44 | int | apCost | confirmed |

### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| OnCollect | 0x734130 | 0x180734130 | Fully analysed. Geometry search + candidate population. |
| OnEvaluate | 0x735D20 | 0x180735D20 | Fully analysed. Per-tile shot scoring. |
| GetHighestScoredTarget | 0x733650 | 0x180733650 | Fully analysed. Argmax over m_Candidates. |
| HasAllyLineOfSight | 0x733890 | 0x180733890 | Fully analysed. Team LoS check for co-fire gate. |
| GetOrder | 0x50C760 | 0x18050C760 | Shared with Assist. Returns order constant. Not decompiled. |

### Behavioural notes

`OnCollect` counts allies within `WeightsConfig+0xC8` range. If 3+ allies are in range, the tile search radius expands. The vehicle/turret branch is triggered when `EntityInfo.flags bit 0` (isImmobile) is set and `m_MinRangeToOpponents > 0`. `HasAllyLineOfSight` skips allies that are dead (`Actor+0x162 != 0`), skips self, and skips actors in `strategyMode == 1` (no-co-fire strategy setting at `Strategy+0x8C`).

---

## 10. Class: `Assist`

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3641 | **Base:** `SkillBehavior`

Mirrors the Attack pipeline but operates on ally tiles rather than enemy tiles. `isCoFire` is always `1` in all scoring calls. Uses the 5-arg GetTargetValue dispatch (`FUN_18000dcd0`) instead of the 7-arg version.

### Fields

| Offset | Type | Name | Status | Notes |
|---|---|---|---|---|
| +0x60 | List\<Assist.Data\>* | m_Candidates | confirmed | Scored ally entries. |
| +0x68 | List\<Tile\>* | m_TargetTiles | confirmed | |
| +0x70 | HashSet\<Tile\>* | m_PossibleOriginTiles | confirmed | Tiles actor can cast from toward an ally. |
| +0x78 | HashSet\<Tile\>* | m_PossibleTargetTiles | confirmed | Ally tiles reachable by the skill. |

**Assist.Data fields:**

| Offset | Type | Name | Status |
|---|---|---|---|
| +0x00 | Actor*/Tile* | targetRef | confirmed |
| +0x30 | float | score | confirmed |
| +0x44 | int | apCost | confirmed |

### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| OnCollect | 0x730B30 | 0x180730B30 | Fully analysed. |
| OnEvaluate | 0x731C60 | 0x180731C60 | Fully analysed. |
| GetHighestScoredTarget | 0x7308F0 | 0x1807308F0 | Fully analysed. |

### Behavioural notes

When `FUN_1806e3af0(skill)` returns false (self-cast skill), only the actor's own current tile is added to `m_PossibleOriginTiles`. No `+0x4F` (reposition flag) is ever set for Assist.

---

## 11. Class: `Deploy`

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3645 | **Base:** `Behavior` (direct, not SkillBehavior)

Positions a unit on the optimal deploy tile before a weapon or stance is activated. Binary lifecycle: find tile → move there → done. Scores a fixed `1000` while active.

### Fields

| Offset | Type | Name | Status | Notes |
|---|---|---|---|---|
| +0x010 | AgentContext* | agentContext | confirmed | Inherited from Behavior. |
| +0x01C | bool | field_0x1c | confirmed | Base Behavior "target set" flag. |
| +0x020 | Tile* | m_TargetTile | confirmed | Chosen deploy destination. |
| +0x028 | bool | m_IsDone | confirmed | Set true after actor reaches target tile. |

### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetHighestTileScore | 0x73A0C0 | 0x18073A0C0 | Fully analysed. Max composite score over tileDict. |
| OnCollect | 0x73A260 | 0x18073A260 | Fully analysed. Candidate collection + two-factor scoring. |
| OnEvaluate | 0x73AD00 | 0x18073AD00 | Fully analysed. Fixed-priority 1000; done-state management. |
| OnExecute | 0x73ADD0 | 0x18073ADD0 | Fully analysed. Issues move command; marks done. |
| GetOrder | 0x519A90 | 0x180519A90 | Confirmed returns 0. Shared with Idle. |
| OnReset | 0x71E0E0 | 0x18071E0E0 | Not analysed. |

### Behavioural notes

Deploy has a hardcoded priority of 1000, which means it always wins over lower-scored combat behaviours when the unit is not yet in position. The system relies on `m_IsDone` to prevent re-evaluation. The ally proximity penalty only applies to allies where `Actor+0x50 != 0` (the "set up" state), preventing the penalty from pushing units away from still-mobile allies. Both `OnEvaluate` and `OnExecute` write byte value `1` to `agentContext + 0x50` — see NQ-42 for the unresolved label conflict at this offset.

---

## 12. Concrete Scoring Subclasses

### 12.1 InflictDamage

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3647 | **Base:** Attack

A thin prepend-and-delegate. The entire scoring formula lives in `SkillBehavior.GetTargetValue`. The only role of this override is to compute and inject `tagValue` for co-fire shots.

```
if isCoFire == false:
    tagValue = 0
else:
    weaponRef = self->agentContext->entityInfo->field_0x18
    tagValue  = weaponRef->vtable[0x458](weaponRef)      // GetTagIndex (NQ-21)
    tagValue  = TagEffectiveness_Apply(weaponData, tagValue, 0)
SkillBehavior_GetTargetValue(self, isCoFire, tagValue, ..., skillEffectType=1, ...)
```

`tagValueScale` (+0xBC) has zero influence on solo attacks by architectural design — `tagValue` is forced to 0 when `isCoFire == false`.

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x73AF00 | 0x18073AF00 |
| GetUtilityFromTileMult | 0x73AFE0 | 0x18073AFE0 — returns WeightsConfig+0x10C |

### 12.2 InflictSuppression

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3648 | **Base:** Attack

Byte-for-byte structurally identical to InflictDamage. The only differences: `GetUtilityFromTileMult` returns `WeightsConfig+0x118` (vs `+0x10C`), and `skillEffectType = 1` (same value — the distinction between InflictDamage and InflictSuppression at the base scorer level is presently NQ-37).

Additional field:

| Offset | Field | Type | Status |
|---|---|---|---|
| +0x090 | m_Name | string | confirmed |

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x73B240 | 0x18073B240 |
| GetUtilityFromTileMult | 0x73B320 | 0x18073B320 |

### 12.3 Stun

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3667 | **Base:** Attack

Structurally identical to InflictSuppression except passes `skillEffectType = 2` to the base scorer.

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x769B40 | 0x180769B40 |

### 12.4 Mindray

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3657 | **Base:** Attack

Two-path dispatch on an EntityInfo flag. Uses `GetResistanceFraction(target)` as a primary gate — target must have resistance > 0. Checks `EntityInfo.flags bit 7` (skip entirely) and `EntityInfo+0xA8 & 0x100` (vulnerability flag → `effectType = 1`). Non-vulnerable targets use `effectType = 0`.

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x762550 | 0x180762550 |

### 12.5 Buff

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3644 | **Base:** Assist

Six-branch additive flag-driven scorer. Contributions accumulate independently.

**Flag bits in `buffSkill->flags` (+0x18):**

| Bit | Mask | Branch |
|---|---|---|
| 0 | 0x0001 | Heal |
| 1 | 0x0002 | Status buff |
| 15 | 0x8000 | Suppress / debuff resistance |
| 16 | 0x10000 | Setup / stance assist |
| 17 | 0x20000 | AoE heal |
| 18 | 0x40000 | AoE buff |

**Complete formula:**

```
total = 0.0

if HEAL (bit 0):
    total += healScoringWeight (+0x17C) * healAmount
              [× 0.5 if immobile and no status buff]
              [× 1.1 if not incapacitated]

if STATUS_BUFF (bit 1):
    total += buffScoringWeight (+0x180)
              [× 0.1 if buffType==2 and no heal]
              [× 1.5 if not incapacitated]

if SUPPRESS (bit 15):
    total += (1 - resistFrac) * suppressScoringWeight (+0x184)
              [× 2.0 if score>0 and slotVal==1]
              [× 0.5 if immobile and no status buff]
              [× 0.9 if buffType==2 and no heal]
              [× 1.5 if not incapacitated]

if AOE_HEAL (bit 17):
    total += aoeHealScoringWeight (+0x190) * Σ(perMemberHealValue over team tiles)

if AOE_BUFF (bit 18):
    aoeSum = Σ(aoeBuffScoringWeight (+0x18C) * perMemberBuffValue)
    [× 1.2 if not incapacitated]
    total += aoeSum

if SETUP (bit 16):
    score = setupAssistScoringWeight (+0x188)  [or 0 if conditions not met]
    [× 0.75 if Actor+0xD0 == 1]
    [× 0.75 if isWeaponSetUp]
    [× 1.1 if not incapacitated]
    [× proximity modifiers per entry]
    [× powf(1.25) if stack count > 0]
    total += score

return actor->buffDataBlock->contextScale * total * buffGlobalScoringScale (+0x174)
```

Guards (all must pass or return 0.0): `entityInfo->weaponData` non-null; target resolves to Actor; `actor->buffDataBlock` (+0xC8) non-null; `CanApplyBuff()` returns true.

`buffType == 2` is a suppression-of-redundancy guard — detected in the Status Buff branch to reduce weight by 90% and in Suppress to reduce by 10%, preventing double-scoring units already in a suppressed state.

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x7391C0 | 0x1807391C0 |
| GetUtilityFromTileMult | 0x739F80 | 0x180739F80 |

### 12.6 SupplyAmmo

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3664 | **Base:** Assist

The most complex scorer in the investigation. HP-fraction blend applied after all multipliers.

```
score = utilityThreshold / behaviorScale
if weapon not setup or wrong type: score = 0
if coFire eligible and target is mobile non-setup: score *= 1.25
for each ally tile (AoE zones 0, 1, 2):
    if AoE_PerMemberScorer hits and score > WeightsConfig.aoeAllyBonusThreshold (+0x1A4):
        score *= 1.05   // stacks up to 3×
if target->Actor+0xD0 != 0: score *= 1.1    // has secondary weapon
if target->isWeaponSetUp:   score *= 1.1
score = score * 0.8 + score * 0.2 * GetHPFraction(target)
return score * target->buffDataBlock->contextScale
```

Counter-intuitively, higher HP targets score slightly higher — SupplyAmmo prefers targets that are healthy and can make better use of the ammo.

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x769E60 | 0x180769E60 |

### 12.7 TargetDesignator

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3665 | **Base:** Attack

Float scorer via two independent loops. Checks `EntityInfo.flags bit 11` — already-designated targets return 0.0.

```
score = 0
for each observer in agentContext->behaviorConfig->field_0x28:
    score += (IsInDesignationZone(observer, context) ? 0.5 : 0.25)
for each tile in agentContext->field_0x20:
    dist = GetDistanceTo(tile->pos, context)
    if 0 < dist < 11: score += (1.0 - dist / 10.0)
return score * proximityEntry->weight (+0x88)
```

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x76A640 | 0x18076A640 |

### 12.8 SpawnPhantom

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3661 | **Base:** Attack

Void eligibility scorer. Filters on `EntityInfo.flags bit 5` (isPhantom — excluded) and `EntityInfo+0xDC > 0` (detection value required). Range bounds from weapon config object.

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x769450 | 0x180769450 |

### 12.9 SpawnHovermine

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3660 | **Base:** Attack

Void weighted proximity scorer. Three range tiers with multipliers 1.5 / 1.25 / 1.0. Weapon-setup bonus ×1.25. No-ally-on-tile penalty ×0.25.

```
score = 0
for each ally tile in entityInfo->tileList:
    dist = GetDistanceTo(ally->pos, target)
    if dist <= maxRange:
        base = maxRange - dist + 1
        if dist <= idealRange: base *= 1.5
        elif dist <= midRange: base *= 1.25
        if ally->isWeaponSetUp: base *= 1.25
        if !TileHasAlly(tile):  base *= 0.25
        score += base * tile->field_0x88
RegisterCandidate(context, tile, score)
```

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x768EF0 | 0x180768EF0 |

### 12.10 CreateLOSBlocker

**Namespace:** `Menace.Tactical.AI.Behaviors` | **TypeDefIndex:** 3655 | **Base:** Assist

Void geometry-aware LOS line scorer. Only proceeds when `PlacementCandidate->losImpact < 0` — the blocker must degrade opponent LOS.

```
for each blockerCandidate in self->blockerCandidateList:
    for each ally tile in entityInfo->tileList:
        if !isTeamMember || !TileHasAlly || isImmobile || state==1: skip
        aoeBase = AoE_PerMemberScorer(tile->aoeTierTable, blocker)
        if aoeBase == 0: skip
        dist = GetDistanceTo(ally->pos, blocker->tile)
        if dist > range->maxDist AND BlockerOnLOSLine AND dist3D <= 5.656854:
            stackMult = (buffStackCount - 1) * 0.25 + 1.0
            contribution = stackMult * aoeBase - (zone0 + zone1 + zone2)
            if contribution > 0 AND ally->isWeaponSetUp: contribution *= 0.8
            tileScore += contribution
    if tileScore > 0: tileScore *= candidateWeight
    totalScore += tileScore
```

The geometry threshold `5.656854 = 4√2` is the diagonal of a 4×4 tile square — the maximum distance a point can be from a line while considered "on" it. The AoE coverage subtraction `stackMult * aoeBase - (z0 + z1 + z2)` is an anti-redundancy mechanism: if existing AoE zone coverage already equals the base value, the blocker contributes nothing. Weapon-setup allies penalised ×0.8 — they are committed and less able to reposition to exploit the blocker.

| Offset | Field | Type | Status |
|---|---|---|---|
| +0x60 | placementEvaluator | PlacementEvaluator* | confirmed |
| +0x88 | blockerCandidateList | List\<BlockerCandidate\>* | confirmed |

| Method | RVA | VA |
|---|---|---|
| GetTargetValue | 0x75EB90 | 0x18075EB90 |

---

## 13. Supporting Utility Functions

### 13.1 ComputeHitProbability — VA `0x1806E0AC0`

Returns `float[6]` written in-place. Standalone utility, not a class member.

| Index | Name | Meaning |
|---|---|---|
| [0] | hitChance | Final hit probability [0, 100]. Floored by `shotPath->minimumHitChance (+0x78)`. |
| [1] | baseAccuracy | Raw weapon accuracy. |
| [2] | coverDefense | Target cover defense (integer, float-cast). |
| [3] | rangeMult | Range-based hit multiplier (1.0 when no target). |
| [4] | autoHitFlag | Set when `SkillData+0xF3 != 0`. When set, hitChance = 100.0 and function returns early. |
| [5] | rangeDistancePenalty | `abs(rangeDeviation) * rangeAccuracyCost`. Only set when `useRange = true`. |

A byte flag at array offset `+0x11` (byte 17, inside float slot [4]) is set to 1 to signal "range calculation was active" — a separate flag from autoHitFlag.

### 13.2 ComputeDamageData — VA `0x1806DF4E0`

Builds and returns a `DamageData` object. Allocates one if `param_9` is null. `param_1` is the `Skill*` object (not `SkillBehavior*`).

**DamageData fields:**

| Offset | Type | Name | Meaning |
|---|---|---|---|
| +0x10 | float | expectedRawDamage | Accumulated expected raw damage across all shot groups. |
| +0x14 | float | expectedEffectiveDamage | Effective damage blended across cover/armour, capped to target HP fraction. |
| +0x18 | float | expectedKills | HP-normalised kill count, capped to max ammo. |
| +0x20 | float | coverPenetrationChance | `clamp((100 - (accuracy * coverStrength - rangePenalty) * 3) * 0.01, 0, 1)`. Max across shot groups. |
| +0x24 | bool | canKillInOneShot | True when `maxAmmo <= expectedKills`. OR'd across groups. |
| +0x25 | bool | canKillWithFullMag | True when full magazine expected to be lethal. |
| +0x28 | Skill* | shotData | ShotData reference. Write-barriered. |

**ShotPath fields accessed:**

| Offset | Name | Used for |
|---|---|---|
| +0x78 | minimumHitChance | Floor for hitChance. |
| +0x8C | accuracyMult | Multiplied into main hit formula. |
| +0x110 | altDistancePenaltyCoeff | Per-tile alternate range penalty. |
| +0x128 | movementAccuracyPenaltyPerTile | Per-tile movement penalty. |
| +0x13C | thirdDistanceModifier | Third additive range modifier. |
| +0x140 | overallAccuracyMultiplier | Applied to entire formula. |
| +0x144 | hpAccuracyCoeff | Scales target HP into accuracy floor. |
| +0x148 | hpAccuracyFloor | Minimum accuracy from HP scaling. |
| +0x14C | apAccuracyCoeff | Scales target AP into accuracy floor. |
| +0x150 | apAccuracyFloor | Minimum accuracy from AP scaling. |
| +0x16C | baseExtraHits | Added to burst group hit count. |
| +0x170 | burstFraction | Proportion of magazine fired per shot group. |

### 13.3 TagEffectiveness_Apply — VA `0x1806E2710`

```
uint TagEffectiveness_Apply(weaponData, tagIndex, 0):
    cap       = max(1, weaponData->tagApplicationCap)     // +0xA8
    tierCount = GetTagTierCount(weaponData, 0)             // FUN_1806ddec0
    result    = min(cap, tagIndex / tierCount)
    for each modifier in weaponData->tagModifiers (+0x48):
        result = min(result, modifier->GetValue(1))
    return result
```

### 13.4 AoE_PerMemberScorer — VA `0x181430AC0`

Tier-table lookup with early-out on negative tier.

```
AoeTierEntry* entry = GetAoETierForMember(aoeTierTable, member)   // FUN_181423600
if entry == null OR entry->tier < 0: return 0, false
score = aoeTierTable->entries[entry->tier].score    // +0x20 + (n×0x18)
return score, true
```

**AoETierTable fields:**

| Offset | Field | Type | Status |
|---|---|---|---|
| +0x18 | count | int | confirmed |
| +0x20 + (n×0x18) | entries[n] | AoETierEntry (24 bytes) | confirmed |
| entry+0x00 | score | float | confirmed |

### 13.5 CanApplyBuff — VA `0x1806E33A0`

All-conditions-must-pass gate over `BuffSkill.conditions` list (+0x48). Iterates each `Condition` and calls its `Evaluate` vtable slot (+0x1D8). Returns false on the first failure; true only if all conditions pass. Concrete `Condition.Evaluate` subclasses are deferred (NQ-36).

### 13.6 ShotPath_ActorCast — VA `0x1806D5040`

Safe `Actor` cast on `ShotPath+0x30` (the `targetActor` field). Reads the pointer, validates it is an `Actor` instance. Returns the Actor pointer or null.

### 13.7 Skill.QueryTargetTiles — VA `0x1806E66F0`

Six-mode dispatcher resolving `EntityInfo+0x178` (shotGroupMode):

| Mode | Name | Behaviour |
|---|---|---|
| 0 | DirectFire | Add targetTile directly |
| 1 | ArcFire | `rand(1,100)` vs `EntityInfo+0x18C`; fallback to AoE builder on miss |
| 2 | RadialAoE | `FUN_1806e1fb0` computes AoE tile set |
| 3 | IndirectFire | `FUN_1806de1d0` trajectory builder |
| 4 | StoredGroup | Use pre-built list at `Skill+0x60` (m_SelectedTiles) |
| 5 | TeamScan | Iterate allies; add living non-dead ally tiles |

After population, calls `ShotCandidate_PostProcess(skill, candidates)`.

### 13.8 ShotCandidate_PostProcess — VA `0x1806DA770`

Packages a validated `ShotPath` into a keyed, sorted container. Not a scorer.

```
entry = new(ShotCandidateWrapper)
entry->shotPath (+0x10) = param_1
if param_1->field_0x10->field_0x180 != NULL:   // trajectory/arc block must exist
    entry->targetActor (+0x18) = ShotPath_ActorCast(param_1)
    container = new(sorted container)
    insert(container, entry, comparatorKey)
    if param_2 != NULL: append(param_2, container)
else:
    NullReferenceException
```

Shots without a trajectory block are silently dropped.

---

## 14. Supporting Data Classes

### 14.1 ProximityData / ProximityEntry

`ProximityData` holds a list of `ProximityEntry` objects, each tracking a tile, its type, and a `readyRound`. Used in the ally-pressure bonus at the end of `GetTargetValue` (private) and in Deploy candidate collection.

**ProximityData fields:**

| Offset | Type | Name | Status |
|---|---|---|---|
| +0x48 | List\<ProximityEntry\>* | entries | confirmed |

**ProximityEntry fields:**

| Offset | Type | Name | Status | Notes |
|---|---|---|---|---|
| +0x10 | Tile* | tile | confirmed | Matched in FindEntryForTile (linear scan). |
| +0x18 | int | readyRound | confirmed | -1 = unassigned. ≥0 = assigned to round index. |
| +0x34 | int | type | confirmed | 0/1 = valid for pressure bonus. 2+ = excluded. |
| +0x88 | float | weight | confirmed | Used in TargetDesignator scoring. |

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| FindEntryForTile | 0x717730 | 0x180717730 | Linear scan by tile pointer equality. |
| IsValidType | 0x717A40 | 0x180717A40 | Returns true for type 0 or 1 only. |
| HasReadyEntry | 0x717870 | 0x180717870 | Returns true if any entry has readyRound ≥ 0. |

### 14.2 TileScore

The core data structure for movement and deploy scoring. Each `TileScore` represents a candidate destination with computed scores, AP cost, path links, and metadata flags. Stored in `m_Destinations` (Move) and in the agent's tile dictionary.

| Offset | Type | Name | Status | Notes |
|---|---|---|---|---|
| +0x10 | Tile* | tile | confirmed | |
| +0x18 | Entity* | entity | confirmed | Entity at this tile. |
| +0x20 | float | movementScore | confirmed | Primary computed score. |
| +0x24 | float | secondaryMovementScore | confirmed | Written in secondary look-ahead path. |
| +0x28 | float | exposureScore | confirmed | |
| +0x2C | float | rangeScore | confirmed | Modified by Deploy penalties. |
| +0x30 | float | utilityScore | confirmed | Threshold comparisons, reserved tile scaling. |
| +0x34 | float | coverScore | confirmed | |
| +0x38 | float | movementScore (alt) | confirmed | |
| +0x3C | float | secondaryMovementScore (alt) | confirmed | |
| +0x40 | int | apCost | confirmed | Path cost in AP. 0 = not yet scored. |
| +0x44 | int | chainCost | confirmed | AP cost for chained subsequent tile. |
| +0x48 | TileScore* | destinationRef | inferred | Forward reference to target destination. |
| +0x50 | TileScore* | prevTileRef | inferred | Previous tile in path chain. |
| +0x58 | TileScore* | nextTileRef | inferred | Next tile in path chain. |
| +0x60 | bool | isForward | inferred | Direction flag; true = forward chain. |
| +0x61 | bool | isPeek | confirmed | True = peek-in-cover move. Written to StartMove flags bit 2. |
| +0x62 | byte | stance | confirmed | Stance to adopt on arrival. |

**Methods accessed by call site:**

| Method | Address | Notes |
|---|---|---|
| GetScore | FUN_180740f20 | Used in GetHighestTileScore. Full signature not yet analysed (NQ-41). |
| GetCompositeScore | FUN_180740e50 | Used in competitor comparisons. |

### 14.3 BehaviorWeights / BehaviorConfig2

Two configuration objects accessed via the agent chain; neither appears as a named class in dump.cs.

**Access paths:**
```
BehaviorWeights:  self->agent (+0x10) -> actor (+0x18) -> GetStrategy() -> strategy->behaviorWeights (+0x310)
BehaviorConfig2:  self->agent (+0x10) -> agentContext (+0x10) -> behaviorConfig/flag (+0x50)   [NQ-42 conflict]
```

**BehaviorWeights fields (via Strategy+0x310):**

| Offset | Type | Name | Status |
|---|---|---|---|
| +0x14 | float | movementWeightMultiplier | confirmed |
| +0x20 | float | movementWeight | confirmed |
| +0x24 | float | weightScale | confirmed |
| +0x2C | float | weightScale2 | confirmed |

**BehaviorConfig2 fields (via AgentContext+0x50 — NQ-42: label may be wrong):**

| Offset | Type | Name | Status |
|---|---|---|---|
| +0x28 | bool | configFlagA | confirmed — part of forced-movement condition |
| +0x34 | bool | configFlagB | confirmed — part of forced-movement condition |

### 14.4 TagEffectivenessTable

Singleton static. A `float[]` indexed by tag match result. Accessed only from `GetTagValueAgainst`.

| Offset | Type | Name | Status |
|---|---|---|---|
| +0x18 | int | length | confirmed — bounds-checked before access |
| +0x20 | float[] | values | confirmed — stride 4, indexed by uint from TagMatcher |

---

## 15. Configuration Classes

### 15.1 WeightsConfig

**IL2CPP class name: UNRESOLVED** — accessed via `*(*(DAT_18394c3d0 + 0xb8) + 8)`. Investigation-internal name. All field offsets confirmed from Ghidra access; field names are inferred from usage context unless otherwise noted.

| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x54 | movementScoreWeight | float | confirmed |
| +0x78 | [scoring weight] | float | inferred — name unresolved (NQ-4) |
| +0x7C | allyCoFireBonus | float | inferred |
| +0xBC | tagValueScale | float | confirmed |
| +0xC0 | baseAttackWeightScale | float | confirmed |
| +0xC4 | maxApproachRange | int | confirmed |
| +0xC8 | allyInRangeMaxDist | int | confirmed |
| +0xCC | rangePenaltyScale | float | confirmed — Deploy.OnCollect |
| +0xD0 | allyProximityPenaltyScale | float | confirmed — Deploy.OnCollect |
| +0xE0 | friendlyFirePenaltyWeight | float | confirmed |
| +0xE4 | killWeight | float | confirmed |
| +0xE8 | killWeight2 | float | confirmed |
| +0xEC | urgencyWeight | float | confirmed |
| +0xF0 | buffWeight / allyCoFireWeight | float | confirmed |
| +0xF8 | proximityBonusCap | float | confirmed |
| +0xFC | minAoeScoreThreshold | float | confirmed |
| +0x100 | allyCoFireBonusScale | float | confirmed |
| +0x10C | utilityFromTileMultiplier | float | confirmed — InflictDamage |
| +0x118 | suppressionTileMultiplier | float | confirmed — InflictSuppression |
| +0x128 | finalMovementScoreScale | float | confirmed |
| +0x12C | movementWeightScale | float | confirmed |
| +0x13C | utilityThreshold | float | confirmed |
| +0x148 | movementScorePathWeight | float | inferred (NQ-4) |
| +0x14C | pathCostPenaltyWeight | float | inferred (NQ-5) |
| +0x150 | minimumImprovementRatio | float | confirmed |
| +0x154 | deployMovementScoreThreshold | float | confirmed |
| +0x15C | secondaryPathPenalty | float | confirmed |
| +0x168 | shortRangePenalty | float | confirmed |
| +0x16C | stanceSkillBonus | float | confirmed |
| +0x174 | buffGlobalScoringScale | float | confirmed |
| +0x17C | healScoringWeight | float | confirmed |
| +0x180 | buffScoringWeight | float | confirmed |
| +0x184 | suppressScoringWeight | float | confirmed |
| +0x188 | setupAssistScoringWeight | float | confirmed |
| +0x18C | aoeBuffScoringWeight | float | confirmed |
| +0x190 | aoeHealScoringWeight | float | confirmed |
| +0x1A4 | aoeAllyBonusThreshold | float | confirmed — SupplyAmmo |

### 15.2 Strategy / StrategyData

**Strategy IL2CPP class name: UNRESOLVED** — accessed via `*(DAT_183981f50 + 0xb8)`.

**Strategy fields:**

| Offset | Field | Type | Status | Notes |
|---|---|---|---|---|
| +0x28 | strategyDataSubRef | ptr | confirmed | Accessed in Deploy.OnCollect |
| +0x60 | strategyMode | int | confirmed | Non-zero = suppress behaviours |
| +0x8C | strategyMode (alt) | int | inferred | Value 1 = no co-fire allowed (NQ-16) |
| +0x2B0 | strategyData | StrategyData* | confirmed | |
| +0x310 | behaviorWeights | BehaviorWeights* | confirmed | |

**StrategyData fields (IL2CPP class name UNRESOLVED):**

| Offset | Field | Type | Status |
|---|---|---|---|
| +0x14 | thresholdMultA | float | confirmed — one-directional threshold raise |
| +0x18 | thresholdMultB | float | confirmed — bidirectional threshold modifier |
| +0x60 | tierMode | int | inferred |
| +0x118 | reservedAP | int | confirmed |

### 15.3 AgentContext / EntityInfo

**AgentContext IL2CPP class name: UNRESOLVED** — held at `Behavior+0x10`.

**AgentContext fields:**

| Offset | Field | Type | Status | Notes |
|---|---|---|---|---|
| +0x10 | entityInfo | EntityInfo* | confirmed | |
| +0x50 | behaviorConfig OR deployCompleteFlag | BehaviorConfig2* OR byte | CONFLICTED — NQ-42 | Deploy.OnCollect reads it as a pointer; Deploy.OnEvaluate/OnExecute write byte 1 to it directly. |

**EntityInfo IL2CPP class name: UNRESOLVED** — held at `AgentContext+0x10`.

| Offset | Field | Type | Status | Notes |
|---|---|---|---|---|
| +0x14 | isActive / teamID | bool/int | confirmed | |
| +0x18 | weaponTagObject | ptr | inferred — NQ-19 | Dereferenced for weapon tag lookup. |
| +0x20 | teamMembers | List\<Actor\>* | confirmed | |
| +0x3C | minimumAP | int | confirmed | |
| +0x48 | tileList | List\<Tile\>* | confirmed | |
| +0xA8 | statusFlags2 | uint | confirmed | Bit 0x100 = mindrayVulnerable (NQ-38) |
| +0xDC | detectionValue | float | inferred — SpawnPhantom | |
| +0xEC | flags | uint | confirmed | Bit 0=immobile, bit 5=isPhantom, bit 7=skipMindray, bit 11=alreadyDesignated (NQ-39) |
| +0x112 | hasSecondaryWeapon | bool | confirmed | |
| +0x113 | hasSetupWeapon | bool | confirmed | |
| +0x178 | shotGroupMode | int enum (0–5) | confirmed | |
| +0x18C | arcCoveragePercent | int (0–100) | confirmed | |
| +0x1A1 | isArcFixed | bool | confirmed | |
| +0x2C8 | weaponData | ptr | confirmed | |

**Actor partial fields (confirmed across all stages):**

| Offset | Field | Type | Status | Notes |
|---|---|---|---|---|
| +0x50 | isSetUp_alt | bool | confirmed | Deploy.OnCollect ally proximity check. Distinct from +0x15C. |
| +0x54 | currentHP | int | confirmed | |
| +0x5C | currentHP alt | int | confirmed | |
| +0xC8 | buffDataBlock | ptr | inferred | +0x34 = contextScale float; +0x38 = stackCount int |
| +0xD0 | secondaryWeaponState | int | inferred | Checked != 0 in SupplyAmmo and Buff setup branch |
| +0x15C | isWeaponSetUp | bool | confirmed | |
| +0x15F | field_0x15F | bool | confirmed | Deploy.OnExecute return value |
| +0x162 | isDead | bool | confirmed | |
| +0x167 | isWeaponSetUp (alt) | bool | confirmed | |

---

## 16. Ghidra Address Reference

### Fully Analysed — All Functions

| VA | Method | Class |
|---|---|---|
| 0x180738E60 | Evaluate(Actor) | Behavior |
| 0x180738F40 | Execute(Actor) | Behavior |
| 0x180739050 | GetUtilityThreshold | Behavior |
| 0x180738D10 | Collect | Behavior |
| 0x180738FE0 | GetBehaviorWeights | Behavior |
| 0x180739020 | GetBehaviorConfig2 | Behavior |
| 0x18073E300 | OnExecute | SkillBehavior |
| 0x18073DF70 | HandleDeployAndSetup | SkillBehavior |
| 0x18073DD90 | GetTargetValue (public) | SkillBehavior |
| 0x18073C130 | GetTargetValue (private) | SkillBehavior |
| 0x18073BDD0 | ConsiderSkillSpecifics | SkillBehavior |
| 0x18073BFA0 | GetTagValueAgainst | SkillBehavior |
| 0x1806E0AC0 | ComputeHitProbability | (utility) |
| 0x1806DF4E0 | ComputeDamageData | (utility) |
| 0x180717730 | FindEntryForTile | ProximityData |
| 0x180717A40 | IsValidType | ProximityEntry |
| 0x180717870 | HasReadyEntry | ProximityData |
| 0x180519A90 | GetOrder (returns 0) | Deploy / Idle |
| 0x1807632F0 | HasUtility | Move |
| 0x1807629F0 | GetAddedScoreForPath | Move |
| 0x180762EB0 | GetHighestTileScore | Move |
| 0x180762D60 | GetHighestTileScoreScaled | Move |
| 0x1807635C0 | OnEvaluate | Move |
| 0x180766370 | OnExecute | Move |
| 0x180735D20 | OnEvaluate | Attack |
| 0x180734130 | OnCollect | Attack |
| 0x180733650 | GetHighestScoredTarget | Attack |
| 0x180733890 | HasAllyLineOfSight | Attack |
| 0x18000DD30 | GetTargetValue dispatch shim (7-arg) | (utility) |
| 0x1806E66F0 | QueryTargetTiles | Skill |
| 0x180731C60 | OnEvaluate | Assist |
| 0x180730B30 | OnCollect | Assist |
| 0x1807308F0 | GetHighestScoredTarget | Assist |
| 0x18073AF00 | GetTargetValue | InflictDamage |
| 0x18073AFE0 | GetUtilityFromTileMult | InflictDamage |
| 0x1807391C0 | GetTargetValue | Buff |
| 0x1806DA770 | ShotCandidate_PostProcess | (utility) |
| 0x1806E2710 | TagEffectiveness_Apply | (utility) |
| 0x181430AC0 | AoE_PerMemberScorer | (utility) |
| 0x1806E33A0 | CanApplyBuff | BuffSkill |
| 0x1806D5040 | ShotPath_ActorCast | (utility) |
| 0x18073B240 | GetTargetValue | InflictSuppression |
| 0x18073B320 | GetUtilityFromTileMult | InflictSuppression |
| 0x180769B40 | GetTargetValue | Stun |
| 0x180762550 | GetTargetValue | Mindray |
| 0x18076A640 | GetTargetValue | TargetDesignator |
| 0x180769E60 | GetTargetValue | SupplyAmmo |
| 0x180769450 | GetTargetValue | SpawnPhantom |
| 0x180768EF0 | GetTargetValue | SpawnHovermine |
| 0x18075EB90 | GetTargetValue | CreateLOSBlocker |
| 0x18073A0C0 | GetHighestTileScore | Deploy |
| 0x18073A260 | OnCollect | Deploy |
| 0x18073AD00 | OnEvaluate | Deploy |
| 0x18073ADD0 | OnExecute | Deploy |

### Called but not fully analysed (secondary targets)

| VA | Inferred Method | Priority |
|---|---|---|
| 0x180740F20 | TileScore.GetScore — composite score getter | Low (NQ-41) |
| 0x18071B640 | AgentContext_GetCandidateSource | Medium (NQ-44) |
| 0x1806343A0 | EvaluateTileFromCoords — fills TileScore list | Medium (NQ-45) |
| 0x18053FEB0 | ComputeDistance — int distance result | Low (NQ-46) |
| 0x1805CA7A0 | Tile_Distance — tile-to-tile distance | Low (NQ-49) |
| 0x181423600 | GetAoETierForMember | Medium (NQ-33) |
| 0x1806E3750 | IsInDesignationZone | Low (NQ-40) |
| 0x1806361F0 | StrategyData.ComputeMoveCost | Deferred — separate system |
| 0x1806DE1D0 | Indirect fire trajectory builder | Deferred — separate system |
| 0x1806E1FB0 | AoE target set builder | Deferred — separate system |

---

## 17. Key Inferences and Design Notes

**The score ceiling of `21474` is not arbitrary.** `0x53E2 = 21474`. It does not correspond to `INT_MAX / 100` or any round number. It is likely a designer-set maximum that emerged from score calibration.

**`m_IsFirstEvaluated` and `m_IsFirstExecuted` are misleadingly named.** Both are cleared on execute and set on evaluate — they mean "this behaviour has been evaluated since it last executed." A subclass checking `m_IsFirstExecuted` is asking "am I in a fresh evaluation cycle?", not "is this the first time I've run?"

**`OnBeforeProcessing` is called twice per turn minimum** — once during Collect, once during Evaluate. Subclasses overriding it must be idempotent or explicitly count calls.

**`m_DontActuallyExecute` is a planning flag, not an execution flag.** It is set during Collect/Evaluate and consumed by the Agent before calling `Execute`. This enables partial turn usage: the AI can commit AP to a deploy stance in one turn and fire in the next, with planning happening upfront.

**The `_forImmediateUse` parameter is a planning-mode switch.** When `false`, `GetTargetValue` computes expected value for future positioning. When `true`, it scores for execution now — applying different modifiers (AoE flags, target stance penalties, ammo efficiency). The same function serves both the "should I move here?" pass and the "should I fire now?" pass.

**Goal type is an enum with at least three values.** `0` = attack, `1` = assist-via-movement, `2` = assist-via-skill. The final score assembly formula differs for each.

**`skillEffectType` is the base scorer's routing key.** The single integer passed as arg5 to `SkillBehavior.GetTargetValue(private)` discriminates between effect classes: `0` = standard (Mindray), `1` = InflictDamage and InflictSuppression, `2` = Stun. Whether InflictDamage and InflictSuppression are handled identically at effectType 1 is NQ-37.

**Three scorer archetypes exist.** All concrete `GetTargetValue` overrides fall into one of: (1) tag-chain-then-delegate (InflictDamage, InflictSuppression, Stun, Mindray), (2) float scorer with its own formula (SupplyAmmo, TargetDesignator), (3) void side-effect scorer that operates via candidate registration (SpawnPhantom, SpawnHovermine, CreateLOSBlocker).

**InflictDamage is a decorator, not a scorer.** All attack subclasses share the `SkillBehavior.GetTargetValue` formula. The InflictDamage override only prepends tag value computation for co-fire shots. `tagValueScale` (+0xBC) has zero influence on solo attacks by architectural design.

**AoE readiness uses a 50/50 blend.** When `IsAoeSkill()` is true, the tile utility multiplier is blended: `0.5 × (currentAmmo/maxAmmo) + 0.5 × tileUtility`. This prevents an AoE skill with low ammo from scoring highly even from ideal positions.

**Arc coverage is probabilistic, not deterministic.** For shotGroupMode 1, the system rolls `rand(1, 100)` against `arcCoveragePercent`. This introduces deliberate stochasticity into turret target selection at collection time.

**`GetHighestTileScoreScaled` and `GetHighestTileScore` are identical.** The distinction is purely the caller's intent — "Scaled" callers have already applied multipliers to the score fields. The callee function itself does not scale.

**The `/20.0` normalisation in Move tile scoring** appears consistently: `apCost / 20.0`. 20 is inferred as the maximum AP value. This normalises AP cost to a 0–1 ratio.

**Reserved tile scoring is asymmetric.** The reserved tile has its `movementScore` halved (less attractive to move there) but its `utilityScore` doubled (more attractive to stay near it).

**Peek bonus is extreme.** When `m_IsAllowedToPeekInAndOutOfCover` is set and the actor is low on AP, the movement score is multiplied by 4.0.

**Marginal move penalty prevents jitter.** When the best destination is only marginally better than the current position, `fWeight` is multiplied by `0.25` and `m_HasDelayedMovementThisTurn` is set.

**Deploy spreads units via soft spacing.** The ally proximity penalty is linear over 6 tiles: strongest when allies are adjacent, zero at 6+ tile separation. Only set-up (`Actor+0x50 != 0`) allies trigger it — still-mobile allies do not count.

**Deploy has a hardcoded priority of 1000.** It always wins over lower-scored combat behaviours while it has an unvisited target tile. `m_IsDone` is the gate that prevents re-evaluation.

**Buff scoring is fully additive.** There is no normalisation or cap before the final `contextScale * total * globalScale` multiplication. A skill with all six bits set accumulates contributions from all six branches simultaneously.

**HP fraction blend in SupplyAmmo is counter-intuitive.** The formula `0.8 + 0.2 * hpFrac` means higher-HP targets score slightly higher. SupplyAmmo prefers healthy targets that can make better use of the ammo.

**AoE branches in Buff iterate the caster's team tile list, not a radius.** AoE score asks "how many of my team members would benefit?" — the target actor is passed to `AoE_PerMemberScorer` as a range reference.

**`5.656854 = 4√2`.** The geometry threshold in CreateLOSBlocker is the diagonal of a 4×4 tile square — the maximum distance a point can be from a line while still considered "on" it in this grid geometry.

**AoE coverage subtraction in CreateLOSBlocker is an anti-redundancy mechanism.** `stackMult * aoeBase - (z0 + z1 + z2)` means that if existing AoE zone coverage already equals the base value, the blocker contributes nothing.

**`agentContext + 0x50` has a label conflict.** This offset was initially identified as a `BehaviorConfig2*` pointer (accessed in `GetBehaviorConfig2`). However, `Deploy.OnEvaluate` and `Deploy.OnExecute` both write byte value `1` to the address stored at this offset — inconsistent with it being a pointer. Either the label is wrong (it is a byte field) or the write intentionally stomps the low byte of a pointer with a flag. NQ-42.

---

## 18. Open Questions

The following questions remain unresolved. Each carries the concrete next step needed to answer it.

**NQ-4/5** — `WeightsConfig +0x78`, `+0x148`, `+0x14C` field names inferred. True class name for `WeightsConfig` unresolved.  
→ Search dump.cs for a class with float fields clustered around `+0xE4`, `+0xE8`, `+0xEC`, `+0xF0` under `Menace.Tactical.AI`. Run `extract_rvas.py` on it. Will also close NQ-47 (+0xCC) and NQ-50 (+0xD0).

**NQ-6** — `Skill +0x48` vs `Skill +0x60` shot group list distinction. Stage 6 confirms `m_SelectedTiles` at `+0x60`; `+0x48` in SkillBehavior is a different class. The annotation `m_AdditionalRadius` at `SkillBehavior +0x48` from dump.cs needs examination.  
→ Extract SkillBehavior class dump; verify field at `+0x48`. Consider closed at collation given Stage 6 evidence.

**NQ-16** — `Strategy +0x8C = strategyMode` (value 1 = no co-fire) is inferred. True class name for Strategy is unresolved.  
→ Search dump.cs for `GetBehaviorWeights` or `GetBehaviorConfig2` as method names to locate the Strategy class.

**NQ-19** — `EntityInfo +0x18` weapon/tag object — dereferenced in `InflictDamage.GetTargetValue`. Type and class name unconfirmed.  
→ Resolve EntityInfo true class name; then run `extract_rvas.py` to confirm field at `+0x18`.

**NQ-21** — Vtable slot `+0x458` on the object at `EntityInfo +0x18` — returns tag index. Class type of this object unknown.  
→ Identify class type of EntityInfo +0x18; look up vtable slot. Deferred — low impact.

**NQ-33** — `FUN_181423600 = GetAoETierForMember`. Called from `AoE_PerMemberScorer`. Internals deferred.  
→ Analyse `0x181423600` if AoE tier assignment logic is needed.

**NQ-36** — Concrete `Condition.Evaluate` implementations (vtable `+0x1D8`). Interface documented; subclasses deferred.  
→ Low priority. Analyse only if `CanApplyBuff` condition logic needs full detail.

**NQ-37** — `InflictSuppression` passes `skillEffectType = 1`, same as `InflictDamage`. Whether the base scorer handles them identically or with distinction is unconfirmed.  
→ Analyse `SkillBehavior.GetTargetValue` (private, `0x18073C130`) branching on arg5.

**NQ-38** — `EntityInfo +0xA8 bit 0x100 = mindrayVulnerable` — field name unresolved.  
→ Resolve EntityInfo class name; confirm field at `+0xA8`.

**NQ-39** — `EntityInfo flags bit 11 = alreadyDesignated` — field name unresolved.  
→ Resolve EntityInfo class name; confirm.

**NQ-40** — `FUN_1806E3750 = IsInDesignationZone`. Low priority.  
→ Analyse `0x1806E3750` if designation scoring internals are needed.

**NQ-41** — `FUN_180740F20 = TileScore.GetScore` (composite score getter used by `GetHighestTileScore`). Exact implementation unknown.  
→ Analyse `0x180740F20` if tile selection ordering or score composition needs clarification.

**NQ-42** — `AgentContext +0x50` label conflict: previously `BehaviorConfig2*` pointer; Deploy writes byte 1 to this location directly. Must resolve before finalising AgentContext layout.  
→ Extract AgentContext true class name; re-examine field at `+0x50`.

**NQ-43** — `entity +0xCC` bool read via vtable `+0x398` in `Deploy.OnCollect`. Likely "isSetUp" state.  
→ Low priority.

**NQ-44** — `FUN_18071B640 = AgentContext_GetCandidateSource`. Returns walk range or ProximityData.  
→ Medium priority. Analyse `0x18071B640` if Deploy collection tracing is needed.

**NQ-45** — `FUN_1806343A0 = EvaluateTileFromCoords`. Path/tile evaluation filling the TileScore list; core of Deploy.OnCollect inner loop.  
→ Medium priority. Analyse `0x1806343A0` if the tile scoring pipeline needs full tracing.

**NQ-46** — `FUN_18053FEB0 = ComputeDistance`. Int distance result used in Deploy range penalty.  
→ Low priority.

**NQ-48** — `Actor +0x50 = isSetUp_alt`. Confirmed from Deploy.OnCollect ally proximity check; not in the prior Actor class dump.  
→ Confirm against Actor class dump when Actor class name is resolved.

**NQ-49** — `FUN_1805CA7A0 = Tile_Distance`. Tile-to-tile distance function.  
→ Low priority.

---

## 19. Scope Boundaries

The following are explicitly out of scope. They were not pursued and should not be derived from this report:

- `Deploy.OnReset` (RVA 0x71E0E0) — bookkeeping only; not material
- `GainBonusTurn`, `Reload`, `Scan`, `MovementSkill`, `RemoveStatusEffect` — entire classes untouched
- `TurnArmorTowardsThreat`, `TransportEntity` — entire classes untouched
- `FUN_1806DE1D0` (indirect fire trajectory builder) — separate system; too large to include here
- `FUN_1806E1FB0` (AoE target set builder) — separate system
- `StrategyData.ComputeMoveCost` (`FUN_1806361F0`) — pathfinding internals; warrants own investigation
- Concrete `Condition.Evaluate` subclasses — interface documented; implementations deferred
- `GetAoETierForMember` (`FUN_181423600`) — deferred
- All `.ctor`, `OnReset`, property accessors throughout the investigation (unless material to scoring model)
- `Attack.OnExecute`, `Assist.OnExecute` — execution mechanics; scoring pipelines are fully documented

---

## 20. Unresolved Class Names

The following investigation-internal names do **not** correspond to any IL2CPP class name found in dump.cs. They were assigned during Ghidra analysis based on field and method behaviour. The objects are accessed exclusively through opaque `DAT_` metadata pointers. All field offsets are confirmed; all class names remain unresolved. Every reference to these names in this report should be understood as an investigation-internal working name, not a verified game class name.

| Investigation Name | DAT_ Access | Recommended Resolution |
|---|---|---|
| WeightsConfig | `*(DAT_18394c3d0 + 0xb8) + 8` | Search dump.cs for a class with float fields at +0xE4, +0xE8, +0xEC, +0xF0 under Menace.Tactical.AI |
| AgentContext | Held at `Behavior+0x10` | Search dump.cs for class with EntityInfo-type field at +0x10 |
| EntityInfo | Held at `AgentContext+0x10` | Search dump.cs for class with `List<Actor>` at +0x20 |
| Strategy (AI) | `*(DAT_183981f50 + 0xb8)` | Search dump.cs for `GetBehaviorWeights` or `GetBehaviorConfig2` as method names |
| BehaviorConfig2 | Held at `AgentContext+0x50` | NQ-42 label conflict must be resolved first |
| BehaviorWeights | Held at `Strategy+0x310` | Resolve Strategy class name first |
| StrategyData | Held at `Strategy+0x2B0` | Resolve Strategy class name first |
