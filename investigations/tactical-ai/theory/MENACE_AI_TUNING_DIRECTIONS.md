# Menace — AI Tuning Directions

**Scope:** AIWeightsTemplate data tuning, and code-level intervention points for tile scoring and behavior scoring. Focused on improving collaborative AI behaviour. All field offsets and VA addresses reference the Unified Investigation Report.

Here be Dragons! But, no, seriously, this is largely AI speculation and prone to hallucinations. Take nothing said here as gospel. This is more of a thought experiment.

---

## Table of Contents

1. How This System Responds to Tuning
2. AIWeightsTemplate — Tuning Directions
   - 2.1 Collaboration-Relevant Fields
   - 2.2 Aggression vs Caution Balance
   - 2.3 Reactive Behaviour (Suppression, Stun, Threat Response)
   - 2.4 Deployment Phase Cohesion
   - 2.5 Known Hazards and Coupled Parameters
3. Code-Level Intervention Points
   - 3.1 Tile Scoring Layer
   - 3.2 Behavior Scoring Layer
4. Prioritised Recommendations

---

## 1. How This System Responds to Tuning

Before touching any value, two structural properties of this system must be understood.

**Exponents shape the distribution, not just the magnitude.** Several `AIWeightsTemplate` fields — particularly `UtilityPOW`, `SafetyPOW`, their Post variants, and the `*POW` fields in the threat/opportunity cluster — are exponents applied inside `powf()` calls. A linear weight changes how much something matters. An exponent changes *how sharply* the AI differentiates between good and marginal options. A `UtilityPOW` of 1.0 gives a shallow distribution where many tiles look similar; a value of 2.0 creates a steeper curve where the best tile is much more decisively preferred over second-best. This affects decision confidence, not just raw scores.

**`expf` fields are exponents, not linear weights.** `AvoidAlliesPOW (+0xB0)`, `AvoidOpponentsPOW (+0xB4)`, and `FleeFromOpponentsPOW (+0xB8)` are passed directly to `expf()`. Doubling these values does not double the effect — it squares the base. Small adjustments here have large consequences. Treat these as logarithmic controls.

**`DistanceScale` is coupled.** It appears twice: as the distance penalty coefficient in `GetScore()` and as the final negation multiplier on `SafetyScore` in `PostProcessTileScores()`. Raising it simultaneously increases movement conservatism and threat sensitivity. There is no way to separate these two effects using only data tuning — they require a code-level fix to decouple.

---

## 2. AIWeightsTemplate — Tuning Directions

### 2.1 Collaboration-Relevant Fields

These are the highest-leverage fields for making the AI behave more as a coordinated squad rather than a collection of independent actors.

---

#### `AllyMetascoreAgainstThreshold` (`+0xAC`, range 0–100)

**What it does:** Controls how much ally scoring pressure (the "metascore" of nearby ally attack opportunities) factors into threshold decisions. A higher value means a unit will more readily delay its own action when nearby allies are in a stronger position to act instead.

**Tuning direction for collaboration:** This is the cleanest lever for cooperative sequencing. Raising it causes units to more often yield initiative to better-positioned allies rather than taking a marginal action themselves. Start with increments of 10–15 and observe whether units begin forming effective firing sequences rather than all acting independently in the same turn.

**Risk:** Too high, and units become passive — perpetually deferring to allies and acting late in situations where they should press independently. Pair any increase here with a corresponding check on `UtilityThreshold` to ensure the base activation gate is not so low that deferral becomes the default state.

---

#### `ScalePositionWithTags` (`+0xBC`, range 0–10)

**What it does:** Controls how strongly weapon-type tag effectiveness (the `TagEffectivenessTable` multiplier) influences targeting value when units are choosing which targets to prioritise. It scales the bonus from `TagEffectivenessTable[tagIndex] × ScalePositionWithTags + 1.0`. Importantly, this weight is **replaced with 1.0 when `_forImmediateUse == true`** — meaning it only applies during planning-ahead scoring, not execution scoring.

**Tuning direction for collaboration:** Tag matching is the mechanism by which units specialise in attacking certain enemy types. Raising this value makes the AI more strongly route specific attack skills toward the enemies those skills are most effective against, leaving other targets for allies better suited to them. This produces role-differentiation without code changes — the spotter designates, the heavy damages, the suppressor pins.

**Practical note:** Changes here only affect future-positioning scoring (planning mode). During immediate execution, the AI falls back to `1.0`. This is deliberate — when a unit is about to fire, target availability matters more than ideal matchup.

---

#### `IncludeAttacksAgainstAllOpponentsMult` (`+0xC0`, range 0–10)

**What it does:** Multiplier on whether the AI includes attacks against opponents outside its primary focus when evaluating its attack opportunities. A higher value broadens target consideration; a lower value focuses fire.

**Tuning direction for collaboration:** Lowering this below the default forces the AI toward target focus — if one opponent is already being attacked by an ally, other units are less likely to pile onto the same target and more likely to distribute fire. This directly reduces the "everyone attacks the same unit" anti-pattern that makes the AI feel uncoordinated, wasting potential by overkilling one target while leaving threats unchecked.

---

#### `FriendlyFirePenalty` (`+0x100`, range 0–50)

**What it does:** Penalty multiplier applied in `Attack.OnEvaluate` when a shot candidate's target is a friendly tile. It discounts the score for any shot that has friendly-fire risk.

**Tuning direction for collaboration:** The current range suggests this can be raised substantially. In a squad that is expected to manoeuvre together, friendly-fire risk is a hard constraint on attack geometry — an AI with a high penalty here will naturally avoid attack lines that cross ally positions, producing cleaner separation of fire lanes. The side effect is that units may hold fire longer in close-quarters situations, which reads as caution rather than aggression. Both are plausible outcomes for a well-coordinated squad.

---

#### `DistanceToAlliesScore` (`+0xD0`, range 0–50) — Deployment only

**What it does:** The per-tile penalty in `Deploy.OnCollect` for each set-up ally within 6 tiles: `rangeScore -= (6 - distance) × DistanceToAlliesScore`. Only set-up allies trigger it.

**Tuning direction for collaboration:** This is the primary control for deployment cohesion vs. spread. A low value clusters units together; a high value spreads them. For collaborative play the ideal is spread enough to avoid AoE vulnerability but close enough to support each other — which sits somewhere in the mid-range. The 6-tile falloff radius is hardcoded; only the penalty magnitude is tunable here.

**Interaction with `CoverInEachDirectionBonus` (`+0xD4`):** The cover bonus competes with the spacing penalty. If cover is strongly concentrated in one area, units may cluster there despite the spacing penalty. If you want spread plus cover priority simultaneously, you need to either lower `DistanceToAlliesScore` or raise `CoverInEachDirectionBonus` depending on which constraint should dominate.

---

#### `CullTilesDistances` (`+0xC8`, range 0–99, int)

**What it does:** The search radius for the ally count check in `Attack.OnCollect`. If 3+ allies are found within this range, the tile search radius for attack candidates expands. This is the only automatic scaling of the attack geometry search based on unit density.

**Tuning direction for collaboration:** This field implicitly determines how aware an attacking unit is of its squad context. A larger value means more allies are counted before the radius expansion triggers, which in dense-squad situations means the AI sees more attack options from more positions. Raising it gives the AI a wider awareness of coordinated attack opportunities but increases evaluation cost. Lowering it makes the radius expansion trigger only for units that are very close — a more local-first approach.

---

### 2.2 Aggression vs Caution Balance

These fields govern whether the AI presses forward or holds — a balance that strongly affects how collaborative the squad reads in play.

---

#### `UtilityThreshold` (`+0x13C`, range 0–100)

**What it does:** The base activation threshold. A behavior must score above this (after strategy modifiers `multA` and `multB` are applied) to be selected. Below threshold, the behavior is filtered out regardless of its score.

**Tuning direction:** This is the primary aggression gate. Lower values make the AI take more actions it is uncertain about; higher values cause it to hold unless confident. For collaborative play, a slightly raised threshold is usually better — it means units wait for genuinely good opportunities rather than burning AP on marginal attacks, which preserves action economy for coordinated moments.

**Coupled to strategy:** The `StrategyData.modifiers.thresholdMultA` and `multB` fields can raise or lower the threshold per-strategy. If the intention is to create strategy archetypes (aggressive vs. defensive factions), those are the right levers to differentiate factions rather than modifying the base threshold.

---

#### `MoveIfNewTileIsBetterBy` (`+0x150`, range 0–10)

**What it does:** The minimum score improvement required before the AI will voluntarily move. If the best tile is not more than this margin better than the current tile, movement is rejected and the marginal-move penalty (×0.25 on `fWeight`) is applied instead.

**Tuning direction for collaboration:** Raising this value reduces unnecessary repositioning. Units that move only when it clearly matters are more predictable to play around as a player and are less likely to vacate positions that were strategically sound for the squad even if marginally suboptimal individually. A higher value here produces units that commit to positions — the squad reads as deliberate and coordinated rather than jittery.

---

#### `DistanceToCurrentTile` (`+0x54`, range 0–50)

**What it does:** Weight on the AP cost to reach a tile in `Criterion.Score`. Higher values penalise distant tiles more strongly, keeping units close to their current position. Lower values make distance a weaker factor, allowing the AI to consider far-away tiles more freely.

**Tuning direction for collaboration:** This is a reach-vs-commitment dial. High values make units defensive and conservative about movement range. Low values let them roam. For a squad that should support each other, this is best kept moderate — low enough that units will move to support an ally under pressure, high enough that they don't chase every marginal opportunity across the map.

---

#### `EntirePathScoreContribution` (`+0x14C`, range 0–1)

**What it does:** How much the quality of the entire movement path (not just the destination tile) contributes to the movement score. A value near 1.0 means the AI cares about path safety; near 0 means only the destination matters.

**Tuning direction for collaboration:** Raising this makes units take safer routes to their destinations even if those routes are longer. The practical effect is that units avoid moving through exposed positions in transit — which reduces unnecessary casualties and keeps units in fight-ready condition longer. For a coordinated squad, this is desirable.

---

### 2.3 Reactive Behaviour (Suppression, Stun, Threat Response)

These fields govern how strongly the AI responds to player-inflicted status effects and threat conditions on its allies.

---

#### Buff behavior multipliers: `RemoveSuppressionMult` (`+0x17C`), `RemoveStunnedMult` (`+0x180`), `RestoreMoraleMult` (`+0x184`)

**What they do:** Multipliers in `Buff.GetTargetValue` for the respective status-removal branches. A suppressed/stunned/demoralised ally scores higher as a Buff target when these values are raised.

**Tuning direction for collaboration:** These are the primary levers for making support units respond quickly to negative status effects inflicted by the player. If the player frequently uses suppression as a tactic, raising `RemoveSuppressionMult` will make support units actively prioritise clearing that suppression rather than scoring it equally with other buff opportunities. This creates a felt responsiveness — the AI squad visibly reacts to what the player does to it. Consider raising these significantly (toward the top of the 0–10 range) if you want a reactive support-feels-intentional quality.

**Note on the `buffType == 2` guard:** When `buffType == 2` (already-suppressed state), the Suppress branch applies a ×0.9 reduction and the Status Buff branch applies ×0.1. This prevents double-scoring for units already debuffed. This is correct behaviour and should not be altered without revisiting the full branch logic.

---

#### Threat sensitivity: `ThreatFromOpponentsDamage` (`+0x7C`), `ThreatFromOpponentsSuppression` (`+0x84`), `ThreatFromOpponentsStun` (`+0x88`)

**What they do:** Per-threat-type multipliers applied in `ThreatFromOpponents.Score (A)` during the post-loop multiplier phase. They scale the threat contribution from enemies capable of dealing damage, suppression, or stun respectively.

**Tuning direction for collaboration:** Differentiating these by threat type allows the AI to respond differently to different player weapons. If the player uses a lot of suppression weapons, raising `ThreatFromOpponentsSuppression` makes the AI prioritise repositioning away from those weapons' fields of fire more aggressively. The result is an AI that reads the player's loadout and adjusts spacing accordingly — a behaviour that reads as intelligent even if its origin is purely mechanical.

---

#### `ThreatFromPinnedDownOpponents` (`+0x8C`), `ThreatFromSuppressedOpponents` (`+0x90`)

**What they do:** Threat multipliers applied when the opponent delivering the threat is themselves pinned or suppressed.

**Tuning direction for collaboration:** These create an opportunity-reading behaviour. When player units are suppressed, lowering the threat from those units (`ThreatFromSuppressedOpponents` toward 0) makes the AI more willing to advance and press its advantage. Raising them keeps the AI cautious even against suppressed enemies. For collaborative, tactically coherent play, lowering these is preferable — a squad that presses when the enemy is suppressed reads as coordinated and smart.

---

#### `ThreatFromOpponentsAtHypotheticalPositionsMult` (`+0xA4`, range 0–5)

**What it does:** Scales threat contribution from enemies evaluated at hypothetical (predicted future) positions rather than current positions. This is the forward-planning component of threat assessment.

**Tuning direction for collaboration:** This is one of the more interesting fields. Raising it makes the AI consider where enemies *will be* rather than just where they are, which produces pre-emptive repositioning rather than purely reactive movement. For a squad AI, this is valuable — units that move to block predicted enemy advances rather than waiting to be flanked read as proactive and coordinated. However, if hypothetical positioning data is not reliable (open question on how positions are predicted), this can produce false-threat responses. Raise cautiously and observe whether the resulting movement looks intelligent or erratic.

---

### 2.4 Deployment Phase Cohesion

The deployment phase is where initial squad formation is established. Getting this right has downstream effects on the entire combat phase.

---

#### `DistanceToZoneDeployScore` (`+0xCC`, range 0–50)

**What it does:** Penalty in `Deploy.OnCollect` for distance from the deployment zone center: `rangeScore -= DistanceToZoneDeployScore × distanceResult × tileScore.secondaryMovementScore`. Keeps units from deploying too far from the intended zone.

**Tuning direction for collaboration:** This constrains how far from the strategic objective the AI will deploy. Higher values produce tighter clustering around the objective; lower values allow flexible positioning. For cohesive squad formation, this should be high enough to keep the squad in mutual support range of the objective, but not so high that it clusters units into AoE vulnerability.

---

#### `InsideBuildingDuringDeployment` (`+0xD8`, range 0–500)

**What it does:** Bonus score for deploying inside a building. The large range suggests this is a strong positional preference signal.

**Tuning direction for collaboration:** If buildings are the natural anchor points for squad formation, raising this bonus ensures the AI consistently occupies them during deployment — establishing clear rally points. This creates predictable initial formations that are easier to reason about when designing encounters.

---

#### `DeploymentConcealmentMult` (`+0xDC`, range 0–100)

**What it does:** Multiplier for concealment quality during deployment tile selection.

**Tuning direction for collaboration:** In conjunction with `CoverInEachDirectionBonus`, this determines how defensively the AI sets up. A high value here produces a squad that deploys into concealed positions first, revealing itself only when it chooses to act. This is realistic and collaborative — units don't advertise their positions to the player unnecessarily.

---

### 2.5 Known Hazards and Coupled Parameters

The following interactions are dangerous to modify without understanding both sides:

**`DistanceScale` (`+0x40`) — do not raise without a code-level fix.** It controls both distance penalty magnitude and SafetyScore negation strength. Raising it to make the AI more threat-sensitive also makes it more conservative about movement. These two effects cannot be separated with data tuning alone.

**`UtilityPOW` + `UtilityPostPOW` — paired exponents.** These shape the utility score distribution. Changing one without adjusting the other can produce unexpectedly flat or sharp score curves. If raising `UtilityPOW`, consider slightly lowering `UtilityPostPOW` to compensate, or test both together.

**`AvoidAlliesPOW` (`+0xB0`) — expf input.** This is an exponent to `expf()` in `AvoidOpponents.Evaluate`. Because of the exponential relationship, what looks like a modest value (e.g. 2.0 → 3.0) produces a non-linear jump in the avoidance pressure. Do not iterate this in large steps.

**Score ceiling (`21474`) and floor (`5`).** The behavior score floor of `5` means any behavior that returns a positive score is treated as viable. The ceiling of `21474` means no behavior, regardless of how good it is, can dominate beyond this value. Deploy's hardcoded `1000` sits comfortably below the ceiling but above typical combat scores — if a combat behavior begins returning scores consistently above `1000`, it will override Deploy, which may be unintentional. Monitor behavior score distributions if raising base score multipliers substantially.

---

## 3. Code-Level Intervention Points

Data tuning is limited by the structure of the scoring formulas. The following are the most impactful places where code changes (or targeted patches) would unlock collaborative behaviours that are structurally impossible to achieve through `AIWeightsTemplate` alone.

### 3.1 Tile Scoring Layer

---

#### Intervention A — Decouple `DistanceScale` from `SafetyScore` negation

**Current behaviour:** `DistanceScale` (`+0x40`) is used in two places: as the coefficient in `GetScore()` and as the negation multiplier in `PostProcessTileScores()`. These are coupled.

**Where:** `Agent.PostProcessTileScores()` at VA `0x18071C450`. The SafetyScore negation is the line:
```c
ts.SafetyScore = −ts.SafetyScore × DistanceScale;
```

**Change:** Introduce a separate `AIWeightsTemplate` field — call it `SafetyNegationScale` — and substitute it here. This allows threat sensitivity and distance conservatism to be tuned independently. Without this change, making the AI more sensitive to threats also makes it more reluctant to move, which is often the wrong tradeoff in collaborative scenarios where units should be willing to reposition to support allies.

---

#### Intervention B — Add an ally proximity bonus to tile scoring

**Current gap:** The tile scoring layer (all 11 Criterions) evaluates each tile entirely from the perspective of the evaluating unit. There is no criterion that scores a tile higher because it keeps the unit in close proximity to allies. `AvoidOpponents` penalises tiles near enemies; there is no complementary bonus for tiles near allies. The `DistanceToAlliesScore` in Deploy is only active during deployment — it disappears in the combat phase, and it is a penalty (for being too close) rather than a bonus (for being within support range).

**Where to add:** A new `Criterion` subclass, or a modification to an existing criterion. The cleanest insertion point is as an additional component in `Criterion.Score` alongside the existing four components (attack, ammo, deploy, sniper). Alternatively, it can be a new sixth criterion evaluated during Pass 1.

**What to compute:**
```
// For each ally in unit.zoneData.allyTileList:
//   dist = distance from candidate tile to ally.tile
//   if dist > supportRangeMax: skip
//   score += (1.0 - dist / supportRangeMax) × allyProximityWeight
//   if ally.isSupprressed or ally.hasNegativeStatus: score += allyInNeedBonus
ctx.accumulatedScore += allyProximityScore
```

Two new `AIWeightsTemplate` floats would control this: `AllyProximityWeight` (the base value per nearby ally) and `AllyInNeedBonus` (an extra kick when the ally has negative status — suppressed, stunned, low HP). The second bonus directly produces "rush to support" behaviour in response to player-inflicted status effects.

---

#### Intervention C — Make `ThreatFromOpponents` threat awareness team-level, not unit-level

**Current behaviour:** `ThreatFromOpponents.Score (B)` scans from each opponent's position outward and scores candidate tiles based on their individual position relative to that opponent. Each unit evaluates this independently, so multiple units may converge on the same "safe" positions near enemies, creating accidental clustering rather than coordinated formation.

**Where:** `ThreatFromOpponents.Score (B)` at VA `0x18076B710`. The spatial scan loop.

**Change:** After computing the per-tile threat score, subtract a discount proportional to how many other AI units have already rated the same tile highly in their evaluations. This is a shared tile desirability budget: the more AI units who "want" to move to the same cover tile, the less each individual unit values it. The effect is natural spread — units independently arrive at non-overlapping positions rather than clustering into the same cover.

**Implementation note:** This requires a shared data structure that all agents write into during evaluation. Given that `Agent.Evaluate()` already uses a double-buffer swap (`m_Tiles → m_TilesToBeUsed`), one approach is a shared `Dictionary<Tile, int>` counting how many agents rated a tile above a threshold in the previous evaluation cycle. This is read-only during scoring and updated at the end of each cycle. No thread synchronisation is required if reads are per-agent and the write is centralised at cycle end.

---

#### Intervention D — Zone-flag-based rally point injection

**Current behaviour:** `ConsiderZones.Evaluate` uses the zone flag bitmask (`0x01` for membership, `0x04` for team-ownership, etc.) to unconditionally promote tiles in owned zones. There is no mechanism to designate a specific tile as a rally point that all units should converge on contextually — for instance, when a flank is threatened.

**Where:** `ConsiderZones.Evaluate` at VA `0x18075CC20` and `ConsiderZones.PostProcess` at VA `0x18075D3B0`.

**Change:** Add a new zone flag bit (e.g. `0x40`) for "active rally." When the game detects that a flank or position is under player pressure, the flag is set on a designated rally tile. `ConsiderZones.Evaluate` then adds a strong positive contribution to `ctx.thresholdAccumulator` for that tile (similar to the existing `9999.0` threshold bypass but at a tunable magnitude). All units evaluate this simultaneously, producing convergent movement toward the rally point without explicit coordination — the AI squad behaves as if it has a shared response to threat even though each unit computes independently.

This is low-cost to implement because the zone flag infrastructure already exists. The game logic that sets and clears the rally flag is the new work.

---

### 3.2 Behavior Scoring Layer

---

#### Intervention E — Co-fire bonus scaling by ally health and AP

**Current behaviour:** In `Attack.OnEvaluate`, the `CoFireBonus` is accumulated per ally with line of sight to the target. It is a flat addition per ally. The ally's current health and available AP are not factored in.

**Where:** The co-fire accumulation loop in `Attack.OnEvaluate` at VA `0x180735D20`.

**Change:** Weight the `CoFireBonus` by the contributing ally's current AP fraction and health fraction:
```c
coFireContribution = CoFireBonus(candidate)
                     × (allyCurrentAP / allyMaxAP)
                     × max(allyHPFraction, 0.5);  // floor at 0.5 to prevent full discount
```

This makes the AI prefer targets that injured-but-capable allies can also hit, rather than targets that exhausted or nearly-dead allies nominally have LoS to. The practical effect is that co-fire decisions are based on real shared attack capability rather than theoretical LoS. Attacks feel more coordinated because they are only launched when genuine mutual fire support exists.

---

#### Intervention F — Suppress-first scoring for high-threat targets

**Current gap:** `InflictDamage` and `InflictSuppression` are structurally identical at the scoring level (both pass `skillEffectType = 1`). The AI has no preference for suppressing high-threat targets before attacking them — it treats suppression and damage as interchangeable based purely on tag effectiveness and hit probability.

**Where:** `SkillBehavior.GetTargetValue` (private) at VA `0x18073C130`, in the goal-type assembly section. Alternatively, `InflictSuppression.GetTargetValue` at VA `0x18073B240`.

**Change:** In the targeting value formula, add a multiplier to suppression-type scoring when the target has not yet acted this turn and is rated as high-threat (from `ThreatFromOpponents` data on that tile):

```c
if (behavior == InflictSuppression && target.threatRating > suppressionPriorityThreshold
    && !target.hasActedThisTurn) {
    total *= suppressionPriorityMult;  // e.g. 1.5–2.0
}
```

The `suppressionPriorityMult` becomes a new `AIWeightsTemplate` float. The result is that high-threat, unactivated enemies are actively prioritised for suppression over damage by units with suppression weapons — producing the correct "pin the dangerous target before it acts" behaviour without writing an explicit coordination system.

---

#### Intervention G — Shared target lock to prevent overkill pile-ons

**Current gap:** Each `Attack` behavior evaluates targets independently. If a target is already being focused by two other AI units, a third will still score it highly — potentially wasting its turn overkilling a nearly-dead enemy while a fresh enemy goes unengaged.

**Where:** `Attack.OnEvaluate` at VA `0x180735D20`, in the `GetHighestScoredTarget` resolution step, or in `InflictDamage.GetTargetValue` at VA `0x18073AF00` before the delegate call.

**Change:** Maintain a shared `Dictionary<Actor, float>` tracking committed expected damage against each target from AI units that have already resolved their action this turn. Before scoring a target, check if committed damage already exceeds the target's remaining HP by a threshold (e.g. `committedDamage > target.currentHP × 1.2`). If so, discount the target's score by a `TargetOverkillDiscount` multiplier (e.g. 0.25–0.5). This does not prevent attacking near-dead targets entirely — it deprioritises them in favour of fresh targets, which is usually correct.

The dictionary is written to when a behavior is executed and cleared at the start of each turn. It is read-only during evaluation. Thread safety is manageable because the dictionary is written during single-threaded execution resolution, not during the threaded criterion evaluation phase.

---

#### Intervention H — SupplyAmmo priority inversion for low-HP targets

**Current behaviour:** `SupplyAmmo.GetTargetValue` uses `0.8 + 0.2 × hpFrac`, which scores healthier targets slightly higher. This is intentional (healthy units use ammo better) but means that a unit at 10% HP who is also out of ammo scores only marginally lower than a full-HP unit who is also out of ammo.

**Change:** Add a `SupplyAmmoLowHPPriorityMult` branch: when a target has HP fraction below a threshold (e.g. 0.3) and zero ammo, apply a strong score penalty rather than the standard HP blend. The semantic is "don't resupply a unit that is about to die anyway — resupply units that can survive to use the ammo." This is a small change that produces sensible prioritisation in the edge case where a nearly-dead ally and a healthy ally are both out of ammo.

**Where:** `SupplyAmmo.GetTargetValue` at VA `0x180769E60`, before the HP fraction blend line.

---

#### Intervention I — Target Designator awareness of uncommitted attackers

**Current behaviour:** `TargetDesignator.GetTargetValue` scores based on observer count and proximity reach. It does not consider whether those observers have already committed their attacks this turn.

**Where:** `TargetDesignator.GetTargetValue` at VA `0x18076A640`, in the observer loop.

**Change:** In the observer loop, weight each observer's contribution by its current AP fraction:
```
for each observer in behaviorConfig.field_0x28:
    observerWeight = IsInDesignationZone(observer) ? 0.5 : 0.25
    observerWeight *= (observer.currentAP / observer.maxAP)  // discount exhausted observers
    score += observerWeight
```

This makes designation most valuable when the designating unit acts before the attackers use their AP, producing natural sequencing: the designator goes first, then the attackers follow into the revealed/marked targets. Without this change, a designator acting last provides no AP benefit to already-spent allies. With it, the AI naturally learns to designate early in the turn order.

---

## 4. Prioritised Recommendations

The following ordering reflects expected impact vs. implementation cost, with collaboration as the primary objective.

**Immediate — data tuning, no code changes:**

1. Raise `RemoveSuppressionMult` (`+0x17C`), `RemoveStunnedMult` (`+0x180`), and `RestoreMoraleMult` (`+0x184`) to the top of their ranges (8–10). This makes support units visibly respond to status effects the player inflicts, which is the strongest signal to the player that the AI is reacting to them as a squad.

2. Lower `IncludeAttacksAgainstAllOpponentsMult` (`+0xC0`) to reduce pile-ons. Even a moderate reduction (e.g. from default toward 30–40% of max) will spread fire more naturally across multiple targets.

3. Raise `MoveIfNewTileIsBetterBy` (`+0x150`) to reduce jitter and make units commit to their positions. A squad that holds ground reads as deliberate and coordinated.

4. Differentiate `ThreatFromOpponentsSuppression` (`+0x84`) and `ThreatFromOpponentsStun` (`+0x88`) from `ThreatFromOpponentsDamage` (`+0x7C`) based on the player's typical loadout. This is the lowest-cost reactive tuning.

5. Raise `AllyMetascoreAgainstThreshold` (`+0xAC`) in moderate steps (increments of 10) until units begin yielding initiative to better-positioned allies without becoming passive.

**Medium term — code changes, well-defined scope:**

6. **Intervention E** (co-fire bonus weighted by ally AP/HP) — small code change, clear impact on attack coordination quality.

7. **Intervention G** (shared target lock for overkill prevention) — requires a shared data structure but cleanly solves the most common collaborative failure mode (everyone attacks the same target).

8. **Intervention A** (decouple `DistanceScale`) — necessary before any further threat-sensitivity tuning is reliable. Low code complexity; high importance for future tuning correctness.

**Longer term — new systems or significant structural changes:**

9. **Intervention B** (ally proximity bonus criterion) — adds a genuinely new collaborative pull force to tile scoring. Most impactful single change for squad cohesion in combat.

10. **Intervention C** (team-level tile desirability budget) — produces natural spread without explicit coordination. Requires shared data structure and careful integration with the threading model.

11. **Intervention D** (rally point zone flag) — most impactful for scripted or reactive encounter design, but requires game-logic integration outside the AI system proper.

12. **Intervention F** (suppress-first for high-threat targets) — good quality-of-life improvement for tactical feel, but benefits depend heavily on how frequently suppression weapons appear in the game's unit roster.
