# Menace Tactical AI — Stage 4 REPORT.md

**Game:** Menace  
**Platform:** Windows x64, Unity IL2CPP  
**Binary:** GameAssembly.dll  
**Image base:** 0x180000000  
**Source material:** Ghidra decompilation, Il2CppDumper dump.cs, extract_rvas.py class dumps  
**Stage:** 4 — Concrete scoring subclasses and shot candidate post-processor  
**Investigation status:** Stage complete; all Next Priority Table items resolved

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. Core Findings
5. New WeightsConfig Fields Confirmed
6. New Actor / Skill Fields Referenced
7. Buff Scoring Formula — Complete Reference
8. Ghidra Address Reference
9. Key Inferences and Design Notes
10. Open Questions

---

## 1. Investigation Overview

### What was investigated

This stage analysed the four functions listed in the Stage 3 Next Priority Table:

- `InflictDamage.GetTargetValue` (0x18073AF00) — the concrete override for the most common attack subclass
- `InflictDamage.GetUtilityFromTileMult` (0x18073AFE0) — its companion static getter
- `Buff.GetTargetValue` (0x1807391C0) — the concrete override for the most common assist subclass
- `FUN_1806DA770` (0x1806DA770) — the shot candidate post-processor flagged as NQ-17

### What was achieved

- Confirmed that `InflictDamage.GetTargetValue` is a prepend-and-delegate pattern: it computes a tag value for co-fire shots and passes it into the already-analysed `SkillBehavior.GetTargetValue` (Stage 1). No novel formula is introduced at the InflictDamage level.
- Confirmed that tag value computation is gated on `isCoFire`: when false, `tagValue` is forced to zero and the tag effectiveness path in the base scorer is a no-op.
- Resolved NQ-17: `FUN_1806DA770` is a shot candidate packaging step, not a scorer. It wraps a validated `ShotPath` in a keyed container and appends to the candidate list.
- Fully reconstructed `Buff.GetTargetValue`, revealing a six-branch flag-driven scoring model covering heal, status buff, suppression, AoE heal, AoE buff, and setup/stance assist.
- Confirmed eight new WeightsConfig float fields at offsets +0x10C through +0x190.

### What was NOT investigated (scope boundaries)

- `FUN_1806D5040` — called inside the post-processor on a ShotPath. Role clear from context; internals deferred (NQ-22).
- `FUN_1806E33A0` — eligibility/range check before buff scoring. Interface confirmed (returns bool); internals deferred (NQ-23).
- `FUN_1805DF080`, `FUN_1805DEE10` — leaf getters (missing HP and resistance fraction). Low priority (NQ-24, NQ-25).
- `FUN_181430AC0` — AoE per-member scorer; five-argument signature confirmed; internals deferred (NQ-26).
- `FUN_180628210`, `FUN_180687590` — minor helpers in setup branch. Low priority (NQ-28, NQ-29).
- All concrete `GetTargetValue` overrides other than InflictDamage and Buff remain unanalysed (InflictSuppression, Stun, SupplyAmmo, TargetDesignator, SpawnHovermine, SpawnPhantom).

---

## 2. Tooling

No new `extract_rvas.py` runs were required for this stage. All class layouts were established in prior stages. Field offsets were resolved directly from Ghidra output against the confirmed field tables carried forward from Stages 1–3.

---

## 3. Class Inventory

| Class | Role in this stage |
|---|---|
| InflictDamage | Attack subclass; GetTargetValue and GetUtilityFromTileMult analysed |
| Buff | Assist subclass; GetTargetValue fully reconstructed |
| WeightsConfig | Singleton config; 8 new fields confirmed |
| Actor | Target of buff scoring; 1 new field (+0xD0) inferred |
| ShotPath | Input to post-processor; +0x10 and field_0x10->field_0x180 referenced |

---

## 4. Core Findings

### 4.1 InflictDamage.GetTargetValue — 0x18073AF00

This function is a thin prepend-and-delegate. It does not contain the InflictDamage scoring formula — that lives entirely in `SkillBehavior.GetTargetValue` (Stage 1, VA 0x18073DD90). The role of this override is to compute and inject a `tagValue` before delegating.

**Logic:**

```
if isCoFire == false:
    tagValue = 0
else:
    weaponRef  = self->entityInfo->field_0x18          // object at EntityInfo +0x18 (NQ-19)
    tagValue   = weaponRef->vtable[0x458](...)          // GetTag() or equivalent (NQ-21)
    tagValue   = FUN_1806E2710(weaponData, tagValue, 0) // tag effectiveness lookup (NQ-20)

SkillBehavior_GetTargetValue(self, isCoFire, tagValue, param_4, 0, param_3, param_5, param_6, 0)
```

Tag effectiveness is only evaluated for co-fire shots. For direct attacks, `tagValue = 0` and the tag path in the base scorer has no effect. This explains why `WeightsConfig->tagValueScale` (+0xBC) has no influence on solo attacks.

**Parameters:**

| Param | Type | Meaning |
|---|---|---|
| param_1 | InflictDamage* | self |
| param_2 | bool (char) | isCoFire |
| param_3–6 | undefined8 | forwarded to base scorer |

---

### 4.2 InflictDamage.GetUtilityFromTileMult — 0x18073AFE0

Pure static getter. Reads one float from the WeightsConfig singleton.

```c
float GetUtilityFromTileMult() {
    return WeightsConfig_WEIGHTS->utilityFromTileMultiplier;  // +0x10C
}
```

---

### 4.3 Buff.GetTargetValue — 0x1807391C0

Scores a buff/assist action against a specific target actor. Score is built by summing contributions from up to six independent branches, each gated on a flag bit in `buffSkill->flags` (+0x18). Final result is scaled by a per-target context factor and a global buff weight.

**Parameters:**

| Param | Type | Meaning |
|---|---|---|
| param_1 | SkillBehavior* (Buff) | self |
| param_2 | undefined8 | unused in visible code |
| param_3 | longlong | caster context — provides EntityInfo and team tile list |
| param_4 | longlong | target reference — Tile* or Actor* |

**Guards (all must pass or return 0.0):**

1. `param_3->entityInfo->weaponData` (+0x2C8) non-null and instanceof Buff skill class.
2. `FUN_180688600(param_4)` resolves to Actor, instanceof Actor class.
3. `actor->field_0xC8` (buff/skill data sub-block) non-null.
4. `FUN_1806E33A0(param_3, param_4, actor)` eligibility check returns true.

**Flag bits in `buffSkill->flags` (+0x18):**

| Bit | Hex mask | Branch |
|---|---|---|
| 0 | 0x0001 | Heal |
| 1 | 0x0002 | Status buff |
| 15 | 0x8000 | Suppress / debuff resistance |
| 17 | 0x20000 | AoE heal |
| 18 | 0x40000 | AoE buff |
| 16 | 0x10000 | Setup / stance assist |

Bits are not mutually exclusive. Multiple branches accumulate additively.

**Branch 1 — Heal (bit 0):**
```
score = WeightsConfig->healScoringWeight (+0x17C) * FUN_1805DF080(actor)
if actor->entityInfo->isImmobile AND NOT hasStatusBuff: score *= 0.5
if NOT actor->isIncapacitated (+0x15C):                 score *= 1.1
fVar14 += score
```

**Branch 2 — Status buff (bit 1):**
```
score = WeightsConfig->buffScoringWeight (+0x180)
buffType = actor->vtable[0x478](...)
if buffType == 2 AND NOT heal: score *= 0.1
if NOT actor->isIncapacitated:  score *= 1.5
fVar14 += score
```

**Branch 3 — Suppress (bit 15 = 0x8000):**
```
resistFrac = FUN_1805DEE10(actor)   // [0,1]
score = (1.0 - resistFrac) * WeightsConfig->suppressScoringWeight (+0x184)
slotVal = actor->vtable[0x468](...)
if score > 0.0 AND slotVal == 1:    score *= 2.0
if actor->entityInfo->isImmobile AND NOT hasStatusBuff: score *= 0.5
if buffType == 2 AND NOT heal:      score *= 0.9
if NOT actor->isIncapacitated:      score *= 1.5
fVar14 += score
```

**Branch 4 — AoE heal (bit 17 = 0x20000):**
```
aoeTotal = 0.0
foreach tile in self->agentContext->entityInfo->tileList (+0x48):
    if tile has ally (FUN_180722ED0):
        healVal, ok = FUN_181430AC0(tile->field_0x20->field_0x58, actor, ...)
        if ok: aoeTotal += healVal
fVar14 += WeightsConfig->aoeHealScoringWeight (+0x190) * aoeTotal
```

**Branch 5 — AoE buff (bit 18 = 0x40000):**
```
aoeTotal = 0.0
if (NOT immobile OR hasStatusBuff) AND NOT (buffType==2 AND NOT hasHeal):
    foreach tile in tileList:
        if tile has ally:
            val1, ok1 = FUN_181430AC0(tileEntry->field_0x20, actor, ..., aoeTotal)
            if ok1: aoeTotal += WeightsConfig->aoeBuffScoringWeight (+0x18C) * val1
            val2, ok2 = FUN_181430AC0(tileEntry->field_0x28, actor, ..., aoeTotal)
            if ok2: aoeTotal += val2 * WeightsConfig->aoeBuffScoringWeight
if NOT actor->isIncapacitated: aoeTotal *= 1.2
fVar14 += aoeTotal
```

**Branch 6 — Setup / stance assist (bit 16 = 0x10000):**
```
score = WeightsConfig->setupAssistScoringWeight (+0x188)

if (NOT immobile OR hasStatusBuff) AND NOT (buffType==2 AND NOT hasHeal):
    if NOT FUN_180628210(actorEntity) AND buffType != 2: score = 0.0
else:
    score = 0.0

if actor->field_0xD0 == 1:          score *= 0.75
if actor->isWeaponSetUp (+0x167):   score *= 0.75
if NOT actor->isIncapacitated:      score *= 1.1

foreach entry in proximityList:
    if entry->flags & 0x02 AND actor in range:  score *= 0.9
    if entry->flags & 0x01 AND actor NOT in range: score *= 1.2

if FUN_180687590(param_4) == 0:
    if targetEntity->field_0xC8 != -2:
        if actor->field_0xC8->field_0x38 > 0: score *= powf(1.25)

fVar14 += score
```

**Final return:**
```
return actor->field_0xC8->field_0x34 * fVar14 * WeightsConfig->buffGlobalScoringScale (+0x174)
```

---

### 4.4 FUN_1806DA770 — Shot Candidate Post-Processor (NQ-17 resolved)

Packages a validated `ShotPath` into a keyed, sorted container and appends to the candidate list. Not a scorer.

```
entry = new(ShotCandidateWrapper class)
entry->field_0x10 = param_1   // ShotPath reference

if param_1->field_0x10->field_0x180 != NULL:   // trajectory/arc block must exist
    entry->field_0x18 = FUN_1806D5040(param_1)  // derived metric (NQ-22)
    container = new(sorted container class)
    FUN_1806F0E90(container, entry, comparatorKey, 0)  // insert with key
    if param_2 != NULL:
        FUN_1818897C0(param_2, container, listClass)   // append to output list
else:
    NullReferenceException
```

Shots without a trajectory block are excluded from the candidate list. No error is raised — they are silently dropped after the ShotPath reference is stored.

---

## 5. New WeightsConfig Fields Confirmed

Singleton accessed via `*(longlong *)(DAT_18394c3d0 + 0xb8) + 8)`.

| Offset | Field name | Type | Status |
|---|---|---|---|
| +0x10C | utilityFromTileMultiplier | float | confirmed |
| +0x174 | buffGlobalScoringScale | float | confirmed |
| +0x17C | healScoringWeight | float | confirmed |
| +0x180 | buffScoringWeight | float | confirmed |
| +0x184 | suppressScoringWeight | float | confirmed |
| +0x188 | setupAssistScoringWeight | float | confirmed |
| +0x18C | aoeBuffScoringWeight | float | confirmed |
| +0x190 | aoeHealScoringWeight | float | confirmed |

---

## 6. New Actor / Skill Fields Referenced

| Class | Offset | Field | Type | Status | Notes |
|---|---|---|---|---|---|
| Actor | +0xD0 | field_0xD0 | int | inferred | Checked == 1 in setup branch; likely stance/setup state enum |
| Actor | +0xC8 | buffDataBlock | ptr | inferred | Sub-object; +0x34 = contextScale float, +0x38 = count int |
| EntityInfo | +0x18 | field_0x18 | ptr | inferred | Dereferenced for weapon tag lookup (NQ-19) |

---

## 7. Buff Scoring Formula — Complete Reference

```
total = 0.0

if HEAL (bit 0):
    total += healScoringWeight * healAmount
              [× 0.5 if immobile and no status]
              [× 1.1 if not incapacitated]

if STATUS_BUFF (bit 1):
    total += buffScoringWeight
              [× 0.1 if buffType==2 and no heal]
              [× 1.5 if not incapacitated]

if SUPPRESS (bit 15):
    total += (1 - resistFrac) * suppressScoringWeight
              [× 2.0 if score>0 and slotVal==1]
              [× 0.5 if immobile and no status]
              [× 0.9 if buffType==2 and no heal]
              [× 1.5 if not incapacitated]

if AOE_HEAL (bit 17):
    total += aoeHealScoringWeight * Σ(perMemberHealValue)

if AOE_BUFF (bit 18):
    aoeSum = Σ(aoeBuffScoringWeight * perMemberBuffValue)
    [× 1.2 if not incapacitated]
    total += aoeSum

if SETUP (bit 16):
    score = setupAssistScoringWeight  [or 0 if conditions not met]
    [× 0.75 if field_0xD0 == 1]
    [× 0.75 if isWeaponSetUp]
    [× 1.1 if not incapacitated]
    [× proximity modifiers per entry]
    [× powf(1.25) if stack count > 0]
    total += score

return actor->buffDataBlock->contextScale * total * buffGlobalScoringScale
```

---

## 8. Ghidra Address Reference

### Fully analysed this stage

| VA | Method | Notes |
|---|---|---|
| 0x18073AF00 | InflictDamage.GetTargetValue | Prepend-and-delegate; co-fire tag gate confirmed |
| 0x18073AFE0 | InflictDamage.GetUtilityFromTileMult | Static getter; WeightsConfig +0x10C |
| 0x1807391C0 | Buff.GetTargetValue | Full 6-branch scoring formula |
| 0x1806DA770 | Shot candidate post-processor | Packaging only; NQ-17 resolved |

### Deferred from this stage

| VA | Likely method | NQ ref |
|---|---|---|
| 0x1806D5040 | ShotPath derived metric | NQ-22 |
| 0x1806E33A0 | CanApplyBuff / eligibility | NQ-23 |
| 0x1805DF080 | GetMissingHPAmount | NQ-24 |
| 0x1805DEE10 | GetResistanceFraction | NQ-25 |
| 0x181430AC0 | AoE per-member scorer | NQ-26 |
| 0x180628210 | IsReadyToFire | NQ-28 |
| 0x180687590 | GetBuffStackCount | NQ-29 |

---

## 9. Key Inferences and Design Notes

**InflictDamage is a decorator, not a scorer.** All attack subclasses share the `SkillBehavior.GetTargetValue` scoring pipeline. The InflictDamage override only prepends tag value computation for co-fire shots, then delegates. This means `tagValueScale` (+0xBC) has zero influence on solo attacks by architectural design.

**Buff scoring is fully additive across branches.** There is no normalization or cap before the final `contextScale * total * globalScale` multiplication. A skill with all six bits set accumulates contributions from all six branches simultaneously.

**The incapacitation bonus is universal and always positive.** Every branch applies a multiplier > 1.0 when the target is not incapacitated. The AI consistently prioritises buffing healthy, active units over downed ones.

**`buffType == 2` is a suppression-of-redundancy guard.** When detected, the status buff branch reduces its weight by 90% and the suppress branch by 10%. This prevents double-scoring a unit already in a suppressed state.

**AoE branches iterate the caster's team tile list, not a radius.** AoE score asks "how many of my team members would benefit?" not "how many tiles are in the AoE?" The target actor is passed to the per-member scorer, suggesting it is used as a range/distance reference inside `FUN_181430AC0`.

**The post-processor silently drops shots without trajectory data.** The condition on `field_0x10->field_0x180` means only shots with a computed arc block get packaged into candidates. This is a clean filter, not an error path.

---

## 10. Open Questions

**NQ-19:** `EntityInfo +0x18` — dereferenced in `InflictDamage.GetTargetValue` to get a weapon/tag object.  
→ Run extract_rvas.py on EntityInfo; confirm field at +0x18.

**NQ-20:** `FUN_1806E2710(weaponData, tagValue, 0)` — tag effectiveness application.  
→ Analyse 0x1806E2710; expected short lookup against TagEffectivenessTable.

**NQ-21:** Vtable slot +0x458 on object at EntityInfo +0x18 — returns tag index/value.  
→ Identify class type of EntityInfo +0x18; look up vtable slot.

**NQ-22:** `FUN_1806D5040(ShotPath*)` — derived value stored in ShotCandidate +0x18. Low priority.  
→ Analyse 0x1806D5040 if ShotCandidate scoring detail needed.

**NQ-23:** `FUN_1806E33A0` — eligibility/range check before buff scoring.  
→ Analyse 0x1806E33A0 if Buff targeting rules needed.

**NQ-24:** `FUN_1805DF080(actor)` — missing HP or heal amount. Low priority.  
→ Analyse 0x1805DF080 if heal formula input needs exact definition.

**NQ-25:** `FUN_1805DEE10(actor)` — resistance fraction [0,1] for suppress branch. Low priority.  
→ Analyse 0x1805DEE10 if suppress formula input needs exact definition.

**NQ-26:** `FUN_181430AC0` — AoE per-member scorer; 5-arg signature confirmed.  
→ Analyse 0x181430AC0 if AoE buff/heal scoring detail required.

**NQ-27:** `Actor +0xD0` — int checked == 1 in setup branch. Not in confirmed Actor table.  
→ Run extract_rvas.py on Actor; confirm field at +0xD0.

**NQ-28:** `FUN_180628210(entityInfo)` — IsReadyToFire or similar. Low priority.  
→ Analyse 0x180628210 if setup scoring conditions need clarification.

**NQ-29:** `FUN_180687590(param_4)` — GetBuffStackCount or similar. Low priority.  
→ Analyse 0x180687590 if stack-count scaling needs clarification.

**NQ-13 (carried):** WeightsConfig +0xF0 vs +0x100 co-fire weight distinction — both fields confirmed; conditions under which each is selected remain in the base scorer (Stage 1). Cross-reference against future InflictDamage subclass analysis if pursued.
