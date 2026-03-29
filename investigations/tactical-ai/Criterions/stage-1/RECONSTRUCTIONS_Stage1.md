# RECONSTRUCTIONS.md — Menace.Tactical.AI.Behaviors.Criterions

---

## Quick-Reference Offset Table

### AIWeightsTemplate instance (via `DAT_18394c3d0 + 0xb8 + 8`)

| Offset | Name | Used in |
|---|---|---|
| `+0x13c` | `baseThreshold` | `GetUtilityThreshold` |
| `+0x70` | `coverScoreWeight` | `CoverAgainstOpponents.Evaluate` |
| `+0x7c` | `W_attack` | `Score` |
| `+0x80` | `W_ammo` | `Score` |
| `+0x84` | `W_deploy` | `Score` |
| `+0x88` | `W_sniper` | `Score` |
| `+0x8c` | `coverMult_Full` | `CoverAgainstOpponents.Evaluate` |
| `+0x90` | `coverMult_Partial` | `CoverAgainstOpponents.Evaluate` |
| `+0x94` | `coverMult_Low` | `CoverAgainstOpponents.Evaluate` |
| `+0x98` | `coverMult_Quarter` | `CoverAgainstOpponents.Evaluate` |
| `+0x9c` | `coverMult_None` | `CoverAgainstOpponents.Evaluate` |
| `+0xa4` | `bestCoverBonusWeight` | `CoverAgainstOpponents.Evaluate` |
| `+0xd4` | `occupiedDirectionPenalty` | `CoverAgainstOpponents.Evaluate` |
| `+0xd8` | `rangeScorePenalty` | `CoverAgainstOpponents.Evaluate` |
| `+0xdc` | `ammoScorePenalty` | `CoverAgainstOpponents.Evaluate` |
| `+0xe4` | `baseAttackWeight` | `Score` |
| `+0xe8` | `ammoPressureWeight` | `Score` |
| `+0xec` | `deployPositionWeight` | `Score` |
| `+0xf0` | `sniperAttackWeight` | `Score` |

### EvaluationContext / TileScoreRecord (`param_3`)

| Offset | Name | Confirmed |
|---|---|---|
| `+0x10` | `tileRef` | confirmed |
| `+0x28` | `accumulatedScore` (writable) | confirmed |
| `+0x30` | `thresholdAccumulator` | confirmed |
| `+0x60` | `isObjectiveTile` (bool flag) | inferred |

### Unit object (`param_1` in `Score`, `param_2` in `Evaluate`)

| Offset | Name | Confirmed |
|---|---|---|
| `+0x54` | `moveRange` | confirmed |
| `+0x5c` | `currentAmmo` | confirmed |
| `+0x60` | `teamSize` | confirmed |
| `+0x70` | `teamId` | confirmed |
| `+0x20` (`[4]*8`) | `movePool` ptr | confirmed |
| `+0xC8` (`[0x19]*8`) | `opponentList` ptr | confirmed |

### MoveRangeData (returned by `GetMoveRangeData`)

| Offset | Name | Confirmed |
|---|---|---|
| `+0x10` | `attackRange` | confirmed |
| `+0x14` | `minRange` | confirmed |
| `+0x1c` | `moveCostToTile` | confirmed |
| `+0x25` | `canAttackFromTile` (bool) | confirmed |

### MovePool (`unit->movePool`)

| Offset | Name | Confirmed |
|---|---|---|
| `+0x18` | `maxMovePoints` | confirmed |

---

## Functions — ordered leaf-first, entry points last

---

## F1 — `Criterion..ctor`

### Raw Ghidra Output

```c
void FUN_1804eb570(undefined8 param_1)
{
  FUN_1804f7ee0(param_1,0);
  return;
}
```

### Annotated Reconstruction

```c
// Criterion..ctor
// VA: 0x1804EB570 | RVA: 0x4EB570
// Shared by: ALL Criterion subclasses except WakeUp
//
// Summary: Pure pass-through to object::.ctor. Criterion carries no instance fields
// and performs no custom initialisation. Stateless by design.

void Criterion_ctor(Criterion* self)
{
    object_ctor(self);  // FUN_1804f7ee0 = object::.ctor
}
```

---

## F2 — `CoverAgainstOpponents..cctor`

### Raw Ghidra Output

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

### Annotated Reconstruction

```c
// CoverAgainstOpponents..cctor  (static constructor)
// VA: 0x18075EB00 | RVA: 0x75EB00

// Static data labels:
//   DAT_18396df28 = CoverAgainstOpponents class descriptor
//   DAT_18393fef8 = float type descriptor (System.Single)
//   DAT_1839500e8 = float[] type descriptor (System.Single[])

void CoverAgainstOpponents_cctor(void)
{
    // [IL2CPP: type init — CoverAgainstOpponents, float, float[]]

    // Allocate COVER_PENALTIES as float[4]
    float[] penalties = Array_CreateInstance(typeof(float), 4);
                                    // FUN_180426ed0(float_typeDesc, 4)

    Array_SetElementType(penalties, typeof(float[]));
                                    // FUN_181a8f520 — sets managed element type

    // Assign to static field CoverAgainstOpponents.COVER_PENALTIES
    CoverAgainstOpponents.staticFields->COVER_PENALTIES = penalties;
    // [IL2CPP: write barrier — GC notification, no logic]

    // NOTE: Actual float values are NOT written here.
    // [UNCERTAIN: values may be zero-initialised by runtime, or written by
    //  element-by-element assignments in assembly not captured by decompiler.
    //  Request: memory dump of COVER_PENALTIES at runtime, or assembly listing
    //  of this function to identify any mov instructions after the array alloc.]
}
```

---

## F3 — `Criterion.GetUtilityThreshold`

### Raw Ghidra Output

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
  /* WARNING: Subroutine does not return */
  FUN_180427d90();
}
```

### Annotated Reconstruction

```c
// Criterion.GetUtilityThreshold
// VA: 0x180760070 | RVA: 0x760070
//
// Returns the minimum score a tile must achieve to be considered by this criterion.
// Scales the base threshold up (never down) based on the tile's zone modifier.
//
// param_1 = Criterion* this  (unused — reads from settings singleton only)
// param_2 = TileCandidate*  (source of zone descriptor at +0xC8 / offset 200)

float Criterion_GetUtilityThreshold(Criterion* self, TileCandidate* tile)
{
    // [IL2CPP: type init — AIWeightsTemplate]
    // [IL2CPP: ensure class init — AIWeightsTemplate]

    AIWeightsTemplate* settings = AIWeightsTemplate.instance;  // DAT_18394c3d0 staticFields[1]
    // Null-guard: if settings or tile is null → NullReferenceException (abort)

    float baseThreshold = settings->baseThreshold;  // settings + 0x13c

    // tile->field_0xC8 is the zone descriptor pointer (offset 200 = 0xC8)
    ZoneDescriptor* zoneDesc = tile->zoneDescriptor;  // *(longlong*)(param_2 + 200)
    // Null-guard: if zoneDesc is null → abort

    TileModifier* modifier = GetTileZoneModifier(zoneDesc);  // FUN_18071ae10
    // Null-guard: if modifier is null → abort

    // Scale threshold up, never below base
    // modifier->field_0x14 = minThresholdScale
    float scaled = baseThreshold * modifier->minThresholdScale;
    float threshold = (baseThreshold < scaled) ? scaled : baseThreshold;
    // equivalent: threshold = max(baseThreshold, baseThreshold * modifier.minThresholdScale)

    // Second modifier fetch (possible cache miss; same address, same result)
    modifier = GetTileZoneModifier(zoneDesc);  // FUN_18071ae10 — called twice
    // Null-guard: if modifier null → abort

    // Apply zone multiplier
    // modifier->field_0x18 = thresholdMultiplier
    return threshold * modifier->thresholdMultiplier;
}

// Formula:
//   threshold = max(base, base × modifier.minScale) × modifier.multiplier
```

---

## F4 — `CoverAgainstOpponents.Evaluate`

### Raw Ghidra Output

```c
void FUN_18075dad0(undefined8 param_1, longlong *param_2, longlong param_3)
{
  float fVar1;
  float fVar2;
  bool bVar3;
  char cVar4;
  char cVar5;
  int iVar6;
  int iVar7;
  int iVar8;
  int iVar9;
  uint uVar10;
  int iVar11;
  int iVar12;
  longlong *plVar13;
  longlong lVar14;
  undefined8 uVar15;
  longlong lVar16;
  longlong lVar17;
  longlong lVar18;
  int iVar19;
  float fVar20;
  float fVar21;
  float fVar22;
  float fVar23;
  float fVar24;
  undefined8 local_118;
  undefined8 *puStack_110;
  longlong local_108;
  longlong local_100;
  longlong local_f8;
  undefined8 local_f0;
  undefined8 *puStack_e8;
  longlong local_e0;
  
  if (DAT_183b93322 == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    FUN_180427b00(&DAT_1839a6198);
    FUN_180427b00(&DAT_18396df28);
    FUN_180427b00(&DAT_1839ada98);
    FUN_180427b00(&DAT_1839adb50);
    FUN_180427b00(&DAT_1839adc08);
    FUN_180427b00(&DAT_183968278);
    FUN_180427b00(&DAT_183942930);
    FUN_180427b00(&DAT_18394df48);
    DAT_183b93322 = '\x01';
  }
  if ((((param_2 == (longlong *)0x0) || (param_2[0x19] == 0)) ||
      (lVar16 = *(longlong *)(param_2[0x19] + 0x10), lVar16 == 0)) ||
     ((cVar4 = FUN_180717870(lVar16,0), param_3 == 0 || (*(longlong *)(param_3 + 0x10) == 0))))
  goto LAB_18075e9a3;  // → NullReferenceException abort

  cVar5 = FUN_1806889c0(*(longlong *)(param_3 + 0x10),0);
  if (cVar5 == '\0') {
    if (*(longlong *)(param_3 + 0x10) == 0) goto LAB_18075e9a3;
    plVar13 = (longlong *)FUN_180688600(*(longlong *)(param_3 + 0x10),0);
    if (plVar13 != param_2) {
      if (cVar4 != '\0') {
        return;
      }
      lVar16 = param_2[0xe];
      if (*(longlong *)(param_3 + 0x10) == 0) goto LAB_18075e9a3;
      lVar14 = FUN_180688600(*(longlong *)(param_3 + 0x10),0);
      if (lVar16 != lVar14) {
        if (*(longlong *)(param_3 + 0x10) == 0) goto LAB_18075e9a3;
        uVar15 = FUN_180688600(*(longlong *)(param_3 + 0x10),0);
        cVar5 = FUN_1806169a0(param_2,uVar15,0);
        if (cVar5 == '\0') {
          return;
        }
      }
      if (((*(longlong *)(param_3 + 0x10) == 0) || ...) goto LAB_18075e9a3;
      lVar16 = *(longlong *)(lVar16 + 0xe8);
      if (*(int *)(DAT_18394df48 + 0xe4) == 0) { il2cpp_runtime_class_init(); }
      cVar5 = FUN_1829a9340(lVar16,0,0);
      if (cVar5 == '\0') { iVar6 = 0; }
      else {
        if (lVar16 == 0) goto LAB_18075e9a3;
        iVar6 = FUN_1806d7700(lVar16,0);
      }
      if (*(int *)(DAT_18394df48 + 0xe4) == 0) { il2cpp_runtime_class_init(); }
      cVar5 = FUN_1829a9340(lVar16,0,0);
      if (cVar5 == '\0') { iVar12 = 0; }
      else {
        if (lVar16 == 0) goto LAB_18075e9a3;
        iVar12 = *(int *)(lVar16 + 100);
      }
      fVar21 = *(float *)(param_3 + 0x28);
      if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) { il2cpp_runtime_class_init(DAT_18394c3d0); }
      lVar16 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
      if (lVar16 == 0) goto LAB_18075e9a3;
      fVar21 = fVar21 - (float)iVar6 * *(float *)(lVar16 + 0xd8);
      *(float *)(param_3 + 0x28) = fVar21;
      lVar16 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
      if (lVar16 == 0) goto LAB_18075e9a3;
      *(float *)(param_3 + 0x28) = fVar21 - (float)iVar12 * *(float *)(lVar16 + 0xdc);
      fVar21 = *(float *)(param_3 + 0x30);
      fVar20 = (float)FUN_180760070(param_1,param_2,0);
      *(float *)(param_3 + 0x30) = fVar20 + fVar21;
    }
  }
  // [... cover iteration loop — see full reconstruction below ...]
  
LAB_18075e9a3:
  /* WARNING: Subroutine does not return */
  FUN_180427d90();
}
```

*(Full raw output is 988 lines; above is structurally representative. Complete listing available in decompiled_functions.txt.)*

### Annotated Reconstruction

```c
// CoverAgainstOpponents.Evaluate
// VA: 0x18075DAD0 | RVA: 0x75DAD0
//
// Evaluates how much cover a candidate tile provides against all known opponents.
// Writes a weighted cover quality score into ctx->accumulatedScore.
// Also writes the utility threshold for this tile into ctx->thresholdAccumulator.
//
// param_1 = CoverAgainstOpponents* this  (unused — stateless criterion)
// param_2 = Unit*                        (the AI-controlled unit being evaluated)
// param_3 = EvaluationContext*           (tile score record, accumulator)

void CoverAgainstOpponents_Evaluate(
    CoverAgainstOpponents* self,
    Unit*                  unit,
    EvaluationContext*     ctx)
{
    // [IL2CPP: type init — 9 classes including AIWeightsTemplate, CoverAgainstOpponents]

    // ── GUARD ──────────────────────────────────────────────────────────────
    // unit->opponentList (unit[0x19] = unit + 0xC8)
    OpponentList* opponentList = unit->opponentList;
    if (unit == null || opponentList == null) goto ABORT;
    void* opponentListContents = opponentList->field_0x10;
    if (opponentListContents == null) goto ABORT;
    bool opponentListNonEmpty = IsListNonEmpty(opponentListContents);  // FUN_180717870
    if (ctx == null || ctx->tileRef == null) goto ABORT;

    // ── PHASE 1 — OCCUPIED TILE PENALTIES ──────────────────────────────────
    // cVar4 = true if this tile IS the unit's current tile
    bool isCurrentTile = IsCurrentTile(ctx->tileRef);  // FUN_1806889c0

    if (!isCurrentTile) {
        Unit* tileOccupant = GetUnitOnTile(ctx->tileRef);  // FUN_180688600
        if (tileOccupant != unit) {
            // Tile is occupied by another unit

            if (opponentListNonEmpty) {
                // If the opponent list is non-empty, skip this tile
                // [UNCERTAIN: this branch exits evaluation for tiles occupied
                //  by allies when there are active opponents — may be "don't
                //  stack on allies" rule]
                return;
            }

            // Check if occupant is on a different team
            int myTeamId      = unit->teamId;  // unit[0xe] = unit + 0x70
            int occupantTeam  = GetUnitOnTile(ctx->tileRef)->teamId;

            if (myTeamId != occupantTeam) {
                // Occupant is an enemy — check if we can target them
                bool canTarget = CanTargetUnit(unit, tileOccupant);  // FUN_1806169a0
                if (!canTarget) return;  // Early-out: can't engage, skip tile
            }

            // Get the occupying unit's equipped weapon
            Weapon* weapon = GetUnitWeapon(tileOccupant)->weaponSlot;  // vtable + 0x398
            bool isRanged  = IsRangedWeapon(weapon);                   // FUN_1829a9340

            int weaponRange = isRanged ? GetWeaponRange(weapon) : 0;   // FUN_1806d7700
            int weaponAmmo  = isRanged ? weapon->field_0x64 : 0;       // +0x64 = ammo/magazine

            // Apply penalties to tile score for occupying enemy's threat
            AIWeightsTemplate* settings = AIWeightsTemplate.instance;

            float score = ctx->accumulatedScore;  // ctx + 0x28
            score -= (float)weaponRange * settings->rangeScorePenalty;  // settings + 0xd8
            ctx->accumulatedScore = score;

            score -= (float)weaponAmmo * settings->ammoScorePenalty;    // settings + 0xdc
            ctx->accumulatedScore = score;

            // Add threshold contribution for this tile
            float threshold    = ctx->thresholdAccumulator;  // ctx + 0x30
            float tileThreshold = GetUtilityThreshold(self, unit);  // FUN_180760070
            ctx->thresholdAccumulator = tileThreshold + threshold;
        }
    }

    // ── PHASE 2 — COVER QUALITY ITERATION ──────────────────────────────────
    // Enumerate nearby opponents and compute cover quality against each one.
    // Uses a filtered iterator over the opponent list (DAT_183968278 = filter type).

    float fBestCover = 0.0f;
    float fSumCover  = 0.0f;

    // Iterator: FUN_180cbab80 = GetEnumerator, FUN_1814f4770 = MoveNext
    for each (OpponentEntry* entry in unit->opponentList->filtered(opponentFilter)) {

        if (!IsEnemy(entry)) continue;  // FUN_180722ed0 — skip non-hostile entries

        // Get the enemy unit object from the entry
        Unit* enemy = *(entry + 0x10);  // enemy unit ptr within entry

        // Get this enemy's tile position
        Tile* enemyTile = GetEnemyTilePosition(enemy);  // vtable *enemy + 0x388

        float coverMultiplier = 1.0f;  // default weight

        // Classify cover type based on enemy's equipment and status
        if (enemy->isRangedUnit) {  // enemy + 0x15c
            uint equipFlags = GetEquipmentFlags(enemy);  // vtable + 0x3d8 → field_0xec

            if ((equipFlags & 1) == 0) {
                // Not fully armoured — check stance
                int stanceA = GetStanceA(enemy);  // vtable + 0x478
                int stanceB = GetStanceB(enemy);  // vtable + 0x468

                if (stanceA == 2) {
                    coverMultiplier = settings->coverMult_Full;   // settings + 0x8c
                }
                else if (stanceB == 1) {
                    coverMultiplier = settings->coverMult_Low;    // settings + 0x98
                }
                else if (stanceA == 1 || stanceB == 2) {
                    coverMultiplier = settings->coverMult_Partial;  // settings + 0x90
                }
                else if (enemy->isRangedUnit && stanceB != 1 && stanceA != 2) {
                    coverMultiplier = settings->coverMult_Quarter;  // settings + 0x9c
                }
                // else coverMultiplier remains 1.0 (no meaningful cover)
            }
            else {
                // Armoured — full cover multiplier applies
                coverMultiplier = settings->coverMult_Full;        // settings + 0x8c
            }
        }
        // [LAB_18075e1fe — coverMultiplier resolved]

        // Compute per-tile spatial relationship for this enemy
        int tileWidth  = *(enemy->tileBounds + 0x18);  // range extent in X
        int tileHeight = *(entry->field_0x28);          // range extent in Y
        Bounds* entryBounds = entry->field_0x18;

        // Iterate candidate tiles within the enemy's attack envelope
        for (int tx = entryBounds->minX; tx <= entryBounds->minX; tx++) {  // [UNCERTAIN: loop bounds look degenerate in Ghidra — likely broader loop]
            for (int ty = entryBounds->minY; ty <= entryBounds->minY; ty++) {

                Tile* candidateTile = GetAdjacentTile(tileGrid, tx);  // FUN_1810c1fc0

                if (candidateTile == null) continue;
                if (!IsCurrentTile(candidateTile) && candidateTile != enemyTile) continue;

                // Compute distance-based proximity score
                int dist = GetTileDistance(ctx->tileRef, candidateTile);  // FUN_1805ca7a0

                float proximity;
                if (isCurrentTile && /* within ±3 of current bounds */) {
                    // Deployment-phase path: use zone range containment
                    // [covers FUN_18073bcf0 range-check and zone boundary math]
                    int span = max(
                        Abs(entryBounds->maxX - entryBounds->minX),
                        Abs(entryBounds->maxY - entryBounds->minY));
                    int relDist = Abs(entryBounds->centerY - dist);
                    proximity = 1.0f - (float)relDist / (float)span;
                    proximity = max(proximity, 0.25f);
                    proximity = proximity * coverMultiplier
                                         * ((float)tileWidth / (float)tileHeight * 0.5f + 0.5f);
                }
                else {
                    // Standard path: linear proximity falloff over 30 tiles
                    proximity = 1.0f - (float)dist / 30.0f;
                    proximity = max(proximity, 0.1f);
                }

                // Get directionality for COVER_PENALTIES lookup
                int dirIdx = GetTileDirectionIndex(ctx->tileRef, candidateTile);  // FUN_1805ca720
                int nextDir = dirIdx + 1;
                if (nextDir > 7) nextDir = 0;
                int prevDir = dirIdx - 1;
                if (prevDir < 0) prevDir = 7;

                // Read cover penalty for this direction from COVER_PENALTIES static array
                // [bVar3 = true when tile is in the "front arc" relative to enemy]
                float penalty, halfPenalty, adjPenalty;
                if (bVar3) {
                    // Front-arc path: use first element of COVER_PENALTIES for all dirs
                    penalty     = COVER_PENALTIES[0];
                    halfPenalty = rawScore * 0.5f * COVER_PENALTIES[0];
                    adjPenalty  = COVER_PENALTIES[0];
                }
                else {
                    // Directional path: look up by direction index
                    penalty     = COVER_PENALTIES[GetDirectionIndex(tileGrid, dirIdx)];
                    halfPenalty = rawScore * 0.5f * COVER_PENALTIES[GetDirectionIndex(tileGrid, nextDir)];
                    adjPenalty  = COVER_PENALTIES[GetDirectionIndex(tileGrid, prevDir)];
                }

                // Accumulate: weighted sum of direction arc coverage
                float tileCoverScore = rawScore * 0.5f * adjPenalty
                                     + halfPenalty
                                     + rawScore * penalty
                                     + 0.0f;

                fBestCover = max(fBestCover, tileCoverScore);
                fSumCover += tileCoverScore;
            }
        }
    }

    // ── PHASE 3 — FINAL SCORE WRITE ────────────────────────────────────────
    // FUN_1804f7ee0 called on local_f0 — resets local iterator state (no logical effect)

    AIWeightsTemplate* settings = AIWeightsTemplate.instance;
    // Null-guard settings

    // Best-cover bonus: weighted sum + best-tile bonus
    float total = fSumCover + fBestCover * settings->bestCoverBonusWeight;  // settings + 0xa4

    // Subtract penalty for each of 8 occupied adjacent directions
    if (!isCurrentTile) {
        for (int dir = 0; dir < 8; dir++) {
            // FUN_180687660 = GetDirectionIndex for context tile
            int occupied = GetDirectionIndex(ctx->tileRef, dir);  // checks occupancy
            if (occupied != 0) {
                total -= settings->occupiedDirectionPenalty;  // settings + 0xd4
            }
        }
    }

    // Choke-point and deployment-lock adjustments
    if (total != 0.0f) {
        int depth = GetMovementDepth(unit);  // FUN_180614d30 — returns -2 if locked
        if (depth != -2) {
            bool isChoke = IsChokePoint(ctx->tileRef);  // FUN_1805ca990
            if (!isChoke) {
                total += 10.0f;  // bonus for non-choke-point tiles
            }
        }
    }

    // Status effect debuff penalty
    if (ctx->isObjectiveTile == false) {  // ctx + 0x60
        StatusEffects* effects = GetStatusEffects(unit);  // vtable + 0x398
        if (effects != null && effects->field_0x310 != null) {
            if (effects->field_0x310->field_0x29 != 0) {
                total *= 0.9f;  // 10% penalty for debuffed unit on non-objective tile
            }
        }
    }

    // Read current accumulated score and apply weighted addition
    float currentScore = ctx->accumulatedScore;  // ctx + 0x28 — fVar21 re-read
    ctx->accumulatedScore = total * settings->coverScoreWeight  // settings + 0x70
                           + currentScore;
    return;

ABORT:
    NullReferenceException();  // FUN_180427d90 — does not return
}
```

---

## F5 — `Criterion.Score`

### Raw Ghidra Output

*(Full 291-line raw output reproduced; see decompiled_functions.txt lines 16–291 for complete listing. Key structural sections annotated below.)*

```c
undefined8
FUN_180760140(longlong *param_1, longlong *param_2, undefined8 param_3,
              longlong param_4, undefined4 param_5)
{
  // [... local variable declarations ...]
  
  if (DAT_183b9331a == '\0') {
    // [IL2CPP init guard — 7 classes]
    DAT_183b9331a = '\x01';
  }
  if (param_2 != (longlong *)0x0) {
    uVar12 = 0;
    if (param_2[3] == 0) {
      uVar6 = thunk_FUN_1804608d0(DAT_183981fc8);
      FUN_18062a050(uVar6,0);
      (**(code **)(*param_2 + 0x2f8))(param_2,...);     // sync score fetch via vtable
    }
    else {
      uVar6 = FUN_1806f2460(param_2[3],...);            // async threaded score fetch
    }
    if (param_1 != (longlong *)0x0) {
      lVar7 = (**(code **)(*param_1 + 1000))(param_1,...);  // GetEnemyList(unit)
      uVar8 = uVar12;
      if (param_2[3] != 0) {
        uVar8 = FUN_1806d5040(param_2,0);               // GetThreadScoreIndex
      }
      if (lVar7 != 0) {
        uVar9 = FUN_1806f2230(lVar7,uVar8,...);          // GetScoredTileData
        pfVar10 = FUN_1806e0ac0(...);                    // GetTileScoreComponents
        fVar22 = *pfVar10 * 0.01;                        // rawScore normalised
        lVar7  = FUN_1806df4e0(...);                     // GetMoveRangeData
        if ((param_1[4] != 0) && (lVar7 != 0)) {
          // Phase 3: movement gating
          fVar13 = fVar22 * *(float *)(lVar7 + 0x1c);   // rawScore * moveCost
          fVar19 = (float)(*(int *)(param_1[4] + 0x18) + -1);  // maxMoves - 1
          if (fVar13 <= fVar19) { fVar19 = fVar13; }
          fVar19 = floorf(fVar19);
          fVar19 = (float)FUN_1806e0300(...,(int)fVar19,...) * 0.01;  // adjScore
          
          // Phase 4+: main scoring kernel
          // [... see annotated reconstruction ...]
          
          // Phase 8: final weighted combination
          auVar18._0_4_ = (float)auVar17._0_8_ *
              (fVar19 * fVar24 + fVar22 * fVar13 + fVar14 * fVar20 + fVar21 * fVar23);
          return auVar18._0_8_;
        }
      }
    }
  }
LAB_180760b0d:
  FUN_180427d90();  // NullReferenceException — does not return
}
```

### Annotated Reconstruction

```c
// Criterion.Score
// VA: 0x180760140 | RVA: 0x760140
//
// Master scoring function. Combines all criterion evaluation results into a
// single float utility score for a candidate tile.
// Called once per tile after all Evaluate() passes have completed.
//
// param_1 (unit)     = Unit*              — the AI-controlled unit
// param_2 (tile)     = TileCandidate*     — the candidate tile record
// param_3 (ctx)      = EvaluationContext* — evaluation context (opaque here)
// param_4 (tileData) = TileData*          — additional game state / tile info
// param_5            = int flags

float Criterion_Score(
    Unit*              unit,
    TileCandidate*     tile,
    EvaluationContext* ctx,
    TileData*          tileData,
    int                flags)
{
    // [IL2CPP: type init — AIWeightsTemplate, 6 other config singletons]

    if (tile == null) goto ABORT;

    // ── PHASE 1 — TILE SCORE RETRIEVAL ─────────────────────────────────────
    TileScoreHandle tileScore;
    if (tile->field_0x18 == 0) {  // tile[3] = tile + 0x18 (no pre-scored data)
        // Synchronous path: invoke vtable scorer directly
        ScoringContext* scoreCtx = AllocScoringContext(scoreCtxClass);  // thunk_FUN_1804608d0
        InitScoringContext(scoreCtx, 0);                                // FUN_18062a050
        tileScore = tile->vtable->ScoreSync(tile, scoreCtx, ctx, tileData, scoreCtx, unit,
                                            tile->vtable->field_0x300);
                                    // (*(*tile + 0x2f8))(tile, ...) — vtable slot 0x2f8
    }
    else {
        // Async/threaded path: retrieve pre-computed score
        tileScore = GetThreadedTileScore(tile->field_0x18, tile, ctx, tileData, unit, 0);
                                    // FUN_1806f2460
    }

    if (unit == null) goto ABORT;

    // Get enemy list via vtable (unit + 1000 = vtable offset 0x3E8)
    EnemyList* enemies = unit->vtable->GetEnemyList(unit, unit->vtable->field_0x3F0);
    if (enemies == null) goto ABORT;

    // Thread-local score index (0 if single-threaded)
    uint threadIdx = (tile->field_0x18 != 0) ? GetThreadScoreIndex(tile, 0) : 0;
                                    // FUN_1806d5040

    // Retrieve the TileScore data object
    TileScore* scored = GetScoredTileData(enemies, threadIdx, ctx, tileData, tile, 0);
                                    // FUN_1806f2230

    // ── PHASE 2 — RAW SCORE EXTRACTION ─────────────────────────────────────
    // GetTileScoreComponents returns float* to the raw score component array
    float* components = GetTileScoreComponents(stackBuf, tile, ctx, tileData, tileScore,
                                               scored, 1, unit, stackArg, 0);
                                    // FUN_1806e0ac0
    float rawScore = components[0] * 0.01f;
    // rawScore is normalised from centiscale integer space to [0.0, 1.0]

    // ── PHASE 3 — MOVEMENT GATING ──────────────────────────────────────────
    MovePool*     movePool  = unit->movePool;     // unit[4] = unit + 0x20
    MoveRangeData* moveData = GetMoveRangeData(tile, ctx, tileData, tileData, unit,
                                               tileScore, scored, flags, 0, 0);
                                    // FUN_1806df4e0
    if (movePool == null || moveData == null) goto ABORT;

    float rangeCost = rawScore * moveData->moveCostToTile;    // moveData + 0x1c
    float maxCost   = (float)(movePool->maxMovePoints - 1);   // movePool + 0x18, minus 1
    if (rangeCost > maxCost) rangeCost = maxCost;
    rangeCost = floorf(rangeCost);

    // Re-score after reachability adjustment
    float adjScore = (float)GetReachabilityAdjustedScore(tile, ctx, tileData, unit,
                                                         tileScore, scored,
                                                         (int)rangeCost, flags, 0, 0)
                     * 0.01f;
                                    // FUN_1806e0300

    // ── PHASE 4 — COMPONENT A: ATTACK WEIGHT ───────────────────────────────
    AIWeightsTemplate* settings = AIWeightsTemplate.instance;
    float fAtk = settings->baseAttackWeight;  // settings + 0xe4 — fVar13

    if (rawScore * moveData->minRange > 0.0f) {
        // ── Sub-component: ammo pressure (fVar24) ──────────────────────────
        // How much remaining ammo the unit has relative to enemy count

        EnemyListData* enemyListData = unit->vtable->GetWeaponList(unit, unit->vtable->field_0x3e0);
                                    // vtable + 0x3d8
        if (enemyListData == null) goto ABORT;

        int  enemyCount   = GetEnemyCountInRange(enemyListData, 3, 0);  // FUN_1806283c0, radius=3
        float reloadChance = GetReloadChance(unit, 0);                  // FUN_180614b30

        float ammoLeft = (float)unit->currentAmmo  // unit + 0x5c
                         - rawScore * moveData->minRange;               // moveData + 0x14
        if (ammoLeft < 0.0f) ammoLeft = 0.0f;

        float teamSize = (float)(int)unit->squadCount;  // unit[0xc] = unit + 0x60
        if (teamSize < 1.0f) teamSize = 1.0f;

        float enemyCap = (float)enemyCount;
        if (enemyCap > 200.0f) enemyCap = 200.0f;

        float fAmmo = (reloadChance * enemyCap
                       - (ammoLeft / teamSize) * enemyCap)
                      * settings->ammoPressureWeight  // settings + 0xe8
                      * enemyCap
                      * 0.0001f;
        // fAmmo = Component B (ammo pressure). Stored in fVar24.
    }

    // ── Range efficiency multiplier for attack component ───────────────────
    float rangeRatio = (rawScore * moveData->attackRange)  // moveData + 0x10
                       / (float)unit->moveRange;           // unit + 0x54
    if (rangeRatio > 2.0f) rangeRatio = 2.0f;
    fAtk = settings->baseAttackWeight * rangeRatio;  // fVar13

    // ── Full-range bonus ────────────────────────────────────────────────────
    if (rawScore * moveData->moveCostToTile >= (float)movePool->maxMovePoints) {
        fAtk *= 2.0f;
        float health = GetHealthRatio(unit);  // FUN_1806155c0
        if (health > 0.95f) {
            fAtk *= 4.0f;  // Near-full-health + max-range = 8× base attack bonus
        }
    }
    else if (moveData->canAttackFromTile && rawScore > 0.0f) {  // moveData + 0x25
        fAtk *= 1.1f;  // Minor bonus for any attack-capable position
    }

    // ── Overwatch suppression multiplier loop ───────────────────────────────
    // Reads from DAT_18396a5e8 static field — two float[] tables:
    //   table_D8 = response thresholds    (at +0xd8 in static fields)
    //   table_E0 = suppression multipliers (at +0xe0 in static fields)
    for (uint i = 0; i < overwatchTable.length; i++) {
        float threshold = overwatchResponseTable[i];          // DAT_18396a5e8 + 0xb8 + 0xd8 [i]
        float rangeGap  = ((float)unit->moveRange            // unit + 0x54
                           - rawScore * moveData->attackRange)
                          / (float)unit->field_0xB;          // unit[0xb]

        if (rangeGap < threshold) {
            // Within suppression zone — apply multiplier
            float mult = overwatchMultTable[i] * 0.3f * 0.01f + 1.0f;
                                    // DAT_18396a5e8 + 0xb8 + 0xe0 [i]
            fAtk *= mult;
        }
    }
    // [Loop exit: i >= table length → break; out-of-bounds → IndexOutOfRangeException]

    // ── PHASE 5 — DEPLOYMENT / RANGED ATTACK BONUS (fVar20, Component C) ───
    float fDeploy = 0.0f;
    if (adjScore > 0.0f) {
        float combined = adjScore * rawScore + adjScore;
        if (combined > 2.0f) combined = 2.0f;
        fDeploy = combined * settings->deployPositionWeight;  // settings + 0xec

        if (TileHasEnemyUnit(tileData, 0) == 0) {  // FUN_180687590
            int depth = GetMovementDepth(unit, 0, 0);  // FUN_180614d30
            fDeploy *= ((float)depth * 0.25f + 1.5f);
        }

        if (adjScore * rawScore + adjScore >= 0.67f) {
            fDeploy *= 3.0f;  // Strong position: ≥0.67 combined → 3× deploy bonus
        }
    }

    // ── PHASE 6 — SNIPER WEAPON BONUS (fVar23, Component D) ────────────────
    // Only executes if the tile candidate holds a unit with a sniper-class weapon.
    // Type-check via IL2CPP vtable: DAT_18397c1e0 = SniperWeapon class descriptor
    float fSniper = 0.0f;
    TileWeaponHolder* weaponHolder = tile->field_0x10;  // tile[2] = tile + 0x10 (?)
    if (weaponHolder != null && weaponHolder->field_0x2c8 != null) {
        // IL2CPP type check: is the weapon a SniperWeapon?
        if (IsInstanceOf(weaponHolder->field_0x2c8, SniperWeapon_typeDesc)) {
            float sniperWeight = settings->sniperAttackWeight;  // settings + 0xf0

            // Count attack steps and viable attack positions
            int rangeSteps  = GetRangeStepCount(tile, weapon->field_0xd0, 0); // FUN_1806defc0
            int attackCount = GetAttackCountFromTile(tile, tileScore, 0);      // FUN_1806de960

            fSniper = (float)attackCount
                      * (float)(rangeSteps * *(int*)(weaponHolder + 0x154))
                      * sniperWeight
                      * rawScore;

            if (TileHasEnemyUnit(tileData, 0) == 0) {
                int depth = GetMovementDepth(unit, 0, 0);
                fSniper *= ((float)depth * 0.25f + 1.5f);
            }

            float health = GetHealthRatio(unit);  // FUN_1806155c0
            float healthFactor = (health < 0.25f) ? 0.25f : health;
            fSniper *= healthFactor;

            fSniper = fSniper * max(GetHealthRatio(unit), 0.25f);
        }
    }

    // ── PHASE 7 — STATUS EFFECT PENALTY ────────────────────────────────────
    // Applied to attack component when unit has an active debuff
    StatusEffects* effects = unit->vtable->GetStatusEffects(unit, unit->vtable->field_0x3a0);
                                    // vtable + 0x398
    if (effects != null && effects->field_0x108 != null) {
        BuffData* buff = effects->field_0x108;
        if (buff->count > 0 && rawScore * moveData->attackRange > 0.0f) {
            // Has active buffs/debuffs — apply overwatch curve per buff entry
            // [Loop reads DAT_18396a5e8 tables again — same suppression curve]
            // fAtk modified by buff-scaled suppression multipliers
        }
    }

    // ── PHASE 8 — FINAL WEIGHTED COMBINATION ───────────────────────────────
    // Read component weights from AIWeightsTemplate
    float W_attack = settings->W_attack;  // settings + 0x7c  (note: reused label for weight)
    float W_ammo   = settings->W_ammo;    // settings + 0x80
    float W_deploy = settings->W_deploy;  // settings + 0x84
    float W_sniper = settings->W_sniper;  // settings + 0x88

    // Movement effectiveness curve
    // GetMovementEffectivenessIndex returns an index into a float[] lookup
    uint movEffIdx  = GetMovementEffectivenessIndex(tile, unit, 0);  // FUN_1806e2400
    float[] movEffTable = DAT_18397ae78.staticFields->movementEffTable;  // +0xb8 → [0]
    float movEffRaw = movEffTable[movEffIdx];
    float movEff    = MathCurve(movEffRaw + 1.0f);
    // MathCurve (FUN_1804bad80): [UNCERTAIN — likely expf or custom monotone curve]
    // Applied to (tableValue + 1.0) which is always > 0, so always positive.

    // Final formula:
    return movEff * (W_attack * fAtk
                   + W_ammo   * fAmmo
                   + W_deploy * fDeploy
                   + W_sniper * fSniper);

ABORT:
    NullReferenceException();  // FUN_180427d90 — does not return
}

// ─────────────────────────────────────────────────────────────────────────────
// Design note:
//   The four components are fully independent in their computation paths and
//   can each be zero without affecting the others. The movement effectiveness
//   curve acts as a global scalar — a tile the unit cannot efficiently reach
//   has its entire score discounted regardless of how well it covers or attacks.
// ─────────────────────────────────────────────────────────────────────────────
```
