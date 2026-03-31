# Menace — Tactical AI Criterion Scoring — Feature Modification Proposals
# Addendum: Behavior-Layer Integration

| Field | Value |
|---|---|
| Game | Menace |
| Platform | PC (Windows x64) |
| Binary | GameAssembly.dll (Unity IL2CPP) |
| Image base | `0x180000000` |
| Namespaces | `Menace.Tactical.AI.Behaviors.Criterions` (criterion layer) · `Menace.Tactical.AI.Behaviors` (behavior layer) |
| Source material | Criterions Investigation Report (Stages 1–2); Behavior System Investigation Report (52 VAs, complete) |
| Parent document | Tactical AI Criterion Scoring — Feature Modification Proposals |
| Document status | **Draft — Pre-implementation** |
| Document purpose | Addendum to the original criterion proposals. Adds new criterion-layer proposals made possible by the completed behavior investigation, corrects three assumptions in the original document that the behavior investigation invalidates, and introduces a dedicated cross-layer integration section describing compound behaviors achievable only through coordinated modifications at both layers simultaneously. |

---

## Table of Contents

A. Corrections to the Original Criterion Proposals
B. New Criterion Proposals (Behavior-Informed)
   - 4.9  Attack Tile Affinity — Weight Criterion Scores Toward Tiles That Enable Attacks
   - 4.10 Co-Fire Position Preference — Boost Tiles Where Allies Have Line of Sight
   - 4.11 Goal-Type Tile Separation — Differentiate Positioning by Behavior Goal Type
   - 4.12 AP-Residual Tile Preference — Penalise Tiles Whose AP Cost Leaves Insufficient Reserve
   - 4.13 Suppression Escape Routing — Bias Flee Accumulation When Unit Is Under Suppression
C. Cross-Layer Integration Proposals
   - I.   Committed Aggressor Archetype
   - II.  Coordinated Fire Team Archetype
   - III. Suppression-Then-Advance Doctrine
   - IV.  Ammo Economy Doctrine
   - V.   Defensive Anchor Archetype
D. Revised Implementation Priority Matrix (Full Set)
E. Revised Open Questions Before Implementation

---

## A. Corrections to the Original Criterion Proposals

The behavior layer investigation resolves three assumptions made in the original criterion proposals that were flagged as needing downstream context. Each correction is stated precisely; the affected proposal number is noted.

---

**Correction A.1 — The "behaviour selection layer" is now fully understood. Revise Scope Section and Open Question 7.**

The original document deferred all discussion of how `Criterion.Score` output is consumed, noting it was "outside investigation scope." The behavior investigation fully resolves this. The consumption path is:

```
Criterion.Score (per tile, per criterion)
    → TileScore.movementScore / utilityScore / rangeScore       (stored in agent tile dict)
    → Move.OnEvaluate reads movementScore, fWeight, MoveBaseScore → int m_Score
    → Attack.OnEvaluate reads tileDict movement scores → (1 - moveCostFraction) multiplier
    → Deploy.OnCollect reads rangeScore → two-penalty adjustment
    → Behavior.Evaluate clamps m_Score to [0, 21474], floors at 5
    → Agent ranks behaviours by m_Score; GetUtilityThreshold filters; winner executes
```

**Implication for Proposal 4.3 (Zone Threshold Cap):** Open Question 7 in the original document asked whether the selection layer applied its own zone override that might make the threshold suppression invisible. The answer is no. `ConsiderZones.Evaluate` writes to `ctx.thresholdAccumulator`, which is compared against `GetUtilityThreshold` at the criterion layer before any behavior scoring occurs. The behavior layer does not re-apply zone logic. Proposal 4.3 will produce its intended effect without interference from the behavior layer. The risk noted in Open Question 7 does not exist. This open question can be closed.

**Implication for the criterion layer generally:** Criterion scores feed `TileScore` fields. The behavior layer multiplies, scales, and clamps them but does not re-score tiles from scratch. Criterion-layer changes are not diluted by behavior-layer overrides; they propagate through faithfully.

---

**Correction A.2 — The `W_attack` / `W_ammo` / `W_deploy` / `W_sniper` master weights are consumed upstream of `Move.OnEvaluate`, not downstream of it. The constraint table entry is misleading. Affects: Section 3 constraint table.**

The original constraint table states: "The four master weights are final-stage scalars — changing them affects all tile evaluations globally." This is correct for `Criterion.Score`, but the behavior investigation clarifies the downstream relationship. `Move.OnEvaluate` does not read the `Criterion.Score` output directly as a single float. It reads `TileScore.movementScore`, which is a field written by the criterion layer's scoring pipeline and stored in the tile dict. The `W_attack`, `W_ammo`, `W_deploy`, `W_sniper` weights affect the magnitude of `Criterion.Score`, which affects `TileScore.movementScore`, which then feeds `Move.OnEvaluate`'s `fWeight` computation:

```
fWeight = BehaviorWeights.weightScale × AIWeightsTemplate.MoveScoreMult (+0x12C) × (currentAP / maxAP) × ...
FinalScore = (int)(fWeight × AIWeightsTemplate.MoveBaseScore (+0x128))
```

The implication is that changes to criterion-layer master weights affect `Move`'s final `m_Score` through two multiplicative stages: the criterion weight changes `TileScore.movementScore`, and `Move.OnEvaluate` then scales that further by `MoveScoreMult` and `MoveBaseScore`. A 2× increase in `W_deploy` does not produce a 2× increase in `Move.m_Score` — it produces `2 × MoveScoreMult × MoveBaseScore / MoveBaseScore_baseline × ...` change, which may differ substantially depending on the current values of those behavior-layer fields. **Anyone modifying `W_attack`, `W_ammo`, `W_deploy`, or `W_sniper` must verify the compound effect on `Move.m_Score` against the ceiling of 21474.**

---

**Correction A.3 — Criterion Proposal 4.6 (Cover Discipline) must account for `Deploy.OnCollect`'s ally proximity penalty, which already operates on tile spacing. The two systems may conflict. Affects: Proposal 4.6.**

The original Proposal 4.6 proposes penalising ally-adjacent tiles in `CoverAgainstOpponents.Evaluate` to discourage stacking in combat. The behavior investigation reveals that `Deploy.OnCollect` already applies an ally proximity penalty during deployment:

```
for each set-up ally within 6 tiles:
    rangeScore -= (6.0 - distance) × AIWeightsTemplate.DistanceToAlliesScore (+0xD0)
```

This is a separate scoring field (`TileScore.rangeScore`) from `CoverAgainstOpponents`'s output (`ctx.accumulatedScore`), and it only fires during deployment phase (gated by `strategyMode == 0`). The two penalties are not the same mechanism, but they serve the same purpose — spreading units out. In combat phase (phase 1+), `Deploy.OnCollect` does not run, so the ally proximity penalty is absent, and Proposal 4.6's cover-layer ally penalty would be the only active spacing mechanism. This is correct and the proposal is sound for combat phase.

However, during deployment phase (phase 0), both the Deploy rangeScore penalty and a potential CoverAgainstOpponents ally-adjacency penalty would apply simultaneously. Since Proposal 4.8 already boosts deployment-phase tile desirability via `fDeploy`, adding an ally-stacking penalty on top during deployment could over-penalise clustering and cause units to spread too wide for effective mutual support. **Proposal 4.6 should be gated to phase 1+ only**, or its effect during phase 0 should be verified against the combined Deploy + Cover penalty to ensure spacing remains tactically reasonable.

The gating is simple: wrap the proposed ally-penalty extension in the existing phase check pattern:

```c
if (!IsDeploymentPhase(unit)) {
    // Apply the ally-adjacency stacking penalty (Proposal 4.6)
    total -= adjAllies * settings.occupiedDirectionPenalty;
}
```

---

## B. New Criterion Proposals (Behavior-Informed)

The following proposals were not possible at the time the original criterion document was written because they require knowledge of how behavior-layer scoring consumes criterion output. The behavior investigation provides that context.

---

### 4.9 Attack Tile Affinity — Weight Criterion Scores Toward Tiles That Enable Attacks

**Behavioural intent:** `Attack.OnEvaluate` reads movement scores from the tile dict and integrates them via `(1 - moveCostFraction)` — tiles that cost more AP to reach reduce the attack score. This means the attack score is highest for tiles the unit can reach cheaply. The criterion layer currently has no awareness of this relationship; `ThreatFromOpponents` scores tiles by spatial threat geometry, but does not know whether arriving at a high-threat tile leaves enough AP to fire.

The proposal adds a small AP-residual affinity term to `ThreatFromOpponents.Score (B)`. After computing the distance-falloff score for each tile in the spatial scan, it applies a multiplier based on how much AP would remain after moving there. Tiles that leave substantial AP — enough to fire — score modestly higher than tiles that exhaust the budget.

**Modification — `ThreatFromOpponents.Score (B)` (VA `0x18076B710`), inner tile scoring loop:**

```c
// After existing distance falloff and directional multipliers:
float moveCostFrac  = GetMoveCostToTile(tile, unit);          // ratio of AP cost to max AP
float apResidual    = max(1.0f - moveCostFrac, 0.0f);         // 1.0 = free move, 0.0 = full budget
float apAffinity    = 0.7f + apResidual * 0.3f;               // [0.7 at full cost → 1.0 at zero cost]
score              *= apAffinity;
```

**Rationale from behavior layer:** `Attack.OnEvaluate` applies `(1 - moveCostFraction)` as a multiplier on the attack score. If a tile is expensive to reach, the attack score is reduced at the behavior layer regardless of how well the criterion layer scored it. The criterion layer's ThreatFromOpponents score and the behavior layer's movement cost penalty are currently independent. This proposal aligns them: tiles that would have been penalised by the behavior layer anyway now score modestly lower at the criterion layer too, producing coherent tile preference rather than contradictory signals.

**Expected change:** Units preferentially seek threatening positions they can reach cheaply, rather than threatening positions that exhaust their AP. This does not override the spatial quality of a tile — a perfect flanking position that costs all AP still scores high — but cheap-to-reach threatening positions receive a systematic 30% uplift over equivalent expensive ones.

**Affected function:** `ThreatFromOpponents.Score (B)` — VA `0x18076B710`. No `AIWeightsTemplate` fields added. `GetMoveCostToTile` must be verified as available in this call context; `GetMoveRangeData` (VA `0x1806DF4E0`) is already used in `Criterion.Score` and provides `moveCostToTile` — check whether calling it from within `Score (B)` is structurally valid, as `Score (B)` is called from within the 4-thread worker pool.

**Risk:** Medium. The computation is lightweight. The main risk is the call context for `GetMoveRangeData` inside a threaded worker — confirm thread safety before adding this call. If the call cannot be made safely inside the worker, the affinity can be applied in `ThreatFromOpponents.Evaluate` post-hoc as a pass over the scored tile set.

**Prerequisite:** Confirm `GetMoveRangeData` thread safety in the 4-worker-thread context of `ThreatFromOpponents`. Behavior-layer `Attack.OnEvaluate` (VA `0x180735D20`) was fully analysed; cross-reference its `moveCostFraction` computation to ensure the criterion-layer approximation uses the same formula.

---

### 4.10 Co-Fire Position Preference — Boost Tiles Where Allies Have Line of Sight

**Behavioural intent:** `Attack.OnEvaluate` accumulates a co-fire bonus for each ally with LoS to the candidate target. This bonus is computed at behavior-layer scoring time — it does not influence which tile the unit moves to. The criterion layer has no concept of ally LoS. The result is a structural gap: the unit may be guided by criterion scoring to a tile with excellent cover and threat geometry, but from which no allies can co-fire, foregoing the co-fire bonus entirely.

The proposal adds an ally-LoS affinity pass to `ThreatFromOpponents.Score (B)`. After the existing spatial scan, each candidate tile receives a score increment proportional to the number of allies that have unobstructed LoS to the target from that tile — the same allies that `Attack.HasAllyLineOfSight` would count at behavior-layer evaluation time.

**Modification — `ThreatFromOpponents.Evaluate` (VA `0x18076ACB0`), post-Score(B) accumulation:**

Rather than modifying the threaded `Score (B)` inner loop, this pass runs after `ThreatFromOpponents.Evaluate` finishes its per-tile computation and before writing to `ctx.accumulatedScore`:

```c
// Post-scan pass: for each candidate tile, count allies with LoS to the opponent
int   allyLoSCount  = CountAlliesWithLoSToOpponent(tile, opponent, unit);   // mirrors Attack.HasAllyLineOfSight logic
float coFireAffinity = 1.0f + allyLoSCount * AIWeightsTemplate.ThreatFromOpponentsDamage * 0.05f;
// ThreatFromOpponentsDamage (+0x7C) is the confirmed co-fire base weight in the behavior layer
// 0.05 scales it to a modest per-tile affinity rather than a full bonus score
tileScore *= coFireAffinity;
```

**Rationale from behavior layer:** `Attack.HasAllyLineOfSight` (VA `0x180733890`) already implements the ally LoS check and respects the `strategyMode == 1` no-co-fire gate. The criterion layer can mirror this logic without duplicating it — the same function can be called from within `ThreatFromOpponents.Evaluate` since it is not inside the threaded worker.

**`AIWeightsTemplate` field reused:** `ThreatFromOpponentsDamage (+0x7C)` — the confirmed co-fire weight from the behavior layer. This makes the criterion-layer co-fire affinity proportional to the same constant the behavior layer uses for the actual co-fire bonus, keeping the two layers calibrated to the same designer intent.

**Expected change:** Units move to tiles from which their allies can also fire. Co-fire is currently a behavior-layer bonus for attacks made from wherever the unit happens to stand; with this proposal it becomes a positional preference that guides the Move decision. The 0.05 scale factor is intentionally small — co-fire affinity is a tiebreaker, not a dominant signal. A tile with superior cover and threat geometry but no ally LoS will still outscore a weaker tile with ally LoS in most cases.

**Risk:** Low-medium. `CountAlliesWithLoSToOpponent` mirrors existing behavior-layer logic. The main risk is that the function does not exist at the criterion layer and must be built inline — it is a spatial LoS check against the ally tile list, which is accessible via `movePool.zoneData.allyTileList` (confirmed). Do not call `Attack.HasAllyLineOfSight` directly from the criterion layer — it holds an `Attack` instance reference (`self`). Reimplement the LoS check as a standalone inline loop.

**Prerequisite:** Confirm `strategyMode` is readable from within `ThreatFromOpponents.Evaluate` context — it is accessed via `*(DAT_183981f50 + 0xb8)` which is a global singleton and is accessible everywhere.

---

### 4.11 Goal-Type Tile Separation — Differentiate Positioning by Behavior Goal Type

**Behavioural intent:** The behavior investigation confirms that `SkillBehavior.GetTargetValue (private)` assembles final scores differently based on `goalType`: `0` = attack (weights proximity heavily), `1` = assist-via-movement (weights kill potential), `2` = assist-via-skill (weights a static bonus term). The criterion layer has no awareness of goal type. Every unit, regardless of whether it is primarily an attacker, a support unit moving to assist, or a skill-assist unit, receives the same tile scoring from `ThreatFromOpponents`, `CoverAgainstOpponents`, and `DistanceToCurrentTile`.

The proposal introduces a `goalType` read into `DistanceToCurrentTile.Evaluate`. Support units (goalType 1 or 2) should prefer tiles that advance toward ally positions rather than toward enemies. The existing `reachabilityScore` computation can be reoriented by substituting the distance-to-enemy-tile reference with a distance-to-nearest-ally-tile reference when the unit's current goal type is non-attack.

**Modification — `DistanceToCurrentTile.Evaluate` (VA `0x180760CF0`):**

Current distance reference (reconstruction):
```c
dist = GetTileDistance(ctx.tileRef, unit.currentTile);
```

Proposed:
```c
int goalType = GetUnitGoalType(unit);   // read from agentContext or behaviorConfig — see note
Tile* reference = (goalType == 0)
                  ? unit.currentTile                          // attack: prefer distance from current pos
                  : GetNearestAllyTile(unit);                 // assist: prefer tiles near allies
dist = GetTileDistance(ctx.tileRef, reference);
```

**Note on `goalType` access:** `goalType` is stored on the `Goal` object referenced at `Attack +0x60`. From the criterion layer, the unit's active goal type is not directly accessible through a confirmed pointer chain. Two implementation paths exist:

- *Path A (preferred):* Read `goalType` from `ScoringContext.singleton` if it is stored there — this requires a targeted Ghidra analysis of `ScoringContext` to confirm. The singleton is accessible from the criterion layer.
- *Path B (fallback):* Infer goal type from existing criterion data. A unit with a non-empty `opponentList` and no ally targets is likely goalType 0. A unit with recent `WakeUp.Collect` activity (readable via `movePool.wakeupPending +0x51`) is clearly goalType 1. This is heuristic but does not require a new pointer chain.

**`GetNearestAllyTile` dependency:** The nearest ally tile is available via `movePool.zoneData.allyTileList` (confirmed) — iterate and keep minimum distance. This is a small loop, not a new function.

**Expected change:** Support units (healers, buff-givers, ammo suppliers) prefer tiles that advance toward their team rather than toward enemies. This is a structural alignment that the criterion layer currently cannot express — every unit is scored as if forward threat pressure is desirable, even for units whose actual role is ally-facing.

**Risk:** High. Goal type is not currently readable at the criterion layer from a confirmed pointer chain. Path A requires an additional Ghidra analysis. Path B is heuristic and may misclassify units in edge states. Do not implement until goal type access is confirmed. Flag as a Phase 2 proposal that requires the additional investigation.

**Prerequisite:** Analyse `ScoringContext` structure to determine if `goalType` is stored there. Alternatively, extract and analyse the `Goal` class and its relationship to the criterion evaluation context. This is the highest-dependency proposal in this document.

---

### 4.12 AP-Residual Tile Preference — Penalise Tiles Whose AP Cost Leaves Insufficient Reserve

**Behavioural intent:** The behavior investigation confirms `StrategyData.reservedAP (+0x118)` as the AP budget that `Attack.OnEvaluate` (Behavior Proposal 5.4) uses to penalise attacks that drain the unit. The criterion layer currently scores tiles without any awareness of AP cost relative to this reserve. A tile that takes 18 of 20 AP to reach scores the same as a tile that takes 4 AP, despite the fact that the behavior layer will penalise an attack from the 18-AP tile heavily.

The proposal adds a movement-cost awareness term to `DistanceToCurrentTile.Evaluate`. When a candidate tile's AP cost would reduce the unit's available AP below `reservedAP`, the tile's `reachabilityScore` is penalised. This aligns the criterion layer's tile preference with the behavior layer's AP-residual penalty before any attack scoring occurs.

**Modification — `DistanceToCurrentTile.Evaluate` (VA `0x180760CF0`):**

After the existing reachability computation:
```c
// Existing:
ctx.reachabilityScore += (float)dist × modScale × penalty;

// Appended:
float moveCostFrac  = GetMoveCostToTile(tile, unit);          // same as Proposal 4.9
float apAfterMove   = unit.movePool.maxMovePoints * (1.0f - moveCostFrac);
float reservedAP    = (float)strategyData->reservedAP;        // StrategyData +0x118 (confirmed)
if (apAfterMove < reservedAP && reservedAP > 0.0f) {
    float apDeficit = (reservedAP - apAfterMove) / reservedAP;   // [0, 1]
    ctx.reachabilityScore *= (1.0f - apDeficit * 0.4f);           // up to 40% reduction at full deficit
}
```

**`StrategyData` access from criterion layer:** `StrategyData` is accessed via `*(DAT_183981f50 + 0xb8)` → Strategy `+0x2B0` → StrategyData. This pointer chain is the same one used by `Behavior.GetUtilityThreshold` — it is a global singleton accessible from anywhere. The criterion layer can read `reservedAP` directly.

**Expected change:** Tiles that consume most or all of the unit's AP are modestly penalised at the criterion layer, reinforcing the behavior-layer penalty that would have fired anyway. The 40% maximum reduction is deliberately smaller than the behavior-layer's 40% penalty (from 1.0 to 0.6) — the criterion-layer penalty serves as an early signal, not a full suppression. The two penalties together produce a combined reduction of up to `0.6 × 0.6 = 0.36` of the original score for a unit with zero AP remaining after the move.

**Risk:** Low-medium. `StrategyData.reservedAP` is an `int` at a confirmed offset. The access path is identical to an existing confirmed access pattern. The main risk is that `moveCostFrac` is not readily available within `DistanceToCurrentTile.Evaluate` context — `GetMoveRangeData` may need to be called, and its thread-safety in this context should be confirmed (see Proposal 4.9 note). If unavailable, use `TileScore.apCost` (confirmed at `TileScore +0x40`) divided by `maxMovePoints` as an approximation.

**Prerequisite:** Confirm `GetMoveRangeData` availability in `DistanceToCurrentTile.Evaluate` call context, or confirm `TileScore.apCost` is already populated by the time `Evaluate` runs. Confirm `StrategyData` pointer chain is accessible from criterion namespace — it is global but verify no IL2CPP class-init guard blocks the access path.

---

### 4.13 Suppression Escape Routing — Bias Flee Accumulation When Unit Is Under Suppression

**Behavioural intent:** The behavior investigation reveals that `Buff.GetTargetValue` applies `buffType == 2` as a suppression-of-redundancy guard — reducing the weight of buffing an already-suppressed unit. This implies that suppressed units are known states that the AI system tracks. The criterion layer, however, has no awareness of whether the evaluating unit is currently suppressed. `FleeFromOpponents.Evaluate` accumulates the same escape pressure regardless.

A suppressed unit should flee more urgently and more directionally — it cannot fire back, so its optimal play is to escape LoS entirely rather than find cover. The proposal modifies `FleeFromOpponents.Evaluate` to check for active suppression and, when found, adds a directional component: tiles that break LoS to the suppressing enemy group score higher than tiles that merely increase distance.

**Modification — `FleeFromOpponents.Evaluate` (VA `0x1807613A0`):**

After the existing per-tile accumulation:
```c
// Existing:
if (group CAN target unit.team):
    fAccum += expf(settings.fleeWeight)   // standard flee

// Proposed extension (suppression case):
bool isSuppressed = CheckSuppression(unit);   // read suppression state — see note
if (isSuppressed) {
    // Additional pass: prefer tiles that break LoS to this group
    if (BreaksLoSToGroup(ctx.tileRef, group)):    // LoS check — tile vs group position
        fAccum += expf(settings.fleeWeight) * 0.5f;   // +50% on top of base flee for LoS-breaking tiles
    else:
        fAccum -= expf(settings.fleeWeight) * 0.2f;   // -20% for tiles that maintain LoS
}
```

**Suppression state access:** The `Buff.GetTargetValue` formula reads `buffType` from the target's buff data block. The evaluating unit's own suppression state should be readable from its `buffDataBlock (+0xC8)` — the same field confirmed in the behavior investigation. The exact flag or field within `buffDataBlock` that encodes `buffType == 2` (suppressed) must be confirmed; the `buffDataBlock +0x38 = stackCount` field from the behavior report is a candidate.

**`BreaksLoSToGroup`:** A LoS check from a candidate tile to a group position. This is a new geometric query at the criterion layer. The criterion layer already has tile position data (`ctx.tileRef`), and the group's position is available from the `avoidGroups` iteration. A simplified version — checking whether the candidate tile is behind the evaluating unit relative to the group — can be implemented using the existing `GetDirectionIndex` utility used in `CoverAgainstOpponents.Evaluate`.

**Expected change:** Suppressed units flee not just away from enemies in general but specifically toward tiles that break LoS to their suppressor. Tiles behind solid cover relative to the suppressing group score substantially higher than open tiles at the same distance. Non-suppressed units are entirely unaffected. This creates a qualitatively different escape pattern for suppressed units — they seek concealment, not just range.

**Risk:** Medium. Two new dependencies: suppression state access (requires confirmation against the buff data block fields) and a lightweight LoS approximation (can use the existing directional index system). Neither requires new Ghidra analysis if the confirmed field offsets are sufficient. Start with the directional approximation (`GetDirectionIndex` result compared against group direction) rather than a full raycast, and upgrade to a proper LoS check only if the approximation produces incorrect routing on complex terrain.

**Prerequisite:** Confirm which field in `buffDataBlock` encodes active suppression state for the evaluating unit. `Actor.buffDataBlock (+0xC8)` is confirmed; the suppression flag within it requires a targeted dump of the buff data block class or a Ghidra analysis of how `Buff.GetTargetValue` reads `buffType`.

---

## C. Cross-Layer Integration Proposals

The following proposals are not single-system modifications. Each describes a coordinated set of changes across both the criterion layer and the behavior layer that, together, produce a coherent emergent behavior archetype. The individual component changes are drawn from both proposal documents; this section specifies the exact combination and the expected compound behavior that neither document achieves alone.

Each integration proposal is described as a named archetype — a coherent behavioral mode for an AI unit type. Implementation means enabling the listed component proposals together, in the stated configuration, and verifying the compound result matches the described archetype.

---

### Integration I — Committed Aggressor Archetype

**Description:** A unit that consistently seeks forward positions, commits to decisive kills when available, and does not flee unless critically damaged. Suitable for heavily armoured assault units or elite melee attackers.

**Component proposals:**

| Layer | Proposal | Role in archetype |
|---|---|---|
| Criterion | 4.1 — Flatten Health Cliff | Eliminates the sniper-camp incentive; healthy units advance rather than hold extreme range |
| Criterion | 4.4 — Flanking Opportunism (multiplier `1.4×`, capped when at max range) | Drives movement toward flanking angles, not just forward pressure |
| Criterion | 4.5 — Melee Roam Aggression | When no targets are visible, unit moves toward enemy rather than standing still |
| Criterion | 4.9 — Attack Tile Affinity | Criterion layer prefers tiles where attacks can be made cheaply, reinforcing commitment |
| Behavior | 5.1 — Kill Confidence Bias | Commits decisively when a one-shot kill is available |
| Behavior | 5.4 — Low-AP Aggression Suppression (floor `0.75`, not `0.6`) | Softened version: unit is less deterred by AP cost because its role is to close and attack |

**Configuration note on 5.4:** The standard Behavior Proposal 5.4 proposes a floor of `0.6` for the AP-residual penalty. For the Aggressor archetype, raise this floor to `0.75` — the unit should still prefer AP-efficient attacks but not be as strongly deterred from committing its full AP budget.

**Expected compound behavior:** The unit advances toward flanking positions (4.4), never stalls when out of range (4.5), prefers tiles where it can attack without exhausting AP (4.9), commits to one-shot kills when present (5.1), and does not camp at maximum range when healthy (4.1). The result is a unit that closes ground, picks decisive fights, and only retreats when critically damaged (4.2 health-radius expansion only fires below 40% health, which is untouched by this archetype).

**Interaction to verify:** 4.1 + 4.4 was flagged in the original cross-proposal notes as potentially producing a `9.6×` score for a healthy flanking-edge unit. With the `1.4×` cap applied to 4.4 (not the full `1.6×`), the combined maximum is `6.0 × 1.4 = 8.4×` — marginally above the original `8×` maximum. Acceptable for an aggressor unit; verify against the `21474` behavior-layer ceiling after `MoveBaseScore` scaling.

---

### Integration II — Coordinated Fire Team Archetype

**Description:** A group of ranged units that prefer positions from which multiple team members can engage the same target simultaneously. Individual score is moderate; co-fire bonus is the primary scoring driver. Suitable for fire teams, suppression squads, or units with linked-fire mechanics.

**Component proposals:**

| Layer | Proposal | Role in archetype |
|---|---|---|
| Criterion | 4.6 — Cover Discipline (phase 1+ only, per Correction A.3) | Units spread to independent covered positions rather than clustering |
| Criterion | 4.10 — Co-Fire Position Preference | Criterion layer biases toward tiles from which allies can also fire |
| Criterion | 4.4 — Flanking Opportunism (`1.2×` — reduced from standard proposal) | Mild directional preference; flanking matters less than mutual LoS |
| Behavior | 5.3 — Co-Fire Coordination (super-linear ally count scaling) | Behavior layer strongly rewards positions where all three units can fire simultaneously |
| Behavior | 5.4 — Low-AP Aggression Suppression | Units do not waste AP on sub-optimal attacks; they wait for coordinated fire opportunities |

**Configuration note on 4.4:** For the Fire Team archetype, reduce the flanking multiplier from the standard `1.6×` to `1.2×`. This archetype values mutual LoS over individual flanking angles — a tile where two allies can co-fire is preferred over a tile with a perfect flanking angle that only one unit can exploit.

**Expected compound behavior:** Units spread to covered positions (4.6), prefer tiles where allies can also engage the target (4.10), and the behavior layer strongly amplifies the score when three units have simultaneous LoS (5.3). The super-linear co-fire scaling means a three-unit coordinated attack scores `1.7×` the base regardless of individual target quality — a mediocre target that all three can hit outscores an excellent target only one can reach. Units hold AP to wait for coordinated fire windows (5.4).

**Interaction to verify:** Proposals 4.10 and 5.3 both amplify co-fire opportunity. At the criterion layer, co-fire affinity is a tiebreaker (`0.05` scale factor). At the behavior layer, it is a super-linear bonus on the final score. These are additive in effect direction but applied to different scoring stages. The compound effect is: criterion layer moves the unit to a co-fire position, then behavior layer rewards the attack from that position. This is the intended two-stage coherence. The risk is that without any co-fire opportunity (all allies dead or out of range), the criterion layer still biases toward ally-LoS tiles, which may not be the best individual positions. Confirm that 4.10's `0.05` scale factor is small enough not to dominate individual positioning when co-fire is unavailable.

---

### Integration III — Suppression-Then-Advance Doctrine

**Description:** Units that prioritise suppressing enemies before advancing rather than advancing directly into fire. Suppression attacks are elevated when enemies are mobile; movement to flanking positions is deferred until enemy fire is reduced. Suitable for assault squads with mixed suppression and damage weapons.

**Component proposals:**

| Layer | Proposal | Role in archetype |
|---|---|---|
| Criterion | 4.4 — Flanking Opportunism | Forward position preference for eventual advance |
| Criterion | 4.13 — Suppression Escape Routing | Suppressed units flee directionally (breaks LoS), not just away |
| Criterion | 4.6 — Cover Discipline | Units occupy independent covered positions from which to suppress |
| Behavior | 5.2 — Suppression-First Doctrine | Suppression attacks score 1.3× against high-AP targets |
| Behavior | 5.4 — Low-AP Aggression Suppression | Units don't attack if they can't afford to suppress and advance |
| Behavior | 5.8 — Movement Commitment (narrowed marginal threshold) | Units that have suppressed their lane commit to advancing rather than hesitating |

**Execution sequence this archetype produces:**

1. Turn 1: Units move to covered independent positions (4.6 spreading). Suppression attacks score highly against mobile enemies (5.2). Cover positions acquired.
2. Turn 2: Enemy is suppressed (low AP). Suppression score drops (5.2 — low-AP penalty). Flanking advance becomes more attractive (4.4). Units commit to forward movement with narrowed hesitation window (5.8).
3. Turn 3+: Units at flanking positions execute damage attacks (4.4 + 5.1 kill confidence). Retreating suppressed enemies are routed directionally (4.13).

**Expected compound behavior:** This archetype produces the "suppress and advance" infantry tactic without any explicit sequencing logic — it emerges entirely from the scoring interactions. Suppression is more attractive when the enemy can shoot back (5.2 × AP fraction). Once the enemy is suppressed, the suppression score drops, and flanking advance becomes the dominant criterion-layer signal (4.4). Units commit to the advance rather than stalling (5.8).

**Interaction to verify:** 5.2 and 5.4 both reduce attack scoring in certain states. The risk is a turn where both penalties apply simultaneously — the unit has spent AP on suppression (low residual AP, triggering 5.4) and the enemy is already suppressed (low-AP target, triggering 5.2 downward, but wait — Proposal 5.2 reduces suppression score against low-AP targets, which means the unit would be guided away from suppression when it is expensive and the target is already pinned, which is correct). The interaction is self-regulating: when AP is low and the target is suppressed, both penalties push the unit toward movement rather than another suppression attack. This is the intended sequencing.

---

### Integration IV — Ammo Economy Doctrine

**Description:** Units that aggressively conserve ammo, prioritise high-value targets for limited shots, and withdraw to safe positions when ammo is depleted. Suitable for units with expensive or limited-supply munitions (artillery, special weapons, snipers with limited magazines).

**Component proposals:**

| Layer | Proposal | Role in archetype |
|---|---|---|
| Criterion | 4.7 — Ammo-Conscious Positioning | Flee accumulation scales up as ammo depletes; unit withdraws |
| Criterion | 4.2 — Flee/Avoid Radius Scale (health portion only — `fleeScale` driven by ammo ratio, not health) | Flee radius expands as ammo depletes rather than as health decreases |
| Criterion | 4.8 — Phase-0 Deploy Surge | Unit establishes strong position during deployment while fully loaded |
| Behavior | 5.5 — Ammo Discipline (AoE gate at < 25%) | AoE shots suppressed at low ammo unless target is exceptional |
| Behavior | 5.1 — Kill Confidence Bias | Remaining shots committed to confirmed kills, not marginal attacks |

**Configuration note on 4.2:** Proposal 4.2 in the original document scales flee radius by health ratio. For this archetype, substitute ammo ratio for health ratio in the `fleeScale` formula:

```c
// Standard 4.2 (health-scaled):
float fleeScale = 1.0f + max(0.4f - healthRatio, 0.0f) * 2.5f;

// Ammo-Economy variant:
float ammoRatio = (float)unit.currentAmmo / (float)max(unit.ammoSlotCount, 1);
float fleeScale = 1.0f + max(0.4f - ammoRatio, 0.0f) * 2.5f;   // same curve, driven by ammo
```

This variant can coexist with the health-driven version by taking the maximum of the two scale factors, or can replace it entirely for this archetype.

**Expected compound behavior:** During deployment (phase 0), the unit aggressively seeks the best firing position (4.8). While well-loaded, it attacks at maximum confidence and does not withdraw (4.7 inactive, 5.5 inactive). As ammo depletes below 40%: flee radius begins expanding (4.2 ammo variant), withdrawal pressure mounts (4.7). Below 25% ammo: AoE attacks suppressed (5.5), remaining shots committed only to confirmed kills (5.1). Below 10% ammo: flee accumulation is high enough to suppress most attack-tile scores; the unit prioritises withdrawal to a resupply position or protected tile.

**Interaction to verify:** 4.7 + 4.2 (ammo variant) compound flee accumulation. As noted in the original cross-proposal section, the two proposals are multiplicatively compounding. For a unit at 10% ammo: `fleeScale ≈ 1.75` (expanded radius) and `adjustedWeight ≈ fleeWeight + 0.72` (amplified per-tile). The combined flee accumulation is approximately `1.75 × 1.75 ≈ 3.0×` the baseline for every tile in the expanded radius. This is the intended extreme withdrawal pressure for a nearly empty unit, but verify it does not produce a frozen state where all tiles score equally badly due to total flee domination.

---

### Integration V — Defensive Anchor Archetype

**Description:** A unit that secures and holds a zone position, spreads allied units around it for mutual cover, refuses to abandon the zone even under pressure, and only retreats when critically damaged. Suitable for heavy weapon emplacements, zone-control specialists, or objective-holding infantry.

**Component proposals:**

| Layer | Proposal | Role in archetype |
|---|---|---|
| Criterion | 4.3 — Zone Threshold Cap (conservative — cap at `750`, not `500`) | Zone tiles remain strongly preferred but the unit can be pushed off truly untenable positions |
| Criterion | 4.6 — Cover Discipline | Allies spread around the anchor position rather than clustering on it |
| Criterion | 4.2 — Flee/Avoid Radius Scale (inverted — *reduce* flee scale for this unit type) | Anchor units hold ground; flee radius is compressed rather than expanded for low health |
| Behavior | 5.6 — Buff Priority Rebalance (setup emphasis) | Buff units supporting the anchor prioritise deploying weapon stances |
| Behavior | 5.9 — Aggressive Utility Decay (disabled or very slow decay rate for this unit) | Anchor units should not drift from their position due to idle-turn decay |
| Behavior | 5.10 — Deploy Spread Enforcement (quadratic penalty) | Allied units deploy spread around the anchor, not on top of it |

**Configuration note on 4.2 (inverted):** Proposal 4.2 in the original document is designed to make damaged units flee more aggressively. The Anchor archetype inverts this: the flee radius should be *compressed* as health decreases (or at minimum, not expanded). For this archetype, set `fleeScale` to a fixed `0.8` regardless of health — the unit always operates with a contracted avoidance footprint, accepting greater risk to hold its position:

```c
// Anchor variant — compressed flee radius regardless of health:
float fleeScale    = 0.8f;    // constant contraction
int   effectiveRad = (int)(16.0f * fleeScale);   // 12 tiles instead of 16
```

**Configuration note on 5.9 (slow decay):** The utility decay in Behavior Proposal 5.9 is `8% per idle turn`. For an anchor unit, this should be reduced to `2% per idle turn` with the same `0.5` floor — the unit is expected to remain in position for extended periods; the decay should only fire for truly unreasonable idle durations (>25 turns).

**Expected compound behavior:** The anchor unit takes a zone position during deployment (4.8 from the original proposals drives it forward in phase 0). It holds that position strongly (4.3 at conservative cap, 4.2 inverted). Allied units spread around it (4.6 + 5.10). Buff units deploy stances on the anchor and its neighbours (5.6). The anchor does not drift under mild idle pressure (5.9 slow decay). It only yields its position if the zone tile becomes genuinely indefensible — meaning its cover score after the Proposal 4.3 cap is applied falls below the utility threshold even with the zone bonus, which only occurs when the tile has zero cover, is occupied by an enemy, and multiple allied units are stacking on it simultaneously.

**Interaction to verify:** 4.3 (cap at 750) + 4.6 (cover discipline ally penalty) on the anchor tile itself. The anchor unit evaluates its own current tile on subsequent turns. If the anchor tile is now surrounded by allies (deployed around it per 4.6 and 5.10), the ally-adjacency penalty in 4.6 will apply and reduce the anchor tile's score. Combined with the reduced threshold bypass (750 vs 9999), this could cause the anchor to abandon its own position. Gate the ally-adjacency penalty in 4.6 so that it does not apply when `tile == unit.currentTile` (the unit is already on the tile — it should not be penalised for being at its own position).

---

## D. Revised Implementation Priority Matrix (Full Set)

The following table consolidates the original eight criterion proposals, the five new behavior-informed criterion proposals, and places both in context of the five integration archetypes. Priorities reflect implementation order given cross-proposal dependencies.

**Tier 1 — No prerequisites, no cross-proposal risk. Implement first.**

| Proposal | Change type | Risk | Notes |
|---|---|---|---|
| 4.8 — Phase-0 Deploy Surge | Code literal | Low | Original priority 1. No dependencies. |
| 4.5 — Melee Roam Aggression | Code patch | Low | Original priority 2. |
| 5.6 — Buff Priority Rebalance (Behavior) | Weight fields only | Low | Behavior Tier 1. No code changes. |
| 5.8 — Movement Commitment (Behavior) | Weight + 1 literal | Low | Behavior Tier 1. |

**Tier 2 — Single prerequisite or minor cross-proposal validation required.**

| Proposal | Prerequisite | Risk |
|---|---|---|
| 4.7 — Ammo-Conscious Flee | P3 (expf convention confirmed) | Low |
| 4.12 — AP-Residual Tile Preference | `GetMoveRangeData` call context; StrategyData pointer | Low–Med |
| 5.4 — Low-AP Suppression (Behavior) | Actor AP offset from dump.cs | Low |
| 5.5 — Ammo Discipline (Behavior) | P3 + runtime value of `+0xFC` | Low–Med |
| 5.10 — Deploy Spread (Behavior) | NQ-48 (`Actor +0x50`) | Low–Med |
| 4.1 — Flatten Health Cliff | None (add clamp guard) | Med |

**Tier 3 — Multiple prerequisites or interaction validation required.**

| Proposal | Prerequisite | Risk |
|---|---|---|
| 4.4 — Flanking Opportunism | 4.1 joint test for score ceiling | Low–Med |
| 4.9 — Attack Tile Affinity | `GetMoveRangeData` thread safety | Med |
| 4.10 — Co-Fire Position Preference | `strategyMode` access, ally LoS inline | Low–Med |
| 5.3 — Co-Fire Coordination (Behavior) | P3 (`+0x7C` value), NQ-16 | Med |
| 5.1 — Kill Confidence Bias (Behavior) | P1 (NQ-37) | Med |
| 4.6 — Cover Discipline (with A.3 phase gate) | P2, apply phase-1 gate per Correction A.3 | Med |
| 4.2 — Flee/Avoid Radius Scale | P3, radius cost profiling | Med–High |
| 4.13 — Suppression Escape Routing | Suppression flag in buffDataBlock | Med |

**Tier 4 — High dependency. Implement after all prerequisites are resolved.**

| Proposal | Prerequisite | Risk |
|---|---|---|
| 4.3 — Zone Threshold Cap | P1, runtime values of `+0x68`/`+0x6c` | High |
| 5.7 — Designation Urgency (Behavior) | P2 (NQ-42) | Med |
| 4.11 — Goal-Type Tile Separation | ScoringContext goalType access investigation | High |

**Integration archetypes (implement after component proposals are validated individually):**

| Archetype | Minimum component proposals required | Notes |
|---|---|---|
| I — Committed Aggressor | 4.1, 4.4, 4.5, 4.9, 5.1, 5.4 | 4.1 + 4.4 joint test mandatory first |
| II — Coordinated Fire Team | 4.6, 4.10, 4.4 (reduced), 5.3, 5.4 | 4.10 + 5.3 compound test mandatory |
| III — Suppression-Then-Advance | 4.4, 4.13, 4.6, 5.2, 5.4, 5.8 | 5.2 + 5.4 self-regulation test first |
| IV — Ammo Economy | 4.7, 4.2 (ammo variant), 4.8, 5.5, 5.1 | 4.7 + 4.2 compound flee ceiling check mandatory |
| V — Defensive Anchor | 4.3, 4.6 (with self-tile gate), 4.2 (inverted), 5.6, 5.9 (slow), 5.10 | 4.3 + 4.6 self-tile interaction must be gated |

---

## E. Revised Open Questions Before Implementation

This section supersedes Open Questions 1–8 in the original criterion proposals document. Items 1–6 are carried forward with updates; items 7–13 are new, arising from the behavior investigation and the new proposals in this addendum.

**1. Resolve `AIWeightsTemplate +0x7c` offset conflict.** *(Original P1 — unchanged.)* Required before any write in `+0x78`–`+0x84`. Blocks: Proposal 4.3.

**2. Confirm runtime values of `COVER_PENALTIES[4]`.** *(Original P2 — unchanged.)* Blocks: Proposal 4.6 calibration.

**3. Confirm `expf` argument convention.** *(Original P3 — confirmed by investigation. No action required; implementers must apply exponential sizing as documented.)*

**4. Analyse `ConsiderSurroundings.Evaluate`.** *(Original Q4 — unchanged.)* VA `0x18075C240`. Until known, Proposal 4.11 (goal-type separation) cannot be fully assessed for interaction with this criterion.

**5. Analyse `ConsiderZones.Collect`.** *(Original Q5 — unchanged.)* VA `0x18075C630`. Batch with Q4.

**6. Confirm runtime values of `zoneThresholdWeight_A/B` (`+0x68`, `+0x6c`).** *(Original Q6 — unchanged.)* Required before Proposal 4.3 implementation.

**7. *(Original Q7 — CLOSED by behavior investigation.)*** The behavior selection layer is now fully understood. `Criterion.Score` output feeds `TileScore` fields which are consumed by `Move.OnEvaluate`, `Attack.OnEvaluate`, and `Deploy.OnCollect`. No separate zone override exists at the behavior layer. No action required.

**8. Confirm `GetMoveRangeData` (VA `0x1806DF4E0`) thread safety inside `ThreatFromOpponents` 4-worker context.** Blocks: Proposal 4.9. If not thread-safe, apply AP affinity in `ThreatFromOpponents.Evaluate` post-scan instead.

**9. Confirm `TileScore.apCost (+0x40)` is populated before `DistanceToCurrentTile.Evaluate` runs.** Blocks: Proposal 4.12 fallback path. `apCost` is at a confirmed offset in `TileScore`; the question is whether the tile dict population sequence writes AP cost before or after `Evaluate` is called.

**10. Confirm suppression state field within `Actor.buffDataBlock (+0xC8)`.** Blocks: Proposal 4.13. The field at `buffDataBlock +0x38 = stackCount` (confirmed) may encode suppression stack depth, but the exact flag encoding is unknown. Memory-dump `buffDataBlock` on a suppressed unit at runtime, or analyse the suppression application path in the `Buff` behavior.

**11. Confirm `goalType` readability at the criterion layer.** Blocks: Proposal 4.11. Analyse `ScoringContext` (singleton at `DAT_183981F50 +0xb8`) for a `goalType` or active behavior identifier field. If absent, analyse the `Goal` class referenced at `Attack +0x60` and determine whether it is accessible through the criterion layer's available pointers.

**12. Confirm `strategyMode` read path from within criterion namespace.** Blocks: Proposal 4.10. `Strategy` is accessed via `*(DAT_183981f50 + 0xb8)`. The criterion namespace accesses this pointer chain via `ScoringContext`. Verify the two access paths reach the same object and that `Strategy.strategyMode (+0x8C)` — currently inferred (NQ-16) — is confirmed before using it as a co-fire gate in the criterion layer.

**13. Resolve `Correction A.2` compound effect on `Move.m_Score`.** Before modifying any of `W_attack`, `W_ammo`, `W_deploy`, `W_sniper`, compute the compound propagation through `MoveScoreMult (+0x12C)` and `MoveBaseScore (+0x128)` at their current runtime values. The criterion-layer weight change and the behavior-layer scaling are multiplicative stages. Confirm that doubling any master weight does not produce `Move.m_Score > 21474` under maximum tile score conditions.
