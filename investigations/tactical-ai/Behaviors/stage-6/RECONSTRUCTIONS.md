# Menace Tactical AI — Stage 6 Annotated Function Reconstructions
# Deploy Behavior Lifecycle

**Source:** Ghidra decompilation of Menace (Windows x64, Unity IL2CPP)
**Image base:** 0x180000000
**Format:** Each function shows the raw Ghidra output followed by a fully annotated
C-style reconstruction with all offsets resolved.

---

## Quick-Reference Field Tables

### Deploy (Menace.Tactical.AI.Behaviors — TypeDefIndex 3645)
| Offset | Type | Name |
|---|---|---|
| +0x010 | AgentContext* | agentContext (inherited from Behavior) |
| +0x01C | bool | field_0x1c (base Behavior flag — "target set") |
| +0x020 | Tile* | m_TargetTile |
| +0x028 | bool | m_IsDone |

### TileScore
| Offset | Type | Name |
|---|---|---|
| +0x010 | Tile* | tile |
| +0x020 | float | movementScore |
| +0x024 | float | secondaryMovementScore |
| +0x028 | float | exposureScore |
| +0x030 | float | rangeScore |
| +0x034 | float | utilityScore |

### WeightsConfig (IL2CPP class name unresolved — accessed via DAT_18394c3d0 + 0xb8 + 8)
| Offset | Type | Inferred Name |
|---|---|---|
| +0x054 | float | movementScoreWeight |
| +0x0BC | float | tagValueScale |
| +0x0CC | float | rangePenaltyScale ← new Stage 6 |
| +0x0D0 | float | allyProximityPenaltyScale ← new Stage 6 |
| +0x0E0 | float | friendlyFirePenaltyWeight |
| ... | ... | (full table in prior stage REPORT.md files) |

### Actor (partial)
| Offset | Type | Name |
|---|---|---|
| +0x050 | bool | isSetUp_alt ← new Stage 6 |
| +0x054 | int | currentHP |
| +0x15C | bool | isWeaponSetUp |
| +0x15F | bool | field_0x15F (checked in OnExecute return) |
| +0x162 | bool | isDead |

---

## 1. Deploy.GetHighestTileScore — 0x18073A0C0

### Raw Ghidra output
```c
longlong FUN_18073a0c0(longlong param_1)

{
  longlong lVar1;
  char cVar2;
  longlong lVar3;
  float fVar4;
  float fVar5;
  undefined8 local_80;
  undefined8 uStack_78;
  undefined8 local_70;
  longlong lStack_68;
  undefined8 local_60;
  undefined8 local_58;
  undefined8 uStack_50;
  undefined8 local_48;
  longlong lStack_40;
  undefined8 local_38;
  
  if (DAT_183b931f8 == '\0') {
    FUN_180427b00(&DAT_183977938);
    FUN_180427b00(&DAT_18395be38);
    FUN_180427b00(&DAT_18395bef8);
    FUN_180427b00(&DAT_18395bfb0);
    FUN_180427b00(&DAT_18398e1b8);
    DAT_183b931f8 = '\x01';
  }
  if ((*(longlong *)(param_1 + 0x10) == 0) ||
     (lVar3 = *(longlong *)(*(longlong *)(param_1 + 0x10) + 0x60), lVar3 == 0)) {
                    /* WARNING: Subroutine does not return */
    FUN_180427d90();
  }
  FUN_18136d8a0(&local_58,lVar3,DAT_183977938);
  local_80 = local_58;
  uStack_78 = uStack_50;
  local_70 = local_48;
  lStack_68 = lStack_40;
  local_60 = local_38;
  lVar3 = 0;
LAB_18073a190:
  cVar2 = FUN_18152f9b0(&local_80,DAT_18395bef8);
  lVar1 = lStack_68;
  if (cVar2 == '\0') {
    FUN_1804f7ee0(&local_80,DAT_18395be38);
    return lVar3;
  }
  if (lVar3 != 0) goto code_r0x00018073a1af;
  goto LAB_18073a1df;
code_r0x00018073a1af:
  if (lStack_68 == 0) {
                    /* WARNING: Subroutine does not return */
    FUN_180427d90();
  }
  fVar4 = (float)FUN_180740f20(lStack_68,0);
  fVar5 = (float)FUN_180740f20(lVar3,0);
  if (fVar5 < fVar4) {
LAB_18073a1df:
    lVar3 = lVar1;
  }
  goto LAB_18073a190;
}
```

### Annotated reconstruction
```c
// IL2CPP lazy init — omitted

TileScore* Deploy_GetHighestTileScore(Deploy* self)
{
    // Null-guard: agentContext and tileDict must exist
    if (self->agentContext == null ||                         // +0x10
        self->agentContext->tileDict == null)                 // agentContext+0x60
        NullReferenceException();

    // Get enumerator over tileDict (Dictionary<Tile, TileScore>)
    DictEnumerator iter = GetEnumerator(self->agentContext->tileDict);

    TileScore* best = null;

    while (DictEnumerator_MoveNext(&iter))                    // iterate all entries
    {
        TileScore* candidate = iter.currentValue;             // current TileScore entry

        if (best == null)
        {
            // First entry — take it unconditionally
            best = candidate;
            continue;
        }

        // Null-guard candidate
        if (candidate == null)
            NullReferenceException();

        float candidateScore = TileScore_GetCompositeScore(candidate, 0);  // FUN_180740f20 — composite score getter
        float bestScore      = TileScore_GetCompositeScore(best, 0);

        if (bestScore < candidateScore)
        {
            // Candidate beats current best
            best = candidate;
        }
    }

    Enumerator_Dispose(&iter);
    return best;
}
```

### GetHighestTileScore — design notes

Standard argmax over `tileDict`. The comparison function `FUN_180740f20` (TileScore composite score getter) is called on both the current best and the challenger each iteration — it is not cached. The exact formula inside `FUN_180740f20` is unknown (NQ-41) but it combines TileScore fields into a single float for ordering. The function is a leaf relative to this investigation.

---

## 2. Deploy.OnEvaluate — 0x18073AD00

### Raw Ghidra output
```c
undefined8 FUN_18073ad00(longlong param_1,longlong *param_2)

{
  longlong lVar1;
  longlong lVar2;
  
  if (DAT_183b9233f == '\0') {
    FUN_180427b00(&DAT_183981f50);
    DAT_183b9233f = '\x01';
  }
  if (**(longlong **)(DAT_183981f50 + 0xb8) != 0) {
    if ((*(int *)(**(longlong **)(DAT_183981f50 + 0xb8) + 0x60) != 0) ||
       (*(char *)(param_1 + 0x28) != '\0')) {
      return 0;
    }
    if (param_2 != (longlong *)0x0) {
      lVar1 = (**(code **)(*param_2 + 0x388))(param_2,*(undefined8 *)(*param_2 + 0x390));
      lVar2 = FUN_18073a0c0(param_1,0);
      if ((lVar2 != 0) && (*(longlong *)(lVar2 + 0x10) != lVar1)) {
        *(undefined8 *)(param_1 + 0x20) = *(undefined8 *)(lVar2 + 0x10);
        FUN_180426e50(param_1 + 0x20);
        return 1000;
      }
      if (*(longlong *)(param_1 + 0x10) != 0) {
        *(undefined1 *)(*(longlong *)(param_1 + 0x10) + 0x50) = 1;
        *(undefined1 *)(param_1 + 0x28) = 1;
        return 0;
      }
    }
  }
                    /* WARNING: Subroutine does not return */
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// IL2CPP lazy init — omitted

int Deploy_OnEvaluate(Deploy* self, Strategy* strategy)
{
    // Null-guard: strategy singleton must exist
    // (DAT_183981f50 = Strategy class static storage)
    Strategy* strategyInstance = Strategy_GetSingleton();
    if (strategyInstance == null)
        NullReferenceException();

    // GUARD 1: strategy mode suppression
    // strategyInstance +0x60 = strategyMode (int; 1 = suppress deploy)
    if (strategyInstance->strategyMode != 0)
        return 0;

    // GUARD 2: already done
    if (self->m_IsDone)            // +0x028
        return 0;

    if (strategy == null)
        NullReferenceException();

    // Get actor's current tile via vtable
    Tile* actorCurrentTile = strategy->vtable[0x388](strategy);  // GetActorTile or equivalent

    // Get best candidate tile
    TileScore* best = Deploy_GetHighestTileScore(self);   // FUN_18073a0c0

    if (best != null && best->tile != actorCurrentTile)   // +0x10 = TileScore.tile
    {
        // Not yet at the best tile — set target and score high
        self->m_TargetTile = best->tile;                  // +0x020 = m_TargetTile; write barrier follows
        // write barrier
        return 1000;
    }

    // Already at the best tile (or no best tile found) — signal done
    if (self->agentContext != null)                       // +0x010
    {
        self->agentContext->field_0x50 = 1;               // agentContext+0x50 — deploy-complete signal (NQ-42: label conflict with behaviorConfig*)
        self->m_IsDone = true;                            // +0x028
        return 0;
    }

    NullReferenceException();  // agentContext was null
}
```

### OnEvaluate — design notes

Deploy uses a hardcoded return value of 1000 when it has work to do — this is the highest fixed score in the behavior system and ensures Deploy preempts other behaviors until complete. The done-state is managed via two mechanisms: `m_IsDone` (prevents re-entry next turn) and `agentContext.field_0x50` (signals to the broader context that deployment has occurred). The label `field_0x50` conflicts with the prior `behaviorConfig*` label for `AgentContext.+0x50` — see NQ-42.

---

## 3. Deploy.OnExecute — 0x18073ADD0

### Raw Ghidra output
```c
bool FUN_18073add0(longlong param_1,longlong param_2)

{
  char cVar1;
  uint local_res8 [2];
  
  if (*(char *)(param_1 + 0x1c) == '\0') {
    if (param_2 != 0) {
LAB_18073ae44:
      return *(char *)(param_2 + 0x15f) == '\0';
    }
  }
  else {
    local_res8[0] = 0;
    if (*(longlong *)(param_1 + 0x20) != 0) {
      cVar1 = FUN_1806889c0(*(longlong *)(param_1 + 0x20),0);
      if (cVar1 == '\0') {
        local_res8[0] = local_res8[0] | 1;
      }
      if (param_2 != 0) {
        FUN_1805e03b0(param_2,*(undefined8 *)(param_1 + 0x20),local_res8,3,0);
        if (*(longlong *)(param_1 + 0x10) != 0) {
          *(undefined1 *)(*(longlong *)(param_1 + 0x10) + 0x50) = 1;
          *(undefined1 *)(param_1 + 0x28) = 1;
          goto LAB_18073ae44;
        }
      }
    }
  }
                    /* WARNING: Subroutine does not return */
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
bool Deploy_OnExecute(Deploy* self, Actor* actor)
{
    if (!self->field_0x1c)           // +0x01C — base Behavior "target set" flag; false = no target assigned
    {
        // No target — passthrough
        if (actor != null)
            return actor->field_0x15F == 0;   // +0x15F — actor readiness flag; true when NOT set
        NullReferenceException();
    }
    else
    {
        // Target tile is set — execute the move
        uint flags = 0;

        if (self->m_TargetTile != null)    // +0x020
        {
            // Check if target tile is currently occupied
            bool isOccupied = Tile_IsOccupied(self->m_TargetTile, 0);  // FUN_1806889c0
            if (!isOccupied)
                flags |= 1;                // flag bit 0: tile is free

            if (actor != null)
            {
                // Issue move command to actor targeting m_TargetTile with flags
                Actor_MoveToTile(actor, self->m_TargetTile, &flags, 3, 0);   // FUN_1805e03b0

                // Signal deploy complete
                if (self->agentContext != null)    // +0x010
                {
                    self->agentContext->field_0x50 = 1;    // agentContext+0x50 — deploy-complete signal
                    self->m_IsDone = true;                 // +0x028
                    return actor->field_0x15F == 0;        // +0x15F
                }
            }
        }
    }

    NullReferenceException();
}
```

### OnExecute — design notes

The function has two branches gated on `self->field_0x1c` (a base `Behavior` field at `+0x1C` whose real name is unknown). When false, execution is a no-op that returns the actor's readiness state. When true, the target tile is passed to `FUN_1805e03b0` (move command issuer) along with an occupancy flag. The `agentContext->field_0x50` write and `m_IsDone` set mirror the pattern in `OnEvaluate`'s already-at-tile path, ensuring idempotency.

---

## 4. Deploy.OnCollect — 0x18073A260

### Raw Ghidra output
```c
undefined8 FUN_18073a260(longlong param_1,longlong *param_2,longlong param_3)

{
  float fVar1;
  longlong lVar2;
  longlong *plVar3;
  char cVar4;
  char cVar5;
  int iVar6;
  longlong lVar7;
  longlong *plVar8;
  longlong lVar9;
  undefined8 uVar10;
  undefined4 local_158;
  undefined4 uStack_154;
  undefined4 uStack_150;
  undefined4 uStack_14c;
  longlong *local_148;
  undefined8 uStack_140;
  undefined8 local_138;
  longlong *local_128;
  undefined4 uStack_120;
  undefined4 uStack_11c;
  undefined4 local_118;
  undefined4 uStack_114;
  undefined4 uStack_110;
  undefined4 uStack_10c;
  longlong *local_108;
  undefined8 local_100;
  undefined8 uStack_f8;
  longlong *local_f0;
  undefined8 local_e8;
  undefined8 uStack_e0;
  longlong *local_d8;
  longlong local_d0;
  longlong local_c8;
  undefined8 local_c0;
  undefined8 uStack_b8;
  longlong *local_b0;
  undefined8 uStack_a8;
  undefined8 local_a0;
  
  if (DAT_183b931f7 == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    FUN_180427b00(&DAT_183977878);
    FUN_180427b00(&DAT_183977938);
    FUN_180427b00(&DAT_183977c38);
    FUN_180427b00(&DAT_18393e110);
    FUN_180427b00(&DAT_183945130);
    FUN_180427b00(&DAT_18395be38);
    FUN_180427b00(&DAT_183993cb0);
    FUN_180427b00(&DAT_1839451e8);
    FUN_180427b00(&DAT_183993d68);
    FUN_180427b00(&DAT_18395bef8);
    FUN_180427b00(&DAT_18393e1c8);
    FUN_180427b00(&DAT_183993e20);
    FUN_180427b00(&DAT_18395bfb0);
    FUN_180427b00(&DAT_18393e280);
    FUN_180427b00(&DAT_1839452a0);
    FUN_180427b00(&DAT_18398e100);
    FUN_180427b00(&DAT_18398e1b8);
    FUN_180427b00(&DAT_18398b9c8);
    FUN_180427b00(&DAT_18399f748);
    FUN_180427b00(&DAT_18398bb30);
    FUN_180427b00(&DAT_1839a25c0);
    FUN_180427b00(&DAT_18399f520);
    FUN_180427b00(&DAT_18398b6e8);
    FUN_180427b00(&DAT_18399f800);
    FUN_180427b00(&DAT_183983180);
    FUN_180427b00(&DAT_1839863c8);
    FUN_180427b00(&DAT_1839888f0);
    DAT_183b931f7 = '\x01';
  }
  local_100 = 0;
  uStack_f8 = 0;
  local_f0 = (longlong *)0x0;
  local_c0 = 0;
  uStack_b8 = 0;
  local_b0 = (longlong *)0x0;
  uStack_a8 = 0;
  local_a0 = 0;
  local_e8 = 0;
  uStack_e0 = 0;
  local_d8 = (longlong *)0x0;
  if (DAT_183b9233f == '\0') {
    FUN_180427b00(&DAT_183981f50);
    DAT_183b9233f = '\x01';
  }
  lVar2 = **(longlong **)(DAT_183981f50 + 0xb8);
  if (lVar2 != 0) {
    if (*(int *)(lVar2 + 0x60) != 0) {
      return 0;
    }
    lVar7 = thunk_FUN_1804608d0(DAT_1839863c8);
    FUN_180cc91f0(lVar7,DAT_18399f520);
    local_d0 = lVar7;
    plVar8 = (longlong *)thunk_FUN_1804608d0(DAT_183983180);
    FUN_180cc91f0(plVar8,DAT_18398b6e8);
    local_128 = plVar8;
    if ((param_2 != (longlong *)0x0) &&
       (lVar9 = (**(code **)(*param_2 + 0x398))(param_2,*(undefined8 *)(*param_2 + 0x390)),
       lVar9 != 0)) {
      cVar5 = *(char *)(lVar9 + 0xcc);
      if ((*(longlong *)(param_1 + 0x10) != 0) &&
         ((lVar9 = FUN_18071b640(*(longlong *)(param_1 + 0x10),0), lVar9 != 0 &&
          (FUN_18073b950(lVar9,lVar7,2,0), lVar7 != 0)))) {
        if (*(int *)(lVar7 + 0x18) == 0) {
          return 0;
        }
        if ((*(longlong *)(param_1 + 0x10) != 0) &&
           (lVar9 = *(longlong *)(*(longlong *)(param_1 + 0x10) + 0x10), lVar9 != 0)) {
          local_c8 = *(longlong *)(lVar9 + 0x20);
          lVar2 = *(longlong *)(lVar2 + 0x28);
          FUN_180cbab80(&local_158,lVar7,DAT_18399f748);
          local_118 = local_158;
          uStack_114 = uStack_154;
          uStack_110 = uStack_150;
          uStack_10c = uStack_14c;
          local_108 = local_148;
          while (cVar4 = FUN_1814f4770(&local_118,DAT_1839451e8), cVar4 != '\0') {
            if (local_108 == (longlong *)0x0) {
                    /* WARNING: Subroutine does not return */
              FUN_180427d90();
            }
            if (lVar2 == 0) {
                    /* WARNING: Subroutine does not return */
              FUN_180427d90();
            }
            local_158 = (undefined4)local_108[2];
            uStack_154 = *(undefined4 *)((longlong)local_108 + 0x14);
            uStack_150 = (undefined4)local_108[3];
            uStack_14c = *(undefined4 *)((longlong)local_108 + 0x1c);
            FUN_1806343a0(lVar2,&local_158,plVar8,cVar5 == '\0',1,1,0);
            if (plVar8 == (longlong *)0x0) {
                    /* WARNING: Subroutine does not return */
              FUN_180427d90();
            }
            FUN_180cbab80(&local_158,plVar8,DAT_18398bb30);
            local_100 = CONCAT44(uStack_154,local_158);
            uStack_f8 = CONCAT44(uStack_14c,uStack_150);
            local_f0 = local_148;
LAB_18073a6a0:
            cVar4 = FUN_1814f4770(&local_100,DAT_18393e1c8);
            plVar3 = local_f0;
            if (cVar4 != '\0') {
              if (local_f0 == (longlong *)0x0) {
                    /* WARNING: Subroutine does not return */
                FUN_180427d90();
              }
              cVar4 = FUN_1806889c0(local_f0,0);
              if (cVar4 == '\0') goto code_r0x00018073a6db;
              goto LAB_18073a758;
            }
            FUN_1804f7ee0(&local_100,DAT_18393e110);
            *(int *)((longlong)plVar8 + 0x1c) = *(int *)((longlong)plVar8 + 0x1c) + 1;
            lVar7 = plVar8[3];
            *(undefined4 *)(plVar8 + 3) = 0;
            if (0 < (int)lVar7) {
              FUN_181b73d10(plVar8[2],0,(int)lVar7,0);
            }
          }
          FUN_1804f7ee0(&local_118,DAT_183945130);
          if (param_3 != 0) {
            FUN_18136d8a0(&local_158,param_3,DAT_183977938);
            local_c0 = CONCAT44(uStack_154,local_158);
            uStack_b8 = CONCAT44(uStack_14c,uStack_150);
            local_b0 = local_148;
            uStack_a8 = uStack_140;
            local_a0 = local_138;
            do {
              cVar5 = FUN_18152f9b0(&local_c0,DAT_18395bef8);
              if (cVar5 == '\0') {
                FUN_1804f7ee0(&local_c0,DAT_18395be38);
                return 1;
              }
              local_128 = local_b0;
              uStack_120 = (undefined4)uStack_a8;
              uStack_11c = uStack_a8._4_4_;
              FUN_180cbab80(&local_158,local_d0,DAT_18399f748);
              plVar8 = local_128;
              local_118 = local_158;
              uStack_114 = uStack_154;
              uStack_110 = uStack_150;
              uStack_10c = uStack_14c;
              local_108 = local_148;
              lVar2 = CONCAT44(uStack_11c,uStack_120);
              while (cVar5 = FUN_1814f4770(&local_118,DAT_1839451e8), plVar3 = local_108,
                    cVar5 != '\0') {
                if (local_108 == (longlong *)0x0) {
                    /* WARNING: Subroutine does not return */
                  FUN_180427d90();
                }
                local_158 = (undefined4)local_108[2];
                uStack_154 = *(undefined4 *)((longlong)local_108 + 0x14);
                uStack_150 = (undefined4)local_108[3];
                uStack_14c = *(undefined4 *)((longlong)local_108 + 0x1c);
                iVar6 = FUN_18053feb0(&local_158,plVar8,0);
                if (lVar2 == 0) {
                    /* WARNING: Subroutine does not return */
                  FUN_180427d90();
                }
                fVar1 = *(float *)(lVar2 + 0x30);
                if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
                  il2cpp_runtime_class_init(DAT_18394c3d0);
                }
                lVar7 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
                if (lVar7 == 0) {
                    /* WARNING: Subroutine does not return */
                  FUN_180427d90();
                }
                if (plVar3 == (longlong *)0x0) {
                    /* WARNING: Subroutine does not return */
                  FUN_180427d90();
                }
                *(float *)(lVar2 + 0x30) =
                     -*(float *)(lVar7 + 0xcc) * (float)iVar6 * *(float *)((longlong)plVar3 + 0x24)
                     + fVar1;
              }
              FUN_1804f7ee0(&local_118,DAT_183945130);
              if (local_c8 == 0) {
                    /* WARNING: Subroutine does not return */
                FUN_180427d90();
              }
              FUN_180cbab80(&local_158,local_c8,DAT_1839a25c0);
              local_e8 = CONCAT44(uStack_154,local_158);
              uStack_e0 = CONCAT44(uStack_14c,uStack_150);
              local_d8 = local_148;
              while (cVar5 = FUN_1814f4770(&local_e8,DAT_183993d68), cVar5 != '\0') {
                if (local_d8 == (longlong *)0x0) {
                    /* WARNING: Subroutine does not return */
                  FUN_180427d90();
                }
                if (local_d8[0x19] == 0) {
                    /* WARNING: Subroutine does not return */
                  FUN_180427d90();
                }
                if (*(char *)(local_d8[0x19] + 0x50) != '\0') {
                  lVar7 = (**(code **)(*local_d8 + 0x388))
                                    (local_d8,*(undefined8 *)(*local_d8 + 0x390));
                  if (lVar7 == 0) {
                    /* WARNING: Subroutine does not return */
                    FUN_180427d90();
                  }
                  iVar6 = FUN_1805ca7a0(lVar7,plVar8,0);
                  if ((float)iVar6 < 6.0) {
                    if (lVar2 == 0) {
                    /* WARNING: Subroutine does not return */
                      FUN_180427d90();
                    }
                    fVar1 = *(float *)(lVar2 + 0x30);
                    if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
                      il2cpp_runtime_class_init(DAT_18394c3d0);
                    }
                    lVar7 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
                    if (lVar7 == 0) {
                    /* WARNING: Subroutine does not return */
                      FUN_180427d90();
                    }
                    *(float *)(lVar2 + 0x30) =
                         (6.0 - (float)iVar6) * -*(float *)(lVar7 + 0xd0) + fVar1;
                  }
                }
              }
              FUN_1804f7ee0(&local_e8,DAT_183993cb0);
            } while( true );
          }
        }
      }
    }
  }
                    /* WARNING: Subroutine does not return */
  FUN_180427d90();
code_r0x00018073a6db:
  if (cVar5 != '\0') {
    if (plVar3 == (longlong *)0x0) {
                    /* WARNING: Subroutine does not return */
      FUN_180427d90();
    }
    lVar7 = FUN_180688600(plVar3,0);
    if (lVar7 == 0) {
                    /* WARNING: Subroutine does not return */
      FUN_180427d90();
    }
    cVar4 = FUN_180616af0(lVar7,0);
    if (cVar4 != '\0') {
      lVar7 = FUN_180688600(plVar3,0);
      if (lVar7 == 0) {
                    /* WARNING: Subroutine does not return */
        FUN_180427d90();
      }
      cVar4 = FUN_180616b30(lVar7,0);
      if (cVar4 == '\0') {
        lVar7 = FUN_180688600(plVar3,0);
        if (lVar7 == 0) {
                    /* WARNING: Subroutine does not return */
          FUN_180427d90();
        }
        cVar4 = FUN_180616780(lVar7,param_2,0);
        if (cVar4 != '\0') {
LAB_18073a758:
          if (param_3 == 0) {
                    /* WARNING: Subroutine does not return */
            FUN_180427d90();
          }
          cVar4 = FUN_181421d50(param_3,plVar3);
          if (cVar4 == '\0') {
            uVar10 = thunk_FUN_1804608d0(DAT_1839888f0);
            FUN_180741530(uVar10,plVar3,0);
            FUN_181446c90(param_3,plVar3);
          }
        }
      }
    }
  }
  goto LAB_18073a6a0;
}
```

### Annotated reconstruction
```c
// IL2CPP lazy init — omitted

bool Deploy_OnCollect(Deploy* self, Strategy* strategy, Dictionary<Tile,TileScore>* tileDict)
{
    // GUARD: strategy suppression
    Strategy* strategyInstance = Strategy_GetSingleton();  // DAT_183981f50 + 0xb8
    if (strategyInstance == null)
        NullReferenceException();
    if (strategyInstance->strategyMode != 0)               // +0x60
        return false;

    // Allocate temporary working lists
    List* candidateList = new List();   // local_d0 — will hold type-2 proximity candidate tiles
    List* pathList      = new List();   // local_128 — will hold TileScore entries per candidate

    // Get entity reference from strategy via vtable +0x398
    // (same vtable slot used in OnEvaluate — returns entity/actor reference)
    Entity* entity = strategy->vtable[0x398](strategy);
    if (entity == null) goto NULL_FAIL;

    bool entityFlag = entity->field_0xCC;   // +0xcc on entity — bool, inferred "isSetUp" or similar (NQ-43)

    // Get candidate source from agentContext
    if (self->agentContext == null) goto NULL_FAIL;   // +0x010
    void* candidateSource = AgentContext_GetCandidateSource(self->agentContext, 0);  // FUN_18071b640 (NQ-44)
    if (candidateSource == null) goto NULL_FAIL;

    // Fill candidateList with type-2 proximity entries
    ProximityData_GetEntriesOfType(candidateSource, candidateList, 2, 0);  // FUN_18073b950
    if (candidateList == null) goto NULL_FAIL;

    // GUARD: no candidates available
    if (candidateList->count == 0)   // +0x18
        return false;

    // Get entityInfo from agentContext
    EntityInfo* entityInfo = self->agentContext->entityInfo;   // agentContext+0x10
    if (entityInfo == null) goto NULL_FAIL;
    List<Actor>* teamMembers = entityInfo->teamMembers;        // entityInfo+0x20

    // Get strategyData sub-object for path cost context
    void* strategyData = strategyInstance->field_0x28;        // strategyInstance+0x28 — inferred StrategyData sub-ref

    // === PHASE 1: Build path lists for each candidate origin tile ===
    // Iterate candidateList
    foreach (ProximityEntry* entry in candidateList)
    {
        if (entry == null || strategyData == null)
            NullReferenceException();

        // Extract tile coordinates from entry (16 bytes at entry+0x10)
        Vector4 tileCoords = entry->tileCoords;   // entry[2] and entry[3]

        // Evaluate tile from these coordinates, fill pathList with TileScore results
        // FUN_1806343a0: path/tile evaluator (NQ-45)
        EvaluateTileFromCoords(strategyData, &tileCoords, pathList, entityFlag == false, 1, 1, 0);

        if (pathList == null)
            NullReferenceException();

        // === Inner loop: process each TileScore in pathList ===
        foreach (TileScore* ts in pathList)
        {
            if (ts == null)
                NullReferenceException();

            // Check tile occupancy
            bool isOccupied = Tile_IsOccupied(ts, 0);   // FUN_1806889c0

            if (!isOccupied)
            {
                // Tile is free — check additional placement conditions
                void* tileData = Tile_GetData(ts, 0);   // FUN_180688600
                if (tileData == null)
                    NullReferenceException();

                bool condA = TileData_CheckConditionA(tileData, 0);   // FUN_180616af0
                if (condA)
                {
                    tileData = Tile_GetData(ts, 0);
                    bool condB = TileData_CheckConditionB(tileData, 0);  // FUN_180616b30
                    if (!condB)
                    {
                        tileData = Tile_GetData(ts, 0);
                        bool condC = TileData_CheckConditionC(tileData, strategy, 0);  // FUN_180616780
                        if (condC)
                        {
                            // Tile passes all conditions — add to tileDict if not already present
                            // FUN_181421d50: check if tileDict already contains this tile
                            if (!tileDict_ContainsTile(tileDict, ts))  // FUN_181421d50
                            {
                                // Create new TileScore entry and add to tileDict
                                void* newEntry = new TileScoreEntry();  // FUN_1804608d0
                                TileScore_Init(newEntry, ts, 0);         // FUN_180741530
                                tileDict_Add(tileDict, ts, newEntry);    // FUN_181446c90
                            }
                        }
                    }
                }
            }
        }

        // Reset pathList for next iteration
        Enumerator_Dispose(&pathListIter);
        pathList->count++;   // +0x1C — list length bookkeeping reset
        // clear backing array if needed: FUN_181b73d10
    }

    Enumerator_Dispose(&candidateListIter);

    // === PHASE 2: Score tiles in tileDict ===
    if (tileDict == null)
        return true;  // no tileDict provided — collection only, no scoring

    WeightsConfig* weights = WeightsConfig_GetInstance();  // DAT_18394c3d0 + 0xb8 + 8

    foreach (TileScore* tileScore in tileDict)
    {
        // --- Range distance penalty ---
        // Iterate candidateList again for each tileDict entry
        foreach (ProximityEntry* entry in candidateList)
        {
            if (entry == null)
                NullReferenceException();

            Vector4 tileCoords = entry->tileCoords;

            // Get distance/count from tile position to candidate
            int distanceResult = ComputeDistance(&tileCoords, pathList, 0);  // FUN_18053feb0 (NQ-46)

            if (tileScore == null || weights == null)
                NullReferenceException();

            // Apply range distance penalty
            // rangeScore -= rangePenaltyScale * distanceResult * secondaryMovementScore
            tileScore->rangeScore -=                          // +0x030
                weights->rangePenaltyScale *                  // weights+0xcc (NQ-47)
                (float)distanceResult *
                tileScore->secondaryMovementScore;            // +0x024
        }
        Enumerator_Dispose(&candidateIter2);

        // --- Ally proximity penalty ---
        if (teamMembers == null)
            NullReferenceException();

        foreach (Actor* ally in teamMembers)
        {
            if (ally == null)
                NullReferenceException();

            // Check inner sub-object at ally[0x19] (Actor field circa +0xC8 area)
            if (ally->field_0xC8 == null)
                NullReferenceException();

            // Only penalise for allies that are currently "set up" (deployed)
            if (ally->field_0xC8->isSetUp != 0)              // ally[0x19] + 0x50 = Actor.isSetUp_alt
            {
                // Get ally's current tile via vtable +0x388
                Tile* allyTile = ally->vtable[0x388](ally);
                if (allyTile == null)
                    NullReferenceException();

                // Get distance between ally tile and candidate position
                int allyDist = Tile_Distance(allyTile, pathList, 0);  // FUN_1805ca7a0 (NQ-49)

                if ((float)allyDist < 6.0f)
                {
                    if (tileScore == null || weights == null)
                        NullReferenceException();

                    // Apply ally proximity penalty (linear falloff over 6 tiles)
                    // rangeScore -= (6 - distance) * allyProximityPenaltyScale
                    tileScore->rangeScore -=                          // +0x030
                        (6.0f - (float)allyDist) *
                        weights->allyProximityPenaltyScale;           // weights+0xd0 (NQ-50)
                }
            }
        }
        Enumerator_Dispose(&teamMembersIter);
    }
    // tileDict iteration loops back — outer do..while(true) with return inside

    return true;  // reached when tileDict enumerator exhausted

NULL_FAIL:
    NullReferenceException();
}
```

### OnCollect — design notes

This is the most complex function in the Deploy class. It has two distinct phases:

**Phase 1** builds the valid tile set. For each type-2 proximity candidate, `FUN_1806343a0` evaluates reachable tiles and fills `pathList`. Each tile in `pathList` is then tested against three placement conditions (`FUN_180616af0`, `FUN_180616b30`, `FUN_180616780`) before being admitted to `tileDict`. The conditions are unanalysed but gate which tiles are structurally valid deploy positions (likely: tile is passable, not in cover that blocks deployment, and reachable from the actor's current position).

**Phase 2** applies the two scoring penalties to each tile in `tileDict`. Both penalties reduce `TileScore.rangeScore` — the range score field accumulates negative adjustments here. The deploy scoring model does not use `utilityScore` or `movementScore` directly; positioning quality is expressed entirely through `rangeScore` modifications.

The `pathList` recycling pattern between Phase 1 iterations (manual count increment + array clear) is a performance optimisation to avoid re-allocating the list per candidate tile.

The outer `do..while(true)` in Phase 2 is Ghidra's representation of a `foreach` loop — the actual exit condition is the `MoveNext()` returning false, which triggers the `return 1` path.
