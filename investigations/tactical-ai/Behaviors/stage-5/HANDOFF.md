---
## Menace Tactical AI — Stage 4 Handoff Prompt

Read Research-AI.md in full before proceeding. Do not re-derive anything listed as confirmed below.

---

## DAT_ Symbol Map (cumulative)

DAT_18394c3d0 = WeightsConfig_class  (static storage: +0xb8 → ptr; ptr+8 → WEIGHTS singleton)
DAT_18394dc38 = Actor_class
DAT_18395f730 = BuffSkill_class
DAT_1839441d8 = AoE_scorer_class (passed to FUN_181430AC0)
DAT_183945130 = ListEnumerator_class (dispose)
DAT_1839ada98 = ListEnumerator_class2 (dispose)
DAT_1839451e8 = ListEnumerator_moveNext_class
DAT_1839adb50 = ListEnumerator_moveNext_class2
DAT_1839adc08 = (unknown — init guard only)
DAT_1839452a0 = (unknown — init guard only)
DAT_18399f748 = List_class (proximity list enumerator)
DAT_183968278 = List_class2 (tile list enumerator)
DAT_18398bd58 = List_append_class
DAT_183992e08 = SortedContainer_class
DAT_18399cc78 = SortedContainer_comparatorKey
DAT_183976118 = ShotCandidateWrapper_class
DAT_183b931f6 = Buff_class_init_guard
DAT_183b931fa = InflictDamage_class_init_guard
DAT_183b92f90 = PostProcessor_class_init_guard
DAT_18397ae78 = TagEffectivenessTable (static: +0x18=length int, +0x20=float[])

---

## FUN_ Symbol Map (cumulative)

FUN_180427b00 = il2cpp_runtime_class_init (lazy init guard — ignore)
FUN_180427d90 = NullReferenceException (does not return)
FUN_180427d80 = IndexOutOfRangeException (does not return)
FUN_180426e50 = IL2CPP write barrier (ignore semantically)
FUN_1804bad80 = powf(value, exponent)
FUN_180cbab80 = List.GetEnumerator
FUN_18136d8a0 = Dictionary.GetEnumerator
FUN_18152f9b0 = Dictionary enumerator MoveNext
FUN_1814f4770 = List enumerator MoveNext
FUN_1804f7ee0 = Enumerator.Dispose (end of foreach)
FUN_180426ed0 = IL2CPP allocate object
FUN_1804608d0 = Allocate/construct list or collection
FUN_180cca560 = List[index] get element
FUN_18073dd90 = SkillBehavior.GetTargetValue (public base scorer) — Stage 1
FUN_18073bfa0 = SkillBehavior.GetTagValueAgainst — Stage 2
FUN_18073af00 = InflictDamage.GetTargetValue — Stage 4 (prepend tag + delegate to base)
FUN_18073afe0 = InflictDamage.GetUtilityFromTileMult — Stage 4 (returns WeightsConfig +0x10C)
FUN_1807391c0 = Buff.GetTargetValue — Stage 4 (6-branch flag-driven scorer)
FUN_1806da770 = ShotCandidate_PostProcess — Stage 4 (packaging step, not scorer)
FUN_1806e2710 = TagEffectiveness_Apply(weaponData, tagIndex, 0) — NQ-20 (short, expected)
FUN_1806e33a0 = CanApplyBuff / eligibility check → bool — NQ-23
FUN_1805df080 = GetMissingHPAmount(actor) → float — NQ-24
FUN_1805dee10 = GetResistanceFraction(actor) → float [0,1] — NQ-25
FUN_181430ac0 = AoE_PerMemberScorer(skillRef, actor, &out, class [, accumulator]) → bool — NQ-26
FUN_180628210 = IsReadyToFire(entityInfo) → bool — NQ-28
FUN_180687590 = GetBuffStackCount(targetRef) → int — NQ-29
FUN_1806d5040 = ShotPath_ComputeDerivedMetric(shotPath) → val — NQ-22
FUN_180688600 = ResolveActor(targetRef) → Actor* (Tile→Actor cast or unwrap)
FUN_180722ed0 = TileHasAlly(tile) → bool
FUN_1805406a0 = IsActorInRange(tileRef, actorPos) → bool
FUN_1806f0e90 = SortedContainer.Insert(container, entry, key, 0)
FUN_1818897c0 = List.Append(list, item, class)
FUN_1804eb570 = Object.Init / constructor call
FUN_1806361f0 = StrategyData.ComputeMoveCost — deferred (NQ-11)
FUN_1806df4e0 = ComputeDamageData — Stage 1
FUN_1806e0ac0 = ComputeHitProbability — Stage 1
FUN_1806e66f0 = Skill.BuildCandidatesForShotGroup — Stage 3
FUN_1806de1d0 = Indirect fire trajectory builder — deferred
FUN_1806e1fb0 = AoE target set builder — deferred

---

## Field Offset Tables (cumulative — confirmed unless marked inferred)

### WeightsConfig (singleton via DAT_18394c3d0 +0xb8 +8)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x13C | utilityThreshold | float | confirmed |
| +0x54  | movementScoreWeight | float | confirmed |
| +0x78  | [scoring weight — TBD] | float | inferred |
| +0x7C  | allyCoFireBonus | float | inferred |
| +0xBC  | tagValueScale | float | confirmed |
| +0xC0  | baseAttackWeightScale | float | confirmed |
| +0xC4  | maxApproachRange | int | confirmed |
| +0xC8  | allyInRangeMaxDist | int | confirmed |
| +0xE0  | friendlyFirePenaltyWeight | float | confirmed |
| +0xE4  | killWeight | float | confirmed |
| +0xE8  | killWeight2 | float | confirmed |
| +0xEC  | urgencyWeight | float | confirmed |
| +0xF0  | buffWeight / allyCoFireWeight | float | confirmed |
| +0xF8  | proximityBonusCap | float | confirmed |
| +0xFC  | minAoeScoreThreshold | float | confirmed |
| +0x100 | allyCoFireBonusScale | float | confirmed |
| +0x10C | utilityFromTileMultiplier | float | confirmed — Stage 4 |
| +0x128 | finalMovementScoreScale | float | confirmed |
| +0x12C | movementWeightScale | float | confirmed |
| +0x148 | movementScorePathWeight | float | inferred |
| +0x14C | pathCostPenaltyWeight | float | inferred |
| +0x150 | minimumImprovementRatio | float | confirmed |
| +0x154 | deployMovementScoreThreshold | float | confirmed |
| +0x15C | secondaryPathPenalty | float | confirmed |
| +0x168 | shortRangePenalty | float | confirmed |
| +0x16C | stanceSkillBonus | float | confirmed |
| +0x174 | buffGlobalScoringScale | float | confirmed — Stage 4 |
| +0x17C | healScoringWeight | float | confirmed — Stage 4 |
| +0x180 | buffScoringWeight | float | confirmed — Stage 4 |
| +0x184 | suppressScoringWeight | float | confirmed — Stage 4 |
| +0x188 | setupAssistScoringWeight | float | confirmed — Stage 4 |
| +0x18C | aoeBuffScoringWeight | float | confirmed — Stage 4 |
| +0x190 | aoeHealScoringWeight | float | confirmed — Stage 4 |

### TileScore
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | tile | Tile* | confirmed |
| +0x18 | entity | Entity* | confirmed |
| +0x20 | movementScore | float | confirmed |
| +0x24 | secondaryMovementScore | float | confirmed |
| +0x28 | exposureScore | float | confirmed |
| +0x30 | rangeScore | float | confirmed |
| +0x34 | utilityScore | float | confirmed |
| +0x38 | movementScore (alt) | float | confirmed |
| +0x3C | secondaryMovementScore (alt) | float | confirmed |
| +0x40 | apCost | int | confirmed |
| +0x44 | chainCost | int | confirmed |
| +0x48 | destinationRef | TileScore* | inferred |
| +0x50 | prevTileRef | TileScore* | inferred |
| +0x58 | nextTileRef | TileScore* | inferred |
| +0x60 | isForward | bool | inferred |
| +0x61 | isPeek | bool | confirmed |
| +0x62 | stance | byte | confirmed |

### Attack
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x60 | m_Goal | Goal | confirmed |
| +0x68 | m_Candidates | List\<Attack.Data\>* | confirmed |
| +0x70 | m_TargetTiles | List\<Tile\>* | confirmed |
| +0x78 | m_PossibleOriginTiles | HashSet\<Tile\>* | confirmed |
| +0x80 | m_PossibleTargetTiles | HashSet\<Tile\>* | confirmed |
| +0x88 | m_MinRangeToOpponents | int | confirmed |

### Attack.Data
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x00 | targetTile | Tile* | confirmed |
| +0x30 | secondaryScore | float | confirmed |
| +0x3C | primaryScore | float | confirmed |
| +0x44 | apCost | int | confirmed |

### Assist / Assist.Data — unchanged from Stage 3

### BehaviorWeights (via Strategy +0x310)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x14 | movementWeightMultiplier | float (≥1.0) | confirmed |
| +0x20 | movementWeight | float | confirmed |
| +0x24 | weightScale | float | confirmed |
| +0x2C | weightScale2 | float | confirmed |

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
| +0x60 | tileDict | Dictionary\<Tile,TileScore\>* | confirmed |

### AgentContext
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | entity | EntityInfo* | confirmed |
| +0x50 | behaviorConfig | BehaviorConfig2* | confirmed |

### EntityInfo
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x14 | isActive | bool | confirmed |
| +0x18 | field_0x18 | ptr | inferred — weapon/tag object (NQ-19) |
| +0x20 | teamMembers | List\<Actor\>* | confirmed |
| +0x3C | minimumAP | int | confirmed |
| +0x48 | tileList | List\<Tile\>* | confirmed |
| +0xEC | flags (bit 0 = isImmobile) | uint | confirmed |
| +0x112 | hasSecondaryWeapon | bool | confirmed |
| +0x113 | hasSetupWeapon | bool | confirmed |
| +0x178 | shotGroupMode | int enum (0–5) | confirmed |
| +0x18C | arcCoveragePercent | int (0–100) | confirmed |
| +0x1A1 | isArcFixed | bool | confirmed |
| +0x2C8 | weaponData | [weapon block]* | confirmed |

### Strategy
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x8C | strategyMode | int (1 = no co-fire) | inferred |
| +0x2B0 | strategyData | StrategyData* | confirmed |
| +0x310 | behaviorWeights | BehaviorWeights* | confirmed |

### StrategyData
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x60 | tierMode | int | inferred |
| +0x118 | reservedAP | int | confirmed |

### Actor (partial)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x54 | currentHP | int | confirmed |
| +0x5C | currentHP alt | int | confirmed |
| +0x15C | isIncapacitated | bool | inferred |
| +0x162 | isDead | bool | confirmed |
| +0x167 | isWeaponSetUp | bool | confirmed |
| +0xC8 | buffDataBlock | ptr | inferred — sub-object; +0x34=contextScale float, +0x38=count int |
| +0xD0 | field_0xD0 | int | inferred — stance/setup state enum, checked ==1 (NQ-27) |

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

### Move, Skill, ShotPath, TagEffectivenessTable — unchanged from Stage 3

### BuffSkill (new — Stage 4)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x18 | flags | byte | confirmed — bit field encoding buff type |

**flags bit definitions:**
- bit 0  (0x0001) = Heal
- bit 1  (0x0002) = Status buff
- bit 15 (0x8000) = Suppress / debuff resistance
- bit 16 (0x10000) = Setup / stance assist
- bit 17 (0x20000) = AoE heal
- bit 18 (0x40000) = AoE buff

### ShotCandidateWrapper (new — Stage 4)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | shotPath | ShotPath* | confirmed |
| +0x18 | derivedMetric | unknown | confirmed (written; purpose NQ-22) |

---

## VA Status — All Stages

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
| 3 | 0x180735D20 | Attack.OnEvaluate | Complete |
| 3 | 0x180734130 | Attack.OnCollect | Complete |
| 3 | 0x180733650 | Attack.GetHighestScoredTarget | Complete |
| 3 | 0x180733890 | Attack.HasAllyLineOfSight | Complete |
| 3 | 0x18000DD30 | GetTargetValue_Dispatch7 | Complete (vtable shim) |
| 3 | 0x1806E66F0 | Skill.BuildCandidatesForShotGroup | Complete |
| 3 | 0x180731C60 | Assist.OnEvaluate | Complete |
| 3 | 0x180730B30 | Assist.OnCollect | Complete |
| 3 | 0x1807308F0 | Assist.GetHighestScoredTarget | Complete |
| 4 | 0x18073AF00 | InflictDamage.GetTargetValue | Complete |
| 4 | 0x18073AFE0 | InflictDamage.GetUtilityFromTileMult | Complete |
| 4 | 0x1807391C0 | Buff.GetTargetValue | Complete |
| 4 | 0x1806DA770 | ShotCandidate_PostProcess | Complete |

---

## Open Questions

[ ] NQ-4/5: WeightsConfig +0x78, +0x148, +0x14C still inferred.
    → Run extract_rvas.py on WeightsConfig class.
[ ] NQ-6: Skill +0x48 vs Skill +0x60 shot group lists — relationship unresolved.
    → Extract SkillBehavior class dump.
[ ] NQ-8 (partial): GetOrder return values for 0x18050C760, 0x180547170, 0x180546260 unknown.
    → Low priority; decompile any one (expected: return N).
[ ] NQ-9: FUN_1806f3c30 return convention (XOR 1 in SkillBehavior.OnExecute).
    → Validate against a leaf subclass OnExecute.
[ ] NQ-11: FUN_1806361f0 = StrategyData.ComputeMoveCost — large pathfinding cost function.
    → Analyse 0x1806361F0 if move cost formula needed.
[ ] NQ-13: WeightsConfig +0xF0 vs +0x100 — two co-fire weights; conditions unclear.
    → Cross-reference base scorer (Stage 1) against InflictDamage subclass if pursued further.
[ ] NQ-14: SkillBehavior +0x58 = chosenTarget storage slot.
    → Extract SkillBehavior class dump.
[ ] NQ-16: Strategy +0x8C = strategyMode (1 = no co-fire). Inferred.
    → Extract Strategy class; verify field name and enum values.
[ ] NQ-18: FUN_18000dcd0 — 5-arg GetTargetValue dispatch shim (Assist).
    → Low priority; confirm by reading (expected ~3 lines).
[ ] NQ-19: EntityInfo +0x18 — weapon/tag object. Not in confirmed table.
    → Extract EntityInfo class; confirm field at +0x18.
[ ] NQ-20: FUN_1806E2710(weaponData, tagIndex, 0) — tag effectiveness application.
    → Analyse 0x1806E2710; expected short lookup against TagEffectivenessTable.
[ ] NQ-21: Vtable slot +0x458 on EntityInfo->field_0x18 object — returns tag index.
    → Identify class type of EntityInfo +0x18; look up vtable slot.
[ ] NQ-22: FUN_1806D5040(ShotPath*) — derived metric in ShotCandidateWrapper +0x18. Low priority.
    → Analyse 0x1806D5040 if ShotCandidate scoring detail needed.
[ ] NQ-23: FUN_1806E33A0 — CanApplyBuff / eligibility check before buff scoring.
    → Analyse 0x1806E33A0 if Buff targeting rules needed.
[ ] NQ-24: FUN_1805DF080(actor) — missing HP / healable amount. Low priority.
    → Analyse 0x1805DF080 if heal formula input needs exact definition.
[ ] NQ-25: FUN_1805DEE10(actor) — resistance fraction [0,1]. Low priority.
    → Analyse 0x1805DEE10 if suppress formula input needs exact definition.
[ ] NQ-26: FUN_181430AC0 — AoE per-member scorer; 5-arg signature confirmed.
    → Analyse 0x181430AC0 if AoE buff/heal scoring detail required.
[ ] NQ-27: Actor +0xD0 — int checked ==1 in setup branch. Not in confirmed Actor table.
    → Extract Actor class; confirm field at +0xD0.
[ ] NQ-28: FUN_180628210(entityInfo) — IsReadyToFire or similar. Low priority.
    → Analyse 0x180628210 if setup scoring conditions need clarification.
[ ] NQ-29: FUN_180687590(targetRef) — GetBuffStackCount or similar. Low priority.
    → Analyse 0x180687590 if stack-count scaling needs clarification.

---

## Scope Boundaries (cumulative)

The following are explicitly out of scope:
- Concrete GetTargetValue overrides other than InflictDamage and Buff: InflictSuppression, Stun, SupplyAmmo, TargetDesignator, SpawnHovermine, SpawnPhantom — base dispatch confirmed; per-skill formulas deferred
- FUN_1806DE1D0 (indirect fire trajectory builder, mode 3) — separate system
- FUN_1806E1FB0 (AoE target set builder, mode 2) — deferred
- StrategyData.ComputeMoveCost (FUN_1806361F0) — pathfinding internals
- Concrete OnCollect for non-Attack/Assist subclasses
- Attack.OnExecute, Assist.OnExecute — execution phase

---

## Next Priority Table

The core scoring pipeline is fully understood. Remaining high-value targets are the tag
effectiveness chain (NQ-19/20/21) and the AoE per-member scorer (NQ-26).
Prioritise the tag chain first as it closes the only remaining gap in InflictDamage scoring.

| Priority | Method | VA | Rationale |
|---|---|---|---|
| 1 | FUN_1806E2710 | 0x1806E2710 | Tag effectiveness apply (NQ-20); expected short; closes InflictDamage co-fire tag chain |
| 2 | FUN_181430AC0 | 0x181430AC0 | AoE per-member scorer (NQ-26); closes AoE branch detail for Buff |
| 3 | FUN_1806E33A0 | 0x1806E33A0 | CanApplyBuff eligibility check (NQ-23); expected moderate length |
| 4 | FUN_1806D5040 | 0x1806D5040 | ShotCandidate derived metric (NQ-22); expected short |

Batch priorities 1+4 (both expected short) and request together. Then 2+3 as second batch.

---
