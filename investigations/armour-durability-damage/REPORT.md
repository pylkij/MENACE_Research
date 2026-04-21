# Menace — Armor Damage System — REPORT.md

**Game:** Menace  
**Platform:** Windows x64, Unity IL2CPP  
**Image base:** `0x180000000`  
**Source material:** `dump.cs` (Il2CppDumper, ~885,000 lines), Ghidra decompilation, custom asset extractor (AssetRipper-based)  
**Investigation status:** Complete (Rend Ammo finding updated with runtime verification — see Section 15)  

---

## Table of Contents

1. Investigation Overview
2. Class Inventory
3. Core Finding — Armor Durability Damage Formula
4. Full Pipeline
5. Class Reference: DamageArmorDurability
6. Class Reference: PropertyChange / ChangePropertyConditional
7. Class Reference: EntityPropertyType (enum)
8. Class Reference: EntityProperties
9. Class Reference: Entity
10. Class Reference: Element
11. Class Reference: DamageInfo
12. Ghidra Address Reference
13. Key Inferences and Design Notes
14. Open Questions
15. Runtime Verification — Rend Ammo Non-Functional

---

## 1. Investigation Overview

### What is being investigated

The armor damage system in Menace — specifically how attacking weapons and skills reduce a target entity's **armor durability** pool, and how the Rend Ammo skill modifies that behavior.

Menace uses a two-layer armor model:

- **Armor** (`Armor`, `ArmorSide`, `ArmorBack`) — static resistance values that determine whether a hit penetrates. These do not change during combat.
- **Armor Durability** (`m_ArmorDurability`) — a pool that is consumed by hits. As durability falls, penetration thresholds shift and the armor becomes progressively less effective.

### What was achieved

- Confirmed the full data path from skill/ammo property modifiers through to the final durability decrement on `Entity`.
- Identified the two distinct armor durability damage formulas (penetrating and non-penetrating hits).
- Confirmed that durability damage scales **quadratically** with current durability — fresh armor degrades faster than worn armor.
- Confirmed that the `DamageToArmorDurabilityMult` and related multipliers are accumulated additively (not multiplicatively) using an offset-from-1.0 convention.
- Confirmed the `PropertyChange` struct layout and how `ChangePropertyConditional` applies skill/ammo modifiers to an `EntityProperties` modifier object.
- Confirmed the `DamageInfo` struct layout, identifying `ArmorDamage` as the durability damage carrier.
- Confirmed how `Entity.OnDamageReceived` is the final applicator of durability damage.
- Traced the Rend Ammo skill's modifier structure and interpreted its likely effect.

### What was NOT investigated

- Concrete subclasses of `Element` (e.g. infantry vs vehicle element types) and their `OnHit` overrides.
- The morale system (`DamageToMoraleMult`, `MoraleImpactMult`).
- The full hit-chance calculation pipeline (`FUN_1806e6490`) — confirmed to be accuracy/dropoff, not durability.
- The `DamageArmorDurability` skill event handler's three fields (`DamageFlatAmount`, `DamagePercentageOfMaxDurability`, `DamagePercentageOfCurrentDurability`) were not traced to their point of consumption in `EntityProperties` assembly. They are confirmed as inputs to `DamageInfo.ArmorDamage` but the assembly step was not decompiled.
- Dismemberment, fatality, and critical hit systems.
- The `FUN_18062d040` armor penetration resolver — confirmed to exist upstream of hit resolution but not decompiled.

---

## 2. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| `DamageArmorDurability` | `Menace.Tactical.Skills.Effects` | 3387 | Skill event handler that contributes armor durability damage to an attack |
| `ChangePropertyConditional` | `Menace.Tactical.Skills.Effects` | 3349 | Skill event handler that applies conditional property modifiers (including Rend Ammo) |
| `PropertyChange` | `Menace.Tactical.Skills.Effects` | 3485 | Struct holding one property modifier: type, flat amount, multiplier delta |
| `EntityPropertyType` | `Menace.Tactical` | 2812 | Enum mapping property names to integer IDs (0–71) |
| `EntityProperties` | `Menace.Tactical` | 2811 | Class holding all entity combat stats as flat fields; used both as a base stat block and as a modifier accumulator |
| `Entity` | `Menace.Tactical` | 2807 | Abstract base for all tactical entities; owns `m_ArmorDurability` and `m_ArmorDurabilityMax`; final applicator of durability damage |
| `Element` | `Menace.Tactical` | 2763 | Per-element (squaddie/vehicle component) visual and gameplay state; receives `OnHit` calls |
| `DamageInfo` | `Menace.Tactical` | 2638 | Struct carrying resolved damage values for one hit: damage, armor direction, armor damage, penetration, flags |

---

## 3. Core Finding — Armor Durability Damage Formula

### Non-penetrating hit

Shot is stopped by the plate; all kinetic energy is absorbed by the armor.

```
armorDamage = DamageInfo.ArmorDamage
            * (m_ArmorDurability / m_ArmorDurabilityMax)   // pct of max, call it D
            * (m_ArmorDurability / m_ArmorDurabilityMax)   // squared

cap = m_ArmorDurability / numElements

if armorDamage > cap:
    armorDamage = cap

m_ArmorDurability = max(0, m_ArmorDurability - armorDamage)
```

### Penetrating hit

Shot punches through the plate; most energy is expended on the target beyond it.

```
penetrationRatio  = max(0.3, ArmorPenetrationRatio * 0.01)   // floored at 0.30
armorDamage = DamageInfo.ArmorDamage * 0.15
            * (m_ArmorDurability / m_ArmorDurabilityMax)     // pct of max
            * (m_ArmorDurability / m_ArmorDurabilityMax)     // squared
            * penetrationRatio

cap = m_ArmorDurability / numElements

if armorDamage > cap:
    armorDamage = cap

m_ArmorDurability = max(0, m_ArmorDurability - armorDamage)
```

### Recording the result

```
DamageInfo.ArmorDamage = armorDurabilityBefore - m_ArmorDurability
```

The field is overwritten with the actual durability lost, not the theoretical damage value.

### Plain-English explanation

Armor durability damage does not scale linearly. The squared `(currentDurability / maxDurability)` term means a fully intact piece of armor takes the full theoretical damage, but armor at 50% durability takes only 25% of the theoretical damage, and armor at 10% durability takes only 1%. This creates a strong asymptotic curve — armor is hardest to finish off once it is already badly damaged.

Penetrating hits deal only 15% of the non-penetrating formula, further reduced by a penetration ratio term (floored at 30%). A round that punches through the plate expends most of its energy on the target beyond it — only residual surface damage accrues to the armor. Conversely, a shot stopped by the plate transfers all its energy to the armor and uses the full `ArmorDamage * D²` formula.

The per-element cap (`m_ArmorDurability / numElements`) prevents any single hit from removing more durability than one element's share of the total pool.

---

## 4. Full Pipeline

```
Skill/Ammo definition
  └─ ChangePropertyConditional.EventHandlers[]
       └─ PropertyChange { PropertyType, Amount, AmountMult }
            │
            ▼
  EntityProperties.UpdateMultProperty(EntityPropertyType, float)
       └─ FUN_1805316d0: field += (value - 1.0)     ← additive mult accumulation
  EntityProperties.UpdateProperty(EntityPropertyType, int)
       └─ direct field += amount
            │
            ▼
  EntityProperties modifier object (NewEmpty() base: all mults = 1.0, all flats = 0)
       Fields populated:
         DamageToArmorDurability        (flat)
         DamageToArmorDurabilityMult    (mult, additive offset)
         DamageToArmorDurabilityDropoff (flat)
         DamageToArmorDurabilityDropoffMult (mult)
         ArmorPenetrationMult           (for Rend Ammo: reduced)
            │
            ▼
  EntityProperties.GetDamageToArmorDurability()
       = DamageToArmorDurability * max(0, DamageToArmorDurabilityMult)
  EntityProperties.GetDamageToArmorDurabilityDropoff()
       = DamageToArmorDurabilityDropoff * max(0, DamageToArmorDurabilityDropoffMult)
            │
            ▼
  DamageInfo assembly (FUN_180561c50 and siblings)
       DamageInfo.ArmorDamage  ← GetDamageToArmorDurability() result
       DamageInfo.ArmorPenetration
       DamageInfo.Damage
       DamageInfo.ArmorDirection
            │
            ▼
  DamageArmorDurability skill handler
       Contributes DamageFlatAmount, DamagePercentageOfMaxDurability,
       DamagePercentageOfCurrentDurability to DamageInfo.ArmorDamage
            │
            ▼
  Entity.OnDamageReceived(attacker, skill, damageInfo, properties)   ← FUN_180616ef0
       Per-element loop:
         Penetration check → selects formula branch
         armorDamage = ArmorDamage * D² (non-penetrating — shot stopped by plate, full damage)
                     = ArmorDamage * 0.15 * D² * penetrationRatio (penetrating — shot punched through, residual surface damage only)
         m_ArmorDurability = max(0, m_ArmorDurability - armorDamage)
         DamageInfo.ArmorDamage = durabilityBefore - m_ArmorDurability
            │
            ▼
  Element.OnHit(attacker, damageInfo, damageApplied, skill)
       Visual/audio response only — durability already applied
```

---

## 5. Class Reference: DamageArmorDurability

**Namespace:** `Menace.Tactical.Skills.Effects`  
**TypeDefIndex:** 3387  
**Base class:** `SkillEventHandlerTemplate`  
**Role:** A skill event handler that defines how much armor durability damage an attack inflicts. Three independent contribution modes can be combined in a single instance.

### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x58 | `float` | `DamageFlatAmount` | Range [0, 1000]. Fixed durability damage regardless of armor state. |
| 0x5C | `float` | `DamagePercentageOfMaxDurability` | Range [0, 1]. Durability damage as fraction of target's maximum pool. |
| 0x60 | `float` | `DamagePercentageOfCurrentDurability` | Range [0, 1]. Durability damage as fraction of target's current pool. Creates diminishing returns as armor degrades. |

### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Create()` | 0x70AF70 | 0x18070AF70 | Factory method, vtable slot 8. Returns a new runtime instance of this handler. |
| `.ctor()` | 0x5128C0 | 0x1805128C0 | Constructor. |

### Behavioural notes

The three fields are additive contributions to `DamageInfo.ArmorDamage`. `DamagePercentageOfCurrentDurability` is mechanically the most interesting: because the formula later squares the current-to-max ratio, this field interacts with the quadratic curve rather than bypassing it.

---

## 6. Class Reference: PropertyChange / ChangePropertyConditional

### PropertyChange

**Namespace:** `Menace.Tactical.Skills.Effects`  
**TypeDefIndex:** 3485  
**Role:** Serialized struct representing one property modifier. Used in arrays by `ChangePropertyConditional` and similar handlers.

#### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x0 | `EntityPropertyType` (int) | `PropertyType` | Which property to modify. |
| 0x4 | `int` | `Amount` | Flat additive delta. Range hint [-1000, 1000] in Inspector, not enforced at runtime. |
| 0x8 | `float` | `AmountMult` | Multiplier delta. Passed to `UpdateMultProperty` which applies `field += (value - 1.0)`. Range hint [0, 4] in Inspector, not enforced at runtime. |

#### Behavioural notes

The `Amount` field is declared `int` in the dump but asset extraction evidence suggests it may be stored as `float` in the binary serialization format. Values of `1065353216` appearing in extracted JSON are the IEEE 754 integer representation of `1.0f`. The `[Range]` attributes on both fields are Inspector-only constraints.

### ChangePropertyConditional

**Namespace:** `Menace.Tactical.Skills.Effects`  
**TypeDefIndex:** 3349  
**Base class:** `SkillEventHandlerTemplate`  
**Role:** Applies an array of `PropertyChange` modifiers to the attacker's `EntityProperties` modifier object, conditional on an `ITacticalCondition`.

#### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x58 | `ITacticalCondition` | `Condition` | Condition that must be true for this handler to fire. |
| 0x60 | `PropertyChange[]` | `Properties` | Array of property modifiers to apply. |
| 0x68 | `ChangePropertyConditional.EventType` | `Event` | Which event triggers this handler. |
| 0x6C | `bool` | `HideIfNotActive` | UI display hint only. |

#### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| `IsMultProperty(EntityPropertyType)` | 0x70AF70 | 0x18070AF70 | Returns true if the property uses the mult accumulation path. |
| `Create()` | 0x70AE70 | 0x18070AE70 | Factory, vtable slot 8. |

---

## 7. Class Reference: EntityPropertyType (enum)

**Namespace:** `Menace.Tactical`  
**TypeDefIndex:** 2812  
**Role:** Integer enum mapping property names to field indices used by `UpdateProperty`, `UpdateMultProperty`, and `GetPropertyValue`.

The enum covers values 0–71. Values outside this range that appear in `PropertyChange` arrays in extracted asset data are out-of-range and not handled by the switch statements in `UpdateProperty` or `UpdateMultProperty` — they fall through to a runtime exception path. This is likely a data serialization artifact.

### Armor-relevant entries

| Value | Name | Notes |
|---|---|---|
| 4 | `Armor` | Static armor value. UpdateProperty applies to front, side, and back simultaneously. |
| 13 | `ArmorMult` | Mult path. |
| 15 | `ArmorPenetrationDropoffMult` | Mult path. |
| 23 | `ArmorPenetrationMult` | Mult path. Key modifier for Rend Ammo. |
| 32 | `ArmorPenetration` | Flat path. |
| 35 | `DamageToArmorDurabilityMult` | Mult path. Key modifier for armor degradation rate. |
| 38 | `ArmorPenetrationDropoff` | Flat path. |
| 58 | `DamageToArmorDurability` | Flat path. Base armor durability damage. |
| 59 | `DamageToArmorDurabilityDropoff` | Flat path. |
| 60 | `DamageToArmorDurabilityDropoffMult` | Mult path. |
| 70 | `ArmorDurabilityPerElement` | Flat path. Per-element durability pool size, set on entity template. |

---

## 8. Class Reference: EntityProperties

**Namespace:** `Menace.Tactical`  
**TypeDefIndex:** 2811  
**Role:** Holds all entity combat properties as flat fields. Used in two distinct roles: (1) as a base stat block on entity templates, and (2) as a runtime modifier accumulator assembled by skill/ammo handlers before hit resolution. In role 2, all mult fields start at 1.0 and all flat fields start at 0.0 (via `NewEmpty()`).

### Armor-relevant fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x1C | `int` | `Armor` | Front armor. |
| 0x20 | `int` | `ArmorSide` | Side armor. |
| 0x24 | `int` | `ArmorBack` | Back armor. |
| 0x28 | `float` | `ArmorMult` | Mult. Init 1.0 in NewEmpty. |
| 0x2C | `float` | `ArmorDurabilityPerElement` | Per-element durability pool. Designer-set in Inspector. |
| 0x30 | `float` | `ArmorDurabilityPerElementMult` | Mult for above. |
| 0x100 | `float` | `ArmorPenetration` | Flat penetration. Hidden in Inspector. |
| 0x104 | `float` | `ArmorPenetrationMult` | Mult. Init 1.0. |
| 0x108 | `float` | `ArmorPenetrationDropoff` | Flat penetration dropoff. |
| 0x10C | `float` | `ArmorPenetrationDropoffMult` | Mult. Init 1.0. |
| 0x12C | `float` | `DamageToArmorDurability` | Flat armor durability damage. Init 0. |
| 0x130 | `float` | `DamageToArmorDurabilityMult` | Mult. Init 1.0. |
| 0x134 | `float` | `DamageToArmorDurabilityDropoff` | Flat dropoff. Init 0. |
| 0x138 | `float` | `DamageToArmorDurabilityDropoffMult` | Mult. Init 1.0. |
| 0x13C | `float` | `DamageToArmorDurabilityDropoffAOE` | AOE dropoff. Not traced further. |

### Key methods

| Method | VA | Notes |
|---|---|---|
| `GetDamageToArmorDurability()` | 0x1806285B0 | Returns `DamageToArmorDurability * max(0, DamageToArmorDurabilityMult)` |
| `GetDamageToArmorDurabilityDropoff()` | 0x180628580 | Returns `DamageToArmorDurabilityDropoff * max(0, DamageToArmorDurabilityDropoffMult)` |
| `GetArmorDurabilityPerElement()` | 0x1806282D0 | Returns `(int)(ArmorDurabilityPerElement * ArmorDurabilityPerElementMult)` (inferred) |
| `UpdateProperty(EntityPropertyType, int)` | 0x180629A50 | Switch on enum value, direct field += amount |
| `UpdateMultProperty(EntityPropertyType, float)` | 0x1806293B0 | Switch on enum value, field += (value - 1.0) via FUN_1805316d0 |
| `NewEmpty()` | 0x1806290F0 | Allocates instance; sets all mults to 1.0 (0x3f800000), all flats to 0 |

### Multiplier accumulation convention

`UpdateMultProperty` calls `FUN_1805316d0` for every mult field:

```c
void FUN_1805316d0(float* field, float value) {
    *field += (value - 1.0f);
}
```

A multiplier of `1.2` (20% increase) adds `0.2` to the stored field. Two `1.2` buffs produce `1.4`, not `1.44`. **Multipliers accumulate additively, not multiplicatively.**

The final clamp in getters uses `FUN_1805316f0`:

```c
float FUN_1805316f0(float value) {
    return value >= 0.0f ? value : 0.0f;
}
```

Multipliers cannot go below zero, preventing negative armor durability damage.

---

## 9. Class Reference: Entity

**Namespace:** `Menace.Tactical`  
**TypeDefIndex:** 2807  
**Base class:** `MonoBehaviour` (abstract)  
**Role:** Abstract base for all tactical entities. Owns the armor durability state and is the final applicator of durability damage.

### Armor-relevant fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x54 | `int` | `m_Hitpoints` | Current hitpoints (entity total). |
| 0x58 | `int` | `m_HitpointsMax` | Max hitpoints. |
| 0x5C | `int` | `m_ArmorDurability` | Current armor durability. Written by OnDamageReceived. |
| 0x60 | `int` | `m_ArmorDurabilityMax` | Max armor durability. Set during entity creation. |

### Key methods

| Method | VA | Notes |
|---|---|---|
| `GetArmorDurability()` | 0x180614B60 | Returns `m_ArmorDurability` |
| `GetArmorDurabilityMax()` | 0x18059C240 | Returns `m_ArmorDurabilityMax` |
| `GetArmorDurabilityPct()` | 0x180614B30 | Returns `m_ArmorDurability / m_ArmorDurabilityMax` |
| `SetArmorDurability(int)` | 0x180618880 | Direct setter |
| `OnDamageReceived(Entity, Skill, DamageInfo, EntityProperties)` | 0x180616EF0 | **Core applicator.** Confirmed location of durability formula. |
| `OnDamageReceived(Entity, Skill, DamageInfo)` | 0x180617B90 | Virtual override; delegates to the four-argument overload. |
| `Create(EntityTemplate, Tile, int, int)` | 0x180613FD0 | Initialises `m_ArmorDurability` and `m_ArmorDurabilityMax` from `ArmorDurabilityPerElement * numElements`. |

### Initialisation

In `Create` (`FUN_180613FD0`):

```c
m_ArmorDurabilityMax = GetArmorDurabilityPerElement() * numElements;  // stored at param_1 + 0xc  (inferred alias)
m_ArmorDurability    = GetArmorDurabilityPerElement() * numElements;  // stored at param_1 + 0x5c
```

Both fields are set to the same value at creation. `m_ArmorDurabilityMax` never changes after this point (confirmed: no other writes observed). `m_ArmorDurability` is decremented by `OnDamageReceived`.

---

## 10. Class Reference: Element

**Namespace:** `Menace.Tactical`  
**TypeDefIndex:** 2763  
**Base class:** `MonoBehaviour`  
**Role:** Represents one element (squaddie or vehicle component) of an entity. Owns per-element hitpoints. Receives `OnHit` after damage has already been applied to the owning `Entity`.

### Key fields (armor-relevant)

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x114 | `int` | `m_Hitpoints` | Current element hitpoints. |
| 0x118 | `int` | `m_HitpointsMax` | Max element hitpoints. |

### Key methods

| Method | VA | Notes |
|---|---|---|
| `OnHit(Entity, DamageInfo, int, Skill)` | 0x1806019A0 | Visual/audio response only. Durability already applied before this fires. |
| `OnDeath(Entity, DamageInfo, int, Skill)` | 0x1805FF650 | Element death visual/audio. |
| `CreateElement(UnitLeaderTemplate, int, int, Vector2)` | 0x180613B20 | Creates element instance; triggers per-element hit resolution loop. |

### Behavioural notes

`OnHit` is a notification, not an applicator. It handles visual effects (damage shader, blood decals, impact position calculations, animation triggers) and audio (gender-specific hit/death sounds). By the time `OnHit` is called, `DamageInfo` has already been fully populated and `m_ArmorDurability` has already been decremented on the owning `Entity`.

---

## 11. Class Reference: DamageInfo

**Namespace:** `Menace.Tactical`  
**TypeDefIndex:** 2638  
**Role:** Struct carrying all resolved values for one hit. Passed through the entire damage pipeline and returned from `OnDamageReceived` with final applied values.

### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x10 | `Tile` | `TargetTile` | Tile the hit was directed at. |
| 0x18 | `FatalityType` | `FatalityType` | Fatality category (normal, dismember, etc.). |
| 0x1C | `DamageVisualizationType` | `DamageVisualizationType` | Visual treatment of the hit. |
| 0x20 | `Vector3` | `ImpactPoint` | World-space point of impact. |
| 0x2C | `int` | `Damage` | Hitpoint damage inflicted. |
| 0x30 | `ArmorDirection` | `ArmorDirection` | Which armor face was hit (front/side/back). |
| 0x34 | `int` | `ArmorPenetration` | Attacker's penetration value for this hit. |
| 0x38 | `int` | `ArmorDamage` | **Armor durability damage.** On entry to `OnDamageReceived`: theoretical value. On exit: actual durability removed. |
| 0x3C | `int` | `ElementsHit` | Number of elements hit. |
| 0x40 | `int` | `DismemberChance` | Chance of dismemberment this hit. |
| 0x44 | `RagdollHitArea` | `DismemberArea` | Body region for dismemberment. |
| 0x48 | `bool` | `IsAoE` | True if area-of-effect hit. |
| 0x49 | `bool` | `IsCrit` | True if critical hit. |
| 0x4A | `bool` | `IsAbleToPenetrate` | Set by penetration check in `OnDamageReceived`. |
| 0x4B | `bool` | `IsDamageInflicted` | True if hitpoint damage was applied. |
| 0x4C | `bool` | `IsElementDestroyed` | True if an element was killed this hit. |
| 0x4D | `bool` | `IsTargetDestroyed` | True if all elements are dead. |
| 0x4E | `bool` | `IsAbleToInflictDefects` | Defect eligibility flag. |
| 0x4F | `bool` | `IsContainerDestroyed` | True if containing entity was also destroyed. |

---

## 12. Ghidra Address Reference

### Fully analysed

| VA | Method | Class | Notes |
|---|---|---|---|
| 0x1806285B0 | `GetDamageToArmorDurability` | `EntityProperties` | Returns `DamageToArmorDurability * max(0, DamageToArmorDurabilityMult)` |
| 0x180628580 | `GetDamageToArmorDurabilityDropoff` | `EntityProperties` | Returns `DamageToArmorDurabilityDropoff * max(0, DamageToArmorDurabilityDropoffMult)` |
| 0x1805316F0 | `(clamp helper)` | internal | `max(0, value)` — multiplier floor clamp |
| 0x1805316D0 | `(mult accumulator)` | internal | `*field += (value - 1.0)` — additive multiplier accumulation |
| 0x180629A50 | `UpdateProperty` | `EntityProperties` | Switch dispatch for flat property updates |
| 0x1806293B0 | `UpdateMultProperty` | `EntityProperties` | Switch dispatch for multiplier property updates |
| 0x1806290F0 | `NewEmpty` | `EntityProperties` | Allocates modifier accumulator with neutral initial values |
| 0x180613FD0 | `Create` (Entity) | `Entity` | Initialises `m_ArmorDurability` and `m_ArmorDurabilityMax` |
| 0x180613B20 | `CreateElement` | `Entity` | Per-element creation and hit resolution loop entry |
| 0x180616EF0 | `OnDamageReceived` (4-arg) | `Entity` | **Core formula.** Final durability decrement. |
| 0x1806019A0 | `OnHit` | `Element` | Visual/audio response only |
| 0x1805FAA90 | `FUN_1805FAA90` | hit pipeline | Hit type routing; delegates to `FUN_180611820` |
| 0x180611820 | `FUN_180611820` | hit pipeline | Hit component assembly loop (slots 1–12) |
| 0x18060C020 | `FUN_18060C020` | hit pipeline | Damage component registration |
| 0x180610D40 | `FUN_180610D40` | hit pipeline | Damage component factory/registry |
| 0x180561C50 | `FUN_180561C50` | attack pipeline | Attack resolution entry (variant 1) |
| 0x180561C67 | `FUN_180561C67` | attack pipeline | Attack resolution entry (variant 2, more XMM saves) |
| 0x180561C72 | `FUN_180561C72` | attack pipeline | Attack resolution entry (variant 3) |
| 0x1806DD290 | `FUN_1806DD290` | hit pipeline | Hit result coordinator; calls `FUN_1806E6490` twice |
| 0x1806E6490 | `FUN_1806E6490` | hit pipeline | Hit chance / accuracy calculator (not durability) |
| 0x1807069C0 | `FUN_1807069C0` | UI | Tooltip/stat display; calls `FUN_1806DD290` for preview |
| 0x180547260 | `FUN_180547260` | UI | Stat panel population; calls `GetArmorDurabilityPerElement` |

### Secondary — not analysed

| VA | Method | Class | Notes |
|---|---|---|---|
| 0x18062D040 | `FUN_18062D040` | hit pipeline | Armor penetration vs durability resolver. Called before DamageInfo assembly. |
| 0x18062D550 | `FUN_18062D550` | hit pipeline | Penetration check. Boolean result used in hit slot gating. |
| 0x180617B90 | `OnDamageReceived` (3-arg virtual) | `Entity` | Virtual dispatch; delegates to 0x180616EF0. |
| 0x1806282D0 | `GetArmorDurabilityPerElement` | `EntityProperties` | Confirmed called in Create and UI; body not decompiled. |
| 0x180618880 | `SetArmorDurability` | `Entity` | Direct setter; body trivial. |

---

## 13. Key Inferences and Design Notes

**Quadratic durability scaling is intentional.** The `(currentDurability / maxDurability)²` term means that fighting a fresh enemy unit is qualitatively different from fighting a damaged one. Anti-armor tactics that degrade durability early have disproportionate payoff for subsequent shots.

**Penetrating hits deal only 15% of the non-penetrating durability formula.** A round that punches through the plate expends most of its energy on the target beyond it — only residual surface damage accrues to the armor. The 0.15 scalar combined with the `penetrationRatio` floor of 0.3 means the minimum penetrating durability damage is `ArmorDamage * 0.15 * D² * 0.30`. Conversely, a shot stopped by the plate transfers all its energy to the armor and uses the full `ArmorDamage * D²` formula with no scalar. Rend Ammo's tradeoff — reducing `ArmorPenetrationMult` while increasing `DamageToArmorDurability` — is therefore self-defeating under this reading: making a weapon more likely to penetrate routes its hits into the 0.15-scalar path, reducing durability damage per hit. Rend Ammo would accelerate durability loss most effectively if it increased `ArmorDamage` without improving penetration, keeping hits on the non-penetrating (full-damage) path.

**Multipliers are additive among themselves.** Two skills each granting `+20%` armor durability damage (AmountMult = 1.2) stack to `+40%`, not `+44%`. This prevents multiplicative stacking exploits but means the formula is `1 + sum(deltas)` not `product(multipliers)`.

**Multipliers are floored at zero.** A sufficiently large negative modifier can reduce the effective multiplier to zero but cannot invert it. Armor durability cannot be healed through this system.

**`DamageInfo.ArmorDamage` is overwritten on exit.** The field enters `OnDamageReceived` holding the theoretical durability damage value; it exits holding the actual durability removed. Downstream consumers (UI, events) see the actual value, not the theoretical one.

**`Armor` UpdateProperty modifies all three faces simultaneously.** Case 4 in `UpdateProperty` increments `Armor`, `ArmorSide`, and `ArmorBack` by the same amount. Skills or effects that modify `Armor` (EntityPropertyType 4) affect all directions equally. Direction-specific armor changes would require a different property type — none appears to exist for that purpose.

**The penetration ratio floor of 0.3 means penetrating hits always deal at least 30% of the penetrating formula.** A hit with zero armor penetration against maximum armor that nonetheless punches through still contributes `ArmorDamage * 0.15 * D² * 0.30` in durability damage. The floor prevents penetrating hits from contributing zero durability wear.

**Rend Ammo is non-functional at runtime.** Runtime verification (see Section 15) confirmed that none of Rend Ammo's three `PropertyChange` entries ever reach `UpdateProperty` or `UpdateMultProperty` during combat. The out-of-range `PropertyType` values (-2, -15, 0) fall through the switch dispatcher to the exception path and write nothing. The skill has no effect on any entity property. The tooltip displays correctly because it reads from a separate display data source that is not subject to the same dispatch logic.

---

## 14. Open Questions

1. ~~**What does Rend Ammo actually modify at runtime?**~~ **RESOLVED — see Section 15.** Rend Ammo modifies nothing at runtime. All three `PropertyChange` entries have out-of-range `PropertyType` values that are silently discarded by the switch dispatcher. The skill is non-functional.

2. **How does `DamageArmorDurability`'s three fields combine into `DamageInfo.ArmorDamage`?** The three fields (`DamageFlatAmount`, `DamagePercentageOfMaxDurability`, `DamagePercentageOfCurrentDurability`) were confirmed as inputs but their assembly point was not decompiled. → Next step: find callers of the `DamageArmorDurability.Create()` result and trace to where ArmorDamage is assembled.

3. **What does `FUN_18062D040` (armor penetration resolver) do?** This function sits between EntityProperties assembly and DamageInfo construction and is called with penetration/armor parameters. It likely determines whether a hit penetrates and sets `DamageInfo.IsAbleToPenetrate`. → Next step: decompile VA `0x18062D040`.

4. **Are there concrete Element subclasses with different `OnHit` behavior?** Infantry and vehicle elements may override `OnHit` with additional durability-related logic (e.g. crew damage when armor is depleted). → Next step: find subclasses of `Element` in dump.cs and check for `OnHit` overrides.

5. **How does `m_ArmorDurabilityMax` relate to penetration thresholds?** The code accesses `param_1 + 0xc` (ArmorDurabilityMax alias in Entity) in the penetration check formula. The relationship `iVar7 * (m_ArmorDurability / max(1, m_ArmorDurabilityMax)) - ArmorPenetration` appears to govern whether a hit penetrates. This formula was not fully traced. → Next step: re-examine the penetration check section of `FUN_180616EF0` with the confirmed field names applied.

---

## 15. Runtime Verification — Rend Ammo Non-Functional

**Status:** Confirmed. Rend Ammo has no effect at runtime.

### Method

A debug plugin was written using the Menace Modpack Loader SDK (`IModpackPlugin` / MelonLoader) and deployed alongside the game. Two patches were applied via Harmony to `EntityProperties.UpdateProperty` and `EntityProperties.UpdateMultProperty`, logging every `(PropertyType, value)` pair dispatched during a session in which a squad equipped with Rend Ammo was loaded into a tactical mission.

```csharp
// Patch targets
// VA: 0x180629A50 — EntityProperties.UpdateProperty(EntityPropertyType _propertyType, int _amount)
// VA: 0x1806293B0 — EntityProperties.UpdateMultProperty(EntityPropertyType _propertyType, float _amountMult)

private static void UpdateProperty_Postfix(
    Il2CppMenace.Tactical.EntityPropertyType _propertyType, int _amount)
{
    _log.Msg($"  UpdateProperty — PropertyType: {_propertyType} ({(int)_propertyType}), Amount: {_amount}");
}

private static void UpdateMultProperty_Postfix(
    Il2CppMenace.Tactical.EntityPropertyType _propertyType, float _amountMult)
{
    _log.Msg($"  UpdateMultProperty — PropertyType: {_propertyType} ({(int)_propertyType}), AmountMult: {_amountMult}");
}
```

The full log of all property updates was captured during squad initialisation and tactical scene load.

### To Reproduce

1. Build the debug plugin against the Menace Modpack Loader SDK targeting MelonLoader v0.7.3.
2. Patch both `UpdateProperty` and `UpdateMultProperty` on `EntityProperties` as above.
3. Equip a squad with Rend Ammo and load into any tactical mission.
4. Collect the MelonLoader log from `UserData/MelonLoader/Latest.log`.
5. Search the log for `PropertyType` values corresponding to the three expected Rend Ammo effects: `DamageToArmorDurability` (58), `DamageToArmorDurabilityMult` (35), and `ArmorPenetrationMult` (23) with a value below 1.0.

### Result

The full session log contained no calls to either method with any of the expected Rend Ammo property types. The only `ArmorPenetrationMult` (23) entries observed were `AmountMult: 1.3`, attributable to a separate unrelated skill on the same squad. No `DamageToArmorDurability` (58) or `DamageToArmorDurabilityMult` (35) entries appeared at any point.

### Conclusion

The `PropertyChange` entries for Rend Ammo carry `PropertyType` values of -2, -15, and 0. Values -2 and -15 are outside the valid enum range (0–71) and are not handled by the switch statements in either `UpdateProperty` or `UpdateMultProperty` — they fall to the default exception path and are discarded. Value 0 maps to `Vision`, which is dispatched but produces a nonsensical result for an ammo type (writing a large negative Vision modifier) and is almost certainly also a data error.

The most probable cause is a data entry error: the `PropertyType` field for all three `PropertyChange` entries was written incorrectly, while the `Amount` and `AmountMult` values may reflect the designer's original intent as described in the tooltip. The tooltip reads from a separate display data source and does not pass through `UpdateProperty` or `UpdateMultProperty`, which is why it continues to display correct-looking values despite the underlying data being broken.
