# RECONSTRUCTIONS.md — `Behavior` & `SkillBehavior` Base Classes

**Game:** Menace
**Platform:** Windows x64, Unity IL2CPP
**Image base:** `0x180000000`
**Format:** Raw Ghidra output followed by fully annotated C-style reconstruction. Functions in leaf-first order.

---

## Quick-Reference Offset Tables

### `Behavior` (`Menace.Tactical.AI`, TypeDefIndex 3623)
| Offset | Type | Name |
|--------|------|------|
| `+0x10` | `Agent*` | `m_Agent` |
| `+0x18` | `int` | `m_Score` |
| `+0x1C` | `bool` | `m_IsFirstEvaluated` |
| `+0x1D` | `bool` | `m_IsFirstExecuted` |
| `+0x1E` | `bool` | `m_IsUsedForDeploymentPhase` |

### `SkillBehavior` (`Menace.Tactical.AI`, TypeDefIndex 3627)
| Offset | Type | Name |
|--------|------|------|
| `+0x20` | `Skill*` | `m_Skill` |
| `+0x28` | `int` | `m_SkillIDHash` |
| `+0x30` | `Skill*` | `m_DeployedStanceSkill` |
| `+0x38` | `Skill*` | `m_RotationSkill` |
| `+0x40` | `Skill*` | `m_SetupWeaponSkill` |
| `+0x4C` | `bool` | `m_IsRotationTowardsTargetRequired` |
| `+0x4D` | `bool` | `m_DeployBeforeExecuting` |
| `+0x4E` | `bool` | `m_SetupBeforeExecuting` |
| `+0x4F` | `bool` | `m_RotateBeforeExecuting` |
| `+0x50` | `bool` | `m_DontActuallyExecute` |
| `+0x51` | `bool` | `m_IsExecuted` |
| `+0x54` | `float` | `m_WaitUntil` |
| `+0x58` | `Tile*` | `m_TargetTile` |

### `DamageData` (heap-allocated object)
| Offset | Type | Name |
|--------|------|------|
| `+0x10` | `float` | `expectedRawDamage` |
| `+0x14` | `float` | `expectedEffectiveDamage` |
| `+0x18` | `float` | `expectedKills` |
| `+0x20` | `float` | `coverPenetrationChance` |
| `+0x24` | `bool` | `canKillInOneShot` |
| `+0x25` | `bool` | `canKillWithFullMag` |
| `+0x28` | `Skill*` | `shotData` |

---

## 1. `Behavior.GetUtilityThreshold` — `0x180739050`

### Raw Ghidra output
```c
float FUN_180739050(longlong param_1)
{
  longlong *plVar1;
  longlong lVar2;
  float fVar3;
  float fVar4;
  
  if (DAT_183b931c2 == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    DAT_183b931c2 = '\x01';
  }
  if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
    il2cpp_runtime_class_init();
  }
  lVar2 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
  if (lVar2 != 0) {
    fVar3 = *(float *)(lVar2 + 0x13c);
    if ((*(longlong *)(param_1 + 0x10) != 0) &&
       (plVar1 = *(longlong **)(*(longlong *)(param_1 + 0x10) + 0x18), plVar1 != (longlong *)0x0)) {
      lVar2 = (**(code **)(*plVar1 + 0x398))(plVar1,*(undefined8 *)(*plVar1 + 0x3a0));
      if ((lVar2 != 0) && (*(longlong *)(lVar2 + 0x310) != 0)) {
        fVar4 = fVar3 * *(float *)(*(longlong *)(lVar2 + 0x310) + 0x14);
        if (fVar3 <= fVar4) {
          fVar3 = fVar4;
        }
        if ((*(longlong *)(param_1 + 0x10) != 0) &&
           (plVar1 = *(longlong **)(*(longlong *)(param_1 + 0x10) + 0x18), plVar1 != (longlong *)0x0
           )) {
          lVar2 = (**(code **)(*plVar1 + 0x398))(plVar1,*(undefined8 *)(*plVar1 + 0x3a0));
          if ((lVar2 != 0) && (*(longlong *)(lVar2 + 0x310) != 0)) {
            return fVar3 * *(float *)(*(longlong *)(lVar2 + 0x310) + 0x18);
          }
        }
      }
    }
  }
  // WARNING: Subroutine does not return
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
float Behavior::GetUtilityThreshold()
{
    // IL2CPP lazy init — omitted
    // DAT_18394c3d0 = WeightsConfig class metadata (identity: NQ-5, pending)

    WeightsConfig* weights = WeightsConfig.Instance; // *(DAT_18394c3d0 + 0xb8) + 8
    if (weights == null) throw NullReferenceException();

    float base = weights->utilityThreshold; // weights + 0x13C — confirmed read

    Actor* actor = m_Agent->actor; // m_Agent (+0x10) -> actor (+0x18)
    if (actor == null) throw NullReferenceException();

    StrategyData* strategy = actor->GetStrategy(); // vtable +0x398
    if (strategy == null) throw NullReferenceException();

    StrategyModifiers* mods = strategy->modifiers; // strategy + 0x310
    if (mods == null) throw NullReferenceException();

    // multA: can only raise the threshold (max with base)
    float scaled = base * mods->thresholdMultA; // mods + 0x14
    float raised = (base <= scaled) ? scaled : base; // max(base, scaled)

    // multB: bidirectional — aggressive strategies lower, defensive raise
    return raised * mods->thresholdMultB; // mods + 0x18
}
```

### GetUtilityThreshold — design notes

`thresholdMultA` applies a one-directional raise via `max(base, base * multA)` — the strategy can never lower the threshold below the global base via this multiplier. `thresholdMultB` is unconditional and can move the result in either direction. The implication is that the two multipliers serve different purposes: `multA` reflects a strategic conservatism floor, and `multB` reflects a moment-to-moment strategic posture (aggressive vs. defensive).

---

## 2. `Behavior.Collect` — `0x180738D10`

### Raw Ghidra output
```c
ulonglong FUN_180738d10(longlong *param_1,undefined8 param_2)
{
  ulonglong uVar1;
  
  (**(code **)(*param_1 + 0x208))(param_1,*(undefined8 *)(*param_1 + 0x210));
  if (*(char *)((longlong)param_1 + 0x1e) == '\0') {
    if (DAT_183b9233f == '\0') {
      FUN_180427b00(&DAT_183981f50);
      DAT_183b9233f = '\x01';
    }
    uVar1 = **(ulonglong **)(DAT_183981f50 + 0xb8);
    if (uVar1 == 0) goto LAB_180738daf;
    if (*(int *)(uVar1 + 0x60) == 0) {
      return uVar1 & 0xffffffffffffff00;
    }
  }
  if (param_1[2] != 0) {
    uVar1 = (**(code **)(*param_1 + 0x1b8))
                      (param_1,param_2,*(undefined8 *)(param_1[2] + 0x60),
                       *(undefined8 *)(*param_1 + 0x1c0));
    return uVar1;
  }
LAB_180738daf:
  // WARNING: Subroutine does not return
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
bool Behavior::Collect(Actor* actor)
{
    // Pre-collect hook (same hook as Evaluate — fires every call)
    this->OnBeforeProcessing(); // vtable +0x208

    // Deployment phase gate
    if (!m_IsUsedForDeploymentPhase) { // +0x1E
        // IL2CPP lazy init — omitted
        // DAT_183981f50 = RoundManager class metadata
        RoundManager* rm = RoundManager.SingletonInstance; // *(DAT_183981f50 + 0xb8) first field
        if (rm == null) throw NullReferenceException();
        if (rm->deploymentRoundCount == 0) { // rm + 0x60 — int round count
            return false; // not a deployment behaviour; skip during deployment phase
        }
    }

    // Dispatch to OnCollect with the agent's shared tile dictionary
    if (m_Agent == null) throw NullReferenceException(); // param_1[2] = m_Agent at +0x10
    // Agent's tile dictionary is at m_Agent + 0x60
    return this->OnCollect(actor, m_Agent->tileDict); // vtable +0x1B8 (Slot 8)
}
```

---

## 3. `Behavior.Evaluate(Actor)` — `0x180738E60`

### Raw Ghidra output
```c
void FUN_180738e60(longlong *param_1,undefined8 param_2)
{
  int iVar1;
  int iVar2;
  
  (**(code **)(*param_1 + 0x208))(param_1,*(undefined8 *)(*param_1 + 0x210));
  if (*(char *)((longlong)param_1 + 0x1e) == '\0') {
    if (DAT_183b9233f == '\0') {
      FUN_180427b00(&DAT_183981f50);
      DAT_183b9233f = '\x01';
    }
    if (**(longlong **)(DAT_183981f50 + 0xb8) == 0) {
      // WARNING: Subroutine does not return
      FUN_180427d90();
    }
    if (*(int *)(**(longlong **)(DAT_183981f50 + 0xb8) + 0x60) == 0) {
      return;
    }
  }
  iVar1 = (**(code **)(*param_1 + 0x1d8))(param_1,param_2,*(undefined8 *)(*param_1 + 0x1e0));
  iVar2 = 0x53e2;
  if (iVar1 < 0x53e2) {
    iVar2 = iVar1;
  }
  iVar1 = 0;
  if (-1 < iVar2) {
    iVar1 = iVar2;
  }
  *(int *)(param_1 + 3) = iVar1;
  iVar2 = (**(code **)(*param_1 + 0x178))(param_1,*(undefined8 *)(*param_1 + 0x180));
  if (((iVar2 != 99999) && (0 < (int)param_1[3])) && (*(uint *)(param_1 + 3) < 5)) {
    *(undefined4 *)(param_1 + 3) = 5;
  }
  *(undefined2 *)((longlong)param_1 + 0x1c) = 1;
  return;
}
```

### Annotated reconstruction
```c
void Behavior::Evaluate(Actor* actor)
{
    // Pre-evaluate hook (fires every evaluate call, not once per turn)
    this->OnBeforeProcessing(); // vtable +0x208

    // Deployment phase gate
    if (!m_IsUsedForDeploymentPhase) { // +0x1E
        // IL2CPP lazy init — omitted
        RoundManager* rm = RoundManager.SingletonInstance;
        if (rm == null) throw NullReferenceException();
        if (rm->deploymentRoundCount == 0) // +0x60
            return; // non-deployment behaviour; skip during deployment
    }

    // Call abstract OnEvaluate — subclass computes score
    int raw = this->OnEvaluate(actor); // vtable +0x1D8 (Slot 10)

    // Clamp to [0, 21474]
    int clamped = (raw < 21474) ? raw : 21474; // 0x53E2
    clamped = (clamped < 0) ? 0 : clamped;
    m_Score = clamped; // +0x18 (written as param_1[3] — int at offset 0x18 of longlong array)

    // Minimum floor: if order is not sentinel AND score is positive but below 5, raise to 5
    int order = this->GetOrder(); // vtable +0x178 (Slot 6)
    if (order != 99999 && m_Score > 0 && (uint)m_Score < 5) {
        m_Score = 5;
    }

    // Mark as evaluated (2-byte write sets both m_IsFirstEvaluated +0x1C and m_IsFirstExecuted +0x1D)
    m_IsFirstEvaluated = true;
    m_IsFirstExecuted  = true; // both written in single *(undefined2*)(+0x1C) = 1
}
```

### Evaluate — design notes

The two-byte write at `+0x1C` sets both `m_IsFirstEvaluated` and `m_IsFirstExecuted` to `1` atomically. This is a Ghidra artefact of the compiler emitting a single 16-bit store for two adjacent booleans. Both flags are reset by `Execute`. Their naming implies "first time" semantics, but their actual behaviour is "toggled on every evaluate / off every execute." Subclasses using these flags to detect "am I being called for the first time ever?" would be incorrect — they should instead use `OnReset` to initialise first-run state.

---

## 4. `Behavior.Execute` — `0x180738F40`

### Raw Ghidra output
```c
void FUN_180738f40(longlong *param_1,undefined8 param_2)
{
  (**(code **)(*param_1 + 0x1e8))(param_1,param_2,*(undefined8 *)(*param_1 + 0x1f0));
  *(undefined1 *)((longlong)param_1 + 0x1c) = 0;
  return;
}
```

### Annotated reconstruction
```c
bool Behavior::Execute(Actor* actor)
{
    // Dispatch to abstract OnExecute
    bool result = this->OnExecute(actor); // vtable +0x1E8 (Slot 11)

    // Clear both flags (single-byte write at +0x1C; +0x1D is not explicitly cleared here —
    // only one byte is written, unlike Evaluate which writes two. m_IsFirstExecuted relies
    // on OnExecute setting it via m_IsFirstEvaluated write path. Confirm on further analysis.)
    m_IsFirstEvaluated = false; // *(undefined1*)(+0x1C) = 0

    return result;
}
```

### Execute — design notes

Unlike `Evaluate` which writes two bytes at `+0x1C`, `Execute` writes only one byte (`undefined1`). This clears `m_IsFirstEvaluated` at `+0x1C` but leaves `m_IsFirstExecuted` at `+0x1D` potentially unchanged if the compiler chose a byte write here. This asymmetry may be intentional (only the evaluated flag needs clearing to signal "not freshly evaluated") or a compiler artefact. Flag semantics should be validated against a concrete subclass that reads `m_IsFirstExecuted`.

---

## 5. `SkillBehavior.ConsiderSkillSpecifics` — `0x18073BDD0`

### Raw Ghidra output
```c
float FUN_18073bdd0(longlong param_1)
{
  longlong lVar1;
  longlong *plVar2;
  char cVar3;
  int iVar4;
  int iVar5;
  undefined8 *puVar6;
  ushort uVar7;
  float fVar9;
  longlong local_res8;
  longlong *local_res18;
  ulonglong uVar8;
  
  if (DAT_183b931cf == '\0') {
    FUN_180427b00(&DAT_1839a64b0);
    FUN_180427b00(&DAT_1839a6620);
    FUN_180427b00(&DAT_183965650);
    FUN_180427b00(&DAT_183965708);
    DAT_183b931cf = '\x01';
  }
  uVar8 = 0;
  fVar9 = 1.0;
  local_res18 = (longlong *)0x0;
  local_res8 = 0;
  if (*(longlong *)(param_1 + 0x20) != 0) {
    cVar3 = FUN_180ba1030(*(longlong *)(param_1 + 0x20),&local_res18,DAT_183965650);
    plVar2 = local_res18;
    if (cVar3 != '\0') {
      if (local_res18 == (longlong *)0x0) goto LAB_18073bf8d;
      lVar1 = *local_res18;
      if (*(ushort *)(lVar1 + 0x12e) != 0) {
        do {
          if (*(longlong *)(*(longlong *)(lVar1 + 0xb0) + uVar8 * 0x10) == DAT_1839a64b0) {
            puVar6 = (undefined8 *)
                     ((longlong)*(int *)(*(longlong *)(lVar1 + 0xb0) + 8 + uVar8 * 0x10) * 0x10 +
                      0x138 + lVar1);
            goto LAB_18073beb3;
          }
          uVar7 = (short)uVar8 + 1;
          uVar8 = (ulonglong)uVar7;
        } while (uVar7 < *(ushort *)(lVar1 + 0x12e));
      }
      puVar6 = (undefined8 *)FUN_180424ea0(local_res18,DAT_1839a64b0,0);
LAB_18073beb3:
      fVar9 = (float)(*(code *)*puVar6)(plVar2,puVar6[1]);
      if (1.0 < fVar9) {
        fVar9 = 1.0;
      }
      fVar9 = 1.0 - fVar9;
    }
    if (*(longlong *)(param_1 + 0x20) != 0) {
      cVar3 = FUN_180ba1030(*(longlong *)(param_1 + 0x20),&local_res8,DAT_183965708);
      if (cVar3 == '\0') {
        return fVar9;
      }
      if ((local_res8 != 0) && (iVar4 = FUN_180002310(1,DAT_1839a6620), local_res8 != 0)) {
        iVar5 = FUN_180002310(2,DAT_1839a6620);
        return fVar9 * (((float)iVar4 / (float)iVar5) * 0.25 + 0.75);
      }
    }
  }
LAB_18073bf8d:
  // WARNING: Subroutine does not return
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
float SkillBehavior::ConsiderSkillSpecifics()
{
    // IL2CPP lazy init — omitted
    // DAT_1839a64b0 = TAG_ARMOR_MATCH class metadata
    // DAT_1839a6620 = AMMO_TABLE lookup table
    // DAT_183965650 = TAG_ARMOR_MATCH tag type identifier
    // DAT_183965708 = TAG_AMMO_COUNT tag type identifier

    float result = 1.0f; // default: no penalty

    if (m_Skill == null) throw NullReferenceException(); // +0x20

    // --- Tag 1: Armour match penalty ---
    // Query m_Skill for TAG_ARMOR_MATCH tag
    SkillTagData* armorTag = null;
    bool hasArmorTag = m_Skill->TryGetTag(TAG_ARMOR_MATCH, out armorTag); // FUN_180ba1030

    if (hasArmorTag) {
        if (armorTag == null) throw NullReferenceException();

        // Search tag array at SkillDef + 0xB0 for the armor match tag type
        // (loop over SkillDef.tagArray entries, count at SkillDef + 0x12E)
        // Falls back to FUN_180424ea0 (interface dispatch) if not found by direct scan
        float tagValue = armorTag->GetValue(); // dynamic dispatch on tag object
        tagValue = min(tagValue, 1.0f);
        result = 1.0f - tagValue;
        // tagValue = 1.0 → result = 0.0 (perfect armour match, full penalty — do not use)
        // tagValue = 0.0 → result = 1.0 (no match relevance, no penalty)
    }

    // --- Tag 2: Ammo count penalty ---
    SkillTagData* ammoTag = null;
    bool hasAmmoTag = m_Skill->TryGetTag(TAG_AMMO_COUNT, out ammoTag); // FUN_180ba1030
    if (!hasAmmoTag) return result; // no ammo tag — return with just armour penalty

    if (ammoTag != null) {
        int currentAmmo = AMMO_TABLE.Get(1); // FUN_180002310(1, AMMO_TABLE)
        int maxAmmo     = AMMO_TABLE.Get(2); // FUN_180002310(2, AMMO_TABLE)
        if (currentAmmo != 0 && maxAmmo != 0) {
            float ammoFraction = (float)currentAmmo / (float)maxAmmo;
            result *= ammoFraction * 0.25f + 0.75f;
            // Full ammo (1.0): factor = 1.0  → no penalty
            // Half ammo (0.5): factor = 0.875 → 12.5% penalty
            // Near empty (→0): factor → 0.75 → 25% penalty (maximum)
        }
    }

    return result; // combined multiplier in (0.0, 1.0]
}
```

---

## 6. `SkillBehavior.HandleDeployAndSetup` — `0x18073DF70`

### Raw Ghidra output
```c
undefined8 FUN_18073df70(longlong param_1,longlong *param_2)
{
  char cVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  int iVar5;
  longlong lVar6;
  
  if ((*(longlong *)(param_1 + 0x20) == 0) ||
     (lVar6 = *(longlong *)(*(longlong *)(param_1 + 0x20) + 0x10), lVar6 == 0)) goto LAB_18073e2f3;
  if (*(char *)(lVar6 + 0x112) == '\0') {
LAB_18073dfe8:
    if ((*(longlong *)(param_1 + 0x20) == 0) ||
       (lVar6 = *(longlong *)(*(longlong *)(param_1 + 0x20) + 0x10), lVar6 == 0))
    goto LAB_18073e2f3;
    if (*(char *)(lVar6 + 0x113) != '\0') {
      if (param_2 == (longlong *)0x0) goto LAB_18073e2f3;
      if ((*(char *)((longlong)param_2 + 0x167) == '\0') && (*(longlong *)(param_1 + 0x40) != 0)) {
        lVar6 = *(longlong *)(*(longlong *)(param_1 + 0x40) + 0x10);
        if (lVar6 == 0) goto LAB_18073e2f3;
        if (*(char *)(lVar6 + 0x112) != '\0') goto LAB_18073e04e;
      }
    }
  }
  else {
    if ((param_2 == (longlong *)0x0) ||
       (lVar6 = (**(code **)(*param_2 + 0x3d8))(param_2,*(undefined8 *)(*param_2 + 0x3e0)),
       lVar6 == 0)) goto LAB_18073e2f3;
    if ((*(uint *)(lVar6 + 0xec) >> 9 & 1) != 0) goto LAB_18073dfe8;
LAB_18073e04e:
    if (((int)param_2[0x1a] != 1) && (cVar1 = FUN_180616ae0(param_2,0), cVar1 == '\0')) {
      if (*(longlong *)(param_1 + 0x30) == 0) {
        return 0;
      }
      cVar1 = FUN_1806e3fa0(*(undefined8 *)(param_1 + 0x30),0);
      if (cVar1 == '\0') {
        return 0;
      }
      if (*(longlong *)(param_1 + 0x30) == 0) goto LAB_18073e2f3;
      iVar2 = FUN_1806ddec0(*(longlong *)(param_1 + 0x30),0);
      iVar3 = (**(code **)(*param_2 + 0x458))(param_2,*(undefined8 *)(*param_2 + 0x460));
      if (iVar3 < iVar2) {
        return 0;
      }
      *(undefined1 *)(param_1 + 0x4d) = 1;
      if (*(longlong *)(param_1 + 0x20) == 0) goto LAB_18073e2f3;
      iVar2 = FUN_1806ddec0(*(longlong *)(param_1 + 0x20),0);
      if (*(longlong *)(param_1 + 0x30) == 0) goto LAB_18073e2f3;
      iVar3 = FUN_1806ddec0(*(longlong *)(param_1 + 0x30),0);
      iVar4 = (**(code **)(*param_2 + 0x458))(param_2,*(undefined8 *)(*param_2 + 0x460));
      if (iVar4 < iVar3 + iVar2) {
        *(undefined1 *)(param_1 + 0x50) = 1;
      }
    }
  }
  if ((*(longlong *)(param_1 + 0x20) == 0) ||
     (lVar6 = *(longlong *)(*(longlong *)(param_1 + 0x20) + 0x10), lVar6 == 0)) goto LAB_18073e2f3;
  if (*(char *)(lVar6 + 0x113) == '\0') {
    return 1;
  }
  if (param_2 == (longlong *)0x0) goto LAB_18073e2f3;
  if (*(char *)((longlong)param_2 + 0x167) != '\0') {
    return 1;
  }
  if (*(longlong *)(param_1 + 0x40) == 0) {
    return 0;
  }
  cVar1 = FUN_1806e3a00(*(undefined8 *)(param_1 + 0x40),0);
  if (cVar1 != '\0') {
    return 0;
  }
  if (*(longlong *)(param_1 + 0x40) == 0) goto LAB_18073e2f3;
  cVar1 = FUN_1806e2e70(*(longlong *)(param_1 + 0x40),0);
  if (cVar1 == '\0') {
    return 0;
  }
  if (*(char *)(param_1 + 0x4d) == '\0') {
LAB_18073e1e3:
    if (*(longlong *)(param_1 + 0x40) == 0) goto LAB_18073e2f3;
    iVar2 = FUN_1806ddec0(*(longlong *)(param_1 + 0x40),0);
    iVar3 = (**(code **)(*param_2 + 0x458))(param_2,*(undefined8 *)(*param_2 + 0x460));
    if (iVar3 < iVar2) {
      return 0;
    }
  }
  else {
    if (*(longlong *)(param_1 + 0x30) == 0) goto LAB_18073e2f3;
    iVar2 = FUN_1806ddec0(*(longlong *)(param_1 + 0x30),0);
    if (*(longlong *)(param_1 + 0x40) == 0) goto LAB_18073e2f3;
    iVar3 = FUN_1806ddec0(*(longlong *)(param_1 + 0x40),0);
    iVar4 = (**(code **)(*param_2 + 0x458))(param_2,*(undefined8 *)(*param_2 + 0x460));
    if (iVar4 < iVar3 + iVar2) {
      return 0;
    }
    if (*(char *)(param_1 + 0x4d) == '\0') goto LAB_18073e1e3;
  }
  *(undefined1 *)(param_1 + 0x4e) = 1;
  if (*(char *)(param_1 + 0x4d) != '\0') {
    if (*(longlong *)(param_1 + 0x20) == 0) goto LAB_18073e2f3;
    iVar2 = FUN_1806ddec0(*(longlong *)(param_1 + 0x20),0);
    if (*(longlong *)(param_1 + 0x30) == 0) goto LAB_18073e2f3;
    iVar3 = FUN_1806ddec0(*(longlong *)(param_1 + 0x30),0);
    if (*(longlong *)(param_1 + 0x40) == 0) goto LAB_18073e2f3;
    iVar4 = FUN_1806ddec0(*(longlong *)(param_1 + 0x40),0);
    iVar5 = (**(code **)(*param_2 + 0x458))(param_2,*(undefined8 *)(*param_2 + 0x460));
    if (iVar5 < iVar4 + iVar3 + iVar2) goto LAB_18073e2ce;
    if (*(char *)(param_1 + 0x4d) != '\0') {
      return 1;
    }
  }
  if (*(longlong *)(param_1 + 0x20) != 0) {
    iVar2 = FUN_1806ddec0(*(longlong *)(param_1 + 0x20),0);
    if (*(longlong *)(param_1 + 0x40) != 0) {
      iVar3 = FUN_1806ddec0(*(longlong *)(param_1 + 0x40),0);
      iVar4 = (**(code **)(*param_2 + 0x458))(param_2,*(undefined8 *)(*param_2 + 0x460));
      if (iVar3 + iVar2 <= iVar4) {
        return 1;
      }
LAB_18073e2ce:
      *(undefined1 *)(param_1 + 0x50) = 1;
      return 1;
    }
  }
LAB_18073e2f3:
  // WARNING: Subroutine does not return
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
bool SkillBehavior::HandleDeployAndSetup(Actor* actor)
{
    // Read m_Skill's SkillData
    if (m_Skill == null) throw NullReferenceException(); // +0x20
    SkillData* skillData = m_Skill->skillData; // m_Skill + 0x10
    if (skillData == null) throw NullReferenceException();

    bool requiresDeploy = skillData->requiresDeployedStance; // SkillData + 0x112
    bool requiresSetup  = skillData->requiresWeaponSetup;    // SkillData + 0x113

    // === DEPLOY PATH ===
    if (requiresDeploy) {
        EntityInfo* info = actor->GetEntityInfo(); // vtable +0x3D8
        if (info == null) throw NullReferenceException();
        bool alreadyDeployed = (info->flags >> 9) & 1; // EntityInfo + 0xEC, bit 9

        if (!alreadyDeployed) {
            // actor->turnState at actor[0x1A] (as int); 1 = already acted
            bool hasActed  = ((int)actor[0x1A] == 1);
            bool canDeploy = FUN_180616ae0(actor); // CanDeploy() or IsDeployable()

            if (!hasActed && !canDeploy) {
                // Cannot deploy right now — check if we need to
                // (falls through to setup check or returns false below)
                goto CheckSetupPath;
            }

            if (m_DeployedStanceSkill == null) return false; // +0x30
            if (!FUN_1806e3fa0(m_DeployedStanceSkill)) return false; // CanUse()

            int deployCost = FUN_1806ddec0(m_DeployedStanceSkill); // GetAPCost()
            int currentAP  = actor->GetCurrentAP(); // vtable +0x458
            if (currentAP < deployCost) return false; // insufficient AP for deploy

            m_DeployBeforeExecuting = true; // +0x4D

            // Check if AP also covers the main skill
            int mainCost = FUN_1806ddec0(m_Skill); // GetAPCost()
            if (currentAP < mainCost + deployCost) {
                m_DontActuallyExecute = true; // +0x50 — deploy only this turn
            }
        }
        // else: already deployed — skip deploy, fall through to setup check
    }

CheckSetupPath:
    // Re-read skillData (compiler re-evaluates)
    if (m_Skill == null) throw NullReferenceException();
    skillData = m_Skill->skillData;
    if (skillData == null) throw NullReferenceException();

    if (!skillData->requiresWeaponSetup) { // +0x113
        return true; // no setup required — sequence is ready
    }

    if (actor == null) throw NullReferenceException();

    // Check if weapon is already set up
    if (actor->isWeaponSetUp) { // actor + 0x167
        return true; // already set up — skip
    }

    // Validate setup skill
    if (m_SetupWeaponSkill == null) return false; // +0x40
    if (FUN_1806e3a00(m_SetupWeaponSkill)) return false;   // IsUnavailable()
    if (!FUN_1806e2e70(m_SetupWeaponSkill)) return false;  // CanBeUsed()

    // AP check for setup
    if (!m_DeployBeforeExecuting) { // +0x4D
        // No deploy planned — check setup cost alone
        int setupCost = FUN_1806ddec0(m_SetupWeaponSkill);
        int currentAP = actor->GetCurrentAP();
        if (currentAP < setupCost) return false;
    } else {
        // Deploy already planned — check deploy + setup combined
        int deployCost = FUN_1806ddec0(m_DeployedStanceSkill);
        int setupCost  = FUN_1806ddec0(m_SetupWeaponSkill);
        int currentAP  = actor->GetCurrentAP();
        if (currentAP < deployCost + setupCost) return false;

        // Re-check: if m_DeployBeforeExecuting, fall through to AP check below
    }

    m_SetupBeforeExecuting = true; // +0x4E

    // Final combined AP check
    if (m_DeployBeforeExecuting) { // +0x4D
        int mainCost   = FUN_1806ddec0(m_Skill);
        int deployCost = FUN_1806ddec0(m_DeployedStanceSkill);
        int setupCost  = FUN_1806ddec0(m_SetupWeaponSkill);
        int currentAP  = actor->GetCurrentAP();

        if (currentAP >= mainCost + deployCost + setupCost) return true; // can do all three
        // else: fall through to set m_DontActuallyExecute
    } else {
        int mainCost  = FUN_1806ddec0(m_Skill);
        int setupCost = FUN_1806ddec0(m_SetupWeaponSkill);
        int currentAP = actor->GetCurrentAP();

        if (mainCost + setupCost <= currentAP) return true; // can do setup + fire
    }

LAB_18073e2ce:
    m_DontActuallyExecute = true; // +0x50 — plan sequence but don't fire this turn
    return true;
}
```

---

## 7. `SkillBehavior.OnExecute` — `0x18073E300`

### Raw Ghidra output
```c
ulonglong FUN_18073e300(longlong param_1,longlong *param_2)
{
  undefined8 uVar1;
  ulonglong uVar2;
  longlong lVar3;
  float fVar4;
  float extraout_XMM0_Da;
  float extraout_XMM0_Da_00;
  float extraout_XMM0_Da_01;
  float extraout_XMM0_Da_02;
  
  if (*(char *)(param_1 + 0x4f) != '\0') {
    if (*(longlong *)(param_1 + 0x38) != 0) {
      FUN_1806e80b0(*(longlong *)(param_1 + 0x38),*(undefined8 *)(param_1 + 0x58),0x10,0);
      if (param_2 != (longlong *)0x0) {
        uVar2 = FUN_1805e00a0(param_2,0);
        if ((char)uVar2 == '\0') {
          uVar2 = FUN_1829b1320(0);
          *(float *)(param_1 + 0x54) = extraout_XMM0_Da_02 + 2.0;
        }
        *(undefined1 *)(param_1 + 0x4f) = 0;
        return uVar2 & 0xffffffffffffff00;
      }
    }
    goto LAB_18073e51e;
  }
  if (*(char *)(param_1 + 0x4d) != '\0') {
    fVar4 = (float)FUN_1829b1320(0);
    if (*(float *)(param_1 + 0x54) <= fVar4) {
      lVar3 = *(longlong *)(param_1 + 0x30);
      if (param_2 == (longlong *)0x0) goto LAB_18073e51e;
      uVar1 = (**(code **)(*param_2 + 0x388))(param_2,*(undefined8 *)(*param_2 + 0x390));
      if (lVar3 == 0) goto LAB_18073e51e;
      FUN_1806e80b0(lVar3,uVar1,0x10,0);
      uVar2 = FUN_1805e00a0(param_2,0);
      if ((char)uVar2 == '\0') {
        lVar3 = (**(code **)(*param_2 + 0x398))(param_2,*(undefined8 *)(*param_2 + 0x3a0));
        if (lVar3 == 0) goto LAB_18073e51e;
        lVar3 = *(longlong *)(lVar3 + 0x1e8);
        uVar2 = FUN_1829b1320(0);
        if (lVar3 == 0) goto LAB_18073e51e;
        *(float *)(param_1 + 0x54) = extraout_XMM0_Da + *(float *)(lVar3 + 0x5c) + 0.1;
      }
      *(undefined1 *)(param_1 + 0x4d) = 0;
      goto LAB_18073e3d4;
    }
  }
  if (*(char *)(param_1 + 0x4e) != '\0') {
    fVar4 = (float)FUN_1829b1320(0);
    if (*(float *)(param_1 + 0x54) <= fVar4) {
      lVar3 = *(longlong *)(param_1 + 0x40);
      if (param_2 != (longlong *)0x0) {
        uVar1 = (**(code **)(*param_2 + 0x388))(param_2,*(undefined8 *)(*param_2 + 0x390));
        if (lVar3 != 0) {
          FUN_1806e80b0(lVar3,uVar1,0x10,0);
          uVar2 = FUN_1805e00a0(param_2,0);
          if ((char)uVar2 == '\0') {
            uVar2 = FUN_1829b1320(0);
            *(float *)(param_1 + 0x54) = extraout_XMM0_Da_00 + 3.0;
          }
          *(undefined1 *)(param_1 + 0x4e) = 0;
          return uVar2 & 0xffffffffffffff00;
        }
      }
      goto LAB_18073e51e;
    }
  }
  uVar2 = FUN_1829b1320(0);
  if (extraout_XMM0_Da_01 < *(float *)(param_1 + 0x54)) {
LAB_18073e3d4:
    return uVar2 & 0xffffffffffffff00;
  }
  if (param_2 != (longlong *)0x0) {
    lVar3 = (**(code **)(*param_2 + 1000))(param_2,*(undefined8 *)(*param_2 + 0x3f0));
    if (lVar3 != 0) {
      uVar2 = FUN_1806f3c30(lVar3,0);
      return uVar2 ^ 1;
    }
  }
LAB_18073e51e:
  // WARNING: Subroutine does not return
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
bool SkillBehavior::OnExecute(Actor* actor)
{
    // === STAGE 1: Rotation ===
    if (m_RotateBeforeExecuting) { // +0x4F
        if (m_RotationSkill != null) { // +0x38
            // Fire rotation skill targeting m_TargetTile
            FUN_1806e80b0(m_RotationSkill, m_TargetTile, /*flags=*/0x10, 0); // Skill.Use(tile, flags)
            if (actor != null) {
                bool isDone = FUN_1805e00a0(actor); // Actor.IsDoneActing()
                if (!isDone) {
                    // Set wait timer: 2 seconds for rotation to complete
                    m_WaitUntil = Time.time + 2.0f; // FUN_1829b1320(0) + 2.0; +0x54
                }
                m_RotateBeforeExecuting = false; // +0x4F — clear regardless
                return (bool)(isDone & 0xFF); // false while rotating, true when done
            }
        }
        throw NullReferenceException(); // LAB_18073e51e
    }

    // === STAGE 2: Deploy ===
    if (m_DeployBeforeExecuting) { // +0x4D
        float now = Time.time; // FUN_1829b1320(0)
        if (m_WaitUntil <= now) { // timer expired — proceed
            Tile* actorTile = actor->GetCurrentTile(); // vtable +0x388
            if (actor == null) throw NullReferenceException();
            if (m_DeployedStanceSkill == null) throw NullReferenceException(); // +0x30

            // Fire deploy stance skill at actor's current tile
            FUN_1806e80b0(m_DeployedStanceSkill, actorTile, /*flags=*/0x10, 0);
            bool isDone = FUN_1805e00a0(actor); // Actor.IsDoneActing()

            if (!isDone) {
                // Wait for animation: animDuration + 0.1s buffer
                ActorInfo* info = actor->GetActorInfo(); // vtable +0x398
                if (info == null) throw NullReferenceException();
                // info->animData at info + 0x1E8; animDuration at animData + 0x5C
                float animDuration = info->animData->animDuration; // +0x5C
                m_WaitUntil = Time.time + animDuration + 0.1f; // +0x54
            }
            m_DeployBeforeExecuting = false; // +0x4D — clear flag
            // Return false: either still animating, or just finished — re-enter next frame
            goto ReturnFalse;
        }
        // else: timer not yet expired — fall through (return false at end)
    }

    // === STAGE 3: Setup ===
    if (m_SetupBeforeExecuting) { // +0x4E
        float now = Time.time; // FUN_1829b1320(0)
        if (m_WaitUntil <= now) { // timer expired — proceed
            if (actor == null) throw NullReferenceException();
            Tile* actorTile = actor->GetCurrentTile(); // vtable +0x388
            if (m_SetupWeaponSkill == null) throw NullReferenceException(); // +0x40

            // Fire weapon setup skill at actor's current tile
            FUN_1806e80b0(m_SetupWeaponSkill, actorTile, /*flags=*/0x10, 0);
            bool isDone = FUN_1805e00a0(actor); // Actor.IsDoneActing()

            if (!isDone) {
                // Fixed 3-second wait for weapon setup
                m_WaitUntil = Time.time + 3.0f; // +0x54
            }
            m_SetupBeforeExecuting = false; // +0x4E — clear flag
            return false; // re-enter next frame
        }
        // else: timer not expired — fall through
    }

    // === STAGE 4: Fire main skill ===
    float now = Time.time; // FUN_1829b1320(0)
    if (m_WaitUntil > now) { // +0x54
ReturnFalse:
        return false; // still waiting
    }

    if (actor == null) throw NullReferenceException();
    Tile* fireTile = actor->GetCurrentTile(); // vtable +0x3E8 (offset 1000)
    if (fireTile == null) throw NullReferenceException();

    // Activate main skill — returns true if activation succeeded
    bool fired = FUN_1806f3c30(fireTile, 0); // Skill.Activate(tile)
    return !fired; // XOR 1: returns true (done) when fire succeeded
                   // Note: inversion — confirm semantics of FUN_1806f3c30 return value
}
```

### OnExecute — design notes

The `return uVar2 ^ 1` inversion on the skill fire result (`FUN_1806f3c30`) is notable. If `FUN_1806f3c30` returns `1` on success, the `^ 1` makes `OnExecute` return `0` (false = not done), which would mean "keep executing." This seems counterintuitive. More likely `FUN_1806f3c30` returns `0` on success (fire initiated, animation pending) and `1` on failure, making `OnExecute` return `true` on failure. Alternatively, the return convention of `OnExecute` may be inverted from what was assumed (false = done, true = keep going). This requires validation against a concrete subclass override. Flagged as NQ-9.

The deploy stage wait uses `animDuration + 0.1` from `ActorInfo + 0x1E8 + 0x5C`. The setup stage uses a hardcoded `3.0` seconds. The rotation stage uses a hardcoded `2.0` seconds. Only the deploy wait is data-driven.

---

## 8. `SkillBehavior.GetTargetValue` (public) — `0x18073DD90`

### Raw Ghidra output
```c
void FUN_18073dd90(undefined8 param_1,undefined1 param_2,undefined4 param_3,longlong param_4,
                  undefined4 param_5,undefined8 param_6,undefined8 param_7,undefined8 param_8)
{
  char cVar1;
  longlong lVar2;
  
  if (DAT_183b931cd == '\0') {
    FUN_180427b00(&DAT_183942930);
    DAT_183b931cd = '\x01';
  }
  if (param_4 != 0) {
    cVar1 = FUN_1806889c0(param_4,0);
    if (cVar1 == '\0') {
      FUN_18073c130(param_1,param_2,param_3,param_4,param_5,param_6,param_7,param_8,0,0);
      lVar2 = FUN_180688600(param_4,0);
      if (lVar2 == 0) goto LAB_18073df5e;
      cVar1 = FUN_180616b30(lVar2,0);
      if (cVar1 != '\0') {
        lVar2 = FUN_180688600(param_4,0);
        if ((((lVar2 == 0) || (*(longlong *)(lVar2 + 0x68) == 0)) ||
            (*(longlong *)(*(longlong *)(lVar2 + 0x68) + 0x20) == 0)) ||
           ((lVar2 = FUN_180688600(param_4,0), lVar2 == 0 || (*(longlong *)(lVar2 + 0x68) == 0))))
        goto LAB_18073df5e;
        FUN_18073c130(param_1,param_2,param_3,param_4,param_5,param_6,param_7,param_8,1,0);
      }
    }
    return;
  }
LAB_18073df5e:
  // WARNING: Subroutine does not return
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
void SkillBehavior::GetTargetValue(
    bool     forImmediateUse,  // param_2
    int      uses,             // param_3
    Goal*    goal,             // param_4
    int      goalType,         // param_5 (0=attack, 1=assist-move, 2=assist-skill)
    Tile*    originTile,       // param_6
    Tile*    targetedTile,     // param_7
    unknown  param_8           // param_8 — alternate target (contained entity context)
)
{
    // IL2CPP lazy init — omitted
    // DAT_183942930 = Goal class metadata

    if (goal == null) throw NullReferenceException();

    if (!goal->IsEmpty()) { // FUN_1806889c0 — Goal.IsEmpty()
        // First pass: score against the primary target
        GetTargetValue_Internal(
            this, forImmediateUse, uses, goal, goalType,
            originTile, targetedTile, param_8,
            /*attackContainedEntity=*/false, 0
        ); // FUN_18073c130

        // Check if goal tile contains a living entity inside a container
        Tile* goalTile = goal->GetTile(); // FUN_180688600
        if (goalTile == null) throw NullReferenceException();

        bool isContainer = FUN_180616b30(goalTile); // Tile.IsContainerWithLivingEntity()
        if (isContainer) {
            // Validate that contained entity exists
            goalTile = goal->GetTile();
            if (goalTile == null)              throw NullReferenceException();
            if (goalTile->container == null)   throw NullReferenceException(); // tile + 0x68
            if (goalTile->container->entity == null) throw NullReferenceException(); // container + 0x20

            // Second pass: score against the contained entity
            GetTargetValue_Internal(
                this, forImmediateUse, uses, goal, goalType,
                originTile, targetedTile, param_8,
                /*attackContainedEntity=*/true, 0
            ); // FUN_18073c130
        }
    }
    return; // void return — results written into output struct by internal function
}
```

---

## 9. `ComputeHitProbability` — `0x1806E0AC0`

### Raw Ghidra output
*(Full raw output is in the decompiled_functions.txt export, lines 423–556. Reproduced verbatim:)*

```c
float * FUN_1806e0ac0(float *param_1,longlong param_2,longlong param_3,longlong param_4,
                     longlong param_5,longlong param_6,char param_7,longlong *param_8,char param_9)
{
  char cVar1;
  undefined1 uVar2;
  int iVar3;
  longlong lVar4;
  undefined8 uVar5;
  longlong *plVar6;
  int iVar7;
  float fVar8;
  float fVar9;
  float fVar10;
  float fVar11;
  
  if (DAT_183b92f89 == '\0') {
    FUN_180427b00(&DAT_183981fc8);
    DAT_183b92f89 = '\x01';
  }
  param_1[0] = 0.0;
  param_1[1] = 0.0;
  param_1[2] = 0.0;
  param_1[3] = 0.0;
  param_1[4] = 0.0;
  param_1[5] = 0.0;
  if (*(longlong *)(param_2 + 0x10) == 0) goto LAB_1806e0ea0;
  if (*(char *)(*(longlong *)(param_2 + 0x10) + 0xf3) != '\0') {
    *(undefined1 *)(param_1 + 4) = 1;
    *param_1 = 100.0;
    return param_1;
  }
  if (param_8 == (longlong *)0x0) {
    if (param_4 == 0) goto LAB_1806e0ea0;
    cVar1 = FUN_1806889c0(param_4,0);
    if (cVar1 == '\0') {
      param_8 = (longlong *)FUN_180688600(param_4,0);
    }
  }
  if (param_5 == 0) {
    if (*(longlong *)(param_2 + 0x18) == 0) {
      param_5 = thunk_FUN_1804608d0(DAT_183981fc8);
      FUN_18062a050(param_5,0);
      FUN_18000d310(0x1c,param_2,param_2,param_3,param_4,param_5,param_8);
    }
    else {
      if (*(longlong *)(param_2 + 0x18) == 0) goto LAB_1806e0ea0;
      param_5 = FUN_1806f2460(*(longlong *)(param_2 + 0x18),param_2,param_3,param_4,param_8,0);
    }
  }
  if (param_8 == (longlong *)0x0) {
    fVar8 = 1.0;
  }
  else {
    if (param_6 == 0) {
      lVar4 = (**(code **)(*param_8 + 1000))(param_8,*(undefined8 *)(*param_8 + 0x3f0));
      uVar5 = FUN_1806d5040(param_2,0);
      if (lVar4 == 0) goto LAB_1806e0ea0;
      param_6 = FUN_1806f2230(lVar4,uVar5,param_3,param_4,param_2,0);
      if (param_6 == 0) goto LAB_1806e0ea0;
    }
    fVar8 = (float)FUN_180531700();
  }
  if (param_5 == 0) {
LAB_1806e0ea0:
    // WARNING: Subroutine does not return
    FUN_180427d90();
  }
  fVar9 = (float)FUN_180628270(param_5,0);
  if (param_9 == '\0') {
    if (param_4 == 0) goto LAB_1806e0ea0;
    cVar1 = FUN_1806889c0(param_4,0);
    if ((cVar1 == '\0') && (plVar6 = (longlong *)FUN_180688600(param_4,0), param_8 != plVar6)) {
      uVar5 = FUN_180688600(param_4,0);
      if (param_8 == (longlong *)0x0) goto LAB_1806e0ea0;
      uVar2 = FUN_1806169a0(param_8,uVar5,0);
      goto LAB_1806e0ce4;
    }
  }
  uVar2 = 0;
LAB_1806e0ce4:
  uVar5 = FUN_1806debe0(param_2,param_3,param_4,param_8,param_6,uVar2,0);
  param_1[2] = (float)uVar5;
  param_1[1] = fVar9;
  param_1[3] = fVar8;
  if ((param_7 == '\0') || (param_3 == 0)) {
    fVar8 = (float)FUN_1805316f0(uVar5,0);
    fVar10 = (float)FUN_1805316f0();
    fVar10 = fVar10 * fVar8 * fVar9;
  }
  else {
    iVar3 = FUN_1805ca7a0(param_3,param_4,0);
    iVar3 = iVar3 - *(int *)(param_2 + 0xb8);
    if (DAT_183b92446 == '\0') {
      FUN_180427b00(&DAT_1839400a8);
      DAT_183b92446 = '\x01';
    }
    if (*(int *)(DAT_1839400a8 + 0xe4) == 0) {
      il2cpp_runtime_class_init();
    }
    iVar7 = -iVar3;
    if (iVar7 < 0) {
      iVar7 = iVar3;
    }
    fVar8 = (float)FUN_180628240(param_5,0);
    fVar10 = (float)FUN_1805316f0();
    fVar11 = (float)FUN_1805316f0();
    *(undefined1 *)((longlong)param_1 + 0x11) = 1;
    fVar10 = fVar11 * fVar10 * fVar9 + (float)iVar7 * fVar8;
    param_1[5] = (float)iVar7 * fVar8;
  }
  if (fVar10 < 0.0) {
    fVar10 = 0.0;
  }
  else if (100.0 < fVar10) {
    fVar10 = 100.0;
  }
  iVar3 = *(int *)(param_5 + 0x78);
  *param_1 = fVar10;
  param_1[1] = param_1[1];
  param_1[2] = param_1[2];
  param_1[3] = param_1[3];
  if (fVar10 < (float)iVar3) {
    *param_1 = (float)*(int *)(param_5 + 0x78);
  }
  return param_1;
}
```

### Annotated reconstruction
```c
float* ComputeHitProbability(
    float[6] out,        // param_1: output array, written in-place
    Skill*   skill,      // param_2
    Tile*    originTile, // param_3
    Goal*    goal,       // param_4
    ShotPath* path,      // param_5 (built internally if null)
    ShotData* shotData,  // param_6 (built internally if null)
    bool     useRange,   // param_7: if true, applies range-distance penalty
    Entity*  target,     // param_8 (derived from goal if null)
    bool     selfTarget  // param_9: if true, uses friendly-fire logic
)
{
    // IL2CPP lazy init — omitted

    // Zero-initialise all 6 output slots
    out[0] = out[1] = out[2] = out[3] = out[4] = out[5] = 0.0f;

    SkillData* data = skill->skillData; // skill + 0x10
    if (data == null) throw NullReferenceException();

    // === AUTO-HIT EARLY OUT ===
    if (data->autoHitFlag) { // SkillData + 0xF3
        out[4] = 1.0f;   // autoHitFlag slot
        out[0] = 100.0f; // hitChance = 100%
        return out;
    }

    // Resolve target entity from goal if not provided
    if (target == null && !goal->IsEmpty()) // FUN_1806889c0
        target = goal->GetEntity(); // FUN_180688600

    // Build shot path if not provided
    if (path == null) {
        if (skill->cachedPath == null) { // skill + 0x18
            // Build fresh path
            path = new List<>(); // thunk_FUN_1804608d0(DAT_183981fc8) — allocate empty list
            FUN_18062a050(path); // initialise
            FUN_18000d310(0x1c, skill, originTile, goal, path, target); // ComputeShotPath
        } else {
            path = FUN_1806f2460(skill->cachedPath, skill, originTile, goal, target);
        }
    }
    if (path == null) throw NullReferenceException();

    // Range multiplier: 1.0 if no target, else read from shot data
    float rangeMult;
    if (target == null) {
        rangeMult = 1.0f;
    } else {
        if (shotData == null) {
            Tile* targetTile = target->GetCurrentTile(); // vtable +0x3E8
            // Build shot data from tile/skill context
            shotData = FUN_1806f2230(targetTile, skill->originTile, originTile, goal, skill);
            if (shotData == null) throw NullReferenceException();
        }
        rangeMult = FUN_180531700(); // range-based probability scalar
    }

    float baseAccuracy = FUN_180628270(path); // ShotPath.GetBaseAccuracy()

    // Self/ally flag for cover computation
    bool isSelfOrAlly = false;
    if (!selfTarget && !goal->IsEmpty()) {
        Entity* goalEntity = goal->GetEntity();
        if (target != null && target != goalEntity)
            isSelfOrAlly = FUN_1806169a0(target, goalEntity); // IsFriendly()
    }

    // Cover defense value
    int coverDefense = FUN_1806debe0(skill, originTile, goal, target, shotData, isSelfOrAlly);

    out[2] = (float)coverDefense;
    out[1] = baseAccuracy;
    out[3] = rangeMult;

    float hitChance;
    if (!useRange || originTile == null) {
        // === STANDARD PATH ===
        float coverMod  = FUN_1805316f0(coverDefense); // accuracy given cover
        float globalMod = FUN_1805316f0();             // global accuracy scalar
        hitChance = coverMod * globalMod * baseAccuracy;
    } else {
        // === RANGE-PENALTY PATH ===
        // Range deviation from skill's optimal range
        int distance  = FUN_1805ca7a0(originTile, goal); // tile distance
        int deviation = distance - skill->optimalRangeOffset; // skill + 0xB8 (int)
        int absDeviation = (deviation < 0) ? -deviation : deviation; // abs()

        float rangeAccCost = FUN_180628240(path); // per-tile accuracy cost
        float distPenalty  = (float)absDeviation * rangeAccCost;

        out[5] = distPenalty; // isolated range penalty component
        // Set range-calc active flag at byte offset +0x11 within out array
        ((byte*)out)[0x11] = 1;

        float coverMod  = FUN_1805316f0(); // accuracy scalar (no cover arg in this branch)
        float globalMod = FUN_1805316f0();
        hitChance = globalMod * coverMod * baseAccuracy + distPenalty;
    }

    // Clamp to [0, 100]
    if (hitChance < 0.0f)   hitChance = 0.0f;
    if (hitChance > 100.0f) hitChance = 100.0f;

    // Apply minimum hit floor from shot path
    int minHit = path->minimumHitChance; // path + 0x78
    if (hitChance < (float)minHit)
        hitChance = (float)minHit;

    out[0] = hitChance;
    // Note: out[1], out[2], out[3] re-assigned (no-op in Ghidra — compiler artefact)
    return out;
}
```

---

## 10. `ComputeDamageData` — `0x1806DF4E0`

### Raw Ghidra output
*(Full raw output in decompiled_functions_2.txt lines 15–418, reproduced verbatim)*

*[Operator note: raw output is 400+ lines; included in full in the attached export file. Reconstruction follows.]*

### Annotated reconstruction
```c
DamageData* ComputeDamageData(
    Skill*    skill,       // param_1: the Skill object (NOT SkillBehavior — confirmed: passed as m_Skill)
    Tile*     originTile,  // param_2: Tile* _from
    Goal*     goal,        // param_3: Goal* _goal
    Goal*     altGoal,     // param_4: Goal* for contained entity (or null)
    Entity*   target,      // param_5: Entity* _target
    ShotPath* path,        // param_6: ShotPath* (built internally if null)
    ShotData* shotData,    // param_7: ShotData* (built internally if null)
    int       uses,        // param_8: int _uses
    DamageData* out        // param_9: output (allocated if null)
)
{
    // IL2CPP lazy init — omitted

    // Allocate output if not provided
    if (out == null) {
        out = new DamageData(); // thunk_FUN_1804608d0(DAT_183976298)
        FUN_1804eb570(out);     // zero-initialise
    }

    // Resolve target from goal if not provided
    if (target == null) {
        if (goal == null) throw NullReferenceException();
        if (goal->IsEmpty()) return out; // FUN_1806889c0
        target = goal->GetEntity();      // FUN_180688600
        if (target == null) return out;
    }

    // Use altGoal as effective target goal if provided (contained entity case)
    Goal* effectiveGoal = (altGoal != null) ? altGoal : goal;

    // Build shot path if not provided
    if (path == null) {
        if (skill->cachedPath == null) { // skill + 0x18
            path = new List<>();
            FUN_18062a050(path);
            FUN_18000d310(0x1c, skill, originTile, goal, path, target);
        } else {
            path = FUN_1806f2460(skill->cachedPath, skill, originTile, goal, target);
        }
        if (target == null) throw NullReferenceException();
    }

    // Self/ally targeting flag (bVar3)
    Tile* targetCurrentTile = target->GetCurrentTile(); // vtable +0x388
    bool isSelfOrAlly;
    if (targetCurrentTile == goal && FUN_180616ae0(target)) { // actor is at goal and is deployed
        isSelfOrAlly = true;
    } else {
        if (goal == null || goal->IsEmpty()) throw NullReferenceException();
        Entity* goalEntity = goal->GetEntity();
        isSelfOrAlly = (target != goalEntity) && FUN_1806169a0(target, goalEntity); // IsFriendly
    }

    // Build shot data if not provided
    if (shotData == null) {
        Tile* targetTile = target->GetCurrentTile(); // vtable +0x3E8
        // FUN_1806d5040 = get origin tile from skill context
        shotData = FUN_1806f2230(targetTile, FUN_1806d5040(skill), originTile, goal, skill);
    }

    // Write shotData reference (with write barrier)
    out->shotData = shotData; // +0x28
    // write barrier — omitted

    if (shotData == null || goal == null) throw NullReferenceException();

    float baseHitChance = FUN_1805316f0(); // base hit chance float

    // Range band for this shot (short/medium/long/extreme)
    uint rangeBand = FUN_1805ca720(goal, originTile);

    // Distance modifiers from path (fVar26, fVar27, fVar28)
    float movePenalty = 0.0f, altDistPenalty = 0.0f, thirdModifier = 0.0f;
    if (goal != effectiveGoal) { // target differs from direct goal — movement involved
        if (skill->hasMovementPenalty) { // skill + 0x10 -> + 0x178
            int dist = FUN_1805ca7a0(effectiveGoal, goal); // tile distance
            movePenalty    = (float)dist * path->movementAccuracyPenaltyPerTile; // path + 0x128
            altDistPenalty = (float)dist * path->altDistancePenaltyCoeff;        // path + 0x110
            thirdModifier  = (float)dist * path->thirdDistanceModifier;          // path + 0x13C
        }
    }

    // Range deviation from optimal
    int rangeDist = FUN_1805ca7a0(originTile, goal);
    int rangeDeviation = abs(rangeDist - skill->optimalRangeOffset); // skill + 0xB4

    // Accuracy formula (when path is provided)
    if (path != null) {
        float hpFloor  = max((float)target->hp * path->hpAccuracyCoeff, path->hpFloor);
                                                 // target + 0x54 * path + 0x144 vs +0x148
        float apFloor  = max((float)target->apCost * path->apAccuracyCoeff, path->apFloor);
                                                 // target[0xB] * path + 0x14C vs +0x150
        float hitBase  = FUN_1806285e0(path);   // ShotPath.GetHitBase()
        float rangeMod = FUN_180628550(path);   // ShotPath.GetRangeMod()

        float hitChance = (hpFloor + rangeMod * rangeDeviation + hitBase
                           + movePenalty + apFloor)
                          * baseHitChance
                          * shotData->accuracyMult   // shotData + 0x8C
                          * path->overallMult;       // path + 0x140

        // Apply team/cover accuracy modifier if relevant
        if (skill->skillData != null && !skill->skillData->isIndirect) { // skill + 0x100
            int tileDist = FUN_1805ca7a0(originTile, goal);
            if (tileDist > 1) {
                // Look up range accuracy table — indexed by rangeBand
                // Applies FUN_1805316d0 modifier to local_e8 (accuracy multiplier)
            }
        }

        // === PER SHOT GROUP LOOP ===
        // Iterates skill->shotGroups (skill + 0x48 — confirmed as Skill field, not SkillBehavior)
        foreach (ShotGroup group in skill->shotGroups) {

            int maxAmmo     = target->ammoCapacity; // target[4] + 0x18
            int extraHits   = path->baseExtraHits;  // path + 0x16C
            float burstFrac = path->burstFraction;  // path + 0x170

            // Burst distribution calculation
            int rawHits = (int)ceil((float)maxAmmo * burstFrac) + extraHits;
            int shotsThisGroup;
            if (rawHits <= 1) {
                shotsThisGroup = 1;
            } else {
                int half = (int)ceil((float)rawHits * 0.5f);
                shotsThisGroup = (rawHits - half) / 2 + half;
            }

            // Cover penetration chance
            float rangePenaltyA   = FUN_180628330(path); // path cover penalty A
            float rangePenaltyB   = FUN_180628300(path); // path cover penalty B
            float accumulated     = max(0.0f, rangePenaltyB * rangeDeviation + rangePenaltyA + thirdModifier);
            int   coverStrength   = FUN_180628380(group); // group cover strength value
            float accuracy        = FUN_180614b30(target); // target accuracy rating
            float coverPenChance  = (100.0f - (accuracy * coverStrength - accumulated) * 3.0f) * 0.01f;
            coverPenChance = clamp(coverPenChance, 0.0f, 1.0f);
            out->coverPenetrationChance = max(out->coverPenetrationChance, coverPenChance); // +0x20

            // Armour residual via powf
            int   armorIgnoredPct = FUN_1806defc0(skill, skill->armorPenetration);
            float armorResidual   = powf(1.0f - (float)(skill->armorReductionPct) * 0.01f);
                                    // FUN_1804bad80 = powf; exponent from skill + 0x244
            armorResidual = max(armorResidual, 1.0f);

            // Expected hits this group
            int effectiveShots = min(shotsThisGroup, maxAmmo);
            float expectedHits = (coverPenChance > 0.0f) ? (float)effectiveShots * hitBase : 0.0f;

            // Accumulate raw damage
            out->expectedRawDamage   += coverPenChance * expectedHits;            // +0x10
            float killFraction        = out->expectedRawDamage / (float)target->maxHP;
            out->expectedKills        = min(killFraction, (float)maxAmmo);         // +0x18
            out->expectedRawDamage_norm += out->expectedRawDamage / (float)target->maxHP; // (+0x1C, inferred)

            // Effective damage (blended cover/armour)
            float effectiveDmg = ((float)rangeDeviation * rangePenaltyB + rangePenaltyA + thirdModifier)
                                 * accuracy * hitRatio;
            effectiveDmg = min(effectiveDmg, (float)target->currentHP / (float)target->maxHP); // cap to kill fraction
            out->expectedEffectiveDamage +=
                (1.0f - coverPenChance) * effectiveDmg + coverPenChance * effectiveDmg; // +0x14
                // Note: both terms collapse — cover-weighted split may be intended as future branching

            // Kill flags
            out->canKillInOneShot   |= ((float)maxAmmo <= out->expectedKills);    // +0x24
            out->canKillWithFullMag  = ((float)maxAmmo <= expectedHits / (float)target->maxHP); // +0x25

            if (baseHitChance <= 0.0f) return out; // no more hits possible
        }
    }

    return out;
}
```

### ComputeDamageData — design notes

**`param_1` is confirmed as `Skill*`, not `SkillBehavior*`.** The function is called from `GetTargetValue` private where `param_1 + 0x20` (`m_Skill`) is passed as the first argument. Therefore `skill + 0x48` is a field on the `Skill` object — a list of `ShotGroup` objects. `SkillBehavior.m_AdditionalRadius` at `+0x48` is unrelated. The preliminary annotation in the class field table has been corrected.

**The `(1 - coverPenChance) * effectiveDmg + coverPenChance * effectiveDmg` formula** is algebraically equal to `effectiveDmg`. The two-term form may be a compiler artefact of a pattern that was originally meant to apply different damage values for the cover vs. no-cover cases. It is faithfully reproduced here.

**`FUN_180002310(1, AMMO_TABLE)` and `FUN_180002310(2, AMMO_TABLE)`** in `ConsiderSkillSpecifics` suggest a shared lookup table for current/max ammo indexed by `1` and `2`. The same table is likely used in `ComputeDamageData`'s ammo capacity reads. The table class is `DAT_1839a6620`.