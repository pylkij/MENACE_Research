# Menace Tactical AI — Stage 4 Annotated Function Reconstructions

**Source:** Ghidra decompilation of Menace (Windows x64, Unity IL2CPP GameAssembly.dll)  
**Image base:** 0x180000000  
**Stage:** 4 — InflictDamage subclass, Buff subclass, shot candidate post-processor  
**Format:** Each function shows the raw Ghidra output followed by a fully annotated C-style reconstruction with all offsets resolved.

---

## Quick-Reference Offset Tables

### WeightsConfig (singleton: DAT_18394c3d0 +0xb8 +8) — Stage 4 fields only

| Offset | Field | Type |
|---|---|---|
| +0x10C | utilityFromTileMultiplier | float |
| +0x174 | buffGlobalScoringScale | float |
| +0x17C | healScoringWeight | float |
| +0x180 | buffScoringWeight | float |
| +0x184 | suppressScoringWeight | float |
| +0x188 | setupAssistScoringWeight | float |
| +0x18C | aoeBuffScoringWeight | float |
| +0x190 | aoeHealScoringWeight | float |

### Actor (partial — Stage 4 additions)

| Offset | Field | Type | Status |
|---|---|---|---|
| +0x15C | isIncapacitated | bool | confirmed |
| +0x167 | isWeaponSetUp | bool | confirmed |
| +0xC8 | buffDataBlock | ptr | inferred |
| +0xD0 | field_0xD0 | int | inferred |

### EntityInfo (partial — Stage 4 additions)

| Offset | Field | Type | Status |
|---|---|---|---|
| +0x18 | field_0x18 | ptr | inferred — weapon/tag object |
| +0x2C8 | weaponData | ptr | confirmed (prior stages) |
| +0x48 | tileList | List\<Tile\>* | confirmed (prior stages) |
| +0xEC | flags (bit 0 = isImmobile) | uint | confirmed (prior stages) |

---

## Function Order (leaf-first)

1. `InflictDamage.GetUtilityFromTileMult` — pure static getter, no callees
2. `FUN_1806DA770` — shot candidate post-processor, no scoring callees
3. `InflictDamage.GetTargetValue` — thin wrapper calling base scorer
4. `Buff.GetTargetValue` — top-level; calls multiple helpers

---

## 1. InflictDamage.GetUtilityFromTileMult — 0x18073AFE0

### Raw Ghidra output

```c
undefined4 FUN_18073afe0(void)

{
  longlong lVar1;
  
  if (DAT_183b931fa == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    DAT_183b931fa = '\x01';
  }
  if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
    il2cpp_runtime_class_init(DAT_18394c3d0);
  }
  lVar1 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
  if (lVar1 != 0) {
    return *(undefined4 *)(lVar1 + 0x10c);
  }
                    /* WARNING: Subroutine does not return */
  FUN_180427d90();
}
```

### Annotated reconstruction

```c
// IL2CPP lazy init — omitted

float InflictDamage_GetUtilityFromTileMult(void)
{
    WeightsConfig* w = WeightsConfig_WEIGHTS;  // DAT_18394c3d0 +0xb8 +8
    if (w == NULL) NullReferenceException();

    return w->utilityFromTileMultiplier;  // +0x10C
}
```

### GetUtilityFromTileMult — design notes

Pure static getter. Returns a single float from the WeightsConfig singleton. No computation. Called as a companion to `InflictDamage.GetTargetValue` to provide a tile-based utility multiplier. The naming implies it scales utility derived from tile position relative to the target — the exact consumption site is inside `SkillBehavior.GetTargetValue`.

---

## 2. FUN_1806DA770 — Shot Candidate Post-Processor — 0x1806DA770

### Raw Ghidra output

```c
void FUN_1806da770(longlong param_1,longlong param_2)

{
  longlong lVar1;
  undefined8 uVar2;
  
  if (DAT_183b92f90 == '\0') {
    FUN_180427b00(&DAT_18398bd58);
    FUN_180427b00(&DAT_183992e08);
    FUN_180427b00(&DAT_18399cc78);
    FUN_180427b00(&DAT_183976118);
    DAT_183b92f90 = '\x01';
  }
  lVar1 = thunk_FUN_1804608d0(DAT_183976118);
  FUN_1804eb570(lVar1,0);
  if (lVar1 != 0) {
    *(longlong *)(lVar1 + 0x10) = param_1;
    FUN_180426e50(lVar1 + 0x10,param_1);
    if (*(longlong *)(param_1 + 0x10) != 0) {
      if (*(longlong *)(*(longlong *)(param_1 + 0x10) + 0x180) != 0) {
        uVar2 = FUN_1806d5040(param_1,0);
        *(undefined8 *)(lVar1 + 0x18) = uVar2;
        FUN_180426e50(lVar1 + 0x18,uVar2);
        uVar2 = thunk_FUN_1804608d0(DAT_183992e08);
        FUN_1806f0e90(uVar2,lVar1,DAT_18399cc78,0);
        if (param_2 == 0) goto LAB_1806da86f;
        FUN_1818897c0(param_2,uVar2,DAT_18398bd58);
      }
      return;
    }
  }
LAB_1806da86f:
                    /* WARNING: Subroutine does not return */
  FUN_180427d90();
}
```

### Annotated reconstruction

```c
// IL2CPP lazy init — omitted

void ShotCandidate_PostProcess(ShotPath* shotPath,   // param_1
                               List* outputList)      // param_2 — candidate output list
{
    // Allocate a new ShotCandidateWrapper object
    ShotCandidateWrapper* entry = new(ShotCandidateWrapper_class);  // DAT_183976118
    entry->Init(0);  // FUN_1804eb570 — constructor/init

    if (entry == NULL) goto null_throw;

    entry->shotPath = shotPath;  // +0x10 — store ShotPath reference
    // write barrier

    if (shotPath->field_0x10 == NULL) goto null_throw;

    // Only package shots that have a valid trajectory/arc block
    if (shotPath->field_0x10->field_0x180 != NULL) {

        // Compute a derived metric from the ShotPath (NQ-22: unknown exact purpose)
        entry->derivedMetric = FUN_1806D5040(shotPath, 0);  // +0x18
        // write barrier

        // Allocate a sorted/keyed container for this entry
        SortedContainer* container = new(SortedContainer_class);  // DAT_183992E08

        // Insert entry into container with comparator key DAT_18399CC78
        FUN_1806F0E90(container, entry, ComparatorKey, 0);

        if (outputList == NULL) goto null_throw;

        // Append container to the caller's output candidate list
        FUN_1818897C0(outputList, container, ListClass);  // DAT_18398BD58
    }
    // If field_0x180 == NULL: shot has no trajectory block — silently skip (no error)
    return;

null_throw:
    NullReferenceException();
}
```

### PostProcess — design notes

This function is a packaging step called at the end of `BuildCandidatesForShotGroup` (Stage 3). It does not score the shot. It wraps a validated `ShotPath` in a keyed container suitable for sorted insertion into the candidates list.

The guard on `shotPath->field_0x10->field_0x180` is the trajectory/arc block — consistent with the deferred indirect-fire trajectory builder (FUN_1806DE1D0). Shots without a computed arc block are excluded from the candidate list silently: control returns after the null check without throwing. This is intentional filtering, not an error path.

`FUN_1806D5040` computes a derived metric stored at `entry +0x18`. Its exact purpose is unknown (NQ-22) but contextually it is likely an accuracy estimate or priority score used by the comparator for sorted insertion.

---

## 3. InflictDamage.GetTargetValue — 0x18073AF00

### Raw Ghidra output

```c
void FUN_18073af00(longlong param_1,char param_2,undefined8 param_3,undefined8 param_4,
                  undefined8 param_5,undefined8 param_6)

{
  longlong lVar1;
  longlong *plVar2;
  undefined4 uVar3;
  
  if (param_2 == '\0') {
    uVar3 = 0;
  }
  else {
    lVar1 = *(longlong *)(param_1 + 0x20);
    if ((*(longlong *)(param_1 + 0x10) == 0) ||
       (plVar2 = *(longlong **)(*(longlong *)(param_1 + 0x10) + 0x18), plVar2 == (longlong *)0x0))
    goto LAB_18073afd4;
    uVar3 = (**(code **)(*plVar2 + 0x458))(plVar2,*(undefined8 *)(*plVar2 + 0x460));
    if (lVar1 == 0) goto LAB_18073afd4;
    uVar3 = FUN_1806e2710(lVar1,uVar3,0);
  }
  if (param_1 != 0) {
    FUN_18073dd90(param_1,param_2,uVar3,param_4,0,param_3,param_5,param_6,0);
    return;
  }
LAB_18073afd4:
                    /* WARNING: Subroutine does not return */
  FUN_180427d90();
}
```

### Annotated reconstruction

```c
void InflictDamage_GetTargetValue(
    InflictDamage* self,    // param_1
    bool isCoFire,          // param_2
    undefined8 param_3,     // forwarded to base scorer
    undefined8 param_4,     // forwarded to base scorer
    undefined8 param_5,     // forwarded to base scorer
    undefined8 param_6)     // forwarded to base scorer
{
    uint tagValue;

    if (!isCoFire) {
        // Direct (non-co-fire) attack: tag value is irrelevant
        tagValue = 0;
    }
    else {
        // Co-fire attack: compute tag effectiveness against target
        longlong weaponData = self->field_0x20;  // +0x20 — weapon data block or secondary ref

        EntityInfo* entity = self->entityInfo;   // +0x10 — confirmed field
        if (entity == NULL) goto null_throw;

        // Resolve tag-carrying object from EntityInfo +0x18 (NQ-19: field not yet named)
        TagObject* tagObj = entity->field_0x18;  // +0x18 — inferred: weapon or tag source
        if (tagObj == NULL) goto null_throw;

        // Virtual call: vtable +0x458 — GetTag() or GetWeaponTag() (NQ-21)
        tagValue = tagObj->vtable[0x458/8](tagObj, tagObj->vtableArg_0x460);

        if (weaponData == NULL) goto null_throw;

        // Apply tag effectiveness: FUN_1806E2710(weaponData, tagIndex, 0) (NQ-20)
        // Looks up TagEffectivenessTable using weapon context and tag index
        tagValue = FUN_1806E2710(weaponData, tagValue, 0);
    }

    if (self == NULL) goto null_throw;

    // Delegate entirely to SkillBehavior.GetTargetValue (public) — Stage 1, 0x18073DD90
    // tagValue is injected as the third argument; base scorer applies tagValueScale (+0xBC)
    SkillBehavior_GetTargetValue_Public(self, isCoFire, tagValue, param_4, 0, param_3, param_5, param_6, 0);
    return;

null_throw:
    NullReferenceException();
}
```

### GetTargetValue — design notes

This function is structurally a decorator: it prepends tag value computation and delegates the actual scoring to `SkillBehavior.GetTargetValue`. The InflictDamage class adds no scoring logic of its own beyond tag value injection.

The co-fire gate is significant. When `isCoFire == false`, `tagValue = 0` is passed to the base scorer. Inside `SkillBehavior.GetTargetValue`, the tag contribution is `tagValue * tagValueScale`. With `tagValue = 0`, this term vanishes. This means `WeightsConfig->tagValueScale` (+0xBC) has architecturally zero effect on solo attacks.

The `weaponData` variable at `self +0x20` is a secondary reference that is not `entityInfo`. Its exact type is not yet confirmed — it may be the ShotPath or a weapon config sub-object (NQ field at InflictDamage +0x20, not previously in the table).

---

## 4. Buff.GetTargetValue — 0x1807391C0

### Raw Ghidra output

```c
float FUN_1807391c0(longlong param_1,undefined8 param_2,longlong param_3,longlong param_4)

{
  longlong lVar1;
  undefined8 uVar2;
  bool bVar3;
  float fVar4;
  char cVar5;
  int iVar6;
  longlong *plVar7;
  longlong lVar8;
  undefined8 uVar9;
  longlong *plVar10;
  longlong *plVar11;
  float fVar12;
  float fVar13;
  float fVar14;
  undefined8 local_120;
  undefined8 *puStack_118;
  longlong local_110;
  float local_108;
  float local_104;
  float local_100 [2];
  longlong *local_f8;
  undefined8 local_f0;
  undefined8 *puStack_e8;
  longlong local_e0;
  longlong *local_d8;
  undefined8 uStack_d0;
  undefined8 local_c8;
  undefined8 *puStack_c0;
  longlong local_b8;
  
  if (DAT_183b931f6 == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    FUN_180427b00(&DAT_18394dc38);
    FUN_180427b00(&DAT_18395f730);
    FUN_180427b00(&DAT_1839441d8);
    FUN_180427b00(&DAT_183945130);
    FUN_180427b00(&DAT_1839ada98);
    FUN_180427b00(&DAT_1839451e8);
    FUN_180427b00(&DAT_1839adb50);
    FUN_180427b00(&DAT_1839adc08);
    FUN_180427b00(&DAT_1839452a0);
    FUN_180427b00(&DAT_18399f748);
    FUN_180427b00(&DAT_183968278);
    DAT_183b931f6 = '\x01';
  }
  local_f0 = 0;
  puStack_e8 = (undefined8 *)0x0;
  local_e0 = 0;
  local_108 = 0.0;
  local_104 = 0.0;
  local_100[0] = 0.0;
  local_c8 = 0;
  puStack_c0 = (undefined8 *)0x0;
  local_b8 = 0;
  if ((param_3 == 0) || (*(longlong *)(param_3 + 0x10) == 0)) goto LAB_180739efb;
  plVar7 = *(longlong **)(*(longlong *)(param_3 + 0x10) + 0x2c8);
  if (plVar7 == (longlong *)0x0) {
    return 0.0;
  }
  if ((*(byte *)(*plVar7 + 0x130) < *(byte *)(DAT_18395f730 + 0x130)) ||
     (*(longlong *)
       (*(longlong *)(*plVar7 + 200) + -8 + (ulonglong)*(byte *)(DAT_18395f730 + 0x130) * 8) !=
      DAT_18395f730)) {
    bVar3 = false;
  }
  else {
    bVar3 = true;
  }
  plVar11 = (longlong *)0x0;
  if (bVar3) {
    plVar11 = plVar7;
  }
  if (plVar11 == (longlong *)0x0) {
    return 0.0;
  }
  local_d8 = plVar11;
  if (param_4 == 0) goto LAB_180739efb;
  plVar7 = (longlong *)FUN_180688600(param_4,0);
  if (plVar7 == (longlong *)0x0) {
    return 0.0;
  }
  if ((*(byte *)(*plVar7 + 0x130) < *(byte *)(DAT_18394dc38 + 0x130)) ||
     (*(longlong *)
       (*(longlong *)(*plVar7 + 200) + -8 + (ulonglong)*(byte *)(DAT_18394dc38 + 0x130) * 8) !=
      DAT_18394dc38)) {
    bVar3 = false;
  }
  else {
    bVar3 = true;
  }
  plVar10 = (longlong *)0x0;
  if (bVar3) {
    plVar10 = plVar7;
  }
  if (plVar10 == (longlong *)0x0) {
    return 0.0;
  }
  if (plVar10[0x19] == 0) {
    return 0.0;
  }
  local_f8 = plVar10;
  cVar5 = FUN_1806e33a0(param_3,param_4,plVar10,0);
  if (cVar5 == '\0') {
    return 0.0;
  }
  fVar14 = 0.0;
  if ((*(byte *)(plVar11 + 3) & 1) != 0) {
    fVar14 = (float)FUN_1805df080(plVar10,0);
    if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
      il2cpp_runtime_class_init(DAT_18394c3d0);
    }
    lVar8 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
    if (lVar8 == 0) goto LAB_180739efb;
    fVar14 = *(float *)(lVar8 + 0x17c) * fVar14;
    lVar8 = (**(code **)(*plVar10 + 0x3d8))(plVar10,*(undefined8 *)(*plVar10 + 0x3e0));
    if (lVar8 == 0) goto LAB_180739efb;
    if (((*(uint *)(lVar8 + 0xec) & 1) != 0) && ((*(byte *)(plVar11 + 3) & 2) == 0)) {
      fVar14 = fVar14 * 0.5;
    }
    if (*(char *)((longlong)plVar10 + 0x15c) == '\0') {
      fVar14 = fVar14 * 1.1;
    }
    fVar14 = fVar14 + 0.0;
  }
  if ((*(byte *)(plVar11 + 3) & 2) != 0) {
    if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
      il2cpp_runtime_class_init(DAT_18394c3d0);
    }
    lVar8 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
    if (lVar8 == 0) goto LAB_180739efb;
    fVar13 = *(float *)(lVar8 + 0x180);
    iVar6 = (**(code **)(*plVar10 + 0x478))(plVar10,*(undefined8 *)(*plVar10 + 0x480));
    if ((iVar6 == 2) && ((*(byte *)(plVar11 + 3) & 1) == 0)) {
      fVar13 = fVar13 * 0.1;
    }
    if (*(char *)((longlong)plVar10 + 0x15c) == '\0') {
      fVar13 = fVar13 * 1.5;
    }
    fVar14 = fVar14 + fVar13;
  }
  if ((*(uint *)(plVar11 + 3) & 0x8000) != 0) {
    if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
      il2cpp_runtime_class_init(DAT_18394c3d0);
    }
    lVar8 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
    if (lVar8 == 0) goto LAB_180739efb;
    fVar13 = *(float *)(lVar8 + 0x184);
    fVar12 = (float)FUN_1805dee10(plVar10,0);
    fVar13 = (1.0 - fVar12) * fVar13;
    if ((0.0 < fVar13) &&
       (iVar6 = (**(code **)(*plVar10 + 0x468))(plVar10,*(undefined8 *)(*plVar10 + 0x470)),
       iVar6 == 1)) {
      fVar13 = fVar13 + fVar13;
    }
    lVar8 = (**(code **)(*plVar10 + 0x3d8))(plVar10,*(undefined8 *)(*plVar10 + 0x3e0));
    if (lVar8 == 0) goto LAB_180739efb;
    if (((*(uint *)(lVar8 + 0xec) & 1) != 0) && ((*(byte *)(plVar11 + 3) & 2) == 0)) {
      fVar13 = fVar13 * 0.5;
    }
    iVar6 = (**(code **)(*plVar10 + 0x478))(plVar10,*(undefined8 *)(*plVar10 + 0x480));
    if ((iVar6 == 2) && ((*(byte *)(plVar11 + 3) & 1) == 0)) {
      fVar13 = fVar13 * 0.9;
    }
    if (*(char *)((longlong)plVar10 + 0x15c) == '\0') {
      fVar13 = fVar13 * 1.5;
    }
    fVar14 = fVar14 + fVar13;
  }
  if ((*(uint *)(plVar11 + 3) & 0x20000) != 0) {
    fVar13 = 0.0;
    if (((*(longlong *)(param_1 + 0x10) == 0) ||
        (lVar8 = *(longlong *)(*(longlong *)(param_1 + 0x10) + 0x10), lVar8 == 0)) ||
       (lVar8 = *(longlong *)(lVar8 + 0x48), lVar8 == 0)) goto LAB_180739efb;
    FUN_180cbab80(&local_120,lVar8,DAT_183968278);
    local_f0 = local_120;
    puStack_e8 = puStack_118;
    local_e0 = local_110;
    local_120 = 0;
    puStack_118 = &local_f0;
    while (cVar5 = FUN_1814f4770(&local_f0,DAT_1839adb50), lVar8 = local_e0, cVar5 != '\0') {
      if (local_e0 == 0) {
                    /* WARNING: Subroutine does not return */
        FUN_180427d90();
      }
      cVar5 = FUN_180722ed0(local_e0,0);
      if (cVar5 != '\0') {
        if (lVar8 == 0) {
                    /* WARNING: Subroutine does not return */
          FUN_180427d90();
        }
        lVar8 = *(longlong *)(lVar8 + 0x20);
        if (lVar8 == 0) {
                    /* WARNING: Subroutine does not return */
          FUN_180427d90();
        }
        lVar8 = *(longlong *)(lVar8 + 0x58);
        if (lVar8 == 0) {
                    /* WARNING: Subroutine does not return */
          FUN_180427d90();
        }
        cVar5 = FUN_181430ac0(lVar8,plVar10,&local_108,DAT_1839441d8);
        if (cVar5 != '\0') {
          fVar13 = fVar13 + local_108;
        }
      }
    }
    FUN_1804f7ee0(&local_f0,DAT_1839ada98);
    if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
      il2cpp_runtime_class_init();
    }
    lVar8 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
    if (lVar8 == 0) goto LAB_180739efb;
    fVar14 = fVar14 + *(float *)(lVar8 + 400) * fVar13;
  }
  // [Lines 231-262 present in full document copy — see below for reconstructed content]
  // AoE buff branch (bit 18 = 0x40000) and setup branch (bit 16 = 0x10000) follow same pattern
  if (plVar10[0x19] != 0) {
    fVar13 = *(float *)(plVar10[0x19] + 0x34);
    if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
      il2cpp_runtime_class_init();
    }
    lVar8 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
    if (lVar8 != 0) {
      return fVar13 * fVar14 * *(float *)(lVar8 + 0x174);
    }
  }
LAB_180739efb:
                    /* WARNING: Subroutine does not return */
  FUN_180427d90();
}
```

### Annotated reconstruction

```c
// IL2CPP lazy init — omitted

float Buff_GetTargetValue(
    SkillBehavior* self,    // param_1 — the Buff behavior object
    undefined8 param_2,     // unused
    longlong casterCtx,     // param_3 — caster context (provides EntityInfo + team tile list)
    longlong targetRef)     // param_4 — target Tile* or Actor*
{
    // ── GUARD: resolve and validate buff skill ──
    if (casterCtx == NULL || casterCtx->entityInfo == NULL) goto null_throw;  // +0x10

    // entityInfo->weaponData (+0x2C8) = the Buff skill object on the caster
    BuffSkill* buffSkill = casterCtx->entityInfo->weaponData;  // EntityInfo +0x2C8
    if (buffSkill == NULL) return 0.0;

    // IL2CPP instanceof check: buffSkill must be instance of Buff skill class (DAT_18395f730)
    if (!instanceof(buffSkill, BuffSkill_class)) return 0.0;

    // ── GUARD: resolve target actor ──
    if (targetRef == NULL) goto null_throw;
    Actor* actor = FUN_180688600(targetRef, 0);  // resolve Tile->Actor or cast
    if (actor == NULL) return 0.0;

    // IL2CPP instanceof check: must be Actor class (DAT_18394dc38)
    if (!instanceof(actor, Actor_class)) return 0.0;

    // actor->buffDataBlock (+0xC8) must exist — holds context scale and stack count
    if (actor->buffDataBlock == NULL) return 0.0;  // plVar10[0x19] = actor +0xC8

    // ── GUARD: eligibility check (range, LOS, applicability) ──
    bool canApply = FUN_1806E33A0(casterCtx, targetRef, actor, 0);  // NQ-23
    if (!canApply) return 0.0;

    // ── Decode buffSkill flags byte at buffSkill +0x18 ──
    // (plVar11 is longlong*, so plVar11+3 as byte* = buffSkill +0x18)
    byte flags = buffSkill->flags;  // +0x18

    float total = 0.0;

    // ══════════════════════════════════════════════════
    // BRANCH 1 — HEAL (flags bit 0)
    // ══════════════════════════════════════════════════
    if (flags & 0x01) {
        // Get heal amount (missing HP or healable value) — NQ-24
        float healAmount = (float)FUN_1805DF080(actor, 0);

        // IL2CPP lazy init — omitted
        WeightsConfig* w = WeightsConfig_WEIGHTS;
        if (w == NULL) goto null_throw;

        float score = w->healScoringWeight * healAmount;  // +0x17C

        // Get actor's EntityInfo via vtable +0x3D8
        EntityInfo* actorEntity = actor->vtable[0x3D8/8](actor, actor->vtableArg_0x3E0);
        if (actorEntity == NULL) goto null_throw;

        // Penalty: immobile target without status buff
        if ((actorEntity->flags & 1) && !(flags & 0x02)) {  // EntityInfo +0xEC bit 0
            score *= 0.5;
        }

        // Bonus: not incapacitated
        if (!actor->isIncapacitated) {  // Actor +0x15C
            score *= 1.1;
        }

        total += score;
        // (fVar14 += score + 0.0 — the + 0.0 is a Ghidra artefact, no semantic meaning)
    }

    // ══════════════════════════════════════════════════
    // BRANCH 2 — STATUS BUFF (flags bit 1)
    // ══════════════════════════════════════════════════
    if (flags & 0x02) {
        WeightsConfig* w = WeightsConfig_WEIGHTS;
        if (w == NULL) goto null_throw;

        float score = w->buffScoringWeight;  // +0x180

        // Get buff type via vtable +0x478 — NQ: likely GetBuffType() → int
        int buffType = actor->vtable[0x478/8](actor, actor->vtableArg_0x480);

        // Type-2 buff with no heal: heavily penalised (suppression-of-redundancy guard)
        if (buffType == 2 && !(flags & 0x01)) {
            score *= 0.1;
        }

        // Bonus: not incapacitated
        if (!actor->isIncapacitated) {  // Actor +0x15C
            score *= 1.5;
        }

        total += score;
    }

    // ══════════════════════════════════════════════════
    // BRANCH 3 — SUPPRESS / DEBUFF RESISTANCE (flags bit 15 = 0x8000)
    // ══════════════════════════════════════════════════
    if (flags & 0x8000) {
        WeightsConfig* w = WeightsConfig_WEIGHTS;
        if (w == NULL) goto null_throw;

        float baseWeight = w->suppressScoringWeight;  // +0x184

        // Resistance fraction [0,1] — NQ-25: GetResistanceFraction or GetBuffLevel
        float resistFrac = (float)FUN_1805DEE10(actor, 0);
        float score = (1.0f - resistFrac) * baseWeight;

        // Double score if buff slot count == 1 (target has exactly one active buff slot)
        int slotVal = actor->vtable[0x468/8](actor, actor->vtableArg_0x470);
        if (score > 0.0f && slotVal == 1) {
            score *= 2.0f;
        }

        // Immobility penalty (same as heal)
        EntityInfo* actorEntity = actor->vtable[0x3D8/8](actor, actor->vtableArg_0x3E0);
        if (actorEntity == NULL) goto null_throw;
        if ((actorEntity->flags & 1) && !(flags & 0x02)) {
            score *= 0.5f;
        }

        // Type-2 / no-heal light penalty
        int buffType = actor->vtable[0x478/8](actor, actor->vtableArg_0x480);
        if (buffType == 2 && !(flags & 0x01)) {
            score *= 0.9f;
        }

        // Not incapacitated bonus
        if (!actor->isIncapacitated) {
            score *= 1.5f;
        }

        total += score;
    }

    // ══════════════════════════════════════════════════
    // BRANCH 4 — AOE HEAL (flags bit 17 = 0x20000)
    // ══════════════════════════════════════════════════
    if (flags & 0x20000) {
        float aoeTotal = 0.0f;

        // Navigate: self->agentContext->entityInfo->tileList
        // self +0x10 = agentContext; agentContext +0x10 = entityInfo; entityInfo +0x48 = tileList
        if (self->agentContext == NULL) goto null_throw;
        EntityInfo* selfEntity = self->agentContext->entityInfo;
        if (selfEntity == NULL) goto null_throw;
        List<Tile>* tileList = selfEntity->tileList;  // EntityInfo +0x48
        if (tileList == NULL) goto null_throw;

        // Iterate team tiles (GetEnumerator + MoveNext pattern)
        foreach (Tile* tile in tileList) {
            if (tile == NULL) NullReferenceException();

            // Check if tile has a valid ally — FUN_180722ED0
            bool hasAlly = FUN_180722ED0(tile, 0);
            if (hasAlly) {
                if (tile == NULL) NullReferenceException();
                // Navigate: tile->field_0x20->field_0x58 — ally's skill reference
                longlong skillRef = tile->field_0x20->field_0x58;
                if (skillRef == NULL) NullReferenceException();

                // Per-member heal scorer (NQ-26)
                float healVal;
                bool ok = FUN_181430AC0(skillRef, actor, &healVal, DAT_1839441D8);
                if (ok) aoeTotal += healVal;
            }
        }
        // Enumerator dispose — omitted

        WeightsConfig* w = WeightsConfig_WEIGHTS;
        if (w == NULL) goto null_throw;

        // Scale total AoE heal by weight (400 decimal = 0x190)
        total += w->aoeHealScoringWeight * aoeTotal;  // +0x190
    }

    // ══════════════════════════════════════════════════
    // BRANCH 5 — AOE BUFF (flags bit 18 = 0x40000)
    // ══════════════════════════════════════════════════
    if (flags & 0x40000) {
        float aoeTotal = 0.0f;

        EntityInfo* actorEntity = actor->vtable[0x3D8/8](actor, actor->vtableArg_0x3E0);
        if (actorEntity == NULL) goto null_throw;
        bool isImmobile    = (actorEntity->flags & 1) != 0;
        bool hasStatusBuff = (flags & 0x02) != 0;
        int buffType       = actor->vtable[0x478/8](actor, actor->vtableArg_0x480);
        bool hasHeal       = (flags & 0x01) != 0;

        // Guard: skip if immobile (without status buff) or type-2 without heal
        if ((!isImmobile || hasStatusBuff) && !(buffType == 2 && !hasHeal)) {
            // Navigate same tileList as Branch 4
            List<Tile>* tileList = self->agentContext->entityInfo->tileList;
            if (tileList == NULL) goto null_throw;

            foreach (Tile* tile in tileList) {
                bool hasAlly = FUN_180722ED0(tile, 0);
                if (hasAlly) {
                    // Navigate: tile->field_0x20->tileDict (+0x68)
                    // List at tileDict->field_0x20 (first element) and tileDict->field_0x28 (second)
                    longlong tileDict = tile->field_0x20->field_0x68;
                    if (tileDict == NULL) NullReferenceException();

                    // Primary target score
                    float val1;
                    bool ok1 = FUN_181430AC0(
                        tileDict->field_0x20, actor, &val1, DAT_1839441D8, aoeTotal);
                    if (ok1) {
                        WeightsConfig* w = WeightsConfig_WEIGHTS;
                        if (w == NULL) NullReferenceException();
                        aoeTotal += w->aoeBuffScoringWeight * val1;  // +0x18C
                    }

                    // Secondary target score
                    float val2;
                    bool ok2 = FUN_181430AC0(
                        tileDict->field_0x28, actor, &val2, DAT_1839441D8, aoeTotal);
                    if (ok2) {
                        WeightsConfig* w = WeightsConfig_WEIGHTS;
                        if (w == NULL) NullReferenceException();
                        aoeTotal += val2 * w->aoeBuffScoringWeight;
                    }
                }
            }
            // Enumerator dispose — omitted
        }

        // Bonus: not incapacitated
        if (!actor->isIncapacitated) {
            aoeTotal *= 1.2f;
        }

        total += aoeTotal;
    }

    // ══════════════════════════════════════════════════
    // BRANCH 6 — SETUP / STANCE ASSIST (flags bit 16 = 0x10000)
    // ══════════════════════════════════════════════════
    if (flags & 0x10000) {
        WeightsConfig* w = WeightsConfig_WEIGHTS;
        if (w == NULL) goto null_throw;

        float score = w->setupAssistScoringWeight;  // +0x188

        EntityInfo* actorEntity = actor->vtable[0x3D8/8](actor, actor->vtableArg_0x3E0);
        if (actorEntity == NULL) goto null_throw;
        bool isImmobile    = (actorEntity->flags & 1) != 0;
        bool hasStatusBuff = (flags & 0x02) != 0;
        int buffType       = actor->vtable[0x478/8](actor, actor->vtableArg_0x480);
        bool hasHeal       = (flags & 0x01) != 0;

        // Determine if score should be zero (target not eligible for setup assist)
        if ((!isImmobile || hasStatusBuff) && !(buffType == 2 && !hasHeal)) {
            // Check if target is ready to fire — FUN_180628210 (NQ-28)
            bool isReadyToFire = FUN_180628210(actorEntity, 0);
            if (!isReadyToFire && buffType != 2) {
                score = 0.0f;  // not ready and not type-2: no value in setup assist
            }
        }
        else {
            score = 0.0f;  // immobile (without status) or type-2 without heal: zero
        }

        // Penalties
        if ((int)actor->field_0xD0 == 1) {  // Actor +0xD0, inferred: stance/setup state (NQ-27)
            score *= 0.75f;
        }
        if (actor->isWeaponSetUp) {  // Actor +0x167 confirmed
            score *= 0.75f;
        }

        // Bonus: not incapacitated
        if (!actor->isIncapacitated) {  // Actor +0x15C
            score *= 1.1f;
        }

        // Proximity list: navigate self->agentContext->entityInfo->field_0x58->field_0x10
        // (list of ProximityEntry-like objects, each with a tile ref and flags)
        List* proximityList = self->agentContext->entityInfo->field_0x58->field_0x10;
        if (proximityList == NULL) goto null_throw;

        foreach (ProximityEntry* entry in proximityList) {
            // Bit 2 set: penalise if actor IS within this entry's range
            if (entry->flags & 0x02) {
                bool inRange = FUN_1805406A0(entry->tileRef, actor->vtable[0x388/8](...), 0);
                if (inRange) score *= 0.9f;
            }
            // Bit 1 set: bonus if actor is NOT within this entry's range
            if (entry->flags & 0x01) {
                bool inRange = FUN_1805406A0(entry->tileRef, actor->vtable[0x388/8](...), 0);
                if (!inRange) score *= 1.2f;
            }
        }
        // Enumerator dispose — omitted

        // Stack count scaling via powf(1.25) — NQ-29
        int stackCount = FUN_180687590(targetRef, 0);
        if (stackCount == 0) {
            // If target's EntityInfo reports no count limit (-2 = unlimited, skip)
            EntityInfo* targetEntity = actor->vtable[0x398/8](actor, actor->vtableArg_0x3A0);
            if (targetEntity == NULL) goto null_throw;
            if (targetEntity->field_0xC8 != -2) {
                if (actor->buffDataBlock->field_0x38 > 0) {  // +0xC8 sub-object, +0x38 = count
                    float pow125 = powf(1.25f);  // FUN_1804BAD80(0x3fa00000) = powf(1.25)
                    score *= pow125;
                }
            }
        }

        total += score;
    }

    // ══════════════════════════════════════════════════
    // FINAL SCALING
    // ══════════════════════════════════════════════════
    if (actor->buffDataBlock != NULL) {  // plVar10[0x19]
        float contextScale = actor->buffDataBlock->field_0x34;  // per-target scale factor
        WeightsConfig* w   = WeightsConfig_WEIGHTS;
        if (w == NULL) goto null_throw;

        return contextScale * total * w->buffGlobalScoringScale;  // +0x174
    }

null_throw:
    NullReferenceException();  // does not return
}
```

### GetTargetValue (Buff) — design notes

**Six branches are fully independent and additive.** There is no cap or normalization between branches. A skill with all six bits set produces a score that is the sum of all six contributions before the final `contextScale * total * globalScale` multiplication. This means WeightsConfig weights for individual branches are tuned relative to each other, not normalized.

**The `isIncapacitated` bonus is always a multiplier > 1.0.** Every branch that checks `actor->isIncapacitated (+0x15C)` applies a bonus when the actor is *not* incapacitated. Downed units consistently receive lower buff priority. The bonus magnitude varies by branch (×1.1 heal, ×1.5 buff/suppress, ×1.2 AoE buff, ×1.1 setup).

**`buffType == 2` is a suppression-of-redundancy guard.** The same enum value appears across multiple branches with different penalties: ×0.1 in the status buff branch, ×0.9 in the suppress branch. This prevents aggressively scoring a unit that is already in a particular state. The exact semantics of `buffType == 2` require a class dump to confirm (vtable +0x478 return).

**AoE branches iterate the caster's team tile list, not a radius.** The AoE score measures "benefit to my team" rather than "targets in area." The target `actor` is passed to the per-member scorer `FUN_181430AC0`, suggesting it is used as a reference origin for distance or applicability filtering, not as the AoE center.

**The AoE buff branch calls `FUN_181430AC0` twice per tile** — once for a primary target (at `tileDict->field_0x20`) and once for a secondary target (at `tileDict->field_0x28`). Both use the same `aoeBuffScoringWeight`. The `accumulator` (fifth argument, `fVar13`) is passed in and updated on each successful call, suggesting the scorer may use the running total for diminishing returns or deduplication.

**`powf(1.25)` in the setup branch encodes a stack bonus.** When the target's buff stack count is above zero and not unlimited, the setup assist score is multiplied by 1.25. This is the only use of a power function in any of the scoring branches; it implies the stack bonus was originally intended to be variable (e.g., `powf(1.25, stackCount)`) but the exponent is hardcoded to 1 here. The raw value `0x3fa00000` as IEEE 754 = 1.25.

**The `contextScale` at `actor->buffDataBlock->field_0x34`** is a per-target, pre-computed float stored in the buff data sub-object. It likely encodes how much the target currently needs or can benefit from buffs (perhaps HP ratio, buff availability, or a designer-authored priority). Its provenance is not analysed in this stage.
