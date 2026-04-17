# Investigation Handoff — Menace OffMapAbility Use Modification — Stage 1 → Stage 2

## Directive
Read Research-AI.md in full before proceeding.

## Investigation Target
- **Game:** Menace (Windows x64, Unity IL2CPP)
- **Image base:** 0x180000000
- **System under investigation:** OffMapAbility runtime use count modification
- **Investigation status:** In Progress — feasibility via managed patching ruled out; native approach required
- **Stage:** 2 of ~2
- **VAs complete across all stages:** 0 (Stage 1 was managed-only; no Ghidra work performed)

## Extraction Report
Not yet run. Priority targets for extraction are listed in the Next Priority Table below.

---

## Stage Artefacts on Disk

---

## Resolved Symbol Maps

### FUN_ → Method Name
None resolved — no Ghidra analysis performed in Stage 1.

### DAT_ → Class / Static Field
None resolved.

---

## Field Offset Tables

### Skill (Il2CppMenace.Tactical.Skills)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| unknown | UsageId | int | confirmed — always 0 for offmap abilities, not a usable discriminator |
| unknown | (uses field) | int | confirmed — written by SetUses(), read by GetUses(), never read by game |

### SkillTemplate (Il2CppMenace.Tactical.Skills)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| unknown | Uses | int | confirmed — static default; writable; not read by game at runtime |
| unknown | IsLimitedUses | bool | confirmed — True for offmap abilities |

### OffmapAbilityAction (Il2CppMenace.States)
| Offset | Field Name | Type | Status |
|---|---|---|---|
| native | (use counter) | int (inferred) | NOT YET FOUND — lives at native offset from pooledPtr |

---

## VAs Analysed — All Stages

| Stage | VA | Method | Status |
|---|---|---|---|
| 1 | — | OffmapAbilityAction.UseOrSchedule | Patched managed-side only; no Ghidra decompilation |
| 1 | — | TacticalState.OnRoundStart | Patched managed-side only; no Ghidra decompilation |

---

## Open Questions

[ ] What is the native field offset of the use counter in OffmapAbilityAction? → Run extract_rvas.py on Il2CppMenace.States namespace; find OffmapAbilityAction TypeDefIndex; extract class; get UseOrSchedule RVA; decompile in Ghidra and locate int field being decremented.
[ ] Does OffmapAbilityAction have a native use-reset or use-add method not in the managed wrapper? → Search dump.cs for OffmapAbilityAction method list (not via reflection — that only shows managed wrapper methods). Look for AddUse, RefreshUse, ResetCooldown, SetRemainingUses.
[ ] What does SkillUsesDisplayTemplate do? → Find in dump.cs; examine fields. May drive UI pip rendering independently of the native counter.
[ ] Does TacticalState hold a collection of offmap ability owners with managed wrappers? → Extract TacticalState from dump.cs and inspect fields for any offmap-ability-typed collections.

---

## Scope Boundaries

- Concrete subclasses of OffmapAbilityAction — deferred; base class investigation first
- SkillUsesDisplayTemplate — deferred; low priority until native counter is located
- Criterion subclasses / skill effect implementations — out of scope

---

## Key Prior Findings (do not re-derive)

- `Skill.GetUses()` and `Skill.GetMaxUses()` always return 0 for offmap abilities. `Skill.SetUses(n)` round-trips correctly but is never read by the game. Both are dead storage for this ability type.
- `SkillTemplate.Uses` holds the correct static default (1 or 2) and is writable, but writing to it has no effect on the UI or fire gate.
- `OffmapAbilityAction` managed wrapper is a pure IL2CPP shell. Only `pooledPtr` (native object address) and `myGcHandle` are real fields. All state is at native offsets from `pooledPtr`.
- The call stack above `UseOrSchedule` crosses the IL2CPP native boundary in 3 frames. There is no accessible managed owner object.
- Object-identity registry key (`RuntimeHelpers.GetHashCode(skill)`) is confirmed correct. `UsageId` is always 0 and cannot disambiguate multiple installations.
- Two `supply_drop` firings produced distinct `Skill` object hashes — multiple instances per ability type are confirmed.
- `OffmapAbilityTemplate.m_ID` uses format `offmap_ability.X`; `Skill.GetID()` uses format `offmap.deploy_X`. These are different namespaces.

---

## Next Priority Table

Run extract_rvas.py on `Il2CppMenace.States` first to get OffmapAbilityAction field offsets and method RVAs before opening Ghidra.

| Priority | Method | VA | Rationale |
|---|---|---|---|
| 1 | OffmapAbilityAction.UseOrSchedule | TBD from dump.cs | Core entry point; will show which native field is decremented on use |
| 2 | OffmapAbilityAction (constructor or Init) | TBD | Will show use counter field being set from template value at creation time |
| 3 | TacticalState fields (dump only, no Ghidra) | — | Check for offmap ability owner collections accessible from OnRoundStart |
| 4 | Any OffmapAbilityAction method matching Add/Refresh/Reset + Use/Cooldown | TBD | May be a managed-invocable reset method |

## Instructions for This Session

1. Read Research-AI.md in full.
2. Review the field tables and prior findings above — treat them as confirmed. Do not re-probe SetUses, GetUses, SkillTemplate.Uses, or the call stack.
3. Run extract_rvas.py on Il2CppMenace.States to get OffmapAbilityAction layout before requesting any Ghidra output.
4. The primary goal is: locate the native field offset of the use counter and determine whether a managed-side write (via unsafe pointer arithmetic or il2cpp_runtime_invoke) is viable.
5. Flag any scope expansion immediately before pursuing it.
6. When this stage is complete, invoke the research-handoff skill for final collation (this is the last expected stage).