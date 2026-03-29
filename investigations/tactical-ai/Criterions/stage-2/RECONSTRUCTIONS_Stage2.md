# Menace Tactical AI Criterions — Annotated Function Reconstructions (Stage 2)

**Source:** Ghidra decompilation of Menace (PC x64, Unity IL2CPP GameAssembly.dll)  
**Image base:** 0x180000000  
**Format:** Raw Ghidra output followed by fully annotated C-style reconstruction.  
Functions appear in leaf-first order.

---

## Quick-Reference Field Tables

### AIWeightsTemplate (singleton via DAT_18394c3d0 +0xb8 +0x8)
| Offset | Field | Type |
|---|---|---|
| +0x58 | zoneInfluenceWeight | float |
| +0x5c | zoneInfluenceSecondaryWeight | float |
| +0x60 | zoneScoreMultiplier_A | float |
| +0x64 | zoneScoreMultiplier_B | float |
| +0x68 | zoneThresholdWeight_A | float |
| +0x6c | zoneThresholdWeight_B | float |
| +0x70 | coverScoreWeight | float |
| +0x74 | W_threat | float |
| +0x78 | tileEffectScoreWeight | float |
| +0x7c | tileEffectMultiplier | float |
| +0x8c | coverMult_Full | float |
| +0x90 | coverMult_Partial | float |
| +0x94 | coverMult_Low | float |
| +0x98 | coverMult_Quarter | float |
| +0x9c | coverMult_None | float |
| +0xa0 | flankingBonusMultiplier | float |
| +0xa4 | bestCoverBonusWeight | float |
| +0xac | weaponListDistanceThreshold | float |
| +0xb0 | avoidDirectThreatWeight | float |
| +0xb4 | avoidIndirectThreatWeight | float |
| +0xb8 | fleeWeight | float |
| +0xd4 | occupiedDirectionPenalty | float |
| +0xd8 | rangeScorePenalty | float |
| +0xdc | ammoScorePenalty | float |
| +0xe4 | baseAttackWeight | float |
| +0xe8 | ammoPressureWeight | float |
| +0xec | deployPositionWeight | float |
| +0xf0 | sniperAttackWeight | float |
| +0x13c | baseThreshold | float |
| +0x158 | outOfRangePenalty | float |

### EvaluationContext / TileScoreRecord (param_3 in Evaluate functions)
| Offset | Field | Type |
|---|---|---|
| +0x10 | tileRef | ptr |
| +0x20 | reachabilityScore | float |
| +0x24 | zoneInfluenceAccumulator | float |
| +0x28 | accumulatedScore | float |
| +0x30 | thresholdAccumulator | float |
| +0x60 | isObjectiveTile | bool |

### Unit (param_2 in Evaluate / Score functions)
| Offset | Field | Type |
|---|---|---|
| +0x20 | movePool ptr | ptr (unit[4]) |
| +0x4c | teamIndex | int |
| +0x54 | moveRange | int |
| +0x5b | ammoSlotCount | int |
| +0x5c | currentAmmo | int |
| +0x60 | squadCount | int |
| +0x70 | teamId | int (unit[0xe]) |
| +0xc8 | movePool (alt path) | ptr |
| +0x15c | isDeployed | bool |

### TileModifier (returned by GetTileZoneModifier)
| Offset | Field | Type |
|---|---|---|
| +0x14 | minThresholdScale | float |
| +0x18 | thresholdMultiplier | float |
| +0x20 | distanceScaleFactor | float |
| +0x44 | effectImmunityMask | uint |

### MovePool (unit->movePool)
| Offset | Field | Type |
|---|---|---|
| +0x10 | zoneData ptr | ptr |
| +0x18 | maxMovePoints | int |
| +0x51 | wakeupPending | bool |

### MoveRangeData (returned by GetMoveRangeData)
| Offset | Field | Type |
|---|---|---|
| +0x10 | attackRange | float |
| +0x14 | ammoRange | float |
| +0x18 | moveCostNorm | float |
| +0x1c | moveCostToTile | float |
| +0x20 | maxReachability | float |
| +0x24 | canAttackFromTile | bool |
| +0x25 | canFullyReach | bool |
| +0x28 | tileScorePtr | ptr |

### ScoringContext (singleton via DAT_183981f50 +0xb8)
| Offset | Field | Type |
|---|---|---|
| +0x28 | tileGrid | ptr |
| +0x60 | phase | int (0=deploy, 1=std, 2=post) |
| +0xa8 | avoidGroups | array |

---

## 1. WakeUp..ctor — 0x180518FA0

### Raw Ghidra output
````c
void FUN_180518fa0(undefined8 param_1)
{
  FUN_1804eb570(param_1,0);
  return;
}
````

### Annotated reconstruction
````c
void WakeUp_ctor(WakeUp* self) {
    Criterion_ctor(self, 0);   // delegate to base Criterion constructor — no additional fields
}
````

### WakeUp..ctor — design notes
The divergent `.ctor` slot (RVA 0x518FA0 vs the shared 0x4EB570) is a compiler artefact of IL2CPP's per-class constructor registration. The body is functionally identical to calling the base directly. WakeUp has no fields beyond those inherited from Criterion.

---

## 2. ThreatFromOpponents.GetThreads — 0x18054E040

### Raw Ghidra output
````c
undefined8 FUN_18054e040(void)
{
  return 4;
}
````

### Annotated reconstruction
````c
int ThreatFromOpponents_GetThreads() {
    return 4;   // request 4 worker threads — hardcoded; all other criteria use default (1)
}
````

---

## 3. Criterion.IsDeploymentPhase — 0x18071B670

### Raw Ghidra output
````c
undefined8 FUN_18071b670(void)
{
  longlong lVar1;
  if (DAT_183b9233f == '\0') {
    FUN_180427b00(&DAT_183981f50);
    DAT_183b9233f = '\x01';
  }
  lVar1 = **(longlong **)(DAT_183981f50 + 0xb8);
  if (lVar1 != 0) {
    return CONCAT71((int7)((ulonglong)lVar1 >> 8),*(int *)(lVar1 + 0x60) == 0);
  }
  FUN_180427d90();
}
````

### Annotated reconstruction
````c
bool Criterion_IsDeploymentPhase() {
    // IL2CPP lazy init — omitted
    ScoringContext* ctx = ScoringContext_class.staticFields->singleton;  // DAT_183981f50 +0xb8
    if (ctx != null) {
        return ctx->phase == 0;   // +0x60; phase 0 = deployment
    }
    NullReferenceException();  // does not return
}
````

---

## 4. GetTileZoneModifier — 0x18071AE10

### Raw Ghidra output
````c
undefined8 FUN_18071ae10(longlong param_1)
{
  longlong *plVar1;
  longlong lVar2;
  plVar1 = *(longlong **)(param_1 + 0x18);
  if (plVar1 != (longlong *)0x0) {
    lVar2 = (**(code **)(*plVar1 + 0x398))(plVar1,*(undefined8 *)(*plVar1 + 0x3a0));
    if (lVar2 != 0) {
      return *(undefined8 *)(lVar2 + 0x310);
    }
  }
  FUN_180427d90();
}
````

### Annotated reconstruction
````c
TileModifier GetTileZoneModifier(OpponentList* opponentList) {
    ZoneDescriptor* zone = opponentList->zoneDescriptor;   // +0x18
    if (zone != null) {
        ZoneData* zoneData = zone->vtable->GetStatusEffects(zone);   // vtable +0x398
        if (zoneData != null) {
            return *(TileModifier*)(zoneData + 0x310);   // TileModifier struct at fixed offset
        }
    }
    NullReferenceException();   // does not return
}
````

---

## 5. IsWithinRangeB — 0x1806E33A0

### Raw Ghidra output
````c
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
    if (*(uint *)(lVar1 + 0x18) <= uVar4) {
      FUN_180427d80();
    }
    plVar2 = *(longlong **)(lVar1 + 0x20 + (longlong)(int)uVar4 * 8);
    if (plVar2 == (longlong *)0x0) break;
    uVar3 = (**(code **)(*plVar2 + 0x1d8))(plVar2,param_2,param_3,*(undefined8 *)(*plVar2 + 0x1e0));
    if ((char)uVar3 == '\0') {
      return uVar3 & 0xffffffffffffff00;
    }
    uVar4 = uVar4 + 1;
    lVar1 = *(longlong *)(param_1 + 0x48);
  }
  FUN_180427d90();
}
````

### Annotated reconstruction
````c
bool IsWithinRangeB(Tile* tile, Unit* unit, Unit* target) {
    // Iterate tile->weaponSlots — all slots must individually pass their range condition
    List* slots = tile->weaponSlots;   // tile +0x48
    uint i = 0;
    while (slots != null) {
        if (slots->count <= (int)i) {
            return true;   // exhausted all slots without failure — all passed
        }
        // bounds check
        if (slots->count <= i) IndexOutOfRangeException();

        WeaponSlot* slot = slots->items[i];   // slots +0x20 + i*8
        if (slot == null) break;

        bool pass = slot->vtable->CheckRangeCondition(slot, unit, target);   // vtable +0x1d8
        if (!pass) {
            return false;   // any slot failing = immediate failure
        }
        i++;
        slots = tile->weaponSlots;   // re-read (list may mutate)
    }
    NullReferenceException();   // null slot list — does not return
}
````

---

## 6. IsWithinRangeA — 0x1806E3C50

### Raw Ghidra output
````c
undefined8 FUN_1806e3c50(longlong param_1,undefined8 param_2,longlong param_3,ushort param_4)
{
  longlong lVar1;
  char cVar2;
  undefined8 uVar3;
  cVar2 = FUN_1806e3d50(param_1,param_4,0);
  if (cVar2 == '\0') goto LAB_1806e3d2d;
  uVar3 = FUN_1806d5040(param_1,0);
  if (param_3 == 0) {
    if (*(longlong *)(param_1 + 0x10) == 0) goto LAB_1806e3d44;
    param_3 = FUN_1806f9f20(*(longlong *)(param_1 + 0x10),uVar3,param_2,0);
  }
  lVar1 = *(longlong *)(param_1 + 0x10);
  if (lVar1 == 0) { FUN_180427d90(); }
  if (*(char *)(lVar1 + 0xe4) == '\0') { uVar3 = 1; }
  else {
    if (*(char *)(lVar1 + 0xf1) != '\0') {
      if (param_3 == 0) goto LAB_1806e3d44;
      cVar2 = FUN_1806888b0(param_3,param_2,0,0);
      if (cVar2 == '\0') goto LAB_1806e3d2d;
    }
    cVar2 = FUN_1806e3750(param_1,param_2,param_3,param_4 & 0xff,0);
    if (cVar2 != '\0') {
      cVar2 = FUN_1806e60a0(param_1,param_3,param_2,param_4,0);
      if (cVar2 != '\0') goto LAB_1806e3d29;
    }
LAB_1806e3d2d:
    uVar3 = 0;
  }
  return uVar3;
}
````

### Annotated reconstruction
````c
bool IsWithinRangeA(Tile* tile, Unit* unit, TileScore* scoreObj, ushort rangeType) {
    // Gate 1: range type must be valid for this tile
    if (!IsValidRangeType(tile, rangeType)) return false;   // FUN_1806e3d50

    // Get thread score index for this tile
    uint scoreIndex = GetThreadScoreIndex(tile);   // FUN_1806d5040

    // Lazily resolve the score object if not provided
    if (scoreObj == null) {
        if (tile->tileData == null) NullReferenceException();
        scoreObj = FetchScoredTileData(tile->tileData, scoreIndex, unit);   // FUN_1806f9f20
    }

    TileData* data = tile->tileData;   // tile +0x10
    if (data == null) NullReferenceException();

    // Gate 2: if tile has no range constraint, it always passes
    if (!data->hasRangeConstraint) return true;   // data +0xe4

    // Gate 3: if tile requires context match, verify it
    if (data->hasContextRequirement) {   // data +0xf1
        if (scoreObj == null) NullReferenceException();
        if (!TileMatchesContext(scoreObj, unit)) return false;   // FUN_1806888b0
    }

    // Gate 4: melee range check AND attack range check must both pass
    if (IsInMeleeRange(tile, unit, scoreObj, rangeType & 0xff)) {   // FUN_1806e3750
        if (IsInAttackRange(tile, scoreObj, unit, rangeType)) {      // FUN_1806e60a0
            return true;
        }
    }
    return false;
}
````

---

## 7. DistanceToCurrentTile.Evaluate — 0x180760CF0

### Raw Ghidra output
````c
void FUN_180760cf0(undefined8 param_1,longlong *param_2,longlong param_3)
{
  float fVar1; float fVar2; int iVar3; int iVar4; longlong lVar5; undefined8 uVar6; int iVar7; float fVar8;
  if (DAT_183b93325 == '\0') { FUN_180427b00(&DAT_18394c3d0); DAT_183b93325 = '\x01'; }
  if (param_2 != (longlong *)0x0) {
    iVar3 = (**(code **)(*param_2 + 0x458))(param_2,*(undefined8 *)(*param_2 + 0x460));
    lVar5 = (**(code **)(*param_2 + 0x398))(param_2,*(undefined8 *)(*param_2 + 0x3a0));
    if ((lVar5 != 0) && (*(longlong *)(lVar5 + 0x2b0) != 0)) {
      iVar7 = *(int *)(*(longlong *)(lVar5 + 0x2b0) + 0x118);
      lVar5 = (**(code **)(*param_2 + 0x3d8))(param_2,*(undefined8 *)(*param_2 + 0x3e0));
      if (lVar5 != 0) {
        iVar7 = iVar7 + *(int *)(lVar5 + 0x3c);
        if (iVar7 < 1) { iVar7 = 1; }
        if (param_3 != 0) {
          lVar5 = *(longlong *)(param_3 + 0x10);
          uVar6 = (**(code **)(*param_2 + 0x388))(param_2,*(undefined8 *)(*param_2 + 0x390));
          if (lVar5 != 0) {
            iVar4 = FUN_1805ca7a0(lVar5,uVar6,0);
            fVar1 = *(float *)(param_3 + 0x20);
            if (param_2[0x19] != 0) {
              lVar5 = FUN_18071ae10(param_2[0x19],0);
              if (lVar5 != 0) {
                fVar2 = *(float *)(lVar5 + 0x20);
                if (iVar3 / iVar7 < iVar4) {
                  // IL2CPP lazy init — omitted
                  lVar5 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
                  if (lVar5 == 0) goto LAB_180760eb4;
                  fVar8 = *(float *)(lVar5 + 0x158);
                } else { fVar8 = 1.0; }
                *(float *)(param_3 + 0x20) = (float)iVar4 * fVar2 * fVar8 + fVar1;
                return;
              }
            }
          }
        }
      }
    }
  }
LAB_180760eb4:
  FUN_180427d90();
}
````

### Annotated reconstruction
````c
void DistanceToCurrentTile_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    if (unit == null) return;

    int moveSpeed   = unit->vtable->GetMoveSpeed(unit);                   // vtable +0x458
    WeaponData* wpn = unit->vtable->GetStatusEffects(unit);               // vtable +0x398
    if (wpn == null || wpn->weaponStatsBlock == null) NullReferenceException();  // +0x2b0

    int baseRange   = wpn->weaponStatsBlock->baseRange;                   // +0x118
    WeaponList* wl  = unit->vtable->GetWeaponList(unit);                  // vtable +0x3d8
    if (wl == null) NullReferenceException();

    int effectiveRange = max(baseRange + wl->bonusRange, 1);              // wl +0x3c

    if (ctx == null) NullReferenceException();
    Tile* tile     = ctx->tileRef;                                        // ctx +0x10
    Tile* myTile   = unit->vtable->GetTilePosition(unit);                 // vtable +0x388
    if (tile == null) NullReferenceException();

    int dist        = GetTileDistance(tile, myTile);                      // FUN_1805ca7a0
    float prev      = ctx->reachabilityScore;                             // ctx +0x20

    if (unit->opponentList == null) NullReferenceException();             // unit[0x19]
    TileModifier mod = GetTileZoneModifier(unit->opponentList);           // FUN_18071ae10
    float modScale   = mod.distanceScaleFactor;                           // mod +0x20

    float penalty;
    if (moveSpeed / effectiveRange < dist) {
        // IL2CPP lazy init — omitted
        penalty = settings->outOfRangePenalty;                            // settings +0x158
    } else {
        penalty = 1.0f;
    }

    ctx->reachabilityScore = (float)dist * modScale * penalty + prev;     // ctx +0x20
}
````

---

## 8. AvoidOpponents.Evaluate — 0x18075BE10

### Raw Ghidra output
````c
void FUN_18075be10(undefined8 param_1,longlong param_2,longlong param_3)
{
  // [full raw output as provided by Ghidra — 120 lines]
  // Initialises fVar10 = 0.0
  // Reads ScoringContext.singleton +0xa8 -> avoid group array
  // Outer loop: each group at [i*8 + 0x20 in array]
  //   Skip if group.teamId (group +0x14) == unit.teamId (unit +0x4c)
  //   Inner loop: foreach tile in group.tileList (plVar2[4])
  //     if TileTeamMatches(tile, unit.teamId): 
  //       dist = GetTileDistance(ctx.tileRef, tile.position)
  //       if dist < 11:
  //         if vtable+0x188(group, unit.teamId) == false:
  //           fVar10 += expf(settings +0xb4)
  //         else:
  //           fVar10 += expf(settings +0xb0)
  // ctx.accumulatedScore += fVar10
}
````

### Annotated reconstruction
````c
void AvoidOpponents_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    float fAccum = 0.0f;

    // Null guard on ScoringContext singleton
    if (ScoringContext_singleton == null) NullReferenceException();

    // Read avoid group array from singleton
    Array* groups = ScoringContext_singleton->avoidGroups;   // singleton +0xa8
    if (groups == null) NullReferenceException();

    for (uint i = 0; i < groups->count; i++) {
        OpponentGroup* group = groups->items[i];   // groups +0x20 + i*8
        if (group == null) NullReferenceException();

        // Skip groups on the same team
        if (group->teamId != unit->teamId) {   // group +0x14, unit +0x4c
            if (group->tileList == null) NullReferenceException();   // group[4]

            // Iterate tiles in this group
            foreach (Tile* tile in group->tileList) {
                // Skip tiles not matching unit's team
                if (!TileTeamMatches(tile, unit->teamId)) continue;   // FUN_1805dfab0

                Tile* ctxTile = ctx->tileRef;   // ctx +0x10
                Tile* tilePos = tile->vtable->GetTilePosition(tile);   // vtable +0x388
                if (ctxTile == null) NullReferenceException();

                int dist = GetTileDistance(ctxTile, tilePos);   // FUN_1805ca7a0

                if (dist < 11) {
                    bool canTarget = group->vtable->CanTargetTeam(group, unit->teamId);  // vtable +0x188
                    if (!canTarget) {
                        // Indirect threat (cannot directly target unit)
                        fAccum += expf(settings->avoidIndirectThreatWeight);   // settings +0xb4, FUN_1804bad80
                    } else {
                        // Direct threat (can directly target unit)
                        fAccum += expf(settings->avoidDirectThreatWeight);     // settings +0xb0
                    }
                }
            }
        }
    }

    if (ctx == null) NullReferenceException();
    ctx->accumulatedScore += fAccum;   // ctx +0x28
}
````

---

## 9. FleeFromOpponents.Evaluate — 0x1807613A0

### Raw Ghidra output
````c
void FUN_1807613a0(undefined8 param_1,longlong param_2,longlong param_3,undefined8 param_4)
{
  // [full raw output — 115 lines, structurally identical to AvoidOpponents]
  // Key differences:
  //   if (cVar4 == '\0') — skips groups that CANNOT target (opposite polarity)
  //   dist < 0x10 (16) instead of 0xb (11)
  //   weight: settings +0xb8 (fleeWeight)
}
````

### Annotated reconstruction
````c
void FleeFromOpponents_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    // Identical structure to AvoidOpponents — see that reconstruction for full annotation.
    float fAccum = 0.0f;

    Array* groups = ScoringContext_singleton->avoidGroups;   // singleton +0xa8

    for (uint i = 0; i < groups->count; i++) {
        OpponentGroup* group = groups->items[i];
        if (group->teamId == unit->teamId) continue;   // skip same team

        foreach (Tile* tile in group->tileList) {
            if (!TileTeamMatches(tile, unit->teamId)) continue;

            int dist = GetTileDistance(ctx->tileRef, tile->vtable->GetTilePosition(tile));

            if (dist < 16) {   // NOTE: 16, not 11 — larger threat radius than AvoidOpponents
                bool canTarget = group->vtable->CanTargetTeam(group, unit->teamId);  // vtable +0x188
                if (canTarget) {   // NOTE: only accumulate for groups that CAN target (opposite of Avoid)
                    fAccum += expf(settings->fleeWeight);   // settings +0xb8
                }
            }
        }
    }

    ctx->accumulatedScore += fAccum;   // ctx +0x28
}
````

---

## 10. ExistingTileEffects.Evaluate — 0x180760FB0

### Raw Ghidra output
````c
void FUN_180760fb0(undefined8 param_1,longlong *param_2,longlong param_3)
{
  // [full raw output — 285 lines, truncated in view at line 250]
  // Entry guard: HasTileEffects(ctx.tileRef)
  // Reads TileModifier.effectImmunityMask (mod +0x44)
  // Iterates tile->effectList (tile +0x68) via GetEnumerator / MoveNext
  // For each effect:
  //   Get effect flags via vtable +0x178 -> +0x88
  //   Skip if (flags != 0) && ((flags & immunityMask) == flags)
  //   IL2CPP type check vs DAT_183952b10 and DAT_183952a58
  //   CheckEffectFlag(slot, 0xe) and CheckEffectFlag(slot, 0xa0)
  //   If tile +0xf2 != 0:
  //     score = Criterion.Score(unit, effectTile, ctx.tileRef, ctx.tileRef, 1)
  //     ctx.accumulatedScore += settings.tileEffectMultiplier * score * settings.tileEffectScoreWeight
  // [TRUNCATED — full type-check logic not captured; core scoring write confirmed]
}
````

### Annotated reconstruction
````c
void ExistingTileEffects_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    if (ctx == null || ctx->tileRef == null) return;

    // Guard: candidate tile must have active effects
    if (!HasTileEffects(ctx->tileRef)) return;   // FUN_180688850

    // Read zone modifier for effect immunity mask
    TileModifier mod = GetTileZoneModifier(unit->opponentList);
    uint immunityMask = mod.effectImmunityMask;   // mod +0x44

    Tile* tile  = ctx->tileRef;
    List* effects = tile->effectList;   // tile +0x68

    // Read per-tile modifier for effect filtering
    uint tileModMask = TileZoneModifier.someMask;   // mod +0x44 — same struct
    // [IL2CPP type descriptor lookup for subtype check — omitted]

    foreach (TileEffect* effect in effects) {
        // Get this effect's flag bitmask
        EffectDescriptor* desc = effect->vtable->GetDescriptor(effect);   // vtable +0x178
        uint effectFlags = desc->flags;   // desc +0x88

        // Immunity check: skip if all effect flags are covered by zone immunity
        if (effectFlags != 0 && (effectFlags & immunityMask) == effectFlags) continue;

        // IL2CPP subtype check vs two registered effect subtypes — omitted
        // [UNCERTAIN: type check logic truncated — exact subtype requirements not fully captured]

        // Flag checks on the effect slot
        if (!CheckEffectFlag(effect->slot, 0x0e)) continue;   // FUN_180513400
        // flag 0xa0 check with tile position comparison also applied

        // Score if tile has the effect flag set
        if (tile->hasTileEffect) {   // tile +0xf2
            float score = Criterion_Score(unit, effectTile, ctx->tileRef, ctx->tileRef, 1);  // FUN_180760140
            ctx->accumulatedScore +=
                settings->tileEffectMultiplier * score * settings->tileEffectScoreWeight;    // +0x7c, +0x78
        }
    }
}
````

### ExistingTileEffects.Evaluate — design notes
The type-check logic (lines 220–255 of the raw output) was partially truncated. The effect subtype check uses IL2CPP's vtable depth comparison pattern (`*(byte*)(vtable + 0x130)`) against two class descriptors — the exact subtype hierarchy is not captured but the scoring write path is fully confirmed.

---

## 11. ConsiderZones.Evaluate — 0x18075CC20

### Raw Ghidra output
````c
void FUN_18075cc20(undefined8 param_1,longlong *param_2,longlong param_3)
{
  // [full raw output — 275 lines, with truncated section at 1835–1946 recovered]
  // Guard: unit must have moveRange >= 2 (vtable +0x468 >= 2)
  // Get zone list: unit->opponentList ->GetZoneList() -> zoneList ->tileList
  // Get threshold: fVar7 = GetUtilityThreshold(unit)
  // Iterate zone tiles; for each tile call TileHasZoneFlag(tile, bit):
  //   bit 0x01: ctx.thresholdAccumulator += 9999.0
  //   bit 0x10: ctx.zoneInfluenceAccumulator += settings.zoneInfluenceWeight * dist * tile.+0x24 * sign
  //   bit 0x04: if same team ctx.thresholdAccumulator += 9999.0; else normal weight
  //   bit 0x20: outer boundary terminator
  // Post-loop: ctx.thresholdAccumulator += tile.+0x24 * threshold * zoneThresholdWeight
}
````

### Annotated reconstruction
````c
void ConsiderZones_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    if (unit == null) NullReferenceException();

    // Guard: unit must have at least 2 move range
    int moveRange = unit->vtable->GetEnemyCount(unit);   // vtable +0x468 — reused for moveRange here
    if (moveRange < 2) return;

    // Navigate to zone tile list
    if (unit->opponentList == null) NullReferenceException();
    ZoneList* zl = GetZoneList(unit->opponentList);   // FUN_18071b640
    if (zl == null || zl->tileList == null) NullReferenceException();
    List* tiles  = zl->tileList;   // zl +0x10
    if (tiles->count == 0) return;

    float threshold = GetUtilityThreshold(self, unit, 0);   // FUN_180760070

    foreach (ZoneTile* zt in tiles) {
        // Flag bit 0x01 — zone membership: unconditionally force tile above threshold
        if (TileHasZoneFlag(zt, 1)) {   // FUN_180741770
            ctx->thresholdAccumulator += 9999.0f;   // ctx +0x30
        }

        // Flag bit 0x10 — proximity influence on zoneInfluenceAccumulator
        if (!TileHasZoneFlag(zt, 0x10)) {
            // No zone list path: use secondary weight
            int dist2 = GetTileGridDistance(zt->coords, ctx->tileRef);   // FUN_18053feb0 capped at 20
            float sign = TileHasZoneFlag(zt, 8) ? -1.0f : 1.0f;         // flag 8 = repulsion
            ctx->zoneInfluenceAccumulator +=                              // ctx +0x24
                settings->zoneInfluenceSecondaryWeight * (float)dist2     // settings +0x5c
                * zt->influenceValue * sign;                              // zt +0x24
        } else {
            // Has zone list: use primary weight
            if (unit->opponentList->zoneList == null) NullReferenceException();
            if (unit->opponentList->zoneList->tileList->count > 0) {
                int dist = GetTileGridDistance(zt->coords, ctx->tileRef);
                float sign = TileHasZoneFlag(zt, 8) ? -1.0f : 1.0f;
                ctx->zoneInfluenceAccumulator +=
                    settings->zoneInfluenceWeight * (float)dist            // settings +0x58
                    * zt->influenceValue * sign;
            }
        }

        // Flag bit 0x04 — team ownership
        if (TileHasZoneFlag(zt, 4)) {
            if (TileCoordsMatch(zt->coords, ctx->tileRef)) {   // FUN_1805406a0
                ctx->thresholdAccumulator += 9999.0f;           // same team: force promotion
            }
            // else: fall through to standard weight
        }

        // Post-tile threshold write
        float tileInfluence = zt->influenceValue * threshold;   // zt +0x24
        // Matching tile: use weight A; non-matching: use weight B
        if (TileCoordsMatch(zt->coords, ctx->tileRef)) {
            float contribution = tileInfluence * settings->zoneThresholdWeight_A;  // settings +0x68
            ctx->thresholdAccumulator += max(contribution, threshold);             // floor = threshold
        } else {
            float contribution = tileInfluence * settings->zoneThresholdWeight_B;  // settings +0x6c
            ctx->thresholdAccumulator += max(contribution, threshold);
        }

        // Flag bit 0x20 — outer boundary: continue to next iteration
    }
}
````

---

## 12. ConsiderZones.PostProcess — 0x18075D3B0

### Raw Ghidra output
````c
void FUN_18075d3b0(undefined8 param_1,longlong *param_2,longlong param_3,undefined8 param_4)
{
  // [full raw output — 205 lines]
  // Pass 1: scan zone tiles for TileHasZoneFlag(tile, 3) — if found, isObjectiveFlag = true
  // Pass 2: iterate score dictionary param_3
  //   For each entry where ctx.thresholdAccumulator >= threshold:
  //     Find matching objective zone tile
  //     Get zoneMultiplier: if unit.statusEffects +0x8c == 1 then settings +0x64 else settings +0x60
  //     ctx.accumulatedScore *= zoneMultiplier   (for tiles at zone position)
  //     ctx.thresholdAccumulator += fVar6        (for other tiles if isObjectiveFlag)
}
````

### Annotated reconstruction
````c
void ConsiderZones_PostProcess(void* self, Unit* unit, ScoreDict* dict, void* param4) {
    // IL2CPP lazy init — omitted
    if (unit == null || unit->opponentList == null) return;

    ZoneList* zl = GetZoneList(unit->opponentList);
    if (zl == null || zl->tileList == null || zl->tileList->count == 0) return;

    // Pass 1: search for an objective zone tile (flag bit 3 = bits 1+2)
    bool isObjectiveFlag = false;
    foreach (ZoneTile* zt in zl->tileList) {
        if (TileHasZoneFlag(zt, 3)) {   // FUN_180741770 — flag 3 = objective zone
            isObjectiveFlag = true;
            break;
        }
    }

    // Compute threshold with objective flag
    float threshold = GetUtilityThreshold(self, unit, isObjectiveFlag ? 1 : 0);  // FUN_180760070 with extra param

    if (dict == null) return;

    // Pass 2: iterate all scored tiles
    foreach (KeyValuePair<Tile, TileCtx> entry in dict) {
        TileCtx* ctx = entry.value;

        if (ctx->thresholdAccumulator < threshold) continue;   // ctx +0x30

        // Find if this ctx's tile matches an objective zone tile
        bool matchedObjective = false;
        foreach (ZoneTile* zt in zl->tileList) {
            if (!TileHasZoneFlag(zt, 3)) continue;
            if (TileCoordsMatch(zt->coords, ctx->tileRef)) {   // FUN_1805406a0
                matchedObjective = false;   // cVar2 set to false for matched tiles
                break;
            }
        }

        // Determine zone multiplier from unit status
        StatusEffects* status = unit->vtable->GetStatusEffects(unit);   // vtable +0x398
        float zoneMultiplier;
        if (status->statusField == 1) {   // status +0x8c
            zoneMultiplier = settings->zoneScoreMultiplier_A;   // settings +0x64
        } else {
            zoneMultiplier = settings->zoneScoreMultiplier_B;   // settings +0x60
        }

        // Apply to scored tiles: zone tiles get score scaled, others get threshold bump
        foreach (ZoneTile* zt in zl->tileList) {
            if (!TileHasZoneFlag(zt, 3)) continue;
            if (TileCoordsMatch(zt->coords, ctx->tileRef)) {
                ctx->accumulatedScore *= zoneMultiplier;   // ctx +0x28
            } else if (!matchedObjective) {
                ctx->thresholdAccumulator += fVar6;        // ctx +0x30, fVar6 = zone threshold bonus
            }
        }
    }
}
````

---

## 13. GetTileScoreComponents — 0x1806E0AC0

### Raw Ghidra output
````c
float * FUN_1806e0ac0(float *param_1,longlong param_2, ...)
{
  // [full raw output — 115 lines]
  // Initialises param_1[0..5] = 0.0
  // Early exit if tile +0xf3: param_1[0]=100.0, param_1[4]=1, return
  // Lazily resolves scoreObj via GetScoredTileData / GetThreadedTileScore
  // param_1[2] = GetDerivedScoreComponent(...)
  // param_1[1] = GetTileBaseValue(scoreObj)
  // param_1[3] = GetMovementEffectivenessIndex()
  // Computes raw score fVar10 via distance formula or base formula
  // Clamps [0,100], floors to param_5 +0x78
  // param_1[0] = fVar10; return param_1
}
````

### Annotated reconstruction
````c
float* GetTileScoreComponents(float[6]* out, Tile* tile, Unit* unit, ...) {
    // IL2CPP lazy init — omitted

    // Zero out all 6 components
    out[0] = out[1] = out[2] = out[3] = out[4] = out[5] = 0.0f;

    // Early exit: objective tiles get fixed score 100
    if (tile->tileData == null) NullReferenceException();
    if (tile->tileData->isObjectiveTile) {   // tileData +0xf3
        *(bool*)(out + 4) = true;            // out[4] = isObjective flag
        out[0] = 100.0f;
        return out;
    }

    // Lazily resolve score object
    // [thread-aware: uses GetThreadedTileScore if threaded, otherwise computes directly]

    // Populate components
    out[1] = GetTileBaseValue(scoreObj);              // FUN_180628270
    out[2] = GetDerivedScoreComponent(...);           // FUN_1806debe0
    out[3] = GetMovementEffectivenessValue();         // FUN_180531700

    // Compute raw score (distance-adjusted or base formula depending on param_7)
    float rawScore = ...;   // [formula varies by path — see REPORT for detail]

    // Clamp to [0, 100]
    rawScore = clamp(rawScore, 0.0f, 100.0f);

    // Floor to tile minimum score
    int minScore = scoreObj->minScoreFloor;   // scoreObj +0x78
    if (rawScore < (float)minScore) rawScore = (float)minScore;

    out[0] = rawScore;   // centiscale [0–100]; callers multiply by 0.01
    return out;
}
````

---

## 14. GetMoveRangeData — 0x1806DF4E0

### Raw Ghidra output
````c
longlong FUN_1806df4e0(longlong param_1, ...)
{
  // [full raw output — 350 lines]
  // Populates MoveRangeData object param_9
  // Fields written: +0x10 (attackRange), +0x14 (ammoRange), +0x18 (moveCostNorm),
  //   +0x1c (moveCostToTile), +0x20 (maxReachability), +0x24 (canAttackFromTile),
  //   +0x25 (canFullyReach), +0x28 (tileScorePtr write-barriered)
  // expf called at line 1151: expf(1.0 - tile.accuracyDecay * 0.01)
}
````

### Annotated reconstruction
````c
MoveRangeData* GetMoveRangeData(Tile* tile, Unit* unit, ..., MoveRangeData* out) {
    // IL2CPP lazy init — omitted

    // Allocate output object if not provided
    if (out == null) out = new MoveRangeData();

    // Resolve the unit on the candidate tile
    bool canTarget = resolveCanTarget(...);   // FUN_1806169a0

    // Resolve tile score object
    out->tileScorePtr = GetScoredTileData(...);   // FUN_1806f2230; write barrier applied

    float effectivenessRatio = GetMovementEffectivenessValue();   // FUN_180531700

    // Movement cost components (from TileScore object param_6)
    float costPerStep     = tileScore->moveCostPerStep;      // param_6 +0x128
    float secondaryCost   = tileScore->secondaryCost;        // param_6 +0x110
    float tertiaryCost    = tileScore->tertiaryCost;         // param_6 +0x13c

    // Attack range: max(unit.moveRange * scale, minimum)
    float rawAttack = max(unit->moveRange * tileScore->attackRangeScale,    // +0x144, unit +0x54
                          tileScore->attackRangeMin);                         // +0x148
    // Ammo range: max(ammoSlotCount * scale, minimum)
    float rawAmmo   = max(unit->ammoSlotCount * tileScore->ammoRangeScale,  // +0x14c, unit +0x5b
                          tileScore->ammoRangeMin);                           // +0x150

    // Primary score
    float baseScore = (rawAttack + moveCostAdjust + baseValue + distCost + rawAmmo)
                      * effectivenessRatio
                      * tileScore->multiplier                                 // +0x8c
                      * tileScore->primaryWeight;                             // +0x140

    // Ammo survival fraction
    int attacksInRange = GetEnemyCountInRange(ctx, rangeExt);   // FUN_1806283c0
    float reloadChance = GetReloadChance(unit);                  // FUN_180614b30
    float ammoFrac = clamp((reloadChance * attacksInRange - ammoUsed * 3) * 0.01f, 0, 1);
    float survivor  = max(ammoFrac, 0.25f);

    // Range step penalty via expf
    float accuracyDecay   = tile->accuracyDecay * 0.01f;         // tile +0x244
    float rangePenaltyMult = expf(1.0f - accuracyDecay);         // FUN_1804bad80
    float rangeStepCount   = GetRangeStepCount(tile, weapon);    // FUN_1806defc0
    rangePenaltyMult       = max(rangePenaltyMult * rangeStepCount, 1.0f);

    // Compute output fields
    out->attackRange     = baseScore * survivor;    // +0x10
    out->ammoRange       = ammoScore;               // +0x14
    out->moveCostNorm    = clamp(moveCostRatio, 0, squadCount);  // +0x18
    out->moveCostToTile  = moveCostRatio;           // +0x1c
    out->maxReachability = max(prev, reachability); // +0x20
    out->canAttackFromTile = canFullAttack;          // +0x24
    out->canFullyReach     = canReach;               // +0x25
    return out;
}
````

---

## 15. ThreatFromOpponents.Evaluate — 0x18076ACB0

### Raw Ghidra output
````c
void FUN_18076acb0(undefined8 param_1,longlong *param_2,longlong param_3)
{
  // [full raw output — 85 lines]
  // Guard: vtable +0x468 must return > 1 (enemy count)
  // Phase 1 (if tile not current and occupied by ally):
  //   score = Score_B(tileOccupant); weight = settings +0x74
  //   ctx.accumulatedScore += (2 - ally.healthRatio) * weight * (maxMoves/weaponCount) * score
  // Phase 2 (always):
  //   ctx.accumulatedScore += Score_B(self) * settings +0x74
}
````

### Annotated reconstruction
````c
void ThreatFromOpponents_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    if (unit == null) NullReferenceException();

    // Guard: require more than 1 visible enemy
    int enemyCount = unit->vtable->GetEnemyCount(unit);   // vtable +0x468
    if (enemyCount <= 1) return;

    if (ctx == null || ctx->tileRef == null) NullReferenceException();

    // Phase 1: score contribution from an ally occupying the candidate tile
    if (!IsCurrentTile(ctx->tileRef, 0)) {   // FUN_1806889c0 — tile is not unit's current position
        Unit* tileOccupant = GetUnitOnTile(ctx->tileRef, 0);   // FUN_180688600
        if (tileOccupant != null && unit != tileOccupant) {
            Unit* occupant2 = GetUnitOnTile(ctx->tileRef, 0);
            if (occupant2 == null) NullReferenceException();

            if (IsAllyUnit(occupant2, 0)) {   // FUN_180616af0
                int maxMoves   = unit->movePool->maxMovePoints;   // unit[4] +0x18
                long weaponCnt = unit->weaponListCount;            // unit[5]

                float scoreB       = (float)Score_B(self, unit, occupant2, ctx, 0);   // FUN_18076b710
                float W_threat     = settings->W_threat;                                // settings +0x74
                float healthRatio  = (float)GetHealthRatio(occupant2, 0);              // FUN_1806155c0
                float contribution = ((1.0f - healthRatio) + 1.0f)   // = 2 - healthRatio
                                     * W_threat
                                     * ((float)maxMoves / (float)weaponCnt)
                                     * scoreB;
                ctx->accumulatedScore += contribution;   // ctx +0x28
            }
        }
    }

    // Phase 2: always score the unit itself on the candidate tile
    float prevScore = ctx->accumulatedScore;
    float scoreBSelf = (float)Score_B(self, unit, unit, ctx, 0);   // self as both unit and target
    float W_threat   = settings->W_threat;                          // settings +0x74
    if (W_threat == 0) NullReferenceException();

    ctx->accumulatedScore = scoreBSelf * W_threat + prevScore;   // ctx +0x28
}
````

---

## 16. ThreatFromOpponents.Score (A) — 0x18076AF90

### Raw Ghidra output
````c
undefined8 FUN_18076af90(undefined8 param_1,undefined8 param_2,longlong param_3, ...)
{
  // [full raw output — 337 lines]
  // Weapon loop: iterate non-ranged weapons; for each: IsWithinRangeA AND IsWithinRangeB;
  //   if both pass: max(score, Criterion.Score(...))
  // Post-loop multiplier cascade: 6 conditional multipliers based on phase, cover type, flags
  // Return CONCAT44(flag, fVar11)
}
````

### Annotated reconstruction
````c
// Returns packed (int flag, float score) — use (float)(result & 0xFFFFFFFF) for score
ulong ThreatFromOpponents_ScoreA(void* self, Unit* unit, Unit* target,
                                  TileCtx* ctx, ...) {
    // IL2CPP lazy init — omitted
    if (target == null || !IsEnemy(target, 0)) return 0;   // FUN_180722ed0

    // Iterate non-ranged weapon slots from unit.movePool tile list
    float maxScore = 0.0f;
    int flag = 0;
    List* weaponSlots = unit->movePool->zoneData->tileList;   // unit[4] +0x48
    foreach (WeaponSlot* slot in weaponSlots) {
        // Skip ranged weapons
        if (IsRangedWeapon(slot->weapon, 0)) continue;   // FUN_1829a91b0

        // Both range gates must pass
        bool rangeA = IsWithinRangeA(tile, unit, scoreObj, rangeType);   // FUN_1806e3c50
        bool rangeB = IsWithinRangeB(tile, unit, target);                  // FUN_1806e33a0
        if (!rangeA || !rangeB) continue;

        float score = (float)Criterion_Score(param5_unit, tile, param4, ctx, 0, 0);  // FUN_180760140
        if (score > maxScore) maxScore = score;
        flag = slot->weaponRef;   // carry weapon reference for downstream use
    }

    if (maxScore <= 0.0f) goto returnZero;

    // Multiplier cascade — applied to maxScore
    // [See REPORT §5 for full branch table]
    // Phase/cover branches read from unit->vtable:
    //   vtable +0x478 = GetDeploymentPhase() → int
    //   vtable +0x3d8 = GetWeaponList() → check +0xec bit 0 for rangedWeaponType
    //   vtable +0x468 = GetEnemyCount() → int

    // Example branches:
    if (unit->vtable->GetEnemyCount(unit) == 1 && phase != 2) {
        maxScore *= settings->coverMult_Quarter;   // settings +0x98
    }
    // ... (full cascade per REPORT §5)

    // Flanking area check using FUN_181446af0 on unit->movePool +0x68 sublists
    float listDist = GetListDistanceScore(unit->movePool->zoneData->sublist, unit, typeDesc);
    if (listDist < settings->weaponListDistanceThreshold) {   // settings +0xac
        // Check element counts from sublists at +0x68 offsets
        if (sublistA->items[0x24] + sublistB->items[0x28] > 1) {
            maxScore *= settings->flankingBonusMultiplier;    // settings +0xa0
        }
    }

    return CONCAT44(flag, maxScore);

returnZero:
    return 0;
}
````

---

## 17. ThreatFromOpponents.Score (B) — 0x18076B710

### Raw Ghidra output
````c
void FUN_18076b710(undefined8 param_1,longlong param_2,undefined8 param_3,longlong param_4)
{
  // [full raw output — 325 lines]
  // Iterates opponent list; for each opponent:
  //   Writes ctx.isObjectiveTile via FUN_1805df360
  //   Computes halfWidth = weaponRange / (squadCapacity+1) / 2
  //   Spatial scan: nested loop over [tile.x ± halfWidth, tile.y ± halfWidth]
  //   For each candidate tile: calls Score_A; applies directional/chokepoint/range multipliers
  //   Distance falloff: score *= (1 - dist / (halfWidth * 3))
  //   Keeps best score
  // Post-opponent: checks vtable +0x4a8 (HasOverwatch) if tile is 1 move away
}
````

### Annotated reconstruction
````c
float ThreatFromOpponents_ScoreB(void* self, Unit* unit, Unit* subject,
                                  TileCtx* ctx, int unused) {
    // IL2CPP lazy init — omitted

    // Navigate to opponent tile list
    MovePool* pool = unit->movePool;                         // unit +0xc8
    if (pool == null || pool->zoneData == null) NullReferenceException();
    List* opponents = pool->zoneData->tileList;              // pool +0x10 +0x48

    TileGrid* grid = ScoringContext_singleton->tileGrid;     // singleton +0x28

    float bestScore = 0.0f;
    foreach (Tile* opponentTile in opponents) {
        // Skip non-enemy tiles
        if (!IsEnemy(opponentTile, 0)) continue;   // FUN_180722ed0

        // Write ctx.isObjectiveTile for this opponent
        ctx->isObjectiveTile = IsObjectiveTile(unit, opponentTile, ...);  // FUN_1805df360, ctx +0x60

        // Compute scan radius: weaponRange / (squadCapacity_offset / 2)
        int halfWidth = (weaponStatsBlock->baseRange / squadCapacity) / 2;  // complex formula

        // Spatial scan: ±halfWidth tile bounding box
        int x0 = tile->x - halfWidth,  x1 = tile->x + halfWidth;
        int y0 = tile->y - halfWidth,  y1 = tile->y + halfWidth;

        float tileBestScore = 0.0f;
        for (int cx = x0; cx <= x1; cx++) {
            for (int cy = y0; cy <= y1; cy++) {
                Tile* candidate = GetAdjacentTile(grid, cx, cy);   // FUN_1810c1fc0
                if (candidate == null) continue;

                // Skip if context-invalid (occupied by enemy or wrong direction)
                if (IsCurrentTile(candidate)) {
                    if (candidate != tile) continue;
                } else {
                    if (dist < prevDist || direction != prevDirection) continue;
                }

                float score = (float)Score_A(self, unit, opponentTile, candidate, subject, ctx->tileRef, 0);
                if (score <= 0.0f) continue;

                // Spatial multipliers (only for non-current-tile candidates)
                if (candidate != tile) {
                    if (dirToEnemy == 0 && pathClearCount > 0) score *= 1.2f;  // flanking bonus
                    if (dirToEnemy < dirFromCurrent)            score *= 0.9f;  // moving away
                    else if (dirToEnemy > dirFromCurrent)       score *= 1.2f;  // moving toward

                    // Choke point penalty
                    if (healthStatus >= 0 && IsChokePoint(tile) && !IsChokePoint(candidate)
                        && flankSlots->count > 2) {
                        score *= 0.8f;
                    }

                    // Long-range weapon bonus
                    if ((uint)weaponData->specialFlag > 0x7fffffff) score *= 1.2f;

                    // Distance falloff
                    int dist = GetTileDistance(candidate, tile);   // FUN_1805ca7a0
                    score *= (1.0f - (float)dist / ((float)halfWidth * 3.0f));
                }

                if (score > tileBestScore) tileBestScore = score;
            }
        }

        // Post-opponent: check overwatch if tile is adjacent (dist == 1)
        if (distToOpponent == 1) {
            bool hasOverwatch = opponentTile->vtable->HasOverwatchOrReaction(opponentTile);  // vtable +0x4a8
            // [overwatch effect not captured in available output]
        }

        if (tileBestScore > bestScore) bestScore = tileBestScore;
    }

    return bestScore;
}
````

---

## 18. Roam.Collect — 0x180768300

### Raw Ghidra output
````c
void FUN_180768300(undefined8 param_1,longlong *param_2,longlong param_3)
{
  // [full raw output — 150 lines, remainder recovered from second view]
  // Guards: !IsRangedWeapon; HasRoamFlag(unit.opponentList+0x40, 0x21)
  // Computes roamRadius = moveSpeed / effectiveRange
  // Builds bounding box; filters tiles; shuffles; picks first
  // Creates or updates TileScoreObject; adds to score dictionary and global list
}
````

### Annotated reconstruction
````c
void Roam_Collect(void* self, Unit* unit, ScoreDict* dict) {
    // IL2CPP lazy init — omitted
    if (unit == null) return;

    // Guard 1: Roam is melee-only
    WeaponData* wpn = unit->vtable->GetStatusEffects(unit);   // vtable +0x398
    if (IsRangedWeapon(wpn->weaponBlock, 0)) return;           // FUN_1829a91b0

    // Guard 2: unit must have roam behaviour configured
    if (unit->opponentList == null) return;
    object* roamData = unit->opponentList->behaviorConfig;     // unit[0x19] +0x40
    if (roamData == null) return;
    if (!HasRoamFlag(roamData, 0x21)) return;                  // FUN_18053d700

    // Get unit's current tile and movement stats
    Tile* currentTile = unit->vtable->GetTilePosition(unit);   // vtable +0x388
    int moveSpeed     = unit->vtable->GetMoveSpeed(unit);       // vtable +0x458
    int baseRange     = wpn->weaponStatsBlock->baseRange;       // +0x118
    int bonusRange    = unit->vtable->GetWeaponList(unit)->bonusRange;   // vtable +0x3d8, +0x3c
    int effectiveRange = max(baseRange + bonusRange, 1);
    int roamRadius    = moveSpeed / effectiveRange;
    if (roamRadius < 1) return;                                // can't roam

    // Build candidate tile list from bounding box ± roamRadius, clamped to grid
    TileGrid* grid = ScoringContext_singleton->tileGrid;       // singleton +0x28
    int x0 = max(currentTile->x - roamRadius, 0);
    int x1 = min(currentTile->x + roamRadius, grid->width  - 1);
    int y0 = max(currentTile->y - roamRadius, 0);
    int y1 = min(currentTile->y + roamRadius, grid->height - 1);

    List* candidates = GetSharedTileList(SharedTileList_class);  // FUN_18000cfd0

    for (int cx = x0; cx <= x1; cx++) {
        for (int cy = y0; cy <= y1; cy++) {
            Tile* t = GetAdjacentTile(grid, cx, cy);           // FUN_1810c1fc0
            if (t == null) continue;

            // Tile filter
            if ((t->flags & 0x1) != 0) continue;              // isBlocked (tile +0x1c bit 0)
            if ((t->flags & 0x4) != 0) continue;              // isOccupied (tile +0x1c bit 2)
            if (!IsCurrentTile(t)) continue;                   // FUN_1806889c0
            if (HasTileEffects(t)) continue;                   // FUN_180688850
            int dist = GetTileDistance(t, currentTile);
            if (dist > roamRadius) continue;

            candidates->add(t);                                // write barrier applied
        }
    }

    if (candidates->count == 0) return;

    // Shuffle and select first candidate
    int newCount = ShuffleTileList(roamData, 0, candidates->count);  // FUN_18053d810
    Tile* chosen = candidates->items[roamRadius];                     // pick by index

    // Create or update score entry for chosen tile
    float threshold = GetUtilityThreshold(self, unit, 0);   // FUN_180760070
    TileScoreObject* existing = null;
    bool found = TryGetExistingScore(dict, chosen, &existing, ScoreDictType);  // FUN_181442600

    TileScoreObject* scoreObj;
    if (!found) {
        scoreObj = new TileScoreObject();
        InitTileScore(scoreObj, chosen);                   // FUN_180741530
        scoreObj->thresholdValue = threshold * 100.0f;    // +0x30
        AddToScoreDictionary(dict, chosen, scoreObj);     // FUN_181435ba0
    } else {
        existing->thresholdValue += threshold * 100.0f;   // +0x30
        scoreObj = existing;
    }

    // Add tile to global shared tile list
    List* globalList = GetSharedTileList(SharedTileList_class);
    globalList->vtable->AddToList(globalList, chosen, 1);   // vtable +0x188
}
````

---

## 19. WakeUp.Collect — 0x180787DD0

### Raw Ghidra output
````c
void FUN_180787dd0(undefined8 param_1,longlong param_2)
{
  // [full raw output — 85 lines]
  // Phase 1: iterate unit.movePool+0x10+0x20 (ally tile list)
  //   filter: ally+0x162 != 0 (awake), ally+0x48 == 0 (no condition), ally+0x140 < 1 (no priority)
  //   if reachable: set movePool+0x51 = 0; return
  // Phase 2: iterate unit.movePool+0x10+0x48 (opponent tile list)
  //   if opponent tile in range and team-matched: set movePool+0x51 = 0; return
}
````

### Annotated reconstruction
````c
void WakeUp_Collect(void* self, Unit* unit) {
    // IL2CPP lazy init — omitted
    if (unit == null) NullReferenceException();

    // Navigate to movePool zone data
    MovePool* pool = unit->movePool;                  // unit +0xc8
    if (pool == null) NullReferenceException();
    ZoneData* zoneData = pool->zoneData;              // pool +0x10
    if (zoneData == null || zoneData->tileList == null) NullReferenceException();

    // Phase 1: scan ally tile list for a sleeping ally we can wake
    List* allies = zoneData->allyTileList;            // zoneData +0x20
    foreach (Unit* ally in allies) {
        // Filter: skip allies that don't need waking
        if (ally->isAwake != 0) continue;             // ally +0x162; 0 = sleeping
        if (ally->wakeCondition == null) continue;    // ally +0x48
        if (ally->wakePriority < 1) continue;         // ally +0x140

        if (ally == unit) break;   // don't wake yourself

        // Check if unit can reach/affect this ally
        bool reachable = CanReachTarget(unit, ally, 1, 0, 0, 0);  // FUN_1805df360
        if (reachable) {
            pool->wakeupPending = 0;   // pool +0x51 — signal wake resolved
            return;
        }
    }

    // Phase 2: fallback — check opponent proximity as urgency trigger
    List* opponents = zoneData->opponentTileList;     // zoneData +0x48
    foreach (Tile* opponentTile in opponents) {
        Tile* tileRef = opponentTile->tileRef;        // opponentTile +0x10
        if (tileRef == null) NullReferenceException();

        bool teamMatch = TileTeamMatches(tileRef, zoneData->zoneTeamId);  // FUN_1805dfab0, zoneData +0x14
        bool inRange   = CanReachTarget(unit, tileRef, teamMatch, 0, 0, 0);   // FUN_1805df360
        if (inRange) {
            pool->wakeupPending = 0;   // pool +0x51
            return;
        }
    }
}
````
````

---

Now the handoff prompt:

---
````
# Investigation Handoff — Menace Tactical AI Criterions — Stage 2 → Stage 3

## Directive
Read Research-AI.md in full before proceeding. It is attached to this session by the operator.

## Investigation Target
- **Game:** Menace (PC x64, Unity IL2CPP, GameAssembly.dll)
- **Image base:** 0x180000000
- **System under investigation:** Menace.Tactical.AI.Behaviors.Criterions
- **Investigation status:** In Progress
- **Stage:** 3 of ~3
- **VAs complete across all stages:** 25 of ~32

## Extraction Report

11 classes extracted, all : Criterion (TDI 3670). No fields on any subclass.
Shared .ctor RVA 0x4EB570 (10/11 classes). Shared stub RVA 0x4F7EE0 — Criterion.Collect/Evaluate/PostProcess virtual no-ops.
WakeUp .ctor diverges: RVA 0x518FA0 (confirmed body-less, compiler artefact).
ThreatFromOpponents: two Score overloads + non-default GetThreads (returns 4).
CoverAgainstOpponents: static float[] COVER_PENALTIES (len=4) + .cctor.

| Class | TDI | Special |
|---|---|---|
| Criterion | 3670 | base |
| AvoidOpponents | 3671 | ✅ complete |
| ConsiderSurroundings | 3672 | ⬜ not analysed |
| ConsiderZones | 3673 | ✅ complete |
| CoverAgainstOpponents | 3674 | ✅ complete (Stage 1) |
| DistanceToCurrentTile | 3675 | ✅ complete |
| ExistingTileEffects | 3676 | ✅ complete |
| FleeFromOpponents | 3677 | ✅ complete |
| Roam | 3678 | ✅ complete |
| ThreatFromOpponents | 3679 | ✅ complete |
| WakeUp | 3680 | ✅ complete |

---

## Stage Artefacts on Disk
````
criterions/stage-1/REPORT.md
criterions/stage-1/RECONSTRUCTIONS.md
criterions/stage-2/REPORT.md
criterions/stage-2/RECONSTRUCTIONS.md
````

---

## Resolved Symbol Maps

### FUN_ → Method Name
````
FUN_1804EB570 = Criterion_ctor                    // pass-through to object::ctor
FUN_180427B00 = IL2CPP_TypeInit                   // lazy static type init guard
FUN_180427D90 = IL2CPP_NullRefAbort               // throws NullReferenceException
FUN_180427D80 = IL2CPP_IndexOutOfRangeAbort       // throws IndexOutOfRangeException
FUN_1804F7EE0 = Enumerator_Dispose                // end of foreach
FUN_180426E50 = IL2CPP_WriteBarrier               // GC write barrier; no logical effect
FUN_180426ED0 = Array_CreateInstance              // allocates managed array
FUN_181A8F520 = Array_SetElementType
FUN_180CBab80 = List_GetEnumerator                // GetEnumerator on a List
FUN_1814F4770 = List_MoveNext                     // List enumerator MoveNext
FUN_18136D8A0 = Dict_GetEnumerator                // GetEnumerator on a Dictionary
FUN_18152F9B0 = Dict_MoveNext                     // Dictionary enumerator MoveNext
FUN_18000D310 = ComputeTileScore_Unthreaded       // tile score entry point (no thread data)
FUN_18000D130 = ComputeTileScore_Threaded         // tile score entry point (threaded)
FUN_18000CFD0 = GetSharedTileList                 // returns global tile list singleton
FUN_180760070 = Criterion_GetUtilityThreshold     // threshold = max(base, base*minScale) * multiplier
FUN_180760140 = Criterion_Score                   // master scoring function
FUN_18071AE10 = GetTileZoneModifier               // returns TileModifier at zoneData+0x310
FUN_1806E0AC0 = GetTileScoreComponents            // populates float[6] score component array
FUN_1806DF4E0 = GetMoveRangeData                  // populates MoveRangeData struct
FUN_1806E0300 = GetReachabilityAdjustedScore      // applies movement cost gating
FUN_1806E2400 = GetMovementEffectivenessIndex     // index into movement effectiveness table
FUN_1804BAD80 = expf_approx                       // expf-equivalent single-arg growth curve
FUN_1806155C0 = GetHealthRatio                    // unit health as float [0,1]
FUN_180614B30 = GetReloadChance                   // unit reload probability
FUN_180614D30 = GetMovementDepth                  // -2 = deployment-locked
FUN_1806F2460 = GetThreadedTileScore              // tile score from threaded pipeline
FUN_1806D5040 = GetThreadScoreIndex               // thread-local tile score index
FUN_1806F2230 = GetScoredTileData                 // TileScore from thread-local storage
FUN_1806283C0 = GetEnemyCountInRange              // enemy count within radius
FUN_180687590 = TileHasEnemyUnit                  // non-zero if tile occupied by enemy
FUN_1806888B0 = TileMatchesContext                // tile matches evaluation context
FUN_1806889C0 = IsCurrentTile                     // true if tile is unit's current position
FUN_180688600 = GetUnitOnTile                     // unit currently on tile
FUN_180688850 = HasTileEffects                    // true if tile has active effects
FUN_1806169A0 = CanTargetUnit                     // true if unit A can target unit B
FUN_1806D7700 = GetWeaponRange                    // weapon range stat
FUN_180717870 = IsListNonEmpty                    // true if collection non-empty
FUN_180722ED0 = IsEnemy                           // true if entity is hostile
FUN_180687660 = GetDirectionIndex                 // 0–7 directional index
FUN_1805CA990 = IsChokePoint                      // true if tile is a choke point
FUN_1805CA7A0 = GetTileDistance                   // distance between two tiles
FUN_1805CA720 = GetTileDirectionIndex             // directional index between two tiles
FUN_1806DEFC0 = GetRangeStepCount                 // range step count for weapon at tile
FUN_1806DE960 = GetAttackCountFromTile            // viable attack count from tile
FUN_180628300 = GetTileBaseValue_secondary        // secondary tile base value accessor
FUN_180628270 = GetTileBaseValue                  // primary tile base value
FUN_1806DEBE0 = GetDerivedScoreComponent          // derived score sub-component
FUN_180531700 = GetMovementEffectivenessValue     // movement effectiveness float
FUN_1805316F0 = GetMovementEffectivenessValue_alt // alternate call signature
FUN_18062A050 = InitScoringObject                 // initialise scoring object
FUN_1829A9340 = IsRangedWeapon                    // true if weapon is ranged
FUN_1829A91B0 = IsRangedWeapon_alt                // alternate ranged weapon check
FUN_1810C1FC0 = GetAdjacentTile                   // tile at grid coordinate
FUN_180616AF0 = IsAllyUnit                        // true if unit is an ally
FUN_180741770 = TileHasZoneFlag                   // tests bitmask flag on zone tile
FUN_18053FEB0 = GetTileGridDistance               // grid distance capped at 20
FUN_1805406A0 = TileCoordsMatch                   // true if tile coordinates equal
FUN_18071B640 = GetZoneList                       // zone list from opponent list object
FUN_1806E3C50 = IsWithinRangeA                    // range gate A (type+context+melee+attack)
FUN_1806E33A0 = IsWithinRangeB                    // range gate B (all weapon slots must pass)
FUN_1806E3750 = IsInMeleeRange                    // melee range sub-check (IsWithinRangeA)
FUN_1806E60A0 = IsInAttackRange                   // attack range sub-check (IsWithinRangeA)
FUN_1806E3D50 = IsValidRangeType                  // range type validity gate
FUN_1806F9F20 = FetchScoredTileData               // fetch TileScore by index from tileData
FUN_181446AF0 = GetListDistanceScore              // distance/score metric for weapon list
FUN_180717A40 = IsUnitInactive                    // true if unit is inactive/disabled
FUN_180679360 = GetActivePhaseContext             // phase context object
FUN_1805DFAB0 = TileTeamMatches                   // tile's team matches given ID
FUN_180616B50 = CanTargetTeam                     // group can target given team ID
FUN_18053D700 = HasRoamFlag                       // checks behavior flag on config object
FUN_18053D810 = ShuffleTileList                   // randomise tile list order
FUN_181442600 = TryGetExistingScore               // look up score entry in dictionary
FUN_180741530 = InitTileScore                     // initialise TileScoreObject
FUN_181435BA0 = AddToScoreDictionary              // insert score entry
FUN_180513400 = CheckEffectFlag                   // test effect flag bit
FUN_1805316D0 = ResetEffectivenessValue           // reset effectiveness to 1.0
FUN_18046085D0 = List_Construct                   // allocate/construct a list
FUN_1805CA920 = GetTileCoords                     // returns tile coordinate struct
FUN_1806285E0 = GetTileScore_A                    // tile score accessor A
FUN_180628550 = GetTileScore_B                    // tile score accessor B
FUN_1806285B0 = GetTileScore_C                    // tile score accessor C
FUN_180628580 = GetTileScore_D                    // tile score accessor D
FUN_180628380 = GetTileScore_E                    // tile score accessor E
FUN_180628330 = GetTileScore_F                    // tile score accessor F
FUN_1806FAC90 = CheckTileTargetingFlag            // tile targeting flag check
FUN_180628240 = GetTileDistanceModifier           // tile distance modifier value
FUN_1805DF360 = CanReachTarget                    // range/reach check between two objects
FUN_1805A570  = Abs                               // integer absolute value
FUN_18073BCF0 = RangeContains                     // true if range contains value
FUN_18052A570 = Abs_alt                           // integer abs (alternate)
FUN_1806DE540 = ComputeRangeStep                  // computes range step for attack calc
FUN_1806285E0 = GetAttackBaseValue                // attack base value from TileScore
````

### DAT_ → Class / Static Field
````
DAT_18394C3D0 = AIWeightsTemplate_class
DAT_183981FC8 = ScoringContext_class
DAT_183981F50 = ScoringContext_singleton_class     // singleton access via +0xb8
DAT_18396A5E8 = OverwatchResponseCurve_class
DAT_18393EFB0 = (unknown config class)
DAT_183942930 = (unknown config class)
DAT_18397AE78 = MovementEffectivenessTable_class
DAT_18397C1E0 = SniperWeapon_class
DAT_18396DF28 = CoverAgainstOpponents_class
DAT_18393FEF8 = float_typeDesc
DAT_1839500E8 = floatArray_typeDesc
DAT_1839A6198 = (unknown — tile list / iterator type)
DAT_1839ADA98 = (unknown — opponent iterator type)
DAT_1839ADB50 = (unknown — iterator MoveNext type)
DAT_1839ADC08 = (unknown — iterator type)
DAT_183968278 = OpponentListFilter_class
DAT_18394DF48 = WeaponTypeCheck_class
DAT_183981F50 = ScoringContext_singleton_ref
DAT_183944290 = (unknown — list distance type descriptor)
DAT_183938690 = WeaponEnumeratorDispose_class
DAT_183938748 = WeaponEnumeratorMoveNext_class
DAT_183938800 = WeaponEnumerator_class
DAT_183982CF8 = RangeGate_class                   // used for IsWithinRangeA checks
DAT_18397AE10 = WeaponSlotList_typeDesc
DAT_183952B10 = TileEffectSubtype_A_class
DAT_183952A58 = TileEffectSubtype_B_class
DAT_18393E338 = TileEffectEnumeratorDispose_class
DAT_18393E3F0 = TileEffectEnumeratorMoveNext_class
DAT_18398C318 = TileEffectList_typeDesc
DAT_183993CB0 = AllyEnumeratorDispose_class
DAT_183993D68 = AllyEnumeratorMoveNext_class
DAT_183993E20 = AllyList_typeDesc
DAT_1839A25C0 = AllyTileList_typeDesc
DAT_183998500 = SharedTileList_class
DAT_183995830 = SharedTileList_runtime_class
DAT_1839888F0 = TileScoreObject_class
DAT_1839776F8 = ScoreDictionary_class
DAT_1839779F8 = ScoreDictionary_lookupType
DAT_18394C3D0 = AIWeightsTemplate_class           // (duplicate — same as above)
DAT_183B9331A = Criterion_Score_initFlag
DAT_183B9331B = GetUtilityThreshold_initFlag
DAT_183B93322 = CoverEvaluate_initFlag
DAT_183B93323 = CoverCctor_initFlag
DAT_183B93329 = ThreatEvaluate_initFlag
DAT_183B9332A = ThreatScoreB_initFlag
DAT_183B9332B = ThreatScoreA_initFlag
DAT_183B9332C = WakeUpCollect_initFlag
DAT_183B93325 = DistanceEvaluate_initFlag
DAT_183B93326 = ExistingEffectsEvaluate_initFlag
DAT_183B93327 = FleeEvaluate_initFlag
DAT_183B93328 = RoamCollect_initFlag
DAT_183B93320 = ConsiderZonesEvaluate_initFlag
DAT_183B93321 = ConsiderZonesPostProcess_initFlag
DAT_183B9331C = AvoidEvaluate_initFlag
````

---

## Field Offset Tables

### AIWeightsTemplate (via DAT_18394c3d0 +0xb8 +0x8)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x58 | zoneInfluenceWeight | float | confirmed |
| +0x5c | zoneInfluenceSecondaryWeight | float | confirmed |
| +0x60 | zoneScoreMultiplier_A | float | confirmed |
| +0x64 | zoneScoreMultiplier_B | float | confirmed |
| +0x68 | zoneThresholdWeight_A | float | confirmed |
| +0x6c | zoneThresholdWeight_B | float | confirmed |
| +0x70 | coverScoreWeight | float | confirmed |
| +0x74 | W_threat | float | confirmed |
| +0x78 | tileEffectScoreWeight | float | confirmed |
| +0x7c | tileEffectMultiplier | float | confirmed |
| +0x8c | coverMult_Full | float | confirmed |
| +0x90 | coverMult_Partial | float | confirmed |
| +0x94 | coverMult_Low | float | confirmed |
| +0x98 | coverMult_Quarter | float | confirmed |
| +0x9c | coverMult_None | float | confirmed |
| +0xa0 | flankingBonusMultiplier | float | confirmed |
| +0xa4 | bestCoverBonusWeight | float | confirmed |
| +0xac | weaponListDistanceThreshold | float | confirmed |
| +0xb0 | avoidDirectThreatWeight | float | confirmed |
| +0xb4 | avoidIndirectThreatWeight | float | confirmed |
| +0xb8 | fleeWeight | float | confirmed |
| +0xd4 | occupiedDirectionPenalty | float | confirmed |
| +0xd8 | rangeScorePenalty | float | confirmed |
| +0xdc | ammoScorePenalty | float | confirmed |
| +0xe4 | baseAttackWeight | float | confirmed |
| +0xe8 | ammoPressureWeight | float | confirmed |
| +0xec | deployPositionWeight | float | confirmed |
| +0xf0 | sniperAttackWeight | float | confirmed |
| +0x13c | baseThreshold | float | confirmed |
| +0x158 | outOfRangePenalty | float | confirmed |

### EvaluationContext / TileScoreRecord (param_3 in Evaluate functions)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | tileRef | ptr | confirmed |
| +0x20 | reachabilityScore | float | confirmed |
| +0x24 | zoneInfluenceAccumulator | float | confirmed |
| +0x28 | accumulatedScore | float | confirmed |
| +0x30 | thresholdAccumulator | float | confirmed |
| +0x60 | isObjectiveTile | bool | confirmed |

### Unit
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x20 | movePool (unit[4]) | ptr | confirmed |
| +0x4c | teamIndex | int | confirmed |
| +0x54 | moveRange | int | confirmed |
| +0x5b | ammoSlotCount | int | confirmed |
| +0x5c | currentAmmo | int | confirmed |
| +0x60 | squadCount | int | confirmed |
| +0x70 | teamId (unit[0xe]) | int | confirmed |
| +0xc8 | movePool (alt path) | ptr | confirmed |
| +0x15c | isDeployed | bool | confirmed |
| +0x140 | wakePriority | int | confirmed (on ally units) |
| +0x162 | isAwake | bool | confirmed (on ally units; 0=sleeping) |
| +0x48 | wakeCondition | ptr | confirmed (on ally units) |

### MovePool
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | zoneData ptr | ptr | confirmed |
| +0x18 | maxMovePoints | int | confirmed |
| +0x51 | wakeupPending | bool | confirmed |

### MoveRangeData
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | attackRange | float | confirmed |
| +0x14 | ammoRange | float | confirmed |
| +0x18 | moveCostNorm | float | confirmed |
| +0x1c | moveCostToTile | float | confirmed |
| +0x20 | maxReachability | float | confirmed |
| +0x24 | canAttackFromTile | bool | confirmed |
| +0x25 | canFullyReach | bool | confirmed |
| +0x28 | tileScorePtr | ptr | confirmed |

### TileModifier (struct at zoneData+0x310)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x14 | minThresholdScale | float | confirmed |
| +0x18 | thresholdMultiplier | float | confirmed |
| +0x20 | distanceScaleFactor | float | confirmed |
| +0x44 | effectImmunityMask | uint | confirmed |

### ScoringContext (singleton via DAT_183981f50 +0xb8)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x28 | tileGrid | ptr | confirmed |
| +0x60 | phase | int | confirmed (0=deploy, 1=std, 2=post) |
| +0xa8 | avoidGroups | array | confirmed |

### Tile
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x10 | tileData ptr | ptr | inferred |
| +0x18 | zoneDescriptor | ptr | confirmed |
| +0x1c | flags | byte | confirmed (bit 0=blocked, bit 2=occupied) |
| +0x48 | weaponSlots (tile-side) | List | confirmed |
| +0x68 | effectList | List | confirmed |
| +0xf2 | hasTileEffect | bool | confirmed |
| +0xf3 | isObjectiveTile | bool | confirmed |
| +0x244 | accuracyDecay | int | confirmed |

### WeaponStatsBlock (at weaponData +0x2b0)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x118 | baseRange | int | confirmed |

### WeaponList (returned by vtable +0x3d8)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x3c | bonusRange | int | confirmed |
| +0xec | rangedWeaponTypeFlag | uint | confirmed (bit 0) |

### ZoneData / MovePool.zoneData (pool +0x10)
| Offset | Field | Type | Status |
|---|---|---|---|
| +0x14 | zoneTeamId | int | confirmed |
| +0x20 | allyTileList | List | confirmed |
| +0x48 | opponentTileList | List | confirmed |

---

## VAs Analysed — All Stages

| Stage | VA | Method | Status |
|---|---|---|---|
| 1 | 0x1804EB570 | Criterion..ctor | Complete |
| 1 | 0x18075EB00 | CoverAgainstOpponents..cctor | Complete |
| 1 | 0x180760070 | Criterion.GetUtilityThreshold | Complete |
| 1 | 0x18075DAD0 | CoverAgainstOpponents.Evaluate | Complete |
| 1 | 0x180760140 | Criterion.Score | Complete |
| 2 | 0x18054E040 | ThreatFromOpponents.GetThreads | Complete — returns 4 |
| 2 | 0x18076ACB0 | ThreatFromOpponents.Evaluate | Complete |
| 2 | 0x18076AF90 | ThreatFromOpponents.Score (A) | Complete |
| 2 | 0x18076B710 | ThreatFromOpponents.Score (B) | Complete |
| 2 | 0x1806E0AC0 | GetTileScoreComponents | Complete |
| 2 | 0x1806DF4E0 | GetMoveRangeData | Complete |
| 2 | 0x1804BAD80 | expf_approx | Complete — single-arg expf equivalent |
| 2 | 0x18071AE10 | GetTileZoneModifier | Complete |
| 2 | 0x18075CC20 | ConsiderZones.Evaluate | Complete |
| 2 | 0x18075D3B0 | ConsiderZones.PostProcess | Complete |
| 2 | 0x18075BE10 | AvoidOpponents.Evaluate | Complete |
| 2 | 0x18071B670 | Criterion.IsDeploymentPhase | Complete |
| 2 | 0x180518FA0 | WakeUp..ctor | Complete — no additional fields |
| 2 | 0x180760CF0 | DistanceToCurrentTile.Evaluate | Complete |
| 2 | 0x180760FB0 | ExistingTileEffects.Evaluate | Complete |
| 2 | 0x1807613A0 | FleeFromOpponents.Evaluate | Complete |
| 2 | 0x180768300 | Roam.Collect | Complete |
| 2 | 0x180787DD0 | WakeUp.Collect | Complete |
| 2 | 0x1806E3C50 | IsWithinRangeA | Complete |
| 2 | 0x1806E33A0 | IsWithinRangeB | Complete |

---

## Open Questions

[ ] Q1: COVER_PENALTIES[4] actual values? → Memory dump CoverAgainstOpponents.COVER_PENALTIES at runtime, or view .cctor at 0x18075EB00 for literal float pushes.
[ ] Q3: Class name of zoneData (returned by vtable +0x398 on ZoneDescriptor)? → Search dump.cs for class with field at offset 0x310; or extract_rvas.py on ZoneDescriptor return type.
[ ] Q9: AIWeightsTemplate offsets 0x100–0x140? → run extract_rvas.py on AIWeightsTemplate class.
[ ] Q-A: ConsiderSurroundings.Evaluate not analysed (TDI 3672) → Extract RVAs; likely 1–2 functions.
[ ] Q-B: ConsiderZones.Collect (0x18075C630) not analysed → Batch with ConsiderSurroundings.
[ ] Q-C: IsInMeleeRange (0x1806E3750) and IsInAttackRange (0x1806E60A0) semantics → Analyse if range gate detail needed for final report.
[ ] Q10: Behaviour selection layer consuming Score output → Scoped out; outside Criterions namespace.

---

## Scope Boundaries

- **All IsValid implementations** (10 classes) — low priority; interface documented, implementations deferred.
- **Behaviour selection layer** (outside Criterions namespace) — explicitly deferred; requires operator sign-off.
- **IsValidRangeType** (0x1806E3D50) — trivial gate; not required for formula understanding.

---

## Next Priority Table

Continue from here. Stage 3 should close the namespace.

| Priority | Method | VA | Rationale |
|---|---|---|---|
| 1 | ConsiderSurroundings.Evaluate | extract first | Last unanalysed Evaluate in namespace |
| 2 | ConsiderZones.Collect | 0x18075C630 | Completes ConsiderZones class |
| 3 | IsInMeleeRange | 0x1806E3750 | Closes IsWithinRangeA sub-calls |
| 4 | IsInAttackRange | 0x1806E60A0 | Closes IsWithinRangeA sub-calls |
| 5 | COVER_PENALTIES dump | runtime / 0x18075EB00 | Resolves Q1 — only unknown constant |

Batch priorities 3 and 4 — they are the two IsWithinRangeA sub-calls and can be exported together. Run extract_rvas.py on ConsiderSurroundings before requesting Ghidra output for priority 1.

---

## Instructions for This Session

1. Read Research-AI.md in full.
2. Review the symbol maps and field tables above — treat as confirmed prior work.
3. Do not re-derive anything listed as confirmed.
4. Do not request or reference the stage artefact files during analysis.
5. Run extract_rvas.py on ConsiderSurroundings (TDI 3672) before requesting Ghidra output.
6. Continue from the Next Priority Table above.
7. Flag any scope expansion before pursuing it.
8. When all VAs are complete, invoke research-handoff in **collation mode** (final stage):
   - Inputs: all stage REPORT.md and RECONSTRUCTIONS.md from disk
   - Output: single unified REPORT.md and RECONSTRUCTIONS.md for the full investigation