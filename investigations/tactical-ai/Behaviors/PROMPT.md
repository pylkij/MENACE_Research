# Investigation Handoff — Menace Tactical AI — Stage 6 → COLLATION

## Directive
Read Research-AI.md and Handoff-AI.md in full before proceeding.
This is the FINAL stage handoff. Do not produce another handoff prompt.
Invoke the research-handoff skill in collation mode to produce the final unified
REPORT.md and RECONSTRUCTIONS.md from all stage artefacts listed below.

## Investigation Target
- **Game:** Menace (Windows x64, Unity IL2CPP)
- **Image base:** 0x180000000
- **System under investigation:** Menace.Tactical.AI — full tactical AI behavior system
- **Investigation status:** COMPLETE — all stages analysed, ready for collation
- **Stage:** Collation (post Stage 6)
- **VAs complete across all stages:** 52

## Stage Artefacts on Disk
The operator has saved the following. Treat all as confirmed — do not re-derive.
```
tactical-ai/stage-1/REPORT.md
tactical-ai/stage-1/RECONSTRUCTIONS.md
tactical-ai/stage-2/REPORT.md
tactical-ai/stage-2/RECONSTRUCTIONS.md
tactical-ai/stage-3/REPORT.md
tactical-ai/stage-3/RECONSTRUCTIONS.md
tactical-ai/stage-4/REPORT.md
tactical-ai/stage-4/RECONSTRUCTIONS.md
tactical-ai/stage-5/REPORT.md
tactical-ai/stage-5/RECONSTRUCTIONS.md
tactical-ai/stage-6/REPORT.md
tactical-ai/stage-6/RECONSTRUCTIONS.md
```

---

## Resolved Symbol Maps

### FUN_ → Method Name
```
FUN_180738E60 = Behavior.Evaluate
FUN_180738F40 = Behavior.Execute
FUN_18073E300 = SkillBehavior.OnExecute
FUN_18073DF70 = SkillBehavior.HandleDeployAndSetup
FUN_180739050 = Behavior.GetUtilityThreshold
FUN_180738D10 = Behavior.Collect
FUN_18073BDD0 = SkillBehavior.ConsiderSkillSpecifics
FUN_18073DD90 = SkillBehavior.GetTargetValue_Public
FUN_18073C130 = SkillBehavior.GetTargetValue_Private
FUN_1806E0AC0 = Skill.GetHitchance                    // confirmed class name: Menace.Tactical.Skills.Skill
FUN_1806DF4E0 = Skill.GetExpectedDamage               // ComputeDamageData alias
FUN_18073BFA0 = SkillBehavior.GetTagValueAgainst
FUN_180717730 = ProximityData.FindEntryForTile
FUN_180717A40 = ProximityEntry.IsValidType
FUN_180519A90 = GetOrder_Deploy_Idle                  // returns 0
FUN_180717870 = ProximityData.HasReadyEntry
FUN_180738FE0 = Behavior.GetBehaviorWeights
FUN_180739020 = Behavior.GetBehaviorConfig2
FUN_1807632F0 = Move.HasUtility
FUN_1807629F0 = Move.GetAddedScoreForPath
FUN_180762EB0 = Move.GetHighestTileScore
FUN_180762D60 = Move.GetHighestTileScoreScaled
FUN_1807635C0 = Move.OnEvaluate
FUN_180766370 = Move.OnExecute
FUN_180735D20 = Attack.OnEvaluate
FUN_180734130 = Attack.OnCollect
FUN_180733650 = Attack.GetHighestScoredTarget
FUN_180733890 = Attack.HasAllyLineOfSight
FUN_18000DD30 = GetTargetValue_Dispatch7
FUN_1806E66F0 = Skill.QueryTargetTiles                // BuildCandidatesForShotGroup alias
FUN_180731C60 = Assist.OnEvaluate
FUN_180730B30 = Assist.OnCollect
FUN_1807308F0 = Assist.GetHighestScoredTarget
FUN_18073AF00 = InflictDamage.GetTargetValue
FUN_18073AFE0 = InflictDamage.GetUtilityFromTileMult
FUN_1807391C0 = Buff.GetTargetValue
FUN_1806DA770 = ShotCandidate_PostProcess
FUN_1806E2710 = TagEffectiveness_Apply
FUN_181430AC0 = AoE_PerMemberScorer
FUN_1806E33A0 = CanApplyBuff
FUN_1806D5040 = ShotPath_ActorCast
FUN_18073B240 = InflictSuppression.GetTargetValue
FUN_18073B320 = InflictSuppression.GetUtilityFromTileMult
FUN_180769B40 = Stun.GetTargetValue
FUN_180762550 = Mindray.GetTargetValue
FUN_18076A640 = TargetDesignator.GetTargetValue
FUN_180769E60 = SupplyAmmo.GetTargetValue
FUN_180769450 = SpawnPhantom.GetTargetValue
FUN_180768EF0 = SpawnHovermine.GetTargetValue
FUN_18075EB90 = CreateLOSBlocker.GetTargetValue
FUN_18073A0C0 = Deploy.GetHighestTileScore
FUN_18073A260 = Deploy.OnCollect
FUN_18073AD00 = Deploy.OnEvaluate
FUN_18073ADD0 = Deploy.OnExecute
FUN_180740F20 = TileScore_GetCompositeScore           // NQ-41; exact impl unknown
FUN_18071B640 = AgentContext_GetCandidateSource       // NQ-44; returns walk range or ProximityData
FUN_1806343A0 = EvaluateTileFromCoords                // NQ-45; path/tile eval → fills TileScore list
FUN_18053FEB0 = ComputeDistance                       // NQ-46; int distance/count result
FUN_1805CA7A0 = Tile_Distance                         // NQ-49; tile-to-tile distance
FUN_1806889C0 = Tile_IsOccupied                       // confirmed by context in multiple functions
FUN_1805E03B0 = Actor_MoveToTile                      // issues move command
FUN_180427B00 = il2cpp_runtime_class_init             // IL2CPP lazy init; always ignore
FUN_180427D90 = NullReferenceException                // IL2CPP null guard; always throws
FUN_180427D80 = IndexOutOfRangeException              // IL2CPP bounds check; always throws
FUN_180426E50 = il2cpp_write_barrier                  // GC write barrier; ignore semantically
FUN_18136D8A0 = Dictionary_GetEnumerator
FUN_18152F9B0 = Dictionary_MoveNext
FUN_180CBB80  = List_GetEnumerator                   // FUN_180cbab80
FUN_1814F4770 = List_MoveNext
FUN_1804F7EE0 = Enumerator_Dispose
FUN_180CCA560 = List_GetAtIndex
FUN_1804608D0 = AllocateObject
FUN_18073B950 = ProximityData_GetEntriesOfType        // fills list with entries of given type
FUN_180688600 = Tile_GetData
FUN_180616AF0 = TileData_CheckConditionA
FUN_180616B30 = TileData_CheckConditionB
FUN_180616780 = TileData_CheckConditionC
FUN_181421D50 = TileDict_ContainsTile
FUN_180741530 = TileScore_Init
FUN_181446C90 = TileDict_Add
FUN_181B73D10 = Array_Clear
FUN_1804BAD80 = powf
```

### DAT_ → Class / Static Field
```
DAT_18394c3d0 = WeightsConfig_class                  // IL2CPP class metadata; true class name UNRESOLVED
DAT_183981f50 = Strategy_class                       // IL2CPP class metadata; true class name UNRESOLVED
DAT_183977938 = Dictionary_TileScore_class           // enumerator class token
DAT_18395be38 = DictEnumerator_dispose_class
DAT_18395bef8 = DictEnumerator_movenext_class
DAT_18395bfb0 = DictEnumerator_class
DAT_18398e1b8 = TileScore_class
DAT_1839863c8 = CandidateList_class
DAT_18399f520 = CandidateList_init_class
DAT_183983180 = PathList_class
DAT_18398b6e8 = PathList_init_class
DAT_18399f748 = ListEnumerator_class
DAT_1839451e8 = List_MoveNext_class
DAT_18398bb30 = PathList_enum_class
DAT_18393e1c8 = PathListEntry_movenext_class
DAT_18393e110 = PathListEntry_dispose_class
DAT_18398e100 = TileDict_class
DAT_1839452a0 = TileDict_enum_class
DAT_1839a25c0 = TeamMembers_enum_class
DAT_183993d68 = TeamMembers_movenext_class
DAT_183993cb0 = TeamMembers_dispose_class
DAT_183945130 = CandidateList_dispose_class
DAT_18393e280 = secondary_enum_dispose_class
DAT_1839888f0 = TileScoreEntry_class
DAT_183993e20 = tertiary_movenext_class
DAT_18398b9c8 = tertiary_class
DAT_18399f800 = tertiary_init_class
DAT_183977878 = WeightsConfig_secondary_class
DAT_183977c38 = WeightsConfig_tertiary_class
DAT_18398bb30 = PathList_enum_class
```

---

## Field Offset Tables

### WeightsConfig (IL2CPP class name UNRESOLVED — accessed via DAT_18394c3d0 + 0xb8 + 8)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x54 | movementScoreWeight | float | confirmed |
| +0x78 | [scoring weight] | float | inferred |
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
| +0x148 | movementScorePathWeight | float | inferred |
| +0x14C | pathCostPenaltyWeight | float | inferred |
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

### TileScore
| Offset | Field Name | Type | Status |
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
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x60 | m_Goal | Goal | confirmed |
| +0x68 | m_Candidates | List<Attack.Data>* | confirmed |
| +0x70 | m_TargetTiles | List<Tile>* | confirmed |
| +0x78 | m_PossibleOriginTiles | HashSet<Tile>* | confirmed |
| +0x80 | m_PossibleTargetTiles | HashSet<Tile>* | confirmed |
| +0x88 | m_MinRangeToOpponents | int | confirmed |

### Attack.Data
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x00 | targetTile | Tile* | confirmed |
| +0x30 | secondaryScore | float | confirmed |
| +0x3C | primaryScore | float | confirmed |
| +0x44 | apCost | int | confirmed |

### BehaviorWeights (via Strategy +0x310)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x14 | movementWeightMultiplier | float | confirmed |
| +0x20 | movementWeight | float | confirmed |
| +0x24 | weightScale | float | confirmed |
| +0x2C | weightScale2 | float | confirmed |

### BehaviorConfig2 (via AgentContext +0x50 — NQ-42: label may be wrong)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x28 | configFlagA | bool | confirmed |
| +0x34 | configFlagB | bool | confirmed |

### Agent
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x10 | agentContext | AgentContext* | confirmed |
| +0x18 | actor | Actor* | confirmed |
| +0x60 | tileDict | Dictionary<Tile,TileScore>* | confirmed |

### AgentContext (IL2CPP class name UNRESOLVED)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x10 | entityInfo | EntityInfo* | confirmed |
| +0x50 | behaviorConfig OR deployCompleteFlag | BehaviorConfig2* OR byte | CONFLICTED — NQ-42 |

### EntityInfo (IL2CPP class name UNRESOLVED)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x14 | isActive / teamID | bool/int | confirmed |
| +0x18 | weaponTagObject | ptr | inferred — NQ-19 |
| +0x20 | teamMembers | List<Actor>* | confirmed |
| +0x3C | minimumAP | int | confirmed |
| +0x48 | tileList | List<Tile>* | confirmed |
| +0xA8 | statusFlags2 | uint (bit 0x100 = mindrayVulnerable) | confirmed — NQ-38 |
| +0xDC | detectionValue | float | inferred — SpawnPhantom |
| +0xEC | flags (bit 0=immobile, bit 5=isPhantom, bit 7=skipMindray, bit 11=alreadyDesignated) | uint | confirmed |
| +0x112 | hasSecondaryWeapon | bool | confirmed |
| +0x113 | hasSetupWeapon | bool | confirmed |
| +0x178 | shotGroupMode | int enum (0–5) | confirmed |
| +0x18C | arcCoveragePercent | int (0–100) | confirmed |
| +0x1A1 | isArcFixed | bool | confirmed |
| +0x2C8 | weaponData | ptr | confirmed |

### Strategy (IL2CPP class name UNRESOLVED — accessed via DAT_183981f50 + 0xb8)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x28 | strategyDataSubRef | ptr | confirmed — Deploy.OnCollect |
| +0x60 | strategyMode | int (non-zero = suppress behaviors) | confirmed |
| +0x8C | strategyMode (alt ref) | int (1=no co-fire) | inferred |
| +0x2B0 | strategyData | StrategyData* | confirmed |
| +0x310 | behaviorWeights | BehaviorWeights* | confirmed |

### StrategyData (IL2CPP class name UNRESOLVED)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x60 | tierMode | int | inferred |
| +0x118 | reservedAP | int | confirmed |

### Actor (partial)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x50 | isSetUp_alt | bool | confirmed — Deploy.OnCollect ally proximity check |
| +0x54 | currentHP | int | confirmed |
| +0x5C | currentHP alt | int | confirmed |
| +0x15C | isWeaponSetUp | bool | confirmed |
| +0x15F | field_0x15F | bool | confirmed — Deploy.OnExecute return value |
| +0x162 | isDead | bool | confirmed |
| +0x167 | isWeaponSetUp (alt) | bool | confirmed |
| +0xC8 | buffDataBlock | ptr (+0x34=contextScale float, +0x38=stackCount int) | inferred |
| +0xD0 | secondaryWeaponState | int (checked != 0) | inferred |

### Deploy
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x010 | agentContext | AgentContext* | confirmed — inherited from Behavior |
| +0x01C | field_0x1c | bool | confirmed — base Behavior "target set" flag |
| +0x020 | m_TargetTile | Tile* | confirmed |
| +0x028 | m_IsDone | bool | confirmed |

### BuffSkill
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x18 | flags (bit 0=Heal, 1=StatusBuff, 15=Suppress, 16=Setup, 17=AoEHeal, 18=AoEBuff) | byte | confirmed |
| +0x48 | conditions | List<Condition>* | confirmed |

### ShotCandidateWrapper
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x10 | shotPath | ShotPath* | confirmed |
| +0x18 | targetActor | Actor* | confirmed — NQ-22 resolved |

### ShotPath
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x30 | targetActor (raw) | ptr (Actor* or null) | confirmed |

### WeaponData (partial)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x48 | tagModifiers | TagModifierList* | confirmed |
| +0xA8 | tagApplicationCap | uint | confirmed |

### AoETierTable
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x18 | count | int | confirmed |
| +0x20 + (n×0x18) | entries[n] | AoETierEntry (24 bytes) | confirmed |
| entry+0x00 | score | float | confirmed |

### PlacementCandidate
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x28 | losImpact | float (negative = blocks LOS) | confirmed |

### ProximityEntry
| Offset | Field Name | Type | Status |
|---|---|---|---|
| +0x10 | tile | Tile* | confirmed |
| +0x18 | readyRound | int (-1=unassigned) | confirmed |
| +0x34 | type | int enum (0/1=valid, 2+=excluded) | confirmed |
| +0x88 | weight | float | confirmed — TargetDesignator |

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
| 1 | 0x1806E0AC0 | Skill.GetHitchance | Complete |
| 1 | 0x1806DF4E0 | Skill.GetExpectedDamage | Complete |
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
| 3 | 0x18000DD30 | GetTargetValue_Dispatch7 | Complete |
| 3 | 0x1806E66F0 | Skill.QueryTargetTiles | Complete |
| 3 | 0x180731C60 | Assist.OnEvaluate | Complete |
| 3 | 0x180730B30 | Assist.OnCollect | Complete |
| 3 | 0x1807308F0 | Assist.GetHighestScoredTarget | Complete |
| 4 | 0x18073AF00 | InflictDamage.GetTargetValue | Complete |
| 4 | 0x18073AFE0 | InflictDamage.GetUtilityFromTileMult | Complete |
| 4 | 0x1807391C0 | Buff.GetTargetValue | Complete |
| 4 | 0x1806DA770 | ShotCandidate_PostProcess | Complete |
| 5 | 0x1806E2710 | TagEffectiveness_Apply | Complete |
| 5 | 0x181430AC0 | AoE_PerMemberScorer | Complete |
| 5 | 0x1806E33A0 | CanApplyBuff | Complete |
| 5 | 0x1806D5040 | ShotPath_ActorCast | Complete |
| 5 | 0x18073B240 | InflictSuppression.GetTargetValue | Complete |
| 5 | 0x18073B320 | InflictSuppression.GetUtilityFromTileMult | Complete |
| 5 | 0x180769B40 | Stun.GetTargetValue | Complete |
| 5 | 0x180762550 | Mindray.GetTargetValue | Complete |
| 5 | 0x18076A640 | TargetDesignator.GetTargetValue | Complete |
| 5 | 0x180769E60 | SupplyAmmo.GetTargetValue | Complete |
| 5 | 0x180769450 | SpawnPhantom.GetTargetValue | Complete |
| 5 | 0x180768EF0 | SpawnHovermine.GetTargetValue | Complete |
| 5 | 0x18075EB90 | CreateLOSBlocker.GetTargetValue | Complete |
| 6 | 0x18073A0C0 | Deploy.GetHighestTileScore | Complete |
| 6 | 0x18073A260 | Deploy.OnCollect | Complete |
| 6 | 0x18073AD00 | Deploy.OnEvaluate | Complete |
| 6 | 0x18073ADD0 | Deploy.OnExecute | Complete |

---

## Open Questions

[ ] NQ-4/5: WeightsConfig +0x78, +0x148, +0x14C names unresolved → Resolve WeightsConfig true class name first
[ ] NQ-6: Skill +0x48 vs +0x60 shot group lists — Stage 6 dump.cs confirms m_SelectedTiles at +0x60; SkillBehavior +0x48 is a different class → Close at collation
[ ] NQ-16: Strategy +0x8C strategyMode inferred; true class name unresolved → Resolve via dump.cs (see class name note below)
[ ] NQ-19: EntityInfo +0x18 weapon/tag object unconfirmed → Resolve EntityInfo true class name
[ ] NQ-21: Vtable +0x458 on EntityInfo+0x18 object → Deferred; low impact
[ ] NQ-33: FUN_181423600 = GetAoETierForMember → Deferred; analyse 0x181423600 if AoE tier logic needed
[ ] NQ-37: InflictSuppression/InflictDamage effectType=1 equivalence → Analyse SkillBehavior.GetTargetValue private (0x18073C130) arg5 branching
[ ] NQ-38: EntityInfo +0xA8 bit 0x100 = mindray vulnerability field name → Resolve EntityInfo class name
[ ] NQ-39: EntityInfo flags bit 11 = alreadyDesignated field name → Resolve EntityInfo class name
[ ] NQ-40: FUN_1806E3750 = IsInDesignationZone → Deferred; low priority
[ ] NQ-41: FUN_180740F20 = TileScore composite score getter → Low priority; analyse 0x180740F20 if tile selection ordering matters
[ ] NQ-42: AgentContext +0x50 label conflict — previously labelled behaviorConfig*, but Deploy writes byte 1 to it directly → MUST resolve at collation; extract AgentContext true class name
[ ] NQ-43: entity +0xcc bool read via vtable +0x398 in Deploy.OnCollect → Low priority
[ ] NQ-44: FUN_18071B640 = AgentContext_GetCandidateSource → Medium priority; analyse if Deploy collection tracing needed
[ ] NQ-45: FUN_1806343A0 = EvaluateTileFromCoords → Medium priority; analyse if tile scoring pipeline tracing needed
[ ] NQ-46: FUN_18053FEB0 = ComputeDistance → Low priority
[ ] NQ-47: WeightsConfig +0xcc name → Close when WeightsConfig class name resolved
[ ] NQ-48: Actor +0x50 bool = isSetUp_alt → Confirm against Actor class dump
[ ] NQ-49: FUN_1805CA7A0 = Tile_Distance → Low priority
[ ] NQ-50: WeightsConfig +0xd0 name → Close when WeightsConfig class name resolved

---

## Unresolved Class Names — Critical Note for Collation

The following investigation-internal names do NOT match any IL2CPP class name in dump.cs.
All are accessed through opaque DAT_ metadata pointers. Field offsets are confirmed;
class names are not. Flag all as "IL2CPP class name unresolved" in the final report.

| Investigation Name | DAT_ Pointer | Recommended Resolution |
|---|---|---|
| WeightsConfig | DAT_18394c3d0 | Search dump.cs for static field of float-heavy type under Menace.Tactical.AI |
| AgentContext | (held at Behavior+0x10) | Search dump.cs for class with field of EntityInfo type at +0x10 |
| EntityInfo | (held at AgentContext+0x10) | Search dump.cs for class with List<Actor> at +0x20 |
| Strategy (AI) | DAT_183981f50 | Search dump.cs for GetBehaviorWeights or GetBehaviorConfig method names |
| BehaviorConfig2 | (held at AgentContext+0x50) | NQ-42 conflict — resolve AgentContext first |
| BehaviorWeights | (held at Strategy+0x310) | Resolve Strategy first |
| StrategyData | (held at Strategy+0x2B0) | Resolve Strategy first |

---

## Scope Boundaries

The following are explicitly out of scope and must not be pursued in collation:
- Deploy.OnReset (RVA 0x71E0E0) — bookkeeping only
- GainBonusTurn, Reload, Scan, MovementSkill, RemoveStatusEffect — untouched
- TurnArmorTowardsThreat, TransportEntity — untouched
- FUN_1806DE1D0 (indirect fire trajectory builder) — separate system
- FUN_1806E1FB0 (AoE target set builder) — separate system
- StrategyData.ComputeMoveCost (FUN_1806361F0) — pathfinding internals
- Concrete Condition.Evaluate subclasses — interface documented; implementations deferred
- GetAoETierForMember (FUN_181423600) — deferred

---

## Instructions for This Session

1. Read Research-AI.md and Handoff-AI.md in full.
2. This is the collation session. Do not analyse new Ghidra functions.
3. Attach the 6 REPORT.md stage artefact files listed above.
4. Invoke the research-handoff skill in collation mode.
5. Apply collation rules from Handoff-AI.md Part 5:
   - Deduplicate all field tables (one table per class)
   - Enforce leaf-first function ordering across all stages
   - Write unified narrative — do not reference stage numbers
   - Resolve cross-stage open questions where later stages answered earlier ones
   - Mark all unresolved class names explicitly (see table above)
   - Consolidate scope boundaries into one definitive list
6. Output: single final REPORT.md. RECONSTRUCTIONS.md will remain staged.
7. These are the permanent deliverables. Stage artefacts are archived after this.
