# Menace — Tactical AI: Attack & Assist Behaviors — Stage 3 Report

**Game:** Menace (Windows x64, Unity IL2CPP)
**Binary:** GameAssembly.dll
**Image base:** 0x180000000
**Source material:** Il2CppDumper dump.cs (~885,000 lines), Ghidra decompilation, extract_rvas.py class dumps
**Investigation status:** In Progress — Stage 3 of ~4
**System under investigation:** `Menace.Tactical.AI.Behaviors` — Attack and Assist behavior pipelines

---

## Table of Contents

1. Investigation Overview
2. Tooling
3. Class Inventory
4. The Core Finding — Attack & Assist Scoring Model
5. Full Pipeline — End-to-End Flow
6. Class Sections
   - 6.1 Attack
   - 6.2 Assist
   - 6.3 Attack.Data / Assist.Data
7. Supporting Functions Analysed
8. Ghidra Address Reference
9. Key Inferences and Design Notes
10. Open Questions

---

## 1. Investigation Overview

This stage investigated the complete scoring pipeline for the `Attack` and `Assist` behaviors in Menace's tactical AI system. These are the two highest-priority behaviors in the agent decision loop (after movement, which was covered in prior stages).

**What was achieved:**

- `Attack.OnCollect` fully reconstructed — geometry search, ally counting, origin/target tile population
- `Attack.OnEvaluate` fully reconstructed — per-tile shot scoring, vehicle/turret arc weighting, ally co-fire accumulation, movement integration, final score return
- `Attack.GetHighestScoredTarget` fully reconstructed — argmax over `m_Candidates`
- `Attack.HasAllyLineOfSight` fully reconstructed — team member LoS check for candidate gating
- `FUN_18000DD30` identified — vtable dispatch shim into `SkillBehavior.GetTargetValue(private)` at slot `+0x248`
- `Skill.BuildCandidatesForShotGroup` fully reconstructed — 6-mode shot group geometry dispatcher
- `Assist.OnCollect` fully reconstructed — ally tile geometry search, origin tile population
- `Assist.OnEvaluate` fully reconstructed — ally scoring, movement integration, final score return
- `Assist.GetHighestScoredTarget` fully reconstructed — identical pattern to Attack version
- `EntityInfo.shotGroupMode` enum fully resolved (6 values, 0–5)
- 9 new `WeightsConfig` field offsets confirmed
- All field offset tables updated

**What was NOT investigated:**

- `SkillBehavior.GetTargetValue(private)` concrete subclass implementations (`InflictDamage`, `InflictSuppression`, `Buff`, `Stun`, `SupplyAmmo`, `TargetDesignator`, `SpawnHovermine`, `SpawnPhantom`) — the dispatch mechanism is confirmed; the per-subclass formulas are out of scope for this stage
- `FUN_1806de1d0` — the indirect fire trajectory builder (mode 3 inside `BuildCandidatesForShotGroup`) — deferred; separate system
- `FUN_1806e1fb0` — AoE target set builder (mode 2) — deferred
- `FUN_1806da770` — shot candidate post-processor called at end of `BuildCandidatesForShotGroup` — deferred
- `StrategyData.ComputeMoveCost` (`FUN_1806361f0`) — deferred from prior stages, still out of scope
- All concrete `OnCollect` implementations for non-Attack/Assist subclasses

---

## 2. Tooling

`extract_rvas.py` was run on the `Menace.Tactical.AI.Behaviors` namespace, covering: Attack, Assist, Buff, Deploy, Idle, InflictDamage, InflictSuppression, SpawnHovermine, SpawnPhantom, SupplyAmmo, TargetDesignator, TransportEntity, Stun, TurnArmorTowardsThreat, and several others.

The extraction report provided complete field layouts for all classes. No extraction errors were reported. `NO_RVA` entries for `GetTargetValue` and `GetUtilityFromTileMult` on the base `Attack` and `Assist` classes were expected — these methods are abstract/virtual overridden only in subclasses.

The report confirmed that Attack's fields start at `+0x060` (after SkillBehavior base), and Assist's fields also start at `+0x060` but with one fewer field than Attack (no `m_Goal`), shifting all subsequent offsets by one slot.

---

## 3. Class Inventory

| Class | Namespace | TypeDefIndex | Role |
|---|---|---|---|
| Attack | Menace.Tactical.AI.Behaviors | 3643 | Base class for all offensive skill behaviors; owns the attack scoring pipeline |
| Assist | Menace.Tactical.AI.Behaviors | 3641 | Base class for all ally-targeting skill behaviors; owns the assist scoring pipeline |
| InflictDamage | Menace.Tactical.AI.Behaviors | 3647 | Attack subclass; implements damage-specific `GetTargetValue` and `GetUtilityFromTileMult` |
| InflictSuppression | Menace.Tactical.AI.Behaviors | 3648 | Attack subclass; implements suppression-specific scoring |
| Buff | Menace.Tactical.AI.Behaviors | 3644 | Assist subclass; implements buff-specific scoring |
| SupplyAmmo | Menace.Tactical.AI.Behaviors | 3664 | Assist subclass; implements ammo resupply scoring |
| TargetDesignator | Menace.Tactical.AI.Behaviors | 3665 | Attack subclass; designates targets for indirect fire |
| Stun | Menace.Tactical.AI.Behaviors | 3667 | Attack subclass; implements stun-specific scoring |
| SpawnHovermine | Menace.Tactical.AI.Behaviors | 3660 | Attack subclass |
| SpawnPhantom | Menace.Tactical.AI.Behaviors | 3661 | Attack subclass |

---

## 4. The Core Finding — Attack & Assist Scoring Model

### Attack final score formula

```
FinalScore = (int)(BestCandidateScore × TileUtilityMultiplier)
```

Where:

```
BestCandidateScore = max over all (originTile, targetTile) pairs of:
    CandidateScore(origin, target)

CandidateScore(origin, target) = Σ over all shotGroup candidates c of:
    RawTargetValue(c)
    × ArcScaling(c)                   // if shotGroupMode == 1 (arc fire)
    / CandidateCount                  // if shotGroupMode == 2 (AoE)
    × HPRatioScalar(origin, target)   // if origin ≠ actor.currentTile
    × FriendlyFirePenalty(c)          // if target is on a friendly tile
    × (1 - MoveCostFraction)          // if movement required
    + CoFireBonus(c)                  // for each ally with LoS to c

TileUtilityMultiplier = GetUtilityFromTileMult()   // virtual, subclass-defined
    × blend(AoEReadiness, 0.5)                     // if IsAoeSkill
    × 1.1                                           // if weapon is set up
    × 0.25                                          // if delayed move in progress and AP constrained
```

Where:
- `RawTargetValue(c)` = `SkillBehavior.GetTargetValue(private)` at vtable `+0x248`, dispatched through `FUN_18000DD30` (7-arg form with secondary tile)
- `ArcScaling` for the primary arc target: `clamp(arcCoveragePercent / 100, 0, 1.0)`
- `ArcScaling` for non-primary arc candidates: `((100 - arcCoveragePercent) / 100) / (candidateCount - 1)`
- `HPRatioScalar` = `clamp(abs((origin.exposure + origin.range) / (resolved.exposure + resolved.range)), 0.25, 2.0)`
- `FriendlyFirePenalty` = `WeightsConfig.killWeight` (field `+0xe4`), applied as multiplier when target tile is friendly
- `MoveCostFraction` = `moveCost / actor.maxAP`
- `CoFireBonus` = `rawValue × WeightsConfig.allyCoFireBonusScale (+0x100) × BehaviorWeights.weightScale × (entity.AP / 140.0)`

### Assist final score formula

```
FinalScore = (int)(BestCandidateScore × TileUtilityMultiplier)
```

Where:

```
BestCandidateScore = max over all ally targets a of:
    AssistCandidateScore(a)

AssistCandidateScore(a) =
    GetTargetValue(private)(self, isCoFire=1, skill, allyTile, ...)
    × (1 - MoveCostFraction)          // if movement required
    × HPRatioScalar(origin, resolved) // if skill resolves to different tile
    / CandidateCount                  // if shotGroupMode == 2
    × ArcScaling                      // if shotGroupMode == 1

Score stored as:
    GetUtilityFromTileMult() × rawScore × local_160 + existingScore
```

The Assist formula is structurally identical to Attack with two differences:
1. `isCoFire` is always `1` — Assist always treats itself as co-fire
2. No secondary tile argument — the 5-arg dispatch `FUN_18000dcd0` is used

---

## 5. Full Pipeline — End-to-End Flow

```
Agent.Evaluate()
    └─► Attack.OnCollect(actor, tileDict)           [populate candidates]
    │       Iterate team members → measure ally count in range
    │       2D grid search → populate m_PossibleOriginTiles, m_PossibleTargetTiles
    │       For each (origin, target) pair:
    │           BuildCandidatesForShotGroup(skill, origin, target, m_Candidates, immobileFlag)
    │               switch(shotGroupMode) { 0→direct, 1→arc, 2→AoE, 3→indirect, 4→stored, 5→team }
    │           Score each shot candidate via GetTargetValue dispatch
    │           Write (tile, score) into m_Candidates
    │       return 1
    │
    └─► Attack.OnEvaluate(actor)                    [score and select winner]
            Pre-flight guards (AP, weapon type, setup, readiness, weapon data)
            ConsiderSkillSpecifics()
            TileUtilityMultiplier = GetUtilityFromTileMult()
            AoE readiness blend (if applicable)
            Branch: vehicle/turret OR normal unit
                Iterate origin tiles, score per target:
                    FUN_18000DD30 → GetTargetValue(private) [vtable +0x248]
                    Arc scaling (mode 1), AoE division (mode 2)
                    Ally co-fire accumulation
                    +1.05 bonus for attacking from current position
            GetHighestScoredTarget() → (bestTarget, bestScore)
            AoE threshold gate (WeightsConfig +0xfc)
            Store bestTarget at self[0xb]
            AP clamping, secondary skill checks
            Movement score integration (tileDict)
            Weapon setup bonus ×1.1
            Delayed-move penalty ×0.25
            return (int)(bestScore × TileUtilityMultiplier)

Assist pipeline is identical in structure with:
    - ally tiles instead of enemy tiles
    - isCoFire=1 always
    - no reposition flag (+0x4f)
    - 5-arg GetTargetValue dispatch instead of 7-arg
```

---

## 6. Class Sections

### 6.1 Attack

**Namespace:** `Menace.Tactical.AI.Behaviors`
**TypeDefIndex:** 3643
**Base class:** SkillBehavior
**Role:** Manages the complete offensive scoring cycle. Owns geometry collection (origin/target tiles), candidate scoring, winner selection, and the movement-integration step. Subclasses override `GetTargetValue` and `GetUtilityFromTileMult` to implement weapon-specific damage formulas.

#### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x60 | Goal | m_Goal | Attack goal reference (confirmed) |
| +0x68 | List\<Attack.Data\>* | m_Candidates | All scored (tile, score) entries (confirmed) |
| +0x70 | List\<Tile\>* | m_TargetTiles | Used as shot-group source; iterated in OnEvaluate (confirmed) |
| +0x78 | HashSet\<Tile\>* | m_PossibleOriginTiles | Populated in OnCollect; tiles actor can fire from (confirmed) |
| +0x80 | HashSet\<Tile\>* | m_PossibleTargetTiles | Populated in OnCollect; tiles actor can fire at (confirmed) |
| +0x88 | int | m_MinRangeToOpponents | Minimum AP range; also encodes reserved AP for range calc (confirmed) |

SkillBehavior base fields (inherited, offsets confirmed from prior stages):

| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x10 | AgentContext* | m_AgentContext | param_1[2] in Ghidra |
| +0x18 | [reserved] | | |
| +0x20 | Skill* | m_Skill | param_1[4] |
| +0x48 | [TBD] | | NQ-14 |
| +0x58 | [chosen target ref] | | param_1[0xb]; NQ-14 |
| +0x60 | Skill* | m_SecondarySkill | param_1[6] (inferred) |
| +0x68 | Skill* | m_TertiarySkill | param_1[7] (inferred) |
| +0x70 | Skill* | m_SetupSkill | param_1[8] (inferred) |
| +0x78 | int | m_MinRangeToOpponents | param_1[9] (confirmed for Attack as +0x88 — slot 9 relative to SkillBehavior base) |

#### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| .ctor | 0x737F10 | 0x180737F10 | Constructor |
| GetOrder | 0x50C760 | 0x18050C760 | Inherited; returns order constant |
| GetGoal | 0x59C240 | 0x18059C240 | Returns m_Goal |
| OnScaleMovementWeight | 0x7334E0 | 0x1807334E0 | Shared stub |
| OnScaleBehaviorWeight | 0x7334E0 | 0x1807334E0 | Shared stub |
| GetTargetValue | NO_RVA | — | Abstract; overridden in subclasses |
| GetUtilityFromTileMult | NO_RVA | — | Abstract; overridden in subclasses |
| OnCollect | 0x734130 | 0x180734130 | Fully analysed this stage |
| OnEvaluate | 0x735D20 | 0x180735D20 | Fully analysed this stage |
| OnExecute | 0x737D40 | 0x180737D40 | Not analysed |
| OnReset | 0x737E20 | 0x180737E20 | Not analysed |
| GetHighestScoredTarget | 0x733650 | 0x180733650 | Fully analysed this stage |
| IsSecondaryTargetInRange (×2) | 0x733AA0 / 0x733C90 | 0x180733AA0 / 0x180733C90 | Not analysed |
| HasAllyLineOfSight | 0x733890 | 0x180733890 | Fully analysed this stage |

#### Behavioural notes

- OnCollect counts allies within `WeightsConfig+0xc8` range before populating tile sets. If 3+ allies in range (`local_234 > 2`), the tile search radius expands to `max(WeightsConfig+0xc8, actor.AP * 2)`.
- OnEvaluate applies a +1.05 multiplier when the best target tile is the actor's current tile (i.e., no movement required to fire). This slightly biases the AI toward firing from current position.
- The `isImmobile` flag (`EntityInfo+0xec bit 0`) combined with `m_MinRangeToOpponents > 0` triggers the vehicle/turret scoring branch.
- `WeightsConfig+0xe0` (field confirmed but unnamed in prior stage — this is the friendly-fire penalty weight) is applied when a shot candidate lands on a friendly tile.

---

### 6.2 Assist

**Namespace:** `Menace.Tactical.AI.Behaviors`
**TypeDefIndex:** 3641
**Base class:** SkillBehavior
**Role:** Manages ally-targeting scoring. Mirrors Attack's pipeline but populates candidate tiles from ally positions rather than enemy approach angles. `isCoFire` is always `1` in all scoring calls.

#### Fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x60 | List\<Assist.Data\>* | m_Candidates | All scored ally entries (confirmed) |
| +0x68 | List\<Tile\>* | m_TargetTiles | (confirmed) |
| +0x70 | HashSet\<Tile\>* | m_PossibleOriginTiles | Tiles actor can cast from toward an ally (confirmed) |
| +0x78 | HashSet\<Tile\>* | m_PossibleTargetTiles | Ally tiles reachable by the skill (confirmed) |

#### Methods

| Method | RVA | VA | Notes |
|---|---|---|---|
| .ctor | 0x7334F0 | 0x1807334F0 | Constructor |
| GetOrder | 0x50C760 | 0x18050C760 | Inherited |
| OnScaleMovementWeight | 0x7334E0 | 0x1807334E0 | Shared stub |
| OnScaleBehaviorWeight | 0x7334E0 | 0x1807334E0 | Shared stub |
| GetTargetValue | NO_RVA | — | Abstract; overridden in subclasses |
| GetUtilityFromTileMult | NO_RVA | — | Abstract; overridden in subclasses |
| OnCollect | 0x730B30 | 0x180730B30 | Fully analysed this stage |
| OnEvaluate | 0x731C60 | 0x180731C60 | Fully analysed this stage |
| OnExecute | 0x733320 | 0x180733320 | Not analysed |
| OnReset | 0x7333F0 | 0x1807333F0 | Not analysed |
| GetHighestScoredTarget | 0x7308F0 | 0x1807308F0 | Fully analysed this stage |

#### Behavioural notes

- In the vehicle/turret branch: if `FUN_1806e3af0(skill)` is false (self-cast skill), only the actor's own current tile is added to `m_PossibleOriginTiles`. This short-circuits the grid search for passive self-buffs.
- `GetTargetValue(private)` is called directly (not through `FUN_18000DD30`) because the Assist scoring has no secondary tile argument. The 5-arg dispatch shim `FUN_18000dcd0` is used instead.
- No `+0x4f` (reposition flag) is ever set for Assist. An assist skill does not require the actor to adopt a specific firing arc — only to be within range.

---

### 6.3 Attack.Data / Assist.Data

These are small value-type structs used as scored candidate entries in `m_Candidates`.

#### Attack.Data fields (confirmed from GetHighestScoredTarget and OnCollect)

| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x00 | Tile* | targetTile | The candidate tile reference |
| +0x08 | [padding/flags] | | |
| +0x30 | float | secondaryScore | Secondary scoring accumulator (confirmed) |
| +0x3c | float | primaryScore | Primary score — used for argmax in GetHighestScoredTarget (confirmed) |
| +0x44 | int | apCost | AP cost to reach this candidate; clamped to actor.AP (confirmed) |

#### Assist.Data fields

| Offset | Type | Name | Notes |
|---|---|---|---|
| +0x00 | Actor*/Tile* | targetRef | The ally tile reference |
| +0x30 | float | score | Scoring accumulator (confirmed) |
| +0x44 | int | apCost | AP cost to reach candidate (confirmed) |

Note: `Assist.Data.score` is at `+0x30`, same offset as `Attack.Data.secondaryScore`. These are structurally the same layout; Assist only uses one score field rather than two.

---

## 7. Supporting Functions Analysed

### FUN_18000DD30 — GetTargetValue dispatch shim (7-arg)

**VA:** 0x18000DD30

A one-line vtable dispatch. Takes `methodIndex = 0x11` (17), resolves to vtable slot `0x138 + 17×0x10 = 0x248`, and calls it with the remaining six arguments. This is the entry point used by Attack's scoring loops when a secondary tile argument is needed.

No logic of its own. All formula content lives in the concrete subclass override at vtable `+0x248`.

### Attack.HasAllyLineOfSight — 0x180733890

Iterates all living allies on the actor's team (via team registry singleton → team member list at `teamData+0x20`). Skips dead actors (`Actor+0x162 != 0`), skips self, skips actors in `strategyMode == 1` (no-co-fire mode, `Strategy+0x8c`). For each qualifying ally, calls `FUN_1805df360(ally, targetTile)` — the LoS check. Returns `true` immediately if any ally has LoS.

### Skill.BuildCandidatesForShotGroup — 0x1806E66F0

Dispatcher that resolves `EntityInfo+0x178` (shotGroupMode) into concrete tile candidate sets. Six modes:

| Mode | Name | Behaviour |
|---|---|---|
| 0 | DirectFire | Add `targetTile` directly |
| 1 | ArcFire | Probabilistic arc coverage check; fallback to AoE builder |
| 2 | RadialAoE | `FUN_1806e1fb0` computes AoE tile set |
| 3 | IndirectFire | `FUN_1806de1d0` trajectory builder |
| 4 | StoredGroup | Use pre-built list at `Skill+0x60` |
| 5 | TeamScan | Iterate allies; add living non-dead ally tiles |

After population, calls `FUN_1806da770(skill, candidates)` as post-processor (NQ-17).

---

## 8. Ghidra Address Reference

### Fully analysed

| Stage | VA | Method | Notes |
|---|---|---|---|
| 3 | 0x180735D20 | Attack.OnEvaluate | Complete |
| 3 | 0x180734130 | Attack.OnCollect | Complete |
| 3 | 0x180733650 | Attack.GetHighestScoredTarget | Complete |
| 3 | 0x180733890 | Attack.HasAllyLineOfSight | Complete |
| 3 | 0x18000DD30 | GetTargetValue dispatch shim (7-arg) | Identified as vtable shim only |
| 3 | 0x1806E66F0 | Skill.BuildCandidatesForShotGroup | Complete |
| 3 | 0x180731C60 | Assist.OnEvaluate | Complete |
| 3 | 0x180730B30 | Assist.OnCollect | Complete |
| 3 | 0x1807308F0 | Assist.GetHighestScoredTarget | Complete |

### Secondary targets — not yet analysed

| VA | Method | Notes |
|---|---|---|
| 0x1806E1FB0 | AoE tile set builder | Mode 2 in BuildCandidatesForShotGroup |
| 0x1806DE1D0 | Indirect fire trajectory builder | Mode 3 |
| 0x1806DA770 | Shot candidate post-processor | End of BuildCandidatesForShotGroup |
| 0x18000DCD0 | GetTargetValue dispatch shim (5-arg) | Used by Assist; NQ-18 |
| 0x180737D40 | Attack.OnExecute | Not analysed |
| 0x180733320 | Assist.OnExecute | Not analysed |
| 0x1806361F0 | StrategyData.ComputeMoveCost | Deferred from prior stages |

---

## 9. Key Inferences and Design Notes

**The scoring model is multiplicative, not additive.** The final score is `(int)(bestScore × tileUtilityMult)`. The `TileUtilityMultiplier` acts as a global gate — if the actor's current tile is poor (low cover, exposed), the attack score is suppressed regardless of how good the target is. This means movement and attack scoring are coupled: a good attack from a bad position is penalised.

**AoE readiness uses a 50/50 blend.** When `IsAoeSkill()` is true, the tile utility multiplier is blended: `0.5 × (currentAmmo/maxAmmo) + 0.5 × tileUtility`. This prevents an AoE skill with low ammo from scoring highly even from ideal positions.

**Arc coverage is probabilistic, not deterministic.** For shotGroupMode 1 (arc fire), the system rolls `rand(1, 100)` and compares to `EntityInfo+0x18c` (arc coverage percent). If the roll succeeds, the target tile is added directly. Otherwise, the AoE builder is consulted. This introduces deliberate stochasticity into turret target selection at collection time.

**The `+1.05` bonus for same-tile attacks is small but deliberate.** Attacking from the actor's current tile (no movement required) receives a 5% score bonus. This slightly biases the AI toward staying put when the attack is nearly as good as any reachable position, avoiding unnecessary movement.

**Attack and Assist share 95% of their OnEvaluate logic.** The post-selection phase (AP clamping, secondary skill check, movement integration, weapon setup bonus, delayed-move penalty, final return) is byte-identical. The only structural differences are: target population (enemies vs allies), `isCoFire` flag, presence of the reposition flag `+0x4f`, and arity of the `GetTargetValue` dispatch.

**`EntityInfo+0x178` encodes fundamentally different firing behaviors, not just AI modes.** The 0–5 enum controls how tile candidates are generated: a value of 5 (TeamScan) means the skill's targets are determined entirely by which allies are alive on the map at that moment, making it impossible to pre-cache the tile set. This has implications for the order in which behaviors are evaluated.

**`FUN_1806e3af0(skill)` distinguishes self-cast from ally-targeted Assist skills.** When false, the skill targets only the actor themselves (the fast path adds just the actor's tile). When true, a grid search is required to find positions from which the actor can reach an ally. This boolean controls a major code branch in both OnCollect and OnEvaluate.

---

## 10. Open Questions

**NQ-11:** `FUN_1806361f0` = `StrategyData.ComputeMoveCost` — pathfinding cost function. Returns int AP cost per tile. Large function; deferred from all prior stages.
→ Next step: Analyse `0x1806361F0` in a dedicated stage.

**NQ-8 (partial):** `GetOrder` return values for `0x18050C760`, `0x180547170`, `0x180546260` unknown.
→ Low priority; expected `return N;`. Decompile any one to confirm.

**NQ-4/5:** `WeightsConfig` fields at `+0x78`, `+0x148`, `+0x14C` still inferred.
→ Run `extract_rvas.py` on WeightsConfig; full field dump needed.

**NQ-9:** `FUN_1806f3c30` return convention (XOR 1 in OnExecute Stage 4).
→ Validate against a leaf subclass OnExecute.

**NQ-13:** `WeightsConfig+0x100` (allyCoFireBonusScale) vs `+0xF0` (buffWeight/allyCoFireWeight) — may be separate weights for different co-fire conditions.
→ Cross-reference against InflictDamage.GetTargetValue.

**NQ-14:** SkillBehavior base field at `+0x58` — used in OnEvaluate as `param_1[0xb]` to store chosen target. Unknown whether this belongs to SkillBehavior or is the first Attack-specific field.
→ Run `extract_rvas.py` on SkillBehavior directly.

**NQ-16:** `Strategy+0x8c` = `strategyMode` (value 1 = no co-fire allowed). Inferred from HasAllyLineOfSight.
→ Verify by extracting Strategy class and cross-referencing.

**NQ-17:** `FUN_1806da770(skill, candidates)` — post-processor called at end of `BuildCandidatesForShotGroup`. Purpose unknown.
→ Analyse `0x1806DA770`.

**NQ-18:** `FUN_18000dcd0` — 5-arg variant of the GetTargetValue dispatch shim used by Assist. Expected to be identical to `FUN_18000DD30` minus the secondary tile argument.
→ Low priority; confirm by reading the function (expected to be ~3 lines).

**NQ-6 (partial):** `Skill+0x60` confirmed as stored shot group list for mode-4 skills. Relationship to `Skill+0x48` (referenced in Stage 1) unresolved — may be a separate list on SkillBehavior.
→ Extract SkillBehavior class dump.

**NQ-15 (resolved):** `FUN_1806e66f0` = `Skill.BuildCandidatesForShotGroup`. ✓
