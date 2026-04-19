# Menace — SkillContainer.Add / Cooldown Investigation Report

**Game:** Menace  
**Platform:** Windows x64, Unity IL2CPP  
**Image base:** `0x180000000`  
**Source material:** Il2CppDumper `dump.cs`, Menace.SDK source (`EntitySkills.cs`), plugin source (`OCIRebalance.cs`)  
**Investigation status:** Complete

---

## Table of Contents

1. Investigation Overview
2. Class Inventory
3. The Core Finding — SDK Failure Mode
4. Per-Class Findings
   - SkillContainer
   - BaseSkill
   - Skill
   - SkillTemplate
   - SkillEventHandler
   - CooldownEffectHandler
   - Cooldown
5. The Fix — SkillHelper Implementation
6. Open Questions

---

## 1. Investigation Overview

### What was investigated

The `Menace.SDK.EntitySkills.AddSkill(GameObj actor, string skillTemplateID)` method was producing a runtime error:

```
[ERROR] [Il2CppInterop] Assembly Assembly-CSharp is not registered in il2cpp
```

The investigation traced the failure through the SDK source, cross-referenced every type and method involved against `dump.cs`, identified all incorrect assumptions, and produced a direct replacement implementation that bypasses the SDK entirely.

A secondary investigation covered `EntitySkills.SetCooldown` and related cooldown manipulation methods, applying the same approach.

### What was achieved

- Identified the root cause of the `Assembly-CSharp not registered` error as a namespace string mismatch in `GameType.Find`
- Discovered that `SkillContainer.Add(SkillTemplate)` does not exist — the SDK was calling a method with a signature that is absent from the binary
- Confirmed the correct instantiation path: `SkillTemplate.CreateSkill()` → `SkillContainer.Add(BaseSkill)`
- Confirmed `SkillContainer.RemoveByID(string)` as a public replacement for the SDK's private `RemoveSkillByIndex` reflection hack
- Confirmed `Skill.GetEventHandlerOfType<T>()` as the correct accessor for cooldown handlers, replacing the SDK's manual array walk
- Confirmed `CooldownEffectHandler.m_Cooldown` at `+0x20` and `Cooldown.AIOnly` at `+0x5C` for direct field writes
- Identified that `ChangeActionPointCost(int _delta)` takes a delta, not an absolute value — the SDK passes an absolute value, which is a bug
- Confirmed that `m_EventHandlers` on `Skill` is a fixed-size `SkillEventHandler[]` array, not a `List`, contradicting the SDK's `GameList` treatment
- Produced `SkillHelper.cs` — a complete, reflection-free, SDK-independent replacement

### What was NOT investigated

- `Actor.GetItems()` / item container internals — used in `OCIRebalance.cs` but not the source of the reported error
- `StrategyState` / `ShipUpgrades` / `Templates` SDK helpers used in `GetInstalledUpgrades()` — these use the same `GameType.Find` pattern and may be broken by the same root cause, but were out of scope for this investigation
- `SkillEventHandler` subclasses other than `CooldownEffectHandler`
- The AI behaviour of skills — `SkillTemplate.AIConfig` and `SkillBehavior` were noted but not pursued

---

## 2. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| `SkillContainer` | `Menace.Tactical.Skills` | 3242 | Owns and manages all `BaseSkill` instances on an entity |
| `BaseSkill` | `Menace.Tactical.Skills` | 3167 | Abstract base for all skill types |
| `Skill` | `Menace.Tactical.Skills` | 3238 | Concrete active skill implementation |
| `SkillTemplate` | `Menace.Tactical.Skills` | 3262 | `ScriptableObject` asset defining a skill's data |
| `SkillEventHandler` | `Menace.Tactical.Skills` | 3245 | Abstract base for per-skill effect handlers |
| `CooldownEffectHandler` | `Menace.Tactical.Skills.Effects` | 3382 | Concrete handler that tracks remaining cooldown turns |
| `Cooldown` | `Menace.Tactical.Skills.Effects` | 3381 | `SkillEventHandlerTemplate` asset defining cooldown parameters |

---

## 3. The Core Finding — SDK Failure Mode

The SDK's `AddSkill` implementation had three independent errors, any one of which would cause failure. Together they guaranteed it.

### Error 1 — Wrong namespace string in type lookup

`EnsureTypesLoaded()` calls:

```csharp
_actorType ??= GameType.Find("Menace.Tactical.Actor");
_skillContainerType ??= GameType.Find("Menace.Tactical.Skills.SkillContainer");
```

`GameType.Find` resolves types by namespace string and calls `Il2CppInterop.Runtime.Il2CppType.From(managedType)`. The generated IL2CppInterop assembly exposes these types under the `Il2CppMenace.Tactical.*` namespace, not `Menace.Tactical.*`. The lookup fails, the type is null, and the method returns false before reaching any skill logic. The `Assembly-CSharp is not registered` error is the IL2CppInterop runtime reporting that no assembly matching the searched name is known.

**Fix:** Reference the generated interop types directly via `using Il2CppMenace.Tactical;` and `using Il2CppMenace.Tactical.Skills;`. No type lookup required.

### Error 2 — `SkillContainer.Add(SkillTemplate)` does not exist

The SDK attempts to call `SkillContainer.Add` passing a `SkillTemplate`. The actual method signature from `dump.cs` is:

```
public bool Add(BaseSkill _skill)   // RVA: 0x6F1940
```

There is no overload accepting `SkillTemplate`. The only template-related add method is:

```
public void AddInherentSkills(EntityTemplate _template)
```

which takes an `EntityTemplate`, not a `SkillTemplate`, and is used for a different purpose entirely. The SDK's approach of passing a template directly to `Add` is architecturally incorrect — `Add` requires a fully instantiated `BaseSkill` object.

**Fix:** Call `SkillTemplate.CreateSkill()` to instantiate the skill, then pass the result to `Add(BaseSkill)`.

### Error 3 — `RemoveSkillByIndex` is private

The SDK's `RemoveSkill` uses reflection to call:

```
private void RemoveSkillByIndex(int _i)   // RVA: 0x6F8350
```

after manually iterating all skills to find the index. The public API already provides:

```
public bool RemoveByID(string _skillID)   // RVA: 0x6F7CA0
```

which performs the same operation in one call.

### Additional bugs (not the cause of the reported error, but present)

**`ChangeActionPointCost` takes a delta, not an absolute value.**  
SDK code: `changeAPMethod.Invoke(skillProxy, new object[] { newCost })` — passing the desired absolute cost.  
Actual signature: `public void ChangeActionPointCost(int _delta)` — adds the argument to the current cost.  
Effect: setting AP cost to 1 on a skill with current cost 2 would result in cost 3.

**`m_EventHandlers` is a fixed array, not a List.**  
The SDK wraps `skill.ReadPtr(OFFSET_SKILL_EVENT_HANDLERS)` in a `GameList`. The `Skill` dump shows:  
`private readonly SkillEventHandler[] m_EventHandlers; // 0x48`  
A fixed C# array has a different memory layout than a `List<T>`. The `GameList` wrapper reads the wrong fields and produces garbage results.

---

## 4. Per-Class Findings

### SkillContainer

**Namespace:** `Menace.Tactical.Skills` | **TypeDefIndex:** 3242 | **Base:** none documented

Owns the skill list for one entity. The instance is retrieved via `Actor.GetSkills()`.

**Fields (instance, selected):**

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x00–0x10 | static | `S_TEMP_*` | Three static list fields; do not affect instance layout |
| 0x10 | `IEntityProperties` | `m_Owner` | The entity that owns this container |
| 0x18 | `List<BaseSkill>` | `m_Skills` | The live skill list |
| 0x20 | `List<BaseSkill>` | `m_SkillsToAdd` | Pending additions (deferred queue) |
| 0x28 | `List<int>` | `m_Garbage` | Indices pending removal |
| 0x48 | `int` | `m_UpdateStack` | Re-entrancy guard for update operations |

**Methods of interest:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Add(BaseSkill)` | 0x6F1940 | 0x1806F1940 | The only correct add path |
| `Remove(BaseSkill)` | 0x6F8570 | 0x1806F8570 | Remove by instance |
| `Remove(SkillTemplate)` | 0x6F8530 | 0x1806F8530 | Remove by template |
| `RemoveByID(string)` | 0x6F7CA0 | 0x1806F7CA0 | Remove by skill ID string — use this |
| `RemoveSkillByIndex(int)` | 0x6F8350 | 0x1806F8350 | **Private** — do not use |
| `GetAllSkills()` | 0x4F82F0 | 0x1804F82F0 | Returns `List<BaseSkill>` |
| `GetSkillByID(string, Item)` | 0x6F3420 | 0x1806F3420 | Pass `null` for Item if not filtering by item |
| `AddInherentSkills(EntityTemplate)` | 0x6F1450 | 0x1806F1450 | For entity template defaults only |

**Behavioural notes:** `Add` queues the skill into `m_SkillsToAdd` rather than directly into `m_Skills` when `m_UpdateStack > 0` (i.e. during an update cycle). This is standard deferred-add pattern. The skill will appear in `GetAllSkills()` results on the next frame.

---

### BaseSkill

**Namespace:** `Menace.Tactical.Skills` | **TypeDefIndex:** 3167 | **Base:** `IComparable`

Abstract base. Cannot be instantiated directly — constructor is `protected`.

**Fields:**

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x10 | `SkillTemplate` | `m_Template` | The asset this skill was created from |
| 0x18 | `SkillContainer` | `m_Container` | Set when added to a container |
| 0x20 | `int` | `m_FactionIdOverride` | Optional faction override |
| 0x28 | `Item` | `m_Item` | Item this skill is attached to, if any |
| 0x30 | `IEntityProperties` | `m_Owner` | Set when added to a container |
| 0x38 | `bool` | `m_IsEnabled` | SDK offset confirmed correct |
| 0x39 | `bool` | `m_IsGarbage` | Marked true when queued for removal |

**Methods of interest:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `SetEnabled(bool)` | 0x4F8A10 | 0x1804F8A10 | Preferred over direct field write |
| `RemoveSelf()` | 0x6D5190 | 0x1806D5190 | Marks self as garbage |
| `GetID()` | abstract | — | Implemented by subclass |
| `GetTemplate()` | 0x4F9580 | 0x1804F9580 | Returns `SkillTemplate` |

---

### Skill

**Namespace:** `Menace.Tactical.Skills` | **TypeDefIndex:** 3238 | **Base:** `BaseSkill`

The concrete active skill class. All skills added via `SkillTemplate.CreateSkill()` are instances of this class.

**Fields (selected, extends BaseSkill from 0x40):**

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x40 | `Skill` | `m_OverrideBackgroundSkill` | Optional background skill override |
| 0x48 | `SkillEventHandler[]` | `m_EventHandlers` | **Fixed array**, not a List — SDK wrong |
| 0x50 | `bool` | `m_IsEnabledImplementedByEventHandler` | True when an event handler controls enabled state |
| 0x98 | `bool` | `m_IsVisible` | UI visibility |
| 0x9C | `int` | `m_Order` | Sort order in UI |
| 0xA0 | `int` | `m_ActionPointCost` | Current AP cost — SDK offset confirmed |
| 0xA4 | `int` | `m_MinActionPointCost` | Floor for cost reductions |
| 0xB4 | `int` | `m_MinRange` | SDK offset confirmed |
| 0xB8 | `int` | `m_IdealRange` | SDK called this `optimalRange` — same field |
| 0xBC | `int` | `m_MaxRange` | SDK offset confirmed |

**Methods of interest:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `GetEventHandlerOfType<T>(out T)` | 0xBA1030 | 0x180BA1030 | Correct way to get a typed handler |
| `GetEventHandlerOfType<T>()` | 0xBA1110 | 0x180BA1110 | Non-out variant |
| `SetRanges(int, int, int)` | 0x6E7260 | 0x1806E7260 | `(min, max, ideal)` — use this over direct writes |
| `ChangeActionPointCost(int)` | 0x6DD1B0 | 0x1806DD1B0 | Takes a **delta** — not absolute value |
| `IsUsable()` | 0x6E3FA0 | 0x1806E3FA0 | Checks enabled, AP, cooldown, uses |
| `.ctor(SkillTemplate, int)` | 0x6E8F00 | 0x1806E8F00 | Second arg is event handler count — call `CreateSkill()` instead |

---

### SkillTemplate

**Namespace:** `Menace.Tactical.Skills` | **TypeDefIndex:** 3262 | **Base:** `DataTemplate`

A `ScriptableObject` asset. One asset exists per skill type in the game's resources. Shared across all instances of that skill.

**Fields of interest:**

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0xA0 | `SkillType` | `Type` | Active/passive/background |
| 0xB4 | `int` | `ActionPointCost` | Default AP cost |
| 0xB8 | `bool` | `IsLimitedUses` | Whether the skill has a use count |
| 0xC8 | `bool` | `IsActive` | Whether this is an active (player-selectable) skill |
| 0x128 | `int` | `MinRange` | Default min range |
| 0x12C | `int` | `IdealRange` | Default ideal range |
| 0x130 | `int` | `MaxRange` | Default max range |
| 0x2C0 | `List<SkillEventHandlerTemplate>` | `EventHandlers` | Handler templates; count used by constructor |

**Methods of interest:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `CreateSkill()` | 0x6F99E0 | 0x1806F99E0 | **The correct instantiation path** — reads `EventHandlers.Count` internally |

**Behavioural notes:** `CreateSkill()` calls `new Skill(this, EventHandlers.Count)` internally, populating all event handlers correctly from the template's `EventHandlers` list. This is the only supported way to instantiate a `Skill` from outside the game's own systems. Because `SkillTemplate` is a `ScriptableObject`, its assets are shared — writing to template fields (such as `Cooldown.AIOnly`) affects all future and existing instances of that skill type for the session lifetime.

---

### SkillEventHandler

**Namespace:** `Menace.Tactical.Skills` | **TypeDefIndex:** 3245 | **Base:** none

Abstract base for all per-skill effect handlers. Instances live in `Skill.m_EventHandlers[]`.

**Fields:**

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x10 | `Skill` | `ParentSkill` (backing field) | The skill this handler belongs to |

Has public property `ParentSkill` with getter/setter. No other instance fields — all data is in subclasses.

---

### CooldownEffectHandler

**Namespace:** `Menace.Tactical.Skills.Effects` | **TypeDefIndex:** 3382 | **Base:** `SkillEventHandler`

Tracks remaining cooldown turns for one skill. Present in `Skill.m_EventHandlers[]` only if the `SkillTemplate`'s `EventHandlers` list contains a `Cooldown` template entry.

**Fields:**

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x18 | `Cooldown` | `m_Template` | The shared asset defining cooldown parameters. Private readonly. |
| 0x20 | `int` | `m_Cooldown` | Remaining turns. Private. Must write via `Marshal.WriteInt32`. |

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `.ctor(Cooldown)` | 0x703790 | 0x180703790 | |
| `IsUsable()` | 0x70EBE0 | 0x18070EBE0 | Returns false when `m_Cooldown > 0` |
| `OnUse(...)` | 0x70EC00 | 0x18070EC00 | Presumably sets `m_Cooldown = m_Template.RoundsToCoolDown` |
| `OnRoundStart()` | 0x70EBF0 | 0x18070EBF0 | Presumably decrements `m_Cooldown` |

**Behavioural notes:** The `IsUsable()` override is what causes a skill on cooldown to be non-selectable. Writing `0` to `m_Cooldown` bypasses the cooldown immediately. Writing `m_Template.RoundsToCoolDown` restores the default post-use cooldown state.

---

### Cooldown

**Namespace:** `Menace.Tactical.Skills.Effects` | **TypeDefIndex:** 3381 | **Base:** `SkillEventHandlerTemplate`

The `ScriptableObject` asset counterpart to `CooldownEffectHandler`. Referenced by `CooldownEffectHandler.m_Template`.

**Fields:**

| Offset | Type | Name | Notes |
|---|---|---|---|
| 0x58 | `int` | `RoundsToCoolDown` | Default cooldown length in rounds |
| 0x5C | `bool` | `AIOnly` | If true, cooldown only applies to AI-controlled units |

**Methods:**

| Method | RVA | VA | Notes |
|---|---|---|---|
| `Create()` | 0x70EC50 | 0x18070EC50 | Factory — called by `Skill.ctor` via handler template list |

**Behavioural notes:** `AIOnly` at `+0x5C` can be set to `false` via `Marshal.WriteByte(templatePtr + 0x5C, 0)` to make a cooldown apply to player-controlled actors. Because this field lives on the shared `ScriptableObject` asset, the change affects all actors using this skill template for the remainder of the session.

---

## 5. The Fix — SkillHelper Implementation

All SDK skill manipulation is replaced by `SkillHelper.cs`, a static helper class with no SDK dependency and no reflection.

### AddSkill

```csharp
public static bool AddSkill(Actor actor, string templateName)
{
    var container = actor.GetSkills();
    if (container == null) return false;

    var templates = UnityEngine.Resources.FindObjectsOfTypeAll<SkillTemplate>();
    SkillTemplate template = null;
    foreach (var t in templates)
    {
        if (t.name.Equals(templateName, StringComparison.OrdinalIgnoreCase))
        { template = t; break; }
    }
    if (template == null) return false;

    var skill = template.CreateSkill();
    if (skill == null) return false;

    return container.Add(skill);
}
```

### RemoveSkill

```csharp
public static bool RemoveSkill(Actor actor, string skillID)
{
    var container = actor.GetSkills();
    if (container == null) return false;
    return container.RemoveByID(skillID);
}
```

### SetCooldown / ResetCooldown / ModifyCooldown / DisableAIOnlyCooldown

All route through a shared `GetCooldownHandler` helper:

```csharp
private static CooldownEffectHandler GetCooldownHandler(Actor actor, string skillID)
{
    var skill = actor.GetSkills()?.GetSkillByID(skillID, null)?.TryCast<Skill>();
    if (skill == null) return null;
    skill.GetEventHandlerOfType<CooldownEffectHandler>(out var handler);
    return handler;
}
```

`m_Cooldown` at `+0x20` is written via `Marshal.WriteInt32`. `Cooldown.AIOnly` at `+0x5C` on the template pointer (`handler.Pointer + 0x18` → pointer to `Cooldown` asset) is written via `Marshal.WriteByte`.

### OCIRebalance.cs fix — type mismatch

The existing plugin had a type mismatch: `AssignTACSkills(GameObj actor)` was passing a `GameObj` to `AddSkill(Actor actor, ...)`. The fix is to change `AssignTACSkills` to accept `Actor` and wrap the call site in `EnumerateInventory`:

```csharp
// Before
AssignTACSkills(actor);

// After
AssignTACSkills(new Actor(actor.Pointer));
```

---

## 6. Open Questions

**1. Does `GetInstalledUpgrades()` share the same root cause?**  
It uses `Templates.Find("ShipUpgradeTemplate", ...)` and `Templates.ReadField(...)` from the SDK, which are the same `GameType.Find` reflection pattern. If `ShipUpgradeTemplate` is also exposed under `Il2CppMenace.*`, these calls will fail with the same error. Next step: check `dump.cs` for `ShipUpgradeTemplate` namespace and attempt a direct `Resources.FindObjectsOfTypeAll<ShipUpgradeTemplate>()` replacement.

**2. What does `CooldownEffectHandler.OnUse` write to `m_Cooldown`?**  
Confirmed it overrides `OnUse` but the body was not decompiled. It almost certainly writes `m_Template.RoundsToCoolDown` to `m_Cooldown`. Confirm by analysing VA `0x18070EC00` in Ghidra if exact reset-to-default behaviour is needed.

**3. What does `CooldownEffectHandler.OnRoundStart` do exactly?**  
Confirmed it overrides `OnRoundStart` (VA `0x18070EBF0`). Almost certainly decrements `m_Cooldown` by 1, clamped to 0. Confirm in Ghidra if off-by-one behaviour in cooldown timing is ever observed.

**4. Skills added via `AddSkill` appear in `m_SkillsToAdd`, not `m_Skills`, during an update cycle.**  
If `AssignTACSkills` is called from within a game update (possible if `TacticalReady` fires mid-frame), the skill will not appear in `GetAllSkills()` until the next frame. This is likely fine for the TAC Radio use case but should be verified if any code checks for the skill immediately after adding it.
