# Menace — OCIRebalance: GetInstalledUpgrades Investigation

**Game:** Menace (Overhype Studios)
**Platform:** Windows x64, Unity IL2CPP, MelonLoader v0.7.3
**Binary:** Menace.exe, Unity 6000.0.63f1, game version v0.6.13+17453
**Source material:** `OCI.cs` (SDK source), `OCIRebalance.cs` (plugin source), `ShipUpgrades` dump, `ShipUpgradeTemplate` dump, `StrategyState` dump (partial), `Latest.log`
**Investigation status:** Complete

---

## Table of Contents

1. Investigation Overview
2. The Deficiency
3. Class Inventory
4. Implementation — GetInstalledUpgrades
5. Integration — Scene Timing
6. Key Inferences and Design Notes
7. Open Questions

---

## 1. Investigation Overview

The `OCIRebalance` plugin needs to determine which ship upgrades are currently installed on the player's ship. The Menace SDK exposes `OCI.GetInstalledUpgrades()` for this purpose, but the class was not addressable from the plugin SDK at the time of development, requiring a standalone reimplementation.

**What was achieved:**

- The SDK source for `OCI.GetInstalledUpgrades()` was read and its internal call chain fully understood.
- The native `ShipUpgrades`, `ShipUpgradeTemplate`, and `StrategyState` class dumps were obtained and cross-referenced against the SDK implementation, identifying several points where the SDK's assumptions did not match the actual binary.
- A correct, SDK-independent implementation of `GetInstalledUpgrades()` was written using direct Il2Cpp type bindings and confirmed working methods from the dump.
- A reliable scene timing solution was identified and integrated for accessing live game state.

**What was NOT investigated:**

- Upgrade slot logic (`GetSlots`, `GetSlotOverride`, `GetSlotLevel`) — out of scope for this plugin's needs.
- `GetAvailableUpgrades()` — not required.
- `InstallUpgrade()` / `UninstallUpgrade()` — not required.
- `LocalizedLine` resolution for display names — the Unity asset `name` field is sufficient for this plugin's purposes.
- Upgrade types other than those in equipped slots — consumable or temporary upgrade mechanisms were not investigated.

---

## 2. The Deficiency

### 2.1 What the SDK does internally

The SDK's `OCI.GetInstalledUpgrades()` follows this sequence:

1. Calls `GetShipUpgrades()` to retrieve the `ShipUpgrades` component as a raw `GameObj` via reflection on `StrategyState`.
2. Resolves the managed `Type` for `ShipUpgrades` from a private cached wrapper (`_shipUpgradesType`).
3. Wraps the raw pointer with `Il2CppUtils.GetManagedProxy()`.
4. Reflects into `GetPermanentUpgrades()` on the proxy.
5. Iterates the result list, calling `GetUpgradeInfo()` and `GetUpgradeAmount()` per entry.

### 2.2 What the SDK gets wrong

Reading the `ShipUpgrades` dump revealed that **`GetPermanentUpgrades()` does not exist** on the class. The SDK call would silently return null at step 4 and produce an empty list. The correct method for iterating installed upgrades is `ForEachActiveUpgrade(Action<ShipUpgradeTemplate, int>)`, which also provides the stack amount inline — making the separate `GetUpgradeAmount()` call unnecessary.

The SDK's `GetShipUpgrades()` also uses a fragile reflection path with raw pointer offset fallbacks to reach `StrategyState.ShipUpgrades`. The actual dump shows `ShipUpgrades` is a direct `readonly` public field at offset `0xA0` on `StrategyState`, and `StrategyState` exposes a clean static `Get()` method — making the fallback chain unnecessary.

### 2.3 Why the direct port was not straightforward

The plugin had no `using` directives for game namespaces. `ShipUpgradeTemplate` and `StrategyState` are in `Il2CppMenace.Strategy` and `Il2CppMenace.States` respectively. Once those were added, a further mismatch emerged: `Templates.ReadField()` accepts an SDK `GameObj`, not a raw Il2Cpp type. The implementation therefore uses `GetEquippedUpgrade(int slotIdx)` to obtain typed `ShipUpgradeTemplate` instances, then uses the Unity `name` property to look each one back up via `Templates.Find()` to obtain a `GameObj` compatible with `Templates.ReadField()`.

---

## 3. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| `ShipUpgrades` | `Menace.Strategy` | 2568 | Manages all equipped ship upgrades across 10 slots. Implements `ISaveStateProcessor`. |
| `ShipUpgradeTemplate` | `Menace.Strategy` | 2573 | Unity ScriptableObject asset defining a single upgrade's type, cost, and unlock conditions. |
| `StrategyState` | `Menace.States` | 1652 | Top-level strategy layer state. Holds `ShipUpgrades` as a direct field. Singleton via `Get()`. |

---

## 4. Implementation — GetInstalledUpgrades

### 4.1 ShipUpgrades field table (relevant fields)

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x10 | `ShipUpgradeTemplate[]` | `m_EquippedUpgrades` | Flat array of 10 slots. Null entries = empty slot. |
| 0x18 | `ShipUpgradeSlotTemplate[]` | `m_SlotTypes` | Slot type definitions. Not used in this implementation. |
| — | `const int` | `TOTAL_SLOTS` | Value: 10. Used to bound the slot iteration loop. |

### 4.2 ShipUpgrades method table (relevant methods)

| Method | RVA | VA | Notes |
|---|---|---|---|
| `GetEquippedUpgrade(int)` | 0x5C0E60 | 0x1805C0E60 | Returns `ShipUpgradeTemplate` at a given slot index. Returns null for empty slots. |
| `ForEachActiveUpgrade(Action<ShipUpgradeTemplate, int>)` | 0x5C09A0 | 0x1805C09A0 | Iterates all non-null equipped upgrades, providing template and stack amount. Correct replacement for the SDK's non-existent `GetPermanentUpgrades()`. |

### 4.3 ShipUpgradeTemplate field table (relevant fields)

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x80 | `LocalizedLine` | `Name` | Localized display name. Not used — Unity asset `name` is used instead. |
| 0x88 | `LocalizedLine` | `ShortName` | Not used. |
| 0x98 | `ShipUpgradeType` | `UpgradeType` | Enum: 0=Armament, 1=Electronics, 2=Hull, 3=Hidden. SDK offsets confirmed correct. |
| 0xB0 | `int` | `OciPointsCosts` | Cost to install. Note: plural (`Costs`), not `Cost` as the SDK named it. SDK offset confirmed correct. |
| 0xB4 | `ShipUpgradeUnlockType` | `UnlockType` | Enum: 0=Always, 1=Faction, 2=EventOnly. SDK offset confirmed correct. |
| 0xB8 | `StoryFactionType` | `UnlockedByFaction` | Faction requirement when UnlockType=Faction. SDK offset confirmed correct. |

### 4.4 StrategyState field table (relevant fields)

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x0 | `StrategyState` | `s_Singleton` | Static field. Not used — `Get()` is the correct access path. |
| 0xA0 | `ShipUpgrades` | `ShipUpgrades` | Direct public readonly field. Confirmed from dump. |

### 4.5 StrategyState method table (relevant methods)

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Get()` | 0x644EF0 | 0x180644EF0 | Public static. Returns the singleton. Preferred over direct `s_Singleton` field access. |

### 4.6 Final implementation

```csharp
private static List<string> GetInstalledUpgrades()
{
    var result = new List<string>();

    var state = StrategyState.Get();
    if (state == null) return result;

    var shipUpgrades = state.ShipUpgrades;
    if (shipUpgrades == null) return result;

    for (int i = 0; i < ShipUpgrades.TOTAL_SLOTS; i++)
    {
        var equipped = shipUpgrades.GetEquippedUpgrade(i);
        if (equipped == null) continue;

        var templateObj = Templates.Find("ShipUpgradeTemplate", equipped.name);
        if (templateObj == null) continue;

        var name = Templates.ReadField(templateObj, "name")?.ToString() ?? string.Empty;
        result.Add(name);
    }

    return result;
}
```

`equipped.name` is the Unity `UnityEngine.Object.name` property, inherited by all ScriptableObjects. It matches the asset name used as the key in `Templates.Find()`.

---

## 5. Integration — Scene Timing

### 5.1 The problem

`OnSceneLoaded` fires when Unity signals the scene is loaded, but `StrategyState` is not synchronously initialized at that point. `ProcessSaveState` on `StrategyState` is an `IEnumerator` — it runs across multiple frames. `StrategyState.Get()` returns non-null before `ShipUpgrades` is populated, so polling on `Get() != null` or `Get()?.ShipUpgrades != null` is insufficient.

### 5.2 What was tried

| Approach | Result |
|---|---|
| Call at `OnInitialize` | Always null — strategy layer does not exist at startup. |
| Call at `OnSceneLoaded` where `sceneName == "Strategy"` | Fires before state is ready on first load. Works on subsequent transitions (already initialized). |
| `GameState.RunWhen(() => StrategyState.Get() != null)` | Insufficient — `Get()` returns non-null before `ShipUpgrades` is populated. |
| `GameState.RunWhen(() => StrategyState.Get()?.ShipUpgrades != null)` | Insufficient — `ShipUpgrades` object exists before its save state is processed. |
| `GameState.RunWhen(() => GetEquippedUpgrade(0) != null)` | Rejected — slot 0 may legitimately be empty, producing a silent failure 100% of the time on those saves. |
| `GameState.RunDelayed(60, ...)` | Works. Pragmatic but relies on a magic frame count. |
| `OnSceneLoaded` where `sceneName == "MissionPreparation"` | **Correct solution.** See 5.3. |

### 5.3 The correct solution

The log shows that `LoadScene('MissionPreparation')` is called by the game as part of the strategy layer's own initialization sequence — immediately after the strategy state is fully ready. Critically, the scene never actually switches: the active scene remains `'Strategy'`. This call is therefore a reliable proxy signal for strategy state readiness, with no timing dependency on frame count or polling.

```csharp
public void OnSceneLoaded(int buildIndex, string sceneName)
{
    if (!GameState.IsScene("MissionPreparation")) return;

    var installed = GetInstalledUpgrades();
    foreach (var name in installed)
    {
        _log.Msg(name);
    }
}
```

This fires exactly once per strategy session load, at the correct moment, with no magic numbers.

---

## 6. Key Inferences and Design Notes

**`GetPermanentUpgrades()` was likely a planned or removed method.** The SDK was written against an earlier version of the game or an anticipated API. The actual runtime class uses `ForEachActiveUpgrade` as the primary iteration mechanism, which is a callback pattern rather than a list-returning one. This is consistent with the game wanting to avoid heap allocation for common queries.

**`Templates.ReadField()` requires an SDK `GameObj`, not a raw Il2Cpp type.** The SDK layer and the Il2Cpp interop layer are not interchangeable. Whenever crossing from a typed Il2Cpp object back into SDK utilities, the object must be re-fetched via `Templates.Find()`. This is a consistent pattern across the codebase (confirmed by the `_shepherdPerk = Templates.Find(...).As<PerkTemplate>()` pattern seen elsewhere).

**`StrategyState.s_Singleton` should not be accessed directly.** The SDK routes through `Get()` for a reason — likely because the static field storage block is accessed differently across IL2CPP interop boundaries than a managed static property would be. `Get()` is the safe and confirmed path.

**`MissionPreparation` scene call as a readiness signal is undocumented but reliable.** It appears consistently in the log at the correct point in initialization. However, it is an implementation detail of the game's scene management and could change in a future update. If it stops working, `GameState.RunDelayed` with a conservative frame count is the fallback.

**Field name discrepancy: `OciPointsCosts` vs `OciPointsCost`.** The SDK's `UpgradeInfo` class names this field `OciPointsCost` (singular). The actual `ShipUpgradeTemplate` field is `OciPointsCosts` (plural). Both refer to the same offset `0xB0`. Any code reading this value directly from the template should use the dump-confirmed name.

---

## 7. Open Questions

1. **Does `ForEachActiveUpgrade` correctly handle stackable upgrades?**
The `int` parameter passed to the action is assumed to be a stack count. This was not verified against a save with stacked upgrades. If the plugin later needs to act on amount, this should be confirmed by logging the value against a known save state.
Next step: test with a save that has multiple copies of the same upgrade equipped.

2. **Will the `MissionPreparation` scene signal remain stable across game updates?**
It is an undocumented initialization side effect. If a future update changes the strategy scene loading sequence, this will silently stop firing.
Next step: monitor across game version updates; add a fallback log if `GetInstalledUpgrades()` is never called after entering Strategy.

3. **What is the correct delegate type for `ForEachActiveUpgrade` if called directly?**
The implementation avoids `ForEachActiveUpgrade` in favour of the slot iteration approach. If a future requirement needs the callback path (e.g. to get stack counts), the correct `Action<ShipUpgradeTemplate, int>` delegate construction for Il2CppInterop needs to be confirmed — the naive lambda cast failed during this investigation.
Next step: check how other plugins construct Il2Cpp-compatible delegates, or use `new Action<ShipUpgradeTemplate, int>(...)` with explicit typing.
