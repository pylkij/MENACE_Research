# Menace — Tactical AI Behavior Layer — Feature Modification Proposals

| Field | Value |
|---|---|
| Game | Menace |
| Platform | PC (Windows x64) |
| Binary | GameAssembly.dll (Unity IL2CPP) |
| Image base | `0x180000000` |
| Namespaces | `Menace.Tactical.AI`, `Menace.Tactical.AI.Behaviors` |
| Source material | Tactical AI Behavior System Investigation Report (52 VAs, all stages complete) |
| Prior proposals | Tactical AI Criterions — Feature Modification Proposals (criterion scoring layer) |
| Document status | **Draft — Pre-implementation** |
| Document purpose | Enumerate proposed code modifications to the behavior scoring and lifecycle system, with implementation targets, expected behavioural outcomes, and risk assessments for each |

---

## Table of Contents

1. Document Purpose and Scope
2. Relationship to Criterion-Layer Proposals
3. System Preconditions
4. Modification Constraint Reference
5. Proposals
   - 5.1 Kill Confidence Bias — Scale Attack Priority by One-Shot Potential
   - 5.2 Suppression-First Doctrine — Elevate Suppression Before Full Attacks
   - 5.3 Co-Fire Coordination — Lower the Co-Fire Bonus Threshold, Raise Its Ceiling
   - 5.4 Low-AP Aggression Suppression — Penalise Attacks When AP Is Insufficient for Follow-Through
   - 5.5 Ammo Discipline — Gate AoE Skill Use on Ammo Ratio
   - 5.6 Buff Priority Rebalance — Break the Status/Heal Tie, Prefer Setup Assistance
   - 5.7 Designation Urgency — Elevate TargetDesignator When Observers Are In Range
   - 5.8 Movement Commitment — Narrow the Marginal-Move Penalty Window
   - 5.9 Aggressive Utility Decay — Accelerate Threshold Escalation for Idle Units
   - 5.10 Deploy Spread Enforcement — Steepen the Ally Proximity Penalty Curve
6. Implementation Priority Matrix
7. Cross-Proposal Interaction Notes
8. Cross-Layer Interactions with Criterion Proposals
9. Modifications Explicitly Out of Scope
10. Open Questions Before Implementation

---

## 1. Document Purpose and Scope

This document proposes concrete, targeted modifications to the Menace tactical AI behavior layer — the system that converts per-tile scores from the criterion layer into integer `m_Score` values, competes those scores against each other to determine which action executes, and governs the lifecycle of every skill-based action a unit can take.

Every proposal operates on the fully analysed and confirmed system. Each identifies a specific property of the scoring pipeline, describes the intended change in plain terms, specifies the exact fields or functions to modify, and assesses risk of unintended side effects.

The behavior layer sits above the criterion scoring layer. It consumes the tile scores that the criterions produce and translates them into decisions: which unit acts, with what skill, against which target, from which tile. Modifications here shape the character and priority of actions — how aggressive, how cooperative, how cautious, how reactive. Modifications to the criterion layer shape which positions on the map are desirable. Both layers must be considered together when designing an AI personality.

**What this document does NOT cover:**

- `GainBonusTurn`, `Reload`, `Scan`, `MovementSkill`, `RemoveStatusEffect`, `TurnArmorTowardsThreat`, `TransportEntity` — entire classes not yet analysed; no proposals can be made safely.
- `StrategyData.ComputeMoveCost` (pathfinding internals) — separate system, deferred.
- Concrete `Condition.Evaluate` subclasses used by `CanApplyBuff` — interface documented, implementations deferred (NQ-36).
- `ConsiderSurroundings.Evaluate` from the criterion layer — still unanalysed; cannot be assessed for interactions.
- The `AgentContext +0x50` label conflict (NQ-42) — any proposal that would read or write this field is explicitly deferred until the conflict is resolved.
- Per-unit weight variation — `AIWeightsTemplate` is a singleton shared by all units. Unit-type personalisation is not architecturally supported without a separate investigation into the template instantiation model.

---

## 2. Relationship to Criterion-Layer Proposals

The criterion and behavior layers are sequential, not parallel. The criterion layer runs first and produces per-tile scores stored in `EvaluationContext.accumulatedScore`. The behavior layer then queries those tile scores — through `TileScore.movementScore`, `TileScore.rangeScore`, `TileScore.utilityScore` — and uses them as inputs to its own scoring formulas. A modification at the criterion layer changes what tiles are considered desirable. A modification at the behavior layer changes which action is prioritised once desirable tiles are known.

This creates compound interactions. The following criterion-layer proposals from the prior document are specifically relevant here:

- **Criterion 4.1 (Flatten health cliff)** and **Criterion 4.4 (Flanking multipliers)**: Both change the tile scores that feed the Attack pipeline's movement integration. `Attack.OnEvaluate` reads `tileDict` movement scores and applies `(1 - moveCostFraction)` against them. If criterion-layer flanking tiles now score higher, Attack's movement score integration will produce larger final scores for flanking attacks, compounding the flanking preference. The magnitude of this interaction should be tested jointly.
- **Criterion 4.8 (Deploy surge in phase 0)**: Deploy has a hardcoded priority of 1000 in this layer and bypasses all scoring competition during phase 0. The deploy tile scoring from the criterion layer feeds `tileScore.rangeScore`, which is modified by the two-penalty model in `Deploy.OnCollect`. The phase-0 surge proposal amplifies the positional component of those scores; this may inflate range scores further and cause Deploy to favour even more aggressively forward tiles during deployment. Monitor jointly.
- **Criterion 4.7 (Ammo-conscious flee)**: Flee accumulation changes at the criterion layer affect `EvaluationContext.accumulatedScore`. The behavior layer's `Attack.OnEvaluate` reads movement scores from the tile dict, which incorporate criterion scores. Heavily ammo-depleted units will have suppressed attack tile scores from the criterion layer, and independently this document's Proposal 5.5 further gates AoE skills on ammo ratio. Confirm that the two effects do not over-suppress attack scoring for units with legitimate ammo reserves.

---

## 3. System Preconditions

The following open questions from the investigation report must be resolved before specific proposals can be safely implemented. Each is flagged at the relevant proposal.

**Precondition P1 — Resolve NQ-37: `skillEffectType = 1` handling for InflictDamage vs InflictSuppression.**
Proposals 5.1 and 5.2 both require understanding whether `SkillBehavior.GetTargetValue(private)` at VA `0x18073C130` applies identical logic to `skillEffectType = 1` regardless of which subclass invokes it. If InflictDamage and InflictSuppression diverge at the base scorer level, the proposals must be implemented separately for each. Resolution path: analyse the `arg5` branching in `0x18073C130`.

**Precondition P2 — Resolve NQ-42: `AgentContext +0x50` label conflict.**
The offset is simultaneously read as a `BehaviorConfig2*` pointer and written as a byte `1` flag. Any proposal touching `BehaviorConfig2` configuration is blocked until this is resolved. Resolution path: extract AgentContext true class name from dump.cs; re-examine the field at `+0x50` in the context of both callers.

**Precondition P3 — Confirm runtime values of key `AIWeightsTemplate` fields.**
Proposals 5.3 (`ThreatFromOpponentsDamage +0x7C`), 5.5 (`ScoreThresholdWithLimitedUses +0xFC`), 5.7 (proximity weight field `+0x88`), and 5.8 (`MoveIfNewTileIsBetterBy +0x150`) all require knowing the current runtime values to size the delta correctly. Memory-dump the `AIWeightsTemplate` singleton before implementing any of these.

**Precondition P4 — Confirm runtime values of `StrategyData.thresholdMultA` and `thresholdMultB`.**
Proposal 5.9 (utility decay) modifies the utility threshold formula. The strategy multipliers (`+0x14`, `+0x18`) are confirmed fields but their runtime values are unknown. An already-high `thresholdMultB` from an aggressive strategy profile could amplify the proposed change far beyond the intended effect.

---

## 4. Modification Constraint Reference

The following constraints apply to all proposals and are derived directly from the investigation report.

| Constraint | Source | Implication |
|---|---|---|
| `m_Score` ceiling is `21474` (0x53E2) | `Behavior.Evaluate` clamping | No proposal can produce scores above this. All proposed formula changes must be verified to stay within bounds under maximum input values. |
| `m_Score` floor is `5` for any positive score | `Behavior.Evaluate` floor gate | A behaviour that evaluates to 1–4 is raised to 5. Proposals relying on very-low scores to signal low priority must produce `0` explicitly, not `1–4`. |
| The `GetOrder() == 99999` sentinel bypasses the floor | `Behavior.Evaluate` | The floor only applies to behaviours with a non-sentinel order. Subclasses that opt out of the floor are unaffected by any floor-adjustment proposal. |
| `Deploy` has a hardcoded priority of `1000` | `Deploy.OnEvaluate` | While a unit has an unvisited deploy target, `Deploy` beats all other behaviours regardless of their scoring. No scoring proposal changes this unless `Deploy.OnEvaluate` itself is patched. |
| `AIWeightsTemplate` is a singleton shared by all units | `DAT_18394c3d0 +0xb8 +0x08` | All `AIWeightsTemplate` field changes affect every unit of the same configuration simultaneously. |
| `Strategy.strategyMode != 0` suppresses `Deploy.OnCollect` and `Deploy.OnEvaluate` entirely | `Deploy.OnCollect`, `Deploy.OnEvaluate` | Deploy behaviour is gated by strategy mode. Proposals to the deploy system have no effect if this mode is set. |
| `Strategy.strategyMode == 1` at `+0x8C` suppresses co-fire | `Attack.HasAllyLineOfSight` | Co-fire bonus proposals are silently inactive for units in no-co-fire strategy profiles. |
| `_forImmediateUse` changes scoring values at the base scorer level | `SkillBehavior.GetTargetValue (private)` | Some modifiers only apply when `_forImmediateUse == true` (execution pass) and others only when `false` (planning pass). Changes to the base scorer must specify which pass they target. |
| AoE scoring uses a 50/50 blend with ammo ratio | `Attack.OnEvaluate` | For AoE skills, `TileUtilityMultiplier = 0.5 × (ammo/maxAmmo) + 0.5 × tileUtility`. The ammo ratio is already baked into the tile multiplier at the Attack level; proposals modifying ammo sensitivity must account for this existing blend. |
| `InflictDamage.GetTargetValue` forces `tagValue = 0` for solo attacks | `InflictDamage.GetTargetValue` | `AIWeightsTemplate.ScalePositionWithTags (+0xBC)` has no influence on solo attack scoring. Proposals to modify tag effectiveness only apply during co-fire evaluations. |
| Buff scoring is fully additive with no per-branch cap | `Buff.GetTargetValue` | The six-branch accumulation has no normalisation. A skill with many bits set can produce very high raw totals before the final `BuffTargetValueMult` scaling. Adjusting individual branch weights can shift total scores substantially. |

---

## 5. Proposals

---

### 5.1 Kill Confidence Bias — Scale Attack Priority by One-Shot Potential

**Behavioural intent:** The current targeting formula in `SkillBehavior.GetTargetValue (private)` weights kill potential (`fVar30`) and expected damage (`fVar27`) additively with equal standing. A target that the unit can kill in one shot scores approximately the same as one it will only suppress. The proposal adds a multiplicative bonus for `canKillInOneShot == true`, so units with reliable one-shot potential strongly prefer those targets over attrition targets, committing resources to eliminating threats completely rather than accumulating suppression that may not resolve.

**Formula change — `SkillBehavior.GetTargetValue (private)` (VA `0x18073C130`), goal-type 0 (attack) assembly:**

Current (reconstruction):
```c
// goal type 0
total = fVar32 * 0.5f + fVar30 + fVar27;
```

Proposed:
```c
float killConfidence = (damageData->canKillInOneShot) ? 1.4f : 1.0f;   // +40% if one-shot possible
total = fVar32 * 0.5f + (fVar30 + fVar27) * killConfidence;
```

**DamageData field used:** `canKillInOneShot` (`DamageData +0x24`, confirmed). This field is already computed by `ComputeDamageData` and is in scope at the point of goal-type assembly.

**Expected change:** Units that can kill a target reliably in a single shot will prefer that target by approximately 40% over otherwise-equally-scored targets. This does not eliminate suppression attacks — if no one-shot target exists, the standard formula applies — but it creates a strong preference for decisive action when it is available. Combined with Criterion 4.1 (health cliff flattening), healthy units at maximum range who also have a one-shot kill available will strongly prioritise executing that kill before retreating to optimal positioning.

**Risk:** Medium. The `canKillInOneShot` flag is set when `maxAmmo <= expectedKills` — it requires expected kills to be at least 1.0. On maps with heavily armoured targets, this flag may never fire, and the proposal is inert. The primary risk is over-aggression against isolated high-value targets when focus fire on a more dangerous but harder-to-kill target would be strategically superior. This is a known limitation of local greedy scoring; it can be addressed by tuning `TargetValueDamageScale (+0xE4)` upward to weight kill potential more heavily in the base formula.

**Prerequisite:** P1 (NQ-37) — confirm that `skillEffectType = 1` applies the same assembly formula for both InflictDamage and InflictSuppression before applying this change to both. If they diverge, apply only to `skillEffectType = 1` on the InflictDamage path.

---

### 5.2 Suppression-First Doctrine — Elevate Suppression Before Full Attacks

**Behavioural intent:** `InflictSuppression.GetTargetValue` and `InflictDamage.GetTargetValue` currently use the same `skillEffectType = 1` path (NQ-37 pending). The `AIWeightsTemplate` provides separate scale fields: `TargetValueSuppressionScale (+0xEC)` for suppression and `TargetValueDamageScale (+0xE4)` for damage. The current values are unknown, but if they are equal, suppression and damage attacks compete on equal terms. The proposal establishes a deliberate preference hierarchy: suppression attacks should score higher when enemies have high remaining AP, and lower when they are already suppressed.

This is achieved by adding a conditional multiplier in `InflictSuppression.GetTargetValue` before the delegate call to the base scorer — analogous to the existing tag-chain prepend in `InflictDamage.GetTargetValue`.

**Modification — `InflictSuppression.GetTargetValue` (VA `0x18073B240`):**

Current flow (reconstruction):
```c
// structurally identical to InflictDamage — no pre-multiplier
SkillBehavior_GetTargetValue(self, isCoFire, 0, ..., skillEffectType=1, ...);
```

Proposed:
```c
float suppressMult = 1.0f;
int   targetAP     = GetActorAP(target);    // read target current AP
int   maxAP        = GetActorMaxAP(target);
if (maxAP > 0) {
    float apFrac    = (float)targetAP / (float)maxAP;
    suppressMult    = 0.7f + apFrac * 0.6f;    // 0.7 at 0 AP → 1.3 at full AP
}
// Pass suppressMult as a pre-scale into the base scorer context,
// or apply it to the result of SkillBehavior_GetTargetValue post-call:
float baseScore = SkillBehavior_GetTargetValue(self, isCoFire, 0, ..., skillEffectType=1, ...);
return baseScore * suppressMult;
```

**Actor fields used:** Target AP is read during `OnCollect`/`OnEvaluate` context. The actor's current AP is accessible through the established `EntityInfo` chain. Confirm the exact offset for current AP against the Actor field table — not yet listed in the investigation report as a confirmed offset; this requires a targeted dump before implementation.

**AIWeightsTemplate interaction:** `AIWeightsTemplate.TargetValueSuppressionScale (+0xEC)` is already applied inside `SkillBehavior.GetTargetValue (private)`. The proposed multiplier is applied after the base scorer returns, stacking multiplicatively with the existing scale. If `TargetValueSuppressionScale` is already calibrated to represent the desired suppression weight relative to damage, the proposed multiplier should be sized to represent only the AP-conditional delta — not the overall suppression priority level.

**Expected change:** Suppression attacks become substantially more attractive against mobile, high-AP targets and substantially less attractive against already-immobile ones. Against a unit at full AP, suppression scores 1.3× the base formula output. Against a unit that is already pinned (near-zero AP), it scores only 0.7×, redirecting resources toward damage attacks or movement instead.

**Risk:** Medium. The multiplier is applied post-delegate, so it does not interfere with tag value computation inside the base scorer. The primary risk is that current AP values are not already captured in the base scorer's `ComputeHitProbability` or `ComputeDamageData` outputs — if they are (through `apAccuracyCoeff (+0x14C)` and `apAccuracyFloor (+0x150)` in `ShotPath`), this proposal may double-count the AP relationship. Verify that the ShotPath AP scaling coefficients are calibrated as accuracy modifiers, not threat-level modifiers, before proceeding.

**Prerequisite:** P1 (NQ-37). P3 for runtime value of `TargetValueSuppressionScale (+0xEC)`. Actor current-AP offset must be confirmed from dump.cs before implementation.

---

### 5.3 Co-Fire Coordination — Lower the Co-Fire Bonus Threshold, Raise Its Ceiling

**Behavioural intent:** Co-fire bonuses are added in `Attack.OnEvaluate` via `HasAllyLineOfSight` gating — for each ally with LoS to the candidate target, a co-fire bonus accumulates. The system already models coordinated fire, but the bonus magnitude is controlled solely by `AIWeightsTemplate.ThreatFromOpponentsDamage (+0x7C)` (previously labelled `allyCoFireBonus`). The current runtime value is unknown. The proposal makes the co-fire bonus scale with the number of allies firing rather than being a flat per-ally increment, and raises the ceiling so that three-unit coordinated attacks generate meaningfully higher scores than two-unit attacks.

**Modification — `Attack.OnEvaluate` co-fire accumulation loop (VA `0x180735D20`):**

Current accumulation (reconstruction):
```c
// Per ally with LoS and alive and not in no-co-fire strategy:
candidateScore += AIWeightsTemplate.ThreatFromOpponentsDamage;   // flat per-ally increment
```

Proposed:
```c
int   allyCount  = CountAlliesWithLoS(candidateTile, target);     // total allies firing
float coFireBase = AIWeightsTemplate.ThreatFromOpponentsDamage;   // +0x7C — unchanged base value
float coFireMult = 1.0f + (allyCount - 1) * 0.35f;               // 1× solo, 1.35× with one ally, 1.7× with two, etc.
candidateScore += coFireBase * coFireMult;
```

In the current implementation, the loop increments `candidateScore` once per ally, producing a linear sum. The proposed change restructures this so the bonus is computed once after counting, with a super-linear scaling factor. The net effect for a single co-firing ally is identical to the current system (baseline unchanged). For two co-firing allies, the bonus is 1.35× the two-ally current total. For three, 1.7×.

**Note on `strategyMode` gate:** `HasAllyLineOfSight` already skips allies in `strategyMode == 1` (NQ-16). The co-fire count used for `allyCount` must use the same gate — only allies that pass `HasAllyLineOfSight` should contribute to the count.

**AIWeightsTemplate field changed:** `ThreatFromOpponentsDamage (+0x7C)` — the base value. The multiplier curve is embedded in code. If the multiplier curve should be designer-tunable, a new `AIWeightsTemplate` field in the unextracted `+0x100–0x140` range (excluding confirmed fields) would be required.

**Expected change:** Units become strongly incentivised to attack targets that multiple allies can also engage. A lone-wolf attack on an isolated target scores the same as today. An attack on a target that two other allies can also hit scores 35% higher than a simple two-ally accumulation would suggest, producing pack-hunting behaviour without any explicit coordination mechanism.

**Risk:** Low-medium. The formula restructuring is straightforward. The primary risk is that the `CountAlliesWithLoS` call introduces an extra iteration of the ally list before the existing per-ally loop. For typical squad sizes this is negligible. The `0.35` scaling factor must be validated against the score ceiling — with three allies and a high base `ThreatFromOpponentsDamage`, the total co-fire contribution must not push `candidateScore` beyond `21474` before `TileUtilityMultiplier` is applied.

**Prerequisite:** P3 (runtime value of `ThreatFromOpponentsDamage +0x7C`). NQ-16 (`Strategy +0x8C = strategyMode`) — inferred but not confirmed; the no-co-fire gate must be applied correctly to the count.

---

### 5.4 Low-AP Aggression Suppression — Penalise Attacks When AP Is Insufficient for Follow-Through

**Behavioural intent:** `HandleDeployAndSetup` already checks AP sufficiency before setting pre-execution flags — it tests whether the unit has enough AP to deploy a stance or set up a weapon after the attack. However, if the unit lacks AP to do anything after firing (e.g., it is a single-shot-remaining turn), `Attack.OnEvaluate` still scores the attack at full value. The proposal introduces a `reservedAP` fraction check: if an attack would leave the unit with less than `StrategyData.reservedAP (+0x118)` AP remaining, the attack score is penalised. Units will prefer attacks that leave tactical headroom.

**Modification — `Attack.OnEvaluate` pre-return calculation (VA `0x180735D20`):**

Current (reconstruction, paraphrased):
```c
return (int)(bestCandidateScore * tileUtilityMultiplier);
```

Proposed:
```c
int   apAfterAttack  = unit.currentAP - bestCandidate.apCost;
int   reservedAP     = strategyData->reservedAP;                  // StrategyData +0x118 (confirmed)
float apSufficiency  = (apAfterAttack >= reservedAP)
                       ? 1.0f
                       : 0.6f + 0.4f * ((float)apAfterAttack / (float)max(reservedAP, 1));
// apSufficiency: 1.0 when AP reserves are met; down to 0.6 at 0 remaining AP

return (int)(bestCandidateScore * tileUtilityMultiplier * apSufficiency);
```

**StrategyData field used:** `reservedAP (+0x118)` — confirmed. `apCost` is stored in `Attack.Data +0x44` (confirmed). Unit current AP is accessible from the established actor chain.

**Expected change:** Attacks that would drain the unit to zero AP score 40% lower than those that preserve the reserved AP budget. This is not a hard block — units will still attack if nothing else scores higher — but the penalty makes the Move behavior more competitive when the unit is AP-constrained and makes the unit more likely to accept a slightly worse attack that leaves it able to reposition.

**Note on interaction with `ConsiderSkillSpecifics`:** `ConsiderSkillSpecifics` already applies an ammo penalty (`(currentAmmo/maxAmmo) × 0.25 + 0.75`). The AP-sufficiency penalty is complementary and orthogonal — ammo tracks whether the unit should use this skill class at all; AP tracks whether this is the right moment to use it.

**Risk:** Low. `reservedAP` is a confirmed field already used in the system. The penalty is a post-calculation multiplier applied at the final return point and does not interact with candidate selection or co-fire accumulation. The `0.6` floor ensures attacks are never fully suppressed, preserving the minimum-viable-score floor for desperate situations.

**Prerequisite:** P3 (runtime value of `StrategyData.reservedAP`). Confirm current AP field offset on Actor from dump.cs.

---

### 5.5 Ammo Discipline — Gate AoE Skill Use on Ammo Ratio

**Behavioural intent:** AoE skills already apply a 50/50 blend in `Attack.OnEvaluate`: `TileUtilityMultiplier = 0.5 × (currentAmmo/maxAmmo) + 0.5 × tileUtility`. This blend means a unit at 10% ammo still receives 55% tile utility on a perfect-position tile. The proposal adds a hard floor gate: if ammo ratio falls below a threshold, AoE attacks are suppressed to a score of `0` unless the `ScoreThresholdWithLimitedUses` condition is met. Units will conserve AoE resources for when they have the ammo to deploy them meaningfully.

**Modification — `Attack.OnEvaluate` AoE branch (VA `0x180735D20`):**

Current AoE path (reconstruction):
```c
if (IsAoeSkill()) {
    tileUtilityMultiplier = 0.5f * (currentAmmo / maxAmmo) + 0.5f * GetUtilityFromTileMult();
}
```

Proposed:
```c
if (IsAoeSkill()) {
    float ammoRatio = (float)currentAmmo / (float)max(maxAmmo, 1);
    if (ammoRatio < 0.25f) {
        // Below 25% ammo: only allow AoE if the score would clear the limited-use threshold
        float rawScore = ComputeRawAoEScore();   // existing computation before multiplier
        if (rawScore < AIWeightsTemplate.ScoreThresholdWithLimitedUses) {
            return 0;    // suppress entirely
        }
    }
    tileUtilityMultiplier = 0.5f * ammoRatio + 0.5f * GetUtilityFromTileMult();
}
```

**AIWeightsTemplate field used:** `ScoreThresholdWithLimitedUses (+0xFC)` — confirmed, already used as an AoE threshold gate in the existing pipeline. This proposal extends its use to the ammo-conservation case.

**Expected change:** AoE skills with fewer than 25% ammo remaining are suppressed unless the expected score is high enough to clear the limited-use threshold. Units in the 25–100% ammo range are unaffected. Units below 25% ammo will use AoE only on high-value targets — concentrations of enemies, suppression-critical moments — rather than depleting reserves on marginal targets.

**Risk:** Low-medium. The gate is a pre-return `return 0` — it completely suppresses the behaviour and returns control to the Agent to select a different action. If all AoE skills are suppressed simultaneously and no other behaviour scores above the utility threshold, the unit may idle. Verify that `Move` or a non-AoE attack scores above threshold for units in this state. The threshold should be tuned: too high, and AoE is never used at low ammo; too low, and the gate is effectively never triggered. Start with `ScoreThresholdWithLimitedUses` at its current runtime value unchanged.

**Prerequisite:** P3 (runtime value of `ScoreThresholdWithLimitedUses +0xFC` and the ammo fields). Cross-reference with Criterion Proposal 4.7 — units suppressed at the criterion level by flee accumulation will have degraded tile scores, and this proposal further suppresses their AoE output. Ensure the compound effect does not produce a deadlock state where low-ammo units neither attack, flee successfully, nor can remain.

---

### 5.6 Buff Priority Rebalance — Break the Status/Heal Tie, Prefer Setup Assistance

**Behavioural intent:** The `Buff.GetTargetValue` formula accumulates contributions from up to six independent branches. The current branch weights are:

- Heal (`RemoveSuppressionMult +0x17C`)
- Status buff (`RemoveStunnedMult +0x180`)
- Suppress (`RestoreMoraleMult +0x184`)
- Setup / stance (`IncreaseMovementMult +0x188`)
- AoE buff (`IncreaseOffensiveStatsMult +0x18C`)
- AoE heal (`IncreaseDefensiveStatsMult +0x190`)

Because the formula is fully additive with no cap before the final `BuffTargetValueMult` multiplication, a skill touching multiple branches can score very high, but the priority between branches is determined entirely by the relative magnitudes of the weight fields. The proposal establishes an explicit priority ordering by adjusting the `AIWeightsTemplate` weight fields, with a specific intent: setup assistance (deploying a weapon stance to enable an ally to fire) should be valued above reactive healing, and AoE buff coverage should outweigh single-target healing when multiple allies are in range.

**AIWeightsTemplate field adjustments:**

| Field | Offset | Proposed change | Rationale |
|---|---|---|---|
| `IncreaseMovementMult` | `+0x188` | Increase by ~20% from baseline | Setup/stance enables follow-up offensive action; currently underweighted relative to heal |
| `IncreaseOffensiveStatsMult` | `+0x18C` | Increase by ~15% from baseline | AoE offensive buff affects multiple allies; currently weighted identically to single-target |
| `RemoveSuppressionMult` | `+0x17C` | Decrease by ~10% from baseline | Heal is reactive; setup and AoE buff are proactive; this rebalances the priority without eliminating heal behaviour |
| `BuffTargetValueMult` | `+0x174` | No change | Global scale; leave unchanged to avoid compounding all adjustments |

**Suppression-of-redundancy guard interaction:** The `buffType == 2` guard in both the Status buff and Suppress branches already reduces weight by 90% and 10% respectively when the target is already in the relevant state. This guard is not modified — the relative weight adjustments proposed here apply before the guard's reduction, so the redundancy suppression continues to operate correctly.

**`contextScale` interaction:** The final multiplication by `actor->buffDataBlock->contextScale` is outside the scope of this proposal. The `contextScale` float at `buffDataBlock +0x34` is set at runtime by the target's status state. The proposed weight changes are applied before this scaling, so they affect all targets proportionally.

**Expected change:** Buff units will preferentially deploy setup assistance to allies who are not yet set up, especially when multiple allies can benefit from AoE coverage. Reactive healing remains available but competes at a slightly lower baseline score, meaning setup and offensive buff take priority when both are possible. Units will not idle on healing when a setup opportunity is available.

**Risk:** Low. These are pure `AIWeightsTemplate` field changes — no code patches. The risk is miscalibration: if `IncreaseMovementMult` is raised too high, Buff units will prioritise setup even on already-set-up allies (the `× 0.75 if isWeaponSetUp` penalty reduces but does not eliminate the setup score). Use the existing `× 0.75 if isWeaponSetUp` penalty as a natural brake; the 20% increase to `IncreaseMovementMult` is likely absorbed by this penalty for already-set-up targets.

**Prerequisite:** P3 (runtime values of all six weight fields). The proposed percentage adjustments are relative to the current baseline; absolute delta values cannot be specified without knowing the baseline.

---

### 5.7 Designation Urgency — Elevate TargetDesignator When Observers Are In Range

**Behavioural intent:** `TargetDesignator.GetTargetValue` scores based on two independent loops: observer coverage (0.5 if in designation zone, 0.25 otherwise) and proximity reach (linear decay over 10 tiles). The final score is multiplied by `proximityEntry.weight (+0x88)`. This is a relatively flat scoring curve — a target at 5 tiles from a single observer in-zone scores `0.5 + 0.5 = 1.0` before the proximity weight. The proposal adds a bonus multiplier when two or more observers have line-of-sight to the same candidate: designation becomes significantly more attractive when the co-observation opportunity is real, creating urgency to designate before observers lose LoS.

**Modification — `TargetDesignator.GetTargetValue` (VA `0x18076A640`):**

Current (reconstruction):
```c
score = 0.0f;
for each observer in agentContext->behaviorConfig->field_0x28:
    score += (IsInDesignationZone(observer, context) ? 0.5f : 0.25f);
for each tile in agentContext->field_0x20:
    dist = GetDistanceTo(tile->pos, context);
    if (0 < dist && dist < 11) score += (1.0f - dist / 10.0f);
return score * proximityEntry->weight;
```

Proposed:
```c
score = 0.0f;
int observerCount = 0;
for each observer in agentContext->behaviorConfig->field_0x28:
    float obs = (IsInDesignationZone(observer, context) ? 0.5f : 0.25f);
    score += obs;
    if (obs >= 0.5f) observerCount++;   // count in-zone observers only
for each tile in agentContext->field_0x20:
    dist = GetDistanceTo(tile->pos, context);
    if (0 < dist && dist < 11) score += (1.0f - dist / 10.0f);

float urgencyMult = 1.0f + max(observerCount - 1, 0) * 0.5f;   // 1.0× alone, 1.5× with 2 observers, 2.0× with 3
return score * proximityEntry->weight * urgencyMult;
```

**Precondition on `agentContext->behaviorConfig->field_0x28`:** This pointer chain traverses through the `AgentContext +0x50` offset, which is subject to NQ-42. If the label conflict at `+0x50` is resolved and the `BehaviorConfig2*` read path is confirmed, this proposal is safe. If `+0x50` is actually a byte field rather than a pointer, this entire access chain is invalid.

**Expected change:** Designation attacks become strongly preferred when two or more friendly observers have LoS to the target zone. With a single in-zone observer the score is unchanged. With two in-zone observers, it is 1.5× as large. With three (uncommon but possible), it is 2×. Designation units will coordinate with observer assets rather than designating targets that only one observer can exploit.

**Risk:** Medium. The `observerCount` loop is an additional pass over the observer list, which is small in practice. The urgency multiplier is bounded above: with three observers at `2.0×` and a proximity weight, the final score must remain below `21474`. Verify against the score ceiling with maximum expected observer counts. Additionally, this proposal depends on NQ-42 resolution.

**Prerequisite:** P2 (NQ-42 resolution). P3 (runtime value of `proximityEntry.weight +0x88`).

---

### 5.8 Movement Commitment — Narrow the Marginal-Move Penalty Window

**Behavioural intent:** `Move.OnEvaluate` applies a `× 0.25` penalty to `fWeight` and sets `m_HasDelayedMovementThisTurn` when the best destination tile is only marginally better than the current position. The margin is controlled by `AIWeightsTemplate.MoveIfNewTileIsBetterBy (+0x150)`. If this threshold is too wide, units frequently accept the penalty and delay movement rather than committing to a position — they oscillate at the margin and appear to jitter in place across turns. The proposal tightens this threshold, reducing the penalty window so that units commit to move when a meaningful improvement is available.

Separately, the peek bonus of `× 4.0` for units with `m_IsAllowedToPeekInAndOutOfCover` and low AP is very large. A unit peekIng in and out of cover scores 4× normal movement weight, which can dominate the move decision regardless of positional quality. The proposal reduces the peek multiplier to `2.5×` to make it a meaningful bonus rather than a near-certain override.

**AIWeightsTemplate field change:**

`MoveIfNewTileIsBetterBy (+0x150)` — reduce by approximately 15–20% from baseline runtime value. This narrows the margin below which the 0.25 penalty fires, making units more willing to commit to moves that provide only modest improvement.

**Code-level change — `Move.OnEvaluate` peek bonus (VA `0x1807635C0`):**

Current:
```c
if (m_IsAllowedToPeekInAndOutOfCover && lowAP) {
    fWeight *= 4.0f;
}
```

Proposed:
```c
if (m_IsAllowedToPeekInAndOutOfCover && lowAP) {
    fWeight *= 2.5f;   // was 4.0 — reduced to keep peek as strong preference, not absolute override
}
```

**Expected change:** Units that would currently stall at the margin commit to movement one tile earlier. The 0.25 penalty fires less often, reducing the incidence of `m_HasDelayedMovementThisTurn` being set unnecessarily. The peek bonus reduction means peek moves are still strongly preferred but no longer guarantee the move decision in all cases — a significantly better non-peek destination can now compete.

**Risk:** Low-medium. The `MoveIfNewTileIsBetterBy` threshold change directly controls how often `m_HasDelayedMovementThisTurn` is set. If tightened too aggressively (threshold near zero), units will always move and the jitter-prevention mechanism is disabled. Reduce incrementally — 15% is a conservative starting point. The peek multiplier reduction from `4.0` to `2.5` is a 37.5% reduction; if peek behaviour was load-bearing for specific unit types (e.g., cover-dependent close-range infantry), this may make them less effective at their intended role. Evaluate by unit type.

**Prerequisite:** P3 (runtime value of `MoveIfNewTileIsBetterBy +0x150`). Required to convert the "15–20% reduction" recommendation into an absolute delta.

---

### 5.9 Aggressive Utility Decay — Accelerate Threshold Escalation for Idle Units

**Behavioural intent:** `Move.OnEvaluate` maintains `m_TurnsBelowUtilityThreshold` — a counter that increments once per round when the best tile scores below the utility threshold. The counter enforces that units eventually move even when no tile is clearly better. However, the current utility threshold formula (`max(base, base × multA) × multB`) does not respond to how long a unit has been idle. The proposal adds a rounds-idle modifier: each turn a unit scores below threshold, its effective `UtilityThreshold` for the move decision is lowered slightly, making it progressively easier for a move to pass the threshold. Units that have been idle for multiple turns eventually accept suboptimal moves rather than continuing to stall.

**Modification — `Behavior.GetUtilityThreshold` (VA `0x180739050`) or inline in `Move.OnEvaluate`:**

Current threshold formula (reconstruction):
```c
base      = AIWeightsTemplate.UtilityThreshold;      // +0x13C
scaled    = max(base, base * strategyData.thresholdMultA);
threshold = scaled * strategyData.thresholdMultB;
return threshold;
```

Proposed (applied only for the move utility comparison in `Move.OnEvaluate`):
```c
float baseThreshold = GetUtilityThreshold();   // existing formula unchanged
int   idleTurns     = m_TurnsBelowUtilityThreshold;
float idleDecay     = max(1.0f - idleTurns * 0.08f, 0.5f);   // 8% decay per idle turn, floor at 50%
float effectiveThreshold = baseThreshold * idleDecay;
// Compare against effectiveThreshold instead of baseThreshold for this comparison only
```

**Important scoping note:** `GetUtilityThreshold` is called by multiple systems (not only Move). The decay should be applied inline in `Move.OnEvaluate` at the point of threshold comparison, not inside `GetUtilityThreshold` itself. Modifying `GetUtilityThreshold` would lower the threshold for all behaviors globally, which is not the intent.

**`m_TurnsBelowUtilityThreshold` usage:** This counter is already confirmed at `Move +0x38` and is read in `HasUtility`. The decay formula reads it at evaluation time — no new counter is needed.

**Expected change:** A unit idle for one turn has an effective threshold of `0.92×` baseline. After three turns, `0.76×`. After seven turns, `0.5×` (floor). This guarantees that units stranded in a stale position for seven turns will accept any move that scores above half the base threshold — a significant reduction that should break deadlocks in most scenarios. Units in active tactical positions (turn-0 threshold passed) are entirely unaffected since `m_TurnsBelowUtilityThreshold` remains zero.

**Risk:** Medium. The decay multiplier modifies behavior for units that are already stalling — the risk is that it causes them to accept moves that look worse than the current position to an outside observer, creating visible "give-up" behavior. The `0.5` floor prevents the threshold from collapsing entirely. The `0.08` per-turn decay is conservative; tune up only if deadlock persists.

**Prerequisite:** P4 (runtime values of `StrategyData.thresholdMultA` and `thresholdMultB`). If `thresholdMultB` from an aggressive strategy is already below 1.0, the effective threshold may already be low, and the decay compound effect could produce immediate zero-threshold states for very long idle streaks. Verify the combined formula range across all expected strategy profiles.

---

### 5.10 Deploy Spread Enforcement — Steepen the Ally Proximity Penalty Curve

**Behavioural intent:** The deploy ally proximity penalty is linear over 6 tiles:

```
for each set-up ally within 6 tiles:
    rangeScore -= (6.0 - distance) × AIWeightsTemplate.DistanceToAlliesScore (+0xD0)
```

A unit adjacent to a set-up ally (distance 1) incurs a penalty of `5 × DistanceToAlliesScore`. A unit 4 tiles away incurs `2 × DistanceToAlliesScore`. The linear curve produces even spacing but does not strongly discourage tight clustering. The proposal changes the distance term from linear to quadratic, so that close proximity incurs a dramatically larger penalty than the current system.

**Modification — `Deploy.OnCollect` penalty loop (VA `0x18073A260`):**

Current penalty term:
```c
rangeScore -= (6.0f - distance) * AIWeightsTemplate.DistanceToAlliesScore;
```

Proposed:
```c
float separationDeficit = max(6.0f - distance, 0.0f);
rangeScore -= (separationDeficit * separationDeficit) * AIWeightsTemplate.DistanceToAlliesScore * 0.2f;
// ×0.2 normalisation: (6-1)² = 25 → 25×0.2 = 5.0 — matches current maximum penalty at distance 1
// At distance 4:    (6-4)² = 4  → 4×0.2 = 0.8  (vs current 2.0) — far separation now penalised less
// At distance 1:    (6-1)² = 25 → 25×0.2 = 5.0  (vs current 5.0) — close penalty unchanged
// At distance 2:    (6-2)² = 16 → 16×0.2 = 3.2  (vs current 4.0) — intermediate reduced
```

The `× 0.2` normalisation factor preserves the maximum penalty (adjacent ally, distance 1) at the same value as today. The curve reshaping makes the penalty fall off much faster with distance — units 3+ tiles from allies are now penalised only slightly compared to today's linear model, while the strong penalty for adjacency is preserved.

**Expected change:** Deploy units cluster more tightly at the penalty level they were already incurring (adjacent tiles hit the same maximum), but the tolerance for "near enough" spacing increases — a unit 3 tiles from an ally pays `9 × 0.2 = 1.8 × DistanceToAlliesScore` instead of `3.0 × DistanceToAlliesScore`. The effective spread radius contracts from 6 tiles to approximately 3–4 tiles as a strong-penalty zone, with soft encouragement to spread beyond that. This is more appropriate for small squad sizes where 6-tile separation may be impractical on confined maps.

**`DistanceToAlliesScore` field:** `AIWeightsTemplate +0xD0` — confirmed. No change to the field value itself; the curve is reshaped in code only.

**Risk:** Low-medium. The `× 0.2` normalisation ensures the maximum penalty matches today's value exactly at distance 1 — the worst-case case is unchanged. Intermediate distances are reduced, not increased. The risk is that the reduced intermediate-distance penalty causes deploy units to cluster at 2–3 tile separation rather than spreading to 5–6 tiles. Monitor whether the target map sizes make this acceptable; if tighter clustering is problematic, increase the normalisation factor toward `0.25–0.28`.

**Prerequisite:** P3 (runtime value of `DistanceToAlliesScore +0xD0`). Also requires NQ-48 confirmation — `Actor +0x50 = isSetUp_alt` is used in the ally proximity loop to skip non-set-up allies. Verify this field is correct before trusting that the penalty correctly excludes mobile allies.

---

## 6. Implementation Priority Matrix

Ranked by expected behavioural impact, implementation risk, and prerequisite dependency.

| Priority | Proposal | Prerequisites | Change Type | Risk |
|---|---|---|---|---|
| 1 | 5.6 — Buff Priority Rebalance | P3 (runtime values) | `AIWeightsTemplate` field edits only | Low |
| 2 | 5.8 — Movement Commitment | P3 (`+0x150`) | `AIWeightsTemplate` field + 1 literal in `Move.OnEvaluate` | Low–Med |
| 3 | 5.4 — Low-AP Aggression Suppression | P3 (reserved AP), actor AP offset | Post-return multiplier in `Attack.OnEvaluate` | Low |
| 4 | 5.5 — Ammo Discipline | P3 (`+0xFC`), cross-check 4.7 | Pre-return gate in `Attack.OnEvaluate` | Low–Med |
| 5 | 5.10 — Deploy Spread Enforcement | P3 (`+0xD0`), NQ-48 | Curve reshape in `Deploy.OnCollect` | Low–Med |
| 6 | 5.1 — Kill Confidence Bias | P1 (NQ-37) | Assembly formula in `GetTargetValue (private)` | Med |
| 7 | 5.3 — Co-Fire Coordination | P3 (`+0x7C`), NQ-16 | Loop restructure in `Attack.OnEvaluate` | Med |
| 8 | 5.9 — Aggressive Utility Decay | P4 (strategy multipliers) | Inline decay in `Move.OnEvaluate` | Med |
| 9 | 5.2 — Suppression-First Doctrine | P1 (NQ-37), actor AP offset | Post-delegate multiplier in `InflictSuppression.GetTargetValue` | Med |
| 10 | 5.7 — Designation Urgency | P2 (NQ-42), P3 (`+0x88`) | Loop + multiplier in `TargetDesignator.GetTargetValue` | Med |

---

## 7. Cross-Proposal Interaction Notes

The following pairings within this document have compound effects that require joint validation.

**5.1 + 5.3 (Kill Confidence × Co-Fire Coordination):** Proposal 5.1 adds a 40% multiplier for one-shot targets. Proposal 5.3 adds a super-linear co-fire bonus. If a target is both one-shot-feasible and reachable by two allies, both bonuses stack multiplicatively at the attack score level. A three-unit coordinated one-shot attack could score `1.4 × 1.7 = 2.38×` the base, potentially approaching the `21474` ceiling on high-quality targets. Profile the combined formula against the score ceiling before shipping both simultaneously.

**5.4 + 5.5 (AP Sufficiency × Ammo Discipline):** Both proposals suppress attack scoring under resource constraints. If a unit is simultaneously low on AP and below 25% ammo, Proposal 5.4 applies a `0.6×` multiplier and Proposal 5.5 may suppress the AoE path entirely. For non-AoE attacks, the unit still evaluates at `0.6×` — the AP penalty does not suppress to zero. Verify that for a dual-constrained unit (low AP, low ammo), at least one non-AoE attack path remains available and scores above the utility threshold.

**5.6 + (Criterion 4.7) (Buff Priority × Ammo-Conscious Flee):** Criterion 4.7 inflates flee accumulation for ammo-depleted units, pushing their criterion-layer tile scores lower. If a unit is both ammo-depleted and buff-capable, its attack tile scores are degraded by the flee pressure but its `Buff.GetTargetValue` score is unaffected by tile scores. In this state, Buff will dominate the behavior selection. This is likely the correct behaviour — a unit that cannot attack effectively should assist allies — but verify that this is not producing passive units in scenarios where they should be repositioning.

**5.8 + 5.9 (Movement Commitment × Utility Decay):** Proposal 5.8 narrows the marginal-move penalty window, making units more willing to commit to movement. Proposal 5.9 lowers the threshold for idle units over time. Both modifications shift the Move behavior toward higher scores more often. If applied together, units that previously stalled may now move aggressively and immediately rather than waiting for a clearly superior tile. Test the compound effect: units should commit to movement sooner but not frivolously — if `MoveIfNewTileIsBetterBy` is tightened too much alongside the decay, units may move every turn even to marginally different tiles.

---

## 8. Cross-Layer Interactions with Criterion Proposals

This section consolidates the cross-layer interactions identified in Section 2 and adds detail from the full proposal set.

**Criterion 4.4 (Flanking Multipliers) + Behavior 5.1 (Kill Confidence Bias):** A flanking tile that also enables a one-shot kill receives both the `1.6×` flanking movement score boost at the criterion layer and the `1.4×` kill confidence multiplier at the behavior layer. The criterion layer score affects `Move.OnEvaluate` tile selection; the behavior layer multiplier affects `Attack.OnEvaluate` target selection. These are independent scoring systems — the tile score influences where the unit moves, and the kill confidence multiplier influences which target the unit fires at after arriving. They do not directly stack in a single formula. However, they reinforce each other directionally: units move to flanking positions (criterion layer) and then execute decisive kills from those positions (behavior layer). This is the intended synergy.

**Criterion 4.3 (Zone Threshold Cap) + Behavior 5.9 (Utility Decay):** Criterion 4.3 makes it possible for tactically exposed zone tiles to fall below the criterion-layer threshold. If a unit's zone tile is suppressed and no other tile scores above the criterion threshold, the unit will fail `HasUtility()` and enter the forced-move path. The idle counter in Behavior 5.9 will begin incrementing. Over several turns, the unit's effective threshold decays, eventually accepting a suboptimal tile. This interaction creates a graceful degradation path for units whose zone position becomes untenable, which is the intended emergent behavior from both proposals combined.

**Criterion 4.1 (Health Cliff Flattening) + Behavior 5.4 (AP Sufficiency Gate):** Criterion 4.1 changes how aggressively healthy units seek maximum-range positions. Behavior 5.4 penalises attacks that leave insufficient AP. A healthy unit at maximum range that also lacks AP to follow through after the attack now faces two competing pressures: the criterion layer incentivises the position, but the behavior layer penalises the attack score. In the absence of a move-and-attack sequence that preserves AP, the unit may hold position and wait for AP recovery. This is the correct strategic behavior for a healthy sniper: take the shot only when AP allows for repositioning afterward.

---

## 9. Modifications Explicitly Out of Scope

The following were considered and rejected or deferred for the reasons stated.

**Modifying `Deploy`'s hardcoded 1000 priority:** Deploy's fixed priority is an architectural invariant that ensures deployment completes before combat scoring can override it. Modifying this without understanding the full deploy completion lifecycle (including `m_IsDone` state management and the `agentContext +0x50` write) would risk units getting stuck in perpetual deploy loops. Deferred pending NQ-42 resolution.

**Modifying the `m_Score` ceiling of `21474`:** The ceiling is not a design choice that can be changed by a field write — it is a hardcoded literal in `Behavior.Evaluate`. Changing it would require a code patch and would affect every behavior simultaneously. Not proposed; the ceiling has never been identified as causing scoring problems.

**Modifying the `GetOrder()` priority ordering between behaviors:** The `GetOrder` return values that resolve tie-breaks between equal-scoring behaviors are confirmed as distinct constants per class but were not all decompiled. Adjusting tie-break priority without knowing all current values risks producing unexpected orderings. Deferred.

**Modifying `InflictDamage.tagValue` injection for solo attacks:** The investigation confirms that `tagValue = 0` is forced for solo attacks by architectural design. Making tag effectiveness apply to solo attacks would require restructuring `InflictDamage.GetTargetValue` to compute tag value unconditionally, and understanding whether `SkillBehavior.GetTargetValue (private)` at `0x18073C130` correctly handles a non-zero tag value on the non-co-fire path. This is a feature addition, not a tuning change. Deferred as a separate investigation.

**New `GetTargetValue` overrides for unanalysed behavior classes:** `GainBonusTurn`, `Reload`, `Scan`, `MovementSkill`, `RemoveStatusEffect`, `TurnArmorTowardsThreat`, and `TransportEntity` are entirely unanalysed. No proposals are made for these classes. Any modification to these classes requires a dedicated investigation first.

**Modifying the `_forImmediateUse` planning-mode behavior:** `_forImmediateUse` controls whether `GetTargetValue` scores for future positioning or immediate execution. The distinction between planning-pass and execution-pass scoring is architecturally load-bearing — disrupting it would affect all skill behaviors simultaneously. The current model is well-designed; no modification is proposed.

---

## 10. Open Questions Before Implementation

The following questions must be answered before proceeding. Items are ordered by the number of proposals they block.

1. **P1 — Resolve NQ-37: `skillEffectType = 1` for InflictDamage vs InflictSuppression (blocks Proposals 5.1, 5.2).** Analyse `SkillBehavior.GetTargetValue (private)` at VA `0x18073C130`. Confirm whether `arg5 = 1` is handled identically regardless of calling subclass or whether there is conditional branching that distinguishes the two.

2. **P3 — Memory-dump `AIWeightsTemplate` singleton (blocks Proposals 5.3, 5.5, 5.6, 5.7, 5.8, 5.10).** Without knowing the current values of `ThreatFromOpponentsDamage (+0x7C)`, `ScoreThresholdWithLimitedUses (+0xFC)`, `MoveIfNewTileIsBetterBy (+0x150)`, `DistanceToAlliesScore (+0xD0)`, and the six `Buff` weight fields (`+0x17C`–`+0x190`), no absolute delta recommendations can be made. Access path confirmed: `*(*(DAT_18394c3d0 + 0xb8) + 8)`.

3. **P2 — Resolve NQ-42: `AgentContext +0x50` label conflict (blocks Proposal 5.7).** Extract `AgentContext` true class name from dump.cs; confirm whether `+0x50` is a `BehaviorConfig2*` pointer or a byte field. If it is a byte, the `TargetDesignator` observer list access chain through this offset is invalid and must be re-routed.

4. **P4 — Confirm runtime values of `StrategyData.thresholdMultA (+0x14)` and `thresholdMultB (+0x18)` (blocks Proposal 5.9).** Access path via `*(DAT_183981f50 + 0xb8)` → Strategy `+0x2B0` → StrategyData `+0x14` / `+0x18`. Confirm the range of these multipliers across all active strategy profiles.

5. **Confirm Actor current-AP field offset (blocks Proposals 5.2, 5.4).** The Actor field table in the report does not list a confirmed offset for current AP. This is needed for the AP-sufficiency penalty formula in Proposal 5.4 and the AP-fraction multiplier in Proposal 5.2. Search dump.cs for the Actor class field list; cross-reference `StrategyData.reservedAP (+0x118)` usage at call sites to find where current AP is read.

6. **Resolve NQ-37 before shipping Proposal 5.6 if Buff subclasses also use `skillEffectType` branching.** If `Buff.GetTargetValue` passes through the base scorer's `skillEffectType` gate, weight adjustments to the Buff branch fields may interact with the `skillEffectType` routing in unexpected ways. Confirm `Buff.GetTargetValue` at VA `0x1807391C0` does not call `SkillBehavior.GetTargetValue (private)` as part of its accumulation.

7. **Confirm NQ-48: `Actor +0x50 = isSetUp_alt` against the Actor class dump.** Proposal 5.10 relies on the Deploy ally-proximity loop correctly reading this field to exclude non-set-up allies. If the field is incorrect, the proximity penalty could apply to mobile allies (reducing effective spreading) or fail to fire entirely (removing spreading entirely). Resolve before testing Proposal 5.10.
