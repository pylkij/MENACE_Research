# Menace Tactical AI — Attack & Assist Behaviors — Annotated Function Reconstructions

**Source:** Ghidra decompilation of Menace (Windows x64, Unity IL2CPP)
**Image base:** 0x180000000
**Stage:** 3
**Format:** Each function shows raw Ghidra output followed by a fully annotated C-style
reconstruction with all offsets resolved, IL2CPP boilerplate collapsed, and all known
symbols named.

---

## Quick-Reference Field Tables

### Attack (inherits SkillBehavior)
| Offset | Field | Type |
|---|---|---|
| +0x10 | agentContext | AgentContext* |
| +0x20 | skill | Skill* |
| +0x48 | [NQ-14 — unknown] | |
| +0x58 | chosenTarget | [ref — NQ-14] |
| +0x60 | m_Goal | Goal |
| +0x68 | m_Candidates | List\<Attack.Data\>* |
| +0x70 | m_TargetTiles | List\<Tile\>* |
| +0x78 | m_PossibleOriginTiles | HashSet\<Tile\>* |
| +0x80 | m_PossibleTargetTiles | HashSet\<Tile\>* |
| +0x88 | m_MinRangeToOpponents | int |

### Assist (inherits SkillBehavior)
| Offset | Field | Type |
|---|---|---|
| +0x60 | m_Candidates | List\<Assist.Data\>* |
| +0x68 | m_TargetTiles | List\<Tile\>* |
| +0x70 | m_PossibleOriginTiles | HashSet\<Tile\>* |
| +0x78 | m_PossibleTargetTiles | HashSet\<Tile\>* |

### WeightsConfig (singleton via DAT_18394c3d0 +0xb8 +8)
| Offset | Field | Type |
|---|---|---|
| +0x13C | utilityThreshold | float |
| +0x54 | movementScoreWeight | float |
| +0xBC | tagValueScale | float |
| +0xC0 | baseAttackWeightScale | float |
| +0xC4 | maxApproachRange | int |
| +0xC8 | allyInRangeMaxDist | int |
| +0xE0 | friendlyFirePenaltyWeight | float |
| +0xE4 | killWeight | float |
| +0xEC | urgencyWeight | float |
| +0xF0 | buffWeight / allyCoFireWeight | float |
| +0xF8 | proximityBonusCap | float |
| +0xFC | minAoeScoreThreshold | float |
| +0x100 | allyCoFireBonusScale | float |

### Attack.Data
| Offset | Field | Type |
|---|---|---|
| +0x00 | targetTile | Tile* |
| +0x30 | secondaryScore | float |
| +0x3C | primaryScore | float |
| +0x44 | apCost | int |

### Assist.Data
| Offset | Field | Type |
|---|---|---|
| +0x00 | targetRef | Tile*/Actor* |
| +0x30 | score | float |
| +0x44 | apCost | int |

### EntityInfo (via Skill +0x10)
| Offset | Field | Type |
|---|---|---|
| +0x14 | isActive | bool |
| +0xEC | flags (bit 0 = isImmobile) | uint |
| +0x112 | hasSecondaryWeapon | bool |
| +0x113 | hasSetupWeapon | bool |
| +0x178 | shotGroupMode | int enum (0–5) |
| +0x18C | arcCoveragePercent | int (0–100) |
| +0x1A1 | isArcFixed | bool |
| +0x2C8 | weaponData | [weapon block]* |

### Actor (partial)
| Offset | Field | Type |
|---|---|---|
| +0x15C | [incapacitated flag] | bool |
| +0x162 | isDead | bool |
| +0x167 | isWeaponSetUp | bool |

### Strategy
| Offset | Field | Type |
|---|---|---|
| +0x8C | strategyMode | int (1 = no co-fire) |
| +0x310 | behaviorWeights | BehaviorWeights* |

### Skill
| Offset | Field | Type |
|---|---|---|
| +0x10 | entityInfo | EntityInfo* |
| +0x48 | [shot group list — NQ-6] | |
| +0x60 | storedShotGroups | List\<ShotGroup\>* |
| +0xA8 | aoeCurrentCount | int |
| +0xAC | aoeMaxCount | int |
| +0xBC | apCost | float |

---

## 1. GetTargetValue Dispatch Shim (7-arg) — 0x18000DD30

### Raw Ghidra output
```c
void FUN_18000dd30(ushort param_1,longlong *param_2,undefined1 param_3,undefined8 param_4,
                  undefined8 param_5,undefined8 param_6,undefined8 param_7)
{
  (**(code **)(*param_2 + 0x138 + (ulonglong)param_1 * 0x10))
            (param_2,param_3,param_4,param_5,param_6,param_7,
             *(undefined8 *)(*param_2 + 0x140 + (ulonglong)param_1 * 0x10));
  return;
}
```

### Annotated reconstruction
```c
// GetTargetValue dispatch shim (7-arg form)
// Resolves vtable slot: self->vtable[0x138 + methodIndex * 0x10]
// Called with methodIndex=0x11 (17) → slot 0x138 + 0x110 = 0x248
// Slot 0x248 = SkillBehavior.GetTargetValue(private) — all scoring logic in subclass overrides
void GetTargetValue_Dispatch7(
    ushort methodIndex,          // always 0x11 in practice
    SkillBehavior* self,
    bool isCoFire,
    Skill* skill,
    Tile* targetTile,
    Tile* originTile,
    Tile* secondaryTile)
{
    // Resolve vtable slot and invoke. The parallel +0x140 slot carries an extra arg.
    self->vtable[0x138 + methodIndex * 0x10](
        self, isCoFire, skill, targetTile, originTile, secondaryTile,
        self->vtable[0x140 + methodIndex * 0x10]  // extra vtable arg
    );
}
```

### Design notes
This is purely a dispatch mechanism. The 0x11 index and 0x10 stride mean the effective vtable offset is always 0x248. The identical offset is called directly in OnEvaluate when Ghidra can see the full call. All scoring formula content lives in the concrete override at each subclass.

---

## 2. Attack.HasAllyLineOfSight — 0x180733890

### Raw Ghidra output
```c
undefined8 FUN_180733890(undefined8 param_1,longlong *param_2,undefined8 param_3)
{
  longlong *plVar1;
  char cVar2;
  longlong lVar3;
  undefined8 local_40;
  undefined8 uStack_38;
  longlong *local_30;
  undefined4 local_28;
  undefined4 uStack_24;
  undefined4 uStack_20;
  undefined4 uStack_1c;
  longlong *local_18;

  // IL2CPP lazy init — omitted (x4)
  if ((((param_2 == (longlong *)0x0) || (**(longlong **)(DAT_183981f50 + 0xb8) == 0)) ||
      (lVar3 = FUN_180679900(**(longlong **)(DAT_183981f50 + 0xb8),
                             *(undefined4 *)((longlong)param_2 + 0x4c),0), lVar3 == 0)) ||
     (*(longlong *)(lVar3 + 0x20) == 0)) {
    FUN_180427d90();  // NullReferenceException
  }
  FUN_180cbab80(&local_40,*(longlong *)(lVar3 + 0x20),DAT_1839a25c0);
  // ... [list enumerator setup — omitted]
LAB_180733990:
  do {
    do {
      cVar2 = FUN_1814f4770(&local_28,DAT_183993d68);
      plVar1 = local_18;
      if (cVar2 == '\0') {
        FUN_1804f7ee0(&local_28,DAT_183993cb0);
        return 0;
      }
      if (local_18 == (longlong *)0x0) FUN_180427d90();
    } while ((*(char *)((longlong)local_18 + 0x162) != '\0') || (local_18 == param_2));
    if (*(char *)((longlong)local_18 + 0x15c) == '\0') {
      lVar3 = (**(code **)(*local_18 + 0x398))(local_18,*(undefined8 *)(*local_18 + 0x3a0));
      if (lVar3 == 0) FUN_180427d90();
      if (*(int *)(lVar3 + 0x8c) == 1) goto LAB_180733990;
    }
    if (plVar1 == (longlong *)0x0) FUN_180427d90();
    cVar2 = FUN_1805df360(plVar1,param_3,0,0,0,0);
    if (cVar2 != '\0') {
      FUN_1804f7ee0(&local_28,DAT_183993cb0);
      return 1;
    }
  } while( true );
}
```

### Annotated reconstruction
```c
// Returns true if any living, eligible ally has line-of-sight to targetTile
bool Attack_HasAllyLineOfSight(Attack* self, Actor* actor, Tile* targetTile)
{
    // IL2CPP lazy init — omitted

    // Get team registry singleton, look up actor's team data
    TeamRegistry* registry = *(TeamRegistry**)(DAT_183981f50 + 0xb8);  // singleton
    TeamData* teamData = TeamRegistry_GetTeamForFaction(registry, actor->teamID /*+0x4c*/);
    List<Actor>* teamMembers = teamData->memberList;  // teamData +0x20

    // Iterate all team members
    foreach (Actor* ally in teamMembers)
    {
        // Skip dead actors
        if (ally->isDead /*+0x162*/) continue;
        // Skip self
        if (ally == actor) continue;

        // If actor is not incapacitated (+0x15c == 0), check strategy mode
        if (!ally->isIncapacitated /*+0x15c*/)
        {
            Strategy* allyStrategy = ally->GetStrategy();  // vtable +0x398
            // strategyMode == 1 means co-fire suppressed — skip this ally
            if (allyStrategy->strategyMode /*+0x8c*/ == 1) continue;
        }

        // Check line-of-sight from this ally to the target tile
        bool hasLoS = FUN_1805df360(ally, targetTile, 0, 0, 0, 0);  // LoS check
        if (hasLoS)
        {
            return true;  // any ally with LoS is sufficient
        }
    }

    return false;  // no ally has LoS
}
```

---

## 3. Attack.GetHighestScoredTarget — 0x180733650

### Raw Ghidra output
```c
undefined8 * FUN_180733650(undefined8 *param_1,longlong param_2)
{
  // [locals omitted for brevity]
  // IL2CPP lazy init — omitted
  local_b8 = 0; uStack_b0 = 0; local_a8 = 0;
  if (*(longlong *)(param_2 + 0x68) == 0) FUN_180427d90();
  FUN_180cbaa60(&local_90,*(longlong *)(param_2 + 0x68),DAT_1839a11e0);
  // [enumerator setup]
LAB_180733740:
  cVar5 = FUN_1814dd090(&local_70,DAT_183945860);
  if (cVar5 == '\0') {
    FUN_1804f7ee0(&local_70,DAT_1839457a8);
    FUN_180dea640(&local_a0,&local_b8,DAT_18397b578);
    *param_1 = local_a0;
    param_1[1] = CONCAT44(uStack_94,fStack_98);
    return param_1;
  }
  // compare fVar3 (current candidate score) to fStack_98 (best so far)
  if ((char)local_b8 != '\0') goto code_r0x000180733789;
  goto LAB_1807337a6;
code_r0x000180733789:
  FUN_180dea640(&local_a0,&local_b8,DAT_18397b578);
  if (fStack_98 < fVar3) {
LAB_1807337a6:
    // new best — copy candidate into best
    FUN_180dea500(&local_90,&local_d8,DAT_18397b408);
    local_b8 = local_90; uStack_b0 = uStack_88; local_a8 = local_80;
  }
  goto LAB_180733740;
}
```

### Annotated reconstruction
```c
// Returns the Attack.Data entry from m_Candidates with the highest primaryScore
Attack_Data Attack_GetHighestScoredTarget(Attack* self)
{
    // IL2CPP lazy init — omitted

    Attack_Data best = default;
    bool hasAny = false;

    // Iterate m_Candidates (+0x68 on Attack)
    foreach (Attack_Data candidate in self->m_Candidates /*+0x68*/)
    {
        float score = candidate.primaryScore;  // fStack_98 at entry +0x38 within candidate

        if (!hasAny || score > best.primaryScore)
        {
            best = candidate;  // struct copy via FUN_180dea500
            hasAny = true;
        }
    }

    return best;
}
```

---

## 4. Assist.GetHighestScoredTarget — 0x1807308F0

### Annotated reconstruction
```c
// Identical to Attack.GetHighestScoredTarget, but iterates m_Candidates at +0x60 (Assist offset)
Assist_Data Assist_GetHighestScoredTarget(Assist* self)
{
    Assist_Data best = default;
    bool hasAny = false;

    foreach (Assist_Data candidate in self->m_Candidates /*+0x60*/)
    {
        float score = candidate.score;  // +0x30 within Assist.Data

        if (!hasAny || score > best.score)
        {
            best = candidate;
            hasAny = true;
        }
    }

    return best;
}
```

---

## 5. Skill.BuildCandidatesForShotGroup — 0x1806E66F0

### Raw Ghidra output
*(Full raw output provided in decompiled_functions_2.txt, reproduced verbatim.)*
```c
void FUN_1806e66f0(longlong *param_1,undefined8 param_2,undefined8 param_3,longlong param_4,
                  int param_5)
{
  // [IL2CPP lazy init block — omitted]
  local_40 = 0; puStack_38 = (undefined8 *)0x0; local_30 = (longlong *)0x0;
  if ((param_5 == 1) || (param_5 == 2)) {
    if (param_1[2] == 0) goto LAB_1806e6e3c;
    iVar3 = *(int *)(param_1[2] + 0x178);
    if (iVar3 != 0) {
      if (iVar3 == 5) {
        // [team-scan for positioned units — iterates allies, adds tiles for those with flag]
        // [detail omitted — same pattern as normal mode 5 below]
      }
      else {
        FUN_1806de1d0(param_1,param_2,param_3,param_4,CONCAT71(uVar6,param_5 == 2),0);
      }
      goto LAB_1806e6c6e;
    }
    if (param_4 == 0) goto LAB_1806e6e3c;
  }
  else {
    lVar5 = param_1[2];
    if (lVar5 == 0) goto LAB_1806e6e3c;
    switch(*(undefined4 *)(lVar5 + 0x178)) {
    case 0: FUN_180002590(param_4,param_3,DAT_18398b858); break;
    case 1:
      if (*(char *)(lVar5 + 0x1a1) == '\0') {
        cVar2 = FUN_1806e60a0(param_1,param_2,param_3,**(undefined2 **)(DAT_183982cf8 + 0xb8),0);
        if (cVar2 != '\0') {
          lVar5 = *(longlong *)(*(longlong *)(DAT_183981f50 + 0xb8) + 8);
          iVar3 = FUN_18053dbd0(lVar5,1,100,0);
          if (param_1[2] == 0) goto LAB_1806e6e3c;
          if (iVar3 <= *(int *)(param_1[2] + 0x18c)) goto switchD_1806e6839_caseD_0; // add direct
        }
      }
      uVar4 = FUN_1806e1fb0(param_1,param_2,param_3,0);
      if (param_4 == 0) goto LAB_1806e6e3c;
      FUN_180002590(param_4,uVar4,DAT_18398b858); break;
    case 2:
      uVar4 = FUN_1806e1fb0(param_1,param_2,param_3,0);
      if (param_4 == 0) goto LAB_1806e6e3c;
      FUN_180002590(param_4,uVar4,DAT_18398b858); break;
    case 3: FUN_1806de1d0(param_1,param_2,param_3,param_4,(ulonglong)uVar6 << 8,0); break;
    case 4:
      if (param_4 == 0) goto LAB_1806e6e3c;
      FUN_1818814d0(param_4,param_1[0xc],DAT_18398b910); break;
    case 5:
      // [team-scan — iterate allies, add living non-dead ally tiles via GetCurrentTile]
      break;
    }
    // [post-switch: global registry append, debug hooks — omitted]
  }
  FUN_180002590(param_4,param_3,DAT_18398b858);  // always append targetTile itself
LAB_1806e6c6e:
  FUN_1806da770(param_1,param_4,0);  // NQ-17: shot candidate post-processor
  return;
}
```

### Annotated reconstruction
```c
// Populates the candidates list based on the skill's shotGroupMode
// param_5 (immobileFlag): 1 or 2 = vehicle/positioned unit path; other = normal path
void Skill_BuildCandidatesForShotGroup(
    Skill* skill,
    Tile* originTile,
    Tile* targetTile,
    List<CandidateTile>* candidates,
    int immobileFlag)
{
    EntityInfo* entity = skill->entityInfo;  // skill +0x10
    int mode = entity->shotGroupMode;        // entity +0x178

    if (immobileFlag == 1 || immobileFlag == 2)
    {
        // Vehicle / positioned unit path
        if (mode != 0)
        {
            if (mode == 5)
            {
                // Team scan: iterate allies on this entity's team (+0x188 = factionID)
                // For each living ally with a movement flag ((char)ally[9] != 0) and not dead:
                //     add ally.GetCurrentTile() to candidates
            }
            else
            {
                // Indirect fire builder handles all other non-direct modes for positioned units
                FUN_1806de1d0(skill, originTile, targetTile, candidates, immobileFlag == 2);
            }
            goto postSwitch;
        }
        // mode == 0: fall through to direct-fire add below
        candidates_AddTile(candidates, targetTile);
    }
    else
    {
        // Normal (mobile) unit path
        switch (mode)
        {
            case 0:  // DirectFire
                candidates_AddTile(candidates, targetTile);
                break;

            case 1:  // ArcFire
                if (!entity->isArcFixed /*+0x1a1*/)
                {
                    bool arcFeasible = FUN_1806e60a0(skill, originTile, targetTile, weaponID);
                    if (arcFeasible)
                    {
                        // Probabilistic: roll 1–100 vs arcCoveragePercent
                        int roll = Random_Range(1, 100);
                        if (roll <= entity->arcCoveragePercent /*+0x18c*/)
                        {
                            candidates_AddTile(candidates, targetTile);  // direct hit
                            break;
                        }
                    }
                }
                // Arc missed or fixed — compute AoE alternative
                Tile* aoeTile = FUN_1806e1fb0(skill, originTile, targetTile);
                candidates_AddTile(candidates, aoeTile);
                break;

            case 2:  // RadialAoE
                Tile* aoeTile = FUN_1806e1fb0(skill, originTile, targetTile);
                candidates_AddTile(candidates, aoeTile);
                break;

            case 3:  // IndirectFire / trajectory
                FUN_1806de1d0(skill, originTile, targetTile, candidates, /*isCoFire=*/false);
                break;

            case 4:  // StoredGroup
                // Append pre-built shot groups from Skill +0x60
                List_AddRange(candidates, skill->storedShotGroups /*+0x60*/);
                break;

            case 5:  // TeamScan
                // Iterate allies on entity's team (via +0x188 factionID)
                // For each living ally (isDead +0x162 == 0):
                //     if vtable[+0x508] check passes:
                //         candidates_AddTile(candidates, ally.GetCurrentTile())
                break;
        }

        // [Post-switch: global shot registry append + debug hooks — omitted as boilerplate]
    }

    // Always append the raw targetTile as well
    candidates_AddTile(candidates, targetTile);

    // NQ-17: unknown post-processing step on the candidate list
    FUN_1806da770(skill, candidates);
}
```

---

## 6. Attack.OnCollect — 0x180734130

### Raw Ghidra output
*(Full raw output in decompiled_functions_1.txt, lines 1194–2188. Reproduced key sections below; full output available in Ghidra export.)*

### Annotated reconstruction
```c
// Populates m_PossibleOriginTiles, m_PossibleTargetTiles, and m_Candidates for Attack
// Returns 1 (true) on success, 0 (false) on any early-out
bool Attack_OnCollect(Attack* self, Actor* actor, Dictionary<Tile,TileScore>* tileDict)
{
    // IL2CPP lazy init — omitted

    // --- Pre-flight guards ---
    if (self->agentContext == null) goto NullTrap;
    if (self->agentContext->isDead /*+0x51*/) return false;

    EntityInfo* entity = self->skill->entityInfo;  // skill +0x10, entity +0x2c8
    if (entity->weaponData /*+0x2c8*/ == null) goto NullTrap;
    if (!entity->isActive /*+0x14*/) return false;

    if (IsSkillOnCooldown(self->skill)) return false;  // FUN_1806e3a00

    Strategy* strategy = actor->GetStrategy();  // vtable +0x398
    StrategyData* stratData = strategy->strategyData;  // +0x2b0
    if (IsStrategyOnCooldown(stratData)) return false;  // FUN_1829a91b0

    if (actor->GetCurrentAP() < 2) return false;

    // GetUtilityFromTileMult — if ≤ 0, this behavior has no tile utility; bail
    float tileUtilityMult = self->vtable[0x228](self);  // GetUtilityFromTileMult base slot
    if (tileUtilityMult <= 0.0f) return false;
    float local_1d4 = tileUtilityMult;

    TileGrid* grid = WorldContext->tileGrid;          // FUN_180511a50 +0x28
    Tile* actorTile = actor->GetCurrentTile();        // vtable +0x388
    Skill* skill = self->skill;                       // +0x20
    float skillAPCost = skill->apCost;                // skill +0xbc
    int totalReach = self->m_MinRangeToOpponents + (int)skillAPCost;  // +0x88

    // --- Ally-in-range counting ---
    // Iterate actor's tile list; count allies within WeightsConfig.allyInRangeMaxDist
    List<Tile>* actorTiles = agentContext->entity->tileList;  // agentContext +0x10, entity +0x48
    int allyCount = 0;
    foreach (Tile* tile in actorTiles)
    {
        if (!IsTileOccupied(tile)) continue;          // FUN_180722ed0
        Entity* occupant = tile->entity;              // +0x10
        Tile* occupantTile = occupant->GetCurrentTile();
        int dist = TileGrid_Distance(actorTile, occupantTile);  // FUN_1805ca7a0
        int threshold = max(WeightsConfig->allyInRangeMaxDist /*+0xc8*/, actor->currentAP * iVar5);
        // Note: second operand uses actor AP from second FUN_1806ddec0 call
        if (dist <= threshold) allyCount++;
    }
    int local_234 = allyCount;

    // --- Clear and populate tile sets ---
    HashSet_Clear(self->m_PossibleOriginTiles /*+0x78*/);  // FUN_1816fa550
    HashSet_Clear(self->m_PossibleTargetTiles /*+0x80*/);  // FUN_1816fa550

    // Origin tile population (vehicle/immobile path omitted for brevity)
    // Normal path: iterate actor tiles, find tiles within range of ally positions
    // Grid search radius = totalReach around each ally tile
    // For each grid cell:
    //   - Check passability (tile flags +0x1c bits 0,1,2)
    //   - Check FUN_1806e3c50(skill, gridTile, weaponID) — range/LoS feasibility
    //   - If local_234 > 2: extended range = max(WeightsConfig+0xc8, actor.AP * 2)
    //   - If range check passes: add to m_PossibleOriginTiles via FUN_181705350

    // HasAllyLineOfSight check — gates LoS-sensitive candidates
    bool noAllyLoS = !HasAllyLineOfSight(self, actor);  // FUN_180733890; local_244 = 1 if no LoS

    // --- Score accumulation ---
    // Iterate m_PossibleOriginTiles (outer) × m_PossibleTargetTiles (inner)
    foreach (Tile* originTile in self->m_PossibleOriginTiles)
    {
        foreach (Tile* targetTile in self->m_PossibleTargetTiles)
        {
            if (!SkillCanFireFrom(skill, targetTile, originTile, weaponID)) continue;  // FUN_1806e3c50

            // Vehicle/immobile: use shot group pipeline
            if (entity->shotGroupMode != 0 || (entity->isImmobile && self->m_MinRangeToOpponents > 0))
            {
                // Increment shot group counter, reset shot array
                self->m_Candidates_ShotGroupCount++;  // param_1[0xe] +0x1c
                // ...
                BuildCandidatesForShotGroup(skill, originTile, targetTile,
                    self->m_Candidates /*param_1[0xd]*/, immobileFlag);

                float shotGroupScore = 0.0f;
                foreach (Tile* candidate in m_Candidates)
                {
                    if (!SkillCanTarget(skill, candidate)) continue;

                    // Direct-fire check paths (omitted — see OnEvaluate for same pattern)
                    float rawScore = GetTargetValue_Dispatch7(
                        0x11, self, /*isCoFire=*/0, skill, candidate, originTile, actorTile);

                    // Arc scaling (mode 1)
                    if (entity->shotGroupMode == 1)
                    {
                        if (candidate == originTile)  // primary arc target
                        {
                            float arc = clamp(entity->arcCoveragePercent * 0.01f, 0.0f, 1.0f);
                            rawScore *= arc;
                        }
                        else  // non-primary arc candidates
                        {
                            float arc = ((100 - entity->arcCoveragePercent) * 0.01f)
                                        / (float)(m_Candidates.count - 1);
                            rawScore *= arc;
                        }
                    }

                    shotGroupScore -= rawScore;  // accumulated (note: sign is negative accumulation
                                                 // for suppression-style scoring — see OnEvaluate)

                    // Double-subtract if candidate is actor's origin tile and skill has double-fire
                    if (candidate == actorTile && IsDoubleFire(skill))
                        shotGroupScore -= rawScore;
                }

                // Write into m_Candidates: score at +0x30 and +0x3c
                // Score formula:
                //   primary = GetUtilityFromTileMult() × rawScore × tileUtilityMult × WeightsConfig.baseAttackWeightScale (+0xc0) × mult
                // mult: 1.0 for base Attack, 2.0 for InflictDamage subclass (vtable class check)
                // secondary score: same formula, written to +0x30
                float mult = IsInflictDamageSubclass(self) ? 2.0f : 1.0f;
                float primary = self->GetUtilityFromTileMult() * rawScore * tileUtilityMult
                                * WeightsConfig->baseAttackWeightScale /*+0xc0*/ * mult;
                Attack_Data entry = GetOrCreateCandidate(tileDict, originTile);  // FUN_181442600
                entry->primaryScore = max(entry->primaryScore, primary);         // +0x3c
                entry->secondaryScore += primary;                                // +0x30
            }
            // Normal path (non-vehicle): populate m_PossibleOriginTiles and score immediately
            // (handled via inner loop and FUN_18000c5b0 accumulation — same structure)
        }
    }

    // --- AP accounting ---
    int primaryAP = GetSkillAPCost(skill);    // FUN_1806ddec0
    int reservedAP = primaryAP;
    // If secondary weapon flags set (+0x112/+0x113) and actor has secondary AP:
    //   Add secondary skill AP (param_1[6]) to total
    // If setup weapon flag set (+0x113) and weapon not set up (!actor.isWeaponSetUp):
    //   Add setup skill AP (param_1[8]) to total

    // --- Movement score integration ---
    foreach ((originTile, TileScore) entry in tileDict)
    {
        if (entry.tileScore.utilityScore <= 0.0f) continue;  // TileScore +0x3c

        // Clamp apCost to available AP
        int available = (entry.originTile == actorTile) ? reservedAP : primaryAP;
        entry.tileScore.apCost = min(entry.tileScore.apCost, available);  // TileScore +0x44

        // Take max of movementScore and secondaryMovementScore
        float best = max(entry.tileScore.movementScore, entry.tileScore.secondaryMovementScore);
        entry.tileScore.movementScore = best;                // TileScore +0x38
        entry.tileScore.secondaryMovementScore = 0.0f;      // TileScore +0x3c zeroed
    }

    return true;
}
```

---

## 7. Attack.OnEvaluate — 0x180735D20

### Annotated reconstruction
```c
// Scores all candidates and returns final integer score for this behavior
// Returns 0 if any guard fails; otherwise (int)(bestScore × tileUtilityMult)
int Attack_OnEvaluate(Attack* self, Actor* actor)
{
    // IL2CPP lazy init — omitted

    // --- Pre-flight guards ---
    if (self->agentContext == null) goto NullTrap;
    if (self->agentContext->isDead /*+0x51*/) return 0;
    if (actor == null) goto NullTrap;

    if (actor->GetCurrentAP() < 2) return 0;

    // Weapon type compatibility
    Skill* skill = self->skill;
    if (!IsWeaponTypeCompatible(skill, weaponID)) return 0;  // FUN_1806e3d50

    // Setup / deploy handling
    if (!HandleDeployAndSetup(self, actor)) return 0;  // FUN_18073df70

    // If neither peek flags set (+0x4d, +0x4e): check skill is ready to fire
    if (!self->isPeekOrigin /*+0x4d*/ && !self->isSetupRequired /*+0x4e*/)
        if (!IsSkillReadyToFire(skill)) return 0;  // FUN_1806e3310

    if (skill->entityInfo->weaponData == null) goto NullTrap;

    // --- Behavior weight / tile utility ---
    ConsiderSkillSpecifics(self);  // FUN_18073bdd0
    float tileUtilityMult = self->GetUtilityFromTileMult();  // vtable +0x238
    if (tileUtilityMult <= 0.0f) return 0;

    // AoE readiness blend
    if (IsAoeSkill(skill))  // FUN_1806e2f50
    {
        if (skill->aoeMaxCount /*+0xac*/ > 0)
            tileUtilityMult = (skill->aoeCurrentCount /*+0xa8*/ / (float)skill->aoeMaxCount) * 0.5f
                            + tileUtilityMult * 0.5f;
    }

    TileGrid* grid = WorldContext->tileGrid;      // FUN_180511a50 +0x28
    Tile* actorTile = actor->GetCurrentTile();    // vtable +0x388
    List<Tile>* actorTileList = agentContext->entity->tileList;  // +0x10, +0x48

    EntityInfo* entity = skill->entityInfo;

    // --- Branch: vehicle/turret (mode != 0 or immobile with reserved AP) ---
    bool isVehicle = (entity->shotGroupMode != 0)
                  || (entity->isImmobile && self->m_MinRangeToOpponents > 0);

    if (!isVehicle)
    {
        // --- Normal unit path ---
        // Iterate actor tile list; for each tile with a valid enemy:
        foreach (Tile* tile in actorTileList)
        {
            if (!IsTileOccupied(tile)) continue;
            Actor* occupant = tile->entity->GetActor();

            // Skip same team
            if (IsSameTeam(occupant->entity, actor->teamID)) continue;

            // Proximity readiness check
            ProximityEntry* proxEntry = ProximityData_FindEntryForTile(agentContext->proximityData, tile);
            if (proxEntry == null) continue;
            if (proxEntry->readyRound < WeightsConfig->someThreshold - 1) continue;

            // Get targeting faction
            Tile* targetTile = occupant->GetCurrentTile();

            // Shot group scoring loop
            BuildCandidatesForShotGroup(skill, actorTile, targetTile, m_Candidates, immobileFlag);
            float tileScore = 0.0f;

            foreach (Tile* candidate in m_Candidates)
            {
                if (!SkillCanTarget(skill, candidate)) continue;

                // Determine shot path: indirect or direct
                bool isIndirect = FUN_180688810(candidate);
                if (!isIndirect)
                {
                    // Direct: check team, LoS, friendly-fire gate
                    if (!IsSameTeam(candidate->entity, actor->teamID)
                        || IsLoSViable(candidate->entity, actorTile))
                    {
                        // Invoke GetTargetValue via shim
                        float rawScore = GetTargetValue_Dispatch7(
                            0x11, self, /*isCoFire=*/0, skill, candidate, targetTile, actorTile);

                        // Friendly tile penalty
                        if (!IsFriendlyTile(candidate, actor->faction))
                            rawScore *= WeightsConfig->friendlyFirePenaltyWeight /*+0xe0*/;

                        // Arc scaling (mode 1)
                        if (entity->shotGroupMode == 1)
                        {
                            if (candidate == actorTile)  // primary
                            {
                                float arc = clamp(entity->arcCoveragePercent * 0.01f, 0, 1.0f);
                                rawScore *= arc;
                                rawScore *= 1.05f;  // same-position bonus
                            }
                            else
                            {
                                rawScore *= ((100 - entity->arcCoveragePercent) * 0.01f)
                                            / (float)(m_Candidates.count - 1);
                            }
                        }
                        else if (candidate == actorTile)
                            rawScore *= 1.05f;  // same-position bonus for non-arc modes

                        tileScore += rawScore;
                    }
                }
                else
                {
                    // Indirect (ally co-fire) branch:
                    float rawScore = GetTargetValue_Dispatch7(
                        0x11, self, /*isCoFire=*/1, skill, candidate, targetTile, actorTile);

                    float coFireScale = WeightsConfig->allyCoFireBonusScale /*+0x100*/
                                     * strategy->behaviorWeights->weightScale /*Strategy +0x310 +0x24*/
                                     * (candidate->entity->ap /*+0xb4*/ / 140.0f);

                    // Arc scaling for co-fire (mode 1)
                    if (entity->shotGroupMode == 1) { /* same arc logic */ }

                    tileScore -= (rawScore * coFireScale);  // co-fire reduces threat score

                    // Double-subtract at actor's tile if double-fire skill
                    if (candidate == actorTile && IsDoubleFire(skill))
                        tileScore -= (rawScore * coFireScale);
                }
            }
        }
    }
    else
    {
        // --- Vehicle / turret path ---
        // Clears m_PossibleTargetTiles, does grid search around ally tiles
        // Delegates to same shot-group scoring loop structure (omitted — identical pattern)
    }

    // --- Winner selection ---
    if (self->m_Candidates->count == 0) return 0;

    Attack_Data best = GetHighestScoredTarget(self);
    Tile* bestTarget = best.targetTile;
    float bestScore = best.primaryScore;

    // AoE threshold gate
    if (IsAoeSkill(skill))
    {
        float threshold = WeightsConfig->minAoeScoreThreshold /*+0xfc*/;
        if (bestScore <= threshold) return 0;
    }
    // Non-AoE threshold gate (same threshold, gated by FUN_180616b40(actor))
    if (!FUN_180616b40(actor))
    {
        if (bestScore <= WeightsConfig->minAoeScoreThreshold) return 0;
    }

    // Weapon setup bonus
    if (entity->hasSetupWeapon /*+0x113*/ && actor->isWeaponSetUp /*+0x167*/)
        tileUtilityMult *= 1.1f;

    // Store chosen target
    self->chosenTarget /*param_1[0xb]*/ = bestTarget;

    // AP feasibility and reposition flag (+0x4f) — omitted (same as Assist below)

    // Secondary skill check, movement score integration — omitted (identical to Assist)

    // Delayed-move penalty
    Move* move = ...; // from agentContext
    if (!move->m_HasMovedThisTurn /*+0x21*/
        && move->m_HasDelayedMovementThisTurn /*+0x22*/
        && move->m_UseSkillBeforeIndex /*+0x78*/ > 0
        && actor->GetCurrentAP() < actor->maxAP /*+0x14c*/)
    {
        tileUtilityMult *= 0.25f;
    }

    return (int)(bestScore * tileUtilityMult);
}
```

---

## 8. Assist.OnCollect — 0x180730B30

### Annotated reconstruction
```c
// Populates m_PossibleOriginTiles, m_PossibleTargetTiles, and m_Candidates for Assist
bool Assist_OnCollect(Assist* self, Actor* actor, Dictionary<Tile,TileScore>* tileDict)
{
    // IL2CPP lazy init — omitted

    // --- Pre-flight guards (identical to Attack.OnCollect) ---
    if (self->agentContext->isDead) return false;
    if (skill->entityInfo->weaponData == null || !entity->isActive) goto NullTrap;
    if (IsSkillOnCooldown(skill)) return false;
    Strategy* strategy = actor->GetStrategy();
    if (IsStrategyOnCooldown(strategy->strategyData)) return false;
    if (actor->GetCurrentAP() < 2) return false;

    // GetUtilityFromTileMult via base slot +0x228
    float tileUtilityMult = self->vtable[0x228](self);
    if (tileUtilityMult <= 0.0f) return false;
    float local_160 = tileUtilityMult;

    TileGrid* grid = WorldContext->tileGrid;
    Tile* actorTile = actor->GetCurrentTile();       // vtable +0x388
    float skillAPCost = skill->apCost;               // skill +0xbc
    int totalReach = self->m_MinRangeToOpponents + (int)skillAPCost;

    // Clear both tile sets
    HashSet_Clear(self->m_PossibleOriginTiles /*+0x70*/);
    HashSet_Clear(self->m_PossibleTargetTiles /*+0x78*/);

    // Get team member list
    List<Actor>* teamMembers = agentContext->entity->teamMembers;  // entity +0x20

    // --- Ally iteration ---
    foreach (Actor* ally in teamMembers)
    {
        if (ally->isDead /*+0x162*/) continue;

        Tile* allyTile = ally->GetCurrentTile();  // vtable +0x388
        int distToAlly = TileGrid_Distance(actorTile, allyTile);  // FUN_1805ca7a0

        if (!IsAllyTargetRequired(skill))  // FUN_1806e3af0 == false → self-cast
        {
            // Self-cast fast path: ally tile IS the origin
            HashSet_Add(self->m_PossibleOriginTiles, allyTile);  // FUN_181705350
        }
        else
        {
            // Vehicle/positioned path: grid search around ally tile
            if (entity->shotGroupMode != 0 || entity->isImmobile)
            {
                // 2D grid search radius = m_MinRangeToOpponents around allyTile
                for (int x = allyTile.x - reach; x <= allyTile.x + reach; x++)
                for (int y = allyTile.y - reach; y <= allyTile.y + reach; y++)
                {
                    Tile* t = TileGrid_GetTile(grid, x, y);  // FUN_1810c1fc0
                    if (SkillCanFireFrom(skill, t, weaponID))  // FUN_1806e3c50
                        HashSet_Add(self->m_PossibleOriginTiles, t);
                }
            }
            else
            {
                // Normal path: 2D grid around ally tile, range = totalReach
                for (int x = allyTile.x - totalReach; x <= allyTile.x + totalReach; x++)
                for (int y = allyTile.y - totalReach; y <= allyTile.y + totalReach; y++)
                {
                    Tile* t = TileGrid_GetTile(grid, x, y);

                    // Passability: tile flags bits 0,1,2 must all be 0
                    if ((t->flags /*+0x1c*/ & 0x7) != 0) continue;

                    // If occupied by non-friendly and not actor's tile: skip
                    if (t != actorTile && !IsTileOccupied(t))
                    {
                        Actor* occupant = GetOccupant(t);
                        if (!IsFriendly(actor, occupant)) continue;
                    }

                    // Must be within skill range of ally
                    if (TileGrid_Distance(t, allyTile) > totalReach) continue;

                    // Must be reachable by actor given remaining AP
                    int approachBudget = clamp(WeightsConfig->maxApproachRange /*+0xc4*/,
                                               0, (int)skillAPCost - distToAlly);
                    if (TileGrid_Distance(t, actorTile) > approachBudget + distToAlly) continue;

                    HashSet_Add(self->m_PossibleOriginTiles, t);  // FUN_181705350

                    if (!IsAllyTargetRequired(skill))
                        HashSet_Add(self->m_PossibleTargetTiles, t);  // FUN_181705350
                }
            }
        }
    }

    // --- AP accounting (identical to Attack.OnCollect) ---
    int primaryAP = GetSkillAPCost(skill);
    int reservedAP = primaryAP;
    // [secondary/setup skill AP addition — same flags and logic as Attack]

    // --- Score accumulation (nested origin × target loop) ---
    foreach (Tile* originTile in self->m_PossibleOriginTiles)
    {
        foreach (Tile* targetTile in self->m_PossibleTargetTiles)
        {
            if (!SkillCanFireFrom(skill, targetTile, originTile, weaponID)) continue;

            if (entity->shotGroupMode != 0 || entity->isImmobile)
            {
                BuildCandidatesForShotGroup(skill, originTile, targetTile,
                    self->m_Candidates /*param_1[0xd]*/, immobileFlag);

                float shotScore = 0.0f;
                foreach (Tile* candidate in m_Candidates)
                {
                    if (!SkillCanTarget(skill, candidate)) continue;

                    // [Same direct/indirect branching as Attack.OnCollect]
                    float rawScore = GetTargetValue_Dispatch7(
                        0x11, self, /*isCoFire=*/0, skill, candidate, originTile, actorTile);

                    // Arc scaling (mode 1) — same formula
                    if (entity->shotGroupMode == 1) { /* arc scale */ }

                    shotScore -= rawScore;
                    if (candidate == actorTile && IsDoubleFire(skill)) shotScore -= rawScore;
                }

                // Write candidate entry
                float finalScore = self->GetUtilityFromTileMult()
                                 * shotScore * local_160
                                 * WeightsConfig->baseAttackWeightScale /*+0xc0*/
                                 * (IsInflictDamageSubclass ? 2.0f : 1.0f);

                Assist_Data* entry = GetOrCreateCandidate(tileDict, originTile);
                entry->score = max(entry->score, finalScore);  // +0x30
            }
            // [Non-vehicle path analogous — uses same FUN_18000c5b0 accumulation]
        }
    }

    // --- Movement score integration (identical to Attack.OnCollect) ---
    foreach ((Tile* t, TileScore* ts) in tileDict)
    {
        if (ts->utilityScore <= 0.0f) continue;
        int available = (t == actorTile) ? reservedAP : primaryAP;
        ts->apCost = min(ts->apCost, available);
        float best = max(ts->movementScore, ts->secondaryMovementScore);
        ts->movementScore = best;
        ts->secondaryMovementScore = 0.0f;
    }

    return true;
}
```

---

## 9. Assist.OnEvaluate — 0x180731C60

### Annotated reconstruction
```c
// Scores all assist candidates and returns final integer score
// Structure mirrors Attack.OnEvaluate; key differences noted
int Assist_OnEvaluate(Assist* self, Actor* actor)
{
    // IL2CPP lazy init — omitted

    // --- Pre-flight guards ---
    if (self->agentContext->isDead) return 0;
    if (actor->GetCurrentAP() < 2) return 0;
    if (!IsSkillReadyToFire(skill)) return 0;              // FUN_1806e3310 — called BEFORE weapon compat
    if (!IsWeaponTypeCompatible(skill, weaponID)) return 0;  // FUN_1806e3d50
    if (!HandleDeployAndSetup(self, actor)) return 0;      // FUN_18073df70
    if (skill->entityInfo->weaponData == null) goto NullTrap;

    // --- Tile utility and AoE blend (identical to Attack) ---
    Tile* actorTile = actor->GetCurrentTile();
    ConsiderSkillSpecifics(self);
    float tileUtilityMult = self->GetUtilityFromTileMult();  // vtable +0x238
    if (tileUtilityMult <= 0.0f) return 0;

    if (IsAoeSkill(skill) && skill->aoeMaxCount > 0)
        tileUtilityMult = (skill->aoeCurrentCount / (float)skill->aoeMaxCount) * 0.5f
                        + tileUtilityMult * 0.5f;

    List<Actor>* teamMembers = agentContext->entity->teamMembers;  // entity +0x20

    EntityInfo* entity = skill->entityInfo;
    bool isVehicle = (entity->shotGroupMode != 0)
                  || (entity->isImmobile && self->m_MinRangeToOpponents > 0);

    if (isVehicle)
    {
        // --- Vehicle / positioned path ---
        HashSet_Clear(self->m_PossibleOriginTiles);

        if (!IsAllyTargetRequired(skill))  // FUN_1806e3af0 == false
        {
            // Self-cast: only actor's own tile
            HashSet_Add(self->m_PossibleOriginTiles, actorTile);
        }
        else
        {
            // Iterate team, grid-search around each ally tile, add valid origin tiles
            foreach (Actor* ally in teamMembers)
            {
                if (ally->isDead || ally == actor) continue;
                Tile* allyTile = ally->GetCurrentTile();
                // 2D grid search around allyTile with radius m_MinRangeToOpponents
                for each grid cell t:
                    if (SkillCanFireFrom(skill, t, weaponID))
                        HashSet_Add(self->m_PossibleOriginTiles, t);
            }
        }

        // Score each origin tile via shot group pipeline
        foreach (Tile* originTile in self->m_PossibleOriginTiles)
        {
            if (!SkillCanFireFrom(skill, originTile, weaponID)) continue;

            BuildCandidatesForShotGroup(skill, actorTile, originTile,
                self->m_Candidates, immobileFlag);

            float tileScore = 0.0f;
            foreach (Tile* candidate in m_Candidates)
            {
                if (!SkillCanTarget(skill, candidate)) continue;
                // [Same direct/indirect branching as Attack.OnEvaluate]
                // isCoFire = 1 always for Assist
                float rawScore = self->vtable[0x248](self, /*isCoFire=*/1, skill, candidate, ...);
                // Arc scaling same as Attack
                tileScore += rawScore;
            }

            // Accumulate into candidate
            Assist_Data* entry = GetOrCreateCandidate(tileDict, originTile);
            entry->score = accumulate(entry->score, tileScore, ...);
        }
    }
    else
    {
        // --- Normal unit path ---
        // Iterate team members directly (no m_PossibleOriginTiles population here)
        foreach (Actor* ally in teamMembers)
        {
            if (ally->isDead || ally == actor) continue;
            Tile* allyTile = ally->GetCurrentTile();

            if (!SkillCanFireFrom(skill, allyTile, weaponID)) continue;   // FUN_1806e3c50
            if (!SkillCanTarget(skill, allyTile)) continue;                // FUN_1806e33a0

            // Call GetTargetValue directly (5-arg form; no secondary tile)
            // isCoFire = 1 always
            float rawScore = self->vtable[0x248](self, /*isCoFire=*/1, skill, allyTile, extraArg);

            if (rawScore <= 0.0f) continue;

            // Movement cost scaling (identical to Attack.OnEvaluate)
            if (!IsSkillSelfTargeting(skill))  // FUN_1806e35d0
            {
                int moveCost = TileGrid_Distance(actorTile, allyTile);  // FUN_1805ca720 + FUN_1805df170
                if (moveCost > 0)
                {
                    int maxAP = actor->GetMaxAP();  // vtable +0x458
                    rawScore *= (1.0f - (float)moveCost / (float)maxAP);
                }
            }

            // HP-ratio scalar for indirect tile resolution
            Tile* resolvedTile = Skill_ResolveEffectiveTile(skill, actorTile, allyTile);  // FUN_1806e09e0
            if (resolvedTile != actorTile)
            {
                TileScore* originScore = tileDict->TryGetValue(actorTile);
                TileScore* resolvedScore = tileDict->TryGetValue(resolvedTile);
                if (originScore != null && resolvedScore != null)
                {
                    float denominator = resolvedScore->exposureScore /*+0x28*/
                                      + resolvedScore->rangeScore /*+0x30*/;
                    if (denominator != 0.0f)
                    {
                        float ratio = ABS((originScore->exposureScore + originScore->rangeScore)
                                          / denominator);
                        ratio = clamp(ratio, 0.25f, 2.0f);
                        rawScore *= ratio;
                    }
                }
            }

            // AoE distribution (mode 2)
            if (entity->shotGroupMode == 2)
                rawScore /= (float)m_Candidates.count;  // param_1[0xd] +0x18

            // Store candidate
            Assist_Data* entry = GetOrCreateCandidate(tileDict, allyTile);  // FUN_18000c5b0
            entry->score = accumulate(entry->score, rawScore);
        }
    }

    // --- Winner selection ---
    if (self->m_Candidates->count == 0) return 0;

    Assist_Data best = GetHighestScoredTarget(self);
    Tile* bestTarget = best.targetRef;
    float bestScore = best.score;

    // AoE threshold gate
    if (IsAoeSkill(skill))
        if (bestScore <= WeightsConfig->minAoeScoreThreshold /*+0xfc*/) return 0;

    // Store chosen target (same slot as Attack)
    self->chosenTarget /*param_1[0xb]*/ = bestTarget;

    // NOTE: No reposition flag (+0x4f) is ever set for Assist

    // AP feasibility check (identical to Attack — omitted for brevity)
    // Secondary skill check (identical — omitted)
    // Movement score integration (identical — omitted)

    // Weapon setup bonus
    if (entity->hasSetupWeapon /*+0x113*/ && actor->isWeaponSetUp /*+0x167*/)
        tileUtilityMult *= 1.1f;

    // Delayed-move penalty
    if (/* move state conditions */) tileUtilityMult *= 0.25f;

    return (int)(bestScore * tileUtilityMult);
}
```

---

*End of Stage 3 Reconstructions*
