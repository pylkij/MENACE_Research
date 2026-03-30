# Menace — Tactical AI Behavior Scorers — Stage 5

**Game:** Menace  
**Platform:** Windows x64, Unity IL2CPP  
**Binary:** GameAssembly.dll  
**Image base:** 0x180000000  
**Source material:** Il2CppDumper dump.cs, Ghidra decompilation, extraction_report_master.txt  
**Investigation status:** In Progress  
**Stage:** 5 of ~6  

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. The Core Findings — Concrete GetTargetValue Scorers
5. Full Pipeline — Scorer Taxonomy
6. Class Sections
7. Ghidra Address Reference
8. Key Inferences and Design Notes
9. Open Questions

---

## 1. Investigation Overview

This stage extended the tactical AI scoring pipeline investigation to cover all concrete
`GetTargetValue` overrides that had been deferred in prior stages. Stages 1–4 fully
documented the base scoring pipeline (SkillBehavior, InflictDamage, Buff, Move, Attack,
Assist). Stage 5 resolved the remaining nine concrete subclass scorers and two utility
sub-functions.

**Achieved this stage:**
- `InflictSuppression.GetTargetValue` — confirmed structurally identical to InflictDamage; tag chain identical; passes skillEffectType = 1
- `InflictSuppression.GetUtilityFromTileMult` — confirmed returns WeightsConfig+0x118 (distinct from InflictDamage's +0x10C)
- `Stun.GetTargetValue` — same tag chain structure; passes skillEffectType = 2
- `Mindray.GetTargetValue` — two-path dispatch on entityInfo flag; uses resistance fraction as gate; passes skillEffectType 0 or 1
- `TargetDesignator.GetTargetValue` — float scorer; observer coverage + proximity scoring
- `SupplyAmmo.GetTargetValue` — complex scorer; HP-fraction blend, AoE ally bonus, weapon setup bonuses, buff context scaling
- `SpawnPhantom.GetTargetValue` — void side-effect scorer; eligibility loop with flag checks
- `SpawnHovermine.GetTargetValue` — void side-effect scorer; weighted proximity loop with tiered range bonuses
- `CreateLOSBlocker.GetTargetValue` — void side-effect scorer; geometry-aware LOS line check with three-zone AoE coverage formula
- `TagEffectiveness_Apply` (FUN_1806E2710) — confirmed: computes clamped tag application count from cap, tier divisor, and per-entry minimums
- `AoE_PerMemberScorer` (FUN_181430AC0) — confirmed: tier-table lookup with negative-tier early-out
- `CanApplyBuff` (FUN_1806E33A0) — confirmed: all-conditions-must-pass gate over BuffSkill condition list
- `ShotCandidate cast` (FUN_1806D5040) — confirmed: safe Actor cast on ShotPath+0x30

**Not investigated this stage:**
- `Deploy` class — OnCollect, OnEvaluate, GetHighestTileScore
- `GainBonusTurn`, `Reload`, `Scan`, `MovementSkill`, `RemoveStatusEffect`, `TurnArmorTowardsThreat`, `TransportEntity` — entire classes untouched
- `StrategyData.ComputeMoveCost` (FUN_1806361F0)
- Indirect fire trajectory builder (FUN_1806DE1D0), AoE target set builder (FUN_1806E1FB0)
- Concrete `Condition.Evaluate` implementations (vtable +0x1D8)
- `GetAoETierForMember` (FUN_181423600)

---

## 2. Tooling

Il2CppDumper extraction was performed prior to this stage. All RVAs come from dump.cs.
VAs are computed as VA = RVA + 0x180000000. Ghidra was used for decompilation, with
functions exported in batches of 2–9. Several large functions (SupplyAmmo, CreateLOSBlocker)
caused truncation when batched; these required individual re-exports to obtain complete output.

---

## 3. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| InflictSuppression | Menace.Tactical.AI.Behaviors | 3648 | Attack subclass; suppression damage scorer |
| Stun | Menace.Tactical.AI.Behaviors | 3667 | Attack subclass; stun effect scorer |
| Mindray | Menace.Tactical.AI.Behaviors | 3657 | Attack subclass; scan/mindray scorer |
| TargetDesignator | Menace.Tactical.AI.Behaviors | 3665 | Attack subclass; designation coverage scorer |
| SupplyAmmo | Menace.Tactical.AI.Behaviors | 3664 | Assist subclass; ammo resupply scorer |
| SpawnPhantom | Menace.Tactical.AI.Behaviors | 3661 | Attack subclass; phantom spawn eligibility scorer |
| SpawnHovermine | Menace.Tactical.AI.Behaviors | 3660 | Attack subclass; hovermine placement scorer |
| CreateLOSBlocker | Menace.Tactical.AI.Behaviors | 3655 | Assist subclass; LOS blocker placement scorer |

---

## 4. The Core Findings — Concrete GetTargetValue Scorers

### 4.1 skillEffectType Enum

All Attack-lineage `GetTargetValue` overrides delegate to `SkillBehavior.GetTargetValue`
(FUN_18073DD90) via a common pattern. The 5th integer argument is a **skillEffectType**
discriminator used by the base scorer to route effect-specific logic:

| Value | Skill class(es) |
|---|---|
| 0 | Mindray (standard path) |
| 1 | InflictDamage, InflictSuppression, Mindray (vulnerable path) |
| 2 | Stun |

### 4.2 Tag Chain (Attack-lineage scorers)

All Attack-lineage scorers that support co-fire run the same tag resolution chain:
```
if coFireFlag:
    plVar2 = self->agentContext->field_0x18->field_0x18  // weapon/tag object
    tagIndex = plVar2->vtable[0x458/8](plVar2)            // NQ-21: GetTagIndex()
    tagValue = TagEffectiveness_Apply(self->weaponData, tagIndex, 0)
else:
    tagValue = 0
delegate to SkillBehavior.GetTargetValue(self, coFireFlag, tagValue, context,
                                          skillEffectType, ...)
```

### 4.3 TagEffectiveness_Apply Formula
```
uint TagEffectiveness_Apply(weaponData, tagIndex):
    cap = max(1, weaponData->tagApplicationCap)      // +0xA8
    tierCount = GetTagTierCount(weaponData, 0)        // FUN_1806ddec0
    result = min(cap, tagIndex / tierCount)
    for each modifier in weaponData->tagModifiers:    // +0x48
        result = min(result, modifier->GetValue(1))
    return result
```

### 4.4 SupplyAmmo Score Formula
```
score = utilityThreshold / behaviorScale
if weapon not setup or wrong type: score = 0
if coFire eligible and target is mobile non-setup: score *= 1.25
for each ally tile (AoE zones 0, 1, 2):
    if AoE_PerMemberScorer hits and score > WEIGHTS->aoeAllyBonusThreshold (+0x1A4):
        score *= 1.05  // stacks up to 3×
if target->field_0xD0 != 0: score *= 1.1          // has secondary weapon
if target->isWeaponSetUp:    score *= 1.1
score = score * 0.8 + score * 0.2 * GetHPFraction(target)
return score * target->buffDataBlock->contextScale  // +0x34
```

### 4.5 TargetDesignator Score Formula
```
score = 0
for each observer in agentContext->behaviorConfig->field_0x28:
    score += (IsInDesignationZone(observer, context) ? 0.5 : 0.25)
for each tile in agentContext->field_0x20:
    dist = GetDistanceTo(tile->pos, context)
    if 0 < dist < 11: score += (1.0 - dist / 10.0)
return score * proximityEntry->field_0x88
```

### 4.6 SpawnHovermine Score Formula
```
score = 0
for each ally tile in entityInfo->tileList:
    dist = GetDistanceTo(ally->pos, target)
    if dist <= maxRange:
        base = maxRange - dist + 1
        if dist <= idealRange:   base *= 1.5
        elif dist <= midRange:   base *= 1.25
        if ally->isWeaponSetUp:  base *= 1.25
        if !TileHasAlly(tile):   base *= 0.25
        score += base * tile->field_0x88
    RegisterCandidate(context, tile, score)
```

### 4.7 CreateLOSBlocker Score Formula
```
for each blockerCandidate in self->blockerCandidateList:
    for each ally tile in entityInfo->tileList:
        if !IsTeamMember || !TileHasAlly || isImmobile || state==1: skip
        aoeBase = AoE_PerMemberScorer(tile->aoeTierTable, blocker)
        if aoeBase == 0: skip
        dist = GetDistanceTo(ally->pos, blocker->tile)
        if dist > range->maxDist and BlockerOnLOSLine and dist3D <= 5.656854:
            stackMult = (buffStackCount - 1) * 0.25 + 1.0
            contribution = stackMult * aoeBase - (zone0 + zone1 + zone2)
            if contribution > 0 and ally->isWeaponSetUp: contribution *= 0.8
            tileScore += contribution
    if tileScore > 0: tileScore *= candidateWeight
    totalScore += tileScore
```

---

## 5. Full Pipeline — Scorer Taxonomy
```
GetTargetValue override
│
├── Attack-lineage (InflictDamage, InflictSuppression, Stun, Mindray)
│   ├── Tag chain → TagEffectiveness_Apply → skillEffectType dispatch
│   └── Delegates to SkillBehavior.GetTargetValue (base scorer)
│
├── Float scorers (return float directly)
│   ├── SupplyAmmo  — HP blend + AoE + weapon bonus + buff scale
│   └── TargetDesignator — observer coverage + proximity reach
│
└── Void side-effect scorers (register candidates, no float return)
    ├── SpawnPhantom   — eligibility filter loop
    ├── SpawnHovermine — weighted proximity loop with tier bonuses
    └── CreateLOSBlocker — geometry-aware LOS line check + AoE coverage formula
```

---

## 6. Class Sections

### InflictSuppression

**Namespace:** Menace.Tactical.AI.Behaviors | **TypeDefIndex:** 3648 | **Base:** Attack

Fields (one additional beyond Attack):

| Offset | Field | Type | Status |
|---|---|---|---|
| +0x090 | m_Name | string | confirmed |

Methods:

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTargetValue | 0x73B240 | 0x18073B240 | Complete — tag chain + delegate, effectType=1 |
| GetUtilityFromTileMult | 0x73B320 | 0x18073B320 | Complete — returns WeightsConfig+0x118 |

**Behavioural notes:** Identical tag chain to InflictDamage. Only difference is WeightsConfig field for tile multiplier (+0x118 vs +0x10C) and the same effectType=1.

---

### Stun

**Namespace:** Menace.Tactical.AI.Behaviors | **TypeDefIndex:** 3667 | **Base:** Attack

Methods:

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTargetValue | 0x769B40 | 0x180769B40 | Complete — tag chain + delegate, effectType=2 |

**Behavioural notes:** Byte-for-byte structurally identical to InflictSuppression except passes skillEffectType = 2 to base scorer.

---

### Mindray

**Namespace:** Menace.Tactical.AI.Behaviors | **TypeDefIndex:** 3657 | **Base:** Attack

Methods:

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTargetValue | 0x762550 | 0x180762550 | Complete — two-path: effectType 0 or 1 based on target flag |

**Behavioural notes:** Uses `GetResistanceFraction(target)` as primary gate — target must have resistance > 0. Checks `entityInfo->flags bit 7` (skip entirely) and `entityInfo->field_0xA8 & 0x100` (vulnerability flag → effectType 1). Non-vulnerable targets use effectType 0.

---

### TargetDesignator

**Namespace:** Menace.Tactical.AI.Behaviors | **TypeDefIndex:** 3665 | **Base:** Attack

Methods:

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTargetValue | 0x76A640 | 0x18076A640 | Complete — observer coverage + proximity float scorer |

**Behavioural notes:** Checks `entityInfo->flags bit 11` — already-designated targets return 0.0. Two independent scoring loops: observer coverage (0.25/0.5 per observer) and proximity reach (linear decay up to dist=10). Result scaled by `proximityEntry->field_0x88`.

---

### SupplyAmmo

**Namespace:** Menace.Tactical.AI.Behaviors | **TypeDefIndex:** 3664 | **Base:** Assist

Methods:

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTargetValue | 0x769E60 | 0x180769E60 | Complete (reconstructed from two partial exports) |

**Behavioural notes:** Most complex scorer in the investigation. HP-fraction blend (`0.8 + 0.2 * hpFrac`) applied after all multipliers. Three stackable AoE zone bonuses (×1.05 each). Final output multiplied by `target->buffDataBlock->contextScale`.

---

### SpawnPhantom

**Namespace:** Menace.Tactical.AI.Behaviors | **TypeDefIndex:** 3661 | **Base:** Attack

Methods:

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTargetValue | 0x769450 | 0x180769450 | Complete — void eligibility scorer |

**Behavioural notes:** Filters on `entityInfo->flags bit 5` (isPhantom — excluded) and `entityInfo->field_0xDC > 0` (detection value required). Range check bounds from weapon config object `plVar10[3]` and `plVar10+0x1C`.

---

### SpawnHovermine

**Namespace:** Menace.Tactical.AI.Behaviors | **TypeDefIndex:** 3660 | **Base:** Attack

Methods:

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTargetValue | 0x768EF0 | 0x180768EF0 | Complete — void proximity scorer |

**Behavioural notes:** Three range tiers with multipliers 1.5/1.25/1.0. Weapon-setup bonus ×1.25. No-ally-on-tile penalty ×0.25. Scores accumulated and weighted by `tile->field_0x88`.

---

### CreateLOSBlocker

**Namespace:** Menace.Tactical.AI.Behaviors | **TypeDefIndex:** 3655 | **Base:** Assist

Additional confirmed fields:

| Offset | Field | Type | Status |
|---|---|---|---|
| +0x60 | placementEvaluator | PlacementEvaluator* | confirmed (via agentContext->field_0x60) |
| +0x88 | blockerCandidateList | List\<BlockerCandidate\>* | confirmed |

Methods:

| Method | RVA | VA | Notes |
|---|---|---|---|
| GetTargetValue | 0x75EB90 | 0x18075EB90 | Complete |

**Behavioural notes:** Only proceeds when `PlacementCandidate->losImpact < 0` — the blocker must degrade opponent LOS. Geometry check uses 3D distance threshold of 5.656854 (= 4√2) to determine if blocker sits on the LOS line between ally and target. Stack multiplier `(stackCount - 1) * 0.25 + 1.0` rewards buff-stacked positions. Weapon-setup allies penalised ×0.8 (committed, less exploitable).

---

## 7. Ghidra Address Reference

### Fully Analysed This Stage

| VA | Method | Class | Notes |
|---|---|---|---|
| 0x18073B240 | GetTargetValue | InflictSuppression | Complete |
| 0x18073B320 | GetUtilityFromTileMult | InflictSuppression | Complete |
| 0x180769B40 | GetTargetValue | Stun | Complete |
| 0x180762550 | GetTargetValue | Mindray | Complete |
| 0x18076A640 | GetTargetValue | TargetDesignator | Complete |
| 0x180769E60 | GetTargetValue | SupplyAmmo | Complete (two-part export) |
| 0x180769450 | GetTargetValue | SpawnPhantom | Complete |
| 0x180768EF0 | GetTargetValue | SpawnHovermine | Complete |
| 0x18075EB90 | GetTargetValue | CreateLOSBlocker | Complete (two-part export) |
| 0x1806E2710 | TagEffectiveness_Apply | — | Complete — NQ-20 closed |
| 0x181430AC0 | AoE_PerMemberScorer | — | Complete — NQ-26 closed |
| 0x1806E33A0 | CanApplyBuff | BuffSkill | Complete — NQ-23 closed |
| 0x1806D5040 | ShotPath_ActorCast | — | Complete — NQ-22 closed |

### Not Yet Analysed (remaining scope)

| VA | Method | Class | Priority |
|---|---|---|---|
| 0x18073A0C0 | GetHighestTileScore | Deploy | High |
| 0x1806361F0 | ComputeMoveCost | StrategyData | Medium |
| 0x181423600 | GetAoETierForMember | — | Medium |
| 0x1806E3750 | IsInDesignationZone | — | Low |
| 0x1806DE1D0 | Indirect fire builder | — | Deferred |
| 0x1806E1FB0 | AoE target set builder | — | Deferred |

---

## 8. Key Inferences and Design Notes

**skillEffectType is the base scorer's routing key.** The single integer passed as arg5 to `SkillBehavior.GetTargetValue` discriminates between effect classes. All Attack subclasses use it; the base scorer presumably branches on it to apply effect-specific modifiers. The enum values seen so far (0, 1, 2) suggest at least 3 paths.

**Three scorer archetypes.** Concrete GetTargetValue overrides fall into three structural categories: (1) tag-chain-then-delegate (InflictDamage, InflictSuppression, Stun, Mindray), (2) full float scorers with their own formula (SupplyAmmo, TargetDesignator), (3) void side-effect scorers that operate via candidate registration (SpawnPhantom, SpawnHovermine, CreateLOSBlocker).

**AoE coverage subtraction in CreateLOSBlocker.** The formula `stackMult * aoeBase - (z0 + z1 + z2)` means that if existing AoE zone coverage already equals the base value, the blocker contributes nothing. This is an anti-redundancy mechanism — the AI naturally avoids placing blockers where AoE already provides equivalent benefit.

**5.656854 = 4√2.** The geometry threshold in CreateLOSBlocker is `4 * sqrt(2)` — the diagonal of a 4×4 tile square. This is the maximum distance a point can be from a line while still being considered "on" it in this grid geometry.

**HP fraction blend in SupplyAmmo.** The formula `0.8 + 0.2 * hpFrac` weights score 80% on the base utility and 20% on how much HP the target has. Counter-intuitively, higher HP targets score slightly higher — SupplyAmmo prefers targets that are healthier and can make better use of the ammo, not targets that are desperate.

**Weapon-setup actors penalised in CreateLOSBlocker (×0.8).** A set-up weapon ally is committed and less able to reposition to exploit the LOS blocker. The penalty encodes the opportunity cost of the blocker being wasted on an immobile ally.

---

## 9. Open Questions

[ ] NQ-4/5: WeightsConfig +0x78, +0x148, +0x14C — still inferred. → Run extract_rvas.py on WeightsConfig class.
[ ] NQ-6: Skill +0x48 vs Skill +0x60 shot group lists — unresolved. → Extract SkillBehavior class dump.
[ ] NQ-8: GetOrder return values for 0x18050C760, 0x180547170, 0x180546260 — unknown. → Low priority; decompile any one.
[ ] NQ-9: FUN_1806F3C30 return convention (XOR 1 in OnExecute). → Validate against leaf subclass.
[ ] NQ-11: StrategyData.ComputeMoveCost (FUN_1806361F0) — pathfinding cost. → Analyse if move cost formula needed.
[ ] NQ-13: WeightsConfig +0xF0 vs +0x100 — two co-fire weights, conditions unclear. → Cross-reference base scorer.
[ ] NQ-16: Strategy +0x8C = strategyMode — inferred. → Extract Strategy class.
[ ] NQ-19: EntityInfo +0x18 — weapon/tag object. → Extract EntityInfo class dump.
[ ] NQ-21: Vtable slot +0x458 on EntityInfo+0x18 object — returns tag index. → Confirm class type.
[ ] NQ-30: FUN_1806ddec0 — GetTagTierCount divisor. → Low priority; short function.
[ ] NQ-31: FUN_180002310 — TagModifier.GetValue. → Low priority; expected simple accessor.
[ ] NQ-33: FUN_181423600 — GetAoETierForMember. → Medium priority; analyse if AoE tier logic needed.
[ ] NQ-36: Condition.Evaluate vtable slot +0x1D8 — concrete implementations unknown. → Low priority.
[ ] NQ-37: InflictSuppression effectType — passes 1, same as InflictDamage. Verify base scorer handles them identically or with distinction. → Analyse SkillBehavior.GetTargetValue (private) branching on arg5.
[ ] NQ-38: EntityInfo->field_0xA8 & 0x100 — mindray vulnerability flag. → Extract EntityInfo class; confirm field name.
[ ] NQ-39: EntityInfo->flags bit 11 — already-designated flag. → Extract EntityInfo class; confirm.
[ ] NQ-40: FUN_1806E3750 — IsInDesignationZone predicate. → Analyse 0x1806E3750 if designation scoring detail needed.
[ ] NQ-41: Closed — CreateLOSBlocker setup phase fully recovered.