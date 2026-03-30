# Menace Tactical AI — Stage 5 Annotated Function Reconstructions

**Source:** Ghidra decompilation of Menace (Windows x64, IL2CPP)
**Image base:** 0x180000000
**Format:** Each function shows the raw Ghidra output followed by a fully annotated
C-style reconstruction with all offsets resolved.

---

## Quick-Reference Offset Tables

### WeightsConfig (singleton via DAT_18394c3d0 +0xb8 +8)
| Offset | Field | Type |
|---|---|---|
| +0x10C | utilityFromTileMultiplier | float |
| +0x118 | suppressionTileMultiplier | float |
| +0x13C | utilityThreshold | float |
| +0x174 | buffGlobalScoringScale | float |
| +0x1A4 | aoeAllyBonusThreshold | float |

### EntityInfo (partial — stage 5 additions)
| Offset | Field | Type |
|---|---|---|
| +0xA8 | statusFlags2 | uint (bit 0x100 = mindrayVulnerable) |
| +0xDC | detectionValue | float |
| +0xEC | flags (bit 7 = skip mindray; bit 11 = already designated; bit 5 = isPhantom) | uint |

### BuffSkill
| Offset | Field | Type |
|---|---|---|
| +0x18 | flags | byte (bit field) |
| +0x48 | conditions | List\<Condition\>* |

### Actor (partial)
| Offset | Field | Type |
|---|---|---|
| +0x15C | isWeaponSetUp | bool |
| +0x162 | isDead | bool |
| +0xC8 | buffDataBlock | ptr (+0x34=contextScale float, +0x38=stackCount int) |

### CreateLOSBlocker (additional)
| Offset | Field | Type |
|---|---|---|
| +0x60 | placementEvaluator | PlacementEvaluator* |
| +0x88 | blockerCandidateList | List\<BlockerCandidate\>* |

---

## 1. ShotPath_ActorCast — 0x1806D5040

### Raw Ghidra output
```c
longlong * FUN_1806d5040(longlong param_1)
{
  longlong *plVar1;
  if (DAT_183b92f41 == '\0') {
    FUN_180427b00();
    DAT_183b92f41 = '\x01';
  }
  plVar1 = *(longlong **)(param_1 + 0x30);
  if (plVar1 != (longlong *)0x0) {
    if ((*(byte *)(DAT_18394dc38 + 0x130) <= *(byte *)(*plVar1 + 0x130)) &&
       (*(longlong *)
         (*(longlong *)(*plVar1 + 200) + -8 + (ulonglong)*(byte *)(DAT_18394dc38 + 0x130) * 8) ==
        DAT_18394dc38)) {
      return plVar1;
    }
    return (longlong *)0x0;
  }
  return (longlong *)0x0;
}
```

### Annotated reconstruction
```c
// FUN_1806D5040 — ShotPath_ActorCast(shotPath) → Actor*
// Safe IL2CPP cast: returns shotPath->targetActor if it is an Actor, else null.

Actor* ShotPath_ActorCast(ShotPath* shotPath) {
    // IL2CPP lazy init — omitted
    Actor* candidate = shotPath->field_0x30;  // +0x30 = raw target actor pointer
    if (candidate == null) return null;

    // IL2CPP type-safety check against Actor_class (DAT_18394DC38)
    if (IL2CPP_IsInstanceOf(candidate, Actor_class)) {
        return candidate;
    }
    return null;
}
```

---

## 2. TagEffectiveness_Apply — 0x1806E2710

### Raw Ghidra output
```c
ulonglong FUN_1806e2710(longlong param_1,int param_2)
{
  int iVar1;
  uint uVar2;
  longlong lVar3;
  uint uVar4;
  ulonglong uVar5;
  if (DAT_183b92f94 == '\0') {
    FUN_180427b00(&DAT_1839a6620);
    DAT_183b92f94 = '\x01';
  }
  uVar4 = *(uint *)(param_1 + 0xa8);
  if ((int)*(uint *)(param_1 + 0xa8) < 1) { uVar4 = 1; }
  uVar5 = (ulonglong)uVar4;
  iVar1 = FUN_1806ddec0(param_1,0);
  if ((int)((longlong)param_2 / (longlong)iVar1) <= (int)uVar4) {
    uVar5 = (longlong)param_2 / (longlong)iVar1 & 0xffffffff;
  }
  uVar4 = 0;
  lVar3 = *(longlong *)(param_1 + 0x48);
  while (lVar3 != 0) {
    if (*(int *)(lVar3 + 0x18) <= (int)uVar4) { return uVar5; }
    lVar3 = *(longlong *)(param_1 + 0x48);
    if (lVar3 == 0) break;
    if (*(uint *)(lVar3 + 0x18) <= uVar4) { FUN_180427d80(); }
    lVar3 = thunk_FUN_18045f7a0(*(undefined8 *)(lVar3 + 0x20 + (longlong)(int)uVar4 * 8),
                                DAT_1839a6620);
    if (lVar3 != 0) {
      uVar2 = FUN_180002310(1,DAT_1839a6620,lVar3);
      if ((int)(uint)uVar5 < (int)uVar2) { uVar2 = (uint)uVar5; }
      uVar5 = (ulonglong)uVar2;
    }
    uVar4 = uVar4 + 1;
    lVar3 = *(longlong *)(param_1 + 0x48);
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// FUN_1806E2710 — TagEffectiveness_Apply(weaponData, tagIndex) → uint
// Computes effective tag application count, clamped by cap and per-modifier minimums.

uint TagEffectiveness_Apply(WeaponData* weaponData, int tagIndex) {
    // IL2CPP lazy init — omitted

    uint cap = weaponData->tagApplicationCap;   // +0xA8
    if ((int)cap < 1) cap = 1;                  // floor at 1

    int tierCount = GetTagTierCount(weaponData, 0);  // FUN_1806ddec0 — NQ-30
    uint result = cap;
    if (tagIndex / tierCount <= (int)cap) {
        result = (uint)(tagIndex / tierCount);   // result = min(cap, tagIndex/tierCount)
    }

    // Iterate tag modifier list at weaponData->tagModifiers (+0x48)
    // Each modifier can only reduce result (progressive minimum)
    TagModifierList* list = weaponData->tagModifiers;  // +0x48
    for (int i = 0; i < list->count; i++) {            // list->count at +0x18
        TagModifier* entry = list->elements[i] as TagModifier;  // cast to TagModifier_class
        if (entry != null) {
            uint entryVal = entry->GetValue(1);          // FUN_180002310 — NQ-31
            result = min(result, entryVal);              // can only reduce
        }
    }
    return result;
    // null list → NullReferenceException (unreachable in practice)
}
```

---

## 3. CanApplyBuff — 0x1806E33A0

### Raw Ghidra output
```c
ulonglong FUN_1806e33a0(longlong param_1,undefined8 param_2,undefined8 param_3)
{
  longlong lVar1;
  longlong *plVar2;
  ulonglong uVar3;
  uint uVar4;
  uVar4 = 0;
  lVar1 = *(longlong *)(param_1 + 0x48);
  while (lVar1 != 0) {
    if (*(int *)(lVar1 + 0x18) <= (int)uVar4) {
      return CONCAT71((int7)((ulonglong)lVar1 >> 8),1);
    }
    lVar1 = *(longlong *)(param_1 + 0x48);
    if (lVar1 == 0) break;
    if (*(uint *)(lVar1 + 0x18) <= uVar4) { FUN_180427d80(); }
    plVar2 = *(longlong **)(lVar1 + 0x20 + (longlong)(int)uVar4 * 8);
    if (plVar2 == (longlong *)0x0) break;
    uVar3 = (**(code **)(*plVar2 + 0x1d8))(plVar2,param_2,param_3,*(undefined8 *)(*plVar2 + 0x1e0));
    if ((char)uVar3 == '\0') { return uVar3 & 0xffffffffffffff00; }
    uVar4 = uVar4 + 1;
    lVar1 = *(longlong *)(param_1 + 0x48);
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// FUN_1806E33A0 — CanApplyBuff(buffSkill, actorRef, context) → bool
// All-conditions-must-pass gate. Returns true only if every condition in the list passes.

bool CanApplyBuff(BuffSkill* buffSkill, ActorRef actorRef, ContextObj context) {
    List<Condition>* conditions = buffSkill->conditions;  // +0x48

    for (int i = 0; i < conditions->count; i++) {
        Condition* cond = conditions->elements[i];
        if (cond == null) break;  // null entry terminates

        // Virtual dispatch: Condition.Evaluate(actorRef, context) → bool
        // vtable slot +0x1D8 (slot 59) — NQ-36: concrete implementations unknown
        bool passed = cond->vtable[0x1D8/8](cond, actorRef, context, cond->vtableArg_0x1E0);

        if (!passed) return false;  // any failure → immediately return false
    }
    return true;  // all conditions passed
    // null conditions list → NullReferenceException
}
```

---

## 4. AoE_PerMemberScorer — 0x181430AC0

### Raw Ghidra output
```c
undefined8 FUN_181430ac0(longlong param_1,undefined8 param_2,undefined4 *param_3,longlong param_4)
{
  longlong lVar1;
  uint uVar2;
  uVar2 = FUN_181423600(param_1,param_2,
                        *(undefined8 *)(*(longlong *)(*(longlong *)(param_4 + 0x20) + 0xc0) + 0xf8));
  if ((int)uVar2 < 0) {
    *param_3 = 0;
    return 0;
  }
  lVar1 = *(longlong *)(param_1 + 0x18);
  if (lVar1 != 0) {
    if (uVar2 < *(uint *)(lVar1 + 0x18)) {
      *param_3 = *(undefined4 *)(lVar1 + ((longlong)(int)uVar2 + 2) * 0x18);
      return CONCAT71((int7)((ulonglong)(((longlong)(int)uVar2 + 2) * 3) >> 8),1);
    }
    FUN_180427d80();
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// FUN_181430AC0 — AoE_PerMemberScorer(skillRef, actorRef, &outScore, accumulator) → bool
// Scores a single AoE target member by looking up their tier in the skill's score table.

bool AoE_PerMemberScorer(Skill* skill, Actor* actor, float* outScore, AoEContext* ctx) {
    // Resolve tier index for this actor within the AoE
    // ctx->field_0x20->field_0xC0->field_0xF8 = context float (NQ-34)
    float contextVal = ctx->field_0x20->field_0xC0->field_0xF8;
    int tier = GetAoETierForMember(skill, actor, contextVal);  // FUN_181423600 — NQ-33

    if (tier < 0) {
        *outScore = 0.0f;
        return false;  // actor not in a valid AoE tier
    }

    AoETierTable* table = skill->aoeTierTable;  // skill->field_0x18
    // table->count at +0x18; entries stride 0x18 bytes; first two entries are header/metadata
    if (tier < table->count) {
        *outScore = table->entries[tier + 2].score;  // float at entry base, +2 skips header
        return true;
    }
    // IndexOutOfRangeException if tier >= count (should not occur)
}
```

---

## 5. InflictSuppression.GetUtilityFromTileMult — 0x18073B320

### Raw Ghidra output
```c
undefined4 FUN_18073b320(void)
{
  longlong lVar1;
  if (DAT_183b931fd == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    DAT_183b931fd = '\x01';
  }
  if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) { il2cpp_runtime_class_init(DAT_18394c3d0); }
  lVar1 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
  if (lVar1 != 0) { return *(undefined4 *)(lVar1 + 0x118); }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// FUN_18073B320 — InflictSuppression.GetUtilityFromTileMult() → float
// Returns the tile utility multiplier for suppression skills from WeightsConfig.

float InflictSuppression_GetUtilityFromTileMult() {
    // IL2CPP lazy init — omitted
    WeightsConfig* weights = WEIGHTS;  // DAT_18394c3d0 static storage → +0xb8 → +8
    if (weights == null) → NullReferenceException;
    return weights->suppressionTileMultiplier;  // +0x118
}
// Compare: InflictDamage returns weights->utilityFromTileMultiplier (+0x10C)
// Each Attack subclass has its own distinct tile multiplier offset.
```

---

## 6. InflictSuppression.GetTargetValue — 0x18073B240

### Raw Ghidra output
```c
void FUN_18073b240(longlong param_1,char param_2,undefined8 param_3,undefined8 param_4,
                  undefined8 param_5,undefined8 param_6)
{
  longlong lVar1;
  longlong *plVar2;
  undefined4 uVar3;
  if (param_2 == '\0') { uVar3 = 0; }
  else {
    lVar1 = *(longlong *)(param_1 + 0x20);
    if ((*(longlong *)(param_1 + 0x10) == 0) ||
       (plVar2 = *(longlong **)(*(longlong *)(param_1 + 0x10) + 0x18), plVar2 == (longlong *)0x0))
    goto LAB_18073b314;
    uVar3 = (**(code **)(*plVar2 + 0x458))(plVar2,*(undefined8 *)(*plVar2 + 0x460));
    if (lVar1 == 0) goto LAB_18073b314;
    uVar3 = FUN_1806e2710(lVar1,uVar3,0);
  }
  if (param_1 != 0) {
    FUN_18073dd90(param_1,param_2,uVar3,param_4,1,param_3,param_5,param_6,0);
    return;
  }
LAB_18073b314:
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// FUN_18073B240 — InflictSuppression.GetTargetValue(self, coFireFlag, p3, context, p5, p6)
// Tag chain identical to InflictDamage. Passes skillEffectType = 1 to base scorer.

void InflictSuppression_GetTargetValue(SkillBehavior* self, bool coFireFlag,
                                        void* p3, void* context, void* p5, void* p6) {
    uint tagValue = 0;

    if (coFireFlag) {
        WeaponData* weaponData = self->field_0x20;             // +0x20
        TagObject* tagObj = self->agentContext->field_0x18;    // self->field_0x10->+0x18 — NQ-19
        if (tagObj == null) → NullReferenceException;

        // vtable +0x458 = GetTagIndex() — NQ-21
        uint tagIndex = tagObj->vtable[0x458/8](tagObj, tagObj->vtableArg_0x460);
        if (weaponData == null) → NullReferenceException;

        tagValue = TagEffectiveness_Apply(weaponData, tagIndex, 0);  // FUN_1806E2710
    }

    // Delegate to base scorer with skillEffectType = 1
    SkillBehavior_GetTargetValue(self, coFireFlag, tagValue, context,
                                  /*skillEffectType=*/1, p3, p5, p6, 0);
    // FUN_18073DD90
}
```

---

## 7. Stun.GetTargetValue — 0x180769B40

### Raw Ghidra output
```c
void FUN_180769b40(longlong param_1,char param_2,undefined8 param_3,undefined8 param_4,
                  undefined8 param_5,undefined8 param_6)
{
  longlong lVar1;
  longlong *plVar2;
  undefined4 uVar3;
  if (param_2 == '\0') { uVar3 = 0; }
  else {
    lVar1 = *(longlong *)(param_1 + 0x20);
    if ((*(longlong *)(param_1 + 0x10) == 0) ||
       (plVar2 = *(longlong **)(*(longlong *)(param_1 + 0x10) + 0x18), plVar2 == (longlong *)0x0))
    goto LAB_180769c14;
    uVar3 = (**(code **)(*plVar2 + 0x458))(plVar2,*(undefined8 *)(*plVar2 + 0x460));
    if (lVar1 == 0) goto LAB_180769c14;
    uVar3 = FUN_1806e2710(lVar1,uVar3,0);
  }
  if (param_1 != 0) {
    FUN_18073dd90(param_1,param_2,uVar3,param_4,2,param_3,param_5,param_6,0);
    return;
  }
LAB_180769c14:
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// FUN_180769B40 — Stun.GetTargetValue(self, coFireFlag, p3, context, p5, p6)
// Identical to InflictSuppression except passes skillEffectType = 2.

void Stun_GetTargetValue(SkillBehavior* self, bool coFireFlag,
                          void* p3, void* context, void* p5, void* p6) {
    uint tagValue = 0;

    if (coFireFlag) {
        WeaponData* weaponData = self->field_0x20;
        TagObject* tagObj = self->agentContext->field_0x18;
        if (tagObj == null) → NullReferenceException;
        uint tagIndex = tagObj->vtable[0x458/8](tagObj, tagObj->vtableArg_0x460);
        if (weaponData == null) → NullReferenceException;
        tagValue = TagEffectiveness_Apply(weaponData, tagIndex, 0);
    }

    // Delegate with skillEffectType = 2 (stun)
    SkillBehavior_GetTargetValue(self, coFireFlag, tagValue, context,
                                  /*skillEffectType=*/2, p3, p5, p6, 0);
}
```

---

## 8. Mindray.GetTargetValue — 0x180762550

### Raw Ghidra output
```c
void FUN_180762550(longlong param_1,char param_2,undefined8 param_3,longlong param_4,
                  undefined8 param_5,undefined8 param_6)
{
  char cVar1;
  undefined4 uVar2;
  longlong *plVar3;
  longlong lVar4;
  float fVar5;
  undefined4 uVar6;
  if (param_4 != 0) {
    cVar1 = FUN_180688810(param_4,0);
    if (((cVar1 != '\0') &&
        (plVar3 = (longlong *)FUN_180687510(param_4,0), plVar3 != (longlong *)0x0)) &&
       (fVar5 = (float)FUN_1805dee10(plVar3,0), 0.0 < fVar5)) {
      lVar4 = (**(code **)(*plVar3 + 0x3d8))(plVar3,*(undefined8 *)(*plVar3 + 0x3e0));
      if (lVar4 == 0) goto LAB_18076274c;
      if ((*(uint *)(lVar4 + 0xec) >> 7 & 1) == 0) {
        lVar4 = (**(code **)(*plVar3 + 0x3d8))(plVar3,*(undefined8 *)(*plVar3 + 0x3e0));
        if (lVar4 == 0) goto LAB_18076274c;
        if ((*(uint *)(lVar4 + 0xa8) & 0x100) != 0) {
          uVar2 = 0;
          if (param_2 != '\0') {
            lVar4 = *(longlong *)(param_1 + 0x20);
            if (((*(longlong *)(param_1 + 0x10) == 0) ||
                (plVar3 = *(longlong **)(*(longlong *)(param_1 + 0x10) + 0x18),
                plVar3 == (longlong *)0x0)) ||
               (uVar2 = (**(code **)(*plVar3 + 0x458))(plVar3,*(undefined8 *)(*plVar3 + 0x460)),
               lVar4 == 0)) goto LAB_18076274c;
            uVar2 = FUN_1806e2710(lVar4,uVar2,0);
          }
          if (param_1 == 0) goto LAB_18076274c;
          uVar6 = 1;
          goto LAB_1807626a5;
        }
      }
    }
    uVar2 = 0;
    if (param_2 != '\0') {
      lVar4 = *(longlong *)(param_1 + 0x20);
      if (((*(longlong *)(param_1 + 0x10) == 0) ||
          (plVar3 = *(longlong **)(*(longlong *)(param_1 + 0x10) + 0x18), plVar3 == (longlong *)0x0)
          ) || (uVar2 = (**(code **)(*plVar3 + 0x458))(plVar3,*(undefined8 *)(*plVar3 + 0x460)),
               lVar4 == 0)) goto LAB_18076274c;
      uVar2 = FUN_1806e2710(lVar4,uVar2,0);
    }
    if (param_1 != 0) {
      uVar6 = 0;
LAB_1807626a5:
      FUN_18073dd90(param_1,param_2,uVar2,param_4,uVar6,param_3,param_5,param_6,0);
      return;
    }
  }
LAB_18076274c:
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// FUN_180762550 — Mindray.GetTargetValue(self, coFireFlag, p3, context, p5, p6)
// Two-path dispatch: skillEffectType 1 for vulnerable targets, 0 for standard.

void Mindray_GetTargetValue(SkillBehavior* self, bool coFireFlag,
                             void* p3, void* context, void* p5, void* p6) {
    if (context == null) → NullReferenceException;

    if (!HasValidContext(context)) return;              // FUN_180688810
    Actor* target = GetTargetActor(context);            // FUN_180687510
    if (target == null) → NullReferenceException;

    float resistance = GetResistanceFraction(target);   // FUN_1805DEE10
    if (resistance <= 0.0f) return;                     // no resistance → skip

    EntityInfo* info = target->vtable[0x3D8/8](target, target->vtableArg_0x3E0);
    if (info == null) → NullReferenceException;

    uint effectType = 0;

    // Bit 7 of flags: skip-mindray flag — if set, return immediately
    if ((info->flags >> 7 & 1) == 0) {
        // Re-fetch info (Ghidra double-read pattern)
        info = target->vtable[0x3D8/8](target, target->vtableArg_0x3E0);
        if (info == null) → NullReferenceException;

        // Bit 0x100 of statusFlags2: mindray vulnerability flag — NQ-38
        if ((info->statusFlags2 & 0x100) != 0) {
            // Vulnerable path — run tag chain, effectType = 1
            uint tagValue = 0;
            if (coFireFlag) {
                WeaponData* wd = self->field_0x20;
                TagObject* tagObj = self->agentContext->field_0x18;
                if (tagObj == null || wd == null) → NullReferenceException;
                uint tagIndex = tagObj->vtable[0x458/8](tagObj, tagObj->vtableArg_0x460);
                tagValue = TagEffectiveness_Apply(wd, tagIndex, 0);
            }
            effectType = 1;
            SkillBehavior_GetTargetValue(self, coFireFlag, tagValue, context,
                                          /*effectType=*/1, p3, p5, p6, 0);
            return;
        }
    }

    // Standard path — run tag chain, effectType = 0
    uint tagValue = 0;
    if (coFireFlag) {
        WeaponData* wd = self->field_0x20;
        TagObject* tagObj = self->agentContext->field_0x18;
        if (tagObj == null || wd == null) → NullReferenceException;
        uint tagIndex = tagObj->vtable[0x458/8](tagObj, tagObj->vtableArg_0x460);
        tagValue = TagEffectiveness_Apply(wd, tagIndex, 0);
    }
    SkillBehavior_GetTargetValue(self, coFireFlag, tagValue, context,
                                  /*effectType=*/0, p3, p5, p6, 0);
}
```

---

## 9. TargetDesignator.GetTargetValue — 0x18076A640

### Raw Ghidra output
*(see decompiled_functions_6.txt — FUN_18076a640, lines 15–148)*

### Annotated reconstruction
```c
// FUN_18076A640 — TargetDesignator.GetTargetValue(self, p2, p3, context, p5) → float
// Scores designation targets by observer coverage and proximity reach.

float TargetDesignator_GetTargetValue(SkillBehavior* self, void* p2, void* p3,
                                       void* context, void* p5) {
    // IL2CPP lazy init (9 classes) — omitted

    if (context == null) → NullReferenceException;

    // Resolve target actor, safe-cast to Actor
    Actor* actor = ResolveActor(context);               // FUN_180688600
    if (actor == null) return 0.0f;
    Actor* actorCast = actor as Actor;                  // type-check vs Actor_class
    if (actorCast == null) return 0.0f;

    EntityInfo* info = actorCast->vtable[0x3D8/8](actorCast, actorCast->vtableArg_0x3E0);
    if (info == null) return 0.0f;  // (via goto)

    // Bit 11: already-designated exclusion flag — NQ-39
    if ((info->flags >> 0xB & 1) != 0) return 0.0f;

    // ProximityData lookup
    AgentData* agentData = self->agentContext->field_0x10;  // self->field_0x10->+0x10
    ProximityEntry* entry = ProximityData_FindEntryForTile(agentData, actorCast, 0);
    // FUN_180717730
    if (entry == null) return 0.0f;  // (via goto)

    void* entryRef = entry->field_0x20;  // position/tile ref from proximity entry
    if (entryRef == null) return 0.0f;

    float score = 0.0f;

    // --- Loop 1: Observer coverage ---
    // agentContext->behaviorConfig->field_0x28 = observer list
    // agentContext->field_0x50->field_0x28 (lVar1 = agentCtx->+0x50, +0x30 = count, +0x28 = list)
    BehaviorConfig2* cfg = self->agentContext->behaviorConfig;  // +0x50
    if (cfg->field_0x28 != null && cfg->field_0x28->count > 0) {
        foreach (ObserverEntry obs in cfg->field_0x28) {
            // FUN_1806E3750 — IsInDesignationZone(obs, context, p5) → bool — NQ-40
            bool inZone = FUN_1806E3750(obs, context, p5, 0, 0);
            score += inZone ? 0.5f : 0.25f;
        }
    }

    // --- Loop 2: Proximity reach ---
    // agentContext->field_0x20 = movement tile list
    if (self->agentContext->field_0x20 != null) {
        foreach (Tile tile in agentContext->field_0x20) {
            if (tile == null) → NullReferenceException;
            // Get tile world position via vtable +0x388
            void* tilePos = tile->vtable[0x388/8](tile, tile->vtableArg_0x390);
            if (tilePos != null) {
                int dist = GetDistanceTo(tilePos, context);  // FUN_1805CA7A0
                if (dist != 0 && dist < 11) {
                    score += (1.0f - (float)dist / 10.0f);  // linear decay
                }
            }
        }
    }

    return score * entry->field_0x88;  // scale by proximity entry weight
}
```

---

## 10. SpawnPhantom.GetTargetValue — 0x180769450

### Raw Ghidra output
*(see decompiled_functions_3.txt — FUN_180769450, lines 1160–1345)*

### Annotated reconstruction
```c
// FUN_180769450 — SpawnPhantom.GetTargetValue(self, p2, p3, context) — void side-effect scorer
// Iterates team tiles; registers eligible phantom-spawn targets via candidate registration.

void SpawnPhantom_GetTargetValue(SkillBehavior* self, void* p2, void* p3, void* context) {
    // IL2CPP lazy init (6 classes) — omitted

    if (context == null) → NullReferenceException;

    if (!HasValidTarget(context)) return;  // FUN_1806889C0

    EntityInfo* info = self->field_0x20->field_0x10;  // agentContext entity
    WeaponData* weapon = info->weaponData;             // +0x2C8
    // Type-check weapon vs PhantomWeapon_class (DAT_183974FD0)
    PhantomWeaponData* phantomWeapon = weapon as PhantomWeapon;
    if (phantomWeapon == null) return;

    if (self->agentContext->field_0x10 == null) → NullReferenceException;
    EntityInfo* agentInfo = self->agentContext->entityInfo;  // field_0x10->+0x10
    int teamID = agentInfo->field_0x14;

    // FUN_1829A9340 — unknown check on phantomWeapon->field_0x20 → bool
    bool needsSetup = FUN_1829A9340(phantomWeapon->field_0x20, 0, 0);
    if (needsSetup) {
        if (phantomWeapon->field_0x2F8 == null) → NullReferenceException;
        FUN_180628510(phantomWeapon->field_0x2F8, 0);  // setup/init action
    }

    bool foundBest = true;

    foreach (Tile tile in agentInfo->tileList) {  // +0x48
        Actor* tileActor = tile->field_0x10;
        if (!IsTeamMember(tileActor, teamID)) continue;  // FUN_180616B50

        // Get entity info via vtable +0x3D8
        EntityInfo* tileInfo = tileActor->vtable[0x3D8/8](tileActor, ...);

        // Bit 5 of flags: isPhantom — skip already-phantom actors
        if ((tileInfo->flags >> 5 & 1) != 0) continue;

        // field_0xDC: detection value — must be > 0
        if (tileInfo->field_0xDC <= 0.0f) continue;

        // Get tile position via vtable +0x388
        void* tilePos = tileActor->vtable[0x388/8](tileActor, ...);

        if (!CanReachTile(context, tilePos, 0, 0)) continue;  // FUN_1806888B0

        // Range bounds from weapon config: plVar10[3] = minRange, plVar10+0x1C = maxRange
        int dist = GetDistanceTo(context, tilePos);  // FUN_1805CA7A0
        if (dist < (int)phantomWeapon->field_0x18) return;  // below min range → abort
        if (dist > (int)phantomWeapon->field_0x1C) continue; // above max range → skip

        // Mark entity and register candidate
        MarkEntityForPhantom(tileInfo, 0);             // FUN_180628690
        void* score = GetTargetScore(context, tilePos); // FUN_1805CA720
        RegisterTarget(context, score, 0, 0, 1, 0);    // FUN_180687660

        FUN_180722ED0(tile, 0);  // TileHasAlly check (side effect or flag)

        if (foundBest) {
            bool isBest = FUN_180688BA0(context, tile->field_0x10);  // RegisterBestCandidate
            if (isBest) foundBest = false;
        }
    }
}
```

---

## 11. SpawnHovermine.GetTargetValue — 0x180768EF0

### Raw Ghidra output
*(see decompiled_functions_4.txt — FUN_180768ef0, lines 876–1040)*

### Annotated reconstruction
```c
// FUN_180768EF0 — SpawnHovermine.GetTargetValue(self, p2, p3, context) — void side-effect scorer
// Scores hovermine placement by proximity to allies; registers best candidate.

void SpawnHovermine_GetTargetValue(SkillBehavior* self, void* p2, void* p3, void* context) {
    // IL2CPP lazy init (6 classes) — omitted

    if (context == null) → NullReferenceException;
    if (!HasValidTarget(context)) return;

    EntityInfo* agentInfo = self->field_0x20->field_0x10;
    WeaponData* weapon = agentInfo->weaponData;  // +0x2C8
    // Type-check vs HovermineWeapon_class (DAT_183974CE0)
    HovermineWeaponData* hweapon = weapon as HovermineWeapon;
    if (hweapon == null) return;

    EntityInfo* entityInfo = self->agentContext->entityInfo;
    int teamID = entityInfo->field_0x14;

    bool needsSetup = FUN_1829A9340(hweapon->field_0x28, 0, 0);
    if (needsSetup) {
        FUN_180628510(hweapon->field_0x2F8, 0);
    }

    bool foundBest = true;
    float totalScore = 0.0f;

    foreach (Tile tile in entityInfo->tileList) {  // +0x48
        Actor* tileActor = tile->field_0x10;
        if (!IsTeamMember(tileActor, teamID)) continue;

        // Get tile world position via vtable +0x388
        void* tilePos = tileActor->vtable[0x388/8](tileActor, ...);

        int dist = GetDistanceTo(context, tilePos);   // FUN_1805CA7A0
        int maxRange = (int)hweapon->field_0x20;      // plVar10[4]
        int idealRange = (int)hweapon->field_0x18;    // plVar10[3]
        int midRange = (int)hweapon->field_0x1C;      // plVar10+0x1C

        if (dist <= maxRange) {
            float base = (float)(maxRange - dist + 1);  // inverse proximity score

            if (dist <= idealRange)   base *= 1.5f;
            else if (dist <= midRange) base *= 1.25f;

            // Bonus: ally is weapon-set-up
            if (tileActor->isWeaponSetUp) base *= 1.25f;  // field_0x15C

            // Penalty: no ally on tile
            if (!TileHasAlly(tile)) base *= 0.25f;        // FUN_180722ED0

            // tile->field_0x20->field_0x88 = tile weight factor
            totalScore += base * tile->field_0x20->field_0x88;

            if (foundBest) {
                bool isBest = FUN_180688BA0(context, tile->field_0x10,
                                            hweapon->setupValue, 0, totalScore);
                if (isBest) foundBest = false;
            }
        }
    }
}
```

---

## 12. SupplyAmmo.GetTargetValue — 0x180769E60

### Raw Ghidra output
*(see decompiled_functions_5.txt — FUN_180769e60, full reconstruction from two partial exports)*

### Annotated reconstruction
```c
// FUN_180769E60 — SupplyAmmo.GetTargetValue(self, coFireFlags, p3, context) → float
// Complex scorer: HP blend, AoE ally bonus (×3), weapon bonuses, buff context scaling.

float SupplyAmmo_GetTargetValue(SkillBehavior* self, byte coFireFlags,
                                 void* p3, void* context) {
    // IL2CPP lazy init (10 classes) — omitted

    // Allocate scoring state object
    ScoringState* state = new ScoringState(ScoringState_class);  // DAT_18397A178
    state->field_0x14 = 0;    // clear flags (2 bytes)
    state->field_0x18 = 0.0f; // clear base score
    state->field_0x10 = 0;    // clear AoE mode flags

    float local_98 = 0.0f, local_94 = 0.0f, local_90 = 0.0f;  // AoE zone outputs

    if (context == null) → NullReferenceException;

    // Guard: context must have valid target
    if (!HasValidContext(context)) return 0.0f;      // FUN_180688810
    Actor* target = GetTargetActor(context);          // FUN_180687510
    if (target == null) → NullReferenceException;

    // HP fraction gate: if target HP <= 15% and already has buffs, skip
    float hpFrac = GetHPFraction(target);             // FUN_1806155C0
    if (hpFrac <= 0.15f) {
        if (target->buffDataBlock == null) → NullReferenceException;
        if (target->buffDataBlock->stackCount > 0) return 0.0f;  // +0x38
    }

    // Compute normalised threshold
    float threshold = GetUtilityThreshold(self);          // FUN_180739050
    float scale = self->vtable[600/8](self, self->vtableArg_0x260);  // scale factor
    float baseScore = threshold / scale;

    // Weapon setup check: agent's weaponData must be set up and correct type
    EntityInfo* agentInfo = self->agentContext->entityInfo;  // self[4]->+0x10
    WeaponData* weapon = agentInfo->weaponData;               // +0x2C8
    // Type-check weapon vs DAT_18397E740
    bool weaponValid = (weapon as CorrectWeaponType) != null
                       && weapon->field_0x18 != null  // plVar9[3] check
                       && (bool)weapon->field_0x18;
    if (!weaponValid) baseScore = 0.0f;

    state->field_0x18 = baseScore;
    state->field_0x10 = 0;

    // Shot group population
    void* shotGroups = target->vtable[125](target, target->vtableArg_0x3F0);
    SortedContainer* container = new SortedContainer(SortedContainer_class2);
    SortedContainer_Insert(container, state, ScoringState_comparatorKey, 0);
    PopulateShotGroups(shotGroups, container, 0, 0);  // FUN_1806F2E60

    // If no valid shot group found
    if (!state->field_0x14) return 0.0f;

    // Co-fire mobility bonus
    if ((state->field_0x15 & coFireFlags) != 0 && !target->isWeaponSetUp) {
        EntityInfo* tgtInfo = target->vtable[0x3D8/8](target, ...);
        if (tgtInfo == null) → NullReferenceException;
        if ((tgtInfo->flags & 1) == 0) {  // not immobile
            int tgtState = target->vtable[0x478/8](target, ...);
            if (tgtState != 2) {
                state->field_0x18 *= 1.25f;  // mobile, non-setup target bonus
            }
        }
    }

    // AoE ally bonus loop (3 zones, each can give ×1.05)
    if (state->field_0x10 != 0) {
        EntityInfo* selfInfo = self->agentContext->field_0x10->entityInfo;
        List<Tile>* tiles = selfInfo->tileList;  // +0x48

        foreach (Tile tile in tiles) {
            if (!TileHasAlly(tile)) continue;  // FUN_180722ED0

            // Zone 0: bit 0 of state->field_0x10
            if (state->field_0x10 & 1) {
                AoETierTable* t0 = tile->field_0x20->field_0x68->elements[0];  // lVar3+0x20
                if (AoE_PerMemberScorer(t0, target, &local_98, AoE_scorer_class)) {
                    if (WEIGHTS->aoeAllyBonusThreshold < local_98) {  // +0x1A4
                        state->field_0x18 *= 1.05f;
                    }
                }
            }
            // Zone 1: bit 1
            if (state->field_0x10 & 2) {
                AoETierTable* t1 = tile->field_0x20->field_0x68->elements[1];  // lVar3+0x28
                if (AoE_PerMemberScorer(t1, target, &local_94, AoE_scorer_class)) {
                    if (WEIGHTS->aoeAllyBonusThreshold < local_94) {
                        state->field_0x18 *= 1.05f;
                    }
                }
            }
            // Zone 2: bit 2
            if (state->field_0x10 & 4) {
                AoETierTable* t2 = tile->field_0x20->field_0x68->elements[2];  // lVar3+0x30
                if (AoE_PerMemberScorer(t2, target, &local_90, AoE_scorer_class)) {
                    if (WEIGHTS->aoeAllyBonusThreshold < local_90) {
                        state->field_0x18 *= 1.05f;
                    }
                }
            }
        }
    }

    // Weapon bonuses
    if ((int)target->field_0xD0 != 0) state->field_0x18 *= 1.1f;  // has secondary weapon
    if (target->isWeaponSetUp)         state->field_0x18 *= 1.1f;  // weapon deployed

    // HP fraction blend: 80% base + 20% HP-scaled
    float finalHpFrac = GetHPFraction(target);
    float score = state->field_0x18;
    score = score * 0.2f * finalHpFrac + score * 0.8f;
    state->field_0x18 = score;

    // Final: multiply by buff context scale
    if (target->buffDataBlock != null) {
        return score * target->buffDataBlock->contextScale;  // +0x34
    }
    → NullReferenceException;
}
```

---

## 13. CreateLOSBlocker.GetTargetValue — 0x18075EB90

### Raw Ghidra output
*(see document index 5 — full function, 500+ lines)*

### Annotated reconstruction
```c
// FUN_18075EB90 — CreateLOSBlocker.GetTargetValue(self, p2, p3, context) — void side-effect scorer
// Geometry-aware LOS placement scorer with three-zone AoE coverage formula.

void CreateLOSBlocker_GetTargetValue(SkillBehavior* self, void* p2, void* p3, void* context) {
    // IL2CPP lazy init (10 classes) — omitted

    if (context == null) → NullReferenceException;

    if (!HasValidTarget(context)) return;  // FUN_1806889C0

    // Get placement evaluator from agent context
    PlacementEvaluator* eval = self->agentContext->field_0x60;  // self->field_0x10->+0x60
    if (eval == null) return;

    // Find candidate: returns PlacementCandidate with losImpact field
    PlacementCandidate candidate;
    if (!FUN_181442600(eval, context, &candidate, PlacementCandidate_class)) return;
    if (candidate == null) return;

    // Only proceed if blocker degrades opponent LOS (losImpact must be negative)
    if (candidate->losImpact >= 0.0f) return;  // +0x28

    EntityInfo* agentInfo = self->agentContext->entityInfo;  // self->field_0x10->+0x10
    List<Tile>* tileList = agentInfo->tileList;              // +0x48
    int teamID = agentInfo->field_0x14;

    // Get target world position
    Vector3 targetPos = GetWorldPosition(&local_1e8, context, 0);  // FUN_1805CA920

    float totalScore = 0.0f;

    // Outer loop: iterate blocker candidates (self->blockerCandidateList, +0x88)
    // FUN_180CBAA60 — special enumerator for this collection type
    foreach (BlockerCandidate blockerCand in self->blockerCandidateList) {
        Actor* blocker = blockerCand.actor;
        float candidateWeight = blockerCand.weight;  // float from enumerator
        fVar17 = 0.0f;

        // Get blocker world position
        void* blockerTile = blocker->vtable[0x388/8](blocker, ...);
        Vector3 blockerPos = GetWorldPosition(local_f8, blockerTile, 0);

        // Inner loop: iterate team tiles
        foreach (Tile tile in tileList) {
            Actor* ally = tile->field_0x10;
            if (!IsTeamMember(ally, teamID)) continue;  // FUN_180616B50
            if (!TileHasAlly(tile)) continue;            // FUN_180722ED0

            EntityInfo* allyInfo = ally->vtable[0x3D8/8](ally, ...);
            if ((allyInfo->flags & 1) != 0) continue;   // skip immobile

            // vtable +0x468 = GetActorState(); state 1 = committed/skip
            int allyState = ally->vtable[0x468/8](ally, ...);
            if (allyState == 1) continue;

            // Check if ally benefits from this blocker via primary AoE table
            // tile->field_0x20->field_0x58 = ally's AoE tier table (slot 2)
            float aoeBase;
            AoETierTable* tierTable = tile->field_0x20->field_0x58;
            if (!AoE_PerMemberScorer(tierTable, blocker, &aoeBase, AoE_scorer_class)) continue;
            if (aoeBase == 0.0f) continue;

            // Distance from ally position to blocker tile
            void* allyPos = ally->vtable[0x388/8](ally, ...);
            int dist = GetDistanceTo(allyPos, blockerTile);  // FUN_1805CA7A0

            // Range/geometry check: blocker must be beyond max range threshold
            RangeData* range = tile->field_0x20->field_0x38;
            if ((float)range->field_0x1C >= (float)dist) continue;

            // Axis-aligned bracket: blocker must lie between ally and target
            // in both X (field_0x10) and Y (field_0x14) dimensions
            if (!BlockerIsOnLOSLine(targetPos, blockerPos, allyPos)) continue;

            // Compute relative position and project onto blocker line
            Vector3 relPos = blockerWorldPos - allyWorldPos;
            Vector3 projected = FUN_1805122A0(local_d8, &relPos, 0);

            // 3D distance from target to the blocker line
            float dist3D = Compute3DDistance(&targetPos, &projected, &allyPos, 0);
            // FUN_180538030

            if (dist3D > 5.656854f) continue;  // 4*sqrt(2) — diagonal threshold

            float contribution = 0.0f;

            // Three-zone AoE coverage check
            // tile->field_0x20->field_0x68 = AoE table with 3 elements
            AoETable* aoeTable = tile->field_0x20->field_0x68;
            float z0, z1, z2;
            bool hit0 = AoE_PerMemberScorer(aoeTable->elements[0], blocker, &z0);
            bool hit1 = hit0 && AoE_PerMemberScorer(aoeTable->elements[1], blocker, &z1);
            bool hit2 = hit1 && AoE_PerMemberScorer(aoeTable->elements[2], blocker, &z2);

            if (hit2) {
                // Stack multiplier: each buff stack above 1 adds 0.25
                int stackCount = blocker->buffDataBlock->stackCount;  // +0xC8->+0x38
                float stackMult = (float)(stackCount - 1) * 0.25f + 1.0f;

                // Core formula: stack-scaled base minus existing AoE coverage
                contribution = stackMult * aoeBase - (z0 + z1 + z2);

                // Weapon-setup penalty: committed ally can't exploit blocker as well
                if (contribution > 0.0f && ally->isWeaponSetUp) {  // +0x15C
                    contribution *= 0.8f;
                }
            }

            fVar17 += contribution;
        }  // end inner tile loop

        if (fVar17 > 0.0f) fVar17 *= candidateWeight;
        totalScore += fVar17;
    }  // end outer blocker candidate loop
    // Result communicated via side effect (candidate registration implicit in loop)
}
```

---

*End of Stage 5 RECONSTRUCTIONS.md*
```

---

Now the handoff prompt:

---
```
# Investigation Handoff — Menace Tactical AI Behavior Scorers — Stage 5 → Stage 6

## Directive
Read Research-AI.md in full before proceeding. It is attached by the operator.

## Investigation Target
- **Game:** Menace, Windows x64, Unity IL2CPP
- **Image base:** 0x180000000
- **System under investigation:** Menace.Tactical.AI.Behaviors namespace — all concrete behavior scorer classes
- **Investigation status:** In Progress
- **Stage:** 6 of ~6
- **VAs complete across all stages:** 47 of ~55

## Extraction Report
Attached as extraction_report_master.txt. Classes covered: Assist, Attack, Buff, Deploy,
GainBonusTurn, Idle, InflictDamage, InflictSuppression, Move, Reload, RemoveStatusEffect,
CreateLOSBlocker, GainBonusTurn, Mindray, MovementSkill, Scan, SpawnHovermine, SpawnPhantom,
SupplyAmmo, TargetDesignator, TransportEntity, Stun, TurnArmorTowardsThreat.

---

## Stage Artefacts on Disk
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
```

---

## Resolved Symbol Maps

### FUN_ → Method Name
```
FUN_180427b00 = il2cpp_runtime_class_init          // lazy init guard — ignore
FUN_180427d90 = NullReferenceException             // does not return
FUN_180427d80 = IndexOutOfRangeException           // does not return
FUN_1804bad80 = powf(value, exponent)
FUN_180426e50 = IL2CPP write barrier               // ignore semantically
FUN_180cbab80 = List.GetEnumerator
FUN_18136d8a0 = Dictionary.GetEnumerator
FUN_18152f9b0 = Dictionary enumerator MoveNext
FUN_1814f4770 = List enumerator MoveNext
FUN_1804f7ee0 = Enumerator.Dispose
FUN_180426ed0 = IL2CPP allocate object
FUN_1804608d0 = Allocate/construct list or collection
FUN_180cca560 = List[index] get element
FUN_18073dd90 = SkillBehavior.GetTargetValue (public base scorer)
FUN_18073bfa0 = SkillBehavior.GetTagValueAgainst
FUN_18073af00 = InflictDamage.GetTargetValue
FUN_18073afe0 = InflictDamage.GetUtilityFromTileMult  // returns WeightsConfig+0x10C
FUN_1807391c0 = Buff.GetTargetValue
FUN_1806da770 = ShotCandidate_PostProcess
FUN_1806e2710 = TagEffectiveness_Apply(weaponData, tagIndex, 0) → uint
FUN_1806e33a0 = CanApplyBuff(buffSkill, actorRef, context) → bool
FUN_1805df080 = GetMissingHPAmount(actor) → float
FUN_1805dee10 = GetResistanceFraction(actor) → float [0,1]
FUN_181430ac0 = AoE_PerMemberScorer(skillRef, actor, &out, class) → bool
FUN_180628210 = IsReadyToFire(entityInfo) → bool
FUN_180687590 = GetBuffStackCount(targetRef) → int
FUN_1806d5040 = ShotPath_ActorCast(shotPath) → Actor* (safe cast on +0x30)
FUN_180688600 = ResolveActor(targetRef) → Actor*
FUN_180722ed0 = TileHasAlly(tile) → bool
FUN_1805406a0 = IsActorInRange(tileRef, actorPos) → bool
FUN_1806f0e90 = SortedContainer.Insert(container, entry, key, 0)
FUN_1818897c0 = List.Append(list, item, class)
FUN_1804eb570 = Object.Init / constructor call
FUN_1806361f0 = StrategyData.ComputeMoveCost            // deferred NQ-11
FUN_1806df4e0 = ComputeDamageData
FUN_1806e0ac0 = ComputeHitProbability
FUN_1806e66f0 = Skill.BuildCandidatesForShotGroup
FUN_1806de1d0 = Indirect fire trajectory builder        // deferred
FUN_1806e1fb0 = AoE target set builder                  // deferred
FUN_1806ddec0 = GetTagTierCount(weaponData, 0) → int    // NQ-30
FUN_180002310 = TagModifier.GetValue(mode, class, entry) → uint  // NQ-31
FUN_181423600 = GetAoETierForMember(skill, actor, contextVal) → int  // NQ-33
FUN_180688810 = HasValidContext(context) → bool
FUN_180687510 = GetTargetActor(context) → Actor*
FUN_1806155c0 = GetHPFraction(actor) → float
FUN_1806f2e60 = PopulateShotGroups(shotGroupList, container, 0, 0)
FUN_180688ba0 = RegisterBestCandidate(context, tileRef, score, ...)
FUN_1806889c0 = HasValidTarget(context) → bool
FUN_181442600 = PlacementEvaluator.FindCandidate(eval, context, &out, class) → bool
FUN_1805ca920 = GetWorldPosition(buffer, tileOrContext, 0) → Vector3*
FUN_1805122a0 = ProjectRelativePosition(buffer, &relPos, 0) → Vector3*
FUN_180cbaa60 = GetEnumerator (blocker candidate list — special collection)
FUN_1814dd090 = BlockerCandidate enumerator MoveNext → bool
FUN_180538030 = Compute3DDistance(posA, posB, ref, 0) → float
FUN_1806e3750 = IsInDesignationZone(entry, context, param, 0, 0) → bool  // NQ-40
FUN_1805ca7a0 = GetDistanceTo(position, context) → int
FUN_1829a9340 = unknown check on weapon subobject → bool
FUN_180628510 = unknown setup/init action on entity subobject
FUN_180628690 = MarkEntityForPhantomSpawn(entityInfo)
FUN_180616b50 = IsTeamMember(actor, teamID) → bool
FUN_180717730 = ProximityData.FindEntryForTile(data, actor, 0) → ProximityEntry*
FUN_18073b240 = InflictSuppression.GetTargetValue       // effectType=1
FUN_18073b320 = InflictSuppression.GetUtilityFromTileMult  // returns WeightsConfig+0x118
FUN_180769b40 = Stun.GetTargetValue                     // effectType=2
FUN_180762550 = Mindray.GetTargetValue                  // effectType 0 or 1
FUN_18076a640 = TargetDesignator.GetTargetValue         // float observer+proximity scorer
FUN_180769e60 = SupplyAmmo.GetTargetValue               // complex float scorer
FUN_180769450 = SpawnPhantom.GetTargetValue             // void eligibility scorer
FUN_180768ef0 = SpawnHovermine.GetTargetValue           // void proximity scorer
FUN_18075eb90 = CreateLOSBlocker.GetTargetValue         // void geometry+AoE scorer
```

### DAT_ → Class / Static Field
```
DAT_18394c3d0 = WeightsConfig_class  (+0xb8 → ptr; ptr+8 → WEIGHTS singleton)
DAT_18394dc38 = Actor_class
DAT_18395f730 = BuffSkill_class
DAT_1839441d8 = AoE_scorer_class
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
DAT_18397ae78 = TagEffectivenessTable (+0x18=length int, +0x20=float[])
DAT_1839a6620 = TagModifier_class
DAT_183974fd0 = PhantomWeapon_class
DAT_183974ce0 = HovermineWeapon_class
DAT_18394df48 = (unknown class — init guard in SpawnPhantom/SpawnHovermine)
DAT_18397e740 = (weapon type class — checked in SupplyAmmo weapon cast)
DAT_18397a178 = ScoringState_class
DAT_183976418 = SortedContainer_class2 (shot group container)
DAT_1839a3118 = ScoringState_comparatorKey
DAT_183993cb0 = DesignationObserver_enumerator_dispose_class
DAT_183938690 = DesignationObserver_dispose_class2
DAT_183993d68 = MovementTile_enumerator_class2
DAT_183938748 = DesignationObserver_moveNext_class
DAT_183938800 = (unknown — init guard)
DAT_183993e20 = (unknown — init guard)
DAT_18397ae10 = DesignationObserver_list_class
DAT_1839a25c0 = MovementTile_list_class
DAT_1839779f8 = PlacementCandidate_class
DAT_1839468d8 = BlockerCandidate_enumerator_dispose_class
DAT_183946990 = BlockerCandidate_moveNext_class
DAT_1839a35d0 = BlockerCandidate_list_class
DAT_183946a48 = (unknown — init guard)
```