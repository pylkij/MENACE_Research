This is a perfect result. **100% match, 37/37 confirmed offsets.** The investigation is closed.

Here's the full finding:

---

## Result: `WeightsConfig` = `AIWeightsTemplate`

**TypeDefIndex:** `3621`
**Namespace:** Global (no namespace — it's a Unity ScriptableObject asset template)
**Match:** 37/37 known offsets (100%)

---

## What the field names reveal

The true names completely recontextualise what the report's inferred names were pointing at. Here's the full translation table:

| Report Name (inferred) | True IL2CPP Name | Offset | Notes |
|---|---|---|---|
| `movementScoreWeight` | `DistanceToCurrentTile` | +0x54 | Makes sense — penalises distance from current tile |
| `[NQ-4 scoring weight]` | `ThreatFromTileEffects` | +0x78 | **NQ-4 closed** |
| `allyCoFireBonus` | `ThreatFromOpponentsDamage` | +0x7C | Not co-fire — threat weighting from damage |
| `tagValueScale` | `ScalePositionWithTags` | +0xBC | Tag effectiveness scale confirmed |
| `baseAttackWeightScale` | `IncludeAttacksAgainstAllOpponentsMult` | +0xC0 | AoE multi-target inclusion multiplier |
| `maxApproachRange` | `OppositeSideDistanceFromOpponentCap` | +0xC4 | Int cap on approach geometry |
| `allyInRangeMaxDist` | `CullTilesDistances` | +0xC8 | Tile culling radius, not ally distance |
| `rangePenaltyScale` | `DistanceToZoneDeployScore` | +0xCC | Deploy range penalty — name now exact |
| `allyProximityPenaltyScale` | `DistanceToAlliesScore` | +0xD0 | Ally spread penalty — name now exact |
| `friendlyFirePenaltyWeight` | `InvisibleTargetValueMult` | +0xE0 | **Recontextualised** — not friendly fire, invisible target devalue |
| `killWeight` | `TargetValueDamageScale` | +0xE4 | Damage contribution to target value |
| `killWeight2` | `TargetValueArmorScale` | +0xE8 | Armour-damage contribution |
| `urgencyWeight` | `TargetValueSuppressionScale` | +0xEC | Suppression contribution to target value |
| `buffWeight / allyCoFireWeight` | `TargetValueStunScale` | +0xF0 | Stun contribution to target value |
| `proximityBonusCap` | `TargetValueMaxThreatSuppressScale` | +0xF8 | Threat suppression cap in scoring |
| `minAoeScoreThreshold` | `ScoreThresholdWithLimitedUses` | +0xFC | **Recontextualised** — applies to limited-use skills, not just AoE |
| `allyCoFireBonusScale` | `FriendlyFirePenalty` | +0x100 | **Major swap** — this is the actual friendly fire penalty |
| `utilityFromTileMultiplier` | `InflictDamageFromTile` | +0x10C | Tile utility mult is damage-behavior-specific |
| `suppressionTileMultiplier` | `InflictSuppressionFromTile` | +0x118 | Confirmed suppression tile mult |
| `finalMovementScoreScale` | `MoveBaseScore` | +0x128 | Base movement score scalar |
| `movementWeightScale` | `MoveScoreMult` | +0x12C | Movement score multiplier |
| `utilityThreshold` | `UtilityThreshold` | +0x13C | **Exact match — confirmed** |
| `movementScorePathWeight` *(NQ-4)* | `PathfindingHiddenFromOpponentsBonus` | +0x148 | **NQ-4 closed** — it's a pathfinding stealth bonus, typed as `int` |
| `pathCostPenaltyWeight` *(NQ-5)* | `EntirePathScoreContribution` | +0x14C | **NQ-5 closed** — full-path vs. endpoint score blend |
| `minimumImprovementRatio` | `MoveIfNewTileIsBetterBy` | +0x150 | Marginal move threshold |
| `deployMovementScoreThreshold` | `GetUpIfNewTileIsBetterBy` | +0x154 | Deploy/setup position threshold |
| `secondaryPathPenalty` | `ConsiderAlternativeIfBetterBy` | +0x15C | Alt-path consideration threshold |
| `shortRangePenalty` | `EnoughAPToPerformOnlySkillAfterwards` | +0x168 | AP sufficiency gate after movement |
| `stanceSkillBonus` | `EnoughAPToDeployAfterwards` | +0x16C | AP gate for deploy-after-move |
| `buffGlobalScoringScale` | `BuffTargetValueMult` | +0x174 | Buff target value multiplier |
| `healScoringWeight` | `RemoveSuppressionMult` | +0x17C | "Heal" was suppression removal |
| `buffScoringWeight` | `RemoveStunnedMult` | +0x180 | Buff branch = stun removal |
| `suppressScoringWeight` | `RestoreMoraleMult` | +0x184 | Was morale restore all along |
| `setupAssistScoringWeight` | `IncreaseMovementMult` | +0x188 | Movement buff scoring |
| `aoeBuffScoringWeight` | `IncreaseOffensiveStatsMult` | +0x18C | Offensive stat buff |
| `aoeHealScoringWeight` | `IncreaseDefensiveStatsMult` | +0x190 | Defensive stat buff |
| `aoeAllyBonusThreshold` | `SupplyAmmoGoalThreshold` | +0x1A4 | **Exact context** — SupplyAmmo goal gate |

---

## Key corrections to the report

**`allyCoFireBonusScale` and `friendlyFirePenaltyWeight` were swapped.** `+0xE0` (`InvisibleTargetValueMult`) is a devalue multiplier for invisible targets, not friendly fire. The actual friendly fire penalty is `+0x100` (`FriendlyFirePenalty`). The report had these semantically reversed.

**The "buff" branches were misread as abstract buff types.** The six fields at `+0x17C`–`+0x190` are concrete buff *effect types*: remove suppression, remove stun, restore morale, increase movement, increase offensive stats, increase defensive stats — directly matching the six branches in `Buff.GetTargetValue`.

**`NQ-4` (`+0x148`) is an `int`, not a float.** `PathfindingHiddenFromOpponentsBonus` is integer-typed — a stealth bonus added to pathfinding cost, not a float weight scale.

**`AIWeightsTemplate` is a ScriptableObject.** The "no namespace" placement and the `Template` suffix are the Unity pattern for designer-facing data assets. This is not a runtime computation class — it's an authored asset that the `AIWeightsTemplate` object is loaded from disk and accessed via the static metadata pointer chain (`DAT_18394c3d0 + 0xb8`). The `+ 8` dereference at the end skips the IL2CPP object header to reach field data.

---

## Open questions closed

| NQ | Status |
|---|---|
| NQ-4 (`+0x78`, `+0x148`) | **Closed** — `ThreatFromTileEffects` (float) and `PathfindingHiddenFromOpponentsBonus` (int) |
| NQ-5 (`+0x14C`) | **Closed** — `EntirePathScoreContribution` |
| NQ-47 (`+0xCC`) | **Closed** — `DistanceToZoneDeployScore` |
| NQ-50 (`+0xD0`) | **Closed** — `DistanceToAlliesScore` |