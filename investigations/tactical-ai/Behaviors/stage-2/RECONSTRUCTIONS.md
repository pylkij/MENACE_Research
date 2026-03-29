# Menace Tactical AI — BehaviorBase/SkillBehavior Subclass Investigation
# Stage 2 Reconstructions

---

## SkillBehavior.GetTagValueAgainst — VA 0x18073BFA0

### Raw Ghidra Output
*(Operator has original in decompiled_functions.txt — not reproduced here)*

### Annotated Reconstruction

```c
// Returns a multiplicative tag-effectiveness bonus for hitting 'opponent' using this skill.
// Always >= 1.0. Bypasses WeightsConfig scale when forImmediateUse == true.
float SkillBehavior_GetTagValueAgainst(
    SkillBehavior* self,
    Entity*        opponent,
    Goal*          goal,
    bool           forImmediateUse)
{
    if (goal == NULL || goal->entityHolder == NULL) goto nullfail;
    Entity* goalEntity = goal->entityHolder->entity;   // goal+0x20 -> +0x50
    if (goalEntity == NULL) goto nullfail;

    uint index;
    bool isTypeA = TagMatcher_IsTypeA(goalEntity, opponent, TAG_TYPE_A);   // FUN_181421d50
    if (!isTypeA) {
        if (opponent == NULL) goto nullfail;
        index = TagMatcher_GetIndexA(opponent, goal->field_0x10, 0);       // FUN_1806e2400
    } else {
        if (goal->entityHolder == NULL || goalEntity == NULL) goto nullfail;
        index = TagMatcher_GetIndexB(goalEntity, opponent, TAG_TYPE_B);    // FUN_1814354a0
    }

    TagEffectivenessTable* table = TagEffectivenessTable.Instance;         // DAT_18397ae78
    if (table == NULL) goto nullfail;
    if (table->length <= index) IndexOutOfRangeException();                // bounds check

    float tableValue = table->values[index];   // *(+0x20 + index*4)

    float scale = forImmediateUse
        ? 1.0f
        : WeightsConfig.Instance->tagValueScale;   // WeightsConfig +0xBC
    return tableValue * scale + 1.0f;

nullfail:
    NullReferenceException();
}
```

---

## ProximityData.FindEntryForTile — VA 0x180717730

```c
// Linear scan. Returns matching ProximityEntry* for tile, or NULL.
ProximityEntry* ProximityData_FindEntryForTile(ProximityData* self, Tile* targetTile)
{
    if (self->entries == NULL) NullReferenceException();   // self+0x48
    foreach (ProximityEntry* entry in self->entries) {
        if (entry == NULL) NullReferenceException();
        if (entry->tile == targetTile) return entry;       // entry+0x10
    }
    return NULL;
}
```

---

## ProximityEntry.IsValidType — VA 0x180717A40

```c
// Returns true if entry type is 0 (ground) or 1 (low). Excludes type 2+ from ally bonuses.
bool ProximityEntry_IsValidType(ProximityEntry* entry)
{
    int type = entry->field_0x34;
    return type == 0 || type == 1;
}
```

---

## Deploy/Idle.GetOrder — VA 0x180519A90

```c
// Deploy and Idle behaviors are order 0 — highest scheduling priority.
int GetOrder_Zero(void) { return 0; }
```

---

## ProximityData.HasReadyEntry — VA 0x180717870

```c
// Returns true if any entry has readyRound >= 0 (is assigned to a round).
bool ProximityData_HasReadyEntry(ProximityData* self)
{
    if (self->entries == NULL) NullReferenceException();   // self+0x48
    foreach (ProximityEntry* entry in self->entries) {
        if (entry == NULL) NullReferenceException();
        if (entry->readyRound >= 0) return true;           // entry+0x18
    }
    return false;
}
```

---

## Behavior.GetBehaviorWeights — VA 0x180738FE0

```c
// Traverses: self->agent->actor->GetStrategy()->behaviorWeights
BehaviorWeights* Behavior_GetBehaviorWeights(Behavior* self)
{
    Agent*    agent  = self->agent;               // +0x10
    Actor*    actor  = agent->actor;              // +0x18
    Strategy* strat  = actor->GetStrategy();      // vtable +0x398
    if (strat == NULL) NullReferenceException();
    return strat->behaviorWeights;                // +0x310
}
```

---

## Behavior.GetBehaviorConfig2 — VA 0x180739020

```c
// Traverses: self->agent->agentContext->behaviorConfig
BehaviorConfig2* Behavior_GetBehaviorConfig2(Behavior* self)
{
    Agent*        agent = self->agent;             // +0x10
    AgentContext* ctx   = agent->agentContext;     // +0x10
    if (ctx == NULL) NullReferenceException();
    return ctx->behaviorConfig;                    // +0x50
}
```

---

## Move.HasUtility — VA 0x1807632F0

```c
// Returns true if any tile in tileDict has utilityScore >= threshold.
// False = movement is "forced" (no good destinations exist).
bool Move_HasUtility(Move* self, Dictionary<Tile, TileScore>* tileDict)
{
    float threshold = Behavior_GetUtilityThreshold(self);   // FUN_180739050
    if (tileDict == NULL) NullReferenceException();
    foreach (KeyValuePair<Tile, TileScore> kv in tileDict) {
        TileScore* score = kv.value;
        if (score == NULL) NullReferenceException();
        if (threshold <= score->utilityScore) return true;  // +0x30
    }
    return false;
}
```

---

## Move.GetAddedScoreForPath — VA 0x1807629F0

```c
// Accumulates (movementScore + utilityScore) along a path starting at startIndex.
// First tile weighted 2x. Missing tile entries extrapolated proportionally.
float Move_GetAddedScoreForPath(
    Move*          self,
    TileScoreList* tileList,
    TileMap*       tileMap,
    int            startIndex)
{
    int   idx          = startIndex;
    float total        = 0.0f;
    int   missingCount = 0;

    while (idx <= tileList->count - 1) {
        Tile*      tile  = TileScoreList_GetTileAt(tileList, idx);
        TileScore* score = NULL;
        bool found = TileMap_TryGet(tileMap, tile, &score);   // FUN_181442600
        if (!found) {
            missingCount++;
        } else {
            float mult = (idx == startIndex) ? 2.0f : 1.0f;
            total += (score->movementScore + score->utilityScore) * mult;  // +0x28, +0x30
        }
        idx++;
    }

    if (missingCount > 0) {
        // Extrapolate for unscored tiles
        total += total / (float)(tileList->count - startIndex) * (float)missingCount;
    }
    return total;
}
```

---

## Move.GetHighestTileScore — VA 0x180762EB0

```c
// Returns the TileScore entry with the highest GetCompositeScore() value.
TileScore* Move_GetHighestTileScore(Move* self, List<TileScore>* candidates)
{
    TileScore* best = NULL;
    foreach (TileScore* entry in candidates) {
        if (best == NULL) { best = entry; continue; }
        float currentScore = TileScore_GetCompositeScore(entry);   // FUN_180740e50
        float bestScore    = TileScore_GetCompositeScore(best);
        if (bestScore < currentScore) best = entry;
    }
    return best;
}
```

---

## Move.GetHighestTileScoreScaled — VA 0x180762D60

```c
// Functionally identical to GetHighestTileScore.
// Used after pre-scaling has been applied to the candidate list by the caller.
TileScore* Move_GetHighestTileScoreScaled(Move* self, List<TileScore>* candidates)
{
    TileScore* best = NULL;
    foreach (TileScore* entry in candidates) {
        if (best == NULL) { best = entry; continue; }
        float currentScore = TileScore_GetCompositeScore(entry);   // FUN_180740e50
        float bestScore    = TileScore_GetCompositeScore(best);
        if (bestScore < currentScore) best = entry;
    }
    return best;
}
```

---

## Move.OnEvaluate — VA 0x1807635C0

```c
// Full movement scoring. Returns int utility score, 0 if unit should not move.
int Move_OnEvaluate(Move* self, Actor* actor)
{
    // ── GUARDS ──────────────────────────────────────────────────────────────
    BehaviorWeights* weights = Behavior_GetBehaviorWeights(self);
    if (weights == NULL) NullReferenceException();
    float fVar27 = weights->weightScale                              // +0x2C
                 * WeightsConfig.Instance->movementWeightScale;     // +0x12C

    if (Actor_IsIncapacitated(actor)) return 0;                     // FUN_1805df7e0

    Strategy* strat = actor->GetStrategy();
    if (Strategy_IsMovementDisabled(strat->strategyData)) return 0; // FUN_1829a91b0

    EntityInfo* info = actor->GetEntityInfo();
    if (info->flags_0xEC & (1 << 2)) return 0;                      // isImmobile bit

    if (Actor_CanDeploy(actor)) {
        if (actor->field_0xE0 != NULL &&
            Container_IsActorLocked(actor->field_0xE0, actor)) return 0;
    }

    if (self->m_IsMovementDone)          return 0;                  // +0x20
    if (self->m_IsInsideContainerAndInert) return 0;                // +0x94

    // ── AP BUDGET ───────────────────────────────────────────────────────────
    int currentAP = actor->GetCurrentAP();                          // vtable +0x458
    if (actor->GetStance() == 1                                     // prone
        && self->m_DeployedStanceSkill != NULL                      // +0x60
        && Skill_CanUse(self->m_DeployedStanceSkill)) {
        currentAP -= Skill_GetAPCost(self->m_DeployedStanceSkill);
    }

    int reservedAP = strat->strategyData->reservedAP;               // StrategyData +0x118
    int minimumAP  = info->minimumAP;                               // EntityInfo +0x3C
    if (currentAP - minimumAP - reservedAP < 1) return 0;

    if (Actor_CanDeploy(actor)) {
        int deployAPCost = EntityInfo_GetDeployAPCost(info);
        if (currentAP - deployAPCost < 1) return 0;
    }

    // AP ratio weight adjustment
    if (!self->m_HasMovedThisTurn) {                                // +0x23
        int maxAP = EntityInfo_GetMaxAP(info);
        fVar27 *= (float)currentAP / (float)maxAP;
    }
    if (actor->isWeaponSetUp) fVar27 *= 0.9f;                      // actor +0x167

    // ── INCAPACITY / STRATEGY CHECKS ───────────────────────────────────────
    Tile* currentTile = actor->GetCurrentTile();                    // vtable +0x388
    Dictionary* tileDict = self->agent->tileDict;                   // agent +0x60

    if (!TileDict_IsInitialised(tileDict)) {
        Log_Warning(); return 0;
    }

    // ── FORCED MOVEMENT CHECK ───────────────────────────────────────────────
    bool forced;
    if (actor->GetStance() == 1) {
        forced = true;
    } else {
        BehaviorConfig2* cfg2 = Behavior_GetBehaviorConfig2(self);
        BehaviorWeights* bw2  = Behavior_GetBehaviorWeights(self);
        if (bw2->configFlagA && cfg2->configFlagB) {
            forced = true;
        } else {
            forced = !Move_HasUtility(self, tileDict);
        }
    }

    // ── UTILITY THRESHOLD AND REFERENCE TILE ───────────────────────────────
    float threshold = Behavior_GetUtilityThreshold(self);
    TileScore* currentTileScore = TileMap_TryGet(tileDict, currentTile);

    if (threshold <= currentTileScore->utilityScore) {
        self->m_TurnsBelowUtilityThreshold = 0;                    // +0x38
    } else {
        // Increment once per round
        if (currentRound != self->m_TurnsBelowUtilityThresholdLastTurn) {
            self->m_TurnsBelowUtilityThreshold++;
            self->m_TurnsBelowUtilityThresholdLastTurn = currentRound;
        }
    }

    // Reserved tile score adjustment
    if (self->m_ReservedTile != NULL) {                            // +0x30
        TileScore* res = TileMap_TryGet(tileDict, self->m_ReservedTile);
        if (res != NULL) {
            res->movementScore *= 0.5f;                            // +0x28
            res->utilityScore  += res->utilityScore;               // ×2 via self-add
        }
    }

    // ── DESTINATION SCORING LOOP ────────────────────────────────────────────
    // (see REPORT.md for full scoring formula — abbreviated here)
    // Per-tile: tileScore.movementScore = WeightsConfig.movementScoreWeight
    //                                   * (apCost / 20.0f)
    //                                   * BehaviorWeights.movementWeight
    // Secondary look-ahead: up to 8 adjacent tiles, WeightsConfig.secondaryPathPenalty applied
    // ... [main loop body — see REPORT.md §Tile Scoring Formula] ...

    // ── BEST TILE SELECTION ─────────────────────────────────────────────────
    TileScore* bestTile = Move_GetHighestTileScoreScaled(self, self->m_Destinations);

    if (bestTile->tile == currentTile) return 0;

    if (!forced) {
        float bestScore    = TileScore_GetCompositeScore(bestTile);
        float currentScore = TileScore_GetCompositeScore(currentTileScore);
        if (bestScore < currentScore * WeightsConfig.Instance->minimumImprovementRatio) // +0x150
            return 0;
    }

    // ── FINAL SCORE SCALING ─────────────────────────────────────────────────
    // powf-based score ratio when forced; ratio-by-denominator when voluntary
    // peek bonus: ×4.0 when allowed to peek and AP < actor->field_0x14C
    // marginality penalty: ×0.25 for barely-better destinations

    // ── SKILL SCHEDULING ────────────────────────────────────────────────────
    if (self->m_UseSkillBefore and skill fits AP budget)
        List_Add(self->m_UseSkillBefore, skill);
    if (self->m_UseSkillAfter and skill fits AP budget)
        List_Add(self->m_UseSkillAfter, skill);

    return (int)(fVar27 * WeightsConfig.Instance->finalMovementScoreScale); // +0x128
}
```

---

## Move.OnExecute — VA 0x180766370

```c
// Movement execution state machine. Returns false while in progress, true when done.
bool Move_OnExecute(Move* self, Actor* actor)
{
    // ── STAGE 0: RE-ROUTING SETUP (if already marked done) ─────────────────
    if (self->m_IsMovementDone) {                                  // +0x1C
        self->m_UseSkillBeforeIndex = 0;                           // +0x78
        self->m_UseSkillAfterIndex  = 0;                           // +0x88

        // Release old reserved tile entity
        if (self->m_ReservedTile != NULL) {                        // +0x30
            MovementEntity* oldEntity = self->m_ReservedTile->movementEntity; // +0x70
            if (oldEntity != NULL) MovementEntity_Release(oldEntity, actor);
            self->m_ReservedTile = NULL;
        }

        // Claim target tile entity
        if (self->m_TargetTile != NULL &&                          // +0x28
            self->m_TargetTile->tile != NULL) {                    // TileScore+0x18
            self->m_ReservedTile = self->m_TargetTile->tile;
            MovementEntity* newEntity = self->m_ReservedTile->movementEntity; // +0x70
            if (newEntity != NULL) {
                uint cost = TileScore_GetMoveCost(self->m_TargetTile);
                MovementEntity_Claim(newEntity, actor, cost);
            }
        }

        // Track previous container actor
        Actor* container = actor->field_0xE0;
        self->m_PreviousContainerActor = IsContainerType(container) ? container : NULL; // +0x98
    }

    // ── STAGE 1: USE-SKILL-BEFORE LOOP ─────────────────────────────────────
    if (self->m_UseSkillBefore != NULL) {                          // +0x70
        while (self->m_UseSkillBeforeIndex < self->m_UseSkillBefore->count) {
            Skill* skill = self->m_UseSkillBefore[self->m_UseSkillBeforeIndex];
            Tile*  tile  = actor->GetCurrentTile();                 // vtable +0x388
            Skill_Use(skill, tile, 0x10);
            bool moved = Actor_IsMoving(actor);                     // FUN_1805dfd80
            if (!moved || !Actor_IsAtTile(actor, self->m_TargetTile->tile)) {
                if (self->agent->behavior != NULL)
                    FUN_18071cc10(self->agent->behavior, 0x40000000);
                else
                    self->m_WaitUntil = Time_time() + 2.0f;
            }
            self->m_UseSkillBeforeIndex++;
            return false;
        }
    }

    // ── STAGE 2: TIMER WAIT / MOVEMENT TRIGGER ─────────────────────────────
    if (!self->m_IsExecuted) {                                     // +0x8C
        if (Time_time() > self->m_WaitUntil) {                    // +0x90
            self->m_IsExecuted = true;
            self->m_IsMovementDone = true;
            self->m_HasMovedThisTurn = true;                       // bits at +0x20 → 0x101

            if (self->m_TargetTile->tile != actor->GetCurrentTile()) {
                uint flags = 0;
                if (Actor_CanDeploy(actor))                flags |= 2;
                if (!Goal_IsEmpty(self->m_TargetTile))    flags |= 1;
                if (self->m_TargetTile->isPeek)            flags |= 4;  // +0x61
                Actor_StartMove(actor, self->m_TargetTile->tile, flags); // FUN_1805e03b0
                actor->stanceOnArrival = self->m_TargetTile->stance;    // TileScore +0x62
            }
        }
        if (!self->m_IsExecuted) return false;
    }

    // ── STAGE 3: USE-SKILL-AFTER LOOP ──────────────────────────────────────
    if (!actor->field_0x15F) {                                     // movement-locked flag
        if (self->m_UseSkillAfter != NULL) {                       // +0x80
            while (self->m_UseSkillAfterIndex < self->m_UseSkillAfter->count) {
                Skill* skill = self->m_UseSkillAfter[self->m_UseSkillAfterIndex];
                Tile*  tile  = actor->GetCurrentTile();            // vtable +0x3E8
                bool ok = Skill_Activate(skill, tile);             // FUN_1806f3c30
                if (!ok) return false;
                self->m_UseSkillAfterIndex++;
            }
        }
    }

    // ── STAGE 4: CONTAINER EXIT / FINAL ACTIVATION ─────────────────────────
    if (self->m_IsExecuted && !actor->field_0x15F
        && self->m_PreviousContainerActor != NULL                  // +0x98
        && self->m_PreviousContainerActor->field_0x4C != 0) {

        if (Actor_CanDeploy(actor)) {
            // Broadcast container-exit event, notify container
            FUN_1819c8600(DAT_183997430, actor->field_0x11, DAT_18399f5b0);
            FUN_182948700(eventResult);
            ContainerActor_Notify(self->m_PreviousContainerActor, 1); // FUN_1805e76f0
            return true;
        } else {
            ContainerActor_Notify(self->m_PreviousContainerActor, 1);
            Strategy* s = self->m_PreviousContainerActor->GetStrategy();
            if (s->field_0xE0 != '\0') {
                s->field_0xC8->field_0x78 = 1;  // mark strategy complete
            }
            return true;
        }
    }

    // Final activation
    if (self->m_IsExecuted) {
        Tile* tile = actor->GetCurrentTile();                      // vtable +0x3E8
        bool ok = Skill_Activate(tile);
        if (!ok) return false;
        return actor->field_0x15F == 0;
    }
    return false;
}
```
```

---

## Handoff Prompt (paste this into the next session)

```
# Investigation Handoff — Menace Tactical AI — BehaviorBase Subclass — Stage 2 → Stage 3

## Directive
Read Research-AI.md in full before proceeding. It is attached to this conversation or
available from the operator. Apply all IL2CPP pattern decoding silently.

## Investigation Target
- **Game:** Menace, Windows x64, Unity IL2CPP
- **Image base:** 0x180000000  (VA = RVA + 0x180000000)
- **System under investigation:** Tactical AI Behavior subclasses
- **Investigation status:** In Progress
- **Stage:** 3 of ~5
- **VAs complete across all stages:** 22

## Extraction Report
(extraction_report_master.txt — attached by operator. Contains all subclass field/method
tables for: Assist, Attack, Buff, Deploy, Idle, InflictDamage, InflictSuppression, Move,
Reload, RemoveStatusEffect, CreateLOSBlocker, GainBonusTurn, Mindray, MovementSkill,
Scan, SpawnHovermine, SpawnPhantom, SupplyAmmo, TargetDesignator, TransportEntity, Stun,
TurnArmorTowardsThreat)

---

## Stage Artefacts on Disk
Treat all content in these files as confirmed — do not re-derive.
```
BehaviorBase/stage-1/REPORT.md
BehaviorBase/stage-1/RECONSTRUCTIONS.md
BehaviorBase/stage-2/REPORT.md
BehaviorBase/stage-2/RECONSTRUCTIONS.md
```

---

## Resolved Symbol Maps

### FUN_ → Method Name
```
FUN_180427b00 = il2cpp_runtime_class_init         // lazy static init guard. IGNORE.
FUN_180427d90 = NullReferenceException            // no-return null guard
FUN_180427d80 = IndexOutOfRangeException          // no-return bounds guard
FUN_180426e50 = IL2CPP_WriteBarrier               // GC write barrier. IGNORE semantically.
FUN_1804608d0 = AllocObject(class)                // allocate new object of given class
FUN_1804f7ee0 = Enumerator.Dispose                // end of foreach
FUN_1814f4770 = List.Enumerator.MoveNext          // returns bool
FUN_180cbab80 = List.GetEnumerator
FUN_18136d8a0 = Dictionary.GetEnumerator
FUN_18152f9b0 = Dictionary.Enumerator.MoveNext    // returns bool
FUN_180cca560 = List[index]                       // get element at index
FUN_180424ea0 = InterfaceMethodDispatch           // tag lookup fallback
FUN_180426ed0 = AllocObjectWithSlots(class, N)    // allocate new object with N slots
FUN_1829b1320 = Time.time                         // current game time (float)
FUN_1804bad80 = powf(value, exponent)             // floating-point power
FUN_180426ed0 = AllocObjectWithSlots
FUN_1806e80b0 = Skill.Use(tile, flags)            // activates skill on target tile
FUN_1805e00a0 = Actor.IsDoneActing                // returns bool
FUN_1806f3c30 = Skill.Activate(tile)              // fires main skill; returns bool
FUN_1806ddec0 = Skill.GetAPCost                   // returns int
FUN_1806e3fa0 = Skill.CanUse                      // returns bool
FUN_1806e3a00 = Skill.IsUnavailable               // returns bool
FUN_1806e2e70 = Skill.CanBeUsed                   // returns bool
FUN_180616ae0 = Actor.CanDeploy                   // returns bool
FUN_180616b30 = Tile.IsContainerWithLivingEntity  // returns bool
FUN_180616b70 = Container.IsActorLocked(actor)    // returns bool
FUN_180688600 = Goal.GetEntity                    // returns object reference
FUN_1806889c0 = Goal.IsEmpty                      // returns bool
FUN_1806169a0 = Entity.IsFriendly(other)          // returns bool
FUN_180ba1030 = Skill.TryGetTag(tagType, out tag) // returns bool
FUN_180002310 = LookupTable.Get(index, table)     // returns int
FUN_1806f2460 = ShotPath.GetFromCache             // retrieves cached ShotPath
FUN_18000d310 = ComputeShotPath(0x1c, ...)        // builds shot path
FUN_18062a050 = List.Clear
FUN_1806f2230 = BuildShotData(tile,origin,targetTile,goal,skill)  // returns ShotData*
FUN_1806d5040 = GetOriginTileFromContext(skill)   // returns Tile*
FUN_1805316f0 = AccuracyScalar(coverDefense?)     // float probability/accuracy value
FUN_180531700 = GetRangeHitMultiplier             // range-based float multiplier
FUN_180628270 = ShotPath.GetBaseAccuracy          // returns float
FUN_180628240 = ShotPath.GetRangeAccuracyCost     // per-tile accuracy cost
FUN_180628550 = ShotPath.GetRangeMod              // range modifier float
FUN_1806285e0 = ShotPath.GetHitBase               // base hit value float
FUN_180628300 = ShotPath.GetRangePenaltyB         // float
FUN_180628330 = ShotPath.GetRangePenaltyA         // float
FUN_180628380 = ShotGroup.GetCoverStrength        // returns int
FUN_1806285b0 = ShotPath.GetRangePenaltyC         // float
FUN_180628580 = ShotPath.GetRangePenaltyD         // float
FUN_1806defc0 = Skill.ComputeArmorIgnored(apValue)// returns int
FUN_1806debe0 = ComputeCoverDefense(skill,from,goal,target,shotData,isFriendly) // returns int
FUN_180614b30 = Entity.GetAccuracy                // returns float
FUN_1806155c0 = Entity.GetExposure                // returns float
FUN_1805ca7a0 = TileDistance(tileA, tileB)        // returns int
FUN_1805ca720 = GetRangeBand(goal, origin)        // returns uint enum
FUN_1804eb570 = DamageData.ZeroInitialise
FUN_1806fac90 = Skill.IgnoresCoverFor(entity)     // returns bool
FUN_1806e0300 = ComputeExpectedDamage(...)        // returns float
FUN_1806e0ac0 = ComputeHitProbability(...)        // returns float[6]
FUN_1806df4e0 = ComputeDamageData(...)            // returns DamageData*
FUN_18073c130 = SkillBehavior.GetTargetValue      // private — full targeting formula
FUN_18073dd90 = SkillBehavior.GetTargetValue      // public — routing + contained entity
FUN_18073bdd0 = SkillBehavior.ConsiderSkillSpecifics // armour/ammo multiplier
FUN_18073df70 = SkillBehavior.HandleDeployAndSetup// AP decision + flag set
FUN_18073e300 = SkillBehavior.OnExecute           // four-stage state machine
FUN_180738d10 = Behavior.Collect(actor)           // deployment gate + OnCollect dispatch
FUN_180738e60 = Behavior.Evaluate(actor)          // score-writing entry point
FUN_180738f40 = Behavior.Execute(actor)           // thin wrapper, flag clear
FUN_180739050 = Behavior.GetUtilityThreshold      // strategy-modulated threshold
FUN_1805316d0 = ModifyAccuracyMultiplier          // applies penalty to accuracy mult
FUN_1806de960 = Skill.GetShotCount                // returns int
FUN_1806de540 = ComputeRangeProfile               // builds range profile for shot groups
FUN_1805ca920 = GetShotProperties(goal)           // returns shot property struct
FUN_180717730 = ProximityData.FindEntryForTile    // returns ProximityEntry* or null
FUN_180717a40 = ProximityEntry.IsValidType        // type 0/1 valid; 2+ excluded
FUN_1806283c0 = ShotGroup.GetStat(group,statIndex)// returns int
FUN_1805deca0 = Entity.GetSurvivalProbability     // returns float (kill prob context)
FUN_1805dee10 = Entity.GetDamageProbability       // returns float
FUN_1805ded50 = Entity.GetSuppressionValue        // returns float
FUN_1805df0a0 = Entity.GetKillCheckWithThreshold  // returns bool
FUN_181446af0 = SpatialQuery(tileSet,agentTeam,rangeConst) // count/distance query
FUN_180687590 = Goal.IsSpecialType                // returns int (0=normal)
FUN_180614d30 = Entity.GetSomeStat(entity,0,0)   // returns int
FUN_1829a9340 = Strategy.IsChainAttackActive
FUN_18073bfa0 = SkillBehavior.GetTagValueAgainst  // tag effectiveness multiplier ≥1.0
FUN_181421d50 = TagMatcher.IsTypeA(entity,opp,tag)// bool tag category check
FUN_1806e2400 = TagMatcher.GetIndexA(opp,ref,0)   // uint table index
FUN_1814354a0 = TagMatcher.GetIndexB(entity,opp,tag)// uint table index
FUN_180738fe0 = Behavior.GetBehaviorWeights       // returns BehaviorWeights* via Strategy+0x310
FUN_180739020 = Behavior.GetBehaviorConfig2       // returns BehaviorConfig2* via AgentContext+0x50
FUN_1805df7e0 = Actor.IsIncapacitated             // returns bool
FUN_1829a91b0 = Strategy.IsMovementDisabled       // returns bool
FUN_180628230 = EntityInfo.GetDeployAPCost        // returns int
FUN_1806282a0 = EntityInfo.GetMaxAP               // returns int
FUN_181372b50 = TileDict.IsInitialised            // returns bool
FUN_1807632f0 = Move.HasUtility(self,tileDict)    // any tile with utilityScore≥threshold
FUN_181442600 = TileMap.TryGet(map,tile,out score)// returns bool
FUN_1806361f0 = StrategyData.ComputeMoveCost(...) // returns int AP cost — NOT YET ANALYSED
FUN_180740a10 = Entity.CanBeTargetedBy(actor)     // returns bool
FUN_180740f20 = TileScore.GetScore                // returns float
FUN_180740e50 = TileScore.GetCompositeScore       // returns float
FUN_180762d60 = Move.GetHighestTileScoreScaled    // identical to GetHighestTileScore
FUN_180762eb0 = Move.GetHighestTileScore          // returns TileScore* with highest composite
FUN_1805e03b0 = Actor.StartMove(actor,tile,flags) // initiates movement
FUN_180740a30 = MovementEntity.Release(actor)
FUN_1807409e0 = MovementEntity.Claim(actor,cost)
FUN_1805e76f0 = ContainerActor.Notify(int)
FUN_180717870 = ProximityData.HasReadyEntry       // any entry with readyRound>=0
FUN_180511a50 = RoundManager.GetCurrentRound      // returns round object
FUN_180511630 = PathFinder.GetInstance            // returns singleton
FUN_180669480 = PathFinder.GetPathGraph           // returns graph
FUN_1806e3310 = Skill.IsReady                     // returns bool
FUN_180002590 = List.Add(list, item)
FUN_180669ab0 = PathFinder.FindPath(...)          // returns bool, fills path data
FUN_1806361f0 = StrategyData.ComputeMoveCost(...)
FUN_1805dfd80 = Actor.IsMoving(actor,tile)        // returns bool
FUN_18071cc10 = Behavior.SetTimer(behavior,duration)
FUN_18071b240 = ProximityData.GetCount            // returns float count
FUN_181883a80 = Dictionary.ContainsKey            // returns bool
FUN_1805ca8d0 = Tile.GetCoordinates               // returns coordinate struct
FUN_180ce35d0 = TileScoreDict.SetCoordinate       // stores coord in dict
FUN_180741530 = TileScore.CreateForTile           // allocates new TileScore for tile
FUN_180740dd0 = TileScore.GetExistingOrNew        // returns existing or allocates new
FUN_180740e50 = TileScore.GetCompositeScore       // float composite score
FUN_1806282a0 = EntityInfo.GetMaxAP               // returns int
FUN_1806282a0 = EntityInfo.GetMaxAP               // returns int (dup entry — confirmed)
FUN_180cc14c0 = TileScoreList.FilterToReachable   // filters tileDict to reachable set
FUN_1817eda90 = TileScoreList.BuildFromDict       // builds list from dict + skill reference
FUN_18136c890 = TileMap.SortByScore(map,class)    // sorts tile map entries
FUN_181435ba0 = TileMap.UpdateEntry               // updates existing entry
FUN_181446a70 = TileMap.GetOrCreate(map,tile,class)// get or allocate entry
FUN_181446c90 = TileMap.UpdateIfBetter            // updates entry only if score improves
FUN_1805fcce0 = PathFinder.GetAlternateTarget     // returns alternate Tile*
FUN_1805fd000 = PathFinder.GetNearestAccessible   // returns nearest accessible Tile*
FUN_180615450 = Actor.GetActorInfo                // returns ActorInfo*
FUN_18071b240 = ProximityData.GetCount
FUN_1804f7ee0 = Enumerator.Dispose               // (dup — confirmed)
FUN_180cca630 = TileScoreList.GetAt(list,idx,class)// returns TileScore at index
FUN_180ce3070 = TileScoreList.GetTileAt(list,idx,class)// returns Tile at index
FUN_180633f40 = RoundData.GetTileForEntry(round,&coord)// returns Tile* for coord pair
FUN_1805ca920 = GetShotProperties
FUN_180004120 = ProximityData.SetShotProps(data,&props,class)
FUN_180cd2730 = TileScoreDict.GetEnumeratorFiltered
FUN_1814dd1f0 = FilteredEnumerator.MoveNext       // returns bool
FUN_180762f0  = Move.GetAddedScoreForPath         // path quality float score
```

### DAT_ → Class / Static Field
```
DAT_183981f50 = RoundManager_class                // singleton at *(+0xb8); round at singleton+0x60
DAT_18394c3d0 = WeightsConfig_class               // Instance at *(+0xb8)+8
DAT_183981fc8 = ShotPathList_class
DAT_183976298 = DamageData_class
DAT_1839a64b0 = TAG_ARMOR_MATCH_class
DAT_1839a6620 = AMMO_TABLE
DAT_183965650 = TAG_ARMOR_MATCH_type_id
DAT_183965708 = TAG_AMMO_COUNT_type_id
DAT_183942930 = Goal_class
DAT_183952b10 = Actor_class_type
DAT_183952a58 = Tile_subtype
DAT_18396a5e8 = AdjacencyTable_class
DAT_183944290 = RANGE_CONST
DAT_18394df48 = StrategyExtension_class
DAT_183971160 = RangeProfile_class
DAT_18399f1b8 = ShotGroupElement_type
DAT_1839654d8 = SUPPRESSION_TAG_type_id
DAT_1839657c8 = AOE_TAG_type_id
DAT_1839400a8 = MathUtility_class
DAT_1839677b0 = TAG_TYPE_A_id                     // first tag category identifier
DAT_183967868 = TAG_TYPE_B_id                     // second tag category identifier
DAT_18397ae78 = TagEffectivenessTable_class        // singleton; length at +0x18; float[] at +0x20
DAT_183976f88 = LogManager_class                  // used for warning broadcasts
DAT_183977ab8 = TileDict_class
DAT_1839779f8 = TileScore_class
DAT_18398c768 = TileScoreList_class
DAT_18397aca0 = SkillList_class
DAT_1839888f0 = TileScoreCandidate_class
DAT_183977938 = TileScoreDict_class
DAT_18394dc38 = ContainerActor_class              // used in type check in OnExecute
DAT_18397b030 = Skill_class                       // used in List[index] calls
DAT_18397af78 = SkillBehavior_class
DAT_18399f5b0 = ContainerExitEvent_class
DAT_18395be38 = DictEnumerator_class
DAT_18395bef8 = DictEnumeratorMoveNext_class
DAT_18395bfb0 = DictEntry_class
DAT_18398e1b8 = ProximityData_class
DAT_183961578 = LogWarning_string
DAT_18396e120 = TileScoreReachableList_class
DAT_1839a20a8 = PathGraphCached_class
DAT_18399a748 = ReachableListFilter_class
DAT_18399a690 = BuildFromDictParam_class
DAT_1839840f0 = PathGraphBuilder_class
DAT_183961c70 = PathGraphManager_class
DAT_183984fa8 = TileScoreCandidateList_class
DAT_183997af8 = CandidateListInit_class
DAT_18398c8d8 = TileScoreDict2_class
DAT_18398c990 = TileScoreListFull_class
DAT_183997d20 = ShotPropsAssign_class
DAT_18393e560 = ListEnumerator_class
DAT_18393e618 = ListEnumeratorMoveNext_class
DAT_18393e6d0 = ListEnumeratorDispose_class
DAT_1839777b8 = TileMapSortClass
DAT_1839776f8 = TileMapUpdateEntry_class
DAT_183977b78 = TileMapGetOrCreate_class
DAT_183977c38 = TileMapUpdateIfBetter_class
DAT_183997430 = ContainerExitEventId
DAT_1839ada98 = ProximityEnumerator_class
DAT_1839adb50 = ProximityEnumeratorMoveNext_class
DAT_1839adc08 = ProximityEntry_class
DAT_183968278 = ProximityEntryList_class
DAT_18394df48 = StrategyExtension_class           // (dup — confirmed)
DAT_1839424a0 = RoundDataEnumeratorMoveNext_class
DAT_1839423e8 = RoundDataEnumerator_class
DAT_183942558 = RoundDataEntry_class
DAT_183977878 = TagTypeCheck_class
DAT_183997f48 = RoundDataEnumeratorFiltered_class
DAT_183998508 = TileCoordSetClass
DAT_183998398 = TileScoreListEntry_class
DAT_183998450 = TileScoreListGetAt_class
```