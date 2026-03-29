# Menace — Tactical AI Criterions — Annotated Function Reconstructions

**Source:** Ghidra decompilation of Menace (PC x64, Unity IL2CPP, GameAssembly.dll)
**Image base:** `0x180000000`
**Format:** Each function shows the raw Ghidra output followed by a fully annotated C-style reconstruction with all offsets resolved. Functions appear in leaf-first order.

---

## Quick-Reference Field Tables

### TacticalAISettings (singleton via `DAT_18394C3D0 +0xb8 +0x8`)

| Offset | Field | Type |
|---|---|---|
| `+0x58` | `zoneInfluenceWeight` | float |
| `+0x5c` | `zoneInfluenceSecondaryWeight` | float |
| `+0x60` | `zoneScoreMultiplier_A` | float |
| `+0x64` | `zoneScoreMultiplier_B` | float |
| `+0x68` | `zoneThresholdWeight_A` | float |
| `+0x6c` | `zoneThresholdWeight_B` | float |
| `+0x70` | `coverScoreWeight` | float |
| `+0x74` | `W_threat` | float |
| `+0x78` | `tileEffectScoreWeight` | float |
| `+0x7c` | `tileEffectMultiplier` / `W_attack` | float |
| `+0x80` | `W_ammo` | float |
| `+0x84` | `W_deploy` | float |
| `+0x88` | `W_sniper` | float |
| `+0x8c` | `coverMult_Full` | float |
| `+0x90` | `coverMult_Partial` | float |
| `+0x94` | `coverMult_Low` | float |
| `+0x98` | `coverMult_Quarter` | float |
| `+0x9c` | `coverMult_None` | float |
| `+0xa0` | `flankingBonusMultiplier` | float |
| `+0xa4` | `bestCoverBonusWeight` | float |
| `+0xac` | `weaponListDistanceThreshold` | float |
| `+0xb0` | `avoidDirectThreatWeight` | float |
| `+0xb4` | `avoidIndirectThreatWeight` | float |
| `+0xb8` | `fleeWeight` | float |
| `+0xd4` | `occupiedDirectionPenalty` | float |
| `+0xd8` | `rangeScorePenalty` | float |
| `+0xdc` | `ammoScorePenalty` | float |
| `+0xe4` | `baseAttackWeight` | float |
| `+0xe8` | `ammoPressureWeight` | float |
| `+0xec` | `deployPositionWeight` | float |
| `+0xf0` | `sniperAttackWeight` | float |
| `+0x13c` | `baseThreshold` | float |
| `+0x158` | `outOfRangePenalty` | float |

### EvaluationContext / TileScoreRecord (`param_3` in Evaluate functions)

| Offset | Field | Type |
|---|---|---|
| `+0x10` | `tileRef` | ptr |
| `+0x20` | `reachabilityScore` | float |
| `+0x24` | `zoneInfluenceAccumulator` | float |
| `+0x28` | `accumulatedScore` | float |
| `+0x30` | `thresholdAccumulator` | float |
| `+0x60` | `isObjectiveTile` | bool |

### Unit

| Offset | Field | Type |
|---|---|---|
| `+0x20` | `movePool` (`unit[4]`) | ptr |
| `+0x4c` | `teamIndex` | int |
| `+0x54` | `moveRange` | int |
| `+0x5b` | `ammoSlotCount` | int |
| `+0x5c` | `currentAmmo` | int |
| `+0x60` | `squadCount` | int |
| `+0x70` | `teamId` (`unit[0xe]`) | int |
| `+0xc8` | `opponentList` (`unit[0x19]`) | ptr |
| `+0x15c` | `isDeployed` | bool |

### MovePool

| Offset | Field | Type |
|---|---|---|
| `+0x10` | `zoneData` | ptr |
| `+0x18` | `maxMovePoints` | int |
| `+0x51` | `wakeupPending` | bool |

### TileModifier (struct at `zoneData +0x310`)

| Offset | Field | Type |
|---|---|---|
| `+0x14` | `minThresholdScale` | float |
| `+0x18` | `thresholdMultiplier` | float |
| `+0x20` | `distanceScaleFactor` | float |
| `+0x44` | `effectImmunityMask` | uint |

### MoveRangeData

| Offset | Field | Type |
|---|---|---|
| `+0x10` | `attackRange` | float |
| `+0x14` | `ammoRange` | float |
| `+0x18` | `moveCostNorm` | float |
| `+0x1c` | `moveCostToTile` | float |
| `+0x20` | `maxReachability` | float |
| `+0x24` | `canAttackFromTile` | bool |
| `+0x25` | `canFullyReach` | bool |
| `+0x28` | `tileScorePtr` | ptr |

### ScoringContext (singleton via `DAT_183981F50 +0xb8`)

| Offset | Field | Type |
|---|---|---|
| `+0x28` | `tileGrid` | ptr |
| `+0x60` | `phase` (0=deploy, 1=std, 2=post) | int |
| `+0xa8` | `avoidGroups` | array |

---

## Functions — leaf-first ordering

---

## F1 — `Criterion..ctor` — `0x1804EB570`

### Raw Ghidra output
```c
void FUN_1804eb570(undefined8 param_1)
{
  FUN_1804f7ee0(param_1,0);
  return;
}
```

### Annotated reconstruction
```c
// Criterion..ctor
// VA: 0x1804EB570 | RVA: 0x4EB570
// Shared by all Criterion subclasses except WakeUp.
// Stateless: Criterion carries no instance fields.

void Criterion_ctor(Criterion* self)
{
    object_ctor(self);   // FUN_1804f7ee0 = object::.ctor — pass-through, no custom init
}
```

---

## F2 — `WakeUp..ctor` — `0x180518FA0`

### Raw Ghidra output
```c
void FUN_180518fa0(undefined8 param_1)
{
  FUN_1804eb570(param_1,0);
  return;
}
```

### Annotated reconstruction
```c
// WakeUp..ctor
// VA: 0x180518FA0 | RVA: 0x518FA0
// Divergent .ctor slot is a compiler artefact — body is identical to Criterion_ctor.
// WakeUp has no instance fields beyond those inherited from Criterion.

void WakeUp_ctor(WakeUp* self) {
    Criterion_ctor(self, 0);   // FUN_1804eb570 — delegate to base, no additional init
}
```

---

## F3 — `ThreatFromOpponents.GetThreads` — `0x18054E040`

### Raw Ghidra output
```c
undefined8 FUN_18054e040(void)
{
  return 4;
}
```

### Annotated reconstruction
```c
// ThreatFromOpponents.GetThreads
// VA: 0x18054E040 | RVA: 0x54E040
// Returns hardcoded 4. All other criteria use the default thread count (1).
// ThreatFromOpponents is by far the most computationally expensive criterion.

int ThreatFromOpponents_GetThreads() {
    return 4;
}
```

---

## F4 — `Criterion.IsDeploymentPhase` — `0x18071B670`

### Raw Ghidra output
```c
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
```

### Annotated reconstruction
```c
// Criterion.IsDeploymentPhase
// VA: 0x18071B670 | RVA: 0x71B670
// Checks if the game is currently in the deployment phase (phase 0).

bool Criterion_IsDeploymentPhase() {
    // IL2CPP lazy init — omitted
    ScoringContext* ctx = ScoringContext_class.staticFields->singleton;   // DAT_183981f50 +0xb8
    if (ctx != null) {
        return ctx->phase == 0;   // +0x60; 0=deployment, 1=standard, 2=post-deployment
    }
    NullReferenceException();   // FUN_180427d90 — does not return
}
```

---

## F5 — `CoverAgainstOpponents..cctor` — `0x18075EB00`

### Raw Ghidra output
```c
void FUN_18075eb00(void)
{
  undefined8 uVar1;
  
  if (DAT_183b93323 == '\0') {
    FUN_180427b00(&DAT_18396df28);
    FUN_180427b00(&DAT_18393fef8);
    FUN_180427b00(&DAT_1839500e8);
    DAT_183b93323 = '\x01';
  }
  uVar1 = FUN_180426ed0(DAT_18393fef8,4);
  FUN_181a8f520(uVar1,DAT_1839500e8,0);
  **(undefined8 **)(DAT_18396df28 + 0xb8) = uVar1;
  FUN_180426e50(*(undefined8 *)(DAT_18396df28 + 0xb8),uVar1);
  return;
}
```

### Annotated reconstruction
```c
// CoverAgainstOpponents..cctor (static constructor)
// VA: 0x18075EB00 | RVA: 0x75EB00
//
// DAT_18396df28 = CoverAgainstOpponents_class
// DAT_18393fef8 = float type descriptor (System.Single)
// DAT_1839500e8 = float[] type descriptor (System.Single[])

void CoverAgainstOpponents_cctor(void)
{
    // IL2CPP lazy init — omitted

    // Allocate COVER_PENALTIES as float[4]
    float[] penalties = Array_CreateInstance(typeof(float), 4);   // FUN_180426ed0

    Array_SetElementType(penalties, typeof(float[]));              // FUN_181a8f520

    // Assign to static field CoverAgainstOpponents.COVER_PENALTIES
    CoverAgainstOpponents.staticFields->COVER_PENALTIES = penalties;
    // write barrier — GC notification, no logic

    // NOTE: The actual float values are NOT written here.
    // [UNCERTAIN: values may be zero-initialised by the runtime, or written by
    //  element stores in the assembly listing not visible to the decompiler.
    //  Resolve by memory dump at runtime or viewing .cctor assembly.]
}
```

---

## F6 — `GetTileZoneModifier` — `0x18071AE10`

### Raw Ghidra output
```c
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
```

### Annotated reconstruction
```c
// GetTileZoneModifier
// VA: 0x18071AE10 | RVA: 0x71AE10
// Returns the TileModifier struct for a tile's zone descriptor.
// Called by GetUtilityThreshold, DistanceToCurrentTile, ExistingTileEffects, ConsiderZones.

TileModifier GetTileZoneModifier(OpponentList* opponentList) {
    ZoneDescriptor* zone = opponentList->zoneDescriptor;   // opponentList +0x18
    if (zone != null) {
        ZoneData* zoneData = zone->vtable->GetStatusEffects(zone);   // vtable +0x398
        if (zoneData != null) {
            return *(TileModifier*)(zoneData + 0x310);   // TileModifier at fixed offset
        }
    }
    NullReferenceException();   // FUN_180427d90 — does not return
}
```

---

## F7 — `IsWithinRangeB` — `0x1806E33A0`

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
```

### Annotated reconstruction
```c
// IsWithinRangeB
// VA: 0x1806E33A0 | RVA: 0x6E33A0
// AND-gate: every weapon slot on the tile must individually pass its range condition.
// Returns true only if all slots pass; false immediately on any failure.

bool IsWithinRangeB(Tile* tile, Unit* unit, Unit* target) {
    List* slots = tile->weaponSlots;   // tile +0x48 — tile-side weapon slot list
    uint i = 0;
    while (slots != null) {
        if (slots->count <= (int)i) {
            return true;   // exhausted all slots — all passed
        }
        if (slots->count <= i) IndexOutOfRangeException();   // FUN_180427d80

        WeaponSlot* slot = slots->items[i];   // slots +0x20 + i*8
        if (slot == null) break;

        bool pass = slot->vtable->CheckRangeCondition(slot, unit, target);   // vtable +0x1d8
        if (!pass) {
            return false;   // any failure = immediate false
        }
        i++;
        slots = tile->weaponSlots;   // re-read in case list mutated
    }
    NullReferenceException();   // null slot list — does not return
}
```

---

## F8 — `IsWithinRangeA` — `0x1806E3C50`

### Raw Ghidra output
```c
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
```

### Annotated reconstruction
```c
// IsWithinRangeA
// VA: 0x1806E3C50 | RVA: 0x6E3C50
// Four-stage range gate. Used by ThreatFromOpponents.Score (A) for each weapon slot.

bool IsWithinRangeA(Tile* tile, Unit* unit, TileScore* scoreObj, ushort rangeType) {
    // Gate 1: range type must be valid for this tile
    if (!IsValidRangeType(tile, rangeType)) return false;   // FUN_1806e3d50

    uint scoreIndex = GetThreadScoreIndex(tile);   // FUN_1806d5040

    // Lazily resolve the score object if not provided
    if (scoreObj == null) {
        if (tile->tileData == null) NullReferenceException();
        scoreObj = FetchScoredTileData(tile->tileData, scoreIndex, unit);   // FUN_1806f9f20
    }

    TileData* data = tile->tileData;   // tile +0x10
    if (data == null) NullReferenceException();

    // Gate 2: if tile has no range constraint, always passes
    if (!data->hasRangeConstraint) return true;   // data +0xe4

    // Gate 3: if tile requires context match, verify it
    if (data->hasContextRequirement) {   // data +0xf1
        if (scoreObj == null) NullReferenceException();
        if (!TileMatchesContext(scoreObj, unit)) return false;   // FUN_1806888b0
    }

    // Gate 4: both melee range AND attack range must pass
    if (IsInMeleeRange(tile, unit, scoreObj, rangeType & 0xff)) {   // FUN_1806e3750
        if (IsInAttackRange(tile, scoreObj, unit, rangeType)) {      // FUN_1806e60a0
            return true;
        }
    }
    return false;
}
```

---

## F9 — `Criterion.GetUtilityThreshold` — `0x180760070`

### Raw Ghidra output
```c
float FUN_180760070(undefined8 param_1, longlong param_2)
{
  longlong lVar1;
  float fVar2;
  float fVar3;
  
  if (DAT_183b9331b == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    DAT_183b9331b = '\x01';
  }
  if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
    il2cpp_runtime_class_init();
  }
  lVar1 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
  if (((lVar1 != 0) && (fVar2 = *(float *)(lVar1 + 0x13c), param_2 != 0)) &&
     (*(longlong *)(param_2 + 200) != 0)) {
    lVar1 = FUN_18071ae10(*(longlong *)(param_2 + 200),0);
    if (lVar1 != 0) {
      fVar3 = fVar2 * *(float *)(lVar1 + 0x14);
      if (fVar2 <= fVar3) {
        fVar2 = fVar3;
      }
      if (*(longlong *)(param_2 + 200) != 0) {
        lVar1 = FUN_18071ae10(*(longlong *)(param_2 + 200),0);
        if (lVar1 != 0) {
          return fVar2 * *(float *)(lVar1 + 0x18);
        }
      }
    }
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Criterion.GetUtilityThreshold
// VA: 0x180760070 | RVA: 0x760070
// Returns the minimum score a tile must achieve to be considered.
// Scales the base threshold up (never down) by the tile's zone modifier.
//
// param_1 = Criterion* this (unused — reads from settings singleton only)
// param_2 = TileCandidate* (source of zone descriptor at +0xC8 / offset 200)

float Criterion_GetUtilityThreshold(Criterion* self, TileCandidate* tile)
{
    // IL2CPP lazy init — omitted

    TacticalAISettings* settings = TacticalAISettings.instance;   // DAT_18394c3d0 staticFields[1]
    float baseThreshold = settings->baseThreshold;                // settings +0x13c

    ZoneDescriptor* zoneDesc = tile->zoneDescriptor;              // *(longlong*)(param_2 + 200)
    // Null-guard: if settings, tile, or zoneDesc null → NullReferenceException

    TileModifier* mod = GetTileZoneModifier(zoneDesc);            // FUN_18071ae10

    // Scale threshold: max(base, base × minScale)
    float scaled    = baseThreshold * mod->minThresholdScale;     // mod +0x14
    float threshold = (baseThreshold < scaled) ? scaled : baseThreshold;
    // equivalent: threshold = max(baseThreshold, baseThreshold × mod.minThresholdScale)

    // Second modifier fetch (same address, same result — compiler did not cache)
    mod = GetTileZoneModifier(zoneDesc);

    // Apply zone multiplier
    return threshold * mod->thresholdMultiplier;                  // mod +0x18
}

// Formula summary:
//   threshold = max(base, base × minThresholdScale) × thresholdMultiplier
```

---

## F10 — `GetTileScoreComponents` — `0x1806E0AC0`

### Raw Ghidra output
```c
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
```

### Annotated reconstruction
```c
// GetTileScoreComponents
// VA: 0x1806E0AC0 | RVA: 0x6E0AC0
// Populates a 6-slot float[] with raw scoring data for a tile.
// Callers multiply [0] by 0.01 to convert from centiscale to [0.0, 1.0].

float* GetTileScoreComponents(float[6]* out, Tile* tile, Unit* unit, ...) {
    // IL2CPP lazy init — omitted

    // Zero out all 6 components
    out[0] = out[1] = out[2] = out[3] = out[4] = out[5] = 0.0f;

    // Early exit: objective tiles always score 100
    if (tile->tileData == null) NullReferenceException();
    if (tile->tileData->isObjectiveTile) {   // tileData +0xf3
        *(bool*)(out + 4) = true;            // out[4] = isObjective flag
        out[0] = 100.0f;
        return out;
    }

    // Lazily resolve score object (thread-aware path omitted for clarity)

    // Slot [1]: tile base value
    out[1] = GetTileBaseValue(scoreObj);              // FUN_180628270

    // Slot [2]: derived score component
    out[2] = GetDerivedScoreComponent(...);           // FUN_1806debe0

    // Slot [3]: movement effectiveness index
    out[3] = GetMovementEffectivenessValue();         // FUN_180531700

    // Slot [0]: raw score, computed then clamped
    float rawScore = ...;   // formula varies by path (distance-adjusted or base)
    rawScore = clamp(rawScore, 0.0f, 100.0f);
    int minScore = scoreObj->minScoreFloor;           // scoreObj +0x78
    if (rawScore < (float)minScore) rawScore = (float)minScore;
    out[0] = rawScore;                                // centiscale [0–100]

    return out;
}
```

---

## F11 — `GetMoveRangeData` — `0x1806DF4E0`

### Raw Ghidra output
```c
longlong FUN_1806df4e0(longlong param_1, ...)
{
  // [full raw output — 350 lines]
  // Populates MoveRangeData object param_9:
  //   +0x10 = attackRange, +0x14 = ammoRange, +0x18 = moveCostNorm,
  //   +0x1c = moveCostToTile, +0x20 = maxReachability,
  //   +0x24 = canAttackFromTile, +0x25 = canFullyReach, +0x28 = tileScorePtr (write-barriered)
  // expf called: expf(1.0 - tile.accuracyDecay * 0.01) for range step penalty
}
```

### Annotated reconstruction
```c
// GetMoveRangeData
// VA: 0x1806DF4E0 | RVA: 0x6DF4E0
// Populates a MoveRangeData struct for a unit→tile pair.

MoveRangeData* GetMoveRangeData(Tile* tile, Unit* unit, ..., MoveRangeData* out) {
    // IL2CPP lazy init — omitted

    if (out == null) out = new MoveRangeData();

    // Resolve score object for this tile
    out->tileScorePtr = GetScoredTileData(...);   // FUN_1806f2230; write barrier applied

    float effectivenessRatio = GetMovementEffectivenessValue();   // FUN_180531700

    // Movement costs from TileScore object (param_6)
    float costPerStep   = tileScore->moveCostPerStep;    // tileScore +0x128
    float secondaryCost = tileScore->secondaryCost;      // tileScore +0x110
    float tertiaryCost  = tileScore->tertiaryCost;       // tileScore +0x13c

    // Attack range
    float rawAttack = max(unit->moveRange * tileScore->attackRangeScale,    // +0x144, unit +0x54
                          tileScore->attackRangeMin);                         // +0x148

    // Ammo range
    float rawAmmo   = max(unit->ammoSlotCount * tileScore->ammoRangeScale,  // +0x14c, unit +0x5b
                          tileScore->ammoRangeMin);                           // +0x150

    // Primary score formula
    float baseScore = (rawAttack + moveCostAdjust + baseValue + distCost + rawAmmo)
                      * effectivenessRatio
                      * tileScore->multiplier       // tileScore +0x8c
                      * tileScore->primaryWeight;   // tileScore +0x140

    // Ammo survival fraction
    float reloadChance = GetReloadChance(unit);             // FUN_180614b30
    float ammoFrac = clamp((reloadChance * attacksInRange - ammoUsed * 3) * 0.01f, 0, 1);

    // Range step penalty via expf
    float accuracyDecay    = tile->accuracyDecay * 0.01f;   // tile +0x244
    float rangePenaltyMult = expf(1.0f - accuracyDecay);    // FUN_1804bad80
    float rangeStepCount   = GetRangeStepCount(tile, weapon);
    rangePenaltyMult       = max(rangePenaltyMult * rangeStepCount, 1.0f);

    // Write all output fields
    out->attackRange      = baseScore * survivor;           // +0x10
    out->ammoRange        = ammoScore;                      // +0x14
    out->moveCostNorm     = clamp(moveCostRatio, 0, squadCount);  // +0x18
    out->moveCostToTile   = moveCostRatio;                  // +0x1c
    out->maxReachability  = max(prev, reachability);        // +0x20
    out->canAttackFromTile = canFullAttack;                 // +0x24
    out->canFullyReach     = canReach;                      // +0x25
    return out;
}
```

---

## F12 — `DistanceToCurrentTile.Evaluate` — `0x180760CF0`

### Raw Ghidra output
```c
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
```

### Annotated reconstruction
```c
// DistanceToCurrentTile.Evaluate
// VA: 0x180760CF0 | RVA: 0x760CF0
// Accumulates a reachabilityScore on ctx proportional to distance from the unit's
// current tile, modulated by zone scale, with an out-of-range penalty.

void DistanceToCurrentTile_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    if (unit == null) return;

    int moveSpeed    = unit->vtable->GetMoveSpeed(unit);                     // vtable +0x458
    WeaponData* wpn  = unit->vtable->GetStatusEffects(unit);                 // vtable +0x398
    if (wpn == null || wpn->weaponStatsBlock == null) NullReferenceException();   // +0x2b0

    int baseRange    = wpn->weaponStatsBlock->baseRange;                     // +0x118
    WeaponList* wl   = unit->vtable->GetWeaponList(unit);                    // vtable +0x3d8
    if (wl == null) NullReferenceException();

    int effectiveRange = max(baseRange + wl->bonusRange, 1);                 // wl +0x3c

    if (ctx == null) NullReferenceException();
    Tile* tile     = ctx->tileRef;                                           // ctx +0x10
    Tile* myTile   = unit->vtable->GetTilePosition(unit);                    // vtable +0x388
    if (tile == null) NullReferenceException();

    int dist         = GetTileDistance(tile, myTile);                        // FUN_1805ca7a0
    float prev       = ctx->reachabilityScore;                               // ctx +0x20

    if (unit->opponentList == null) NullReferenceException();
    TileModifier mod = GetTileZoneModifier(unit->opponentList);              // FUN_18071ae10
    float modScale   = mod.distanceScaleFactor;                              // mod +0x20

    float penalty;
    if (moveSpeed / effectiveRange < dist) {
        penalty = settings->outOfRangePenalty;                               // settings +0x158
    } else {
        penalty = 1.0f;
    }

    ctx->reachabilityScore = (float)dist * modScale * penalty + prev;        // ctx +0x20
}
```

---

## F13 — `AvoidOpponents.Evaluate` — `0x18075BE10`

### Raw Ghidra output
```c
void FUN_18075be10(undefined8 param_1,longlong param_2,longlong param_3)
{
  // [full raw output — 120 lines]
  // Reads ScoringContext.singleton +0xa8 -> avoid group array
  // Outer loop: each group; skip if group.teamId == unit.teamId (unit +0x4c)
  // Inner loop: foreach tile in group.tileList
  //   if TileTeamMatches(tile, unit.teamId):
  //     dist = GetTileDistance(ctx.tileRef, tile.position)
  //     if dist < 11:
  //       if vtable+0x188(group, unit.teamId) == false: fAccum += expf(settings +0xb4)
  //       else:                                         fAccum += expf(settings +0xb0)
  // ctx.accumulatedScore += fAccum
}
```

### Annotated reconstruction
```c
// AvoidOpponents.Evaluate
// VA: 0x18075BE10 | RVA: 0x75BE10
// Accumulates an expf-scaled penalty for tiles near opponent groups
// that CANNOT directly target the unit (indirect area threat).

void AvoidOpponents_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    float fAccum = 0.0f;

    if (ScoringContext_singleton == null) NullReferenceException();
    Array* groups = ScoringContext_singleton->avoidGroups;   // singleton +0xa8
    if (groups == null) NullReferenceException();

    for (uint i = 0; i < groups->count; i++) {
        OpponentGroup* group = groups->items[i];
        if (group == null) NullReferenceException();

        if (group->teamId != unit->teamId) {   // group +0x14, unit +0x4c — skip same team
            if (group->tileList == null) NullReferenceException();

            foreach (Tile* tile in group->tileList) {
                if (!TileTeamMatches(tile, unit->teamId)) continue;   // FUN_1805dfab0

                int dist = GetTileDistance(ctx->tileRef, tile->vtable->GetTilePosition(tile));
                if (dist < 11) {
                    bool canTarget = group->vtable->CanTargetTeam(group, unit->teamId);  // vtable +0x188
                    if (!canTarget) {
                        fAccum += expf(settings->avoidIndirectThreatWeight);   // +0xb4, FUN_1804bad80
                    } else {
                        fAccum += expf(settings->avoidDirectThreatWeight);     // +0xb0
                    }
                }
            }
        }
    }

    if (ctx == null) NullReferenceException();
    ctx->accumulatedScore += fAccum;   // ctx +0x28
}
```

---

## F14 — `FleeFromOpponents.Evaluate` — `0x1807613A0`

### Raw Ghidra output
```c
void FUN_1807613a0(undefined8 param_1,longlong param_2,longlong param_3,undefined8 param_4)
{
  // [full raw output — 115 lines, structurally identical to AvoidOpponents]
  // Key differences from AvoidOpponents:
  //   dist < 0x10 (16) not 0xb (11)
  //   only accumulates when group CAN target unit (polarity inverted)
  //   weight: settings +0xb8 (fleeWeight)
}
```

### Annotated reconstruction
```c
// FleeFromOpponents.Evaluate
// VA: 0x1807613A0 | RVA: 0x7613A0
// Mirror of AvoidOpponents with inverted CanTarget polarity and larger radius (16).
// Accumulates penalty for tiles near groups that CAN directly target the unit.

void FleeFromOpponents_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    float fAccum = 0.0f;

    Array* groups = ScoringContext_singleton->avoidGroups;   // singleton +0xa8

    for (uint i = 0; i < groups->count; i++) {
        OpponentGroup* group = groups->items[i];
        if (group->teamId == unit->teamId) continue;   // skip same team

        foreach (Tile* tile in group->tileList) {
            if (!TileTeamMatches(tile, unit->teamId)) continue;

            int dist = GetTileDistance(ctx->tileRef, tile->vtable->GetTilePosition(tile));

            if (dist < 16) {   // ← larger radius than AvoidOpponents
                bool canTarget = group->vtable->CanTargetTeam(group, unit->teamId);  // vtable +0x188
                if (canTarget) {   // ← only when CAN target (opposite of AvoidOpponents)
                    fAccum += expf(settings->fleeWeight);   // settings +0xb8
                }
            }
        }
    }

    ctx->accumulatedScore += fAccum;   // ctx +0x28
}
```

---

## F15 — `ExistingTileEffects.Evaluate` — `0x180760FB0`

### Raw Ghidra output
```c
void FUN_180760fb0(undefined8 param_1,longlong *param_2,longlong param_3)
{
  // [full raw output — 285 lines; type-check section partially truncated]
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
  // [TRUNCATED — type-check logic partially captured]
}
```

### Annotated reconstruction
```c
// ExistingTileEffects.Evaluate
// VA: 0x180760FB0 | RVA: 0x760FB0
// Scores tiles carrying active effects matching the unit's type,
// filtered by the zone's effect immunity mask.

void ExistingTileEffects_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    if (ctx == null || ctx->tileRef == null) return;

    if (!HasTileEffects(ctx->tileRef)) return;   // FUN_180688850

    TileModifier mod = GetTileZoneModifier(unit->opponentList);
    uint immunityMask = mod.effectImmunityMask;   // mod +0x44

    Tile* tile    = ctx->tileRef;
    List* effects = tile->effectList;   // tile +0x68

    foreach (TileEffect* effect in effects) {
        EffectDescriptor* desc = effect->vtable->GetDescriptor(effect);   // vtable +0x178
        uint effectFlags = desc->flags;   // desc +0x88

        // Skip if zone fully immunises this effect
        if (effectFlags != 0 && (effectFlags & immunityMask) == effectFlags) continue;

        // IL2CPP subtype check vs DAT_183952b10 and DAT_183952a58 — omitted
        // [UNCERTAIN: truncated; exact subtype requirements not fully captured]

        if (!CheckEffectFlag(effect->slot, 0x0e)) continue;   // FUN_180513400
        // flag 0xa0 also checked with tile position comparison

        if (tile->hasTileEffect) {   // tile +0xf2
            float score = Criterion_Score(unit, effectTile, ctx->tileRef, ctx->tileRef, 1);  // FUN_180760140
            ctx->accumulatedScore +=
                settings->tileEffectMultiplier * score * settings->tileEffectScoreWeight;    // +0x7c, +0x78
        }
    }
}
```

### ExistingTileEffects.Evaluate — design notes
The IL2CPP subtype check logic (lines ~220–255 of the raw output) was partially truncated. The check uses the vtable depth comparison pattern (`*(byte*)(vtable + 0x130)`) against two registered class descriptors (`DAT_183952b10`, `DAT_183952a58`). The scoring write path is fully confirmed.

---

## F16 — `ConsiderZones.Evaluate` — `0x18075CC20`

### Raw Ghidra output
```c
void FUN_18075cc20(undefined8 param_1,longlong *param_2,longlong param_3)
{
  // [full raw output — 275 lines]
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
```

### Annotated reconstruction
```c
// ConsiderZones.Evaluate
// VA: 0x18075CC20 | RVA: 0x75CC20
// Processes zone flag bitmasks to adjust ctx.thresholdAccumulator and
// ctx.zoneInfluenceAccumulator. Flag 0x01 and 0x04 force tiles above threshold
// by writing 9999.0 — this is a bypass, not a real score.

void ConsiderZones_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    if (unit == null) NullReferenceException();

    int moveRange = unit->vtable->GetEnemyCount(unit);   // vtable +0x468 (reused for moveRange)
    if (moveRange < 2) return;

    if (unit->opponentList == null) NullReferenceException();
    ZoneList* zl = GetZoneList(unit->opponentList);       // FUN_18071b640
    if (zl == null || zl->tileList == null) NullReferenceException();
    List* tiles  = zl->tileList;
    if (tiles->count == 0) return;

    float threshold = GetUtilityThreshold(self, unit, 0);   // FUN_180760070

    foreach (ZoneTile* zt in tiles) {

        // Flag 0x01 — zone membership: unconditionally force tile above threshold
        if (TileHasZoneFlag(zt, 1)) {              // FUN_180741770
            ctx->thresholdAccumulator += 9999.0f;  // ctx +0x30 — bypass, not a score
        }

        // Flag 0x10 — proximity influence on zoneInfluenceAccumulator
        if (!TileHasZoneFlag(zt, 0x10)) {
            // No zone list path: secondary weight
            int dist2  = GetTileGridDistance(zt->coords, ctx->tileRef);   // FUN_18053feb0, capped at 20
            float sign = TileHasZoneFlag(zt, 8) ? -1.0f : 1.0f;          // flag 8 = repulsion
            ctx->zoneInfluenceAccumulator +=                               // ctx +0x24
                settings->zoneInfluenceSecondaryWeight * (float)dist2      // settings +0x5c
                * zt->influenceValue * sign;                               // zt +0x24
        } else {
            // Has zone list: primary weight
            int dist  = GetTileGridDistance(zt->coords, ctx->tileRef);
            float sign = TileHasZoneFlag(zt, 8) ? -1.0f : 1.0f;
            ctx->zoneInfluenceAccumulator +=
                settings->zoneInfluenceWeight * (float)dist                // settings +0x58
                * zt->influenceValue * sign;
        }

        // Flag 0x04 — team ownership
        if (TileHasZoneFlag(zt, 4)) {
            if (TileCoordsMatch(zt->coords, ctx->tileRef)) {   // FUN_1805406a0
                ctx->thresholdAccumulator += 9999.0f;           // same team: force promotion
            }
        }

        // Post-tile threshold write
        float tileInfluence = zt->influenceValue * threshold;   // zt +0x24
        if (TileCoordsMatch(zt->coords, ctx->tileRef)) {
            float contribution = tileInfluence * settings->zoneThresholdWeight_A;   // settings +0x68
            ctx->thresholdAccumulator += max(contribution, threshold);
        } else {
            float contribution = tileInfluence * settings->zoneThresholdWeight_B;   // settings +0x6c
            ctx->thresholdAccumulator += max(contribution, threshold);
        }

        // Flag 0x20 — outer boundary: continue (loop terminator role)
    }
}
```

---

## F17 — `ConsiderZones.PostProcess` — `0x18075D3B0`

### Raw Ghidra output
```c
void FUN_18075d3b0(undefined8 param_1,longlong *param_2,longlong param_3,undefined8 param_4)
{
  // [full raw output — 205 lines]
  // Pass 1: scan zone tiles for TileHasZoneFlag(tile, 3) — if found, isObjectiveFlag = true
  // Pass 2: iterate score dictionary param_3
  //   For each entry where ctx.thresholdAccumulator >= threshold:
  //     Find matching objective zone tile
  //     Get zoneMultiplier: if unit.statusEffects +0x8c == 1 then settings +0x64 else settings +0x60
  //     ctx.accumulatedScore *= zoneMultiplier  (for tiles at zone position)
  //     ctx.thresholdAccumulator += fVar6       (for other tiles if isObjectiveFlag)
}
```

### Annotated reconstruction
```c
// ConsiderZones.PostProcess
// VA: 0x18075D3B0 | RVA: 0x75D3B0
// Two-pass. Pass 1 scans for objective zone tiles (flag 3).
// Pass 2 applies a zone score multiplier to tiles that passed the threshold.

void ConsiderZones_PostProcess(void* self, Unit* unit, ScoreDict* dict, void* param4) {
    // IL2CPP lazy init — omitted
    if (unit == null || unit->opponentList == null) return;

    ZoneList* zl = GetZoneList(unit->opponentList);
    if (zl == null || zl->tileList == null || zl->tileList->count == 0) return;

    // Pass 1: search for an objective zone tile (flag 3 = bits 1+2 combined)
    bool isObjectiveFlag = false;
    foreach (ZoneTile* zt in zl->tileList) {
        if (TileHasZoneFlag(zt, 3)) {   // FUN_180741770
            isObjectiveFlag = true;
            break;
        }
    }

    float threshold = GetUtilityThreshold(self, unit, isObjectiveFlag ? 1 : 0);

    if (dict == null) return;

    // Pass 2: iterate all scored tiles
    foreach (KeyValuePair<Tile, TileCtx> entry in dict) {
        TileCtx* ctx = entry.value;
        if (ctx->thresholdAccumulator < threshold) continue;   // ctx +0x30

        // Determine zone multiplier from unit status
        StatusEffects* status = unit->vtable->GetStatusEffects(unit);   // vtable +0x398
        float zoneMultiplier;
        if (status->statusField == 1) {   // status +0x8c
            zoneMultiplier = settings->zoneScoreMultiplier_B;   // settings +0x64
        } else {
            zoneMultiplier = settings->zoneScoreMultiplier_A;   // settings +0x60
        }

        // Apply to matching zone tiles; bump threshold for others
        foreach (ZoneTile* zt in zl->tileList) {
            if (!TileHasZoneFlag(zt, 3)) continue;
            if (TileCoordsMatch(zt->coords, ctx->tileRef)) {   // FUN_1805406a0
                ctx->accumulatedScore *= zoneMultiplier;        // ctx +0x28
            } else if (isObjectiveFlag) {
                ctx->thresholdAccumulator += fVar6;             // ctx +0x30, zone threshold bonus
            }
        }
    }
}
```

---

## F18 — `CoverAgainstOpponents.Evaluate` — `0x18075DAD0`

### Raw Ghidra output

*(Full raw output is 988 lines. Structurally representative excerpt shown; complete listing in decompiled_functions.txt.)*

```c
void FUN_18075dad0(undefined8 param_1, longlong *param_2, longlong param_3)
{
  // [IL2CPP init guard — 9 classes including TacticalAISettings, CoverAgainstOpponents]
  if (DAT_183b93322 == '\0') { /* ... */ DAT_183b93322 = '\x01'; }

  // Guard: opponentList non-empty and ctx valid
  if ((param_2 == 0) || (param_2[0x19] == 0) || ...) goto ABORT;

  // IsCurrentTile check
  cVar5 = FUN_1806889c0(*(longlong*)(param_3 + 0x10), 0);   // IsCurrentTile

  if (cVar5 == '\0') {
    // Phase 1 — occupied tile checks and penalties
    plVar13 = FUN_180688600(*(longlong*)(param_3 + 0x10), 0);   // GetUnitOnTile
    if (plVar13 != param_2) {
      if (cVar4 != '\0') { return; }
      // ... team/target checks, weapon range/ammo penalties ...
      *(float*)(param_3 + 0x28) -= (float)iVar6 * *(float*)(lVar16 + 0xd8);   // rangeScorePenalty
      *(float*)(param_3 + 0x28) -= (float)iVar12 * *(float*)(lVar16 + 0xdc);  // ammoScorePenalty
      *(float*)(param_3 + 0x30) += FUN_180760070(param_1, param_2, 0);        // thresholdAccumulator
    }
  }
  // Phase 2 — cover quality iteration (foreach enemy in opponentList)
  // Phase 3 — final write to ctx.accumulatedScore
  // ... [full 988-line body] ...
ABORT:
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// CoverAgainstOpponents.Evaluate
// VA: 0x18075DAD0 | RVA: 0x75DAD0
// Evaluates cover quality against all known opponents for the candidate tile.
// Writes weighted cover score to ctx.accumulatedScore.
//
// param_1 = CoverAgainstOpponents* this (stateless — unused)
// param_2 = Unit* (AI-controlled unit)
// param_3 = EvaluationContext*

void CoverAgainstOpponents_Evaluate(
    CoverAgainstOpponents* self,
    Unit*                  unit,
    EvaluationContext*     ctx)
{
    // IL2CPP lazy init — 9 classes — omitted

    // ── GUARD ──────────────────────────────────────────────────────────────
    OpponentList* opponentList = unit->opponentList;          // unit[0x19] = unit +0xC8
    if (unit == null || opponentList == null) goto ABORT;
    void* opponentListContents = opponentList->field_0x10;
    if (opponentListContents == null) goto ABORT;
    bool opponentListNonEmpty = IsListNonEmpty(opponentListContents);   // FUN_180717870
    if (ctx == null || ctx->tileRef == null) goto ABORT;

    // ── PHASE 1 — OCCUPIED TILE PENALTIES ──────────────────────────────────
    bool isCurrentTile = IsCurrentTile(ctx->tileRef);   // FUN_1806889c0

    if (!isCurrentTile) {
        Unit* tileOccupant = GetUnitOnTile(ctx->tileRef);   // FUN_180688600
        if (tileOccupant != unit) {
            // Tile is occupied by another unit
            if (opponentListNonEmpty) {
                return;   // allied tile with opponents active — skip
            }

            int myTeamId     = unit->teamId;              // unit[0xe] = unit +0x70
            int occupantTeam = tileOccupant->teamId;
            if (myTeamId != occupantTeam) {
                bool canTarget = CanTargetUnit(unit, tileOccupant);   // FUN_1806169a0
                if (!canTarget) return;
            }

            Weapon* weapon  = GetUnitWeapon(tileOccupant)->weaponSlot;   // vtable +0x398
            bool isRanged   = IsRangedWeapon(weapon);                    // FUN_1829a9340
            int weaponRange = isRanged ? GetWeaponRange(weapon) : 0;     // FUN_1806d7700
            int weaponAmmo  = isRanged ? weapon->field_0x64 : 0;

            TacticalAISettings* settings = TacticalAISettings.instance;
            ctx->accumulatedScore -= (float)weaponRange * settings->rangeScorePenalty;  // settings +0xd8
            ctx->accumulatedScore -= (float)weaponAmmo  * settings->ammoScorePenalty;   // settings +0xdc

            float tileThreshold = GetUtilityThreshold(self, unit);   // FUN_180760070
            ctx->thresholdAccumulator += tileThreshold;               // ctx +0x30
        }
    }

    // ── PHASE 2 — COVER QUALITY ITERATION ──────────────────────────────────
    float fBestCover = 0.0f;
    float fSumCover  = 0.0f;

    foreach (OpponentEntry* entry in unit->opponentList->filtered(opponentFilter)) {

        if (!IsEnemy(entry)) continue;   // FUN_180722ed0

        Unit* enemy    = *(entry + 0x10);
        Tile* enemyTile = GetEnemyTilePosition(enemy);   // vtable *enemy +0x388

        // Classify cover type from enemy stance and equipment
        float coverMultiplier = 1.0f;
        if (enemy->isRangedUnit) {   // enemy +0x15c
            uint equipFlags = GetEquipmentFlags(enemy);   // vtable +0x3d8 → +0xec
            if ((equipFlags & 1) == 0) {
                int stanceA = GetStanceA(enemy);   // vtable +0x478
                int stanceB = GetStanceB(enemy);   // vtable +0x468
                if      (stanceA == 2)                      coverMultiplier = settings->coverMult_Full;    // +0x8c
                else if (stanceB == 1)                      coverMultiplier = settings->coverMult_Low;     // +0x94 [note: stages used different label — Low vs Partial; see Q2]
                else if (stanceA == 1 || stanceB == 2)      coverMultiplier = settings->coverMult_Partial; // +0x90
                else if (enemy->isRangedUnit)               coverMultiplier = settings->coverMult_Quarter; // +0x98
            } else {
                coverMultiplier = settings->coverMult_Full;  // +0x8c — armoured
            }
        }

        // Compute direction and proximity
        int dirIdx  = GetTileDirectionIndex(ctx->tileRef, candidateTile);   // FUN_1805ca720
        int nextDir = (dirIdx + 1) & 7;
        int prevDir = (dirIdx - 1 + 8) & 7;

        // Read COVER_PENALTIES for this direction arc
        float penalty     = COVER_PENALTIES[GetDirectionIndex(tileGrid, dirIdx)];
        float halfPenalty = rawScore * 0.5f * COVER_PENALTIES[GetDirectionIndex(tileGrid, nextDir)];
        float adjPenalty  = COVER_PENALTIES[GetDirectionIndex(tileGrid, prevDir)];

        // [front-arc path uses COVER_PENALTIES[0] for all three — omitted for brevity]

        float tileCoverScore = rawScore * 0.5f * adjPenalty
                             + halfPenalty
                             + rawScore * penalty;

        fBestCover = max(fBestCover, tileCoverScore);
        fSumCover += tileCoverScore;
    }

    // ── PHASE 3 — FINAL SCORE WRITE ────────────────────────────────────────
    float total = fSumCover + fBestCover * settings->bestCoverBonusWeight;   // settings +0xa4

    if (!isCurrentTile) {
        for (int dir = 0; dir < 8; dir++) {
            int occupied = GetDirectionIndex(ctx->tileRef, dir);
            if (occupied != 0) {
                total -= settings->occupiedDirectionPenalty;   // settings +0xd4
            }
        }
    }

    if (total != 0.0f) {
        int depth = GetMovementDepth(unit);   // FUN_180614d30 — returns -2 if deployment-locked
        if (depth != -2) {
            if (!IsChokePoint(ctx->tileRef)) {   // FUN_1805ca990
                total += 10.0f;   // bonus for non-choke-point tiles
            }
        }
    }

    if (ctx->isObjectiveTile == false) {   // ctx +0x60
        StatusEffects* effects = GetStatusEffects(unit);   // vtable +0x398
        if (effects != null && effects->field_0x310 != null) {
            if (effects->field_0x310->field_0x29 != 0) {
                total *= 0.9f;   // 10% penalty for debuffed unit on non-objective tile
            }
        }
    }

    ctx->accumulatedScore = total * settings->coverScoreWeight   // settings +0x70
                           + ctx->accumulatedScore;
    return;

ABORT:
    NullReferenceException();   // FUN_180427d90 — does not return
}
```

---

## F19 — `ThreatFromOpponents.Evaluate` — `0x18076ACB0`

### Raw Ghidra output
```c
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
```

### Annotated reconstruction
```c
// ThreatFromOpponents.Evaluate
// VA: 0x18076ACB0 | RVA: 0x76ACB0
// Two-phase threat accumulation.
// Phase 1: wounded allies on the candidate tile contribute threat weight.
// Phase 2: the scoring unit itself contributes threat regardless.

void ThreatFromOpponents_Evaluate(void* self, Unit* unit, TileCtx* ctx) {
    // IL2CPP lazy init — omitted
    if (unit == null) NullReferenceException();

    int enemyCount = unit->vtable->GetEnemyCount(unit);   // vtable +0x468
    if (enemyCount <= 1) return;

    if (ctx == null || ctx->tileRef == null) NullReferenceException();

    // Phase 1: ally occupant
    if (!IsCurrentTile(ctx->tileRef, 0)) {
        Unit* tileOccupant = GetUnitOnTile(ctx->tileRef, 0);   // FUN_180688600
        if (tileOccupant != null && unit != tileOccupant) {
            Unit* occupant2 = GetUnitOnTile(ctx->tileRef, 0);
            if (occupant2 == null) NullReferenceException();

            if (IsAllyUnit(occupant2, 0)) {   // FUN_180616af0
                int maxMoves  = unit->movePool->maxMovePoints;   // unit[4] +0x18
                long weaponCnt = unit->weaponListCount;           // unit[5]

                float scoreB       = (float)ThreatFromOpponents_ScoreB(self, unit, occupant2, ctx, 0);
                float W_threat     = settings->W_threat;          // settings +0x74
                float healthRatio  = GetHealthRatio(occupant2, 0);   // FUN_1806155c0

                float contribution = (2.0f - healthRatio)
                                     * W_threat
                                     * ((float)maxMoves / (float)weaponCnt)
                                     * scoreB;
                ctx->accumulatedScore += contribution;   // ctx +0x28
            }
        }
    }

    // Phase 2: self threat (always)
    float prevScore  = ctx->accumulatedScore;
    float scoreBSelf = (float)ThreatFromOpponents_ScoreB(self, unit, unit, ctx, 0);
    float W_threat   = settings->W_threat;   // settings +0x74
    if (W_threat == 0) NullReferenceException();

    ctx->accumulatedScore = scoreBSelf * W_threat + prevScore;
}
```

---

## F20 — `ThreatFromOpponents.Score (A)` — `0x18076AF90`

### Raw Ghidra output
```c
undefined8 FUN_18076af90(undefined8 param_1,undefined8 param_2,longlong param_3, ...)
{
  // [full raw output — 337 lines]
  // Weapon loop: iterate non-ranged weapons from unit.movePool;
  //   for each: IsWithinRangeA AND IsWithinRangeB; if both pass: max(score, Criterion.Score(...))
  // Post-loop multiplier cascade: 6 conditional multipliers based on phase, cover type, flags
  // Return CONCAT44(weaponRef, fVar11)
}
```

### Annotated reconstruction
```c
// ThreatFromOpponents.Score (A)
// VA: 0x18076AF90 | RVA: 0x76AF90
// Per-weapon-per-tile threat evaluator.
// Returns packed ulong: low 32 bits = float score, high 32 bits = weapon ref flag.

ulong ThreatFromOpponents_ScoreA(void* self, Unit* unit, Unit* target,
                                  TileCtx* ctx, ...) {
    // IL2CPP lazy init — omitted
    if (target == null || !IsEnemy(target, 0)) return 0;   // FUN_180722ed0

    float maxScore = 0.0f;
    int flag = 0;

    // Iterate non-ranged weapon slots from unit.movePool
    List* weaponSlots = unit->movePool->zoneData->tileList;   // unit[4] +0x48
    foreach (WeaponSlot* slot in weaponSlots) {
        if (IsRangedWeapon(slot->weapon, 0)) continue;   // FUN_1829a91b0 — melee only

        bool rangeA = IsWithinRangeA(tile, unit, scoreObj, rangeType);   // FUN_1806e3c50
        bool rangeB = IsWithinRangeB(tile, unit, target);                  // FUN_1806e33a0
        if (!rangeA || !rangeB) continue;

        float score = (float)Criterion_Score(param5_unit, tile, param4, ctx, 0, 0);  // FUN_180760140
        if (score > maxScore) { maxScore = score; flag = slot->weaponRef; }
    }

    if (maxScore <= 0.0f) return 0;

    // Multiplier cascade
    if (unit->vtable->GetEnemyCount(unit) == 1 && phase != 2)
        maxScore *= settings->coverMult_Quarter;           // settings +0x98
    // else if not deployment, weapon not ranged:
    //   maxScore *= settings->coverMult_Full;             // settings +0x8c
    // else if phase 2, weapon not ranged:
    //   maxScore *= settings->coverMult_Low;              // settings +0x94
    // else if multiple enemies, not deployment:
    //   maxScore *= settings->coverMult_Partial;          // settings +0x90
    // if isObjectiveTile:
    //   maxScore *= settings->coverMult_None;             // settings +0x9c
    // if weapon list distance < threshold:
    //   maxScore *= settings->flankingBonusMultiplier;    // settings +0xa0

    float listDist = GetListDistanceScore(unit->movePool->zoneData->sublist, unit, typeDesc);  // FUN_181446af0
    if (listDist < settings->weaponListDistanceThreshold) {   // settings +0xac
        if (sublistA->count + sublistB->count > 1) {
            maxScore *= settings->flankingBonusMultiplier;
        }
    }

    return CONCAT44(flag, maxScore);
}
```

---

## F21 — `ThreatFromOpponents.Score (B)` — `0x18076B710`

### Raw Ghidra output
```c
void FUN_18076b710(undefined8 param_1,longlong param_2,undefined8 param_3,longlong param_4)
{
  // [full raw output — 325 lines]
  // Iterates opponent list; for each opponent:
  //   Writes ctx.isObjectiveTile via FUN_1805df360
  //   Computes halfWidth = weaponRange / (squadCapacity+1) / 2
  //   Spatial scan: nested loop over [tile ± halfWidth]
  //   For each candidate: calls Score_A; applies directional/choke/range multipliers
  //   Distance falloff: score *= (1 - dist / (halfWidth * 3))
  //   Keeps best score
  // Post-opponent: checks vtable +0x4a8 (HasOverwatch) if tile is 1 move away
}
```

### Annotated reconstruction
```c
// ThreatFromOpponents.Score (B)
// VA: 0x18076B710 | RVA: 0x76B710
// Spatial threat scorer. Scans a bounding box around each enemy and
// finds the highest-scoring position using Score (A) with spatial multipliers.
// Side effect: writes ctx.isObjectiveTile.

float ThreatFromOpponents_ScoreB(void* self, Unit* unit, Unit* subject,
                                  TileCtx* ctx, int unused) {
    // IL2CPP lazy init — omitted

    MovePool* pool = unit->movePool;                         // unit +0xc8
    if (pool == null || pool->zoneData == null) NullReferenceException();
    List* opponents = pool->zoneData->opponentTileList;      // pool +0x10 +0x48

    TileGrid* grid = ScoringContext_singleton->tileGrid;     // singleton +0x28

    float bestScore = 0.0f;
    foreach (Tile* opponentTile in opponents) {
        if (!IsEnemy(opponentTile, 0)) continue;   // FUN_180722ed0

        // Side effect: write ctx.isObjectiveTile for this opponent
        ctx->isObjectiveTile = CanReachTarget(unit, opponentTile, ...);   // FUN_1805df360, ctx +0x60

        // Compute scan radius
        int halfWidth = (weaponStatsBlock->baseRange / squadCapacity) / 2;

        // Spatial scan: ±halfWidth bounding box
        float tileBestScore = 0.0f;
        for (int cx = tile->x - halfWidth; cx <= tile->x + halfWidth; cx++) {
            for (int cy = tile->y - halfWidth; cy <= tile->y + halfWidth; cy++) {
                Tile* candidate = GetAdjacentTile(grid, cx, cy);   // FUN_1810c1fc0
                if (candidate == null) continue;

                float score = (float)ThreatFromOpponents_ScoreA(self, unit, opponentTile,
                                                                  candidate, subject, ctx->tileRef, 0);
                if (score <= 0.0f) continue;

                // Spatial multipliers (non-current-tile candidates only)
                if (candidate != tile) {
                    if (dirToEnemy == 0 && pathClearCount > 0)   score *= 1.2f;  // flanking
                    if (dirToEnemy < dirFromCurrent)             score *= 0.9f;  // moving away
                    else if (dirToEnemy > dirFromCurrent)        score *= 1.2f;  // moving toward
                    if (healthStatus >= 0 && IsChokePoint(tile)
                        && !IsChokePoint(candidate) && flankSlots->count > 2)
                                                                  score *= 0.8f;  // choke exit
                    if ((uint)weaponData->specialFlag > 0x7fffffff) score *= 1.2f;  // long-range weapon

                    // Distance falloff
                    int dist = GetTileDistance(candidate, tile);   // FUN_1805ca7a0
                    score *= (1.0f - (float)dist / ((float)halfWidth * 3.0f));
                }

                if (score > tileBestScore) tileBestScore = score;
            }
        }

        // Post-opponent: overwatch check if adjacent (dist == 1)
        if (distToOpponent == 1) {
            bool hasOverwatch = opponentTile->vtable->HasOverwatchOrReaction(opponentTile);  // vtable +0x4a8
            // [overwatch effect on score not captured in available output]
        }

        if (tileBestScore > bestScore) bestScore = tileBestScore;
    }

    return bestScore;
}
```

---

## F22 — `Roam.Collect` — `0x180768300`

### Raw Ghidra output
```c
void FUN_180768300(undefined8 param_1,longlong *param_2,longlong param_3)
{
  // [full raw output — 150 lines]
  // Guards: !IsRangedWeapon; HasRoamFlag(unit.opponentList+0x40, 0x21)
  // Computes roamRadius = moveSpeed / effectiveRange
  // Builds bounding box; filters tiles; shuffles; picks first
  // Creates or updates TileScoreObject; adds to score dictionary and global list
}
```

### Annotated reconstruction
```c
// Roam.Collect
// VA: 0x180768300 | RVA: 0x768300
// Populates candidate tile list for melee units with no active targets.
// Melee-only by structural enforcement — ranged units exit immediately.

void Roam_Collect(void* self, Unit* unit, ScoreDict* dict) {
    // IL2CPP lazy init — omitted
    if (unit == null) return;

    // Guard 1: melee units only
    WeaponData* wpn = unit->vtable->GetStatusEffects(unit);   // vtable +0x398
    if (IsRangedWeapon(wpn->weaponBlock, 0)) return;           // FUN_1829a91b0

    // Guard 2: roam behaviour flag required
    if (unit->opponentList == null) return;
    object* roamData = unit->opponentList->behaviorConfig;     // unit[0x19] +0x40
    if (roamData == null) return;
    if (!HasRoamFlag(roamData, 0x21)) return;                  // FUN_18053d700

    Tile* currentTile  = unit->vtable->GetTilePosition(unit);  // vtable +0x388
    int moveSpeed      = unit->vtable->GetMoveSpeed(unit);     // vtable +0x458
    int baseRange      = wpn->weaponStatsBlock->baseRange;     // +0x118
    int bonusRange     = unit->vtable->GetWeaponList(unit)->bonusRange;  // vtable +0x3d8, +0x3c
    int effectiveRange = max(baseRange + bonusRange, 1);
    int roamRadius     = moveSpeed / effectiveRange;
    if (roamRadius < 1) return;

    TileGrid* grid = ScoringContext_singleton->tileGrid;       // singleton +0x28
    int x0 = max(currentTile->x - roamRadius, 0);
    int x1 = min(currentTile->x + roamRadius, grid->width  - 1);
    int y0 = max(currentTile->y - roamRadius, 0);
    int y1 = min(currentTile->y + roamRadius, grid->height - 1);

    List* candidates = GetSharedTileList(SharedTileList_class);   // FUN_18000cfd0

    for (int cx = x0; cx <= x1; cx++) {
        for (int cy = y0; cy <= y1; cy++) {
            Tile* t = GetAdjacentTile(grid, cx, cy);           // FUN_1810c1fc0
            if (t == null) continue;
            if ((t->flags & 0x1) != 0) continue;              // isBlocked  (tile +0x1c bit 0)
            if ((t->flags & 0x4) != 0) continue;              // isOccupied (tile +0x1c bit 2)
            if (!IsCurrentTile(t)) continue;                   // FUN_1806889c0
            if (HasTileEffects(t)) continue;                   // FUN_180688850
            if (GetTileDistance(t, currentTile) > roamRadius) continue;
            candidates->add(t);
        }
    }

    if (candidates->count == 0) return;

    int newCount = ShuffleTileList(roamData, 0, candidates->count);   // FUN_18053d810
    Tile* chosen = candidates->items[roamRadius];

    // Create or update score entry
    float threshold = GetUtilityThreshold(self, unit, 0);   // FUN_180760070
    TileScoreObject* existing = null;
    bool found = TryGetExistingScore(dict, chosen, &existing, ScoreDictType);  // FUN_181442600

    if (!found) {
        TileScoreObject* scoreObj = new TileScoreObject();
        InitTileScore(scoreObj, chosen);                    // FUN_180741530
        scoreObj->thresholdValue = threshold * 100.0f;     // +0x30
        AddToScoreDictionary(dict, chosen, scoreObj);      // FUN_181435ba0
    } else {
        existing->thresholdValue += threshold * 100.0f;
    }

    // Add to global shared tile list
    List* globalList = GetSharedTileList(SharedTileList_class);
    globalList->vtable->AddToList(globalList, chosen, 1);   // vtable +0x188
}
```

---

## F23 — `WakeUp.Collect` — `0x180787DD0`

### Raw Ghidra output
```c
void FUN_180787dd0(undefined8 param_1,longlong param_2)
{
  // [full raw output — 85 lines]
  // Phase 1: iterate unit.movePool+0x10+0x20 (ally tile list)
  //   filter: ally+0x162 != 0 (awake), ally+0x48 == 0 (no condition), ally+0x140 < 1 (no priority)
  //   if reachable: set movePool+0x51 = 0; return
  // Phase 2: iterate unit.movePool+0x10+0x48 (opponent tile list)
  //   if opponent tile in range and team-matched: set movePool+0x51 = 0; return
}
```

### Annotated reconstruction
```c
// WakeUp.Collect
// VA: 0x180787DD0 | RVA: 0x787DD0
// Sets movePool.wakeupPending = 0 when a sleeping ally can be woken.
// Does NOT populate a tile list — behaviorally different from all other Collect overrides.

void WakeUp_Collect(void* self, Unit* unit) {
    // IL2CPP lazy init — omitted
    if (unit == null) NullReferenceException();

    MovePool* pool   = unit->movePool;                    // unit +0xc8
    if (pool == null) NullReferenceException();
    ZoneData* zone   = pool->zoneData;                    // pool +0x10
    if (zone == null || zone->tileList == null) NullReferenceException();

    // Phase 1: scan ally tile list for a wakeable sleeping ally
    List* allies = zone->allyTileList;                    // zone +0x20
    foreach (Unit* ally in allies) {
        if (ally->isAwake != 0) continue;                 // ally +0x162; 0 = sleeping
        if (ally->wakeCondition == null) continue;        // ally +0x48
        if (ally->wakePriority < 1) continue;             // ally +0x140
        if (ally == unit) break;

        bool reachable = CanReachTarget(unit, ally, 1, 0, 0, 0);   // FUN_1805df360
        if (reachable) {
            pool->wakeupPending = 0;   // pool +0x51 — signal wake action
            return;
        }
    }

    // Phase 2: fallback — opponent proximity as urgency trigger
    List* opponents = zone->opponentTileList;             // zone +0x48
    foreach (Tile* opponentTile in opponents) {
        Tile* tileRef = opponentTile->tileRef;            // +0x10
        if (tileRef == null) NullReferenceException();
        bool teamMatch = TileTeamMatches(tileRef, zone->zoneTeamId);   // FUN_1805dfab0, zone +0x14
        bool inRange   = CanReachTarget(unit, tileRef, teamMatch, 0, 0, 0);
        if (inRange) {
            pool->wakeupPending = 0;
            return;
        }
    }
}
```

---

## F24 — `Criterion.Score` — `0x180760140`

### Raw Ghidra output

*(291-line function. Key structural sections shown; complete listing in decompiled_functions.txt.)*

```c
undefined8
FUN_180760140(longlong *param_1, longlong *param_2, undefined8 param_3,
              longlong param_4, undefined4 param_5)
{
  // [IL2CPP init guard — 7 classes]

  if (param_2 != (longlong *)0x0) {
    if (param_2[3] == 0) {
      // Synchronous path
      uVar6 = thunk_FUN_1804608d0(DAT_183981fc8);
      FUN_18062a050(uVar6,0);
      (**(code **)(*param_2 + 0x2f8))(param_2,...);
    } else {
      uVar6 = FUN_1806f2460(param_2[3],...);   // async threaded score fetch
    }
    if (param_1 != (longlong *)0x0) {
      lVar7 = (**(code **)(*param_1 + 1000))(param_1,...);  // GetEnemyList
      // ...
      pfVar10 = FUN_1806e0ac0(...);              // GetTileScoreComponents
      fVar22  = *pfVar10 * 0.01;                 // rawScore
      lVar7   = FUN_1806df4e0(...);              // GetMoveRangeData
      // Phase 3: movement gating ...
      // Phase 4-7: four scoring components ...
      // Phase 8: final combination
      auVar18._0_4_ = (float)auVar17._0_8_ *
          (fVar19 * fVar24 + fVar22 * fVar13 + fVar14 * fVar20 + fVar21 * fVar23);
      return auVar18._0_8_;
    }
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
// Criterion.Score
// VA: 0x180760140 | RVA: 0x760140
// Master scoring function. Combines four independent utility components with
// a movement-effectiveness curve multiplier.
//
// param_1 = Unit*
// param_2 = TileCandidate*
// param_3 = EvaluationContext*
// param_4 = TileData*
// param_5 = int flags

float Criterion_Score(
    Unit*              unit,
    TileCandidate*     tile,
    EvaluationContext* ctx,
    TileData*          tileData,
    int                flags)
{
    // IL2CPP lazy init — omitted
    if (tile == null) goto ABORT;

    // ── PHASE 1 — TILE SCORE RETRIEVAL ─────────────────────────────────────
    TileScoreHandle tileScore;
    if (tile->field_0x18 == 0) {
        // Synchronous path
        ScoringContext* scoreCtx = AllocScoringContext(scoreCtxClass);   // thunk_FUN_1804608d0
        InitScoringObject(scoreCtx, 0);                                  // FUN_18062a050
        tileScore = tile->vtable->ScoreSync(tile, scoreCtx, ...);        // vtable +0x2f8
    } else {
        tileScore = GetThreadedTileScore(tile->field_0x18, tile, ...);   // FUN_1806f2460
    }

    if (unit == null) goto ABORT;
    EnemyList* enemies = unit->vtable->GetEnemyList(unit, ...);          // vtable +1000 (0x3E8)

    uint threadIdx = (tile->field_0x18 != 0) ? GetThreadScoreIndex(tile, 0) : 0;  // FUN_1806d5040
    TileScore* scored = GetScoredTileData(enemies, threadIdx, ctx, tileData, tile, 0);  // FUN_1806f2230

    // ── PHASE 2 — RAW SCORE ─────────────────────────────────────────────────
    float* components = GetTileScoreComponents(stackBuf, tile, ctx, tileData, tileScore,
                                               scored, 1, unit, stackArg, 0);  // FUN_1806e0ac0
    float rawScore    = components[0] * 0.01f;   // centiscale → [0.0, 1.0]

    // ── PHASE 3 — MOVEMENT GATING ──────────────────────────────────────────
    MovePool*      movePool  = unit->movePool;   // unit[4] = unit +0x20
    MoveRangeData* moveData  = GetMoveRangeData(tile, ctx, tileData, tileData, unit,
                                                 tileScore, scored, flags, 0, 0);  // FUN_1806df4e0
    if (movePool == null || moveData == null) goto ABORT;

    float rangeCost = rawScore * moveData->moveCostToTile;   // moveData +0x1c
    float maxCost   = (float)(movePool->maxMovePoints - 1);  // movePool +0x18
    if (rangeCost > maxCost) rangeCost = maxCost;
    rangeCost = floorf(rangeCost);

    float adjScore = (float)GetReachabilityAdjustedScore(tile, ctx, tileData, unit,
                                                          tileScore, scored,
                                                          (int)rangeCost, flags, 0, 0)
                     * 0.01f;   // FUN_1806e0300

    // ── PHASE 4 — COMPONENT A: ATTACK WEIGHT ───────────────────────────────
    TacticalAISettings* settings = TacticalAISettings.instance;
    float fAtk = settings->baseAttackWeight;   // settings +0xe4

    float rangeRatio = (rawScore * moveData->attackRange) / (float)unit->moveRange;  // moveData +0x10, unit +0x54
    if (rangeRatio > 2.0f) rangeRatio = 2.0f;
    fAtk = settings->baseAttackWeight * rangeRatio;

    if (rawScore * moveData->moveCostToTile >= (float)movePool->maxMovePoints) {
        fAtk *= 2.0f;
        if (GetHealthRatio(unit) > 0.95f) {   // FUN_1806155c0
            fAtk *= 4.0f;   // near-full-health + max-range = 8× base attack component
        }
    } else if (moveData->canAttackFromTile && rawScore > 0.0f) {   // moveData +0x24 (bool, not +0x25)
        fAtk *= 1.1f;
    }

    // Overwatch suppression loop (reads from DAT_18396a5e8 response curve tables)
    for (uint i = 0; i < overwatchTable.length; i++) {
        float threshold = overwatchResponseTable[i];   // DAT_18396a5e8 +0xb8 +0xd8 [i]
        float rangeGap  = ((float)unit->moveRange - rawScore * moveData->attackRange)
                          / (float)unit->field_0xB;
        if (rangeGap < threshold) {
            float mult = overwatchMultTable[i] * 0.3f * 0.01f + 1.0f;   // +0xe0 [i]
            fAtk *= mult;
        }
    }

    // ── PHASE 5 — COMPONENT B: AMMO PRESSURE ───────────────────────────────
    float fAmmo = 0.0f;
    if (rawScore * moveData->ammoRange > 0.0f) {   // moveData +0x14
        EnemyListData* wl = unit->vtable->GetWeaponList(unit);   // vtable +0x3d8
        if (wl == null) goto ABORT;

        int   enemyCount  = GetEnemyCountInRange(wl, 3, 0);   // FUN_1806283c0
        float reloadChance = GetReloadChance(unit, 0);         // FUN_180614b30

        float ammoLeft = (float)unit->currentAmmo - rawScore * moveData->ammoRange;  // unit +0x5c
        if (ammoLeft < 0.0f) ammoLeft = 0.0f;
        float teamSize = max((float)unit->squadCount, 1.0f);   // unit +0x60
        float enemyCap = min((float)enemyCount, 200.0f);

        fAmmo = (reloadChance * enemyCap - (ammoLeft / teamSize) * enemyCap)
                * settings->ammoPressureWeight   // settings +0xe8
                * enemyCap
                * 0.0001f;
    }

    // ── PHASE 6 — COMPONENT C: DEPLOYMENT/POSITIONAL BONUS ─────────────────
    float fDeploy = 0.0f;
    if (adjScore > 0.0f) {
        float combined = adjScore * rawScore + adjScore;
        if (combined > 2.0f) combined = 2.0f;
        fDeploy = combined * settings->deployPositionWeight;   // settings +0xec

        if (TileHasEnemyUnit(tileData, 0) == 0) {   // FUN_180687590
            int depth = GetMovementDepth(unit, 0, 0);   // FUN_180614d30
            fDeploy *= ((float)depth * 0.25f + 1.5f);
        }
        if (adjScore * rawScore + adjScore >= 0.67f) {
            fDeploy *= 3.0f;
        }
    }

    // ── PHASE 7 — COMPONENT D: SNIPER BONUS ────────────────────────────────
    float fSniper = 0.0f;
    TileWeaponHolder* weaponHolder = tile->field_0x10;
    if (weaponHolder != null && weaponHolder->field_0x2c8 != null) {
        if (IsInstanceOf(weaponHolder->field_0x2c8, SniperWeapon_typeDesc)) {   // DAT_18397c1e0
            float sniperWeight = settings->sniperAttackWeight;   // settings +0xf0

            int rangeSteps  = GetRangeStepCount(tile, weapon->field_0xd0, 0);  // FUN_1806defc0
            int attackCount = GetAttackCountFromTile(tile, tileScore, 0);       // FUN_1806de960

            fSniper = (float)attackCount
                      * (float)(rangeSteps * *(int*)(weaponHolder + 0x154))
                      * sniperWeight
                      * rawScore;

            if (TileHasEnemyUnit(tileData, 0) == 0) {
                int depth = GetMovementDepth(unit, 0, 0);
                fSniper *= ((float)depth * 0.25f + 1.5f);
            }

            float health = GetHealthRatio(unit);
            fSniper *= max(health, 0.25f);
        }
    }

    // ── PHASE 8 — STATUS EFFECT DEBUFF CHECK ───────────────────────────────
    StatusEffects* effects = unit->vtable->GetStatusEffects(unit);   // vtable +0x398
    if (effects != null && effects->field_0x108 != null) {
        BuffData* buff = effects->field_0x108;
        if (buff->count > 0 && rawScore * moveData->attackRange > 0.0f) {
            // Overwatch curve applied per buff entry (same DAT_18396a5e8 tables)
            // [Loop body omitted — same suppression multiplier pattern as Phase 4]
        }
    }

    // ── PHASE 9 — FINAL WEIGHTED COMBINATION ───────────────────────────────
    float W_attack = settings->W_attack;   // settings +0x7c (verify vs tileEffectMultiplier — see REPORT §8)
    float W_ammo   = settings->W_ammo;    // settings +0x80
    float W_deploy = settings->W_deploy;  // settings +0x84
    float W_sniper = settings->W_sniper;  // settings +0x88

    uint  movEffIdx  = GetMovementEffectivenessIndex(tile, unit, 0);   // FUN_1806e2400
    float movEffRaw  = movEffTable[movEffIdx];                          // DAT_18397ae78 +0xb8 [0]
    float movEff     = expf(movEffRaw + 1.0f);                         // FUN_1804bad80 (expf_approx)

    return movEff * (W_attack * fAtk
                   + W_ammo   * fAmmo
                   + W_deploy * fDeploy
                   + W_sniper * fSniper);

ABORT:
    NullReferenceException();   // FUN_180427d90 — does not return
}
```

### Criterion.Score — design notes
The four components are fully independent: each can be zero without affecting the others. The movement effectiveness curve (`expf(movEffTable[idx] + 1.0)`) acts as a global discount — a tile the unit cannot efficiently reach is penalised proportionally regardless of its cover or attack value. The overwatch suppression tables (read from `DAT_18396a5e8`) are applied twice: once to `fAtk` in Phase 4 (position-based) and again in Phase 8 (status-buff-based). Both loops use the same table data via the same indexing logic.

---

## Resolved Symbol Maps

### FUN_ → Method Name

```
FUN_1804EB570 = Criterion_ctor                      // pass-through to object::ctor
FUN_180427B00 = IL2CPP_TypeInit                     // lazy static type init guard
FUN_180427D90 = IL2CPP_NullRefAbort                 // throws NullReferenceException
FUN_180427D80 = IL2CPP_IndexOutOfRangeAbort         // throws IndexOutOfRangeException
FUN_1804F7EE0 = Enumerator_Dispose                  // end of foreach
FUN_180426E50 = IL2CPP_WriteBarrier                 // GC write barrier; no logical effect
FUN_180426ED0 = Array_CreateInstance                // allocates managed array
FUN_181A8F520 = Array_SetElementType
FUN_180CBab80 = List_GetEnumerator
FUN_1814F4770 = List_MoveNext
FUN_18136D8A0 = Dict_GetEnumerator
FUN_18152F9B0 = Dict_MoveNext
FUN_18000D310 = ComputeTileScore_Unthreaded
FUN_18000D130 = ComputeTileScore_Threaded
FUN_18000CFD0 = GetSharedTileList
FUN_180760070 = Criterion_GetUtilityThreshold       // threshold = max(base, base*minScale) * multiplier
FUN_180760140 = Criterion_Score                     // master scoring function
FUN_18071AE10 = GetTileZoneModifier                 // returns TileModifier at zoneData+0x310
FUN_1806E0AC0 = GetTileScoreComponents              // populates float[6] score component array
FUN_1806DF4E0 = GetMoveRangeData                    // populates MoveRangeData struct
FUN_1806E0300 = GetReachabilityAdjustedScore        // applies movement cost gating
FUN_1806E2400 = GetMovementEffectivenessIndex       // index into movement effectiveness table
FUN_1804BAD80 = expf_approx                         // expf-equivalent single-arg growth curve
FUN_1806155C0 = GetHealthRatio                      // unit health as float [0,1]
FUN_180614B30 = GetReloadChance                     // unit reload probability
FUN_180614D30 = GetMovementDepth                    // -2 = deployment-locked
FUN_1806F2460 = GetThreadedTileScore                // tile score from threaded pipeline
FUN_1806D5040 = GetThreadScoreIndex                 // thread-local tile score index
FUN_1806F2230 = GetScoredTileData                   // TileScore from thread-local storage
FUN_1806283C0 = GetEnemyCountInRange                // enemy count within radius
FUN_180687590 = TileHasEnemyUnit                    // non-zero if tile occupied by enemy
FUN_1806888B0 = TileMatchesContext                  // tile matches evaluation context
FUN_1806889C0 = IsCurrentTile                       // true if tile is unit's current position
FUN_180688600 = GetUnitOnTile                       // unit currently on tile
FUN_180688850 = HasTileEffects                      // true if tile has active effects
FUN_1806169A0 = CanTargetUnit                       // true if unit A can target unit B
FUN_1806D7700 = GetWeaponRange                      // weapon range stat
FUN_180717870 = IsListNonEmpty                      // true if collection non-empty
FUN_180722ED0 = IsEnemy                             // true if entity is hostile
FUN_180687660 = GetDirectionIndex                   // 0–7 directional index
FUN_1805CA990 = IsChokePoint                        // true if tile is a choke point
FUN_1805CA7A0 = GetTileDistance                     // distance between two tiles
FUN_1805CA720 = GetTileDirectionIndex               // directional index between two tiles
FUN_1806DEFC0 = GetRangeStepCount                  // range step count for weapon at tile
FUN_1806DE960 = GetAttackCountFromTile              // viable attack count from tile
FUN_180628270 = GetTileBaseValue                    // primary tile base value
FUN_1806DEBE0 = GetDerivedScoreComponent            // derived score sub-component
FUN_180531700 = GetMovementEffectivenessValue       // movement effectiveness float
FUN_18062A050 = InitScoringObject
FUN_1829A9340 = IsRangedWeapon
FUN_1829A91B0 = IsRangedWeapon_alt
FUN_1810C1FC0 = GetAdjacentTile                     // tile at grid coordinate
FUN_180616AF0 = IsAllyUnit
FUN_180741770 = TileHasZoneFlag                     // tests bitmask flag on zone tile
FUN_18053FEB0 = GetTileGridDistance                 // grid distance capped at 20
FUN_1805406A0 = TileCoordsMatch
FUN_18071B640 = GetZoneList
FUN_1806E3C50 = IsWithinRangeA                      // range gate A (4-stage)
FUN_1806E33A0 = IsWithinRangeB                      // range gate B (all weapon slots must pass)
FUN_1806E3750 = IsInMeleeRange                      // melee range sub-check (IsWithinRangeA)
FUN_1806E60A0 = IsInAttackRange                     // attack range sub-check (IsWithinRangeA)
FUN_1806E3D50 = IsValidRangeType                    // range type validity gate
FUN_1806F9F20 = FetchScoredTileData                 // fetch TileScore by index from tileData
FUN_181446AF0 = GetListDistanceScore                // distance/score metric for weapon list
FUN_180717A40 = IsUnitInactive
FUN_1805DFAB0 = TileTeamMatches                     // tile's team matches given ID
FUN_180616B50 = CanTargetTeam                       // group can target given team ID
FUN_18053D700 = HasRoamFlag                         // checks behavior flag on config object
FUN_18053D810 = ShuffleTileList
FUN_181442600 = TryGetExistingScore
FUN_180741530 = InitTileScore
FUN_181435BA0 = AddToScoreDictionary
FUN_180513400 = CheckEffectFlag
FUN_1805CA920 = GetTileCoords
FUN_1805DF360 = CanReachTarget
FUN_18052A570 = Abs
FUN_18073BCF0 = RangeContains
FUN_1806DE540 = ComputeRangeStep
```

### DAT_ → Class / Static Field

```
DAT_18394C3D0 = TacticalAISettings_class
DAT_183981FC8 = ScoringContext_class
DAT_183981F50 = ScoringContext_singleton_class        // singleton via +0xb8
DAT_18396A5E8 = OverwatchResponseCurve_class
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
DAT_183944290 = (unknown — list distance type descriptor)
DAT_183938690 = WeaponEnumeratorDispose_class
DAT_183938748 = WeaponEnumeratorMoveNext_class
DAT_183938800 = WeaponEnumerator_class
DAT_183982CF8 = RangeGate_class
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
DAT_183B9233F = IsDeploymentPhase_initFlag
```
