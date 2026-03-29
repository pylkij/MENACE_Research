## Field Offset Tables

### WeightsConfig (singleton via DAT_18394c3d0 +0xb8 +8)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x13C | utilityThreshold | float | confirmed |
| +0x54 | movementScoreWeight | float | confirmed |
| +0x78 | [scoring weight — TBD] | float | inferred |
| +0x7C | allyCoFireBonus | float | inferred |
| +0xBC | tagValueScale | float | confirmed |
| +0xE4 | killWeight | float | confirmed |
| +0xE8 | killWeight2 | float | confirmed |
| +0xEC | urgencyWeight | float | confirmed |
| +0xF0 | buffWeight / allyCoFireWeight | float | confirmed |
| +0xF8 | proximityBonusCap | float | confirmed |
| +0x128 | finalMovementScoreScale | float | confirmed |
| +0x12C | movementWeightScale | float | confirmed |
| +0x148 | movementScorePathWeight | float | inferred |
| +0x14C | pathCostPenaltyWeight | float | inferred |
| +0x150 | minimumImprovementRatio | float | confirmed |
| +0x154 | deployMovementScoreThreshold | float | confirmed |
| +0x15C | secondaryPathPenalty | float | confirmed |
| +0x168 | shortRangePenalty | float | confirmed |
| +0x16C | stanceSkillBonus | float | confirmed |

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

### BehaviorWeights (via Strategy +0x310)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x14 | movementWeightMultiplier | float (≥1.0) | confirmed |
| +0x20 | movementWeight | float | confirmed |
| +0x2C | weightScale | float | confirmed |

### BehaviorConfig2 (via AgentContext +0x50)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x28 | configFlagA | bool | confirmed |
| +0x34 | configFlagB | bool | confirmed |

### Agent
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | agentContext | AgentContext* | confirmed |
| +0x18 | actor | Actor* | confirmed |
| +0x60 | tileDict | Dictionary<Tile,TileScore>* | confirmed |

### AgentContext
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x50 | behaviorConfig | BehaviorConfig2* | confirmed |

### Strategy
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x2B0 | strategyData | StrategyData* | confirmed |
| +0x310 | behaviorWeights | BehaviorWeights* | confirmed |

### StrategyData
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x60 | tierMode | int | inferred |
| +0x118 | reservedAP | int | confirmed |

### EntityInfo
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x3C | minimumAP | int | confirmed |
| +0xEC | flags (bit 2 = isImmobile) | uint | confirmed |

### Actor (partial)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x18 | [reserved — see Agent] | | |
| +0x54 | currentHP | int | confirmed |
| +0x5C | currentHP alt | int | confirmed |
| +0x167 | isWeaponSetUp | bool | confirmed |

### StrategyModifiers
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x14 | thresholdMultA | float (raises only) | confirmed |
| +0x18 | thresholdMultB | float (bidirectional) | confirmed |

### ProximityEntry
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | tile | Tile* | confirmed |
| +0x18 | readyRound | int (-1=unassigned) | confirmed |
| +0x34 | type | int enum (0/1=valid, 2+=excluded) | confirmed |

### Move
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x20 | m_IsMovementDone | bool | confirmed |
| +0x21 | m_HasMovedThisTurn | bool | confirmed |
| +0x22 | m_HasDelayedMovementThisTurn | bool | confirmed |
| +0x23 | m_HasMovedThisTurnBit | bool | confirmed |
| +0x24 | m_IsAllowedToPeekInAndOutOfCover | bool | confirmed |
| +0x28 | m_TargetTile | TileScore* | confirmed |
| +0x30 | m_ReservedTile | Tile* | confirmed |
| +0x38 | m_TurnsBelowUtilityThreshold | int | confirmed |
| +0x3C | m_TurnsBelowUtilityThresholdLastTurn | int | confirmed |
| +0x40 | m_Destinations | List<TileScore>* | confirmed |
| +0x48 | m_Path | List<Vector3>* | confirmed |
| +0x50 | m_AlternativePath | List<Vector3>* | confirmed |
| +0x58 | m_DeployedStanceSkill | Skill* | confirmed |
| +0x60 | m_DefaultStanceSkill | Skill* | confirmed |
| +0x68 | m_SetupWeaponSkill | Skill* | confirmed |
| +0x70 | m_UseSkillBefore | List<Skill>* | confirmed |
| +0x78 | m_UseSkillBeforeIndex | int | confirmed |
| +0x80 | m_UseSkillAfter | List<Skill>* | confirmed |
| +0x88 | m_UseSkillAfterIndex | int | confirmed |
| +0x8C | m_IsExecuted | bool | confirmed |
| +0x90 | m_WaitUntil | float | confirmed |
| +0x94 | m_IsInsideContainerAndInert | bool | confirmed |
| +0x98 | m_PreviousContainerActor | Actor* | confirmed |

### ShotPath (partial)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x78 | minimumHitChance | int | confirmed |
| +0x8C | accuracyMult | float | confirmed |
| +0x110 | altDistancePenaltyCoeff | float | confirmed |
| +0x128 | movementAccuracyPenaltyPerTile | float | confirmed |
| +0x13C | thirdDistanceModifier | float | confirmed |
| +0x140 | overallAccuracyMultiplier | float | confirmed |
| +0x144 | hpAccuracyCoeff | float | confirmed |
| +0x148 | hpAccuracyFloor | float | confirmed |
| +0x14C | apAccuracyCoeff | float | confirmed |
| +0x150 | apAccuracyFloor | float | confirmed |
| +0x16C | baseExtraHits | int | confirmed |
| +0x170 | burstFraction | float | confirmed |

### TagEffectivenessTable (DAT_18397ae78)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x18 | length | int | confirmed |
| +0x20 | values[] | float[] | confirmed |

---

## VAs Analysed — All Stages

| Stage | VA | Method | Status |
|---|---|---|---|
| 1 | 0x180738E60 | Behavior.Evaluate | Complete |
| 1 | 0x180738F40 | Behavior.Execute | Complete |
| 1 | 0x18073E300 | SkillBehavior.OnExecute | Complete |
| 1 | 0x18073DF70 | SkillBehavior.HandleDeployAndSetup | Complete |
| 1 | 0x180739050 | Behavior.GetUtilityThreshold | Complete |
| 1 | 0x180738D10 | Behavior.Collect | Complete |
| 1 | 0x18073BDD0 | SkillBehavior.ConsiderSkillSpecifics | Complete |
| 1 | 0x18073DD90 | SkillBehavior.GetTargetValue (public) | Complete |
| 1 | 0x18073C130 | SkillBehavior.GetTargetValue (private) | Complete |
| 1 | 0x1806E0AC0 | ComputeHitProbability | Complete |
| 1 | 0x1806DF4E0 | ComputeDamageData | Complete |
| 2 | 0x18073BFA0 | SkillBehavior.GetTagValueAgainst | Complete |
| 2 | 0x180717730 | ProximityData.FindEntryForTile | Complete |
| 2 | 0x180717A40 | ProximityEntry.IsValidType | Complete |
| 2 | 0x180519A90 | GetOrder (Deploy/Idle = 0) | Complete |
| 2 | 0x180717870 | ProximityData.HasReadyEntry | Complete |
| 2 | 0x180738FE0 | Behavior.GetBehaviorWeights | Complete |
| 2 | 0x180739020 | Behavior.GetBehaviorConfig2 | Complete |
| 2 | 0x1807632F0 | Move.HasUtility | Complete |
| 2 | 0x1807629F0 | Move.GetAddedScoreForPath | Complete |
| 2 | 0x180762EB0 | Move.GetHighestTileScore | Complete |
| 2 | 0x180762D60 | Move.GetHighestTileScoreScaled | Complete |
| 2 | 0x1807635C0 | Move.OnEvaluate | Complete |
| 2 | 0x180766370 | Move.OnExecute | Complete |

---

## Open Questions

[ ] NQ-11: FUN_1806361f0 = StrategyData.ComputeMoveCost — pathfinding cost function called per-tile in Move.OnEvaluate. Returns int AP cost. → Separate stage recommended; large function.
[ ] NQ-8 (partial): GetOrder return values for 0x18050C760, 0x180547170, 0x180546260 unknown. → Low priority; decompile any one (expected: return N;).
[ ] NQ-4/5: WeightsConfig full field map. Fields at +0x78, +0x148, +0x14C still inferred. → Run extract_rvas.py on WeightsConfig class; full dump needed.
[ ] NQ-6: Skill+0x48 = shotGroups list confirmed on Skill not SkillBehavior. → Verify with extract_rvas.py on Skill class.
[ ] NQ-9: FUN_1806f3c30 return convention (XOR 1 in SkillBehavior.OnExecute Stage 4). → Validate against a leaf subclass OnExecute.

---

## Scope Boundaries

- `FUN_1806361f0` (StrategyData.ComputeMoveCost) — pathfinding internals. Deferred; separate stage.
- Concrete OnCollect implementations for all subclasses — deferred until base is fully mapped.
- Subclasses with NO_RVA on GetTargetValue/GetUtilityFromTileMult (Assist, Attack) — these are inherited from SkillBehavior; already covered by Stage 1.

---

## Next Priority Table

Continue from here. Analyse in order.

| Priority | Method | VA | Rationale |
|---|---|---|---|
| 1 | Attack.OnEvaluate | 0x180735D20 | Core attack scoring; exercises fully-understood shot pipeline. Highest value. |
| 2 | Attack.OnCollect | 0x180734130 | Populates m_Candidates and tile sets. Needed to understand what Attack.OnEvaluate scores over. |
| 3 | Attack.GetHighestScoredTarget | 0x180733650 | Winner selection from m_Candidates. Expected short. |

Batch priorities 1–3 — they form Attack's complete scoring pipeline and can be exported together.

Prioritise `Attack` and `Assist` as they are the most impactful on gameplay.

---

## Instructions for This Session

1. Read Research-AI.md in full.
2. Review all symbol maps and field tables above — treat them as confirmed prior work.
3. Do not re-derive anything already listed as confirmed. Build on it.
4. Do not request or reference stage artefact files during analysis.
5. Continue from the Next Priority Table above. Request Ghidra output for priorities 1–3 first.
6. Flag any scope expansion immediately before pursuing it.
7. When this stage is complete, invoke the research-handoff skill to produce stage artefacts and the next handoff prompt.