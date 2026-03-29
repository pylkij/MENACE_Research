# Menace Tactical AI — BehaviorBase/SkillBehavior Subclass Investigation
# Stage 2 Report

## Scope

This stage resolved the remaining base-class dependencies from Stage 1 and completed
the full analysis of the `Move` behavior subclass, including its evaluation and execution
state machines.

---

## Stage 1 Dependency Closures

### GetTagValueAgainst (VA 0x18073BFA0)

`SkillBehavior.GetTagValueAgainst(self, opponent, goal, forImmediateUse)` returns a
multiplicative bonus (always ≥ 1.0) applied to a target's score based on tag-type
effectiveness. It resolves two tag indices — one per tag category — against a static
`TagEffectivenessTable` singleton whose float array starts at `+0x20`. The result is
`tableValue * WeightsConfig.tagValueScale + 1.0`. The `tagValueScale` field is bypassed
when `forImmediateUse == true`, returning `tableValue * 1.0 + 1.0` instead.

**NQ-7 closed.**

### ProximityData.FindEntryForTile (VA 0x180717730)

Linear scan over `ProximityData->entries` (`+0x48`). Matches on `entry->tile` (`+0x10`).
Returns the matching `ProximityEntry*` or null. No complexity.

### ProximityEntry.IsValidType (VA 0x180717A40)

Reads `entry->type` (`+0x34`). Returns true if `type == 0 || type == 1`. Excludes type 2+
from the ally-pressure bonus in `GetTargetValue`.

**NQ-3 closed.**

### GetOrder — Deploy/Idle (VA 0x180519A90)

Returns `0`. Deploy and Idle behaviors have order 0 — highest scheduling priority.

**NQ-8 partially closed** (other GetOrder implementations not yet decompiled; low priority).

---

## ProximityData.HasReadyEntry (VA 0x180717870)

Iterates `ProximityData->entries` (`+0x48`). Returns `true` if any `entry->readyRound`
(`+0x18`) is `>= 0`. A value of `-1` means the entry is unassigned. Called in
`Move.OnExecute` to gate the container-exit / skill-after path.

---

## Move Subclass

`Move` inherits directly from `Behavior` (not `SkillBehavior`). It does not use the shot
pipeline. Its evaluation is tile-based, scored against the agent's pre-populated tile
dictionary.

### Move.HasUtility (VA 0x1807632F0)

Iterates the tile dictionary. Returns `true` if any tile has
`utilityScore >= GetUtilityThreshold()`. When false, movement is treated as "forced" and
the threshold filter is bypassed — the unit considers all tiles regardless of utility.

### Move.GetHighestTileScore (VA 0x180762EB0)

Linear scan over a `List<TileScore>`. Returns the entry with the highest
`TileScore.GetCompositeScore()` (`FUN_180740e50`).

### Move.GetHighestTileScoreScaled (VA 0x180762D60)

Functionally identical to `GetHighestTileScore`. Used after pre-scaling has been applied
to the candidate list by the caller.

### Move.GetAddedScoreForPath (VA 0x1807629F0)

Iterates tiles in a path list starting from `startIndex`. For each tile, looks up its
`TileScore` in the tile map. Accumulates `(movementScore + utilityScore) * mult`, where
`mult = 2.0` for the immediate next tile and `1.0` thereafter. Tiles with no map entry
increment a `missingCount`; at loop end these are extrapolated proportionally:
`total += total * (missingCount / remainingCount)`. Returns the accumulated float.

**Design note:** The 2× weight on the first path tile strongly biases the AI toward paths
where the very next step is already toward a high-value destination.

### Move.OnEvaluate (VA 0x1807635C0)

The central movement scoring function. Returns an int utility score for the behavior.

#### Guards (all return 0 on failure)

1. `Actor.IsIncapacitated()` — skip if incapacitated.
2. `Strategy.IsMovementDisabled(strategyData)` — skip if strategy disables movement.
3. `EntityInfo +0xEC` bit 2 = `isImmobile` — skip if set.
4. `Container.IsActorLocked(actor)` — skip if locked inside a container.
5. `Move->m_IsMovementDone` (`+0x20`) — skip if already done this turn.
6. `Move->m_IsInsideContainerAndInert` (`+0x94`) — skip if inert.

#### AP Budget

```
currentAP = actor->GetCurrentAP()
// If prone AND m_DeployedStanceSkill available AND skill.CanUse():
//     currentAP -= skill.GetAPCost()
effectiveBudget = currentAP - EntityInfo.minimumAP (+0x3C) - strategyData.reservedAP (+0x118)
if (effectiveBudget < 1) return 0
```

#### Weight Initialisation

```
weights   = Behavior.GetBehaviorWeights(self)    // Strategy+0x310
fVar27    = weights.weightScale * WeightsConfig.movementWeightScale (+0x12C)
// If m_HasMovedThisTurn bit (+0x23) is false:
fVar27 *= (currentAP / EntityInfo.GetMaxAP())
// If actor weapon not set up (actor+0x167):
fVar27 *= 0.9
```

#### "Should Move" Decision

```
bVar4 (forced) = actor.GetStance() == 1 (prone)
              OR (BehaviorConfig2.configFlagA AND BehaviorConfig2.configFlagB)
              OR !Move.HasUtility(self, tileDict)
```

#### Reference Tile

```
currentTileScore = TileMap.TryGet(tileDict, currentTile)
threshold        = GetUtilityThreshold()
if threshold <= currentTileScore.utilityScore:
    m_TurnsBelowUtilityThreshold = 0
else:
    m_TurnsBelowUtilityThreshold += 1  (once per round)
```

Reserved tile adjustment (if `m_ReservedTile` set):
- `reservedScore.movementScore *= 0.5`
- `reservedScore.utilityScore  *= 2.0`

#### Tile Scoring Formula

For each candidate tile in `m_Destinations`:
```
apCost = StrategyData.ComputeMoveCost(...)   // FUN_1806361f0 — NOT YET ANALYSED
tileScore.movementScore = WeightsConfig.movementScoreWeight (+0x54)
                        * (apCost / 20.0)
                        * BehaviorWeights.movementWeight (+0x20)
```

Secondary look-ahead scoring checks up to 8 adjacent tiles using the same formula with
`WeightsConfig.secondaryPathPenalty (+0x15C)` applied. A 0.15 relative tolerance band
prefers closer tiles among near-equal scores.

#### Post-loop Adjustments

| Condition | Modification |
|---|---|
| `apCost < maxAP / 2` | `score *= WeightsConfig.shortRangePenalty (+0x168)` |
| Chain tile fits budget | `score *= 2.0` (forward) or `score *= 0.5` (backward) |
| Stance skill fits budget (`m_DefaultStanceSkill +0x58`) | `score *= WeightsConfig.stanceSkillBonus (+0x16C)` |

#### Best-tile Validation

```
if bestTile.tile == currentTile: return 0
if !forced:
    if GetCompositeScore(bestTile) < GetCompositeScore(currentTile) * WeightsConfig.minimumImprovementRatio (+0x150):
        return 0
```

#### Final Score Return

```
return (int)(fVar27 * WeightsConfig.finalMovementScoreScale (+0x128))
```

### Move.OnExecute (VA 0x180766370)

Four-stage state machine. Returns `false` while in progress, `true` when complete.

**Stage 0 — Re-routing setup** (when `m_IsMovementDone` true at entry):
Releases the reserved tile entity (`MovementEntity.Release`), claims the new target tile
entity (`MovementEntity.Claim`). Updates `m_PreviousContainerActor (+0x98)`.

**Stage 1 — UseSkillBefore loop:**
Iterates `m_UseSkillBefore (+0x70)` from `m_UseSkillBeforeIndex (+0x78)`. Calls
`Skill.Use(currentTile, flags=0x10)` for each. Returns `false` (not done) until all
pre-move skills are consumed.

**Stage 2 — Timer wait / movement trigger:**
Checks `Time.time >= m_WaitUntil (+0x90)`. Once elapsed, sets `m_IsExecuted (+0x8C) = true`
and `m_IsMovementDone = true`. Assembles a `flags` bitmask:
- bit 0 = `!Goal.IsEmpty(targetTile)`
- bit 1 = `Actor.CanDeploy()`
- bit 2 = `TileScore.isPeek (+0x61)`

Calls `Actor.StartMove(actor, targetTile, flags)`. If already at target, reads
`TileScore.stance (+0x62)` to set final stance.

**Stage 3 — UseSkillAfter loop:**
Iterates `m_UseSkillAfter (+0x80)` from `m_UseSkillAfterIndex (+0x88)`. Calls
`Skill.Activate(currentTile)` for each. Returns `false` until all are consumed.

**Stage 4 — Container exit / final activation:**
If `m_PreviousContainerActor (+0x98)` is set and has a ready ProximityData entry:
- If deployable: broadcasts container-exit event, calls `ContainerActor.Notify(1)`, returns `true`.
- Otherwise: evaluates strategy satisfaction, marks completion, returns `true`.

Final fallback: `Skill.Activate(currentTile)`. Returns `actor->field_0x15F == 0`.

---

## Field Offset Tables (Stage 2 additions)

### TileScore
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | tile | Tile* | confirmed |
| +0x18 | entity | Entity* | confirmed |
| +0x20 | movementScore | float | confirmed |
| +0x24 | secondaryMovementScore | float | confirmed |
| +0x28 | exposureScore | float | confirmed |
| +0x2C | rangeScore | float | confirmed |
| +0x30 | utilityScore | float | confirmed |
| +0x34 | coverScore | float | confirmed |
| +0x40 | apCost | int | confirmed |
| +0x44 | chainCost | int | confirmed |
| +0x48 | destinationRef | TileScore* | inferred |
| +0x50 | prevTileRef | TileScore* | inferred |
| +0x58 | nextTileRef | TileScore* | inferred |
| +0x60 | isForward | bool | inferred |
| +0x61 | isPeek | bool | confirmed |
| +0x62 | stance | byte | confirmed |

### BehaviorWeights (Strategy +0x310)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x14 | movementWeightMultiplier | float (≥1.0) | confirmed |
| +0x20 | movementWeight | float | confirmed |
| +0x2C | weightScale | float | confirmed |

### BehaviorConfig2 (AgentContext +0x50)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x28 | configFlagA | bool | confirmed |
| +0x34 | configFlagB | bool | confirmed |

### ProximityEntry (additions)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | tile | Tile* | confirmed |
| +0x18 | readyRound | int (-1=unassigned) | confirmed |
| +0x34 | type | int enum (0/1=valid, 2+=excluded) | confirmed |

### Agent (additions)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | agentContext | AgentContext* | confirmed |
| +0x18 | actor | Actor* | confirmed |
| +0x60 | tileDict | Dictionary<Tile,TileScore>* | confirmed (Stage 1) |

### Strategy (additions)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x2B0 | strategyData | StrategyData* | confirmed |
| +0x310 | behaviorWeights | BehaviorWeights* | confirmed |

### StrategyData (additions)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x60 | tierMode | int | inferred |
| +0x118 | reservedAP | int | confirmed |

### EntityInfo (additions)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x3C | minimumAP | int | confirmed |
| +0xEC bit 2 | isImmobile | bool | confirmed |

### WeightsConfig (additions this stage)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x54 | movementScoreWeight | float | confirmed |
| +0xBC | tagValueScale | float | confirmed |
| +0x128 | finalMovementScoreScale | float | confirmed |
| +0x12C | movementWeightScale | float | confirmed |
| +0x148 | movementScorePathWeight | float | inferred |
| +0x14C | pathCostPenaltyWeight | float | inferred |
| +0x150 | minimumImprovementRatio | float | confirmed |
| +0x154 | deployMovementScoreThreshold | float | confirmed |
| +0x15C | secondaryPathPenalty | float | confirmed |
| +0x168 | shortRangePenalty | float | confirmed |
| +0x16C | stanceSkillBonus | float | confirmed |

---

## Open Questions After Stage 2

**NQ-11** `FUN_1806361f0` — `StrategyData.ComputeMoveCost(...)`. The pathfinding cost
function called per-tile in `Move.OnEvaluate`. Returns int AP cost. Large function;
recommend a separate investigation stage.

**NQ-8** (partial) — GetOrder return values for `0x18050C760`, `0x180547170`,
`0x180546260` not yet decompiled. Low priority.