# Menace Armor Damage System — Annotated Function Reconstructions

**Source:** Ghidra decompilation of Menace (Windows x64, Unity IL2CPP)  
**Image base:** `0x180000000`  
**Format:** Each function shows the raw Ghidra output followed by a fully annotated C-style reconstruction with all offsets resolved.

---

## Quick-Reference Field Tables

### EntityProperties (param_1 in most functions below)

| Offset | Field | Type |
|---|---|---|
| 0x18 | `HitpointsPerElementMult` | float |
| 0x28 | `ArmorMult` | float |
| 0x2C | `ArmorDurabilityPerElement` | float |
| 0x34 | `ActionPoints` | int |
| 0x38 | `ActionPointsMult` | float |
| 0x5C | `BackwardsMovementMult` | float (NewEmpty only — confirmed not durability at this offset) |
| 0x68 | `Accuracy` | float |
| 0x6C | `AccuracyMult` | float |
| 0x74 | `AccuracyDropoffMult` | float |
| 0x84 | `DefenseMult` | float |
| 0x88 | `CoverEffectivenessMult` | float |
| 0x8C | `DamageSustainedMult` | float |
| 0xA0 | `Discipline` | float |
| 0xA4 | `DisciplineMult` | float |
| 0xB0 | `MoraleMult` | float |
| 0xB4 | `MoraleRecoveryMult` | float |
| 0xB8 | `DamageToMoraleMult` | float |
| 0xBC | `MoraleImpactMult` | float |
| 0xC4 | `Vision` | int |
| 0xC8 | `VisionMult` | float |
| 0xCC | `Detection` | int |
| 0xD0 | `DetectionMult` | float |
| 0xD4 | `Concealment` | int |
| 0xD8 | `ConcealmentMult` | float |
| 0xDC | `SuppressionImpactMult` | float |
| 0xE0 | `SuppressionDealt` | float |
| 0xE4 | `SuppressionDealtMult` | float |
| 0xF0 | `PromotionCostMult` | float |
| 0xF4 | `DeploymentZoneMult` | float |
| 0xFC | `DeployCostMult` | float |
| 0x100 | `ArmorPenetration` | float |
| 0x104 | `ArmorPenetrationMult` | float |
| 0x108 | `ArmorPenetrationDropoff` | float |
| 0x10C | `ArmorPenetrationDropoffMult` | float |
| 0x114 | `IgnoreCoverMult` | float |
| 0x118 | `Damage` | float |
| 0x11C | `DamageMult` | float |
| 0x120 | `DamageDropoff` | float |
| 0x124 | `DamageDropoffMult` | float |
| 0x12C | `DamageToArmorDurability` | float |
| 0x130 | `DamageToArmorDurabilityMult` | float |
| 0x134 | `DamageToArmorDurabilityDropoff` | float |
| 0x138 | `DamageToArmorDurabilityDropoffMult` | float |
| 0x140 | `TotalDamageMult` | float |
| 0x158 | `GetDismemberedChanceMult` | float |
| 0x184 | `AIPriorityMult` | float |

### Entity (param_1 in OnDamageReceived)

| Offset | Field | Type |
|---|---|---|
| 0x54 | `m_Hitpoints` | int |
| 0x58 | `m_HitpointsMax` | int |
| 0x5C | `m_ArmorDurability` | int |
| 0x60 | `m_ArmorDurabilityMax` | int |

### DamageInfo (param_4 in OnDamageReceived)

| Offset | Field | Type |
|---|---|---|
| 0x2C | `Damage` | int |
| 0x30 | `ArmorDirection` | int |
| 0x34 | `ArmorPenetration` | int |
| 0x38 | `ArmorDamage` | int |
| 0x3C | `ElementsHit` | int |
| 0x4A | `IsAbleToPenetrate` | bool |
| 0x4B | `IsDamageInflicted` | bool |
| 0x4C | `IsElementDestroyed` | bool |
| 0x4D | `IsTargetDestroyed` | bool |

---

## 1. FUN_1805316F0 — Multiplier Floor Clamp — 0x1805316F0

### Raw Ghidra output
```c
float FUN_1805316f0(float param_1)
{
  float fVar1;
  
  fVar1 = 0.0;
  if (0.0 <= param_1) {
    fVar1 = param_1;
  }
  return fVar1;
}
```

### Annotated reconstruction
```c
// Helper: clamp a multiplier value to a minimum of 0.0
// Prevents negative multipliers from inverting effects
float ClampMultiplierToZero(float value)
{
    return (value >= 0.0f) ? value : 0.0f;
}
```

---

## 2. FUN_1805316D0 — Additive Multiplier Accumulator — 0x1805316D0

### Raw Ghidra output
```c
void FUN_1805316d0(float *param_1, float param_2)
{
  *param_1 = (param_2 - 1.0) + *param_1;
  return;
}
```

### Annotated reconstruction
```c
// Accumulate a multiplier modifier additively.
// Convention: multipliers are stored as offsets from 1.0.
// A buff of 1.2 (+20%) adds 0.2 to the field.
// Two buffs of 1.2 each produce 1.4 total, not 1.44.
// The field is initialized to 1.0 by NewEmpty().
void AccumulateMultiplier(float* field, float newMultiplierValue)
{
    *field += (newMultiplierValue - 1.0f);
}
```

### Design notes

This is the key convention for the multiplier system. All `*Mult` fields in `EntityProperties` use this accumulation model when modified by skills or ammo. The initial value of 1.0 (set by `NewEmpty`) plus accumulated deltas gives the effective multiplier. A field that receives no modifications remains at 1.0 (no change). A field that receives a single 1.5 modifier becomes 1.5. A field that receives two 1.5 modifiers becomes 2.0, not 2.25.

---

## 3. EntityProperties.GetDamageToArmorDurability — 0x1806285B0

### Raw Ghidra output
```c
float FUN_1806285b0(longlong param_1)
{
  float fVar1;
  float fVar2;
  
  fVar1 = *(float *)(param_1 + 300);
  fVar2 = (float)FUN_1805316f0(*(undefined4 *)(param_1 + 0x130),0);
  return fVar2 * fVar1;
}
```

### Annotated reconstruction
```c
float EntityProperties_GetDamageToArmorDurability(EntityProperties* self)
{
    float baseValue   = self->DamageToArmorDurability;        // +0x12C (300 decimal)
    float clampedMult = ClampMultiplierToZero(self->DamageToArmorDurabilityMult); // +0x130

    return clampedMult * baseValue;
}
```

### Design notes

The multiplier is clamped to zero before application, so `DamageToArmorDurability` can be reduced to zero but cannot become negative (which would otherwise heal armor durability). The flat `DamageToArmorDurability` field is the accumulated delta from all skills and ammo effects contributing durability damage. The mult is the accumulated product-of-deltas for scaling.

---

## 4. EntityProperties.GetDamageToArmorDurabilityDropoff — 0x180628580

### Raw Ghidra output
```c
float FUN_180628580(longlong param_1)
{
  float fVar1;
  float fVar2;
  
  fVar1 = *(float *)(param_1 + 0x134);
  fVar2 = (float)FUN_1805316f0(*(undefined4 *)(param_1 + 0x138),0);
  return fVar2 * fVar1;
}
```

### Annotated reconstruction
```c
float EntityProperties_GetDamageToArmorDurabilityDropoff(EntityProperties* self)
{
    float baseDropoff   = self->DamageToArmorDurabilityDropoff;        // +0x134
    float clampedMult   = ClampMultiplierToZero(self->DamageToArmorDurabilityDropoffMult); // +0x138

    return clampedMult * baseDropoff;
}
```

### Design notes

Structurally identical to `GetDamageToArmorDurability`. The dropoff value reduces armor durability damage over range, parallel to how `DamageDropoff` reduces hitpoint damage. Both are clamped to zero.

---

## 5. EntityProperties.UpdateProperty — 0x180629A50

### Raw Ghidra output
```c
void FUN_180629a50(longlong param_1, undefined4 param_2, int param_3)
{
  char cVar1;
  // [IL2CPP init guards omitted for brevity — see full raw output in session log]
  
  cVar1 = FUN_180637d60(param_2, 0);  // IsMultProperty check
  local_res10[0] = param_2;
  if (cVar1 == '\0') {
    switch(param_2) {
    case 0:   *(int *)(param_1 + 0xc4) = *(int *)(param_1 + 0xc4) + param_3; return;  // Vision
    case 1:   *(float *)(param_1 + 0xa0) = (float)param_3 + *(float *)(param_1 + 0xa0); return;  // Discipline
    case 2:   *(int *)(param_1 + 0xd4) = *(int *)(param_1 + 0xd4) + param_3; return;  // Concealment
    case 3:   *(float *)(param_1 + 0x68) = (float)param_3 + *(float *)(param_1 + 0x68); return;  // Accuracy
    case 4:   // Armor — applies to all three directions
      *(int *)(param_1 + 0x1c) = *(int *)(param_1 + 0x1c) + param_3;  // Armor (front)
      *(int *)(param_1 + 0x20) = *(int *)(param_1 + 0x20) + param_3;  // ArmorSide
      *(int *)(param_1 + 0x24) = *(int *)(param_1 + 0x24) + param_3;  // ArmorBack
      return;
    case 5:   *(int *)(param_1 + 0x14) += param_3; return;  // HitpointsPerElement
    case 6:   *(int *)(param_1 + 0x34) += param_3; return;  // ActionPoints
    case 7:   *(int *)(param_1 + 0xcc) += param_3; return;  // Detection
    case 8:   *(int *)(param_1 + 0x10) += param_3; return;  // MaxElements
    // cases 9-28 are mult properties — handled by UpdateMultProperty
    case 0x1d: *(float *)(param_1 + 0x118) += (float)param_3; return;  // Damage (29)
    case 0x1e: *(float *)(param_1 + 0xe0) += (float)param_3; return;   // SuppressionDealt (30)
    case 0x1f: *(float *)(param_1 + 0x70) += (float)param_3; return;   // AccuracyDropoff (31)
    case 0x20: *(float *)(param_1 + 0x100) += (float)param_3; return;  // ArmorPenetration (32)
    case 0x21: *(float *)(param_1 + 0x120) += (float)param_3; return;  // DamageDropoff (33)
    case 0x22: *(int *)(param_1 + 0x16c) += param_3; return;           // ElementsHit (34)
    case 0x25: *(int *)(param_1 + 0x3c) += param_3; return;            // AdditionalMovementCost (37)
    case 0x26: *(float *)(param_1 + 0x108) += (float)param_3; return;  // ArmorPenetrationDropoff (38)
    case 0x27: *(int *)(param_1 + 0x164) += param_3; return;           // DismemberChance (39)
    case 0x28: *(int *)(param_1 + 0x154) += param_3; return;           // GetDismemberedChanceBonus (40)
    case 0x2a: *(float *)(param_1 + 0xac) += (float)param_3; return;   // MoraleBonus (42)
    case 0x2d: *(int *)(param_1 + 0x40) += param_3; return;            // AdditionalTurningCost (45)
    case 0x30: *(int *)(param_1 + 0x174) += param_3; return;           // ReduceElementsHit (48)
    case 0x32: *(int *)(param_1 + 0x50) += param_3; return;            // APEnterCost (50)
    case 0x33: *(int *)(param_1 + 0x54) += param_3; return;            // APLeaveCost (51)
    case 0x35: *(int *)(param_1 + 0x94) += param_3; return;            // ProvidedCoverBonus (53)
    case 0x36: *(int *)(param_1 + 0x178) += param_3; return;           // DefectThresholdOffset (54)
    case 0x38: *(int *)(param_1 + 0x98) += param_3; return;            // CoverTypeOffset (56)
    case 0x3a: *(float *)(param_1 + 300) += (float)param_3; return;    // DamageToArmorDurability (58) — 300 = 0x12C
    case 0x3b: *(float *)(param_1 + 0x134) += (float)param_3; return;  // DamageToArmorDurabilityDropoff (59)
    case 0x3d: *(int *)(param_1 + 0x15c) += param_3; return;           // GetDismemberedMinParts (61)
    case 0x3e: *(int *)(param_1 + 0x160) += param_3; return;           // GetDismemberedMaxParts (62)
    case 0x3f: *(int *)(param_1 + 0xc0) += param_3; return;            // MoraleStateOffset (63)
    case 0x41: *(int *)(param_1 + 0x9c) += param_3; return;            // CoverGainedByVehicleOffset (65)
    case 0x42: *(int *)(param_1 + 0xf8) += param_3; return;            // DeploymentZoneMinExtend (66)
    case 0x44: *(int *)(param_1 + 0x78) += param_3; return;            // HitchanceMin (68)
    case 0x45: *(int *)(param_1 + 0x7c) += param_3; return;            // CriticalChance (69)
    case 0x46: *(float *)(param_1 + 0x2c) += (float)param_3; return;   // ArmorDurabilityPerElement (70)
    default:   // out-of-range enum value → runtime exception
      // [IL2CPP exception path omitted]
    }
  }
  // IsMultProperty returned true — delegate to UpdateMultProperty path
  // [runtime exception for mult properties passed to UpdateProperty — omitted]
}
```

### Annotated reconstruction (clean)

```c
void EntityProperties_UpdateProperty(EntityProperties* self,
                                      EntityPropertyType propertyType,
                                      int amount)
{
    // IL2CPP lazy init — omitted
    
    bool isMult = IsMultProperty(propertyType);
    if (!isMult) {
        switch (propertyType) {
            case Vision:                        self->Vision += amount; break;
            case Discipline:                    self->Discipline += (float)amount; break;
            case Concealment:                   self->Concealment += amount; break;
            case Accuracy:                      self->Accuracy += (float)amount; break;
            case Armor:                         // All three armor directions updated together
                                                self->Armor += amount;
                                                self->ArmorSide += amount;
                                                self->ArmorBack += amount;
                                                break;
            case HitpointsPerElement:           self->HitpointsPerElement += amount; break;
            case ActionPoints:                  self->ActionPoints += amount; break;
            case Detection:                     self->Detection += amount; break;
            case MaxElements:                   self->MaxElements += amount; break;
            case Damage:                        self->Damage += (float)amount; break;
            case SuppressionDealt:              self->SuppressionDealt += (float)amount; break;
            case AccuracyDropoff:               self->AccuracyDropoff += (float)amount; break;
            case ArmorPenetration:              self->ArmorPenetration += (float)amount; break;
            case DamageDropoff:                 self->DamageDropoff += (float)amount; break;
            case ElementsHit:                   self->ElementsHit += amount; break;
            case AdditionalMovementCost:        self->AdditionalMovementCost += amount; break;
            case ArmorPenetrationDropoff:       self->ArmorPenetrationDropoff += (float)amount; break;
            case DismemberChance:               self->DismemberChance += amount; break;
            case GetDismemberedChanceBonus:     self->GetDismemberedChanceBonus += amount; break;
            case MoraleBonus:                   self->MoraleBonus += (float)amount; break;
            case AdditionalTurningCost:         self->AdditionalTurningCost += amount; break;
            case ReduceElementsHit:             self->ReduceElementsHit += amount; break;
            case APEnterCost:                   self->APEnterCost += amount; break;
            case APLeaveCost:                   self->APLeaveCost += amount; break;
            case ProvidedCoverBonus:            self->ProvidedCoverBonus += amount; break;
            case DefectThresholdOffset:         self->DefectThresholdOffset += amount; break;
            case CoverTypeOffset:               self->CoverTypeOffset += amount; break;
            case DamageToArmorDurability:       self->DamageToArmorDurability += (float)amount; break;
            case DamageToArmorDurabilityDropoff:self->DamageToArmorDurabilityDropoff += (float)amount; break;
            case GetDismemberedMinParts:        self->GetDismemberedMinParts += amount; break;
            case GetDismemberedMaxParts:        self->GetDismemberedMaxParts += amount; break;
            case MoraleStateOffset:             self->MoraleStateOffset += amount; break;
            case CoverGainedByVehicleOffset:    self->CoverGainedByVehicleOffset += amount; break;
            case DeploymentZoneMinExtend:       self->DeploymentZoneMinExtend += amount; break;
            case HitchanceMin:                  self->HitchanceMin += amount; break;
            case CriticalChance:                self->CriticalChance += amount; break;
            case ArmorDurabilityPerElement:     self->ArmorDurabilityPerElement += (float)amount; break;
            default:
                throw NullReferenceException(); // out-of-range enum — fatal
        }
    } else {
        throw NullReferenceException(); // mult property passed to flat updater — fatal
    }
}
```

### Design notes

`Armor` (case 4) is the only property that writes three fields simultaneously. All other properties map 1:1. The `DamageToArmorDurabilityDropoffMult` (60) and `DamageToArmorDurabilityMult` (35) are absent — they are mult properties handled exclusively by `UpdateMultProperty`.

---

## 6. EntityProperties.UpdateMultProperty — 0x1806293B0

### Raw Ghidra output
```c
void FUN_1806293b0(longlong param_1, undefined4 param_2, float param_3)
{
  // [IL2CPP init guards omitted]
  cVar1 = FUN_180637d60(param_2, 0);  // IsMultProperty check
  if (cVar1 != '\0') {
    switch(param_2) {
    case 9:   FUN_1805316d0(param_1 + 0x6c, param_3, 0); return;   // AccuracyMult
    case 10:  FUN_1805316d0(param_1 + 0x84, param_3, 0); return;   // DefenseMult
    case 0xb: FUN_1805316d0(param_1 + 0x8c, param_3, 0); return;   // DamageSustainedMult
    case 0xc: FUN_1805316d0(param_1 + 0xdc, param_3, 0); return;   // SuppressionImpactMult
    case 0xd: FUN_1805316d0(param_1 + 0x28, param_3, 0); return;   // ArmorMult
    case 0xe: FUN_1805316d0(param_1 + 0x74, param_3, 0); return;   // AccuracyDropoffMult
    case 0xf: FUN_1805316d0(param_1 + 0x10c, param_3, 0); return;  // ArmorPenetrationDropoffMult
    case 0x10: FUN_1805316d0(param_1 + 0x124, param_3, 0); return; // DamageDropoffMult
    case 0x11: FUN_1805316d0(param_1 + 0xd8, param_3, 0); return;  // ConcealmentMult
    case 0x12: FUN_1805316d0(param_1 + 0x11c, param_3, 0); return; // DamageMult
    case 0x13: FUN_1805316d0(param_1 + 0xd0, param_3, 0); return;  // DetectionMult
    case 0x14: FUN_1805316d0(param_1 + 200, param_3, 0); return;   // VisionMult (200 = 0xC8)
    case 0x15: FUN_1805316d0(param_1 + 0xa4, param_3, 0); return;  // DisciplineMult
    case 0x16: FUN_1805316d0(param_1 + 0x38, param_3, 0); return;  // ActionPointsMult
    case 0x17: FUN_1805316d0(param_1 + 0x104, param_3, 0); return; // ArmorPenetrationMult
    case 0x18: FUN_1805316d0(param_1 + 0x88, param_3, 0); return;  // CoverEffectivenessMult
    case 0x19: FUN_1805316d0(param_1 + 0xe4, param_3, 0); return;  // SuppressionDealtMult
    case 0x1a: FUN_1805316d0(param_1 + 0x140, param_3, 0); return; // TotalDamageMult
    case 0x1b: FUN_1805316d0(param_1 + 0x158, param_3, 0); return; // GetDismemberedChanceMult
    case 0x1c: FUN_1805316d0(param_1 + 0x18, param_3, 0); return;  // HitpointsPerElementMult
    case 0x23: FUN_1805316d0(param_1 + 0x130, param_3, 0); return; // DamageToArmorDurabilityMult (35)
    case 0x24: FUN_1805316d0(param_1 + 0xb8, param_3, 0); return;  // DamageToMoraleMult
    case 0x29: FUN_1805316d0(param_1 + 0xb0, param_3, 0); return;  // MoraleMult
    case 0x2b: FUN_1805316d0(param_1 + 0xb4, param_3, 0); return;  // MoraleRecoveryMult
    case 0x2c: FUN_1805316d0(param_1 + 0xbc, param_3, 0); return;  // MoraleImpactMult
    case 0x2e: *(float *)(param_1 + 0x170) += param_3; return;     // ElementsHitPct — additive, no AccumulateMultiplier
    case 0x2f: FUN_1805316d0(param_1 + 0x184, param_3, 0); return; // AIPriorityMult
    case 0x31: *(float *)(param_1 + 0x114) += param_3; return;     // IgnoreCoverMult — additive, no AccumulateMultiplier
    case 0x34: FUN_1805316d0(param_1 + 0xf0, param_3, 0); return;  // PromotionCostMult
    case 0x37: FUN_1805316d0(param_1 + 0x5c, param_3, 0); return;  // BackwardsMovementMult
    case 0x39: FUN_1805316d0(param_1 + 0xf4, param_3, 0); return;  // DeploymentZoneMult
    case 0x3c: FUN_1805316d0(param_1 + 0x138, param_3, 0); return; // DamageToArmorDurabilityDropoffMult (60)
    case 0x40: FUN_1805316d0(param_1 + 0xfc, param_3, 0); return;  // DeployCostMult
    case 0x43: FUN_1805316d0(param_1 + 0x90, param_3, 0); return;  // DamageSustainedSquadLeaderMult
    case 0x47: FUN_1805316d0(param_1 + 0x80, param_3, 0); return;  // CriticalDamageMult
    default:   // out-of-range enum value → runtime exception
    }
  }
  // flat property passed to mult updater → runtime exception
}
```

### Annotated reconstruction
```c
void EntityProperties_UpdateMultProperty(EntityProperties* self,
                                          EntityPropertyType propertyType,
                                          float multiplierValue)
{
    // IL2CPP lazy init — omitted
    
    bool isMult = IsMultProperty(propertyType);
    if (isMult) {
        switch (propertyType) {
            case AccuracyMult:                       AccumulateMultiplier(&self->AccuracyMult, multiplierValue); break;
            case DefenseMult:                        AccumulateMultiplier(&self->DefenseMult, multiplierValue); break;
            case DamageSustainedMult:                AccumulateMultiplier(&self->DamageSustainedMult, multiplierValue); break;
            case SuppressionImpactMult:              AccumulateMultiplier(&self->SuppressionImpactMult, multiplierValue); break;
            case ArmorMult:                          AccumulateMultiplier(&self->ArmorMult, multiplierValue); break;
            case AccuracyDropoffMult:                AccumulateMultiplier(&self->AccuracyDropoffMult, multiplierValue); break;
            case ArmorPenetrationDropoffMult:        AccumulateMultiplier(&self->ArmorPenetrationDropoffMult, multiplierValue); break;
            case DamageDropoffMult:                  AccumulateMultiplier(&self->DamageDropoffMult, multiplierValue); break;
            case ConcealmentMult:                    AccumulateMultiplier(&self->ConcealmentMult, multiplierValue); break;
            case DamageMult:                         AccumulateMultiplier(&self->DamageMult, multiplierValue); break;
            case DetectionMult:                      AccumulateMultiplier(&self->DetectionMult, multiplierValue); break;
            case VisionMult:                         AccumulateMultiplier(&self->VisionMult, multiplierValue); break;
            case DisciplineMult:                     AccumulateMultiplier(&self->DisciplineMult, multiplierValue); break;
            case ActionPointsMult:                   AccumulateMultiplier(&self->ActionPointsMult, multiplierValue); break;
            case ArmorPenetrationMult:               AccumulateMultiplier(&self->ArmorPenetrationMult, multiplierValue); break;
            case CoverEffectivenessMult:             AccumulateMultiplier(&self->CoverEffectivenessMult, multiplierValue); break;
            case SuppressionDealtMult:               AccumulateMultiplier(&self->SuppressionDealtMult, multiplierValue); break;
            case TotalDamageMult:                    AccumulateMultiplier(&self->TotalDamageMult, multiplierValue); break;
            case GetDismemberedChanceMult:           AccumulateMultiplier(&self->GetDismemberedChanceMult, multiplierValue); break;
            case HitpointsPerElementMult:            AccumulateMultiplier(&self->HitpointsPerElementMult, multiplierValue); break;
            case DamageToArmorDurabilityMult:        AccumulateMultiplier(&self->DamageToArmorDurabilityMult, multiplierValue); break;
            case DamageToMoraleMult:                 AccumulateMultiplier(&self->DamageToMoraleMult, multiplierValue); break;
            case MoraleMult:                         AccumulateMultiplier(&self->MoraleMult, multiplierValue); break;
            case MoraleRecoveryMult:                 AccumulateMultiplier(&self->MoraleRecoveryMult, multiplierValue); break;
            case MoraleImpactMult:                   AccumulateMultiplier(&self->MoraleImpactMult, multiplierValue); break;
            case ElementsHitPct:                     self->ElementsHitPct += multiplierValue; break; // EXCEPTION: direct add, not AccumulateMultiplier
            case AIPriorityMult:                     AccumulateMultiplier(&self->AIPriorityMult, multiplierValue); break;
            case IgnoreCoverMult:                    self->IgnoreCoverMult += multiplierValue; break; // EXCEPTION: direct add, not AccumulateMultiplier
            case PromotionCostMult:                  AccumulateMultiplier(&self->PromotionCostMult, multiplierValue); break;
            case BackwardsMovementMult:              AccumulateMultiplier(&self->BackwardsMovementMult, multiplierValue); break;
            case DeploymentZoneMult:                 AccumulateMultiplier(&self->DeploymentZoneMult, multiplierValue); break;
            case DamageToArmorDurabilityDropoffMult: AccumulateMultiplier(&self->DamageToArmorDurabilityDropoffMult, multiplierValue); break;
            case DeployCostMult:                     AccumulateMultiplier(&self->DeployCostMult, multiplierValue); break;
            case DamageSustainedSquadLeaderMult:     AccumulateMultiplier(&self->DamageSustainedSquadLeaderMult, multiplierValue); break;
            case CriticalDamageMult:                 AccumulateMultiplier(&self->CriticalDamageMult, multiplierValue); break;
            default:
                throw NullReferenceException(); // out-of-range enum — fatal
        }
    } else {
        throw NullReferenceException(); // flat property passed to mult updater — fatal
    }
}
```

### Design notes

Two properties use direct addition instead of `AccumulateMultiplier`: `ElementsHitPct` (46) and `IgnoreCoverMult` (49). These receive the raw `multiplierValue` directly rather than `(multiplierValue - 1.0)`. This means their accumulation semantics differ from all other mult properties — a value of `0.5` adds `0.5` to the field, whereas for other mults the same value would subtract `0.5`. This appears to be an intentional design distinction for these two properties.

---

## 7. EntityProperties.NewEmpty — 0x1806290F0

### Raw Ghidra output
```c
longlong FUN_1806290f0(void)
{
  longlong lVar1;
  // [IL2CPP init guard omitted]
  lVar1 = thunk_FUN_1804608d0(DAT_183981fc8);  // allocate EntityProperties instance
  FUN_18062a050(lVar1, 0);                      // constructor call
  if (lVar1 != 0) {
    *(undefined8 *)(lVar1 + 0x18) = 0x3f800000;  // HitpointsPerElementMult = 1.0
    *(undefined4 *)(lVar1 + 0x68) = 0;            // Accuracy = 0
    *(undefined4 *)(lVar1 + 0xd4) = 0;            // Concealment = 0
    *(undefined8 *)(lVar1 + 0x114) = 0;           // IgnoreCoverMult = 0 (also covers adjacent field)
    *(undefined4 *)(lVar1 + 0xcc) = 0;            // Detection = 0
    *(undefined4 *)(lVar1 + 0xa0) = 0;            // Discipline = 0
    *(undefined4 *)(lVar1 + 0xac) = 0;            // MoraleBonus = 0
    *(undefined4 *)(lVar1 + 0xc4) = 0;            // Vision = 0
    *(undefined4 *)(lVar1 + 0x34) = 0;            // ActionPoints = 0
    *(undefined8 *)(lVar1 + 0x16c) = 0;           // ElementsHit = 0
    *(undefined8 *)(lVar1 + 0x174) = 0;           // ReduceElementsHit = 0
    *(undefined8 *)(lVar1 + 0xe8) = 0;            // SuppressionDealtDropoffAOE = 0
    *(undefined8 *)(lVar1 + 0x10) = 0;            // MaxElements = 0
    *(undefined4 *)(lVar1 + 0xe0) = 0;            // SuppressionDealt = 0
    *(undefined4 *)(lVar1 + 0x40) = 0;            // AdditionalTurningCost = 0
    *(undefined8 *)(lVar1 + 0x50) = 0;            // APEnterCost = 0 (covers APLeaveCost too)
    *(undefined4 *)(lVar1 + 0x154) = 0;           // GetDismemberedChanceBonus = 0
    *(undefined4 *)(lVar1 + 0x168) = 0;           // DismemberArea = 0
    *(undefined8 *)(lVar1 + 0x148) = 0;           // DamagePctCurrentHitpointsMin
    *(undefined4 *)(lVar1 + 0x150) = 0;           // DamagePctMaxHitpoints
    *(undefined4 *)(lVar1 + 300) = 0;             // DamageToArmorDurability = 0  (300 = 0x12C)
    *(undefined8 *)(lVar1 + 0x94) = 0;            // ProvidedCoverBonus = 0
    // All multiplier fields initialized to 1.0 (0x3f800000):
    *(undefined4 *)(lVar1 + 0xb0) = 0x3f800000;  // MoraleMult = 1.0
    *(undefined4 *)(lVar1 + 0xb4) = 0x3f800000;  // MoraleRecoveryMult = 1.0
    *(undefined8 *)(lVar1 + 0xbc) = 0x3f800000;  // MoraleImpactMult = 1.0
    *(undefined8 *)(lVar1 + 0x6c) = 0x3f800000;  // AccuracyMult = 1.0
    *(undefined4 *)(lVar1 + 0x28) = 0x3f800000;  // ArmorMult = 1.0
    *(undefined8 *)(lVar1 + 0xfc) = 0x3f800000;  // DeployCostMult = 1.0
    *(undefined4 *)(lVar1 + 0xd8) = 0x3f800000;  // ConcealmentMult = 1.0
    *(undefined8 *)(lVar1 + 0x11c) = 0x3f800000; // DamageMult = 1.0
    *(undefined4 *)(lVar1 + 0x84) = 0x3f800000;  // DefenseMult = 1.0
    *(undefined4 *)(lVar1 + 0xd0) = 0x3f800000;  // DetectionMult = 1.0
    *(undefined4 *)(lVar1 + 0xa4) = 0x3f800000;  // DisciplineMult = 1.0
    *(undefined4 *)(lVar1 + 200) = 0x3f800000;   // VisionMult = 1.0  (200 = 0xC8)
    *(undefined4 *)(lVar1 + 0x74) = 0x3f800000;  // AccuracyDropoffMult = 1.0
    *(undefined8 *)(lVar1 + 0x38) = 0x3f800000;  // ActionPointsMult = 1.0
    *(undefined8 *)(lVar1 + 0x104) = 0x3f800000; // ArmorPenetrationMult = 1.0
    *(undefined4 *)(lVar1 + 0x88) = 0x3f800000;  // CoverEffectivenessMult = 1.0
    *(undefined4 *)(lVar1 + 0x124) = 0x3f800000; // DamageDropoffMult = 1.0
    *(undefined4 *)(lVar1 + 0x8c) = 0x3f800000;  // DamageSustainedMult = 1.0
    *(undefined4 *)(lVar1 + 0xe4) = 0x3f800000;  // SuppressionDealtMult = 1.0
    *(undefined4 *)(lVar1 + 0xdc) = 0x3f800000;  // SuppressionImpactMult = 1.0
    *(undefined8 *)(lVar1 + 0x140) = 0x3f800000; // TotalDamageMult = 1.0
    *(undefined4 *)(lVar1 + 0x10c) = 0x3f800000; // ArmorPenetrationDropoffMult = 1.0
    *(undefined4 *)(lVar1 + 0x158) = 0x3f800000; // GetDismemberedChanceMult = 1.0
    *(undefined4 *)(lVar1 + 0x15c) = 1;           // GetDismemberedMinParts = 1
    *(undefined8 *)(lVar1 + 0x160) = 1;           // GetDismemberedMaxParts = 1
    *(undefined8 *)(lVar1 + 0x130) = 0x3f800000; // DamageToArmorDurabilityMult = 1.0
    *(undefined4 *)(lVar1 + 0x138) = 0x3f800000; // DamageToArmorDurabilityDropoffMult = 1.0
    *(undefined4 *)(lVar1 + 0xb8) = 0x3f800000;  // DamageToMoraleMult = 1.0
    *(undefined4 *)(lVar1 + 0x184) = 0x3f800000; // AIPriorityMult = 1.0
    *(undefined4 *)(lVar1 + 0xf0) = 0x3f800000;  // PromotionCostMult = 1.0
    *(undefined4 *)(lVar1 + 0x5c) = 0x3f800000;  // BackwardsMovementMult = 1.0
    *(undefined8 *)(lVar1 + 0xf4) = 0x3f800000;  // DeploymentZoneMult = 1.0
    return lVar1;
  }
  throw NullReferenceException();
}
```

### Annotated reconstruction
```c
EntityProperties* EntityProperties_NewEmpty()
{
    // IL2CPP lazy init — omitted
    EntityProperties* self = AllocateObject(EntityProperties_class);
    EntityProperties_ctor(self);
    
    if (self == null) throw NullReferenceException();
    
    // All flat property fields initialized to 0 (no contribution)
    self->HitpointsPerElementMult              = 1.0f; // note: written as 8-byte store covering adjacent field
    self->Accuracy                             = 0;
    self->Concealment                          = 0;
    self->IgnoreCoverMult                      = 0;
    self->Detection                            = 0;
    self->Discipline                           = 0;
    self->MoraleBonus                          = 0;
    self->Vision                               = 0;
    self->ActionPoints                         = 0;
    self->ElementsHit                          = 0;
    self->ReduceElementsHit                    = 0;
    self->MaxElements                          = 0;
    self->SuppressionDealt                     = 0;
    self->AdditionalTurningCost                = 0;
    self->APEnterCost                          = 0;
    self->APLeaveCost                          = 0;
    self->GetDismemberedChanceBonus            = 0;
    self->DamageToArmorDurability              = 0;     // KEY: flat armor durability damage starts at 0
    self->ProvidedCoverBonus                   = 0;

    // All multiplier fields initialized to 1.0 (neutral — no change)
    self->MoraleMult                           = 1.0f;
    self->MoraleRecoveryMult                   = 1.0f;
    self->MoraleImpactMult                     = 1.0f;
    self->AccuracyMult                         = 1.0f;
    self->ArmorMult                            = 1.0f;
    self->DeployCostMult                       = 1.0f;
    self->ConcealmentMult                      = 1.0f;
    self->DamageMult                           = 1.0f;
    self->DefenseMult                          = 1.0f;
    self->DetectionMult                        = 1.0f;
    self->DisciplineMult                       = 1.0f;
    self->VisionMult                           = 1.0f;
    self->AccuracyDropoffMult                  = 1.0f;
    self->ActionPointsMult                     = 1.0f;
    self->ArmorPenetrationMult                 = 1.0f;  // KEY: penetration mult starts neutral
    self->CoverEffectivenessMult               = 1.0f;
    self->DamageDropoffMult                    = 1.0f;
    self->DamageSustainedMult                  = 1.0f;
    self->SuppressionDealtMult                 = 1.0f;
    self->SuppressionImpactMult                = 1.0f;
    self->TotalDamageMult                      = 1.0f;
    self->ArmorPenetrationDropoffMult          = 1.0f;
    self->GetDismemberedChanceMult             = 1.0f;
    self->GetDismemberedMinParts               = 1;
    self->GetDismemberedMaxParts               = 1;
    self->DamageToArmorDurabilityMult          = 1.0f;  // KEY: armor durability mult starts neutral
    self->DamageToArmorDurabilityDropoffMult   = 1.0f;
    self->DamageToMoraleMult                   = 1.0f;
    self->AIPriorityMult                       = 1.0f;
    self->PromotionCostMult                    = 1.0f;
    self->BackwardsMovementMult                = 1.0f;
    self->DeploymentZoneMult                   = 1.0f;

    return self;
}
```

---

## 8. Entity.OnDamageReceived (EntityProperties overload) — 0x180616EF0

### Raw Ghidra output

See session log. Function body was provided in full and is approximately 250 lines of Ghidra pseudocode.

### Annotated reconstruction

```c
DamageInfo Entity_OnDamageReceived(Entity*          self,
                                    Entity*          attacker,
                                    Skill*           skill,
                                    DamageInfo*      damageInfo,      // param_4
                                    EntityProperties* properties)     // param_5
{
    // IL2CPP lazy init — omitted
    
    // Early out: entity has no elements or is not alive
    if (self->m_IsAlive == false)        return *damageInfo;
    if (self->m_Elements == null)        return *damageInfo;
    if (self->m_Elements->Count == 0)   return *damageInfo;

    EntityProperties* weaponProps = self->vtable->GetEntityWeaponProperties(self);
    
    // Snapshot current armor durability before any modification
    int durabilityBefore = self->m_ArmorDurability;   // +0x5C

    if (damageInfo != null && properties != null) {

        // --- Penetration check ---
        // GetArmor for the direction this hit came from
        int armorValue    = GetArmor(properties, damageInfo->ArmorDirection);   // +0x30
        int netPenetration = armorValue - damageInfo->ArmorPenetration;         // +0x34
        if (netPenetration < 0) netPenetration = 0;

        // Effective hit chance modifier from penetration margin
        // Higher armor over penetration = lower chance to penetrate
        int penetrationHitChance = 100 - (netPenetration * 3);
        if (penetrationHitChance < 0) penetrationHitChance = 0;

        // Per-element armor durability ratio used in damage formula
        float maxDurabilityF = (float)self->m_ArmorDurabilityMax;        // +0x60 (via param_1[0xc])
        if (maxDurabilityF < 1.0f) maxDurabilityF = 1.0f;                // prevent divide-by-zero

        // Penetration threshold: does current armor durability still resist?
        float penetrationThreshold = (float)armorValue
                                   * ((float)self->m_ArmorDurability / maxDurabilityF)  // +0x5C
                                   - (float)damageInfo->ArmorPenetration;
        if (penetrationThreshold < 0.0f) penetrationThreshold = 0.0f;

        int penetrationHitChance2 = (int)(100.0f - penetrationThreshold * 3.0f);
        if (penetrationHitChance2 < 0) penetrationHitChance2 = 0;

        // Set penetration flag on DamageInfo
        damageInfo->IsAbleToPenetrate = (penetrationHitChance2 > 0);

        // Snapshot durability again (used to compute final ArmorDamage at end)
        int durabilitySnapshot = self->m_ArmorDurability;

        // Number of elements to process
        int numElementsToHit = min(self->m_Elements->Count, damageInfo->ElementsHit);

        // --- Per-element damage loop ---
        for (int i = 0; i < numElementsToHit; i++) {

            // Roll penetration check
            int roll = RollD100(weaponProps);  // FUN_18053d2e0

            if (penetrationHitChance2 < roll) {
                // --- HIT PENETRATES ---
                
                // Get the element for this iteration
                Element* element = GetElement(self, numElementsToHit);

                float durF1 = (float)self->m_ArmorDurabilityMax;
                if (durF1 < 1.0f) durF1 = 1.0f;
                float durF2 = (float)self->m_ArmorDurabilityMax;
                if (durF2 < 1.0f) durF2 = 1.0f;

                // D = current / max (per-element ratio)
                float D = (float)self->m_ArmorDurability / (float)self->m_Elements->Count;

                // Penetrating armor durability damage formula:
                // damage = ArmorDamage * D * D   (quadratic scaling)
                float armorDmg = (float)damageInfo->ArmorDamage       // +0x38
                               * ((float)self->m_ArmorDurability / durF1)
                               * ((float)self->m_ArmorDurability / durF2);

                // Cap: cannot remove more than one element's share of durability
                if (armorDmg > D) armorDmg = D;

                // Apply durability damage
                int newDurability = (int)roundf((float)self->m_ArmorDurability - armorDmg);
                if (newDurability < 0) newDurability = 0;
                self->m_ArmorDurability = newDurability;                // +0x5C

                // Recalculate penetration chance for next iteration with updated durability
                float updatedThreshold = (float)armorValue
                                       * ((float)newDurability / durF1)
                                       - (float)damageInfo->ArmorPenetration;
                if (updatedThreshold < 0.0f) updatedThreshold = 0.0f;
                penetrationHitChance2 = (int)(100.0f - (updatedThreshold + updatedThreshold));
                if (penetrationHitChance2 < 0) penetrationHitChance2 = 0;

            } else {
                // --- HIT DOES NOT PENETRATE ---
                successfulPenetrationsThisHit++;
            }
        }

        // --- Non-penetrating elements loop ---
        // For each element that did NOT penetrate:
        while (successfulPenetrationsThisHit > 0) {
            successfulPenetrationsThisHit--;

            Element* element = GetLastLivingElement(self);
            if (element == null || !element->m_IsAlive) break;

            // Hitpoint damage for non-penetrating hit
            int elementHP = element->m_Hitpoints;
            float damageRoll = (float)damageInfo->Damage * RollDamageVariance(weaponProps);
            if (element->m_SquaddieId == 0) {
                // Leader element: apply squad leader damage mult
                damageRoll *= properties->DamageSustainedSquadLeaderMult;  // +0x238 on template
            }
            int hpDamage = (int)min(damageRoll, (float)damageInfo->Damage);
            int actualHPDamage = min(hpDamage, elementHP);

            successfulHPDamageTotal += actualHPDamage;
            SetHitpoints(element, elementHP - actualHPDamage);  // FUN_180604210
            damageInfo->IsDamageInflicted = true;

            // If element is killed by this hit:
            if (element->m_Hitpoints == 0) {

                // Check if the entity template has armor-linked durability loss on element death
                if (entityTemplate->hasArmorLinkedDurabilityLoss) {
                    // Remove one element's share of durability on element death
                    int durLoss = self->m_ArmorDurability
                                - self->m_ArmorDurability / self->m_Elements->Count;
                    if (durLoss < 0) durLoss = 0;
                    self->m_ArmorDurability = durLoss;

                    int maxDurLoss = (int)self->m_ArmorDurabilityMax
                                  - (int)self->m_ArmorDurabilityMax / self->m_Elements->Count;
                    if (maxDurLoss < 0) maxDurLoss = 0;
                    self->m_ArmorDurabilityMax = maxDurLoss;

                    // Trigger element death event
                    OnElementDeath(self, element, attacker, damageInfo, actualHPDamage, skill);
                    continue; // back to top of while loop
                }

                // No armor-linked loss — standard non-penetrating durability damage:
                float durF3 = (float)self->m_ArmorDurabilityMax;
                if (durF3 < 1.0f) durF3 = 1.0f;
                float durF4 = (float)self->m_ArmorDurabilityMax;
                if (durF4 < 1.0f) durF4 = 1.0f;

                // penetrationRatio = max(0.3, penetrationHitChance * 0.01)
                float penetrationRatio = (float)penetrationHitChance * 0.01f;
                if (penetrationRatio < 0.3f) penetrationRatio = 0.3f;

                // Non-penetrating armor durability damage formula:
                // damage = ArmorDamage * 0.15 * D² * penetrationRatio
                float D_nonpen = (float)self->m_ArmorDurability / (float)self->m_Elements->Count;
                float armorDmgNonPen = (float)damageInfo->ArmorDamage    // +0x38
                                     * 0.15f
                                     * ((float)self->m_ArmorDurability / durF3)
                                     * ((float)self->m_ArmorDurability / durF4)
                                     * penetrationRatio;

                // Cap: cannot remove more than one element's share
                if (armorDmgNonPen > D_nonpen) armorDmgNonPen = D_nonpen;

                int newDur = (int)roundf((float)self->m_ArmorDurability - armorDmgNonPen);
                if (newDur < 0) newDur = 0;
                self->m_ArmorDurability = newDur;   // +0x5C

                // Trigger element hit event
                OnElementHit(self, element, attacker, damageInfo, actualHPDamage, skill);
            }
        }
    }

    // Commit final values to DamageInfo
    damageInfo->Damage    = successfulHPDamageTotal;              // +0x2C
    damageInfo->ArmorDamage = durabilitySnapshot - self->m_ArmorDurability;  // +0x38 — actual durability removed

    // [Defect system — scope boundary — not reconstructed]
    // [Element destruction flag setting — omitted]
    // [Entity death check — omitted]
    // [Element update loop — omitted]

    return *damageInfo;
}
```

### OnDamageReceived — design notes

**The durability formula is quadratic.** The term `(m_ArmorDurability / m_ArmorDurabilityMax)²` means fresh armor takes full theoretical damage, but 50% durability armor takes only 25%, and 10% durability armor takes only 1%. This is deliberate — the designers wanted armor to be hard to fully destroy once significantly degraded.

**Non-penetrating hits apply 15% of the penetrating formula.** Even a complete miss in terms of armor penetration still damages the armor. The `0.15` scalar combined with the `penetrationRatio` floor of `0.3` means the minimum non-penetrating durability damage is `ArmorDamage * 0.15 * D² * 0.3`.

**Penetration chance recalculates after each element.** After a penetrating hit reduces `m_ArmorDurability`, the penetration check threshold is recalculated for the next element in the loop. As durability drops, subsequent elements in the same attack are more likely to be penetrated. This creates a snowball effect within a single multi-element attack.

**Armor-linked durability on element death.** Some entity templates have a flag (`hasArmorLinkedDurabilityLoss`, confirmed at template offset `0xf9`) that ties durability pool to the number of living elements. When an element dies, one proportional share of durability is removed from both `m_ArmorDurability` and `m_ArmorDurabilityMax`. This represents vehicle subsystems or armor segments being destroyed rather than just worn down.

**`DamageInfo.ArmorDamage` is overwritten on exit** with the actual durability removed (`durabilitySnapshot - m_ArmorDurability`), not the theoretical value that entered the function.

---

## 9. Entity.Create — 0x180613FD0 (partial — armor initialization only)

### Raw Ghidra output (relevant section only)

```c
// Near end of FUN_180613fd0, after element creation loop:
iVar12 = FUN_1806286d0(lVar7, 0);   // GetHitpointsPerElement
*(int *)(param_1 + 0xb) = iVar12 * (int)param_1[5];   // total hitpoints

iVar12 = FUN_1806282d0(lVar7, 0);   // GetArmorDurabilityPerElement
*(int *)((longlong)param_1 + 0x5c) = iVar12 * (int)param_1[5];   // m_ArmorDurability

iVar12 = FUN_1806282d0(lVar7, 0);   // GetArmorDurabilityPerElement (called again)
*(int *)(param_1 + 0xc) = iVar12 * (int)param_1[5];   // m_ArmorDurabilityMax
```

### Annotated reconstruction

```c
// During entity initialization, after all elements have been created:
int hpPerElement      = EntityProperties_GetHitpointsPerElement(entityProperties);
// [total hitpoints stored — not relevant to armor investigation]

int durabilityPerElem = EntityProperties_GetArmorDurabilityPerElement(entityProperties);
int numElements       = (int)self->m_Elements->Count;  // param_1[5]

self->m_ArmorDurability    = durabilityPerElem * numElements;   // +0x5C — current pool
self->m_ArmorDurabilityMax = durabilityPerElem * numElements;   // +0x60 — maximum pool
// Both initialized to the same value. m_ArmorDurabilityMax never changes after this.
```

### Design notes

`GetArmorDurabilityPerElement` is called twice and produces the same result both times (no side effects). Both `m_ArmorDurability` and `m_ArmorDurabilityMax` are set to `ArmorDurabilityPerElement * numElements`. The maximum is fixed at creation; only the current value is decremented during combat.
