# Menace Tactical AI — Behavior/SkillBehavior Subclass Investigation
# Stage 2 Report

**Game:** Menace
**Platform:** Windows x64, Unity IL2CPP
**Binary:** GameAssembly.dll
**Image base:** 0x180000000 (VA = RVA + 0x180000000)
**Source material:** Il2CppDumper dump.cs (~885,000 lines), Ghidra decompilation, extraction_report_master.txt
**Investigation status:** In Progress (Stage 2 of ~5)

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. Core Findings
   4.1 GetTagValueAgainst — Tag Effectiveness Formula
   4.2 Move Behavior — Tile Scoring Pipeline
   4.3 Move.OnExecute — State Machine
5. Full Pipeline: Move Behavior Flow
6. Class Sections
   6.1 SkillBehavior (dependency closure)
   6.2 ProximityData / ProximityEntry
   6.3 Move
   6.4 BehaviorWeights / BehaviorConfig2
   6.5 TileScore
   6.6 TagEffectivenessTable
7. Ghidra Address Reference
8. Key Inferences and Design Notes
9. Open Questions

---

## 1. Investigation Overview

### What was investigated

Stage 2 had two goals:

**Goal A — Close remaining Stage 1 dependencies.** Four functions were carried forward as
open questions from Stage 1: `GetTagValueAgainst` (NQ-7), the proximity data pair
(NQ-3), and a `GetOrder` implementation (NQ-8). All were resolved in this stage.

**Goal B — Complete the Move behavior subclass.** `Move` is the most complex non-skill
behavior in the system, with 23 fields and 23 methods. It is the only behavior that
inherits directly from `Behavior` (not `SkillBehavior`) and uses a tile-based scoring
model rather than the shot pipeline. The evaluation, scoring, winner-selection, and
execution state machine are all fully reconstructed.

### What was achieved

- `SkillBehavior.GetTagValueAgainst` fully reconstructed. Tag effectiveness formula confirmed.
- `ProximityData.FindEntryForTile` and `ProximityEntry.IsValidType` confirmed. NQ-3 closed.
- `ProximityData.HasReadyEntry` reconstructed (new function, found during Move.OnExecute analysis).
- `GetOrder() = 0` confirmed for Deploy and Idle behaviors.
- `Behavior.GetBehaviorWeights` and `Behavior.GetBehaviorConfig2` reconstructed. Access paths
  to `BehaviorWeights` (via `Strategy +0x310`) and `BehaviorConfig2` (via `AgentContext +0x50`) confirmed.
- `Move.HasUtility` reconstructed. Forced/voluntary movement distinction confirmed.
- `Move.GetAddedScoreForPath` reconstructed. Path quality float scoring confirmed.
- `Move.GetHighestTileScore` and `Move.GetHighestTileScoreScaled` confirmed identical logic.
- `Move.OnEvaluate` fully reconstructed (~1,500 lines raw). Complete tile scoring formula confirmed.
- `Move.OnExecute` fully reconstructed. Four-stage state machine confirmed.
- `TileScore` field layout mapped to 19 confirmed or inferred fields.
- `WeightsConfig` extended with 11 confirmed movement-related fields.

### What was NOT investigated

- `FUN_1806361f0` (`StrategyData.ComputeMoveCost`) — the pathfinding cost function called
  per-tile in `Move.OnEvaluate`. This function is large and constitutes a subsystem in its
  own right. Deferred to a separate stage.
- `Move.OnCollect` — not yet decompiled. Its role (populating `m_Destinations`) is inferred
  from how `OnEvaluate` consumes the list.
- `Move.GetAddedScoreForPath` interaction with the path graph — the graph construction
  functions (`FUN_180669480`, `FUN_180cc14c0`) are resolved by name only.
- All Attack, Reload, Deploy, Assist, and other subclass implementations — deferred to Stage 3+.
- `GetOrder` return values for RVAs `0x50C760`, `0x547170`, `0x546260` — not yet decompiled.

---

## 2. Tooling

`extract_rvas.py` was run prior to this stage to produce `extraction_report_master.txt`,
covering all behavior subclasses in the `Menace.Tactical.AI.Behaviors` namespace. The
report was used throughout Stage 2 to cross-reference field offsets and method RVAs
against Ghidra decompilation.

No tool issues were encountered. All 13 target VAs were returned by Ghidra without
truncation. Functions were batched in two passes: (1) the four Stage-1 dependency closures,
(2) the five Move analysis functions.

---

## 3. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| SkillBehavior | Menace.Tactical.AI.Behaviors | (base) | Base class for skill-using behaviors; provides GetTagValueAgainst |
| ProximityData | Menace.Tactical.AI | — | Holds a list of ProximityEntry objects; used in ally-pressure scoring |
| ProximityEntry | Menace.Tactical.AI | — | Single entry in the proximity list; tracks tile, type, and readyRound |
| Move | Menace.Tactical.AI.Behaviors | 3650 | Tile-based movement behavior; 23 fields, full scoring and execution pipeline |
| BehaviorWeights | (internal, via Strategy) | — | Per-behavior weight configuration accessed via Strategy+0x310 |
| BehaviorConfig2 | (internal, via AgentContext) | — | Secondary behavior flags accessed via AgentContext+0x50 |
| TileScore | Menace.Tactical.AI | — | Scored tile candidate; 19 fields covering movement, utility, AP, path links |
| TagEffectivenessTable | (internal singleton) | — | Static float[] indexed by tag match result; drives GetTagValueAgainst |

---

## 4. Core Findings

### 4.1 GetTagValueAgainst — Tag Effectiveness Formula

`SkillBehavior.GetTagValueAgainst` produces a multiplicative bonus applied to the target
score when the skill has a tag match against the opponent. The formula is:
```
bonus = TagEffectivenessTable[tagIndex] * WeightsConfig.tagValueScale + 1.0
```

Where:
- `tagIndex` is determined by one of two tag-matching paths (TypeA or TypeB), each
  producing a uint index into the `TagEffectivenessTable` float array.
- `WeightsConfig.tagValueScale` (`+0xBC`) is bypassed (replaced with `1.0`) when
  `forImmediateUse == true`, preventing config scaling for snap decisions.
- The `+ 1.0` ensures the bonus is always ≥ 1.0 — a no-match returns `0 * scale + 1.0 = 1.0`
  (no effect). A strong match returns e.g. `1.0 * scale + 1.0 ≈ 2.0+` (doubling the score).

The bonus is applied multiplicatively in `GetTargetValue`. It is the final multiplier
before the score is written to the tile dictionary.

### 4.2 Move Behavior — Tile Scoring Pipeline

The movement decision pipeline runs as follows:

**Weight initialisation:**
```
fWeight = BehaviorWeights.weightScale × WeightsConfig.movementWeightScale
// Adjusted by:
//   × (currentAP / maxAP)        if not yet moved this turn
//   × 0.9                         if weapon not yet set up
```

**Per-tile score formula:**
```
TileScore.movementScore = WeightsConfig.movementScoreWeight
                        × (apCost / 20.0)
                        × BehaviorWeights.movementWeight
```

Where `apCost` is the integer path cost returned by `StrategyData.ComputeMoveCost`.
The division by `20.0` normalises to a 0–1 range (max AP in the game is inferred as 20).

**Secondary look-ahead (up to 8 adjacent tiles):**
```
adjacentScore = primaryScore × WeightsConfig.secondaryPathPenalty (+0x15C)
// Adjacent tile preferred if its score is within 15% of the current candidate
// AND it is closer to the actor's current tile.
```

**Post-loop adjustments:**

| Condition | Adjustment |
|---|---|
| `apCost < maxAP / 2` | `× WeightsConfig.shortRangePenalty (+0x168)` |
| Chain tile fits AP budget | `× 2.0` (forward chain) or `× 0.5` (backward chain) |
| Stance skill fits budget | `× WeightsConfig.stanceSkillBonus (+0x16C)` |

**Best tile validation:**
```
// Only move if:
bestTileCompositeScore >= currentTileCompositeScore × WeightsConfig.minimumImprovementRatio (+0x150)
// Or if movement is "forced" (no tile exceeds utility threshold anywhere in the map)
```

**Final score return:**
```
return (int)(fWeight × WeightsConfig.finalMovementScoreScale (+0x128))
```

**"Forced" movement** is triggered when:
1. Actor is prone (stance == 1), OR
2. `BehaviorConfig2.configFlagA` AND `BehaviorConfig2.configFlagB` are both set, OR
3. `Move.HasUtility()` returns false — no tile in the map meets the utility threshold.

When forced, the minimum-improvement filter is bypassed and the unit considers all
destinations regardless of their utility score.

**Score scaling when forced:**
```
ratio = powf(bestScore / currentScore, exponent)
fWeight *= max(ratio, 0.33)
```
This provides a soft floor of 0.33× the base weight — the unit still has reduced urgency
even when forced, unless the destination is substantially better.

### 4.3 Move.OnExecute — State Machine

Four sequential stages. Returns `false` (keep ticking) until all stages complete.
```
Stage 0: Re-routing setup (release old reserved tile entity, claim new target tile entity)
Stage 1: UseSkillBefore loop — consume m_UseSkillBefore list, one skill per tick
Stage 2: Timer wait → trigger Actor.StartMove(targetTile, flags)
Stage 3: UseSkillAfter loop — consume m_UseSkillAfter list, one skill per tick
Stage 4: Container exit handling / final Skill.Activate → return true
```

`flags` bitmask passed to `Actor.StartMove`:
- bit 0 = `!Goal.IsEmpty(targetTile)` — tile has a goal entity
- bit 1 = `Actor.CanDeploy()` — actor has a deployable stance
- bit 2 = `TileScore.isPeek (+0x61)` — this is a peek-in-cover move

---

## 5. Full Pipeline: Move Behavior Flow
```
Move.OnCollect (not yet analysed)
  → Populates m_Destinations (List<TileScore>)
  → Populates m_UseSkillBefore, m_UseSkillAfter

Move.OnEvaluate(actor)
  ├── Guards: incapacitated? immobile? movement disabled? locked? done? inert?
  ├── AP budget: currentAP - minimumAP - reservedAP < 1 → return 0
  ├── Weight init: fWeight = weightScale × movementWeightScale × apRatio × weaponPenalty
  ├── Forced check: HasUtility(tileDict) → voluntary vs forced movement
  ├── Reference tile: TileMap.TryGet(currentTile) → currentTileScore
  ├── Reserved tile adjustment: movementScore×0.5, utilityScore×2.0
  ├── Destination loop (over m_Destinations):
  │     ├── StrategyData.ComputeMoveCost(...) → apCost
  │     ├── TileScore.movementScore = movementScoreWeight × (apCost/20.0) × movementWeight
  │     ├── Secondary look-ahead: up to 8 adjacent tiles, secondaryPathPenalty applied
  │     ├── Post-loop: shortRangePenalty, chainBonus, stanceSkillBonus
  │     └── Competitor comparison: mode 1 (tag-type) or mode 2 (round-snapshot)
  ├── Winner: Move.GetHighestTileScoreScaled(m_Destinations)
  ├── Validation: winner.tile != currentTile AND score >= currentScore × minimumImprovementRatio
  ├── Score scaling: powf ratio (forced) or denominator ratio (voluntary)
  ├── Peek bonus: ×4.0 if m_IsAllowedToPeekInAndOutOfCover and low AP
  ├── Marginal move penalty: ×0.25 if barely better than staying
  ├── Skill scheduling: add to m_UseSkillBefore / m_UseSkillAfter
  └── return (int)(fWeight × finalMovementScoreScale)

Move.OnExecute(actor)
  ├── Stage 0: rerouting setup (entity claim/release)
  ├── Stage 1: UseSkillBefore loop
  ├── Stage 2: wait timer → Actor.StartMove(targetTile, flags)
  ├── Stage 3: UseSkillAfter loop
  └── Stage 4: container exit / Skill.Activate → return true
```

---

## 6. Class Sections

### 6.1 SkillBehavior — GetTagValueAgainst (dependency closure)

**Namespace:** Menace.Tactical.AI.Behaviors
**Base class:** Behavior
**Role:** Provides tag-based effectiveness scoring against a specific opponent.
This method was identified in Stage 1 as the final unresolved multiplier in `GetTargetValue`.

**New fields confirmed this stage (on classes accessed within GetTagValueAgainst):**

TagEffectivenessTable (singleton, DAT_18397ae78):
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x18 | int | length | Array length. Bounds-checked before access. Confirmed. |
| +0x20 | float[] | values | Float array, stride 4. Index computed by TagMatcher. Confirmed. |

WeightsConfig (singleton, DAT_18394c3d0):
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0xBC | float | tagValueScale | Multiplies table value. Bypassed (= 1.0) when forImmediateUse. Confirmed. |

**Methods table:**
| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTagValueAgainst | 0x73BFA0 | 0x18073BFA0 | Fully analysed this stage. |

---

### 6.2 ProximityData / ProximityEntry

**Role:** `ProximityData` holds a list of `ProximityEntry` objects. Each entry tracks a
tile, its type enum (0=ground, 1=low, 2+=excluded), and a `readyRound` (-1 = unassigned,
≥0 = assigned to a specific round). Two query functions were analysed: `FindEntryForTile`
(linear scan by tile pointer equality) and `HasReadyEntry` (any entry with `readyRound ≥ 0`).

A third function from Stage 1, `IsValidType`, reads `entry->type (+0x34)` and returns
true only for values 0 or 1 — i.e. ground and low-profile entries contribute to the
ally-pressure bonus in `GetTargetValue`; aerial or other types (2+) do not.

**ProximityData fields:**
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x48 | List<ProximityEntry>* | entries | Iterated by FindEntryForTile and HasReadyEntry. Confirmed. |

**ProximityEntry fields:**
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x10 | Tile* | tile | Matched against search target in FindEntryForTile. Confirmed. |
| +0x18 | int | readyRound | -1 = unassigned. ≥0 = assigned to round index. Confirmed. |
| +0x34 | int | type | 0/1 = valid for pressure bonus. 2+ = excluded. Confirmed. |

**Methods table:**
| Method | RVA | VA | Notes |
|---|---|---|---|
| FindEntryForTile | 0x717730 | 0x180717730 | Fully analysed Stage 1 (NQ-3a). |
| IsValidType | 0x717A40 | 0x180717A40 | Fully analysed Stage 1 (NQ-3b). |
| HasReadyEntry | 0x717870 | 0x180717870 | Fully analysed Stage 2. |

---

### 6.3 Move

**Namespace:** Menace.Tactical.AI.Behaviors
**TypeDefIndex:** 3650
**Base class:** Behavior (not SkillBehavior — does not use the shot pipeline)
**Role:** Selects and executes the best movement destination for an actor. Operates on a
pre-populated tile dictionary (`Agent.tileDict`) and a list of candidate destinations
(`m_Destinations`). Scores tiles using AP cost, utility, cover, and path quality.

**Fields table:**
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x020 | bool | m_IsMovementDone | True = movement complete this turn. Early-out guard. Confirmed. |
| +0x021 | bool | m_HasMovedThisTurn | True = already moved. Affects weight scaling. Confirmed. |
| +0x022 | bool | m_HasDelayedMovementThisTurn | Set when marginal move penalty applied (×0.25). Confirmed. |
| +0x023 | bool | [hasMovedBit] | Second bit of HasMovedThisTurn word. AP ratio gating. Confirmed. |
| +0x024 | bool | m_IsAllowedToPeekInAndOutOfCover | Enables ×4.0 peek bonus in low-AP situations. Confirmed. |
| +0x028 | TileScore* | m_TargetTile | Chosen destination (TileScore including tile + scores). Confirmed. |
| +0x030 | Tile* | m_ReservedTile | Tile whose entity is currently claimed by this actor. Confirmed. |
| +0x038 | int | m_TurnsBelowUtilityThreshold | Counter: how many rounds below threshold. Confirmed. |
| +0x03C | int | m_TurnsBelowUtilityThresholdLastTurn | Last round index when counter was incremented. Confirmed. |
| +0x040 | List<TileScore>* | m_Destinations | Pre-scored candidate tiles. Populated by OnCollect. Confirmed. |
| +0x048 | List<Vector3>* | m_Path | Primary movement path. Confirmed. |
| +0x050 | List<Vector3>* | m_AlternativePath | Fallback path. Confirmed. |
| +0x058 | Skill* | m_DeployedStanceSkill | Deployed-stance skill; AP cost subtracted if usable and prone. Confirmed. |
| +0x060 | Skill* | m_DefaultStanceSkill | Default-stance skill; triggers stanceSkillBonus if affordable. Confirmed. |
| +0x068 | Skill* | m_SetupWeaponSkill | Weapon setup skill. Confirmed. |
| +0x070 | List<Skill>* | m_UseSkillBefore | Skills to activate before moving. Consumed in OnExecute Stage 1. Confirmed. |
| +0x078 | int | m_UseSkillBeforeIndex | Current index into m_UseSkillBefore. Confirmed. |
| +0x080 | List<Skill>* | m_UseSkillAfter | Skills to activate after moving. Consumed in OnExecute Stage 3. Confirmed. |
| +0x088 | int | m_UseSkillAfterIndex | Current index into m_UseSkillAfter. Confirmed. |
| +0x08C | bool | m_IsExecuted | True = StartMove has been called. Confirmed. |
| +0x090 | float | m_WaitUntil | Game time threshold; movement triggers once Time.time exceeds this. Confirmed. |
| +0x094 | bool | m_IsInsideContainerAndInert | Early-out guard: true = skip evaluation. Confirmed. |
| +0x098 | Actor* | m_PreviousContainerActor | Set in OnExecute Stage 0; used in Stage 4 container-exit logic. Confirmed. |

**Methods table:**
| Method | RVA | VA | Notes |
|---|---|---|---|
| .ctor | 0x766D00 | 0x180766D00 | Not analysed. |
| GetOrder | 0x546260 | 0x180546260 | Returns int. Not yet decompiled. |
| GetID | 0x54E040 | 0x18054E040 | Not analysed. |
| IsMovementDone | 0x4FDE30 | 0x18004FDE30 | Accessor. Not analysed. |
| HasMovedThisTurn | 0x4FDE40 | 0x18004FDE40 | Accessor. Not analysed. |
| HasDelayedMovementThisTurn | 0x7632E0 | 0x1807632E0 | Not analysed. |
| IsDelayingMovement | 0x502F40 | 0x180502F40 | Not analysed. |
| IsInsideContainerAndInert | 0x763460 | 0x180763460 | Not analysed. |
| GetTargetTile | 0x4F04B0 | 0x18004F04B0 | Accessor. Not analysed. |
| **OnEvaluate** | **0x7635C0** | **0x1807635C0** | **Fully analysed. Core scoring function.** |
| **OnExecute** | **0x766370** | **0x180766370** | **Fully analysed. Four-stage state machine.** |
| OnReset | 0x766C00 | 0x180766C00 | Not analysed. |
| OnBeforeProcessing | 0x763470 | 0x180763470 | Not analysed. |
| CheckInsideContainerAndInert | 0x762910 | 0x180762910 | Not analysed. |
| OnNewTurn | 0x766A40 | 0x180766A40 | Not analysed. |
| OnClear | 0x763560 | 0x180763560 | Not analysed. |
| GetTilesSortedByScore | 0x763170 | 0x180763170 | Not analysed. |
| GetTilesSortedByDistance | 0x763000 | 0x180763000 | Not analysed. |
| **GetHighestScore** | **0x762BF0** | **0x180762BF0** | Not analysed (different from GetHighestTileScore). |
| **GetHighestTileScore** | **0x762EB0** | **0x180762EB0** | **Fully analysed. Max-scan over composite score.** |
| **GetHighestTileScoreScaled** | **0x762D60** | **0x180762D60** | **Fully analysed. Identical to GetHighestTileScore.** |
| **GetAddedScoreForPath** | **0x7629F0** | **0x1807629F0** | **Fully analysed. Path quality float accumulator.** |
| **HasUtility** | **0x7632F0** | **0x1807632F0** | **Fully analysed. Forced/voluntary movement gate.** |

---

### 6.4 BehaviorWeights / BehaviorConfig2

**Role:** Two configuration objects accessed via the behavior's owning agent chain.
Neither appears directly as a named class in the dump — they are inferred from the
access patterns of `GetBehaviorWeights` and `GetBehaviorConfig2`.

**Access paths:**
```
BehaviorWeights:  self->agent (+0x10) -> actor (+0x18) -> GetStrategy() -> strategy->behaviorWeights (+0x310)
BehaviorConfig2:  self->agent (+0x10) -> agentContext (+0x10) -> behaviorConfig (+0x50)
```

**BehaviorWeights fields:**
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x14 | float | movementWeightMultiplier | Clamped to ≥ 1.0 when used in final denominator. Confirmed. |
| +0x20 | float | movementWeight | Per-behavior base weight; part of tile score formula. Confirmed. |
| +0x2C | float | weightScale | Multiplied with WeightsConfig.movementWeightScale at start. Confirmed. |

**BehaviorConfig2 fields:**
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x28 | bool | configFlagA | Part of forced-movement condition. Confirmed. |
| +0x34 | bool | configFlagB | Part of forced-movement condition. Confirmed. |

**Methods:**
| Method | VA | Notes |
|---|---|---|
| Behavior.GetBehaviorWeights | 0x180738FE0 | Fully analysed. 6 lines. |
| Behavior.GetBehaviorConfig2 | 0x180739020 | Fully analysed. 4 lines. |

---

### 6.5 TileScore

**Role:** The core data structure for movement scoring. Each `TileScore` represents a
candidate destination tile with its computed scores, AP cost, path links, and metadata
flags. Instances are stored in `m_Destinations` (List) and in the agent's tile dictionary.

**Fields table:**
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x10 | Tile* | tile | Pointer to the game tile. Confirmed from multiple accesses. |
| +0x18 | Entity* | entity | Entity at this tile, if any. Used in targeting/container checks. Confirmed. |
| +0x20 | float | movementScore | Primary computed score. Written by tile formula. Confirmed. |
| +0x24 | float | secondaryMovementScore | Written in secondary look-ahead path. Confirmed. |
| +0x28 | float | exposureScore | Exposure/coverage component. Used in path accumulator and competitor comparisons. Confirmed. |
| +0x2C | float | rangeScore | Copied from +0x28 in some paths; separate range evaluation. Confirmed. |
| +0x30 | float | utilityScore | General utility value. Threshold comparisons, reserved tile scaling. Confirmed. |
| +0x34 | float | coverScore | Modified by stance/range post-loop adjustments. Confirmed. |
| +0x40 | int | apCost | Path cost in AP. Written by ComputeMoveCost; 0 = not yet scored. Confirmed. |
| +0x44 | int | chainCost | AP cost for a chained subsequent tile. Chain bonus logic. Confirmed. |
| +0x48 | TileScore* | destinationRef | Forward reference to target destination if this is a path node. Inferred. |
| +0x50 | TileScore* | prevTileRef | Previous tile in path chain. Inferred from chain logic. Inferred. |
| +0x58 | TileScore* | nextTileRef | Next tile in path chain. Inferred. |
| +0x60 | bool | isForward | Direction flag; set true for forward-chain tiles. Inferred. |
| +0x61 | bool | isPeek | True = peek-in-cover move. Passed as bit 2 of StartMove flags. Confirmed. |
| +0x62 | byte | stance | Stance to adopt on arrival. Written to actor on reach. Confirmed. |

**Key methods (resolved by call site):**
| Method | Address | Notes |
|---|---|---|
| GetScore | FUN_180740f20 | Used in GetHighestTileScore. |
| GetCompositeScore | FUN_180740e50 | Used in GetHighestTileScoreScaled and competitor comparisons. Distinct from GetScore. |

---

### 6.6 TagEffectivenessTable

**Role:** Singleton static table. A float array indexed by tag match result, providing
the raw effectiveness value before `WeightsConfig.tagValueScale` is applied. Accessed
only from `GetTagValueAgainst`.

**Fields:**
| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x18 | int | length | Array length. Bounds check enforced before access. Confirmed. |
| +0x20 | float[] | values | stride 4. Index is uint from TagMatcher. Confirmed. |

---

## 7. Ghidra Address Reference

### Fully analysed this stage

| VA | RVA | Method | Class | Notes |
|---|---|---|---|---|
| 0x18073BFA0 | 0x73BFA0 | GetTagValueAgainst | SkillBehavior | NQ-7 closed. Tag effectiveness formula confirmed. |
| 0x180717730 | 0x717730 | FindEntryForTile | ProximityData | NQ-3a closed. Linear scan. |
| 0x180717A40 | 0x717A40 | IsValidType | ProximityEntry | NQ-3b closed. Type 0/1 valid only. |
| 0x180519A90 | 0x519A90 | GetOrder | Deploy / Idle | NQ-8 partial. Returns 0. |
| 0x180717870 | 0x717870 | HasReadyEntry | ProximityData | readyRound ≥ 0 check. |
| 0x180738FE0 | 0x738FE0 | GetBehaviorWeights | Behavior | Via Strategy+0x310. |
| 0x180739020 | 0x739020 | GetBehaviorConfig2 | Behavior | Via AgentContext+0x50. |
| 0x1807632F0 | 0x7632F0 | HasUtility | Move | Forced/voluntary gate. |
| 0x1807629F0 | 0x7629F0 | GetAddedScoreForPath | Move | Path quality float accumulator. |
| 0x180762EB0 | 0x762EB0 | GetHighestTileScore | Move | Max-scan on GetCompositeScore. |
| 0x180762D60 | 0x762D60 | GetHighestTileScoreScaled | Move | Identical logic to above. |
| 0x1807635C0 | 0x7635C0 | OnEvaluate | Move | Full scoring pipeline. ~1500 lines raw. |
| 0x180766370 | 0x766370 | OnExecute | Move | Four-stage state machine. |

### Secondary targets — not yet analysed

| VA | RVA | Method | Class | Notes |
|---|---|---|---|---|
| 0x18073BFA0 | — | GetTagValueAgainst | SkillBehavior | Complete — listed here for reference. |
| 0x1806361F0 | — | ComputeMoveCost | StrategyData | NQ-11. Per-tile pathfinding cost. Separate stage. |
| 0x180762BF0 | 0x762BF0 | GetHighestScore | Move | Float variant. Not yet decompiled. |
| 0x180763170 | 0x763170 | GetTilesSortedByScore | Move | Not analysed. |
| 0x180763000 | 0x763000 | GetTilesSortedByDistance | Move | Not analysed. |
| 0x18050C760 | 0x50C760 | GetOrder | Assist/Attack | NQ-8. Returns unknown int. |
| 0x180547170 | 0x547170 | GetOrder | Reload/MovementSkill | NQ-8. Returns unknown int. |
| 0x180546260 | 0x546260 | GetOrder | Move/Idle.OnEvaluate | NQ-8. Returns unknown int. |

---

## 8. Key Inferences and Design Notes

**GetHighestTileScore vs GetHighestTileScoreScaled are identical.** Both functions
compile to the same logic. The distinction is purely in the call context: "Scaled" is
called after the caller has already applied multipliers to the score fields in the list.
The function itself does not scale anything. This is a naming convention for the caller's
intent, not a functional difference in the callee.

**The `/ 20.0` normalisation in the tile score formula.** The expression
`apCost / 20.0` appears consistently in the score formula. 20 is inferred as the maximum
AP value in the game. This normalises AP cost to a 0–1 ratio, making the score
independent of absolute AP counts. Confirmed by `EntityInfo.GetMaxAP()` being called and
used in the AP ratio weight adjustment.

**Forced movement is a safety valve, not a reroute.** When `HasUtility()` returns false,
the AI does not conclude "I have nowhere to go." It concludes "I have no preferred
destination, so I should move to whatever is best regardless." The score still goes through
the full formula and can return 0 if the winner's composite score fails validation. The
unit can legitimately stay put even in forced mode.

**The `m_TurnsBelowUtilityThreshold` counter increments once per round.** The check
`currentRound != m_TurnsBelowUtilityThresholdLastTurn` guards against multiple
increments in the same round. This means a unit that has been below threshold for N full
rounds accumulates N in this counter. It is used in the forced-movement path to decide
whether to override the threshold filter.

**Reserved tile scoring is asymmetric.** The reserved tile has its `movementScore`
halved (making movement there less attractive) but its `utilityScore` doubled (making
staying near it more attractive). This biases the AI toward maintaining proximity to a
reserved position without forcing it to move there.

**Peek bonus is extreme.** When `m_IsAllowedToPeekInAndOutOfCover` is set and the actor
is low on AP (`currentAP < actor->field_0x14C`), the movement score is multiplied by 4.0.
This makes peek-capable units in low-AP states very strongly prefer peek positions.

**Marginal move penalty prevents jitter.** When the best destination is only marginally
better than the current position, `fWeight` is multiplied by `0.25` and
`m_HasDelayedMovementThisTurn` is set. This prevents an actor from making trivially small
repositions every turn, which would waste AP and produce erratic movement.

**Chain bonus is bidirectional with a sign check.** A forward chain (the path continues
toward a better tile) multiplies by 2.0. A backward chain (the path retreats) multiplies
by 0.5. The forward/backward distinction is determined by comparing the chain tile's
`rangeScore (+0x2C)` against 0.0.

**`Actor.field_0x15F` appears to be a "movement locked" flag.** It gates the UseSkillAfter
loop and the final Activate call in OnExecute. When set, the actor cannot fire skills or
proceed to completion — it remains in progress. The identity of this flag is inferred from
context; it may be a server-authority lock or a physics state.

**Container exit in OnExecute triggers a separate event broadcast.** When an actor exits a
container (`m_PreviousContainerActor` is set), OnExecute broadcasts a container-exit event
(`FUN_1819c8600`) and calls `ContainerActor.Notify(1)`. This is distinct from the normal
move completion path and produces additional side effects not yet fully traced.

---

## 9. Open Questions

**NQ-11** `FUN_1806361f0` — `StrategyData.ComputeMoveCost`. Called per-candidate-tile in
`Move.OnEvaluate`. Returns int AP cost. This is the pathfinding cost function and likely
wraps path graph queries. Large function; warrants its own stage.
*Next step: Decompile at VA 0x1806361F0. Expect multiple nested calls into path graph.*

**NQ-8 (partial)** GetOrder return values for `0x18050C760` (Assist/Attack),
`0x180547170` (Reload/MovementSkill), `0x180546260` (Move/Idle). These establish the
scheduling priority order among behaviors. Currently only 0 (Deploy/Idle) is confirmed.
*Next step: Decompile any one — expected `return N;` (3 lines).*

**NQ-4/NQ-5** `WeightsConfig` full field map. Several fields used in movement scoring
(`+0x78`, `+0x148`, `+0x14C`) are inferred by position and usage context but not yet
named. The class dump is needed to confirm all field names.
*Next step: Run `extract_rvas.py` targeting `WeightsConfig` class; full field dump.*

**NQ-6** `Skill +0x48 = shotGroups` confirmed as a Skill field (not SkillBehavior). The
dump.cs annotation `m_AdditionalRadius` at `SkillBehavior +0x48` needs examination —
this may be a dump artefact or the field is genuinely on both classes at the same offset.
*Next step: `extract_rvas.py` on Skill class; verify field layout at +0x48.*

**NQ-9** `FUN_1806f3c30` (`Skill.Activate`) return convention. In `SkillBehavior.OnExecute`
Stage 4, the result is XOR'd with 1 before being used as a return value. If Activate
returns 1 on success, XOR makes OnExecute return 0 (continue). This suggests a
false=done or 0=success convention — uncommon but consistent with the observed branching.
*Next step: Validate against a leaf subclass OnExecute (e.g. Reload.OnExecute RVA 0x767B70).*

**NQ-12 (closed)** `GetHighestTileScoreScaled` — confirmed identical to `GetHighestTileScore`.

**NQ-13 (closed)** `FUN_180717870` — confirmed as `ProximityData.HasReadyEntry`.