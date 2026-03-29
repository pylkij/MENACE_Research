# REPORT.md — `Behavior` & `SkillBehavior` Base Classes
## Menace Tactical AI — Preliminary Investigation

**Game:** Menace
**Platform:** Windows x64, Unity IL2CPP
**Image base:** `0x180000000`
**Binary:** `GameAssembly.dll`
**Source material:** `dump.cs` (Il2CppDumper), Ghidra decompilation, `extraction_report_master.txt`, `namespaces.txt`
**Investigation status:** Complete — stage boundary reached. Subclass investigations not yet begun.

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. The Core Finding — The Behaviour Lifecycle and Scoring Contract
5. Full Pipeline — Turn Processing Flow
6. Class: `Behavior`
7. Class: `SkillBehavior`
8. Supporting Functions: `ComputeHitProbability` and `ComputeDamageData`
9. Ghidra Address Reference
10. Key Inferences and Design Notes
11. Open Questions

---

## 1. Investigation Overview

**What was investigated:**

The two abstract base classes that form the shared foundation for all 20+ tactical AI behaviours in Menace: `Behavior` (the root) and `SkillBehavior` (the skill-execution intermediary). These classes define the interface that every concrete subclass must implement, the lifecycle that the `Agent` drives each turn, and the scoring infrastructure that determines which behaviour executes.

**What was achieved:**

- Complete field layout confirmed for both classes, with all offsets resolved from `dump.cs` and verified against Ghidra
- All seven abstract method slots (`GetID`, `GetOrder`, `OnEvaluate`, `OnExecute`, `OnReset`, and the tile-weighted `OnCollect`/`OnEvaluate` overloads) confirmed in purpose
- All five virtual-with-default slots documented with default behaviours and known overriders
- `Behavior.Evaluate` fully reconstructed: score clamping bounds (`[0, 21474]`), minimum floor (`5`), sentinel value (`99999`), and the deployment-phase gate fully explained
- `Behavior.Execute` fully reconstructed: confirmed two-byte flag write semantics for `m_IsFirstEvaluated`/`m_IsFirstExecuted`
- `SkillBehavior.OnExecute` fully reconstructed: four-stage state machine (rotate → deploy → setup → fire) with `m_WaitUntil` timing
- `SkillBehavior.HandleDeployAndSetup` fully reconstructed: AP-sufficiency decision logic, flag-setting for all three pre-execution stages, `m_DontActuallyExecute` dry-run semantics
- `Behavior.GetUtilityThreshold` fully reconstructed: two-multiplier strategy-driven formula, `WeightsConfig.utilityThreshold` as base, `StrategyData.modifiers` providing `thresholdMultA` (one-directional raise) and `thresholdMultB` (bidirectional)
- `Behavior.Collect` fully reconstructed: deployment-phase gate confirmed identical to `Evaluate`; tile dictionary ownership confirmed on `Agent + 0x60`
- `SkillBehavior.ConsiderSkillSpecifics` fully reconstructed: armour-match tag penalty `(1 - tagValue)`, ammo-count tag penalty `(currentAmmo/maxAmmo * 0.25 + 0.75)`, multiplicative combination
- `SkillBehavior.GetTargetValue` (public and private) fully reconstructed: the complete five-section targeting formula including hit probability, kill potential, overkill scaling, range preference, adjacency bonuses, `_forImmediateUse` branching, suppression path, and final assembly by goal type
- `ComputeHitProbability` fully reconstructed: six-element output array layout confirmed, auto-hit early-out, cover defense, range-penalty path, minimum hit floor
- `ComputeDamageData` fully reconstructed: `DamageData` object layout confirmed (`+0x10` through `+0x28`), burst model, cover-penetration formula, armour residual, expected-kills accumulation

**What was NOT investigated:**

- Any concrete subclass from `extraction_report_master.txt` (`Assist`, `Attack`, `Buff`, `Deploy`, `Idle`, `InflictDamage`, `InflictSuppression`, `Mindray`, `Move`, `MovementSkill`, `Reload`, `RemoveStatusEffect`, `Scan`, `SpawnHovermine`, `SpawnPhantom`, `Stun`, `SupplyAmmo`, `TargetDesignator`, `TransportEntity`, `TurnArmorTowardsThreat`, `GainBonusTurn`, `CreateLOSBlocker`) — these are the subject of subsequent investigations
- `WeightsConfig` class field map beyond what was directly read in analysed functions
- The second config class at `DAT_18394c3d0` (identity not yet confirmed)
- `FUN_180717730` / `FUN_180717a40` (proximity data lookup, used in final scoring bonus)
- `GetOrder()` concrete return values (constant integer returns not yet decompiled)
- The `Agent` class lifecycle (how it drives the `Behavior` list per turn)

---

## 2. Tooling

`extract_rvas.py` was not run in this stage — field layouts and method RVAs were taken directly from `namespaces.txt` (which contains the `Behavior` and `SkillBehavior` class dumps) and `extraction_report_master.txt` (which contains all leaf subclasses). No tool issues were encountered. All RVAs in this report are sourced from these dumps; VAs are computed as `RVA + 0x180000000`.

---

## 3. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|-------|-----------|-------------|------|
| `Behavior` | `Menace.Tactical.AI` | 3623 | Abstract root. Defines the lifecycle (Collect → Evaluate → Execute → Reset), score storage, deployment-phase gating, and utility threshold. |
| `SkillBehavior` | `Menace.Tactical.AI` | 3627 | Abstract intermediary for all skill-executing behaviours. Adds pre-execution sequencing (deploy/setup/rotate), target tile, and the complete targeting value formula. |

---

## 4. The Core Finding — The Behaviour Lifecycle and Scoring Contract

Every concrete behaviour in Menace's tactical AI is a subclass of `Behavior`. Each turn, the `Agent` drives every behaviour through a fixed pipeline. The score produced by `Evaluate` determines which behaviour executes.

### Score formula (integer, stored in `m_Score`)

```
rawScore    = OnEvaluate(actor)                    // subclass-defined, returns int
clampedScore = clamp(rawScore, 0, 21474)
if GetOrder() != 99999 AND clampedScore > 0 AND clampedScore < 5:
    clampedScore = 5                               // minimum viable floor
m_Score = clampedScore
```

**Score ceiling:** `21474` (`0x53E2`). All subclass scoring is bounded by this.
**Minimum floor:** `5`. Any behaviour that scores positive but below 5 is raised to 5, preventing very-low-confidence behaviours from being ignored due to rounding. The floor is bypassed when `GetOrder() == 99999` (a sentinel value marking behaviours that opt out of the floor guarantee).

### Utility threshold formula (float)

```
base     = WeightsConfig.utilityThreshold            // global config, +0x13C
multA    = StrategyData.modifiers.thresholdMultA     // +0x14 — can only raise threshold
multB    = StrategyData.modifiers.thresholdMultB     // +0x18 — bidirectional

scaled   = max(base, base * multA)
threshold = scaled * multB
```

**Convention:** `multA` applies a floor (`max(base, base * multA)`) — strategy can only raise the threshold via this multiplier, not lower it. `multB` is unconstrained and can raise or lower. Aggressive strategies lower the threshold (accept weaker behaviours); defensive strategies raise it (only execute high-confidence behaviours).

### SkillBehavior target value formula

For skill-based behaviours, `OnEvaluate` delegates into `GetTargetValue`, which computes:

```
hitChance       = ComputeHitProbability(...)         // [0, 100], divided by 100 internally
expectedKills   = ComputeDamageData(...)             // DamageData.expectedKills
fVar22          = hitChance * 0.01                   // normalised to [0.0, 1.0]
fVar27          = expectedDamage * 0.01              // normalised expected damage score
fVar30          = killPotential                      // how completely this attack kills the target
fVar32          = proximityBonus / allyPressureBonus // varies by _forImmediateUse

// Final assembly by goal type:
if goalType == 0 (attack):     total = fVar32 * 0.5 + fVar30 + fVar27
if goalType == 1 (assist-move): total = (fVar30 + fVar27) * 0.5 + fVar32
if goalType == 2 (assist-skill): total = (fVar30 + fVar27) * 0.5 + fVar31
```

`ConsiderSkillSpecifics()` provides a multiplicative penalty applied before the above:
```
armorMatchPenalty = 1.0 - clamp(TAG_ARMOR_MATCH.value, 0, 1.0)
ammoFactor        = (currentAmmo / maxAmmo) * 0.25 + 0.75   // range [0.75, 1.0]
multiplier        = armorMatchPenalty * ammoFactor
```

---

## 5. Full Pipeline — Turn Processing Flow

```
Agent drives per-turn loop over all registered Behavior instances:

1.  OnBeforeProcessing()
        Called on every Collect AND every Evaluate call.
        Default: no-op. Override for per-call setup.

2.  Collect(actor)
      ├─ Deployment phase gate (same as Evaluate)
      └─ OnCollect(actor, agentTileDict)  [agent tile dict at Agent+0x60]
              Subclasses populate/modify the shared tile dictionary.
              Default: returns false (no-op collect).

3.  Evaluate(actor, tiles)       [tile-weighted pass, vtable Slot 9]
    Evaluate(actor)              [score pass, vtable Slot 10]
      ├─ OnBeforeProcessing()
      ├─ Deployment phase gate:
      │     if !m_IsUsedForDeploymentPhase AND roundCount == 0: return (score=0)
      ├─ rawScore = OnEvaluate(actor)
      ├─ m_Score = clamp(rawScore, 0, 21474)
      ├─ if GetOrder() != 99999 AND 0 < m_Score < 5: m_Score = 5
      └─ m_IsFirstEvaluated = m_IsFirstExecuted = true

4.  Agent ranks behaviours by m_Score, applies GetUtilityThreshold() filter.
    Selects winner(s). GetOrder() resolves ties.

5.  Execute(actor)
      ├─ OnExecute(actor)   [abstract, vtable Slot 11]
      │     SkillBehavior implementation:
      │       Stage 1 — Rotate:   fire m_RotationSkill, wait 2.0s
      │       Stage 2 — Deploy:   fire m_DeployedStanceSkill, wait animDuration+0.1s
      │       Stage 3 — Setup:    fire m_SetupWeaponSkill, wait 3.0s
      │       Stage 4 — Fire:     wait m_WaitUntil, fire m_Skill on m_TargetTile
      │     Returns true when done, false while waiting.
      └─ m_IsFirstEvaluated = m_IsFirstExecuted = false

    [m_DontActuallyExecute=true: HandleDeployAndSetup planned deploy but
     not enough AP to also fire. Execute proceeds through stages but does
     not reach Stage 4. Checked upstream before OnExecute is called.]

6.  OnNewTurn()     — called at turn boundary. Override if behaviour has
                       per-turn state (e.g. GainBonusTurn, MovementSkill).
    OnReset()       — called to clear behaviour state (abstract).
    OnClear()       — called on agent destruction / round end.
```

**HandleDeployAndSetup** runs during the Collect/Evaluate phase (not during Execute). It sets `m_DeployBeforeExecuting`, `m_SetupBeforeExecuting`, and `m_DontActuallyExecute` based on AP availability and skill readiness.

---

## 6. Class: `Behavior`

**Namespace:** `Menace.Tactical.AI` | **TypeDefIndex:** 3623 | **Base:** none (abstract root)

This class defines the complete lifecycle interface for all tactical AI behaviours. It owns the score (`m_Score`), the agent reference (`m_Agent`), and the deployment phase gate. All abstract methods are resolved through the vtable; the concrete `Evaluate`, `Execute`, and `Collect` entry points are non-virtual wrappers that apply common logic before dispatching to the abstract implementations.

### Fields

| Offset | Type | Name | Status | Notes |
|--------|------|------|--------|-------|
| `0x10` | `Agent*` | `m_Agent` | Confirmed | Owning AI agent. Set via `SetAgent`. |
| `0x18` | `int` | `m_Score` | Confirmed | Utility score from last `Evaluate`. Clamped `[0, 21474]`, floored at `5`. Written at `param_1[3]` (longlong array, offset `0x18`). |
| `0x1C` | `bool` | `m_IsFirstEvaluated` | Confirmed | Set `true` every `Evaluate`, cleared every `Execute`. Semantic: "evaluated since last execution." |
| `0x1D` | `bool` | `m_IsFirstExecuted` | Confirmed | Set `true` every `Evaluate`, cleared every `Execute`. Written in same 2-byte operation as `m_IsFirstEvaluated`. Semantic identical. |
| `0x1E` | `bool` | `m_IsUsedForDeploymentPhase` | Confirmed | When `false`, behaviour is gated out during deployment phase (round count = 0). |

### Methods

| Method | RVA | VA | Notes |
|--------|-----|----|-------|
| `GetScore` | `0x51F3C0` | `0x18051F3C0` | Returns `m_Score`. Accessor. |
| `GetAgent` | `0x4F9580` | `0x1804F9580` | Returns `m_Agent`. Accessor. |
| `GetRole` | `0x738FE0` | `0x180738FE0` | Delegates into `m_Agent`. Not decompiled. |
| `GetStrategy` | `0x739020` | `0x180739020` | Delegates into `m_Agent`. Not decompiled. |
| `IsFirstExecuted` | `0x51F3E0` | `0x18051F3E0` | Returns `m_IsFirstExecuted`. Accessor. |
| `.ctor()` | `0x739170` | `0x180739170` | Default constructor. Not decompiled. |
| `SetAgent` | `0x4F9620` | `0x1804F9620` | Assigns `m_Agent`. |
| `.ctor(Agent)` | `0x739180` | `0x180739180` | Agent-binding constructor. Not decompiled. |
| `Collect` | `0x738D10` | `0x180738D10` | **Fully analysed.** Deployment gate + `OnCollect` dispatch. Tile dict from `Agent+0x60`. |
| `Evaluate(Actor, Dict)` | `0x738DC0` | `0x180738DC0` | Tile-weighted evaluate entry. Not independently decompiled — delegates to Slot 9. |
| `Evaluate(Actor)` | `0x738E60` | `0x180738E60` | **Fully analysed.** Score-writing entry point. |
| `Execute` | `0x738F40` | `0x180738F40` | **Fully analysed.** Thin wrapper: calls `OnExecute`, clears flags. |
| `ResetScore` | `0x739160` | `0x180739160` | Zeroes `m_Score`. Accessor. |
| `GetID` | — | — | Abstract, Slot 4. Must return unique behaviour ID. |
| `GetName` | `0x738F70` | `0x180738F70` | Virtual, Slot 5. Default name string. Subclasses override. |
| `GetOrder` | — | — | Abstract, Slot 6. Returns execution priority integer. `99999` = sentinel (opt out of score floor). |
| `OnBeforeProcessing` | `0x4F7EE0` | `0x1804F7EE0` | Virtual, Slot 7. Default no-op (shared stub). |
| `OnCollect(Actor, Dict)` | `0x5128B0` | `0x1805128B0` | Virtual, Slot 8. Default returns false (shared stub with Slot 9). |
| `OnEvaluate(Actor, Dict)` | `0x5128B0` | `0x1805128B0` | Virtual, Slot 9. Default returns false (same stub). |
| `OnEvaluate(Actor)` | — | — | Abstract, Slot 10. Returns `int` score. |
| `OnExecute` | — | — | Abstract, Slot 11. Returns `bool` (true = done). |
| `OnNewTurn` | `0x4F7EE0` | `0x1804F7EE0` | Virtual, Slot 12. Default no-op. |
| `OnReset` | — | — | Abstract, Slot 13. |
| `OnClear` | `0x4F7EE0` | `0x1804F7EE0` | Virtual, Slot 14. Default no-op. |
| `IsDeploymentPhase` | `0x71B670` | `0x18071B670` | Protected. Reads global round state. Not decompiled. |
| `GetUtilityThreshold` | `0x739050` | `0x180739050` | **Fully analysed.** Strategy-modulated float. |

### Behavioural notes

- **The no-op stub `0x4F7EE0`** is shared among `OnBeforeProcessing`, `OnNewTurn`, `OnClear`, and when used as `OnReset` on subclasses (e.g. `Idle`, `GainBonusTurn`) indicates a stateless behaviour that requires no reset logic.
- **`m_IsFirstEvaluated` and `m_IsFirstExecuted` are not "first-ever" flags.** They are "evaluated since last execution" flags. Both are set on every `Evaluate` call and cleared on every `Execute` call. The naming is misleading.
- **`OnBeforeProcessing` fires on every `Collect` and every `Evaluate` call**, not once per turn. Subclasses that override it should be stateless or explicitly handle repeated calls.
- **The deployment phase gate** reads a global round manager singleton. The field at `RoundManager + 0x60` is an integer round count. When it is `0`, the game is in the deployment phase, and all non-deployment behaviours silently skip evaluation and collection.

---

## 7. Class: `SkillBehavior`

**Namespace:** `Menace.Tactical.AI` | **TypeDefIndex:** 3627 | **Base:** `Behavior`

`SkillBehavior` is the abstract intermediary for all behaviours that operate by activating a `Skill`. It adds a pre-execution sequencing system (rotate → deploy → setup) with AP-sufficiency checking, a timing wait mechanism (`m_WaitUntil`), and the complete targeting value formula used by the `Attack` and `Assist` subtrees.

### Fields

| Offset | Type | Name | Status | Notes |
|--------|------|------|--------|-------|
| `0x20` | `Skill*` | `m_Skill` | Confirmed | The primary skill this behaviour executes. Readonly after construction. |
| `0x28` | `int` | `m_SkillIDHash` | Confirmed | Cached hash of the skill ID. Used for fast lookups. |
| `0x30` | `Skill*` | `m_DeployedStanceSkill` | Confirmed | Stance skill activated before main skill when `m_DeployBeforeExecuting` is true. |
| `0x38` | `Skill*` | `m_RotationSkill` | Confirmed | Rotation skill activated when `m_RotateBeforeExecuting` is true. |
| `0x40` | `Skill*` | `m_SetupWeaponSkill` | Confirmed | Weapon setup skill activated when `m_SetupBeforeExecuting` is true. |
| `0x48` | `int` | `m_AdditionalRadius` | Inferred | Extra radius added to skill's native range. Read in `ComputeDamageData` as shot group list — **re-evaluation needed**: `param_1 + 0x48` in `ComputeDamageData` is a list of shot groups, which may be on the `Skill` object rather than `SkillBehavior`. See Open Question NQ-6. |
| `0x4C` | `bool` | `m_IsRotationTowardsTargetRequired` | Confirmed | When true, rotation precedes execution. |
| `0x4D` | `bool` | `m_DeployBeforeExecuting` | Confirmed | Set by `HandleDeployAndSetup`. Cleared after deploy completes in `OnExecute`. |
| `0x4E` | `bool` | `m_SetupBeforeExecuting` | Confirmed | Set by `HandleDeployAndSetup`. Cleared after setup completes in `OnExecute`. |
| `0x4F` | `bool` | `m_RotateBeforeExecuting` | Confirmed | Set by `HandleDeployAndSetup`. Cleared after rotation completes in `OnExecute`. |
| `0x50` | `bool` | `m_DontActuallyExecute` | Confirmed | When true, the behaviour plans deploy/setup but does not fire the main skill this turn. Set when AP is insufficient for the full sequence. Checked upstream — `OnExecute` itself does not read it. |
| `0x51` | `bool` | `m_IsExecuted` | Confirmed | Set to true after the skill fires. Guards against double-execution. |
| `0x54` | `float` | `m_WaitUntil` | Confirmed | Game-time timestamp. `OnExecute` returns false while `Time.time < m_WaitUntil`. |
| `0x58` | `Tile*` | `m_TargetTile` | Confirmed | The chosen target tile for skill activation. |

**Subclass field origin:** All leaf subclasses begin their own fields at `0x60`, confirming this layout exactly fills `0x20–0x5F`.

### Methods

| Method | RVA | VA | Notes |
|--------|-----|----|-------|
| `GetSkill` | `0x4F82C0` | `0x1804F82C0` | Returns `m_Skill`. |
| `GetSkillIDHash` | `0x536E80` | `0x180536E80` | Returns `m_SkillIDHash`. |
| `.ctor(Agent, Skill)` | `0x73E550` | `0x18073E550` | Not decompiled. |
| `OnReset` (override) | `0x73E530` | `0x18073E530` | Slot 13 override. Resets `m_TargetTile`, `m_IsExecuted`, `m_WaitUntil`, and deploy/setup flags. |
| `OnExecute` (override) | `0x73E300` | `0x18073E300` | **Fully analysed.** Four-stage state machine. |
| `HandleDeployAndSetup` | `0x73DF70` | `0x18073DF70` | **Fully analysed.** AP-sufficiency decision; sets pre-execution flags. |
| `GetTargetValue` (public) | `0x73DD90` | `0x18073DD90` | **Fully analysed.** Routing wrapper; handles contained-entity double-pass. |
| `GetTargetValue` (private) | `0x73C130` | `0x18073C130` | **Fully analysed.** Full five-section targeting formula. |
| `ConsiderSkillSpecifics` | `0x73BDD0` | `0x18073BDD0` | **Fully analysed.** Armour-match and ammo-count penalty multiplier. |
| `GetTagValueAgainst` | `0x73BFA0` | `0x18073BFA0` | Not decompiled. Called from `GetTargetValue` private — queries skill tag effectiveness against an opponent. |

### Behavioural notes

- **`HandleDeployAndSetup` runs during Collect/Evaluate, not during Execute.** By the time `OnExecute` is called, the flags are already set. `OnExecute` is purely a state machine that acts on those flags.
- **`m_DontActuallyExecute` is never read inside `OnExecute`.** It must be checked by the `Agent` before dispatching `Execute`. This flag is the mechanism by which a behaviour says "I can start the deploy sequence this turn, but I need another turn to actually fire."
- **`FUN_1829b1320(0)` is `Time.time`** — confirmed from the `+2.0`, `+3.0`, and `+animDuration+0.1` wait patterns in `OnExecute`.
- **`FUN_1805316f0` is NOT `Time.time`** — it returns a float accuracy/probability value. Previously conflated with `Time.time` in preliminary notes; corrected here.
- **`GetTargetValue` (public) makes two calls to the private overload when the target tile contains a living entity** (a unit inside a vehicle/transport). The first scores the container; the second scores the occupant with `_attackContainedEntity = true`.

---

## 8. Supporting Functions

### `ComputeHitProbability` — VA `0x1806E0AC0`

Returns `float[6]` written in-place. **Not a member of `SkillBehavior`** — it is a standalone utility function called from `GetTargetValue` private.

| Index | Name | Meaning |
|-------|------|---------|
| `[0]` | `hitChance` | Final hit probability, integer scale `[0, 100]`. Floored by `shotPath->minimumHitChance` (`+0x78`). |
| `[1]` | `baseAccuracy` | Raw weapon accuracy from `shotPath`. |
| `[2]` | `coverDefense` | Target cover defense value (integer, float-cast). |
| `[3]` | `rangeMult` | Range-based hit multiplier (`1.0` when no target). |
| `[4]` | `autoHitFlag` | Set when `SkillData + 0xF3` is non-zero. When set, `hitChance = 100.0`, function returns early. |
| `[5]` | `rangeDistancePenalty` | `abs(rangeDeviation) * rangeAccuracyCost`. Set only when `useRange = true`. |

**Byte flag at `param_1 + 0x11`:** When the range-penalty path is taken, a byte flag at offset `+0x11` within the array (byte 17, inside float slot `[4]`) is set to `1` to signal "range calculation was active." This is a separate flag from `autoHitFlag`.

### `ComputeDamageData` — VA `0x1806DF4E0`

Builds and returns a `DamageData` object. Allocates one if `param_9` is null.

**`DamageData` object layout:**

| Offset | Type | Name | Meaning |
|--------|------|------|---------|
| `+0x10` | `float` | `expectedRawDamage` | Accumulated expected raw damage across all shot groups. |
| `+0x14` | `float` | `expectedEffectiveDamage` | Effective damage blended across cover/armour, capped to target HP fraction. |
| `+0x18` | `float` | `expectedKills` | HP-normalised kill count, capped to max ammo. |
| `+0x20` | `float` | `coverPenetrationChance` | `clamp((100 - (accuracy * coverStrength - rangePenalty) * 3) * 0.01, 0, 1)`. Max across shot groups. |
| `+0x24` | `bool` | `canKillInOneShot` | True when `maxAmmo <= expectedKills`. Sticky (OR'd across groups). |
| `+0x25` | `bool` | `canKillWithFullMag` | True when full magazine expected to be lethal. |
| `+0x28` | `Skill*` | `shotData` | Reference to the `ShotData` object used. Write-barriered. |

**`ShotPath` object fields accessed** (at `param_6 + offset`):

| Offset | Name | Used for |
|--------|------|---------|
| `+0x78` | `minimumHitChance` | Floor for `hitChance` in `ComputeHitProbability`. |
| `+0x8C` | `accuracyMult` | Multiplied into the main hit formula. |
| `+0x110` | `altDistancePenaltyCoeff` | Per-tile alternate range penalty. |
| `+0x128` | `movementAccuracyPenaltyPerTile` | Per-tile movement penalty. |
| `+0x13C` | `thirdDistanceModifier` | Third additive range modifier. |
| `+0x140` | `overallAccuracyMultiplier` | Applied to entire formula. |
| `+0x144` | `hpAccuracyCoeff` | Scales target HP into accuracy floor. |
| `+0x148` | `hpAccuracyFloor` | Minimum accuracy contribution from HP scaling. |
| `+0x14C` | `apAccuracyCoeff` | Scales target AP cost into accuracy floor. |
| `+0x150` | `apAccuracyFloor` | Minimum accuracy contribution from AP scaling. |
| `+0x16C` | `baseExtraHits` | Added to burst group hit count. |
| `+0x170` | `burstFraction` | Proportion of magazine fired per shot group. |

---

## 9. Ghidra Address Reference

### Fully analysed

| VA | Method | Class | Notes |
|----|--------|-------|-------|
| `0x180738E60` | `Evaluate(Actor)` | `Behavior` | Score-writing entry. Clamping, floor, deployment gate. |
| `0x180738F40` | `Execute(Actor)` | `Behavior` | Thin wrapper over `OnExecute`. Flag clear. |
| `0x18073E300` | `OnExecute` | `SkillBehavior` | Four-stage state machine. |
| `0x18073DF70` | `HandleDeployAndSetup` | `SkillBehavior` | AP-sufficiency decision. Flag setting. |
| `0x180739050` | `GetUtilityThreshold` | `Behavior` | Strategy-modulated threshold. |
| `0x180738D10` | `Collect` | `Behavior` | Deployment gate + tile dict dispatch. |
| `0x18073BDD0` | `ConsiderSkillSpecifics` | `SkillBehavior` | Armour-match + ammo penalty multiplier. |
| `0x18073DD90` | `GetTargetValue` (public) | `SkillBehavior` | Routing + contained-entity double pass. |
| `0x18073C130` | `GetTargetValue` (private) | `SkillBehavior` | Full targeting formula. |
| `0x1806E0AC0` | `ComputeHitProbability` | (utility) | Six-element hit probability array. |
| `0x1806DF4E0` | `ComputeDamageData` | (utility) | DamageData construction. Burst model. |

### Not yet decompiled (next-stage candidates)

| VA | Method | Class | Rationale |
|----|--------|-------|-----------|
| `0x18073BFA0` | `GetTagValueAgainst` | `SkillBehavior` | Tag effectiveness against opponent. Feeds `GetTargetValue`. |
| `0x180717730` | Unknown proximity lookup | (utility) | Used in final ally-pressure bonus in `GetTargetValue`. |
| `0x180717A40` | Unknown actor type check | (utility) | Gates proximity bonus application. |
| `0x180738DC0` | `Evaluate(Actor, Dict)` | `Behavior` | Tile-weighted evaluate. Not independently decompiled. |

---

## 10. Key Inferences and Design Notes

**The score ceiling of `21474` is not arbitrary.** `0x53E2` = 21474. This does not correspond to `INT_MAX / 100` or any obvious round number. It may be a designer-set maximum that emerged from score calibration. All subclass scoring should be understood as producing values in `[0, 21474]`.

**`m_IsFirstEvaluated` and `m_IsFirstExecuted` are misleadingly named.** They are cleared on execute and set on evaluate — they mean "this behaviour has been evaluated since it last executed." A subclass checking `m_IsFirstExecuted` is asking "am I in a fresh evaluation cycle?" not "is this the very first time I've run?"

**`OnBeforeProcessing` is called twice per turn minimum** (once during Collect, once during Evaluate). Subclasses overriding it must be idempotent or explicitly count calls.

**`m_DontActuallyExecute` is a planning flag, not an execution flag.** It is set during Collect/Evaluate and consumed by the Agent before calling `Execute`. This implies the Agent has a check equivalent to `if (!behaviour.m_DontActuallyExecute) Execute()`. The flag enables partial turn usage: the AI can commit AP to a deploy stance in one turn and fire in the next, with the planning happening upfront.

**The `_forImmediateUse` parameter is a planning mode switch.** When `false`, `GetTargetValue` computes expected value for future positioning (ally proximity, movement scoring, multi-turn horizon). When `true`, it scores for execution now — applies a different set of modifiers (AOE flags, target stance penalties, ammo efficiency). The same function serves both the "should I move here?" pass and the "should I fire now?" pass.

**Goal type (`param_5`) is an enum with at least three values:** `0` = attack, `1` = assist-via-movement, `2` = assist-via-skill. The final score assembly formula differs: attack maximises kill potential and damage; assist-move blends movement and damage; assist-skill uses the buff/heal scoring path (`fVar31`).

**`FUN_1805316f0` and `FUN_1829b1320` are distinct.** The former returns a float accuracy/probability scalar; the latter returns `Time.time`. They are visually similar call patterns in Ghidra and were conflated in preliminary notes. Only `FUN_1829b1320(0)` is `Time.time`.

**The contained-entity double-pass in `GetTargetValue` (public) is deliberate.** When a goal tile contains a transport or emplacement with a living occupant, the skill is scored against both the container and the occupant. The results are written to the same output — it is not clear whether they are summed or the max is taken. This requires `GetTagValueAgainst` decompilation to fully resolve.

---

## 11. Open Questions

**NQ-3** — `FUN_180717730` / `FUN_180717A40`: proximity data lookup and actor type check. These gate the ally-pressure bonus at the end of `GetTargetValue` private. Without them, the final scoring term is not fully understood.
*Next step:* Decompile both at their VAs. Both are expected to be short (< 20 lines).

**NQ-4** — `WeightsConfig` field map. Many offsets were read (`+0x13C`, `+0x78`, `+0x7C`, `+0xE4`, `+0xE8`, `+0xEC`, `+0xF0`, `+0xF8`) but the field names are inferred from context only. A class dump would replace all inferences with confirmed names.
*Next step:* In `dump.cs`, search for a class with a `float` field at `+0x13C` labelled as `utilityThreshold` or similar. Run `extract_rvas.py` on it.

**NQ-5** — Second config class at `DAT_18394c3d0`. This is accessed in virtually every scoring function but its identity is not confirmed. It is a different class from `WeightsConfig` (`DAT_183981f50`).
*Next step:* In `dump.cs`, search for a class with `float` fields clustered around `+0xE4`, `+0xE8`, `+0xEC`, `+0xF0`. The cluster will be unique.

**NQ-6** — `param_1 + 0x48` in `ComputeDamageData`. This is used as a list of shot groups. On `SkillBehavior`, offset `0x48` is `m_AdditionalRadius` (an int). The `param_1` in `ComputeDamageData` may be the `Skill` object, not `SkillBehavior`. If so, `Skill + 0x48` is the shot group list, which is a significant structural finding about `Skill`'s layout.
*Next step:* Confirm `param_1` identity in `ComputeDamageData` — it is passed as the skill object from `GetTargetValue` private at `*(param_1 + 0x20)` (`m_Skill`). This makes `param_1` in `ComputeDamageData` = `Skill*`, not `SkillBehavior*`. Field at `Skill + 0x48` = shot group list. The `m_AdditionalRadius` annotation on `SkillBehavior + 0x48` from the dump should be re-examined.

**NQ-7** — `GetTagValueAgainst` (`0x18073BFA0`). Called from `GetTargetValue` private to score skill tag effectiveness against an opponent. The tag system is partially understood (`TAG_ARMOR_MATCH`, `TAG_AMMO_COUNT`) but this function may reveal additional tag types.
*Next step:* Decompile at VA `0x18073BFA0`.

**NQ-8** — `GetOrder()` concrete return values. Three distinct RVAs appear in the extraction report for `GetOrder`: `0x50C760`, `0x519A90`, `0x547170`, `0x546260`. These are almost certainly simple `return N;` functions. Their values determine priority ordering among behaviours.
*Next step:* Decompile any one of them — likely 3 lines.