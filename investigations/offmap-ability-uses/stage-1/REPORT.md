# Menace — OffMapAbility Runtime Use Modification — Stage 1 REPORT

**Game:** Menace (Windows x64, Unity IL2CPP)
**Image base:** 0x180000000
**Binary type:** IL2CPP (managed wrappers via Il2CppInterop)
**Investigation status:** Complete — feasibility determination reached
**Source material:** Runtime logging via MelonLoader / Harmony patching; dump.cs; no Ghidra decompilation performed

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. Core Finding
5. Full Investigation Pipeline
6. Class Sections
   - OffmapAbilityAction
   - OffmapAbilityTemplate
   - Skill
   - SkillTemplate
7. Feasibility Verdict
8. Key Inferences and Design Notes
9. Open Questions

---

## 1. Investigation Overview

### What was investigated

Whether the remaining-use count for OffMapAbilities (the player's off-map support abilities — e.g. `deploy_auto_laser_sentry_turret`, `supply_drop`) can be modified at runtime via managed Harmony patching, with the goal of implementing a 3-turn cooldown-based use refresh in `TacticalState.OnRoundStart`.

### What was achieved

- Confirmed `TacticalState.OnRoundStart(int _round)` fires correctly and is patchable via `GameState.FindManagedType`.
- Confirmed `OffmapAbilityAction.UseOrSchedule` is patchable and fires on every player ability use.
- Built a stable `Dictionary<int, (Skill, string, SkillTemplate)>` registry populated on first encounter of each ability, keyed by `RuntimeHelpers.GetHashCode(skill)` (object identity) to handle duplicate ability IDs.
- Confirmed `UsageId` is always 0 and is not a usable discriminator for multiple installations of the same ability type.
- Confirmed `Skill.SetUses(int)` / `Skill.GetUses()` round-trip correctly (write → re-read returns written value).
- Confirmed `SkillTemplate.Uses` holds the correct non-zero static default (e.g. `1` for laser turret, `2` for supply drop).
- Confirmed `SkillTemplate.Uses` is writable at runtime.
- Confirmed that neither `Skill.SetUses` nor `SkillTemplate.Uses` writes have any effect on the in-game UI use counter or the ability fire gate.
- Determined that the live use counter is maintained entirely in native (IL2CPP-compiled) memory, inaccessible via managed reflection or the known managed API surface.

### What was NOT investigated

- Raw native memory writes via unsafe pointer arithmetic from `pooledPtr` — requires Ghidra analysis of the native class layout for `OffmapAbilityAction`.
- IL2CPP native method invocation via `IL2CPP.il2cpp_runtime_invoke` for any native use-reset method that may exist on `OffmapAbilityAction`.
- Whether the native owner object above `OffmapAbilityAction` in the call stack (not visible from managed code) exposes a managed-side reset method.
- Concrete subclasses or specialisations of `OffmapAbilityAction`.
- The `SkillUsesDisplayTemplate` field on `SkillTemplate` — its role in driving the UI display was not investigated.

---

## 2. Tooling

No `extract_rvas.py` was used. This investigation was conducted entirely via runtime instrumentation:

- **MelonLoader** — mod loader providing the `IModpackPlugin` entry point.
- **HarmonyLib** — used to postfix-patch `OffmapAbilityAction.UseOrSchedule` and `TacticalState.OnRoundStart`.
- **`GameState.FindManagedType(string)`** — Menace SDK utility that resolves IL2CPP managed types by fully-qualified name at runtime. Used in place of compile-time type references for all patch targets.
- **`System.Reflection`** — used for field/property/method enumeration dumps on `OffmapAbilityAction`, `OffmapAbilityTemplate`, and `SkillTemplate`.
- **`System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode`** — used to produce stable object-identity keys for the skill registry.
- **`System.Diagnostics.StackTrace`** — used to determine the managed call stack above `UseOrSchedule` (confirmed as 3 frames deep, crossing immediately into IL2CPP native).

No issues with tooling were encountered. All patch targets resolved successfully on first attempt.

---

## 3. Class Inventory

| Class | Namespace | Role |
|---|---|---|
| `OffmapAbilityAction` | `Il2CppMenace.States` | Per-use action object; fires when player triggers an off-map ability. Entry point for `UseOrSchedule`. |
| `TacticalAction` | `Il2CppMenace.States` | Base class of `OffmapAbilityAction`. Contributes no relevant managed fields. |
| `OffmapAbilityTemplate` | `Il2CppMenace.OffmapAbilities` | `ScriptableObject` asset defining an off-map ability type. Holds `SkillTemplate` reference, `DelayInRounds`, and `SoundOnUse`. Shared across all installations of a given ability type. |
| `Skill` | `Il2CppMenace.Tactical.Skills` | Per-installation runtime skill instance. Exposes `GetUses()`, `SetUses(int)`, `GetMaxUses()`, `HasLimitedUses()`, `IsOutOfUses()`, `GetID()`, `UsageId`. |
| `SkillTemplate` | `Il2CppMenace.Tactical.Skills` | `ScriptableObject` asset defining a skill type. Holds static defaults including `IsLimitedUses` and `Uses`. Shared across all installations of a given skill type. |

---

## 4. Core Finding

**The managed API surface for OffMapAbility use counts is entirely decoupled from the game's live use tracking.**

The game maintains the actual remaining-use counter for each ability installation in native (IL2CPP-compiled) memory on the `OffmapAbilityAction` object or its native owner. None of the managed methods that appear to read or write use counts (`Skill.GetUses`, `Skill.SetUses`, `Skill.GetMaxUses`, `Skill.IsOutOfUses`, `SkillTemplate.Uses`) have any connection to this native counter at runtime.

Specifically:

- `Skill.GetUses()` returns 0 for all active offmap abilities regardless of their true remaining uses.
- `Skill.GetMaxUses()` returns 0 for all active offmap abilities regardless of their template-defined maximum.
- `Skill.IsOutOfUses()` returns `True` even when the ability has remaining uses and can still fire.
- `Skill.SetUses(n)` writes to a field that round-trips correctly but is never read by the game's gate or UI render path.
- `SkillTemplate.Uses` holds the correct static default (confirmed `1` and `2` for the two observed abilities), is writable, but writing to it produces no observable effect on the UI or fire gate.

The call stack above `UseOrSchedule` is only 3 frames deep before crossing the IL2CPP native boundary. There is no managed owner object accessible above `OffmapAbilityAction`.

---

## 5. Full Investigation Pipeline

```
Hypothesis: OffMapAbility uses can be refreshed via SetUses() or SkillTemplate.Uses writes.

Step 1 — Patch UseOrSchedule (postfix)
  → Log Skill fields: GetUses()=0, GetMaxUses()=0, HasLimitedUses()=True, IsOutOfUses()=True
  → Abilities fire despite IsOutOfUses()=True  [confirmed: gate does not read Skill]

Step 2 — Patch OnRoundStart (postfix)
  → Registry empty on round 1 (abilities not yet fired)
  → Registry populated after first use of each ability
  → SetUses(5) probe: round-trips correctly, but UI unchanged  [Skill field is dead storage]

Step 3 — Reflect OffmapAbilityAction fields/methods
  → Managed wrapper contains only: isWrapped, pooledPtr, m_OffmapAbility (prop), m_Skill (prop)
  → All actual state lives at native offsets from pooledPtr  [IL2CPP shell confirmed]

Step 4 — Reflect OffmapAbilityTemplate fields/methods
  → ScriptableObject asset: SkillTemplate, DelayInRounds, SoundOnUse, m_ID, IsUsable()
  → No per-installation mutable state  [static asset confirmed]

Step 5 — Reflect SkillTemplate fields
  → IsLimitedUses=True, Uses=1 (turret) / Uses=2 (supply drop)
  → Writable, but writes produce no UI or gate effect  [static asset; gate reads native counter]

Step 6 — Walk call stack above UseOrSchedule
  → 3 frames: Plugin.Postfix → DMD<UseOrSchedule> → (il2cpp→managed) bridge
  → No managed owner object accessible  [native ownership confirmed]

RESULT: Managed patching cannot reach the live use counter.
        Native memory access or native method invocation required.
```

---

## 6. Class Sections

### OffmapAbilityAction

**Namespace:** `Il2CppMenace.States`
**Base class:** `TacticalAction` → `Object` → `Il2CppObjectBase`
**Role:** The action object instantiated when a player triggers an off-map ability. `UseOrSchedule` is the method that executes the ability use. The managed wrapper is a thin IL2CPP interop shell; all behavioural state is in native memory.

**Fields (managed reflection — IL2CPP shell only):**

| Offset | Type | Name | Notes |
|---|---|---|---|
| — | `bool` | `isWrapped` | IL2CPP interop flag. Always `False`. |
| — | `IntPtr` | `pooledPtr` | Native pointer to the actual object in unmanaged memory. The real use counter is at an offset from this pointer. |
| — | `IntPtr` | `myGcHandle` | GC handle. IL2CPP bookkeeping. |

**Properties (managed, accessible):**

| Name | Type | Notes |
|---|---|---|
| `m_OffmapAbility` | `OffmapAbilityTemplate` | The ability type definition. `ScriptableObject` asset — static, shared. |
| `m_Skill` | `Skill` | The skill instance associated with this action. |
| `Pointer` | `IntPtr` | Same value as `pooledPtr`. Native object address. |
| `WasCollected` | `bool` | GC collection flag. Always `False` during active combat. |

**Methods (confirmed patchable):**

| Method | Notes |
|---|---|
| `UseOrSchedule` | Fires on each ability use. Patchable via Harmony postfix. `__instance` provides access to `m_OffmapAbility` and `GetSkill()`. |

**Behavioural notes:** The managed call stack above `UseOrSchedule` crosses into the IL2CPP native bridge immediately (confirmed via `StackTrace` — 3 frames). The object that owns and calls `UseOrSchedule` is in native code. `GetSkill()` returns the associated `Skill` instance. Two distinct ability firings of `supply_drop` produced two distinct `Skill` object hashes, confirming separate instances per installation.

---

### OffmapAbilityTemplate

**Namespace:** `Il2CppMenace.OffmapAbilities`
**Base class:** `DataTemplate` → `SerializedScriptableObject` → `ScriptableObject`
**Role:** Static asset defining an off-map ability type. One instance per ability type in the game; shared across all player installations of that ability.

**Properties (confirmed):**

| Name | Type | Value (observed) | Notes |
|---|---|---|---|
| `SkillTemplate` | `SkillTemplate` | — | Reference to the skill definition for this ability. |
| `DelayInRounds` | `int` | `1` | How many rounds before the ability takes effect after scheduling. |
| `SoundOnUse` | `ID` | `(631059796): 866095814` | Audio ID. |
| `m_ID` | `string` | `offmap_ability.auto_laser_sentry_turret` | Internal asset ID. Distinct from `Skill.GetID()` which returns `offmap.deploy_auto_laser_sentry_turret`. |
| `m_IsInitialized` | `bool` | `True` | — |

**Methods (confirmed):**

| Method | Notes |
|---|---|
| `IsUsable()` | Returns `True` during active ability use. Purpose not fully investigated — likely a template-level eligibility check, not a per-installation use gate. |

**Behavioural notes:** This is a `ScriptableObject` asset. It carries no per-installation mutable state. Writing to any of its fields affects all installations of that ability type globally.

---

### Skill

**Namespace:** `Il2CppMenace.Tactical.Skills`
**Role:** Per-installation runtime skill instance. Created from `SkillTemplate` via `SkillTemplate.CreateSkill()` (inferred). Exposes a use-count API that is populated with zeroes for offmap abilities and appears to be dead storage — not read by the game's fire gate or UI.

**Confirmed field/method behaviour:**

| Member | Observed behaviour |
|---|---|
| `GetID()` | Returns the skill's string ID (e.g. `offmap.deploy_auto_laser_sentry_turret`). Reliable. |
| `UsageId` | Always `0` for all observed offmap abilities. Not a usable per-installation discriminator. |
| `GetUses()` | Always returns `0` for active offmap abilities, regardless of true remaining uses. |
| `GetMaxUses()` | Always returns `0` for active offmap abilities. |
| `HasLimitedUses()` | Returns `True` for offmap abilities. |
| `IsOutOfUses()` | Returns `True` even when the ability has remaining uses and fires successfully. |
| `SetUses(int n)` | Writes to an instance field; `GetUses()` subsequently returns `n`. But the game never reads this field — the fire gate and UI are unaffected. |

**Behavioural notes:** `Skill` instances are distinct per installation (confirmed by `RuntimeHelpers.GetHashCode` showing different hashes for separate `supply_drop` installations). Object identity is the correct registry key; `GetID()` alone is insufficient for disambiguation.

---

### SkillTemplate

**Namespace:** `Il2CppMenace.Tactical.Skills`
**Base class:** `DataTemplate` → `SerializedScriptableObject` → `ScriptableObject`
**Role:** Static asset defining a skill type. Holds static defaults for all skill parameters including use counts.

**Confirmed properties:**

| Name | Type | Value (observed) | Notes |
|---|---|---|---|
| `IsLimitedUses` | `bool` | `True` | Confirms uses are limited. |
| `Uses` | `int` | `1` (turret), `2` (supply drop) | Static default. Writable at runtime, but writes have no effect on UI or gate. |
| `IsActive` | `bool` | `True` | — |
| `Type` | `SkillType` | `Active, Offmap` | Flags enum. Confirms offmap classification. |
| `m_ID` | `string` | `offmap.deploy_auto_laser_sentry_turret` | Matches `Skill.GetID()`. |
| `SkillUsesDisplayTemplate` | `SkillUsesDisplayTemplate` | (empty/null observed) | Inferred role: drives UI rendering of use pips. Not investigated. |

**Behavioural notes:** `SkillTemplate` is a `ScriptableObject` asset. Writing `Uses = 1` at round start round-trips correctly (log shows `Uses 2 -> 1`) but the in-game UI counter does not change. The game does not read `SkillTemplate.Uses` at runtime to drive the display or the gate — or it caches the value at load time and never re-queries it.

---

## 7. Feasibility Verdict

**Managed Harmony patching cannot modify OffMapAbility remaining uses.**

The managed API surface (`Skill.SetUses`, `SkillTemplate.Uses`) is entirely disconnected from the native counter the game enforces. No managed field or method that writes to the live use count has been identified.

**Two avenues remain for future investigation:**

1. **Native memory write via `pooledPtr` offset arithmetic.** The `pooledPtr` on `OffmapAbilityAction` is the native object address. If the field offset of the use counter within the native `OffmapAbilityAction` class layout can be determined (via Ghidra analysis of the IL2CPP binary), an `unsafe` pointer write could modify it directly. This requires a separate Ghidra investigation targeting `OffmapAbilityAction` in the compiled binary.

2. **Native method invocation via `IL2CPP.il2cpp_runtime_invoke`.** If the native `OffmapAbilityAction` class exposes a method that resets or adds uses (e.g. `AddUse`, `RefreshUses`, `ResetCooldown`), it may be invocable from managed code using the IL2CPP interop layer even if no managed wrapper exists. This requires identifying the method's native token from `dump.cs` or Ghidra.

---

## 8. Key Inferences and Design Notes

**`Skill` use-count API is vestigial for offmap abilities.** The `GetUses` / `SetUses` / `GetMaxUses` / `IsOutOfUses` API exists on `Skill` and functions correctly for some skill types (inferred from the API's existence), but for offmap abilities the use count is tracked natively and the managed API is never connected to it. This may be a historical artefact of a refactor where offmap abilities were migrated to native-side tracking while the managed API was retained but not updated.

**`IsOutOfUses()` returning `True` while the ability fires is the key diagnostic signal.** This was the first strong evidence that the gate does not go through `Skill` at all. The ability fired twice in sequence with `IsOutOfUses() = True` both times — not once.

**`SkillTemplate` being a `ScriptableObject` means any write is global.** Writing `Uses` on the template affects every installation of that ability type. For a per-player-installation cooldown system this would be acceptable only if the player never has two installations of the same ability simultaneously — which may or may not be true in practice.

**Two `supply_drop` firings in one session produced two distinct `Skill` object hashes.** This confirms multiple skill instances can exist for the same ability ID, validating the object-identity keying strategy for the registry.

**`m_ID` values differ between `OffmapAbilityTemplate` and `SkillTemplate`/`Skill`.** The template uses `offmap_ability.auto_laser_sentry_turret` (underscore-separated prefix) while the skill uses `offmap.deploy_auto_laser_sentry_turret` (verb form with dot separator). Any lookup by ID must use the correct namespace.

---

## 9. Open Questions

1. **What is the native field offset of the use counter within `OffmapAbilityAction`?**
   Why it matters: Required for a direct native memory write approach.
   Next step: Ghidra investigation of `OffmapAbilityAction` in the IL2CPP binary. Start by searching `dump.cs` for `OffmapAbilityAction` to find TypeDefIndex, then extract the class and identify RVAs for `UseOrSchedule` and any use-count-adjacent methods.

2. **Does `OffmapAbilityAction` or its native owner expose a use-reset or use-add native method not surfaced in the managed wrapper?**
   Why it matters: If such a method exists and is invocable via `il2cpp_runtime_invoke`, it is the cleanest solution.
   Next step: Full method dump of `OffmapAbilityAction` from `dump.cs` (not reflection — reflection only shows managed wrapper methods). Search for any method named `AddUse`, `RefreshUse`, `ResetCooldown`, `SetRemainingUses`, or similar.

3. **What is the role of `SkillUsesDisplayTemplate` on `SkillTemplate`?**
   Why it matters: It may be the object that drives the UI pip rendering. If so, writing to it (or to a field it references) might update the display even if the gate lives natively.
   Next step: Find `SkillUsesDisplayTemplate` in `dump.cs` and examine its fields.

4. **Does the native `OffmapAbilityAction` owner (the object that calls `UseOrSchedule`) have a managed wrapper accessible from `TacticalState`?**
   Why it matters: `TacticalState` is already patchable. If it holds a collection of ability owners that have managed wrappers with use-count setters, that is a viable injection point.
   Next step: Examine `TacticalState` fields in `dump.cs` for any collection typed as offmap-ability-related.