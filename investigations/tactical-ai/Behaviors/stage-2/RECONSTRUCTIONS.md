# Menace Tactical AI — Behavior/SkillBehavior Subclass — Annotated Reconstructions
# Stage 2

**Source:** Ghidra decompilation of Menace (Windows x64, Unity IL2CPP)
**Image base:** 0x180000000
**Format:** Each function shows raw Ghidra output followed by a fully annotated
C-style reconstruction with all offsets resolved.

---

## Quick-Reference Field Tables

### TileScore
| Offset | Field | Type |
|---|---|---|
| +0x10 | tile | Tile* |
| +0x18 | entity | Entity* |
| +0x20 | movementScore | float |
| +0x24 | secondaryMovementScore | float |
| +0x28 | exposureScore | float |
| +0x2C | rangeScore | float |
| +0x30 | utilityScore | float |
| +0x34 | coverScore | float |
| +0x40 | apCost | int |
| +0x44 | chainCost | int |
| +0x61 | isPeek | bool |
| +0x62 | stance | byte |

### Move
| Offset | Field | Type |
|---|---|---|
| +0x20 | m_IsMovementDone | bool |
| +0x21 | m_HasMovedThisTurn | bool |
| +0x22 | m_HasDelayedMovementThisTurn | bool |
| +0x24 | m_IsAllowedToPeekInAndOutOfCover | bool |
| +0x28 | m_TargetTile | TileScore* |
| +0x30 | m_ReservedTile | Tile* |
| +0x38 | m_TurnsBelowUtilityThreshold | int |
| +0x3C | m_TurnsBelowUtilityThresholdLastTurn | int |
| +0x40 | m_Destinations | List<TileScore>* |
| +0x58 | m_DeployedStanceSkill | Skill* |
| +0x60 | m_DefaultStanceSkill | Skill* |
| +0x68 | m_SetupWeaponSkill | Skill* |
| +0x70 | m_UseSkillBefore | List<Skill>* |
| +0x78 | m_UseSkillBeforeIndex | int |
| +0x80 | m_UseSkillAfter | List<Skill>* |
| +0x88 | m_UseSkillAfterIndex | int |
| +0x8C | m_IsExecuted | bool |
| +0x90 | m_WaitUntil | float |
| +0x94 | m_IsInsideContainerAndInert | bool |
| +0x98 | m_PreviousContainerActor | Actor* |

### WeightsConfig (relevant fields, singleton)
| Offset | Field | Type |
|---|---|---|
| +0x54 | movementScoreWeight | float |
| +0xBC | tagValueScale | float |
| +0x128 | finalMovementScoreScale | float |
| +0x12C | movementWeightScale | float |
| +0x150 | minimumImprovementRatio | float |
| +0x15C | secondaryPathPenalty | float |
| +0x168 | shortRangePenalty | float |
| +0x16C | stanceSkillBonus | float |

### BehaviorWeights (via Strategy+0x310)
| Offset | Field | Type |
|---|---|---|
| +0x14 | movementWeightMultiplier | float |
| +0x20 | movementWeight | float |
| +0x2C | weightScale | float |

### ProximityEntry
| Offset | Field | Type |
|---|---|---|
| +0x10 | tile | Tile* |
| +0x18 | readyRound | int |
| +0x34 | type | int |

---

## 1. ProximityEntry.IsValidType — 0x180717A40

### Raw Ghidra output
```c
bool FUN_180717a40(longlong param_1)
{
  if (*(int *)(param_1 + 0x34) == 0) {
    return true;
  }
  return *(int *)(param_1 + 0x34) == 1;
}
```

### Annotated reconstruction
```c
// Returns true if the entry's type is ground (0) or low (1).
// Type 2+ is excluded from the ally-pressure bonus in GetTargetValue.
bool ProximityEntry_IsValidType(ProximityEntry* self)
{
    int type = self->type;   // +0x34
    return type == 0 || type == 1;
}
```

---

## 2. Deploy/Idle.GetOrder — 0x180519A90

### Raw Ghidra output
```c
undefined8 FUN_180519a90(void)
{
  return 0;
}
```

### Annotated reconstruction
```c
// Deploy and Idle behaviors are scheduling order 0.
// Order 0 = highest priority — these behaviors run before all others.
int GetOrder_ZeroImpl(void) { return 0; }
```

---

## 3. ProximityData.FindEntryForTile — 0x180717730

### Raw Ghidra output
```c
longlong FUN_180717730(longlong param_1, longlong param_2)
{
  longlong lVar1;
  char cVar2;
  undefined8 local_40;
  undefined8 uStack_38;
  longlong local_30;
  undefined4 local_28;
  undefined4 uStack_24;
  undefined4 uStack_20;
  undefined4 uStack_1c;
  longlong local_18;

  if (DAT_183b931b2 == '\0') {
    FUN_180427b00(&DAT_1839ada98);
    FUN_180427b00(&DAT_1839adb50);
    FUN_180427b00(&DAT_1839adc08);
    FUN_180427b00(&DAT_183968278);
    DAT_183b931b2 = '\x01';
  }
  if (*(longlong *)(param_1 + 0x48) != 0) {
    FUN_180cbab80(&local_40,*(longlong *)(param_1 + 0x48),DAT_183968278);
    local_28 = (undefined4)local_40;
    uStack_24 = local_40._4_4_;
    uStack_20 = (undefined4)uStack_38;
    uStack_1c = uStack_38._4_4_;
    local_18 = local_30;
    local_40 = 0;
    uStack_38 = &local_28;
    while( true ) {
      cVar2 = FUN_1814f4770(&local_28,DAT_1839adb50);
      lVar1 = local_18;
      if (cVar2 == '\0') {
        FUN_1804f7ee0(&local_28,DAT_1839ada98);
        return 0;
      }
      if (local_18 == 0) break;
      if (*(longlong *)(local_18 + 0x10) == param_2) {
        FUN_1804f7ee0(&local_28,DAT_1839ada98);
        return lVar1;
      }
    }
    FUN_180427d90();
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Linear scan over ProximityData->entries. Returns matching ProximityEntry* or NULL.
ProximityEntry* ProximityData_FindEntryForTile(ProximityData* self, Tile* targetTile)
{
    // IL2CPP lazy init — omitted
    if (self->entries == NULL) NullReferenceException();   // +0x48

    // foreach (ProximityEntry* entry in self->entries)
    foreach (ProximityEntry* entry in self->entries) {   // List.GetEnumerator + MoveNext
        if (entry == NULL) NullReferenceException();
        if (entry->tile == targetTile) {   // +0x10: pointer equality
            // Enumerator.Dispose — omitted
            return entry;
        }
    }
    // Enumerator.Dispose — omitted
    return NULL;   // not found
}
```

---

## 4. ProximityData.HasReadyEntry — 0x180717870

### Raw Ghidra output
```c
undefined8 FUN_180717870(longlong param_1)
{
  char cVar1;
  undefined8 local_40;
  undefined8 uStack_38;
  longlong local_30;
  undefined4 local_28;
  undefined4 uStack_24;
  undefined4 uStack_20;
  undefined4 uStack_1c;
  longlong local_18;

  if (DAT_183b931b1 == '\0') {
    FUN_180427b00(&DAT_1839ada98);
    FUN_180427b00(&DAT_1839adb50);
    FUN_180427b00(&DAT_1839adc08);
    FUN_180427b00(&DAT_183968278);
    DAT_183b931b1 = '\x01';
  }
  if (*(longlong *)(param_1 + 0x48) != 0) {
    FUN_180cbab80(&local_40,*(longlong *)(param_1 + 0x48),DAT_183968278);
    local_28 = (undefined4)local_40;
    uStack_24 = local_40._4_4_;
    uStack_20 = (undefined4)uStack_38;
    uStack_1c = uStack_38._4_4_;
    local_18 = local_30;
    local_40 = 0;
    uStack_38 = &local_28;
    while( true ) {
      cVar1 = FUN_1814f4770(&local_28,DAT_1839adb50);
      if (cVar1 == '\0') {
        FUN_1804f7ee0(&local_28,DAT_1839ada98);
        return 0;
      }
      if (local_18 == 0) break;
      if (-1 < *(int *)(local_18 + 0x18)) {
        FUN_1804f7ee0(&local_28,DAT_1839ada98);
        return 1;
      }
    }
    FUN_180427d90();
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Returns true if any entry has been assigned to a round (readyRound >= 0).
// readyRound == -1 means the entry slot is unassigned.
bool ProximityData_HasReadyEntry(ProximityData* self)
{
    // IL2CPP lazy init — omitted
    if (self->entries == NULL) NullReferenceException();   // +0x48

    // foreach (ProximityEntry* entry in self->entries)
    foreach (ProximityEntry* entry in self->entries) {
        if (entry == NULL) NullReferenceException();
        if (entry->readyRound >= 0) {   // +0x18: -1 = unassigned, >=0 = assigned round index
            // Enumerator.Dispose — omitted
            return true;
        }
    }
    // Enumerator.Dispose — omitted
    return false;
}
```

---

## 5. SkillBehavior.GetTagValueAgainst — 0x18073BFA0

### Raw Ghidra output
```c
float FUN_18073bfa0(undefined8 param_1, longlong param_2, longlong param_3, char param_4)
{
  float fVar1;
  longlong lVar2;
  char cVar3;
  uint uVar4;
  float fVar5;

  if (DAT_183b931d0 == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    FUN_180427b00(&DAT_1839677b0);
    FUN_180427b00(&DAT_183967868);
    FUN_180427b00(&DAT_18397ae78);
    DAT_183b931d0 = '\x01';
  }
  if (((param_3 != 0) && (*(longlong *)(param_3 + 0x20) != 0)) &&
     (lVar2 = *(longlong *)(*(longlong *)(param_3 + 0x20) + 0x50), lVar2 != 0)) {
    cVar3 = FUN_181421d50(lVar2,param_2,DAT_1839677b0);
    if (cVar3 == '\0') {
      if (param_2 == 0) goto LAB_18073c11f;
      uVar4 = FUN_1806e2400(param_2,*(undefined8 *)(param_3 + 0x10),0);
    }
    else {
      if ((*(longlong *)(param_3 + 0x20) == 0) ||
         (lVar2 = *(longlong *)(*(longlong *)(param_3 + 0x20) + 0x50), lVar2 == 0))
      goto LAB_18073c11f;
      uVar4 = FUN_1814354a0(lVar2,param_2,DAT_183967868);
    }
    if (*(int *)(DAT_18397ae78 + 0xe4) == 0) {
      il2cpp_runtime_class_init(DAT_18397ae78);
    }
    lVar2 = **(longlong **)(DAT_18397ae78 + 0xb8);
    if (lVar2 != 0) {
      if (*(uint *)(lVar2 + 0x18) <= uVar4) {
        FUN_180427d80();
      }
      fVar1 = *(float *)(lVar2 + 0x20 + (longlong)(int)uVar4 * 4);
      if (param_4 == '\0') {
        if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
          il2cpp_runtime_class_init(DAT_18394c3d0);
        }
        lVar2 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
        if (lVar2 == 0) goto LAB_18073c11f;
        fVar5 = *(float *)(lVar2 + 0xbc);
      }
      else {
        fVar5 = 1.0;
      }
      return fVar1 * fVar5 + 1.0;
    }
  }
LAB_18073c11f:
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Returns a multiplicative tag-effectiveness bonus for this skill against 'opponent'.
// Result is always >= 1.0:
//   - No tag match → tableValue ~= 0.0 → returns 0.0 * scale + 1.0 = 1.0 (no effect)
//   - Strong match → tableValue ~= 1.0 → returns 1.0 * scale + 1.0 ≈ 2.0+ (doubles score)
// The bonus is applied as a multiplier in GetTargetValue.
float SkillBehavior_GetTagValueAgainst(
    SkillBehavior* self,       // param_1 (unused beyond dispatch)
    Entity*        opponent,   // param_2
    Goal*          goal,       // param_3
    bool           forImmediateUse)  // param_4
{
    // IL2CPP lazy init — omitted (WeightsConfig, TAG_TYPE_A, TAG_TYPE_B, TagEffectivenessTable)

    // Null-check the goal's entity chain: goal->entityHolder (+0x20) -> entity (+0x50)
    if (goal == NULL || goal->entityHolder == NULL) goto nullfail;
    Entity* goalEntity = goal->entityHolder->entity;   // goal+0x20 -> +0x50
    if (goalEntity == NULL) goto nullfail;

    uint index;

    // Branch on tag category
    bool isTypeA = TagMatcher_IsTypeA(goalEntity, opponent, TAG_TYPE_A_id);  // FUN_181421d50
    if (!isTypeA) {
        // TypeB path: index derived from opponent and goal->field_0x10
        if (opponent == NULL) goto nullfail;
        index = TagMatcher_GetIndexA(opponent, goal->field_0x10, 0);   // FUN_1806e2400
    } else {
        // TypeA path: index derived from goalEntity and opponent
        if (goal->entityHolder == NULL || goalEntity == NULL) goto nullfail;
        index = TagMatcher_GetIndexB(goalEntity, opponent, TAG_TYPE_B_id);  // FUN_1814354a0
    }

    // IL2CPP lazy init for TagEffectivenessTable — omitted
    TagEffectivenessTable* table = TagEffectivenessTable.Instance;   // *(DAT_18397ae78 +0xb8)
    if (table == NULL) goto nullfail;

    // Bounds check
    if (table->length <= index) IndexOutOfRangeException();   // +0x18

    // Index the float array (stride 4, base at +0x20)
    float tableValue = table->values[index];   // *(+0x20 + index * 4)

    // Scale factor: use WeightsConfig.tagValueScale unless this is an immediate-use query
    float scale;
    if (!forImmediateUse) {
        // IL2CPP lazy init for WeightsConfig — omitted
        WeightsConfig* cfg = WeightsConfig.Instance;   // *(DAT_18394c3d0 +0xb8) + 8
        if (cfg == NULL) goto nullfail;
        scale = cfg->tagValueScale;   // +0xBC
    } else {
        scale = 1.0f;   // forImmediateUse bypasses config scaling
    }

    return tableValue * scale + 1.0f;   // always >= 1.0

nullfail:
    NullReferenceException();
}
```

### GetTagValueAgainst — design notes

The `+ 1.0` is architecturally significant. It means the function returns a multiplier
in the range `[1.0, N]` rather than `[0.0, N-1]`. A skill with no tag affinity for the
target does not penalise the score — it simply does not bonus it. This is a conservative
design: tag matching is an upside-only modifier.

The `forImmediateUse` path bypasses `WeightsConfig.tagValueScale`, returning the raw
table value plus 1. This suggests immediate-use queries (e.g. deciding whether to fire
right now) use a stricter, un-scaled effectiveness estimate, while normal scoring uses the
config-adjusted value.

---

## 6. Behavior.GetBehaviorWeights — 0x180738FE0

### Raw Ghidra output
```c
undefined8 FUN_180738fe0(longlong param_1)
{
  longlong *plVar1;
  longlong lVar2;

  if ((*(longlong *)(param_1 + 0x10) != 0) &&
     (plVar1 = *(longlong **)(*(longlong *)(param_1 + 0x10) + 0x18), plVar1 != (longlong *)0x0)) {
    lVar2 = (**(code **)(*plVar1 + 0x398))(plVar1,*(undefined8 *)(*plVar1 + 0x3a0));
    if (lVar2 != 0) {
      return *(undefined8 *)(lVar2 + 0x310);
    }
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Returns the BehaviorWeights object for this behavior.
// Access path: self->agent->actor->GetStrategy()->behaviorWeights
BehaviorWeights* Behavior_GetBehaviorWeights(Behavior* self)
{
    Agent* agent = self->agent;               // +0x10
    if (agent == NULL) goto nullfail;

    Actor* actor = agent->actor;              // +0x18
    if (actor == NULL) goto nullfail;

    Strategy* strategy = actor->GetStrategy();  // vtable +0x398
    if (strategy == NULL) goto nullfail;

    return strategy->behaviorWeights;         // +0x310

nullfail:
    NullReferenceException();
}
```

---

## 7. Behavior.GetBehaviorConfig2 — 0x180739020

### Raw Ghidra output
```c
undefined8 FUN_180739020(longlong param_1)
{
  longlong lVar1;

  if ((*(longlong *)(param_1 + 0x10) != 0) &&
     (lVar1 = *(longlong *)(*(longlong *)(param_1 + 0x10) + 0x10), lVar1 != 0)) {
    return *(undefined8 *)(lVar1 + 0x50);
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Returns the BehaviorConfig2 object for this behavior.
// Access path: self->agent->agentContext->behaviorConfig
// NOTE: reads agent->agentContext (+0x10), NOT agent->actor (+0x18).
BehaviorConfig2* Behavior_GetBehaviorConfig2(Behavior* self)
{
    Agent* agent = self->agent;                    // +0x10
    if (agent == NULL) goto nullfail;

    AgentContext* ctx = agent->agentContext;        // +0x10 (different offset from actor)
    if (ctx == NULL) goto nullfail;

    return ctx->behaviorConfig;                    // +0x50

nullfail:
    NullReferenceException();
}
```

---

## 8. Move.HasUtility — 0x1807632F0

### Raw Ghidra output
```c
undefined8 FUN_1807632f0(undefined8 param_1, longlong param_2)
{
  char cVar1;
  float fVar2;
  undefined8 local_70;
  undefined8 uStack_68;
  undefined8 local_60;
  longlong lStack_58;
  undefined8 local_50;
  undefined8 local_48;
  undefined8 uStack_40;
  undefined8 local_38;
  longlong lStack_30;
  undefined8 local_28;

  if (DAT_183b932e8 == '\0') {
    FUN_180427b00(&DAT_183977938);
    FUN_180427b00(&DAT_18395be38);
    FUN_180427b00(&DAT_18395bef8);
    FUN_180427b00(&DAT_18395bfb0);
    FUN_180427b00(&DAT_18398e1b8);
    DAT_183b932e8 = '\x01';
  }
  fVar2 = (float)FUN_180739050(param_1,0);
  if (param_2 != 0) {
    FUN_18136d8a0(&local_48,param_2,DAT_183977938);
    local_70 = local_48;
    uStack_68 = uStack_40;
    local_60 = local_38;
    lStack_58 = lStack_30;
    local_50 = local_28;
    while( true ) {
      cVar1 = FUN_18152f9b0(&local_70,DAT_18395bef8);
      if (cVar1 == '\0') {
        FUN_1804f7ee0(&local_70,DAT_18395be38);
        return 0;
      }
      if (lStack_58 == 0) break;
      if (fVar2 <= *(float *)(lStack_58 + 0x30)) {
        FUN_1804f7ee0(&local_70,DAT_18395be38);
        return 1;
      }
    }
    FUN_180427d90();
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Returns true if any tile in tileDict has utilityScore >= utilityThreshold.
// If false: movement is "forced" — the actor has no preferred destination.
// When forced, OnEvaluate bypasses the utility threshold filter entirely.
bool Move_HasUtility(Move* self, Dictionary<Tile, TileScore>* tileDict)
{
    // IL2CPP lazy init — omitted
    float threshold = Behavior_GetUtilityThreshold(self);   // FUN_180739050

    if (tileDict == NULL) NullReferenceException();

    // foreach (KeyValuePair<Tile, TileScore> kv in tileDict)
    foreach (kv in tileDict) {   // Dictionary.GetEnumerator + MoveNext
        TileScore* score = kv.value;   // lStack_58 = the TileScore* value
        if (score == NULL) NullReferenceException();

        if (threshold <= score->utilityScore) {   // +0x30
            // Enumerator.Dispose — omitted
            return true;   // found at least one tile worth going to
        }
    }
    // Enumerator.Dispose — omitted
    return false;   // no tile meets the threshold — movement is forced
}
```

### HasUtility — design notes

`HasUtility` returning `false` does NOT mean the actor won't move. It means the movement
becomes unconditional — `OnEvaluate` will still score all tiles and can still return 0 if
the best destination is below the minimum improvement ratio. `HasUtility = false` is a
mode switch, not an abort.

---

## 9. Move.GetHighestTileScore — 0x180762EB0

### Raw Ghidra output
```c
longlong FUN_180762eb0(undefined8 param_1, longlong param_2)
{
  longlong lVar1;
  char cVar2;
  longlong lVar3;
  float fVar4;
  float fVar5;
  undefined8 local_50;
  undefined8 uStack_48;
  longlong local_40;
  undefined4 local_38;
  undefined4 uStack_34;
  undefined4 uStack_30;
  undefined4 uStack_2c;
  longlong local_28;

  if (DAT_183b932e5 == '\0') {
    FUN_180427b00(&DAT_18393e560);
    FUN_180427b00(&DAT_18393e618);
    FUN_180427b00(&DAT_18393e6d0);
    FUN_180427b00(&DAT_18398c990);
    DAT_183b932e5 = '\x01';
  }
  if (param_2 == 0) {
    FUN_180427d90();
  }
  FUN_180cbab80(&local_50,param_2,DAT_18398c990);
  local_38 = (undefined4)local_50;
  uStack_34 = local_50._4_4_;
  uStack_30 = (undefined4)uStack_48;
  uStack_2c = uStack_48._4_4_;
  local_28 = local_40;
  local_50 = 0;
  lVar3 = 0;
  uStack_48 = &local_38;
LAB_180762f53:
  cVar2 = FUN_1814f4770(&local_38,DAT_18393e618);
  lVar1 = local_28;
  if (cVar2 == '\0') {
    FUN_1804f7ee0(&local_38,DAT_18393e560);
    return lVar3;
  }
  if (lVar3 != 0) goto code_r0x000180762f72;
  goto LAB_180762f93;
code_r0x000180762f72:
  if (local_28 == 0) {
    FUN_180427d90();
  }
  fVar4 = (float)FUN_180740f20(local_28,0);
  fVar5 = (float)FUN_180740f20(lVar3,0);
  if (fVar5 < fVar4) {
LAB_180762f93:
    lVar3 = lVar1;
  }
  goto LAB_180762f53;
}
```

### Annotated reconstruction
```c
// Returns the TileScore* with the highest GetScore() value from the candidates list.
// First element is always accepted unconditionally. Subsequent elements replace the
// winner only if their score exceeds the current best.
TileScore* Move_GetHighestTileScore(Move* self, List<TileScore>* candidates)
{
    // IL2CPP lazy init — omitted
    if (candidates == NULL) NullReferenceException();

    TileScore* best = NULL;

    // foreach (TileScore* entry in candidates)
    foreach (TileScore* entry in candidates) {   // List.GetEnumerator + MoveNext
        if (best == NULL) {
            best = entry;   // first element accepted unconditionally
            continue;
        }
        if (entry == NULL) NullReferenceException();

        float entryScore = TileScore_GetScore(entry);   // FUN_180740f20
        float bestScore  = TileScore_GetScore(best);    // FUN_180740f20

        if (bestScore < entryScore) {
            best = entry;   // new winner
        }
    }
    // Enumerator.Dispose — omitted
    return best;
}
```

---

## 10. Move.GetHighestTileScoreScaled — 0x180762D60

### Raw Ghidra output
```c
longlong FUN_180762d60(undefined8 param_1, longlong param_2)
{
  longlong lVar1;
  char cVar2;
  longlong lVar3;
  float fVar4;
  float fVar5;
  undefined8 local_50;
  undefined8 uStack_48;
  longlong local_40;
  undefined4 local_38;
  undefined4 uStack_34;
  undefined4 uStack_30;
  undefined4 uStack_2c;
  longlong local_28;

  if (DAT_183b932e6 == '\0') {
    FUN_180427b00(&DAT_18393e560);
    FUN_180427b00(&DAT_18393e618);
    FUN_180427b00(&DAT_18393e6d0);
    FUN_180427b00(&DAT_18398c990);
    DAT_183b932e6 = '\x01';
  }
  if (param_2 == 0) {
    FUN_180427d90();
  }
  FUN_180cbab80(&local_50,param_2,DAT_18398c990);
  local_38 = (undefined4)local_50;
  uStack_34 = local_50._4_4_;
  uStack_30 = (undefined4)uStack_48;
  uStack_2c = uStack_48._4_4_;
  local_28 = local_40;
  local_50 = 0;
  lVar3 = 0;
  uStack_48 = &local_38;
LAB_180762e03:
  cVar2 = FUN_1814f4770(&local_38,DAT_18393e618);
  lVar1 = local_28;
  if (cVar2 == '\0') {
    FUN_1804f7ee0(&local_38,DAT_18393e560);
    return lVar3;
  }
  if (lVar3 != 0) goto code_r0x000180762e22;
  goto LAB_180762e43;
code_r0x000180762e22:
  if (local_28 == 0) {
    FUN_180427d90();
  }
  fVar4 = (float)FUN_180740e50(local_28,0);
  fVar5 = (float)FUN_180740e50(lVar3,0);
  if (fVar5 < fVar4) {
LAB_180762e43:
    lVar3 = lVar1;
  }
  goto LAB_180762e03;
}
```

### Annotated reconstruction
```c
// Functionally identical to GetHighestTileScore. Uses GetCompositeScore (FUN_180740e50)
// rather than GetScore (FUN_180740f20). Called after score pre-scaling by the caller.
// The "Scaled" name reflects caller intent, not this function's behaviour.
TileScore* Move_GetHighestTileScoreScaled(Move* self, List<TileScore>* candidates)
{
    // IL2CPP lazy init — omitted
    if (candidates == NULL) NullReferenceException();

    TileScore* best = NULL;

    // foreach (TileScore* entry in candidates)
    foreach (TileScore* entry in candidates) {
        if (best == NULL) {
            best = entry;
            continue;
        }
        if (entry == NULL) NullReferenceException();

        float entryScore = TileScore_GetCompositeScore(entry);   // FUN_180740e50
        float bestScore  = TileScore_GetCompositeScore(best);

        if (bestScore < entryScore) {
            best = entry;
        }
    }
    // Enumerator.Dispose — omitted
    return best;
}
```

### GetHighestTileScoreScaled — design notes

The difference between `GetHighestTileScore` (uses `FUN_180740f20`) and
`GetHighestTileScoreScaled` (uses `FUN_180740e50`) is the scoring accessor. `GetScore`
and `GetCompositeScore` are distinct methods on TileScore — the composite score is
presumably a combination of multiple score components, while `GetScore` may return a
single component. Both functions are max-scans; neither scales anything itself.

---

## 11. Move.GetAddedScoreForPath — 0x1807629F0

### Raw Ghidra output
```c
float FUN_1807629f0(undefined8 param_1, longlong param_2, longlong param_3, int param_4)
{
  longlong lVar1;
  char cVar2;
  undefined8 uVar3;
  int iVar4;
  int iVar5;
  float fVar6;
  float fVar7;
  longlong local_res10;
  undefined8 local_68;
  undefined4 local_60;
  undefined8 local_58;
  undefined4 local_50;

  if (DAT_183b932e7 == '\0') {
    FUN_180427b00(&DAT_1839779f8);
    FUN_180427b00(&DAT_183998398);
    FUN_180427b00(&DAT_183998450);
    DAT_183b932e7 = '\x01';
  }
  iVar5 = 0;
  fVar7 = 0.0;
  local_res10 = 0;
  iVar4 = param_4;
  if (param_2 != 0) {
    while( true ) {
      if (*(int *)(param_2 + 0x18) + -1 <= iVar4) {
        if (iVar5 != 0) {
          fVar7 = fVar7 + (fVar7 / (float)(*(int *)(param_2 + 0x18) - param_4)) * (float)iVar5;
        }
        return fVar7;
      }
      if (DAT_183b9233f == '\0') {
        FUN_180427b00(&DAT_183981f50);
        DAT_183b9233f = '\x01';
      }
      if (**(longlong **)(DAT_183981f50 + 0xb8) == 0) break;
      lVar1 = *(longlong *)(**(longlong **)(DAT_183981f50 + 0xb8) + 0x28);
      FUN_180ce3070(&local_68,param_2,iVar4,DAT_183998450);
      if (lVar1 == 0) break;
      local_58 = local_68;
      local_50 = local_60;
      uVar3 = FUN_180633f40(lVar1,&local_58,0);
      if (param_3 == 0) break;
      cVar2 = FUN_181442600(param_3,uVar3,&local_res10,DAT_1839779f8);
      if (cVar2 == '\0') {
        iVar5 = iVar5 + 1;
        iVar4 = iVar4 + 1;
      }
      else {
        if (local_res10 == 0) break;
        if (iVar4 == param_4) {
          fVar6 = 2.0;
        }
        else {
          fVar6 = 1.0;
        }
        fVar7 = fVar7 + (*(float *)(local_res10 + 0x28) + *(float *)(local_res10 + 0x30)) * fVar6;
        iVar4 = iVar4 + 1;
      }
    }
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Accumulates a float score for the path starting at tileList[startIndex].
// For each scored tile: adds (exposureScore + utilityScore) * multiplier.
//   multiplier = 2.0 for the first tile (immediate next step), 1.0 for all others.
// For tiles with no TileScore entry: counts as missing; extrapolated at end.
// Extrapolation: total += total * (missingCount / totalPathTiles)
float Move_GetAddedScoreForPath(
    Move*          self,        // param_1 (unused beyond dispatch)
    TileScoreList* tileList,    // param_2: the path tile list
    TileMap*       tileMap,     // param_3: the agent's tile score dictionary
    int            startIndex)  // param_4: index to start scoring from
{
    // IL2CPP lazy init — omitted
    int   idx          = startIndex;
    float total        = 0.0f;
    int   missingCount = 0;

    if (tileList == NULL) NullReferenceException();

    // Walk path from startIndex to end (tileList->count - 1)
    while (idx <= tileList->count - 1) {   // tileList +0x18 = count
        // IL2CPP lazy init for RoundManager — omitted
        RoundManager* rm = RoundManager.Instance;   // *(DAT_183981f50 +0xb8)
        if (rm == NULL) NullReferenceException();

        // Get the round's current path data object at +0x28
        RoundPathData* roundData = rm->currentRoundPathData;   // rm +0x28

        // Get the Tile at this index in the path list
        // FUN_180ce3070 = TileScoreList.GetTileAt(list, idx, class) → stores in local struct
        // FUN_180633f40 = RoundData.GetTileForEntry(roundData, &coord) → returns Tile*
        TileCoord coord = TileScoreList_GetCoordAt(tileList, idx);
        Tile* tile = RoundData_GetTileForCoord(roundData, &coord);

        if (tileMap == NULL) NullReferenceException();

        // Look up TileScore for this tile
        TileScore* score = NULL;
        bool found = TileMap_TryGet(tileMap, tile, &score);   // FUN_181442600

        if (!found) {
            // No score entry — count as missing for later extrapolation
            missingCount++;
        } else {
            if (score == NULL) NullReferenceException();
            // 2× weight on the first (immediate next) tile; 1× for all others
            float mult = (idx == startIndex) ? 2.0f : 1.0f;
            total += (score->exposureScore + score->utilityScore) * mult;   // +0x28 and +0x30
        }
        idx++;
    }

    // Extrapolate for tiles with no score entry
    if (missingCount > 0) {
        int totalPathTiles = tileList->count - startIndex;
        total += (total / (float)totalPathTiles) * (float)missingCount;
    }
    return total;
}
```

### GetAddedScoreForPath — design notes

The path accumulator uses `exposureScore (+0x28)` and `utilityScore (+0x30)`, not
`movementScore (+0x20)`. This means the path quality bonus rewards tiles that are both
safe (low exposure) and useful (high utility), independently of their movement cost. The
2× first-tile weight ensures the immediate next step dominates the path score — the AI
prefers paths where the first move is already directionally correct, even if later tiles
are unknown.

The missing-tile extrapolation is an optimistic estimate: it assumes unscored tiles will
match the average quality of the scored tiles. This biases the AI slightly toward longer
paths into unexplored territory.

---

## 12. Move.OnEvaluate — 0x1807635C0

### Raw Ghidra output
*(Raw output not reproduced here — ~1,500 lines. Operator has original in
decompiled_functions_2.txt. The full decompilation is archived with this stage.)*

### Annotated reconstruction
```c
// Returns int utility score for the Move behavior. 0 = do not move.
// This is the core movement AI decision function. It:
//   1. Validates all preconditions
//   2. Computes per-tile movement scores
//   3. Selects the best destination
//   4. Returns a final weighted score
int Move_OnEvaluate(Move* self, Actor* actor)
{
    // ── SECTION 1: WEIGHT INITIALISATION ────────────────────────────────────
    // IL2CPP lazy init — omitted (WeightsConfig and many other classes)

    BehaviorWeights* weights = Behavior_GetBehaviorWeights(self);   // FUN_180738FE0
    if (weights == NULL) NullReferenceException();

    // Base weight: per-behavior scale × config movement scale
    float fWeight = weights->weightScale                              // +0x2C
                  * WeightsConfig.Instance->movementWeightScale;     // WeightsConfig +0x12C

    // ── SECTION 2: EARLY-OUT GUARDS ─────────────────────────────────────────
    if (Actor_IsIncapacitated(actor)) return 0;                     // FUN_1805df7e0

    Strategy* strategy = actor->GetStrategy();                       // vtable +0x398
    StrategyData* sd = strategy->strategyData;                       // +0x2B0
    if (Strategy_IsMovementDisabled(sd)) return 0;                  // FUN_1829a91b0; DAT_18394df48

    EntityInfo* info = actor->GetEntityInfo();                       // vtable +0x3D8
    if (info->flags_0xEC & (1 << 2)) return 0;                      // bit 2 = isImmobile

    // Container lock check (deployable actors only)
    if (Actor_CanDeploy(actor)) {                                    // FUN_180616AE0
        Actor* container = actor->field_0xE0;
        if (container != NULL && Container_IsActorLocked(container, actor)) return 0;  // FUN_180616B70
    }

    if (self->m_IsMovementDone)           return 0;                 // +0x20
    if (self->m_IsInsideContainerAndInert) return 0;                // +0x94

    // ── SECTION 3: AP BUDGET ────────────────────────────────────────────────
    int currentAP = actor->GetCurrentAP();                          // vtable +0x458

    // If prone AND deployed-stance skill is available and usable: pre-deduct its cost
    if (actor->GetStance() == 1 &&                                  // vtable +0x468; 1 = prone
        self->m_DeployedStanceSkill != NULL &&                      // +0x58 (NOTE: +0x60 in dump — verify)
        Skill_CanUse(self->m_DeployedStanceSkill)) {                // FUN_1806E3FA0
        currentAP -= Skill_GetAPCost(self->m_DeployedStanceSkill); // FUN_1806DDEC0
    }
    int localAP = currentAP;   // working copy (local_228)

    // Check: AP after reservations must be ≥ 1
    int reservedAP = sd->reservedAP;                                // StrategyData +0x118
    int minimumAP  = info->minimumAP;                               // EntityInfo +0x3C
    if ((localAP - (minimumAP + reservedAP)) < 1) return 0;

    // Deploy AP check
    if (Actor_CanDeploy(actor)) {
        int deployAPCost = EntityInfo_GetDeployAPCost(info);        // FUN_180628230
        if (localAP - deployAPCost < 1) return 0;
    }

    // ── SECTION 4: WEIGHT ADJUSTMENT BY AP AND WEAPON STATE ─────────────────
    // If not yet moved this turn: scale weight by AP ratio (penalises low-AP actors)
    if (!self->m_HasMovedThisTurn) {                                // +0x23
        int maxAP  = EntityInfo_GetMaxAP(info);                     // FUN_1806282A0
        int fullAP = actor->GetCurrentAP();                         // vtable +0x458 (re-read)
        // Adjust for deployed stance skill cost
        // ... (same conditional as Section 3)
        fWeight *= (float)fullAP / (float)maxAP;
    }

    // Weapon not yet set up: 10% weight reduction
    if (actor->isWeaponSetUp) fWeight *= 0.9f;                     // actor +0x167

    // If HasMovedThisTurn is NOT set (bit +0x23 in dump as m_HasMovedThisTurn):
    // compute AP ratio and multiply weight
    // FUN_1806282A0 = EntityInfo.GetMaxAP
    // fWeight *= currentAP / maxAP

    // ── SECTION 5: TILE MAP SETUP ────────────────────────────────────────────
    Tile* currentTile = actor->GetCurrentTile();                    // vtable +0x388
    local_220 = currentTile;

    Agent* agent   = self->agent;                                   // Behavior +0x10
    Dictionary* tileDict = agent->tileDict;                         // Agent +0x60
    if (!TileDict_IsInitialised(tileDict, TileDict_class)) {        // FUN_181372B50
        Log_Warning(LogWarning_string);                             // FUN_182948700
        return 0;
    }

    // ── SECTION 6: FORCED MOVEMENT CHECK ────────────────────────────────────
    bool forced;
    int  stance = actor->GetStance();                               // vtable +0x468
    if (stance == 1) {
        forced = true;   // prone actors always try to move
    } else {
        BehaviorWeights* bw2 = Behavior_GetBehaviorWeights(self);
        BehaviorConfig2* cfg2 = Behavior_GetBehaviorConfig2(self);  // FUN_180739020
        if (bw2->configFlagA && cfg2->configFlagB) {                // configFlagA at BW+?, cfg2+0x28/+0x34
            forced = true;
        } else {
            forced = !Move_HasUtility(self, tileDict);              // FUN_1807632F0
        }
    }

    // ── SECTION 7: UTILITY THRESHOLD AND REFERENCE TILE ─────────────────────
    float threshold = Behavior_GetUtilityThreshold(self);           // FUN_180739050
    float local_1d0 = threshold;   // saved for later comparisons

    // Get TileScore for current tile
    TileScore* currentTileScore = NULL;
    bool hasCurrentScore = TileMap_TryGet(tileDict, currentTile, &currentTileScore);  // FUN_181442600
    // ... (null checks omitted)

    // Track consecutive below-threshold rounds
    if (threshold <= currentTileScore->utilityScore) {             // +0x30
        self->m_TurnsBelowUtilityThreshold = 0;                    // +0x38
    } else {
        // Increment once per round (guard: round must have changed)
        RoundObject* round = RoundManager_GetCurrentRound();        // FUN_180511A50
        if (round->roundIndex != self->m_TurnsBelowUtilityThresholdLastTurn) { // round +0x60
            self->m_TurnsBelowUtilityThreshold++;
            self->m_TurnsBelowUtilityThresholdLastTurn = round->roundIndex; // +0x3C
        }
    }

    // Reserved tile score adjustment
    if (self->m_ReservedTile != NULL) {                            // +0x30
        TileScore* resScore = NULL;
        if (TileMap_TryGet(tileDict, self->m_ReservedTile, &resScore)) {
            resScore->movementScore *= 0.5f;                       // +0x28: halve movement attractiveness
            resScore->utilityScore  += resScore->utilityScore;     // +0x30: double utility (via self-add)
        }
    }

    // ── SECTION 8: REACHABLE TILE SET CONSTRUCTION ──────────────────────────
    // Build reachable set filtered from tileDict for this actor's movement range
    TileScoreList* reachableList = AllocObject(TileScoreReachableList_class);
    TileScoreList_BuildFromDict(reachableList, tileDict, PathGraphParam);  // FUN_1817EDA90
    PathGraph* graph = PathFinder_GetPathGraph(PathFinder_GetInstance());  // FUN_180511630 + FUN_180669480
    TileScoreList_FilterToReachable(reachableList, graph, FilterParam);    // FUN_180CC14C0

    // ── SECTION 9: DESTINATION SCORING LOOP ─────────────────────────────────
    int strategyTierMode = sd->tierMode;                           // StrategyData +0x60
    int apBudget         = localAP / max(minimumAP + reservedAP, 1);

    if (apBudget == 0) return 0;

    // foreach candidate TileScore in m_Destinations
    foreach (TileScore* candidate in self->m_Destinations) {       // +0x40

        // Skip already-scored tiles (+0x40 = apCost, 0 = not yet processed)
        if (candidate->apCost != 0) continue;                      // +0x40
        Tile* candidateTile = candidate->tile;                     // +0x10
        if (candidateTile == currentTile) continue;                // already here

        // Skip low-utility tiles unless forced
        if (!forced) {
            if (threshold > candidate->utilityScore              // +0x30
                && self->m_TurnsBelowUtilityThreshold < 1) {
                continue;
            }
        }

        // Get the goal entity at this tile
        Tile* goalTile = candidate->tile;
        Entity* goalEntity = goalTile->entity;                     // tile +0x70 via accessor
        bool canTarget = Entity_CanBeTargetedBy(goalEntity, actor); // FUN_180740A10

        // Assemble flags bitmask for ComputeMoveCost
        uint flags = 0;
        if (Actor_CanDeploy(actor)) flags |= 2;
        if (!Goal_IsEmpty(goalTile)) flags |= 1;                   // FUN_1806889C0
        if (candidate->isPeek) flags |= 4;                        // +0x61

        // Compute path cost in AP
        // NOTE: FUN_1806361F0 (ComputeMoveCost) — not yet analysed. Returns int AP cost.
        //       Also returns out params: outOriginTile, outFlags.
        Tile* outOriginTile = NULL;
        uint  outFlags      = 0;
        int apCost = StrategyData_ComputeMoveCost(
            sd,
            self->m_Destinations,           // +0x40
            &outOriginTile,
            &outFlags,
            &flags,
            localAP,
            actor,
            currentAP,
            0);                             // FUN_1806361F0

        // Primary tile score formula:
        //   movementScore = movementScoreWeight × (apCost / 20.0) × movementWeight
        if (outOriginTile == candidateTile) {
            candidate->apCost = apCost;                           // +0x40
            float movScoreWeight = WeightsConfig.Instance->movementScoreWeight;  // +0x54
            float movWeight      = weights->movementWeight;        // BehaviorWeights +0x20
            candidate->movementScore = movScoreWeight * ((float)apCost / 20.0f) * movWeight;  // +0x20
            candidate->isPeek = (bool)(flags & 4);                // +0x61

            // Update tile dictionary entry
            TileScore* dictEntry = TileMap_GetOrCreate(tileDict, candidateTile);  // FUN_181446A70
            dictEntry->apCost         = apCost;
            dictEntry->movementScore  = candidate->movementScore;
            dictEntry->isPeek         = candidate->isPeek;

            // Secondary look-ahead: up to 8 adjacent tiles
            for (int adj = 0; adj < 8; adj++) {
                Tile* adjTile = GetAdjacentTile(goalTile, adj);   // FUN_180688690
                if (adjTile == NULL) continue;
                // Skip: bits 0/2 set in adjTile->flags, or Goal.IsEmpty, or is current/candidate tile
                if ((adjTile->flags & 1) || (adjTile->flags & 4)) continue;
                if (Goal_IsEmpty(adjTile)) continue;
                if (adjTile == local_1c0 || adjTile == outOriginTile) continue;

                // Distance and score checks
                int dist = TileDistance(currentTile, adjTile);    // FUN_1805CA7A0
                if (dist > apBudget) continue;

                TileScore* adjScore = NULL;
                if (!TileMap_TryGet(tileDict, adjTile, &adjScore)) continue;

                // Prefer adj tile if its score is within 15% of candidate's AND closer
                float secondaryPenalty = WeightsConfig.Instance->secondaryPathPenalty; // +0x15C
                if (adjScore->exposureScore < candidate->exposureScore ||
                    adjScore->exposureScore == candidate->exposureScore) {
                    // Compute secondary path score with penalty applied
                    adjScore->movementScore = movScoreWeight
                                            * ((float)apCost / 20.0f)
                                            * movWeight
                                            * secondaryPenalty;
                    // 15% tolerance band: prefer closer tile among near-equal scores
                    float delta = ABS(adjScore->exposureScore - candidate->exposureScore)
                                / ABS(candidate->exposureScore);
                    if (delta <= 0.15f) {
                        int adjDist = TileDistance(adjTile, outOriginTile);
                        if (adjDist < dist) {
                            // adj is closer AND within tolerance — prefer it
                            // ... path selection logic
                        }
                    }
                } else {
                    // adj score > candidate score with AP to spare:
                    // apply secondary penalty from WeightsConfig
                    adjScore->movementScore = movScoreWeight
                                           * ((float)apCost / 20.0f)
                                           * movWeight
                                           * secondaryPenalty;
                }
            } // end adjacent look-ahead loop
        }
    } // end destination loop

    // ── SECTION 10: POST-LOOP SCORE ADJUSTMENTS ──────────────────────────────
    // Iterate final candidates, apply modifiers:

    // Short-range penalty: if apCost < maxAP/2
    if (apCost < EntityInfo_GetMaxAP(info) / 2) {
        candidate->coverScore *= WeightsConfig.Instance->shortRangePenalty; // +0x168
    }

    // Chain bonus
    //   if (chainCost (+0x44) + apCost (+0x40) <= localAP):
    //     forward chain (rangeScore (+0x2C) >= 0): coverScore *= 2.0
    //     backward chain (rangeScore < 0):         coverScore *= 0.5
    if (candidate->chainCost + candidate->apCost <= localAP) {
        if (candidate->rangeScore >= 0.0f) {
            candidate->coverScore *= 2.0f;
        } else {
            candidate->coverScore *= 0.5f;
        }
    }

    // Stance skill bonus: if m_DefaultStanceSkill (+0x60) AP fits budget
    if (self->m_DefaultStanceSkill != NULL) {
        int stanceSkillCost = Skill_GetAPCost(self->m_DefaultStanceSkill);
        if (stanceSkillCost + candidate->apCost <= localAP) {
            candidate->coverScore *= WeightsConfig.Instance->stanceSkillBonus; // +0x16C
        }
    }

    // ── SECTION 11: COMPETITOR COMPARISON ───────────────────────────────────
    // (Mode depends on WeightsConfig config field at +0x04)
    // Mode 1: tag-type comparison — not detailed here (see REPORT.md)
    // Mode 2: round-snapshot comparison — caps competitor score at 9000.0 if dominated

    // ── SECTION 12: BEST TILE SELECTION AND VALIDATION ──────────────────────
    TileScore* bestTile = Move_GetHighestTileScoreScaled(self, self->m_Destinations);  // FUN_180762D60

    // Return 0 if best tile is the current tile (no movement needed)
    if (bestTile->tile == currentTile) return 0;                   // +0x10

    // Voluntary movement gate: best must be meaningfully better than current
    if (!forced) {
        float bestScore    = TileScore_GetCompositeScore(bestTile);         // FUN_180740E50
        float currentScore = TileScore_GetCompositeScore(currentTileScore);
        float minRatio     = WeightsConfig.Instance->minimumImprovementRatio; // +0x150
        if (bestScore < currentScore * minRatio) return 0;
    }

    // ── SECTION 13: SCORE SCALING ────────────────────────────────────────────
    float bestExposure    = TileScore_GetCompositeScore(bestTile);
    float currentExposure = TileScore_GetCompositeScore(currentTileScore);

    if (bestExposure == 0.0f) {
        if (forced) {
            // powf-based ratio: max(powf(best/current, exp), 0.33)
            float ratio = powf(bestExposure / currentExposure, exponent);  // FUN_1804BAD80
            fWeight *= max(ratio, 0.33f);
        }
        // else: no voluntary scaling when best score is zero
    } else {
        if (forced) {
            // Forced: use powf ratio with 0.33 floor
            float ratio = powf(bestExposure / currentExposure, exponent);
            fWeight *= max(ratio, 0.33f);
        } else {
            // Voluntary: scale by (best / max(configWeight, currentScore))
            float denominator = max(WeightsConfig.Instance->movementWeightMultiplier, // BW +0x14
                                    currentTileScore->utilityScore);
            if (denominator < currentTileScore->utilityScore)
                denominator = currentTileScore->utilityScore;
            fWeight *= (bestExposure / denominator);
        }
    }

    // ── SECTION 14: PEEK BONUS ───────────────────────────────────────────────
    // If peek allowed and actor has low AP: ×4.0 bonus
    if (self->m_IsAllowedToPeekInAndOutOfCover &&                 // +0x24
        localAP < actor->field_0x14C) {
        fWeight *= 4.0f;
    }

    // ── SECTION 15: DELAYED MOVEMENT HANDLING ────────────────────────────────
    // Prone actors (stance==1): apply reduced penalty for marginally better destinations
    if (actor->GetStance() == 1) {
        if (bestTile->apCost + currentTileScore->chainCost <= localAP &&
            bestTile->utilityScore * 1.1f < currentTileScore->utilityScore &&
            bestTile->exposureScore * 1.1f >= currentTileScore->exposureScore) {
            fWeight *= 0.25f;                                      // marginal move penalty
            self->m_HasDelayedMovementThisTurn = true;             // +0x22
            // Check if delay is permitted by config
            RoundObject* r = RoundManager_GetCurrentRound();
            if (!r->field_0xB8) {
                self->m_IsAllowedToPeekInAndOutOfCover = true;    // +0x23
            }
        }
    } else {
        // Non-prone: if best is barely better than current, strong penalty
        if (bestTile->utilityScore > threshold                     // above threshold
            && bestTile->utilityScore <= currentTileScore->utilityScore * 1.1f) {
            // Compute distance to target
            int distToTarget = TileDistance(currentTile, bestTile->tile);
            if (distToTarget <= 1 ||
                localAP - bestTile->apCost < bestTile->chainCost) {
                // Worth it if close enough or can chain attack after
                float bestUtil    = bestTile->utilityScore;
                float currentUtil = currentTileScore->utilityScore;
                if (currentUtil < threshold) currentUtil = threshold;
                float utilRatio = bestUtil / currentUtil;
                fWeight *= max(utilRatio, 2.0f);
            } else {
                fWeight *= 0.25f;                                  // marginality penalty
            }
        }
    }

    // ── SECTION 16: PEEK DESTINATION / SETUP SKILL SCHEDULING ───────────────
    // If best tile has isPeek set (+0x61) and entity is absent:
    //   add m_UseSkillAfter skill if AP permits
    if (self->m_UseSkillAfter != NULL &&                          // +0x68 (m_SetupWeaponSkill)
        bestTile->apCost + Skill_GetAPCost(self->m_SetupWeaponSkill) <= localAP &&
        bestTile->isPeek) {                                        // +0x61
        if (!actor->field_0x15F) {                                 // not movement-locked
            List_Add(self->m_UseSkillAfter, self->m_SetupWeaponSkill); // FUN_180002590
        }
    }

    // ── SECTION 17: FINAL RETURN ─────────────────────────────────────────────
    // Write selected destination
    self->m_TargetTile = bestTile;                                // +0x28; write barrier applied

    // Final score = accumulated weight × config multiplier, cast to int
    return (int)(fWeight * WeightsConfig.Instance->finalMovementScoreScale); // WeightsConfig +0x128
}
```

### OnEvaluate — design notes

The `/ 20.0` in the tile score formula is the normalisation constant for AP cost. The
game's maximum AP appears to be 20, inferred from `EntityInfo.GetMaxAP()` being the
denominator in the AP ratio weight and from the consistent use of `/ 20.0` in scoring.

The competitor comparison (Section 11) exists to prevent two AI units from converging on
the same tile. When a competitor's path intersects a candidate's planned route and the
competitor has a significantly better score, the candidate's score is capped at 9000.0f
(the float constant `0x460ca000`). This is a very high value rather than a penalty,
suggesting it marks the tile as "already claimed" rather than penalising the movement.

The `m_TurnsBelowUtilityThreshold` counter increments at most once per round (guarded by
`m_TurnsBelowUtilityThresholdLastTurn`). A unit that has been stuck below its utility
threshold for multiple rounds will eventually force movement even without a good
destination.

---

## 13. Move.OnExecute — 0x180766370

### Raw Ghidra output
*(Raw output not reproduced here — ~220 lines. Operator has original in
decompiled_functions_2.txt. The full decompilation is archived with this stage.)*

### Annotated reconstruction
```c
// Movement execution state machine. Called every tick until it returns true.
// Returns false = keep ticking; true = behavior complete.
bool Move_OnExecute(Move* self, Actor* actor)
{
    // ── STAGE 0: REROUTING SETUP ─────────────────────────────────────────────
    // Entered when m_IsMovementDone was set true at the start of this execution cycle.
    // This handles releasing the previously reserved tile and claiming the new target.
    if (self->m_IsMovementDone) {                                  // +0x1C
        // Reset skill-use indices
        self->m_UseSkillBeforeIndex = 0;                           // +0x78
        self->m_UseSkillAfterIndex  = 0;                           // +0x88

        // Release old reserved tile entity claim
        if (self->m_ReservedTile != NULL) {                        // +0x30
            MovementEntity* oldEnt = self->m_ReservedTile->movementEntity; // tile +0x70
            if (oldEnt != NULL) {
                MovementEntity_Release(oldEnt, actor);              // FUN_180740A30
            }
            self->m_ReservedTile = NULL;                           // write barrier
        }

        // Claim new target tile entity
        if (self->m_TargetTile != NULL &&                          // +0x28
            self->m_TargetTile->tile != NULL) {                    // TileScore +0x18 NOTE: +0x10 in table — verify
            self->m_ReservedTile = self->m_TargetTile->tile;      // +0x30; write barrier
            MovementEntity* newEnt = self->m_ReservedTile->movementEntity; // tile +0x70
            if (newEnt != NULL) {
                uint moveCost = TileScore_GetMoveCost(self->m_TargetTile); // FUN_180740F20
                MovementEntity_Claim(newEnt, actor, moveCost);     // FUN_1807409E0
            }
        }

        // Track the previous container actor for Stage 4
        Actor* container = (Actor*)actor->field_0xE0;
        // Type-check: is this actor a ContainerActor type?
        bool isContainerType = IsInstanceOf(container, ContainerActor_class); // vtable type check
        self->m_PreviousContainerActor = isContainerType ? container : NULL;  // +0x98; write barrier
    }

    // ── STAGE 1: USE-SKILL-BEFORE LOOP ─────────────────────────────────────
    // Consume m_UseSkillBefore one skill per tick, before moving.
    if (self->m_UseSkillBefore != NULL &&                          // +0x70
        self->m_UseSkillBeforeIndex < self->m_UseSkillBefore->count) {  // +0x78
        Skill* skill    = self->m_UseSkillBefore[self->m_UseSkillBeforeIndex]; // List[idx]
        Tile*  currTile = actor->GetCurrentTile();                 // vtable +0x388

        Skill_Use(skill, currTile, 0x10);                          // FUN_1806E80B0; flags=0x10

        // Check movement state and target alignment
        bool isMoving = Actor_IsMoving(actor, currTile);           // FUN_1805DFD80
        if (!isMoving ||
            (!Actor_IsAtTargetTile(actor, self->m_TargetTile->tile) &&    // FUN_1805DFD80 second call
             self->m_TargetTile->tile != actor->GetCurrentTile())) {
            // Not yet arrived — set a timer or signal behavior system
            if (self->agent->behavior != NULL) {
                Behavior_SetTimer(self->agent->behavior, 0x40000000);  // FUN_18071CC10; large timer
            } else {
                self->m_WaitUntil = Time_time() + 2.0f;           // FUN_1829B1320
            }
        }
        self->m_UseSkillBeforeIndex++;                             // +0x78
        return false;   // not done — tick again
    }

    // ── STAGE 2: TIMER WAIT / MOVEMENT TRIGGER ─────────────────────────────
    if (!self->m_IsExecuted) {                                     // +0x8C
        float now = Time_time();                                   // FUN_1829B1320
        if (now <= self->m_WaitUntil) {                           // +0x90
            return false;   // wait — timer not expired
        }

        // Timer expired — trigger movement
        self->m_IsExecuted    = true;                              // +0x8C
        self->m_IsMovementDone = true;                             // +0x20
        self->m_HasMovedThisTurn = true;                           // +0x21 (writes 0x101 to +0x20 word)

        if (self->m_TargetTile->tile != actor->GetCurrentTile()) {
            // Assemble StartMove flags
            uint flags = 0;
            if (Actor_CanDeploy(actor))                  flags |= 2;  // FUN_180616AE0
            if (!Goal_IsEmpty(self->m_TargetTile->tile)) flags |= 1;  // FUN_1806889C0
            if (self->m_TargetTile->isPeek)              flags |= 4;  // TileScore +0x61

            Actor_StartMove(actor, self->m_TargetTile->tile, flags);  // FUN_1805E03B0
            // Write stance-on-arrival from TileScore
            // actor->arrivalStance = self->m_TargetTile->stance;   // TileScore +0x62
        }
        // If not executed yet after assignment: return false and wait for next tick
        if (!self->m_IsExecuted) return false;
    }

    // ── STAGE 3: USE-SKILL-AFTER LOOP ──────────────────────────────────────
    // Consume m_UseSkillAfter one skill per tick, after moving.
    if (!actor->field_0x15F) {                                     // movement-locked flag
        if (self->m_UseSkillAfter != NULL &&                       // +0x80
            self->m_UseSkillAfterIndex < self->m_UseSkillAfter->count) { // +0x88
            Skill* skill    = self->m_UseSkillAfter[self->m_UseSkillAfterIndex]; // List[idx]
            Tile*  currTile = actor->GetCurrentTile();             // vtable +0x3E8 (1000)

            bool ok = Skill_Activate(skill, currTile);             // FUN_1806F3C30
            if (!ok) return false;                                 // activation failed — wait

            self->m_UseSkillAfterIndex++;                          // +0x88
            // loop continues next tick
        }
    }

    // ── STAGE 4: CONTAINER EXIT / FINAL ACTIVATION ─────────────────────────
    if (self->m_IsExecuted) {
        // Container exit path
        if (!actor->field_0x15F &&                                 // not locked
            self->m_PreviousContainerActor != NULL &&              // +0x98
            self->m_PreviousContainerActor->field_0x4C != 0) {    // container has living HP/slot

            if (Actor_CanDeploy(actor)) {
                // Broadcast container-exit event to the event system
                Object* evt = FUN_1819C8600(ContainerExitEventId,
                                            actor->field_0x11,
                                            ContainerExitEvent_class);
                FUN_182948700(evt);                                // broadcast
                ContainerActor_Notify(self->m_PreviousContainerActor, 1);  // FUN_1805E76F0
                return true;   // done
            } else {
                // Non-deployable container exit
                ContainerActor_Notify(self->m_PreviousContainerActor, 1);
                Strategy* cs = self->m_PreviousContainerActor->GetStrategy(); // vtable +0x398
                if (cs->field_0xE0 != '\0') {
                    cs->strategyData2->field_0x78 = 1;            // mark strategy slot complete
                }
                return true;   // done
            }
        }

        // Final activation — not container exit
        if (actor == NULL) goto nullfail;
        Tile* finalTile = actor->GetCurrentTile();                 // vtable +0x3E8
        bool ok = Skill_Activate(finalTile);                       // FUN_1806F3C30
        if (!ok) return false;
        return actor->field_0x15F == 0;                            // true if not locked
    }

    return false;

nullfail:
    NullReferenceException();
}
```

### OnExecute — design notes

`actor->field_0x15F` appears throughout OnExecute as a "movement locked" flag. When set,
the UseSkillAfter loop is skipped entirely and the final `Skill.Activate` return is forced
to false. This likely represents server-authority movement lock or a physics constraint.

The two vtable slots for `GetCurrentTile` (`+0x388` in Stage 2 and `+0x3E8` / decimal 1000
in Stages 3–4) were observed in Stage 1 as well. The alternate slot at `+0x3E8` may return
the tile the actor is physically occupying after movement completes, while `+0x388` returns
the logical/assigned tile. Both slots were confirmed to return `Tile*`.

The `0x40000000` passed to `Behavior_SetTimer` is a very large integer (~1 billion). As a
timer duration, this effectively means "wait indefinitely" — it is used when a before-move
skill triggers a state that requires waiting for an external signal rather than a time
expiry.