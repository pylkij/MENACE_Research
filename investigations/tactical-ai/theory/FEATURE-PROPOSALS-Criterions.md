# Menace — Tactical AI Criterion Scoring — Feature Modification Proposals

| Field | Value |
|---|---|
| Game | Menace |
| Platform | PC (Windows x64) |
| Binary | GameAssembly.dll (Unity IL2CPP) |
| Image base | `0x180000000` |
| Namespace | `Menace.Tactical.AI.Behaviors.Criterions` |
| Source material | Tactical AI Criterions Investigation Report (Stages 1–2, complete) |
| Document status | **Draft — Pre-implementation** |
| Document purpose | Enumerate proposed code modifications to the criterion scoring system, with implementation targets, expected behavioural outcomes, and risk assessments |

---

## Table of Contents

1. Document Purpose and Scope
2. System Preconditions
3. Modification Constraint Reference
4. Proposals
   - 4.1 Aggressive Forward Pressure — Flatten the Health-Gated Attack Cliff
   - 4.2 Tactical Retreat Graduated Response — Differentiated Flee/Avoid Radii
   - 4.3 Zone Denial Exploitation — Suppress the Threshold Bypass
   - 4.4 Flanking Opportunism — Amplify the ThreatFromOpponents Directional Multipliers
   - 4.5 Melee Roam Aggression — Extend Roam Radius Dynamically
   - 4.6 Cover Discipline — Penalise Chokepoint Stacking
   - 4.7 Ammo-Conscious Positioning — Scale Flee Behaviour by Ammo State
   - 4.8 Phase-Aware Deployment Surge — Boost the Deploy Component in Phase 0
5. Implementation Priority Matrix
6. Cross-Proposal Interaction Notes
7. Modifications Explicitly Out of Scope
8. Open Questions Before Implementation

---

## 1. Document Purpose and Scope

This document proposes concrete, targeted modifications to the Menace tactical AI criterion scoring system as reverse-engineered in the Criterions investigation report. Each proposal identifies a specific exploitable or tunable property of the scoring pipeline, describes the intended behavioural change in plain terms, specifies the exact fields and functions to modify, and assesses the risk of unintended side-effects.

The proposals are purely mechanical — they operate by modifying constants, conditions, and multipliers within the existing scoring framework. No new criterion subclasses are proposed. No new virtual methods are introduced. The goal is to achieve well-defined behavioural changes through the smallest possible interventions on a fully understood system.

All proposals are scoped to the `Menace.Tactical.AI.Behaviors.Criterions` namespace and the `AIWeightsTemplate` singleton as documented in the investigation report. Behaviour downstream of `Criterion.Score` output — the selection layer consuming scored tiles — is not addressed here.

**What this document does NOT cover:**

- Modifications to `ConsiderSurroundings.Evaluate` (not yet analysed; behaviour unknown).
- Modifications to `ConsiderZones.Collect` (deferred).
- Changes to the behaviour selection layer consuming `Score` output (outside investigation scope; requires a separate investigation before any proposals can be made).
- New criterion classes or new scoring dimensions not present in the current pipeline.
- Any change to `WakeUp.Collect` — the wakeup system integrates with a dispatch system outside the tile-scoring pipeline; proposing changes without that context would be unsound.

---

## 2. System Preconditions

Before any proposal can be implemented, the following open questions from the investigation report must be resolved. Each is listed here because at least one proposal depends on it.

**Precondition P1 — Resolve `AIWeightsTemplate +0x7c` offset conflict.**
The investigation identified `+0x7c` as potentially occupied by both `W_attack` (from `Criterion.Score`) and `tileEffectMultiplier` (from `ExistingTileEffects.Evaluate`). Proposals 4.1 and 4.3 both touch scoring weight fields in this region. Writing the wrong offset will corrupt the wrong system. This must be verified before writing any patch in the `+0x78`–`+0x84` range.

*Resolution path:* Re-read the Stage 2 raw decompilation of `ExistingTileEffects.Evaluate` at VA `0x180760FB0`. Confirm which param offset reads `+0x7c` and which reads `+0x78`. The two labels should separate cleanly once the raw Ghidra context is checked.

**Precondition P2 — Resolve runtime values of `COVER_PENALTIES[4]`.**
Proposals 4.6 (Cover Discipline) depends on the current penalty gradient across the four directional slots. Without knowing the baseline values it is not possible to assess whether a proposed change is a marginal adjustment or a floor inversion.

*Resolution path:* Memory-dump `CoverAgainstOpponents.COVER_PENALTIES` at runtime, or view the `.cctor` assembly listing at VA `0x18075EB00` for four float push instructions after the array allocation call.

**Precondition P3 — Confirm the `expf` argument convention for `+0xb0`, `+0xb4`, `+0xb8`.**
`AvoidOpponents` and `FleeFromOpponents` call `expf_approx` with the weight constant directly as the exponent. The investigation confirms this but it is worth re-stating: when modifying `avoidDirectThreatWeight` (`+0xb0`), `avoidIndirectThreatWeight` (`+0xb4`), or `fleeWeight` (`+0xb8`), the relationship between the stored float and the resulting score contribution is exponential, not linear. A change from `1.0` to `1.5` is not a 50% increase; it is an increase by factor `e^0.5 ≈ 1.65`. All proposals touching these fields include adjusted delta recommendations that account for this.

---

## 3. Modification Constraint Reference

The following hard constraints apply to all proposals. They are derived directly from the investigation report and must not be violated.

| Constraint | Source | Implication |
|---|---|---|
| `AIWeightsTemplate` is a singleton | `DAT_18394C3D0 +0xb8 +0x08` | All weight changes affect all units of the same AI configuration simultaneously. Per-unit weight variation is not possible without a separate investigation into the template's instantiation model. |
| `expf` is the score transform for avoid/flee weights | `AvoidOpponents.Evaluate`, `FleeFromOpponents.Evaluate` | Weight fields `+0xb0`, `+0xb4`, `+0xb8` are exponent inputs. Changes must be sized accordingly. |
| Zone threshold promotion is a hard bypass | `ConsiderZones.Evaluate`, `ctx.thresholdAccumulator += 9999.0` | Tiles in owned strategic zones will always pass the threshold gate regardless of any scoring changes. No proposal can suppress this without modifying `ConsiderZones.Evaluate` itself. |
| Roam is melee-only by structural enforcement | `Roam.Collect` first guard | The ranged weapon exit in `Roam.Collect` is unconditional code, not a weight. It cannot be tuned with an `AIWeightsTemplate` field change; modifying it requires a code patch. |
| `WakeUp` does not interact with tile scoring | `WakeUp.Collect` | The `wakeupPending` flag routes to a separate dispatch system. Changes to scoring weights do not affect wakeup behaviour. |
| `GetTileScoreComponents` returns 100.0 unconditionally for objective tiles | `GetTileScoreComponents` early exit at `tile +0xf3` | Objective tiles are immune to raw score suppression. No scoring weight change can de-prioritise a tile flagged as objective at the tile-data level. |
| The four master weights (`W_attack`, `W_ammo`, `W_deploy`, `W_sniper`) are final-stage scalars | `Criterion.Score` final combination | These weights multiply the already-computed component scores. Changing them affects all tile evaluations globally — they are not per-criterion guards. |

---

## 4. Proposals

---

### 4.1 Aggressive Forward Pressure — Flatten the Health-Gated Attack Cliff

**Behavioural intent:** The current system awards 8× the base attack component to healthy units at maximum range (health > 95%, `moveCostToTile ≥ maxMoves`). This creates a strong "sniper camp" incentive for healthy units, who score dramatically higher by holding at extreme range than by advancing. The proposal replaces the cliff (a hard 4× bonus at > 95% health) with a linear gradient, so that the attack bonus increases smoothly from 1× at 50% health to ~3× at 100% health. Units are still incentivised to stay healthy and hold range, but the cliff is eliminated, reducing the tendency to freeze high-health units at the map edge.

**Formula change — Component A of `Criterion.Score` (VA `0x180760140`):**

Current logic (reconstructed):
```c
if (rawScore × moveData.moveCostToTile >= unit.movePool.maxMoves) {
    fAtk *= 2.0f;
    if (GetHealthRatio(unit) > 0.95f) {
        fAtk *= 4.0f;   // 8× total at max range + near-full health
    }
}
```

Proposed logic:
```c
if (rawScore × moveData.moveCostToTile >= unit.movePool.maxMoves) {
    fAtk *= 2.0f;
    float healthRatio  = GetHealthRatio(unit);
    float healthBonus  = 1.0f + max(healthRatio - 0.5f, 0.0f) * 4.0f;  // [1.0 @ 50% .. 3.0 @ 100%]
    fAtk *= healthBonus;
}
```

**Expected change:** Maximum range attack multiplier drops from a maximum of 8× to a maximum of 6× (at 100% health), and the threshold for receiving the full bonus is removed. Units between 50–95% health that previously received only the 2× max-range bonus now receive 2× to 5× based on health. Damaged units become more aggressive under this model, not less.

**Affected function:** `Criterion.Score` — VA `0x180760140`. No `AIWeightsTemplate` fields changed; this is a code-level logic patch.

**Risk:** Medium. The health multiplier is a simple conditional in a well-understood function. The linear replacement is safe arithmetic. The primary risk is that `GetHealthRatio` returns values outside [0.0, 1.0] under edge conditions (unit at max health with buffs); add a `clamp(healthRatio, 0.0f, 1.0f)` guard.

**Prerequisite:** None. This does not depend on any unresolved open question.

---

### 4.2 Tactical Retreat Graduated Response — Differentiated Flee/Avoid Radii

**Behavioural intent:** `FleeFromOpponents` (radius 16) and `AvoidOpponents` (radius 11) currently use fixed radii. The result is that all units regardless of their current health or ammo state generate the same avoidance footprint. The proposal introduces health-scaled radii: a unit below 30% health should expand its flee radius aggressively (up to 22 tiles), while a unit above 70% health should contract its avoid radius (down to 7 tiles), making healthy units more willing to enter contested ground and damaged units more sharply evasive.

This requires two changes: a code patch to `FleeFromOpponents.Evaluate` and `AvoidOpponents.Evaluate` to replace the hard-coded radius literals with runtime expressions, and a new pair of `AIWeightsTemplate` fields to hold the health thresholds and radius scale factors.

**Modification A — `FleeFromOpponents.Evaluate` (VA `0x1807613A0`):**

Current radius literal:
```c
if (dist < 16) { ... }
```

Proposed:
```c
float healthRatio   = GetHealthRatio(unit);
float fleeScale     = 1.0f + max(0.4f - healthRatio, 0.0f) * 2.5f;   // 1.0 at ≥ 40% health, up to 1.75 at 0%
int   effectiveRad  = (int)(16.0f * fleeScale);                        // 16 → up to 28, floor at 16
if (dist < effectiveRad) { ... }
```

**Modification B — `AvoidOpponents.Evaluate` (VA `0x18075BE10`):**

Current radius literal:
```c
if (dist < 11) { ... }
```

Proposed:
```c
float healthRatio   = GetHealthRatio(unit);
float avoidScale    = 0.6f + healthRatio * 0.4f;    // 0.6 at 0% health → 1.0 at full health
int   effectiveRad  = (int)(11.0f * avoidScale);     // 7 tiles at full health, 11 at 0%
if (dist < effectiveRad) { ... }
```

**Note on `expf` interaction:** `AvoidOpponents` and `FleeFromOpponents` accumulate `expf(weightConstant)` per tile within the radius. Expanding the radius increases the number of tiles that contribute, multiplying the total penalty accumulation. With a radius of 22 instead of 16, `FleeFromOpponents` accumulates from a roughly 1.9× larger tile area. The weight constants at `+0xb0`, `+0xb4`, `+0xb8` should be reduced by approximately `ln(1.9) ≈ 0.64` to maintain current intensity at baseline health. For a unit at near-zero health the accumulation will be substantially larger — this is the intended effect.

**AIWeightsTemplate impact:** None — the scale factors above are embedded in the code logic. If tunable scale factors are desired, two new float fields would need to be allocated in the `AIWeightsTemplate` structure in the `+0x100–0x140` range (currently unextracted per the report). This is marked as a follow-up option rather than a requirement for the initial implementation.

**Risk:** Medium-high. Radius expansion directly increases the number of loop iterations in `FleeFromOpponents`. With a radius of 22+, the tile area is `π × 22² ≈ 1520` tiles vs `π × 16² ≈ 804` for the current implementation. On maps with dense opponent groups, this could double the loop cost for flee evaluation. Profile before shipping; consider capping the effective radius at 20.

**Prerequisite:** P3 (confirm `expf` argument convention). The weight reduction recommendation is based on the confirmed exponential relationship; verify before adjusting `+0xb4` and `+0xb8`.

---

### 4.3 Zone Denial Exploitation — Suppress the Threshold Bypass

**Behavioural intent:** `ConsiderZones.Evaluate` unconditionally writes `ctx.thresholdAccumulator += 9999.0` for tiles in owned strategic zones, guaranteeing they always pass the threshold gate regardless of scoring. This means an owned zone tile is never filtered out even if it scores poorly on cover, threat, and positioning criteria. In heavily contested maps this creates a pathology: AI units fixate on owned zone tiles even when those tiles are tactically exposed, overriding the nuanced scoring produced by all other criteria.

The proposal replaces the hard bypass with a capped bonus. Instead of `9999.0`, write a large but finite value — `settings.zoneThresholdWeight_A` or `settings.zoneThresholdWeight_B` from `AIWeightsTemplate +0x68` / `+0x6c` — scaled by cover quality. Tiles in owned zones are still strongly promoted, but a tile with zero cover quality or occupied by an enemy contributes less to the threshold accumulator and can be filtered out if it scores poorly enough on other criteria.

**Modification — `ConsiderZones.Evaluate` (VA `0x18075CC20`):**

Current write for zone-membership flag `0x01`:
```c
ctx.thresholdAccumulator += 9999.0f;
```

Proposed:
```c
float coverComponent = max(ctx.accumulatedScore, 0.0f);   // read current cover/threat score
float zoneBoost      = settings.zoneThresholdWeight_A     // already exists at AIWeightsTemplate +0x68
                       * (1.0f + coverComponent * 0.1f);  // scale up with good cover
ctx.thresholdAccumulator += min(zoneBoost, 500.0f);       // hard cap replaces 9999
```

The same change should be applied to the team-ownership flag `0x04` path:
```c
ctx.thresholdAccumulator += min(zoneBoost, 500.0f);   // was: 9999.0
```

**Expected change:** Units will still strongly prefer owned zone tiles, but a tile in an owned zone that has been flanked, occupied by an enemy, or has zero cover against known opponents can now score below the threshold and be discarded. Units become capable of abandoning a zone tile that has become indefensible, which the current system makes structurally impossible.

**AIWeightsTemplate fields leveraged:** `zoneThresholdWeight_A` (`+0x68`) and `zoneThresholdWeight_B` (`+0x6c`). These already exist; the proposal uses them as the cap rather than a separate constant. The current values of these fields at runtime are unknown — confirm via memory dump before testing, as an extremely low value here would cause owned zone tiles to be discarded far too readily.

**Risk:** High. The 9999.0 bypass is clearly intentional design — it enforces that the zone system is a hard strategic override. Weakening it may produce units that retreat from owned objectives when under fire, which may or may not be the desired behaviour in context. This modification should be tuned conservatively: start with a cap of `500.0` and lower it only if the pathological fixation behaviour persists.

**Prerequisite:** P1 (resolve `+0x7c` conflict) — not directly, but any corruption of the `zoneThresholdWeight_A` field reading in the region `+0x68` could be masked by offset errors in nearby fields. Resolve P1 before any write in the `+0x58`–`+0x88` region.

---

### 4.4 Flanking Opportunism — Amplify the ThreatFromOpponents Directional Multipliers

**Behavioural intent:** `ThreatFromOpponents.Score (B)` applies directional multipliers of `1.2×` for flanking approach tiles and `0.9×` for retreating tiles during its spatial scan. These are modest nudges — a 33% ratio between the best and worst direction. The proposal increases this spread, making flanking tiles significantly more attractive and direct retreat tiles significantly more penalised. The goal is units that aggressively seek flanking angles rather than converging on the obvious direct approach.

**Modification — `ThreatFromOpponents.Score (B)` (VA `0x18076B710`):**

Current directional multipliers (from reconstruction):
```c
if (flanking direction and path clear): score *= 1.2f;
if (moving away from enemy):            score *= 0.9f;
if (moving toward enemy):               score *= 1.2f;
```

Proposed multipliers:
```c
if (flanking direction and path clear): score *= 1.6f;   // was 1.2
if (moving away from enemy):            score *= 0.65f;  // was 0.9 — stronger penalty
if (moving toward enemy):               score *= 1.2f;   // unchanged — direct advance is neutral
```

Additionally, the existing flanking bonus in `ThreatFromOpponents.Score (A)` — applied when `weaponList distance < weaponListDistanceThreshold` — currently uses `settings.flankingBonusMultiplier` (`AIWeightsTemplate +0xa0`). Increase this field value from its current runtime value to approximately `1.4×` baseline to reinforce the flanking preference at the individual weapon evaluation level as well.

**AIWeightsTemplate fields changed:** `flankingBonusMultiplier` (`+0xa0`) — increase by approximately 30–40% from baseline runtime value.

**Code-level changes:** Multiplier literals in `ThreatFromOpponents.Score (B)` at VA `0x18076B710`. These are inline float constants, not weight template reads.

**Expected change:** Units will orbit around opponents more actively rather than advancing in straight lines. The retreat penalty makes withdrawing from a flanking-eligible position costly, reinforcing commitment to the flanking approach once selected. Combined with Proposal 4.1, high-health units will still want to find maximum-range positions, but those positions will now be scored significantly higher if they also represent a flanking angle.

**Risk:** Low-medium. The directional multipliers are applied inside a spatial scan that already selects the best tile. Increasing the multiplier spread does not change which tiles are evaluated, only how they are ranked. The primary risk is that if flanking paths are consistently blocked by terrain, the `1.6×` bonus will never fire and the `0.65×` penalty will cause units to stall without advancing. Playtest on maps with varied terrain before tuning further.

**Prerequisite:** None. Both the code-level patch and the `+0xa0` field write are clean.

---

### 4.5 Melee Roam Aggression — Extend Roam Radius Dynamically

**Behavioural intent:** `Roam.Collect` computes `roamRadius = moveSpeed / effectiveRange` and uses a bounding box of that size around the unit's current position. For melee units with high weapon range or low move speed, this collapses to a very small radius, causing the unit to select from a tiny candidate set and effectively stand still. The proposal adds a minimum roam radius floor and, optionally, an enemy-proximity amplifier so that melee units with no current targets actively move toward the nearest opponent group.

**Modification — `Roam.Collect` (VA `0x180768300`):**

Current radius logic:
```c
float roamRadius = moveSpeed / effectiveRange;
if (roamRadius < 1) return;
```

Proposed:
```c
float roamRadius    = moveSpeed / effectiveRange;
float minRadius     = 3.0f;   // floor — melee units always consider at least a 3-tile ring
roamRadius          = max(roamRadius, minRadius);

// Optional enemy-proximity amplifier
float nearestEnemyDist = GetNearestOpponentDist(unit);   // requires investigation of available utility functions
if (nearestEnemyDist > 0.0f && nearestEnemyDist < 20.0f) {
    roamRadius += (20.0f - nearestEnemyDist) * 0.15f;   // up to +3 tiles when enemy is 20 tiles away
}
if (roamRadius < 1) return;
```

**Note:** `GetNearestOpponentDist` is not a confirmed function name from the investigation. The existing `zoneData.opponentTileList` is iterated by `WakeUp.Collect` and is accessible from the unit's move pool (`movePool.zoneData +0x48`). The nearest opponent distance can be computed inline using the same `GetTileDistance` call used throughout the namespace, iterating `opponentTileList` and keeping the minimum. This is approximately 5 lines of loop code, not a new function dependency.

**Expected change:** Melee units with no targets will generate larger candidate tile sets and will be drawn toward opponent proximity. Units that currently stall due to a near-zero roam radius will now move purposefully. The enemy-proximity amplifier ensures that as the enemy approaches, the unit's interest in intermediate tiles grows proportionally.

**Risk:** Low. Roam only fires when the unit has no active targets (`unit.opponentList.behaviorConfig` roam flag check). It cannot override combat-phase scoring. The only risk is that the expanded candidate set causes Roam to select tiles that are blocked or near hazards — the existing `tile.isBlocked` and `tile.isOccupied` guards already filter these.

**Prerequisite:** None. The floor radius of 3.0 is unconditionally safe. The enemy-proximity amplifier requires confirming `opponentTileList` access is legal from within `Collect` context (it is — `WakeUp.Collect` already does this).

---

### 4.6 Cover Discipline — Penalise Chokepoint Stacking

**Behavioural intent:** `CoverAgainstOpponents.Evaluate` Phase 3 adds a flat `+10.0` bonus to any tile that is not a chokepoint (`if not IsChokePoint(tile): total += 10.0`). This is a mild anti-chokepoint nudge. The proposal replaces the flat bonus with a stacking penalty: each ally occupying an adjacent tile subtracts from the total, discouraging clusters. The flat chokepoint avoidance bonus is preserved but its magnitude is reduced to balance against the new ally-adjacency penalty.

**Modification — `CoverAgainstOpponents.Evaluate` Phase 3 (VA `0x18075DAD0`):**

Current logic:
```c
if (total != 0.0f && !IsDeploymentLocked(tile)) {
    if (!IsChokePoint(tile)) total += 10.0f;
}
```

Proposed:
```c
if (total != 0.0f && !IsDeploymentLocked(tile)) {
    if (!IsChokePoint(tile)) total += 6.0f;    // reduced from 10.0 to make room for stack penalty
    int adjAllies = GetAdjacentAllyCount(tile, unit);  // requires utility function investigation — see note
    total -= adjAllies * settings.occupiedDirectionPenalty;   // reuse +0xd4; applies per adjacent ally
}
```

**Note:** `GetAdjacentAllyCount` is not a confirmed function from the investigation. However, `CoverAgainstOpponents.Evaluate` Phase 3 already iterates all 8 directions and checks `if direction occupied: total -= occupiedDirectionPenalty`. That loop already counts occupied adjacent directions. The proposal is simply to also subtract `occupiedDirectionPenalty` when the occupant is an ally rather than only when it is an enemy threat. This can be implemented inline in the existing direction loop without a new function dependency: modify the occupant type check to apply the penalty regardless of occupant team, rather than only for enemy-team occupants.

**AIWeightsTemplate fields changed:** `occupiedDirectionPenalty` (`+0xd4`) — the field already exists and is already used in Phase 3. The same value drives both the enemy-occupant penalty (current) and the new ally-stacking penalty (proposed). If the two penalties should have different magnitudes, a new `allyAdjacencyPenalty` field would need to be allocated at an unextracted offset (`+0x100–0x140`).

**Expected change:** Units will spread out, preferring open tiles over tiles adjacent to allies. Combined with the existing enemy-occupant penalty already in the system, Phase 3 will penalise both ally clustering and enemy proximity consistently. Units in cover will seek independent positions rather than piling behind the same wall.

**Risk:** Low-medium. The direction-loop occupancy check in Phase 3 already runs; extending it to ally occupants is a small condition change. The risk is that the penalty is too large relative to the cover bonus, causing units to prefer exposed isolated positions over covered stacked positions. The starting value should use the existing `occupiedDirectionPenalty` field unchanged — do not increase its value for the first test.

**Prerequisite:** P2 (resolve `COVER_PENALTIES[4]` values) is not strictly required but informs whether the cover bonus changes in Phase 2 are already large enough to absorb the additional penalty introduced here.

---

### 4.7 Ammo-Conscious Positioning — Scale Flee Behaviour by Ammo State

**Behavioural intent:** Currently, `FleeFromOpponents.Evaluate` is agnostic to the unit's ammo state. A unit with 0 ammo remaining generates the same flee accumulation as a fully-loaded unit. The proposal makes units with low ammo more aggressively evasive — a unit that cannot shoot should strongly prefer to withdraw. This is achieved by scaling `fleeWeight` at evaluation time based on `unit.currentAmmo / unit.ammoSlotCount`.

**Modification — `FleeFromOpponents.Evaluate` (VA `0x1807613A0`):**

Current accumulation per in-range tile:
```c
if (group CAN target unit.team) {
    fAccum += expf(settings.fleeWeight);   // settings.fleeWeight at AIWeightsTemplate +0xb8
}
```

Proposed:
```c
if (group CAN target unit.team) {
    float ammoRatio      = (unit.ammoSlotCount > 0)
                           ? (float)unit.currentAmmo / (float)unit.ammoSlotCount
                           : 0.0f;
    float adjustedWeight = settings.fleeWeight + (1.0f - ammoRatio) * 0.8f;   // up to +0.8 exponent at 0 ammo
    fAccum += expf(adjustedWeight);
}
```

**`expf` scaling note (Precondition P3 applies directly here):** Because the weight is an exponent, adding `0.8` to `fleeWeight` multiplies the per-tile contribution by `e^0.8 ≈ 2.2`. At zero ammo, every in-range tile contributes 2.2× its normal flee accumulation, driving the unit out of the contested area proportionally harder. At full ammo, behaviour is unchanged. The `0.8` delta is the recommended starting point; reduce to `0.5` if the withdrawal behaviour is too extreme in testing.

**AIWeightsTemplate fields read:** `fleeWeight` (`+0xb8`) — read-only in this context; the adjusted weight is computed inline and not written back to the template.

**Unit fields read:** `currentAmmo` (`unit +0x5c`), `ammoSlotCount` (`unit +0x5b`) — both confirmed from the investigation.

**Expected change:** A unit with low or zero ammo will generate significantly higher flee accumulation for every opponent-group tile within 16 tiles, pushing its tile evaluations toward distant or covered positions. A fully loaded unit is unaffected. This creates an emergent ammo-conservation behaviour without any explicit "am I out of ammo?" decision tree.

**Risk:** Low. The computation is added inside an already-correct loop, reading confirmed field offsets. The only new dependency is the integer division for `ammoRatio`, which needs a zero-denominator guard (provided above).

**Prerequisite:** P3 (confirm `expf` argument convention). The delta of `0.8` is sized with the exponential relationship in mind; if P3 is incorrect and the weights are used linearly, the delta would need to be `0.8 × baseline_flee_weight` instead.

---

### 4.8 Phase-Aware Deployment Surge — Boost the Deploy Component in Phase 0

**Behavioural intent:** `Criterion.Score` Component C (deployment/positional bonus) applies a multiplier of `3.0×` when `combined ≥ 0.67`, but this multiplier is not phase-gated. During deployment phase (phase 0), units should be far more willing to advance aggressively toward strong positional tiles regardless of enemy proximity, because no combat has started yet. The proposal gates a larger positional multiplier specifically to phase 0, giving deployment AI a distinct "surge" character compared to mid-game cautious positioning.

**Modification — `Criterion.Score` Component C (VA `0x180760140`):**

Current logic:
```c
if (adjScore > 0.0f) {
    combined = min(adjScore * rawScore + adjScore, 2.0f);
    fDeploy  = combined * settings.deployPositionWeight;
    if (!tile.hasEnemy)
        fDeploy *= (GetMovementDepth(unit) * 0.25f + 1.5f);
    if (combined >= 0.67f) fDeploy *= 3.0f;
}
```

Proposed:
```c
if (adjScore > 0.0f) {
    combined = min(adjScore * rawScore + adjScore, 2.0f);
    fDeploy  = combined * settings.deployPositionWeight;
    if (!tile.hasEnemy)
        fDeploy *= (GetMovementDepth(unit) * 0.25f + 1.5f);

    float combineBonus = (IsDeploymentPhase(unit))
                         ? 5.0f     // phase 0: surge — prioritise strong positions
                         : 3.0f;    // phase 1/2: standard behaviour unchanged
    if (combined >= 0.67f) fDeploy *= combineBonus;
}
```

**`IsDeploymentPhase` reuse:** `Criterion.IsDeploymentPhase` (VA `0x18071B670`) is already defined on the base class and returns `ScoringContext.singleton.phase == 0`. It is called inline throughout the namespace. Using it here is consistent with existing patterns and adds no new dependency.

**`deployPositionWeight` field:** `AIWeightsTemplate +0xec`. An alternative implementation would increase this field for phase 0 directly rather than patching the multiplier literal; however, `deployPositionWeight` is a global weight applied to all phases, so modifying it would bleed into phase 1/2 behaviour. The inline phase gate is preferred.

**Expected change:** During deployment, tiles that score above the `0.67` combined threshold receive a positional bonus of 5× instead of 3× — a 67% increase in deployment-phase positional drive. Units will cluster more aggressively toward high-value positions at the start of the scenario. Post-deployment (phases 1 and 2), behaviour is identical to today.

**Risk:** Low. `IsDeploymentPhase` is a simple singleton read. The only code change is replacing the literal `3.0f` with a conditional. The 5× factor is conservative — in the worst case, deployment AI is slightly too aggressive in seeking forward positions, which is a correctable tuning issue rather than a structural problem.

**Prerequisite:** None.

---

## 5. Implementation Priority Matrix

Ranked by combination of expected behavioural impact, implementation risk, and prerequisite simplicity.

| Priority | Proposal | Prerequisite | Code Change | Weight Change | Risk |
|---|---|---|---|---|---|
| 1 | 4.8 — Phase-0 Deploy Surge | None | `Criterion.Score` Component C multiplier | None | Low |
| 2 | 4.5 — Melee Roam Aggression | None | `Roam.Collect` radius floor | None | Low |
| 3 | 4.7 — Ammo-Conscious Flee | P3 (expf convention) | `FleeFromOpponents.Evaluate` weight compute | None (`+0xb8` read-only) | Low |
| 4 | 4.1 — Flatten Health Cliff | None | `Criterion.Score` Component A condition | None | Medium |
| 5 | 4.4 — Flanking Opportunism | None | `ThreatFromOpponents.Score (B)` literals | `+0xa0` flankingBonusMultiplier | Low–Med |
| 6 | 4.6 — Cover Discipline | P2 (COVER_PENALTIES) | `CoverAgainstOpponents.Evaluate` Phase 3 direction loop | `+0xd4` occupiedDirectionPenalty (unchanged) | Med |
| 7 | 4.2 — Flee/Avoid Radius Scale | P3 (expf convention) | `FleeFromOpponents.Evaluate`, `AvoidOpponents.Evaluate` radius expressions | `+0xb4`, `+0xb8` reduce to compensate | Med–High |
| 8 | 4.3 — Zone Threshold Cap | P1 (`+0x7c` conflict) | `ConsiderZones.Evaluate` threshold writes | `+0x68` / `+0x6c` values at runtime | High |

---

## 6. Cross-Proposal Interaction Notes

Several proposals interact and their combined effect is not simply additive. The following pairs warrant joint testing before independent deployment:

**4.1 + 4.4 (Health Cliff × Flanking):** Proposal 4.1 reduces the max-range attack bonus from 8× to at most 6×. Proposal 4.4 increases the flanking multiplier to 1.6×. For a high-health unit at a flanking-angle maximum-range tile, the combined effect is `6.0 × 1.6 = 9.6×` base attack, which is higher than the current `8×` maximum. If the intent is to reduce the incentive for edge-camping, these two proposals may partially cancel each other for the specific case of a flanking edge position. Either reduce the flanking multiplier to `1.4×`, or add a range cap to the flanking bonus (only apply when the unit is not already at maximum range).

**4.2 + 4.7 (Radius Scale × Ammo Flee):** Both proposals increase flee accumulation for damaged or ammo-depleted units. If both are active simultaneously, a unit at low health and low ammo will have both an expanded flee radius and an amplified per-tile accumulation. The combined effect is multiplicative. Test both proposals independently on baseline-health, full-ammo units first, then test the combined case with a low-health, low-ammo unit. If flee accumulation becomes large enough to suppress all other scores, units may freeze rather than retreat — cap the combined flee accumulation with a ceiling value if necessary.

**4.3 + 4.6 (Zone Threshold Cap × Cover Discipline):** Proposal 4.3 reduces the attractiveness of owned zone tiles with poor cover. Proposal 4.6 penalises stacking on any tile near allies. If an owned zone has limited cover and multiple allied units nearby, both penalties apply, and the zone tile may drop below threshold. This is the correct emergent behaviour — the unit should seek a better position — but it creates a visible feedback loop where a contested zone gradually becomes deprioritised. Monitor whether AI units abandon objectives in contested zones more readily than intended.

---

## 7. Modifications Explicitly Out of Scope

The following changes were considered and rejected or deferred for the reasons stated.

**Modifying `WakeUp.Collect`:** The `wakeupPending` flag routes to a dispatch system outside the scoring pipeline. Changes to the tile-scoring weights cannot affect wakeup behaviour, and changes to `WakeUp.Collect` itself would require a separate investigation into the wakeup dispatch system. Deferred.

**Removing the melee-only guard from `Roam.Collect`:** The first guard in `Roam.Collect` is a hard structural exit for ranged units. This is not a configurable option. Making Roam available to ranged units would require understanding why the original designers enforced this boundary — it likely exists because ranged units have dedicated positioning logic via `ThreatFromOpponents` that melee units do not benefit from. Opening Roam to ranged units without that context could produce double-scoring pathologies. Deferred pending investigation of `ConsiderSurroundings.Evaluate`.

**Modifying `GetTileScoreComponents` objective tile fast-exit:** The `tile.isObjectiveTile` early exit to `[0]=100.0` is a tile-data-level override that bypasses all scoring logic. Making objective tile scoring conditional on unit state or phase would require changes in `GetTileScoreComponents` and would interact with `ConsiderZones.PostProcess`'s own objective-tile logic. The two "objective tile" mechanisms (`tile +0xf3` vs `ctx +0x60`) must be fully understood before any modification. Deferred.

**Modifying `ThreatFromOpponents.GetThreads`:** Changing the thread count from 4 to a different value affects only performance, not the scoring outcome. Out of scope for a behavioural proposal.

**Adding per-unit weight variation:** `AIWeightsTemplate` is a singleton; all units share the same weight set at runtime. Unit-type-specific weight differentiation would require either multiple template instances or per-unit overrides neither of which is supported by the current architecture as observed. Out of scope.

---

## 8. Open Questions Before Implementation

The following questions are inherited from the investigation report or arise from the proposals themselves. They must be answered before implementation proceeds on the affected proposals.

1. **Resolve `AIWeightsTemplate +0x7c` offset conflict (P1).** Affects: Proposal 4.3 safety boundary. Steps: Re-read raw Ghidra decompilation for `ExistingTileEffects.Evaluate` at VA `0x180760FB0`; confirm which access reads `+0x7c` vs `+0x78`.

2. **Confirm runtime values of `COVER_PENALTIES[4]` (P2).** Affects: Proposal 4.6 calibration. Steps: Memory-dump the static array at runtime, or read the `.cctor` assembly listing at VA `0x18075EB00`.

3. **Confirm `expf` argument convention (P3).** Affects: Proposals 4.2 and 4.7. Steps: Confirmed from the investigation report — exponent convention is established. Requires only that implementers apply the correct delta sizing as specified in each proposal.

4. **What does `ConsiderSurroundings.Evaluate` do?** Until this is known, any proposal that might interact with it — particularly cover and zone scoring — cannot be assessed for completeness. Extract RVAs and decompile VA `0x18075C240` before marking the feature set final.

5. **What does `ConsiderZones.Collect` do?** VA `0x18075C630`. Zone-tile candidate set construction may interact with Proposal 4.3's threshold suppression in ways that are not yet predictable. Batch with `ConsiderSurroundings` analysis.

6. **What are the current runtime values of `zoneThresholdWeight_A` (`+0x68`) and `zoneThresholdWeight_B` (`+0x6c`)?** Proposal 4.3 uses these as the replacement for the 9999.0 bypass. If these fields are set very low (e.g., < 10.0) at runtime, the proposal would effectively de-prioritise owned zone tiles entirely — the opposite of the intended conservative tuning. Memory-dump the `AIWeightsTemplate` singleton before implementing 4.3.

7. **Behaviour selection layer consuming `Score` output.** Several proposals produce aggregate score changes that may interact with how the selection layer filters or ranks tiles post-scoring. This is particularly relevant for Proposal 4.3 (zone threshold cap): if the selection layer applies its own zone override, suppressing the scoring-layer threshold bypass may be invisible. Requires a separate investigation; see investigation report Open Question 7.
