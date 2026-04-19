# Menace — SDK Inventory Investigation

**Game:** Menace  
**Platform:** Windows x64, Unity IL2CPP  
**Image base:** `0x180000000`  
**Source material:** Il2CppDumper `dump.cs`, class dumps, SDK source (`Inventory.cs`), plugin source (`OCIRebalance.cs`)  
**Investigation status:** Complete

---

## Table of Contents

1. [Investigation Overview](#1-investigation-overview)
2. [Source Material](#2-source-material)
3. [Class Inventory](#3-class-inventory)
4. [Root Cause: Why the SDK Fails in IL2CPP](#4-root-cause-why-the-sdk-fails-in-il2cpp)
5. [Field Offset Verification](#5-field-offset-verification)
6. [Method Signature Mismatches](#6-method-signature-mismatches)
7. [ItemSlot Enum Mismatch](#7-itemslot-enum-mismatch)
8. [Container Access: The Missing Field](#8-container-access-the-missing-field)
9. [The Working Replacement](#9-the-working-replacement)
10. [Key Inferences and Design Notes](#10-key-inferences-and-design-notes)
11. [Open Questions](#11-open-questions)

---

## 1. Investigation Overview

### What was investigated

`Menace.SDK.Inventory` — a third-party SDK wrapper providing access to actor item containers and their contents during tactical missions. The specific entry points under investigation were `Inventory.GetContainer(actor)` and `Inventory.GetAllItems(container)`, used in the plugin `OCIRebalance` to enumerate equipped items on faction 1 actors at the start of a tactical scene.

### What was achieved

- Identified the root architectural failure of the SDK: reflection-based managed type resolution does not function in IL2CPP at runtime.
- Verified all field offsets claimed by the SDK against `dump.cs` class dumps for `ItemContainer`, `Item`, `BaseItem`, `ItemTemplate`, `Entity`, `Actor`, and `StrategyState`.
- Identified every method signature mismatch between what the SDK calls and what the game actually exposes.
- Discovered that `m_ItemContainer` does not exist as a field on `Actor` or `Entity` — the SDK's fallback `ReadPtr("m_ItemContainer")` always returns zero.
- Identified `Entity.GetItems()` as the correct access path, confirmed from the `Entity` dump.
- Confirmed that `ItemSlot` enum values do not match the SDK's named constants.
- Produced a working replacement for `GetContainer` + `GetAllItems` that enumerates all items with correct slot names, verified against live game output (6 actors, 28 items, correct slot assignments).

### What was NOT investigated

- `Inventory.FindByGUID` and its dependency on `OwnedItems.GetItemByGuid` — not needed for the tactical use case.
- `Inventory.GetTradeValue` — correct fix identified (requires `float _tradeValueMult` parameter) but not implemented or tested.
- `Inventory.GetHighestRarity` — confirmed broken (static method misused as instance method); the correct field on `BaseItemTemplate` for per-item rarity was not dumped.
- `Inventory.TransferItem` and `Inventory.RemoveItem` — name mismatch confirmed (`RemoveItem` does not exist; real method is `Remove`), replacement not implemented.
- `Inventory.HasItemWithTag` / `GetItemsWithTag` — confirmed broken (takes `TagType` enum, not `string`), replacement not implemented.
- `Inventory.GetItemTemplates` — uses `Resources.FindObjectsOfTypeAll`; not relevant to tactical use case and not tested.
- All `BaseItemTemplate` fields including rarity — class not dumped.
- All `Structure` subclass implementations of `GetItems()` — only `Actor` subclass confirmed.

---

## 2. Source Material

| Source | Purpose |
|---|---|
| `Menace.SDK.Inventory` source (`Inventory.cs`) | SDK under investigation — 1,285 lines |
| `ItemContainer` dump | Field offsets and method signatures for the container class |
| `Item` dump | Field offsets and method signatures for individual items |
| `BaseItem` dump | Base class fields and method signatures including trade value and rarity |
| `ItemTemplate` dump | Field offsets confirming `SlotType` field location |
| `ItemSlot` enum dump | Enum values for all slot types |
| `Actor` dump | Confirmed absence of `m_ItemContainer` field |
| `Entity` dump | Confirmed presence of `GetItems()` virtual method |
| `StrategyState` field (`OwnedItems`) | Confirmed offset `+0x80` |
| Live log output | Runtime verification of working replacement |

---

## 3. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| `ItemContainer` | `Menace.Items` | 2194 | Holds all items equipped by an entity, organised by slot type in a fixed-size array of lists |
| `Item` | `Menace.Items` | 2191 | A single equipped item instance, referencing its template and container |
| `BaseItem` | `Menace.Items` | 2188 | Base class for all item types; holds GUID, template reference, and trade/rarity utilities |
| `ItemTemplate` | `Menace.Items` | 2207 | Abstract ScriptableObject defining an equippable item's slot, type, skills, and visual data |
| `ItemSlot` | `Menace.Items` | 2183 | Enum of 11 equipment slots plus sentinel values (`None = -1`, `All = 255`) |
| `Entity` | `Menace.Tactical` | 2807 | Abstract base for all tactical entities; exposes `GetItems()` virtual method |
| `Actor` | `Menace.Tactical` | 2711 | Concrete infantry/vehicle entity subclass; overrides `GetItems()` |

---

## 4. Root Cause: Why the SDK Fails in IL2CPP

### The architectural problem

The SDK's entire access pattern relies on resolving managed types at runtime via `System.Reflection`:

```csharp
// From Inventory.cs — EnsureTypesLoaded()
_itemContainerType ??= GameType.Find("Menace.Items.ItemContainer");

// From GetAllItems()
var containerType = _itemContainerType?.ManagedType;
var proxy = GetManagedProxy(container, containerType);
var getAllMethod = containerType.GetMethod("GetAllItems", BindingFlags.Public | BindingFlags.Instance);
var items = getAllMethod?.Invoke(proxy, null);
```

In a Unity IL2CPP build, `Assembly-CSharp` does not exist as a managed DLL at runtime. The original C# assembly has been compiled to native code in `GameAssembly.dll`. `Il2CppInterop` generates thin interop wrapper DLLs (one per original assembly) that allow managed code to call into the native binary, but these wrappers must be referenced at compile time — they cannot be resolved by name at runtime via `AppDomain.CurrentDomain.GetAssemblies()`.

The result is that `GameType.Find(...)` returns null for every type, `GetManagedProxy` returns null, and every method invoked via `GetMethod(...).Invoke(...)` either throws a `NullReferenceException` (caught silently by the SDK's try/catch blocks) or returns null. The SDK's null guards swallow every failure silently, returning empty lists and `GameObj.Null` throughout.

The error in the original log confirms this:

```
[ERROR] [Il2CppInterop] Assembly Assembly-CSharp is not registered in il2cpp
```

This fires once per `GetManagedProxy` call. Six actors, multiple calls each — that is exactly what the log shows.

### Why the SDK's fallback also fails

`GetContainer` has a fallback path:

```csharp
// Fallback: try direct field access via m_ItemContainer
var containerPtr = entity.ReadPtr("m_ItemContainer");
```

This also returns zero for every actor because `m_ItemContainer` does not exist as a field anywhere in the `Actor` or `Entity` class hierarchy. The field name lookup finds nothing. See Section 8 for details.

### The fix

Replace all reflection-based access with direct calls on the Il2CppInterop wrapper types, which are available at compile time and resolve correctly to native calls. No `GetMethod`, no `GetManagedProxy`, no `GameType.Find`.

---

## 5. Field Offset Verification

All offsets claimed in the SDK source comments were verified against `dump.cs`.

### ItemContainer — `Menace.Items.ItemContainer` (TypeDefIndex 2194)

| Offset | Type | Field | SDK claim | Status |
|---|---|---|---|---|
| `+0x10` | `List<Item>[]` | `m_Items` | "SlotLists\[11\] @ +0x10" | ✅ Confirmed |
| `+0x18` | `IEntityProperties` | `m_Owner` | "Owner @ +0x18" | ✅ Confirmed |
| `+0x20` | `ItemsModularVehicle` | `m_ModularVehicle` | "+0x20" | ✅ Confirmed |
| `+0x28` | `GameObject[]` | `m_VisualAlterations` | Not claimed | — |
| `+0x30` | `bool` | `m_VisualAlterationsDirty` | Not claimed | — |
| `+0x38` | event delegate | `OnVisualAlterationChanged` | Not claimed | — |

### Item — `Menace.Items.Item` (TypeDefIndex 2191)

| Offset | Type | Field | SDK claim | Status |
|---|---|---|---|---|
| `+0x28` | `ItemContainer` | `m_Container` | "Item.Container @ +0x28" | ✅ Confirmed |
| `+0x30` | `List<BaseSkill>` | `m_Skills` | "Item.Skills @ +0x30" | ✅ Confirmed |
| `+0x38` | `bool` | `m_IsUsingAlternativeIcon` | Not claimed | — |

Note: The SDK comment "Item.Template @ +0x18" is incorrect in attribution — the template field lives on `BaseItem`, not `Item`. The offset itself is correct on `BaseItem`.

### BaseItem — `Menace.Items.BaseItem` (TypeDefIndex 2188)

| Offset | Type | Field | SDK claim | Status |
|---|---|---|---|---|
| `+0x10` | `string` | `m_Guid` | Not claimed directly | ✅ Confirmed |
| `+0x18` | `BaseItemTemplate` | `m_Template` | "Item.Template @ +0x18" (misattributed) | ✅ Offset correct |
| `+0x20` | `BlackMarketStackType` | `m_BlackMarketStackType` | Not claimed | — |

### ItemTemplate — `Menace.Items.ItemTemplate` (TypeDefIndex 2207)

| Offset | Type | Field | SDK claim | Status |
|---|---|---|---|---|
| `+0xB8` | `Sprite` | `IconEquipment` | Not claimed | — |
| `+0xE8` | `ItemSlot` | `SlotType` | "m_SlotType @ +0xe8" | ✅ Confirmed (field is public, not private; name is `SlotType` not `m_SlotType`) |
| `+0xEC` | `ItemType` | `ItemType` | Not claimed | — |

### StrategyState — `Menace.States.StrategyState`

| Offset | Type | Field | SDK claim | Status |
|---|---|---|---|---|
| `+0x80` | `OwnedItems` | `OwnedItems` | "+0x80 verified via REPL" | ✅ Confirmed. Field is `public readonly`, not a property. |

**Summary:** All SDK offset claims are correct. No memory layout bugs were found. Every bug discovered is a method call or type resolution issue, not a struct layout issue.

---

## 6. Method Signature Mismatches

The following SDK method calls fail at runtime due to wrong method names or wrong argument counts. All were confirmed by comparing `Inventory.cs` invocations against `dump.cs` signatures.

### `ItemContainer` — mismatched method names and signatures

| SDK calls | Real signature | Failure mode |
|---|---|---|
| `containerType.GetMethod("RemoveItem", ...)` | Does not exist. Real method: `Remove(Item _item, bool _fireVisualAlterationChangedEvent = True)` | `GetMethod` returns null; remove always silently fails |
| `Place(item)` — one argument | `Place(Item _item, int _index, bool _fireEvents = True)` — three parameters | Invocation throws `TargetParameterCountException`, caught silently |
| `GetAllItemsAtSlot(int slotType)` | `GetAllItemsAtSlot(ItemSlot _slotType)` — parameter is `ItemSlot` enum, not `int` | Type mismatch; marshalling may fail or produce incorrect results |
| `GetItemAtSlot(int slotType, int index)` — two arguments | `GetItemAtSlot(ItemSlot _slotType)` — one argument, returns single `Item` not indexed | Invocation throws `TargetParameterCountException`, caught silently |

### `BaseItem` — broken method calls

| SDK calls | Real signature | Failure mode |
|---|---|---|
| `GetTradeValue()` — no arguments | `GetTradeValue(float _tradeValueMult)` — one required parameter | `TargetParameterCountException`, caught silently; `TradeValue` always 0 |
| `GetHighestRarity()` — instance call | `static int GetHighestRarity(IReadOnlyCollection<BaseItem> _items)` — static, takes a collection | Called as instance method on a single proxy, always fails; `Rarity` always empty/default |

### `Item` — correct calls

| SDK calls | Real signature | Status |
|---|---|---|
| `GetID()` | `public string GetID()` | ✅ Correct |
| `GetTemplate()` | `public ItemTemplate GetTemplate()` | ✅ Correct |
| `GetSkills()` | `public List<BaseSkill> GetSkills()` | ✅ Correct (SDK reads raw pointer instead, but both work) |

Note: Even the correct `Item` method calls are unreachable in practice because `GetManagedProxy` fails before they are invoked.

---

## 7. ItemSlot Enum Mismatch

The SDK defines 11 named slot constants (`SLOT_WEAPON1 = 0` through `SLOT_VEHICLE_ACCESSORY = 10`) that do not match the `ItemSlot` enum values in the game.

### ItemSlot enum — `Menace.Items.ItemSlot` (TypeDefIndex 2183)

| Value | SDK constant | Real name | Match |
|---|---|---|---|
| `-1` | (not defined) | `None` | — |
| `0` | `SLOT_WEAPON1` | `InfantryWeapon` | Name wrong |
| `1` | `SLOT_WEAPON2` | `InfantrySpecial` | Name wrong |
| `2` | `SLOT_ARMOR` | `InfantryArmor` | Name wrong |
| `3` | `SLOT_ACCESSORY1` | `InfantryAccessory` | Name wrong |
| `4` | `SLOT_ACCESSORY2` | `Vehicle` | Name wrong — SDK implies a second accessory slot; this is the vehicle chassis slot |
| `5` | `SLOT_CONSUMABLE1` | `VehicleAccessory` | Name wrong — SDK implies consumables; this is vehicle accessories |
| `6` | `SLOT_CONSUMABLE2` | `VehicleLightTurret` | Name wrong |
| `7` | `SLOT_GRENADE` | `VehicleHeavyTurret` | Name wrong — SDK implies grenades; this is a heavy turret slot |
| `8` | `SLOT_VEHICLE_WEAPON` | `ModularVehicleLight` | Name wrong |
| `9` | `SLOT_VEHICLE_ARMOR` | `ModularVehicleMedium` | Name wrong |
| `10` | `SLOT_VEHICLE_ACCESSORY` | `ModularVehicleHeavy` | Name wrong |
| `11` | `SLOT_TYPE_COUNT` | `COUNT` | Correct (sentinel, not a real slot) |
| `255` | (not defined) | `All` | — |

The integer values (0–10) are correct. Any SDK code that branches on slot type using the named constants — for example, `if (slotType == SLOT_GRENADE)` to find thrown weapons — would silently operate on `VehicleHeavyTurret` items instead. The game has no dedicated grenade or consumable slots.

---

## 8. Container Access: The Missing Field

The SDK attempts two strategies to get an actor's `ItemContainer`:

**Strategy 1** — `IHasItemContainer` interface:
```csharp
var hasContainerType = GameType.Find("Menace.Items.IHasItemContainer")?.ManagedType;
var proxy = GetManagedProxy(entity, hasContainerType);
var containerProp = hasContainerType.GetProperty("ItemContainer", ...);
```
Fails because `GameType.Find` returns null (IL2CPP registration issue).

**Strategy 2** — Direct field read:
```csharp
var containerPtr = entity.ReadPtr("m_ItemContainer");
```
Returns zero for every actor because `m_ItemContainer` does not exist as a field on `Actor` (TypeDefIndex 2711) or its base class `Entity` (TypeDefIndex 2807). The complete field tables for both classes were verified. Neither contains a field with this name or an `ItemContainer`-typed field at any offset.

### The correct access path

`Entity` exposes a virtual method at vtable slot 44:

```csharp
// Entity — Slot: 44
public virtual ItemContainer GetItems() { }
```

This is the intended access path. `Actor` overrides it to return the actor's item container. The method is accessible directly on the Il2CppInterop wrapper without any reflection.

The SDK author appears to have searched for a stored field reference and assumed `m_ItemContainer` existed by analogy with similar Unity game patterns, without verifying against the dump.

---

## 9. The Working Replacement

The following replaces `Inventory.GetContainer(actor)` + `Inventory.GetAllItems(container)` in full. It uses no reflection, no `GameType.Find`, and no raw pointer reads.

### `GetActorItems`

```csharp
private static List<(string SlotName, string TemplateName)> GetActorItems(GameObj actor)
{
    var result = new List<(string, string)>();
    try
    {
        var container = new Actor(actor.Pointer).GetItems();
        if (container == null) return result;

        var items = container.GetAllItems();
        if (items == null) return result;

        foreach (var item in items)
        {
            var template = item?.GetTemplate();
            if (template == null) continue;
            result.Add((GetSlotTypeName((int)template.SlotType), template.name));
        }
    }
    catch (Exception ex)
    {
        _log.Error($"GetActorItems failed: {ex.Message}");
    }
    return result;
}
```

### `GetSlotTypeName`

```csharp
private static string GetSlotTypeName(int slotType) => slotType switch
{
    -1  => "None",
    0   => "InfantryWeapon",
    1   => "InfantrySpecial",
    2   => "InfantryArmor",
    3   => "InfantryAccessory",
    4   => "Vehicle",
    5   => "VehicleAccessory",
    6   => "VehicleLightTurret",
    7   => "VehicleHeavyTurret",
    8   => "ModularVehicleLight",
    9   => "ModularVehicleMedium",
    10  => "ModularVehicleHeavy",
    255 => "All",
    _   => $"Unknown({slotType})"
};
```

### Verified runtime output

Tested against a tactical scene with 6 faction 1 actors (2 infantry, 1 infantry with launcher, 3 vehicles). All 28 items enumerated correctly across 46ms. Slot names match game data. No errors.

```
[InfantryWeapon] weapon.generic_battle_rifle_tier1_crowbar_sup
[InfantrySpecial] specialweapon.medium_machinegun_tier2_m80
[InfantryArmor] armor.player_jaeger_fatigues
[InfantryAccessory] accessory.ammo_match_ammo
[InfantryAccessory] accessory.ammo_bag
[Vehicle] vehicle.chassis_carrier
[VehicleAccessory] accessory.vehicle_ammo_cases
[ModularVehicleLight] mod_weapon.light.plasma_rifle
[ModularVehicleHeavy] mod_weapon.heavy.cannon_long
...
```

---

## 10. Key Inferences and Design Notes

**The SDK was written for a Mono build, not IL2CPP.** The reflection-based approach (`GetMethod`, `GetManagedProxy`, `AppDomain.CurrentDomain.GetAssemblies()`) is a standard pattern for runtime interop in Unity Mono games. It does not work in IL2CPP. The SDK either predates the game's switch to IL2CPP or was written targeting a different build configuration.

**All offset comments in the SDK are accurate.** Despite the code being non-functional, whoever wrote the SDK correctly reverse-engineered the memory layout. The offsets for `ItemContainer`, `Item`, `BaseItem`, and `StrategyState` are all verified correct. The only error is the attribution comment "Item.Template @ +0x18" — the field is on `BaseItem`, not `Item`, though the offset is correct on the right class.

**`ItemContainer.m_Items` is a fixed-length array of 11 lists, not a dictionary.** Slot access is `m_Items[slotIndex]` — a direct array dereference. This is consistent with `SLOT_TYPE_COUNT = 11` and `COUNT = 11`.

**`Entity.GetItems()` defaults to returning null.** The base class implementation at RVA `0x519A90` is a no-op stub (same RVA shared with `GetSkills()` and several other virtual methods that return null by default). Only concrete subclasses that carry items override it. A null check after `GetItems()` is mandatory.

**`StrategyState.OwnedItems` is a public readonly field, not a property.** The SDK's comment says "verified via REPL" and uses `ReadPtr(0x80)` directly. This is correct. Any attempt to call a `get_OwnedItems()` method would fail — no such method exists.

**`GetHighestRarity` is a utility for comparing collections, not a per-item accessor.** Its signature `static int GetHighestRarity(IReadOnlyCollection<BaseItem> _items)` makes clear it is meant for comparing groups of items (e.g. finding the rarity of the best item in a loot drop). There is no equivalent instance method. Per-item rarity lives on `BaseItemTemplate`, which was not dumped in this investigation.

**`ItemSlot.None = -1` and `ItemSlot.All = 255` are sentinels.** If either appears in live enumeration output from `GetAllItems()`, it indicates a data integrity issue — an item with no assigned slot or an item that was incorrectly configured to occupy all slots simultaneously.

---

## 11. Open Questions

**1. What field on `BaseItemTemplate` holds per-item rarity?**  
Matters for: correctly implementing `ItemInfo.Rarity`.  
Next step: Dump `BaseItemTemplate` (TypeDefIndex unknown — search `dump.cs` for `class BaseItemTemplate`). Look for a field of type `int`, `RarityType`, or similar around offset `+0xA0`–`+0xB0` (before the `IconEquipment` sprite at `+0xB8` on `ItemTemplate`).

**2. What is the correct method name and signature to remove an item from a container?**  
Matters for: implementing `RemoveItem`, `TransferItem`, `ClearInventory`.  
Answer is already known from the dump: `Remove(Item _item, bool _fireVisualAlterationChangedEvent = True)`. Needs to be tested.

**3. What is the correct call to add an item to a container?**  
Matters for: implementing `TransferItem`.  
Answer is already known from the dump: `Place(Item _item, int _index, bool _fireEvents = True)`. The `_index` parameter semantics are unknown — whether it is a slot index, a list-within-slot index, or something else. Needs Ghidra analysis of `Place` at VA `0x1805592D0` to confirm.

**4. Does `Structure` override `Entity.GetItems()`?**  
Matters for: using `GetActorItems` on non-actor entities (crates, buildings).  
Next step: Dump `Structure` and check for a `GetItems()` override.

**5. What is the `TagType` enum?**  
Matters for: implementing `HasItemWithTag` and `GetItemsWithTag` correctly.  
Next step: Search `dump.cs` for `public enum TagType` and enumerate its values. The SDK passes raw strings; the real method takes a `TagType` enum value.
