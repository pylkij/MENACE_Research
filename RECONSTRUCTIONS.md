# Menace Tactical AI — Annotated Function Reconstructions

**Source:** Ghidra decompilation of Menace (Unity IL2CPP, Windows x64)
**Image base:** `0x180000000`
**Format:** Each function shows the raw Ghidra output, followed by a fully annotated C-style reconstruction with all offsets resolved against the field tables in REPORT.md.

---

## Table of Contents

1. [TileScore.GetScore — 0x180740F20](#1-tilescoregetscore--0x180740f20)
2. [TileScore.GetScaledScore — 0x180740E50](#2-tilescoregetscaledscore--0x180740e50)
3. [TileScore.GetScoreWithoutDistance — 0x180740F10](#3-tilescoregetsscorewithoutdistance--0x180740f10)
4. [TileScore.CompareScores — 0x180740D40](#4-tilescorecomparescores--0x180740d40)
5. [TacticalStateSettings.GetScore — 0x180756DE0](#5-tacticalstatesettingsgetscore--0x180756de0)
6. [TacticalStateSettings.Start — 0x180757530](#6-tacticalstatesettingsstart--0x180757530)
7. [TacticalStateSettings.OnAIDestinationOnlyChanged — 0x180756EA0](#7-tacticalstatesettingsonaidestinationonlychanged--0x180756ea0)
8. [TacticalStateSettings.DrawHeatmap — 0x180756180](#8-tacticalstatesettingsdrawheatmap--0x180756180)
9. [TacticalState.Get — 0x180648D90](#9-tacticalstateget--0x180648d90)
10. [Agent.GetThreatLevel — 0x18071B240](#10-agentgetthreatLevel--0x18071b240)
11. [Agent.GetOpportunityLevel — 0x18071ABC0](#11-agentgetopportunitylevel--0x18071abc0)
12. [Agent.GetScoreMultForPickingThisAgent — 0x18071AE50](#12-agentgetscoremultforpickingthisagent--0x18071ae50)
13. [Agent.PickBehavior — 0x18071BD20](#13-agentpickbehavior--0x18071bd20)
14. [Agent.Evaluate — 0x180719860](#14-agentevaluate--0x180719860)
15. [Agent.PostProcessTileScores — 0x18071C450](#15-agentpostprocesstilescores--0x18071c450)

---

## Offset Reference (quick lookup)

### TileScore instance offsets
```
+0x10  Tile             Tile
+0x18  Tile             UltimateTile
+0x20  float            DistanceToCurrentTile
+0x24  float            DistanceScore
+0x28  float            SafetyScore            ← STORED NEGATIVE after PostProcess
+0x2C  float            SafetyScoreScaled
+0x30  float            UtilityScore
+0x34  float            UtilityScoreScaled
+0x38  float            UtilityByAttacksScore
+0x3C  float            UtilityByAttacksScoreCandidate
+0x40  int              APCost
+0x44  int              MinimumUtilityAPCost
+0x48  List<Vector3>    Path
+0x50  TileScore        HighestSafetyNeighbor
+0x58  TileScore        HighestUtilityNeighbor
```

### Agent instance offsets
```
+0x10  AIFaction        m_Faction
+0x18  Actor            m_Actor
+0x20  List<Behavior>   m_Behaviors
+0x28  Behavior         m_ActiveBehavior
+0x30  int              m_Score
+0x34  float            m_Priority
+0x38  int              m_NumThreatsFaced
+0x3C  Agent.State      m_State      (0=None,1=Evaluating,2=Scored,3=Done)
+0x40  PseudoRandom     m_Random
+0x48  int              m_Iterations
+0x4C  float            m_SleepUntil
+0x50  bool             m_IsDeployed
+0x51  bool             m_IsSleeping
+0x54  uint             m_Flags      (bit 0 = neighbor propagation enabled)
+0x58  Dict<Tile,TS>    m_Tiles
+0x60  Dict<Tile,TS>    m_TilesToBeUsed
+0x68  List<Task>       m_Tasks
+0x70  string           m_QueuedDebugString
+0x78  bool             FlaggedForDeactivation
```

### AIWeightsTemplate critical offsets (via DebugVisualization.WEIGHTS)
```
+0x20  float  UtilityPOW
+0x24  float  UtilityScale
+0x28  float  UtilityPostPOW
+0x2C  float  UtilityPostScale
+0x30  float  SafetyPOW
+0x34  float  SafetyScale
+0x38  float  SafetyPostPOW
+0x3C  float  SafetyPostScale
+0x40  float  DistanceScale        ← also used as SafetyScore negation factor
+0x44  float  DistancePickScale
+0x48  float  ThreatLevelPOW
+0x4C  float  OpportunityLevelPOW
+0x50  float  PickingScoreMultPOW
```

### IL2CPP patterns used throughout
```
DAT_18394c3d0          = DebugVisualization class static
DAT_183981f50          = TacticalState class static
DAT_1839820c0          = TacticalState class static (in Get())
*(classStatic + 0xb8)  = static field storage pointer
*(fieldStorage + 0x00) = s_Singleton (TacticalState)
*(fieldStorage + 0x08) = WEIGHTS (AIWeightsTemplate)
*(classStatic + 0xe4)  = class init flag (0 = not yet initialised)
FUN_180427b00          = il2cpp_runtime_class_init()
FUN_180427d90          = NullReferenceException() / throws, does not return
FUN_1804bad80          = powf(float value, float exponent)
```

---

## 1. TileScore.GetScore — 0x180740F20

### Raw Ghidra output
```c
float FUN_180740f20(longlong param_1)
{
  float fVar1;
  float fVar2;
  float fVar3;
  float fVar4;
  longlong lVar5;
  
  if (DAT_183b931dd == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    DAT_183b931dd = '\x01';
  }
  fVar1 = *(float *)(param_1 + 0x30);
  fVar2 = *(float *)(param_1 + 0x28);
  fVar3 = *(float *)(param_1 + 0x20);
  fVar4 = *(float *)(param_1 + 0x24);
  if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
    il2cpp_runtime_class_init(DAT_18394c3d0);
  }
  lVar5 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
  if (lVar5 != 0) {
    return (fVar2 + fVar1) - (fVar4 + fVar3) * *(float *)(lVar5 + 0x40);
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
float TileScore_GetScore(TileScore* self)
{
    // IL2CPP lazy static init for DebugVisualization class
    if (!DebugVisualization_classInitFlag) {
        il2cpp_runtime_class_init(&DebugVisualization_class);
        DebugVisualization_classInitFlag = true;
    }

    // Load the four relevant TileScore fields:
    float utilityScore          = self->UtilityScore;           // +0x30
    float safetyScore           = self->SafetyScore;            // +0x28  (negative after PostProcess)
    float distanceToCurrentTile = self->DistanceToCurrentTile;  // +0x20
    float distanceScore         = self->DistanceScore;          // +0x24

    // Resolve the weight:
    // DebugVisualization class static (+0xb8) → static field storage pointer
    // field storage + 0x08 = WEIGHTS (AIWeightsTemplate instance)
    // WEIGHTS + 0x40 = DistanceScale
    AIWeightsTemplate* weights = DebugVisualization.WEIGHTS;  // *(staticStorage + 8)
    if (weights == null) NullReferenceException();

    float distanceScale = weights->DistanceScale;  // +0x40

    // THE SCORING FORMULA:
    // SafetyScore is already negative (see PostProcessTileScores).
    // Adding it to UtilityScore subtracts threat penalty from utility value.
    // Distance terms are an additional AP-cost penalty, weighted by DistanceScale.
    return (safetyScore + utilityScore)
           - (distanceScore + distanceToCurrentTile) * distanceScale;
}
```

---

## 2. TileScore.GetScaledScore — 0x180740E50

### Raw Ghidra output
```c
float FUN_180740e50(longlong param_1)
{
  float fVar1;
  float fVar2;
  float fVar3;
  float fVar4;
  longlong lVar5;
  
  if (DAT_183b931de == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    DAT_183b931de = '\x01';
  }
  fVar1 = *(float *)(param_1 + 0x34);
  fVar2 = *(float *)(param_1 + 0x2c);
  fVar3 = *(float *)(param_1 + 0x20);
  fVar4 = *(float *)(param_1 + 0x24);
  if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
    il2cpp_runtime_class_init(DAT_18394c3d0);
  }
  lVar5 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
  if (lVar5 != 0) {
    return (fVar2 + fVar1) - (fVar4 + fVar3) * *(float *)(lVar5 + 0x44);
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
float TileScore_GetScaledScore(TileScore* self)
{
    // Same structure as GetScore(), but uses:
    //   UtilityScoreScaled (+0x34) instead of UtilityScore (+0x30)
    //   SafetyScoreScaled  (+0x2C) instead of SafetyScore  (+0x28)
    //   DistancePickScale  (+0x44) instead of DistanceScale (+0x40)
    // Distance inputs (DistanceToCurrentTile, DistanceScore) are unchanged.

    float utilityScoreScaled    = self->UtilityScoreScaled;     // +0x34
    float safetyScoreScaled     = self->SafetyScoreScaled;      // +0x2C
    float distanceToCurrentTile = self->DistanceToCurrentTile;  // +0x20
    float distanceScore         = self->DistanceScore;          // +0x24

    AIWeightsTemplate* weights = DebugVisualization.WEIGHTS;
    float distancePickScale = weights->DistancePickScale;  // +0x44

    return (safetyScoreScaled + utilityScoreScaled)
           - (distanceScore + distanceToCurrentTile) * distancePickScale;
}
```

**Note:** Distance is never scaled — only safety and utility have scaled variants. The "scaled" versions are produced by the same POW/Scale pipeline in `PostProcessTileScores` applied to the same raw inputs, but the result is stored separately in `SafetyScoreScaled`/`UtilityScoreScaled`. The mechanism that populates these separately from the non-scaled fields is in `PostProcessTileScores` but uses the same pipeline; the distinction between "Score" and "ScoreScaled" storage appears to be a checkpoint for inspection, not a fundamentally different calculation.

---

## 3. TileScore.GetScoreWithoutDistance — 0x180740F10

### Raw Ghidra output
```c
float UndefinedFunction_180740f10(longlong param_1)
{
  return *(float *)(param_1 + 0x30) + *(float *)(param_1 + 0x28);
}
```

### Annotated reconstruction
```c
float TileScore_GetScoreWithoutDistance(TileScore* self)
{
    // No weights, no distance terms. Pure utility + safety.
    // Used for UltimateTile evaluation: when scoring a waypoint destination
    // rather than a movement tile, AP cost is irrelevant.
    // SafetyScore is still negative here (post-processed value).
    return self->UtilityScore   // +0x30
         + self->SafetyScore;   // +0x28  (negative = threat penalty)
}
```

**Note:** Ghidra marks this as `UndefinedFunction` because the function is tiny (two instructions) and Ghidra may not have analysed it as a proper function boundary. The name comes from the dump.cs method list at this RVA.

---

## 4. TileScore.CompareScores — 0x180740D40

### Raw Ghidra output
```c
ulonglong FUN_180740d40(longlong param_1, longlong param_2)
{
  float fVar1;
  float fVar2;
  
  if (param_1 != 0) {
    fVar1 = (float)FUN_180740f20(param_1,0);
    if (param_2 != 0) {
      fVar2 = (float)FUN_180740f20(param_2,0);
      if (fVar1 <= fVar2) {
        fVar1 = (float)FUN_180740f20(param_1,0);
        fVar2 = (float)FUN_180740f20(param_2,0);
        return (ulonglong)(fVar1 < fVar2);
      }
      return 0xffffffff;
    }
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
int TileScore_CompareScores(TileScore* a, TileScore* b)
{
    // Null guard — either null throws.
    if (a == null || b == null) NullReferenceException();

    float scoreA = TileScore_GetScore(a);
    float scoreB = TileScore_GetScore(b);

    // Standard IComparer contract: negative = a < b, positive = a > b, zero = equal.
    // Returns 0xFFFFFFFF (-1 as signed int) when a > b → a sorts BEFORE b.
    // Returns 1 when a < b → b sorts before a.
    // Returns 0 when equal.
    // Net result: DESCENDING sort — highest GetScore() wins.
    if (scoreA > scoreB) return -1;       // 0xFFFFFFFF
    if (scoreA < scoreB) return 1;
    return 0;

    // Note: GetScore() is called TWICE in the equal-or-less branch (lines 8-9 raw).
    // This is a Ghidra decompilation artefact of an inlined comparison — not two
    // actual function calls at runtime. The compiled code evaluates once.
}
```

---

## 5. TacticalStateSettings.GetScore — 0x180756DE0

### Raw Ghidra output
```c
ulonglong FUN_180756de0(longlong param_1, longlong param_2)
{
  ulonglong uVar1;
  
  switch(*(undefined4 *)(param_1 + 0x24)) {
  case 1:
    if (param_2 != 0) {
      uVar1 = FUN_180740f20(param_2,0);
      return uVar1;
    }
    break;
  case 2:
    if (param_2 != 0) {
      uVar1 = FUN_180740e50(param_2,0);
      return uVar1;
    }
    break;
  case 3:
    if (param_2 != 0) {
      return (ulonglong)*(uint *)(param_2 + 0x30);
    }
    break;
  case 4:
    if (param_2 != 0) {
      return (ulonglong)*(uint *)(param_2 + 0x28);
    }
    break;
  case 5:
    if (param_2 != 0) {
      return (ulonglong)*(uint *)(param_2 + 0x2c);
    }
    break;
  case 6:
    if (param_2 != 0) {
      return (ulonglong)(uint)(*(float *)(param_2 + 0x20) * -100.0);
    }
    break;
  default:
    return 0;
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
float TacticalStateSettings_GetScore(TacticalStateSettings* self, TileScore* ts)
{
    // self->ShowHeatmap is at offset +0x24 (DebugVisualization enum)
    switch (self->ShowHeatmap) {

    case 1: // TotalScore
        if (ts == null) NullReferenceException();
        return TileScore_GetScore(ts);

    case 2: // TotalScoreScaled
        if (ts == null) NullReferenceException();
        return TileScore_GetScaledScore(ts);

    case 3: // Utility
        if (ts == null) NullReferenceException();
        return ts->UtilityScore;          // +0x30

    case 4: // Safety
        if (ts == null) NullReferenceException();
        return ts->SafetyScore;           // +0x28  (negative = threat; heatmap shows raw value)

    case 5: // SafetyScaled
        if (ts == null) NullReferenceException();
        return ts->SafetyScoreScaled;     // +0x2C

    case 6: // Distance
        if (ts == null) NullReferenceException();
        // DistanceToCurrentTile (+0x20) is an AP cost — positive, raw.
        // Multiplied by -100.0 for display:
        //   - Negates it (distance is a penalty; this makes it positive for heatmap coloring)
        //   - Scales by 100 to put it in a human-readable range
        return ts->DistanceToCurrentTile * -100.0f;  // +0x20

    default: // None (0) or any unknown value
        return 0.0f;
    }
}
```

---

## 6. TacticalStateSettings.Start — 0x180757530

### Raw Ghidra output
```c
void FUN_180757530(longlong param_1)
{
  undefined4 uVar1;
  longlong lVar2;
  int iVar3;
  undefined8 uVar4;
  
  if (DAT_183b9233f == '\0') {
    FUN_180427b00(&DAT_183981f50);
    DAT_183b9233f = '\x01';
  }
  if (**(longlong **)(DAT_183981f50 + 0xb8) != 0) {
    if (DAT_183b9233f == '\0') {
      FUN_180427b00(&DAT_183981f50);
      DAT_183b9233f = '\x01';
    }
    if (**(longlong **)(DAT_183981f50 + 0xb8) != 0) {
      if (DAT_183b9233f == '\0') {
        FUN_180427b00(&DAT_183981f50);
        DAT_183b9233f = '\x01';
      }
      if ((**(longlong **)(DAT_183981f50 + 0xb8) == 0) ||
         (lVar2 = *(longlong *)(**(longlong **)(DAT_183981f50 + 0xb8) + 0x28), lVar2 == 0))
      goto LAB_180757712;
      FUN_180634b80(lVar2,*(undefined1 *)(param_1 + 0x20),0);
    }
    if (DAT_183b931ff == '\0') {
      FUN_180427b00(&DAT_18394c3d0);
      FUN_180427b00(&DAT_183977ab8);
      DAT_183b931ff = '\x01';
    }
    if (DAT_183b9233f == '\0') {
      FUN_180427b00(&DAT_183981f50);
      DAT_183b9233f = '\x01';
    }
    if (**(longlong **)(DAT_183981f50 + 0xb8) != 0) {
      if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
        il2cpp_runtime_class_init();
      }
      if (**(int **)(DAT_18394c3d0 + 0xb8) != *(int *)(param_1 + 0x24)) {
        if (*(longlong *)(param_1 + 0x30) == 0) {
LAB_180757712:
          FUN_180427d90();
        }
        uVar4 = FUN_1829a21f0(*(longlong *)(param_1 + 0x30),0);
        FUN_1808c9500(uVar4,0);
        uVar1 = *(undefined4 *)(param_1 + 0x24);
        if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
          il2cpp_runtime_class_init(DAT_18394c3d0);
        }
        **(undefined4 **)(DAT_18394c3d0 + 0xb8) = uVar1;
        if ((*(int *)(param_1 + 0x24) != 0) && (*(longlong *)(param_1 + 0x50) != 0)) {
          iVar3 = FUN_181372b50(*(undefined8 *)(param_1 + 0x50),DAT_183977ab8);
          if (iVar3 != 0) {
            FUN_180756180(param_1,*(undefined8 *)(param_1 + 0x50),0);
            return;
          }
        }
      }
    }
  }
  return;
}
```

### Annotated reconstruction
```c
void TacticalStateSettings_Start(TacticalStateSettings* self)
{
    // ── IL2CPP triple-checked lazy static init (standard IL2CPP pattern) ──
    // DAT_183981f50 = TacticalState class static pointer
    // DAT_183b9233f = TacticalState class init flag
    // The repeated triple-check is IL2CPP's thread-safe lazy initialisation.
    if (!TacticalState_classInitFlag) {
        il2cpp_runtime_class_init(&TacticalState_class);
        TacticalState_classInitFlag = true;
    }

    // ── Get TacticalState singleton ─────────────────────────────────────
    // *(TacticalState_classStatic + 0xb8) = static field storage pointer
    // *staticStorage = s_Singleton instance
    TacticalState* state = **(TacticalState_class.staticFields);
    if (state == null) return;

    // ── Register OnFogOfWarChanged callback ─────────────────────────────
    // state->m_CurrentTile is at TacticalState+0x28
    // FUN_180634b80 = property change event registration
    // The callback registers on some event/delegate on m_CurrentTile.
    // self->ShowFogOfWar (+0x20) is the value being watched.
    // Third arg (0) = event type or callback slot index.
    if (state == null || state->m_CurrentTile == null)
        goto NullRef;  // LAB_180757712
    RegisterChangeCallback(state->m_CurrentTile, self->ShowFogOfWar, 0);
    //                                             ^^^ +0x20

    // ── Init DebugVisualization and DebugVisualizationFilter classes ─────
    // DAT_18394c3d0 = DebugVisualization class static
    // DAT_183977ab8 = DebugVisualizationFilter class static
    if (!DebugViz_classInitFlag) {
        il2cpp_runtime_class_init(&DebugVisualization_class);
        il2cpp_runtime_class_init(&DebugVisualizationFilter_class);
        DebugViz_classInitFlag = true;
    }

    // ── Check if ShowHeatmap has changed ────────────────────────────────
    // **(DebugVisualization_class + 0xb8) = static field storage
    // static field at +0x00 = the currently committed ShowHeatmap enum value
    // self->ShowHeatmap (+0x24) = the inspector-visible desired value
    int committedShowHeatmap = **DebugVisualization_class.staticFields;
    if (committedShowHeatmap != self->ShowHeatmap) {
        //                              ^^^ +0x24

        // ── Null guard HeatmapParent (+0x30) ────────────────────────────
        if (self->HeatmapParent == null)
            goto NullRef;

        // ── Destroy existing heatmap tokens ─────────────────────────────
        // FUN_1829a21f0 = likely GetComponentsInChildren<Transform>() or
        //                 equivalent child-gathering function.
        // FUN_1808c9500 = Destroy() or DestroyImmediate() on the result.
        var children = GetComponentsInChildren(self->HeatmapParent, 0);
        Destroy(children, 0);

        // ── Commit new ShowHeatmap value to static ───────────────────────
        **DebugVisualization_class.staticFields = self->ShowHeatmap;

        // ── Conditionally call DrawHeatmap ───────────────────────────────
        // Conditions:
        //   1. ShowHeatmap != None (0)
        //   2. m_Tiles (+0x50) is not null
        //   3. m_Tiles is not empty (FUN_181372b50 = Dictionary.Count or similar)
        if (self->ShowHeatmap != 0 && self->m_Tiles != null) {
            //                                ^^^ +0x50
            int tileCount = GetCount(self->m_Tiles, DebugVisualizationFilter_class);
            if (tileCount != 0) {
                DrawHeatmap(self, self->m_Tiles, 0);  // FUN_180756180
                return;
            }
        }
    }

    return;

NullRef:
    NullReferenceException();  // FUN_180427d90 — does not return
}
```

---

## 7. TacticalStateSettings.OnAIDestinationOnlyChanged — 0x180756EA0

### Raw Ghidra output
```c
void FUN_180756ea0(longlong param_1)
{
  undefined4 uVar1;
  
  if (DAT_183b93200 == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    DAT_183b93200 = '\x01';
  }
  uVar1 = *(undefined4 *)(param_1 + 0x28);
  if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
    il2cpp_runtime_class_init(DAT_18394c3d0);
  }
  *(undefined4 *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 4) = uVar1;
  return;
}
```

### Annotated reconstruction
```c
void TacticalStateSettings_OnAIDestinationOnlyChanged(TacticalStateSettings* self)
{
    // Init DebugVisualization class if needed
    if (!DebugViz_classInitFlag) {
        il2cpp_runtime_class_init(&DebugVisualization_class);
        DebugViz_classInitFlag = true;
    }

    // Read self->Filter (DebugVisualizationFilter enum at offset +0x28)
    DebugVisualizationFilter filterValue = self->Filter;  // +0x28

    // Write to DebugVisualization static field at offset +0x04
    // This is the globally-visible current filter value used by DrawHeatmap.
    // *(DAT_18394c3d0 + 0xb8) = static field storage pointer
    // field storage + 4 = static DebugVisualizationFilter slot
    DebugVisualization.staticFields->currentFilter = filterValue;  // +0x04 in static storage

    // Note on method name: "OnAIDestinationOnlyChanged" is a legacy name.
    // The actual field it watches is `Filter` (DebugVisualizationFilter enum).
    // "DestinationOnly" was the old name for the `Destinations` enum value.
}
```

---

## 8. TacticalStateSettings.DrawHeatmap — 0x180756180

### Raw Ghidra output
```c
void FUN_180756180(longlong param_1, longlong param_2)
{
  // [full 450-line output — see GhidraAddressLookupRESULTS.txt lines 59–512]
  // Key variables:
  //   param_1 = TacticalStateSettings* self
  //   param_2 = Dictionary<Tile, TileScore>* _tiles  (m_Tiles passed from caller)
  //   fVar12  = running maximum score (for normalization)
  //   fVar14  = running minimum score (for normalization, stored as negative)
  //   fVar10  = per-tile score (current tile)
  //   iVar9   = color index into HeatmapColors list
  //   lVar5   = Transform component of instantiated HeatmapToken
  //   lVar8   = Tile key (current iteration)
  //   lStack_168 = TileScore value (current iteration)
}
```

### Annotated reconstruction
```c
void TacticalStateSettings_DrawHeatmap(TacticalStateSettings* self,
                                       Dictionary<Tile, TileScore>* _tiles)
{
    // ── Guard: HeatmapParent and HeatmapToken must not be destroyed ──────
    // FUN_1829a91b0 = Object.IsNativeObjectAlive() or equivalent null/destroyed check
    // DAT_18394df48 = UnityEngine.Object class static (for IsNativeObjectAlive)
    // self->HeatmapParent (+0x30), self->HeatmapToken (+0x38)
    if (!IsAlive(self->HeatmapParent)) return;  // +0x30
    if (!IsAlive(self->HeatmapToken))  return;  // +0x38

    // ── Guard: TacticalState singleton must exist ────────────────────────
    TacticalState* state = TacticalState.s_Singleton;
    if (state == null) return;

    // ── Store tiles reference ────────────────────────────────────────────
    // self->m_Tiles (+0x50) = param_2 (the dictionary passed in)
    // FUN_180426e50 = IL2CPP write barrier (GC notification)
    self->m_Tiles = _tiles;  // +0x50
    WriteBarrier(self->m_Tiles, _tiles);

    // ── Destroy existing tokens ──────────────────────────────────────────
    // FUN_1829a21f0 = GetComponentsInChildren<Transform>() or equivalent
    // FUN_1808c9500 = DestroyImmediate() on the array of transforms
    if (self->HeatmapParent != null) {
        var existingChildren = GetComponentsInChildren(self->HeatmapParent, 0);
        DestroyImmediate(existingChildren, 0);
    }

    // ── Early-out: no tiles to draw ──────────────────────────────────────
    if (_tiles == null) return;

    // ═══════════════════════════════════════════════════════════════════════
    // PASS 1: Compute normalization range (max and min scores)
    // ═══════════════════════════════════════════════════════════════════════
    // FUN_18136d8a0 = Dictionary.GetEnumerator()
    // FUN_18152f9b0 = Dictionary enumerator MoveNext()
    //   → lStack_168 = TileScore* (current value), local_170 = Tile (current key)
    // self->ShowHeatmap (+0x24) drives the same switch as TacticalStateSettings.GetScore()

    float maxScore = 0.0f;    // fVar12 — running max
    float minScore = float.MaxValue;  // fVar14 = 3.4028235e+38 (FLT_MAX)

    foreach (KeyValuePair<Tile, TileScore> kv in _tiles) {
        TileScore* ts = kv.Value;  // lStack_168

        // Read score for this tile using the same switch as GetScore()
        float tileScore;
        switch (self->ShowHeatmap) {  // +0x24
        case 1: tileScore = TileScore_GetScore(ts);        break;  // FUN_180740f20
        case 2: tileScore = TileScore_GetScaledScore(ts);  break;  // FUN_180740e50
        case 3: tileScore = ts->UtilityScore;              break;  // +0x30
        case 4: tileScore = ts->SafetyScore;               break;  // +0x28
        case 5: tileScore = ts->SafetyScoreScaled;         break;  // +0x2C
        case 6: tileScore = ts->DistanceToCurrentTile * -100.0f; break; // +0x20
        default: tileScore = 0.0f; break;
        }

        // Track running maximum
        if (maxScore < tileScore) {
            // Update maxScore using the SAME switch — reads from same TileScore
            // (Ghidra shows the switch twice; the second read is the committed update)
            maxScore = tileScore;  // same value, already computed above
        }

        // Track running minimum (third switch block in raw output)
        // fVar14 starts at FLT_MAX; updated when tileScore < current min
        if (tileScore < minScore) {
            minScore = 0.0f;  // reset to 0 first (raw: fVar14 = 0.0 before re-read)
            minScore = tileScore;
        }
    }

    // ── Compute effective min (for color normalization) ─────────────────
    // If minScore >= 0: clamp to 0 (no negative contribution)
    // If minScore < 0:  use abs(minScore * 0.75) as effective negative floor
    // This 0.75 factor softens the lower bound to avoid extreme color compression.
    float effectiveMin;
    if (minScore >= 0.0f) {
        effectiveMin = 0.0f;
    } else {
        effectiveMin = ABS(minScore * 0.75f);
    }

    // ── Compute effective max ────────────────────────────────────────────
    // self->HeatmapExpectedMaxValue (+0x40) is the inspector-set ceiling.
    // Take the larger of: (effectiveMin + maxScore) vs HeatmapExpectedMaxValue.
    float scoreRange = effectiveMin + maxScore;
    float effectiveMax = self->HeatmapExpectedMaxValue;  // +0x40
    if (effectiveMax <= scoreRange) {
        effectiveMax = scoreRange;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PASS 2: Instantiate and color one HeatmapToken per tile
    // ═══════════════════════════════════════════════════════════════════════

    foreach (KeyValuePair<Tile, TileScore> kv in _tiles) {
        TileScore* ts   = kv.Value;  // lStack_168 / lVar1
        Tile       tile = kv.Key;   // local_170 / lVar8

        // ── Instantiate HeatmapToken at tile position ────────────────────
        // FUN_1829a21f0 = GetComponentsInChildren (reused here to get Transform list)
        // FUN_180b11230(HeatmapToken, childTransforms, ObjectClass) = Instantiate
        // FUN_1829a21f0(instance) = get the instance's Transform
        // FUN_1805ca8d0(tile, enumerator, 0) = get tile world position (Vector3)
        //   local_1c0 = position enumerator/iterator
        //   puVar7 = pointer to Vector3 position data
        var tokenChildTransforms = GetComponentsInChildren(self->HeatmapParent, 0);
        var instance = Instantiate(self->HeatmapToken, tokenChildTransforms, ObjectClass);
        //                          ^^^ +0x38
        var instanceTransform = GetTransform(instance, 0);
        Vector3 tileWorldPos = GetTileWorldPosition(tile, &positionIterator);

        // ── Set token position ───────────────────────────────────────────
        // FUN_1829b6ca0(transform, &position, 0) = Transform.set_position(Vector3)
        instanceTransform.set_position(tileWorldPos);

        // ── Get tile's Transform for position data ───────────────────────
        // FUN_180ab6540(instance, ObjectClass) = some component getter
        // FUN_182978b10(component, 0) = get sub-component (likely the token's renderer)
        var tileComponent = GetComponent(instance, DAT_1839a07d8);
        var tokenRenderer = GetSubComponent(tileComponent, 0);  // lVar5

        // ── Compute this tile's score (same switch as Pass 1) ───────────
        float tileScore;
        switch (self->ShowHeatmap) {
        case 1: tileScore = TileScore_GetScore(ts);        break;
        case 2: tileScore = TileScore_GetScaledScore(ts);  break;
        case 3: tileScore = ts->UtilityScore;              break;
        case 4: tileScore = ts->SafetyScore;               break;
        case 5: tileScore = ts->SafetyScoreScaled;         break;
        case 6: tileScore = ts->DistanceToCurrentTile * -100.0f; break;
        default: tileScore = 0.0f; break;
        }

        // ── Normalize score to [0, 1] color range ───────────────────────
        // Shift by effectiveMin so negatives map to 0+
        // Divide by effectiveMax to get normalized position
        // Clamp to [0, effectiveMax]
        float shifted = tileScore + effectiveMin;
        if (shifted < 0.0f) shifted = 0.0f;
        if (shifted > effectiveMax) shifted = effectiveMax;

        // Map to color index in HeatmapColors list:
        // self->HeatmapColors (+0x48) = List<Color>
        // HeatmapColors.Count at *(HeatmapColors + 0x18)
        // normalized = (shifted / effectiveMax) × (colorCount - 1)
        int colorCount = self->HeatmapColors->Count;  // +0x48 → +0x18
        float normalized = (shifted / effectiveMax) * (float)(colorCount - 1);
        int colorIndex = (int)normalized;

        // ── Sample color from gradient ───────────────────────────────────
        // FUN_180cca630(&outColor, HeatmapColors, index, ColorClass) = List[index] getter
        // Two cases:
        //   a) colorIndex == colorCount-1: use exact last color (no interpolation)
        //   b) otherwise: lerp between color[colorIndex] and color[colorIndex+1]
        Color finalColor;
        if (colorIndex == colorCount - 1) {
            // Exact last color
            // FUN_18296ac80(renderer, &color, 0) = set renderer color
            finalColor = HeatmapColors[colorIndex];
            tokenRenderer.SetColor(finalColor);
        } else {
            // Lerp between adjacent colors
            // fVar13 = fractional part: ABS(floor(normalized) - normalized)
            // fVar12 = 1.0 - fVar13  (weight for lower color)
            // fVar13 = weight for upper color
            float frac = ABS(floorf(normalized) - normalized);
            Color colorLow  = HeatmapColors[colorIndex];      // local_1b0..local_1a0 (RGBA)
            Color colorHigh = HeatmapColors[colorIndex + 1];  // local_1a0..fStack_184

            // Component-wise lerp: result = colorLow*(1-frac) + colorHigh*frac
            // local_190 = R, fStack_18c = G, fStack_188 = B, fStack_184 = A
            // (CONCAT44 in raw output assembles float pairs into Color struct)
            finalColor.R = colorLow.R * (1.0f - frac) + colorHigh.R * frac;
            finalColor.G = colorLow.G * (1.0f - frac) + colorHigh.G * frac;
            finalColor.B = colorLow.B * (1.0f - frac) + colorHigh.B * frac;
            finalColor.A = colorLow.A * (1.0f - frac) + colorHigh.A * frac;

            // FUN_18296ac80(renderer, &color, 0) = set renderer color
            tokenRenderer.SetColor(finalColor);
        }

        // ── Position the token at the tile's world location ──────────────
        // FUN_1829794f0(tileComponent, tokenRenderer, 0) = SetPosition or parent assignment
        SetTokenPosition(tileComponent, tokenRenderer, 0);
    }
}
```

### DrawHeatmap — design notes

**Three passes of the ShowHeatmap switch.** The switch appears three times in the raw Ghidra output:
1. Pass 1 first switch — read score for max tracking
2. Pass 1 second switch — re-read score for max commit (Ghidra decompilation artefact of `fVar12 = max(fVar12, score)` inlined)
3. Pass 1 third switch — read score for min tracking
4. Pass 2 switch — read score per tile for normalization and coloring

All four reads use the identical dispatch. The score is not cached between passes.

**Color normalization formula:**
```
effectiveMin = max(0, abs(minScore * 0.75))   // soften negative floor
effectiveMax = max(HeatmapExpectedMaxValue, effectiveMin + maxScore)
normalized   = clamp(tileScore + effectiveMin, 0, effectiveMax) / effectiveMax
colorIndex   = floor(normalized × (colorCount - 1))
color        = lerp(HeatmapColors[colorIndex], HeatmapColors[colorIndex+1], frac)
```

The `0.75` factor on the negative minimum is intentional design — it prevents extreme negative scores (large threat penalties) from compressing the entire color range to one end.

**`HeatmapExpectedMaxValue` acts as a floor on the range**, not a ceiling. If the actual score range exceeds it, the actual range wins. This means setting it too low just widens the color ramp; it never clips scores.

---

## 9. TacticalState.Get — 0x180648D90

### Raw Ghidra output
```c
undefined8 FUN_180648d90(void)
{
  if (DAT_183b92b70 == '\0') {
    FUN_180427b00(&DAT_1839820c0);
    DAT_183b92b70 = '\x01';
  }
  if (*(int *)(DAT_1839820c0 + 0xe4) == 0) {
    il2cpp_runtime_class_init(DAT_1839820c0);
  }
  return **(undefined8 **)(DAT_1839820c0 + 0xb8);
}
```

### Annotated reconstruction
```c
TacticalState* TacticalState_Get(void)
{
    // Note: This uses a DIFFERENT class static than most other functions.
    // DAT_1839820c0 = TacticalState class static (this accessor's version)
    // DAT_183981f50 = TacticalState class static (as seen in TacticalStateSettings)
    // Both refer to TacticalState but may be different DAT symbols for the same
    // class object — IL2CPP can emit multiple static references to the same class.

    if (!TacticalState_classInitFlag2) {
        il2cpp_runtime_class_init(&TacticalState_class2);
        TacticalState_classInitFlag2 = true;
    }

    // Ensure class is runtime-initialised
    if (TacticalState_class2.runtimeInitFlag == 0) {
        il2cpp_runtime_class_init(TacticalState_class2);
    }

    // Return the singleton:
    // *(classStatic + 0xb8) = pointer to static field storage
    // **staticFieldStorage  = s_Singleton (first static field, offset 0x00)
    return **(TacticalState**)(&TacticalState_class2.staticFields);
    //     ↑ s_Singleton
}
```

---

## 10. Agent.GetThreatLevel — 0x18071B240

### Raw Ghidra output
```c
undefined8 FUN_18071b240(longlong param_1)
{
  longlong *plVar1;
  longlong lVar2;
  char cVar3;
  int iVar4;
  longlong lVar5;
  longlong lVar6;
  undefined8 uVar7;
  float fVar8;
  float fVar9;
  float fVar10;
  float fVar11;
  undefined8 local_c0;
  undefined8 uStack_b8;
  longlong local_b0;
  undefined4 local_a8;
  ...

  plVar1 = *(longlong **)(param_1 + 0x18);  // self->m_Actor
  if (plVar1 != (longlong *)0x0) {
    fVar11 = (float)(int)plVar1[0x28];      // actor->field_0x140 (NumThreatsFaced cast to float)
    lVar5 = (**(code **)(*plVar1 + 0x388))(plVar1,*(undefined8 *)(*plVar1 + 0x390)); // GetFaction
    if (lVar5 == 0) return 0;

    // Enumerate m_Faction->field_0x48 (actor's skill list — same as GetOpportunityLevel)
    foreach (Skill skill in m_Faction->field_0x48) {
      // skill->+0x10 = some Actor reference (the threat source actor)
      // skill->+0x10->+0x10 = the threat source actor's Actor object
      // vtable +0x3d8 = GetArmor() or GetWeapon() — something on the opponent
      // lVar6->+0xec bit 0: some state flag on the weapon/armor object
      ...
      // Per threat contribution:
      fVar8 = FUN_180a2d5c0(..., self->m_Actor, 0, DAT_18399ef28); // threat score evaluator
      if (fVar8 > 3.0) fVar8 = 3.0;                                // clamp at 3.0
      fVar9 = (skill->+0x18 < 0) ? -1.0f : 1.0f;                  // sign from field at +0x18
      if (actor->+0x15C != 0) fVar9 *= 0.8f;                       // suppression penalty
      iVar4 = FUN_1805ca7a0(lVar5, opponentFaction, 0);             // opponent count/index
      fVar10 = clamp((float)iVar4 * 0.0625f, 0.0f, 1.0f);          // attenuation
      fVar11 += (1.0f - fVar10) * (fVar8 + 1.0f) * fVar9;          // accumulate
    }

    // Apply ThreatLevelPOW
    lVar5 = WEIGHTS;
    return powf(fVar11, WEIGHTS->ThreatLevelPOW);  // lVar5+0x48
  }
  NullReferenceException();
}
```

### Annotated reconstruction
```c
float Agent_GetThreatLevel(Agent* self)
{
    // ── Actor setup ──────────────────────────────────────────────────────
    Actor* actor = self->m_Actor;  // +0x18
    if (actor == null) NullReferenceException();

    // fVar11 starts as a cast of actor->field_0x140 (plVar1[0x28] = actor offset 0x140).
    // This is likely m_NumThreatsFaced cast to float, used as an initial bias
    // or the field stores a pre-computed partial threat sum.
    float accumulator = (float)(int)actor->field_0x140;  // plVar1[0x28]

    // actor vtable +0x388 = GetFaction() — returns this actor's faction
    // If no faction, return 0 (no threat level without faction context)
    var myFaction = actor->vtable[0x388](actor, actor->vtableArg_0x390);
    if (myFaction == null) return 0;

    // ── Enumerate threat sources (actor's skill list, same as GetOpportunityLevel) ──
    // m_Faction->+0x48 = skill collection (same field as in GetOpportunityLevel)
    // Each entry in this collection represents a threat relationship,
    // not a player-owned skill. The skills here encode threat sources (opponents
    // who can attack this agent) rather than this agent's own attacks.
    if (self->m_Faction == null || self->m_Faction->field_0x48 == null)
        goto NullRef;

    foreach (object threatEntry in self->m_Faction->field_0x48) {
        // threatEntry->+0x10 = the threat source actor reference
        // threatEntry->+0x10->+0x10 = Actor* (the opponent)
        Actor* opponent = threatEntry->field_0x10->field_0x10;
        if (opponent == null) NullReferenceException();

        // vtable +0x3d8 on opponent = GetWeapon() or GetEquipment()
        // Returns an equipment/weapon object; lVar6 = that object
        var opponentWeapon = opponent->vtable[0x3d8](opponent, opponent->vtableArg_0x3e0);
        if (opponentWeapon == null) NullReferenceException();

        // lVar6->+0xec bit 0: weapon state flag
        // If bit 0 is SET: this threat is suppressed/inactive — skip it entirely
        if ((opponentWeapon->field_0xec & 1) != 0) continue;

        // ── Actor state checks on the threat source ───────────────────
        // threatEntry->+0x10 = some Actor reference for the threat actor
        Actor* threatActor = threatEntry->field_0x10;
        if (threatActor == null) NullReferenceException();

        // vtable +0x478 = some state accessor returning int
        // If result == 2: skip (e.g., actor already acted this turn, no threat)
        int stateA = threatActor->vtable[0x478](threatActor, threatActor->vtableArg_0x480);
        if (stateA == 2) continue;

        // vtable +0x468 = another state accessor
        // If result == 1: skip (another state exclusion — possibly fleeing or stunned)
        int stateB = threatActor->vtable[0x468](threatActor, threatActor->vtableArg_0x470);
        if (stateB == 1) continue;

        // threatActor->vtable +0x388 = GetFaction() on the threat actor
        var opponentFaction = threatActor->vtable[0x388](threatActor, threatActor->vtableArg_0x390);
        if (opponentFaction == null) continue;

        // ── Compute threat score for this opponent ────────────────────
        // FUN_1805ca7a0(myFaction, opponentFaction, 0) = relationship/distance metric
        // Returns int — number of opponents on same team, or spatial proximity count.
        // Used for attenuation: more opponents = diminishing marginal threat.
        int opponentCount = FUN_1805ca7a0(myFaction, opponentFaction, 0);  // iVar4

        // FUN_180a2d5c0(threatActor->+0x20->+0x58, self->m_Actor, 0, ThreatEvalClass)
        //   = per-threat score evaluator
        //   threatActor->+0x20->+0x58 = some threat data object
        //   Returns float threat severity for this specific opponent
        //   DAT_18399ef28 = ThreatEvaluator class static
        float threatScore = EvaluateThreat(
            threatActor->field_0x20->field_0x58,
            self->m_Actor,
            0,
            ThreatEvaluator_class
        );  // fVar8

        // Clamp individual threat at 3.0
        if (threatScore > 3.0f) threatScore = 3.0f;

        // ── Direction sign ────────────────────────────────────────────
        // threatEntry->+0x18 = a signed int field.
        // Negative = threat comes from behind / flanking = negative sign modifier.
        // Positive = frontal threat = positive.
        float sign = (threatEntry->field_0x18 < 0) ? -1.0f : 1.0f;  // fVar9

        // Suppression penalty: if actor is suppressed (+0x15C flag on threatActor's actor)
        // Suppressed actors contribute 20% less threat.
        if (threatActor->field_0x10->field_0x15C != 0) {
            sign *= 0.8f;
        }

        // ── Attenuation ───────────────────────────────────────────────
        // fVar10 = clamp(opponentCount × 0.0625, 0, 1)
        // 0.0625 = 1/16, so at 16+ opponents, attenuation = 1.0 (full diminishment)
        // (1 - attenuation) falls from 1.0 (no opponents) to 0.0 (16+ opponents)
        float attenuation = (float)opponentCount * 0.0625f;
        if (attenuation > 1.0f) attenuation = 1.0f;

        // ── Accumulate ────────────────────────────────────────────────
        // +1.0 ensures even zero-threat opponents contribute marginally
        accumulator += (1.0f - attenuation) * (threatScore + 1.0f) * sign;
    }

    // ── Apply ThreatLevelPOW ─────────────────────────────────────────────
    // WEIGHTS->ThreatLevelPOW at +0x48
    AIWeightsTemplate* weights = DebugVisualization.WEIGHTS;
    return powf(accumulator, weights->ThreatLevelPOW);  // +0x48

NullRef:
    NullReferenceException();
}
```

### GetThreatLevel — formula summary

```
accumulator = (float)actor->field_0x140   // initial bias (pre-computed partial or NumThreatsFaced)

for each threatEntry in threatSources:
    skip if: weapon state bit 0 set (inactive threat)
    skip if: threatActor stateA == 2  (already acted)
    skip if: threatActor stateB == 1  (fleeing/stunned)

    threatScore  = clamp(EvaluateThreat(opponent, actor), 0, 3.0)
    sign         = (threatEntry.field_0x18 < 0) ? -1.0 : +1.0
    if opponent is suppressed: sign *= 0.8
    attenuation  = clamp(opponentCount × 0.0625, 0, 1.0)
    accumulator += (1.0 - attenuation) × (threatScore + 1.0) × sign

return powf(accumulator, WEIGHTS.ThreatLevelPOW)
```

**Key design observations:**
- The `+1.0` offset on `threatScore` means every non-skipped opponent contributes at least `(1 - attenuation) × 1.0 × sign` even if their raw threat is zero.
- The attenuation caps at 16 opponents (0.0625 × 16 = 1.0). Beyond 16 opponents, additional threats contribute nothing — preventing runaway threat accumulation in mass-combat scenarios.
- Flanking threats (negative sign) reduce `accumulator`, making flanked positions score lower overall when combined with the negated SafetyScore post-processing.

---

## 11. Agent.GetOpportunityLevel — 0x18071ABC0

### Raw Ghidra output
```c
void FUN_18071abc0(longlong param_1)
{
  longlong lVar1;
  longlong lVar2;
  char cVar3;
  uint uVar4;
  float fVar5;
  float fVar6;
  float local_res8 [2];
  undefined8 local_70;
  undefined8 uStack_68;
  longlong local_60;
  undefined4 local_58;
  undefined4 uStack_54;
  undefined4 uStack_50;
  undefined4 uStack_4c;
  longlong local_48;
  
  if (DAT_183b9319f == '\0') {
    FUN_180427b00(&DAT_18394c3d0);
    FUN_180427b00(&DAT_1839441d8);
    FUN_180427b00(&DAT_1839ada98);
    FUN_180427b00(&DAT_1839adb50);
    FUN_180427b00(&DAT_1839adc08);
    FUN_180427b00(&DAT_183968278);
    DAT_183b9319f = '\x01';
  }
  local_res8[0] = 0.0;
  if ((*(longlong *)(param_1 + 0x10) != 0) &&
     (lVar1 = *(longlong *)(*(longlong *)(param_1 + 0x10) + 0x48), lVar1 != 0)) {
    FUN_180cbab80(&local_70,lVar1,DAT_183968278);
    local_58 = (undefined4)local_70;
    uStack_54 = local_70._4_4_;
    uStack_50 = (undefined4)uStack_68;
    uStack_4c = uStack_68._4_4_;
    local_48 = local_60;
    local_70 = 0;
    fVar6 = 0.0;
    uStack_68 = &local_58;
    while (cVar3 = FUN_1814f4770(&local_58,DAT_1839adb50), lVar1 = local_48, cVar3 != '\0') {
      fVar5 = 0.0;
      for (uVar4 = 0; (int)uVar4 < 3; uVar4 = uVar4 + 1) {
        if (lVar1 == 0) {
          FUN_180427d90();
        }
        lVar2 = *(longlong *)(lVar1 + 0x20);
        if (lVar2 == 0) {
          FUN_180427d90();
        }
        lVar2 = *(longlong *)(lVar2 + 0x68);
        if (lVar2 == 0) {
          FUN_180427d90();
        }
        if (*(uint *)(lVar2 + 0x18) <= uVar4) {
          FUN_180427d80();
        }
        lVar2 = *(longlong *)(lVar2 + 0x20 + (longlong)(int)uVar4 * 8);
        if (lVar2 == 0) {
          FUN_180427d90();
        }
        cVar3 = FUN_181430ac0(lVar2,*(undefined8 *)(param_1 + 0x18),local_res8,DAT_1839441d8);
        if ((cVar3 != '\0') && (fVar5 <= local_res8[0])) {
          fVar5 = local_res8[0];
        }
      }
      if (fVar6 <= fVar5) {
        fVar6 = fVar5;
      }
    }
    FUN_1804f7ee0(&local_58,DAT_1839ada98);
    if (*(int *)(DAT_18394c3d0 + 0xe4) == 0) {
      il2cpp_runtime_class_init(DAT_18394c3d0);
    }
    lVar1 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
    if (lVar1 != 0) {
      FUN_1804bad80(fVar6,*(undefined4 *)(lVar1 + 0x4c));
      return;
    }
  }
  FUN_180427d90();
}
```

### Annotated reconstruction
```c
float Agent_GetOpportunityLevel(Agent* self)
{
    // DAT_1839441d8 = AttackEvaluator class static (parameter to FUN_181430ac0)
    // DAT_183968278 = used for skill list enumeration (GetEnumerator type)
    // FUN_180cbab80 = GetEnumerator on a list
    // FUN_1814f4770 = MoveNext() on an enumerator
    // FUN_181430ac0 = per-attack evaluator: (attack, actor, &outScore, evaluatorClass) → bool

    float bestScore = 0.0f;

    // self->m_Faction (+0x10) must exist
    // m_Faction->field_0x48 = the actor's skill list (on m_Actor via m_Faction, or direct actor?)
    // Actually: self->m_Actor (+0x18) is more likely; +0x48 on actor = actor's skill collection.
    if (self->m_Faction == null) goto NullRef;
    var skillCollection = self->m_Faction->field_0x48;  // actor's skills
    if (skillCollection == null) goto NullRef;

    // Enumerate skills
    foreach (Skill skill in skillCollection) {
        float bestScoreForThisSkill = 0.0f;

        // Each skill has up to 3 attack slots
        // skill->+0x20 = some attack container
        // container->+0x68 = the actual attack array/list
        // array->+0x18 = array length
        // array->+0x20 + index*8 = array element (attack object pointer)
        for (int slot = 0; slot < 3; slot++) {
            var attackContainer = skill->field_0x20;
            if (attackContainer == null) NullReferenceException();
            var attackArray = attackContainer->field_0x68;
            if (attackArray == null) NullReferenceException();

            // Bounds check: slot must be < array length
            if ((uint)slot >= attackArray->length) IndexOutOfRangeException();

            var attack = attackArray->elements[slot];
            if (attack == null) NullReferenceException();

            // Evaluate this attack:
            // FUN_181430ac0(attack, self->m_Actor, &outScore, AttackEvaluatorClass)
            // Returns bool (success), writes float score to outScore
            float attackScore;
            bool valid = EvaluateAttack(attack, self->m_Actor, out attackScore);
            if (valid && attackScore > bestScoreForThisSkill) {
                bestScoreForThisSkill = attackScore;
            }
        }

        // Track global best across all skills
        if (bestScoreForThisSkill > bestScore) {
            bestScore = bestScoreForThisSkill;
        }
    }

    // Apply OpportunityLevelPOW shaping:
    // WEIGHTS at DebugVisualization static +0x08
    // OpportunityLevelPOW at WEIGHTS+0x4C
    // FUN_1804bad80 = powf(value, exponent)
    AIWeightsTemplate* weights = DebugVisualization.WEIGHTS;
    float result = powf(bestScore, weights->OpportunityLevelPOW);  // +0x4C
    return result;

NullRef:
    NullReferenceException();
}
```

---

## 12. Agent.GetScoreMultForPickingThisAgent — 0x18071AE50

### Raw Ghidra output (abbreviated — full function is ~120 lines of vtable dispatch)
```c
void FUN_18071ae50(longlong param_1)
{
  // ... init guards ...
  
  // Early-out: player unit check
  if (*(longlong *)(**(longlong **)(DAT_183981f50 + 0xb8) + 0x50) == *(longlong *)(param_1 + 0x18))
    return;
  
  // Ensure opportunity level is computed
  if (*(longlong *)(param_1 + 0x28) == 0) {
    FUN_18071abc0(param_1,0);  // GetOpportunityLevel
  }
  FUN_18071b240(param_1,0);  // GetThreatLevel
  
  // ... actor state checks (stealth, vehicle, fleeing, Scout behavior) ...
  
  // Final POW application:
  lVar4 = *(longlong *)(*(longlong *)(DAT_18394c3d0 + 0xb8) + 8);
  FUN_1804bad80(lVar4, *(undefined4 *)(lVar4 + 0x50));  // powf(score, PickingScoreMultPOW)
}
```

### Annotated reconstruction
```c
float Agent_GetScoreMultForPickingThisAgent(Agent* self)
{
    // ── Early-out: skip player-controlled unit ───────────────────────────
    // TacticalState.singleton->m_DeployedUnitLeaders (+0x50) is compared to
    // self->m_Actor (+0x18). If this agent IS the player's unit, return immediately.
    TacticalState* state = TacticalState.s_Singleton;
    if (state->m_DeployedUnitLeaders == self->m_Actor) return 0.0f;
    //          ^^^ +0x50                  ^^^ +0x18

    // ── Ensure sub-scores are computed ──────────────────────────────────
    // m_ActiveBehavior (+0x28) being null is used as a proxy for
    // "opportunity level not yet computed this cycle"
    if (self->m_ActiveBehavior == null) {
        GetOpportunityLevel(self);  // FUN_18071abc0
    }
    GetThreatLevel(self);  // FUN_18071b240

    // ── Actor state checks ───────────────────────────────────────────────
    // FUN_180616ae0 = IsVehicle() or IsMoving() on actor
    // vtable +0x408 / +0x3d8 = actor state accessors
    // FUN_180952f00(self, 4, DAT_18396a640) = GetBehavior<Scout>() — checks if Scout behavior assigned
    // *(lVar4 + 0xec) & 1 = some actor flag (stealth? fleeing?)
    // vtable +0x468 = GetUnitCount() or GetRiderCount() for vehicles
    // vtable +0x478 = additional vehicle/rider state accessor
    //
    // The exact modifiers from these checks are not fully decoded —
    // they modify an intermediate combined score before the final POW.
    // Key known adjustments:
    //   - Scout behavior: additional multiplier applied
    //   - Vehicle with riders: rider count affects score
    //   - Actor flag 0xEC bit 0: some state modifier (stealth/concealment likely)

    float combinedScore = /* threat + opportunity + state modifiers */;

    // ── Final: apply PickingScoreMultPOW ────────────────────────────────
    // WEIGHTS->PickingScoreMultPOW is at +0x50 on AIWeightsTemplate
    // FUN_1804bad80 = powf(value, exponent)
    AIWeightsTemplate* weights = DebugVisualization.WEIGHTS;
    return powf(combinedScore, weights->PickingScoreMultPOW);  // +0x50
}
```

The final `m_Score` computed in `Evaluate()` using this result:
```c
float mult = GetScoreMultForPickingThisAgent(self);
int behaviorBaseScore = self->m_ActiveBehavior->baseScore;  // +0x18 on Behavior
self->m_Score = max(1, (int)(mult * (float)behaviorBaseScore));
```

---

## 13. Agent.PickBehavior — 0x18071BD20

### Raw Ghidra output
```c
undefined8 FUN_18071bd20(longlong param_1)
{
  int iVar1;
  char cVar2;
  int iVar3;
  longlong lVar4;
  longlong lVar5;
  longlong *plVar6;
  undefined8 uVar7;
  int iVar8;
  int iVar9;
  float fVar10;
  undefined4 local_res8 [2];

  // [full output — see GhidraAddressLookupRESULTS2.txt lines 811–1022]
}
```

### Annotated reconstruction
```c
Behavior* Agent_PickBehavior(Agent* self)
{
    // ── Guard: m_Behaviors list must exist and be non-empty ─────────────
    // self->m_Behaviors (+0x20), *(m_Behaviors + 0x18) = list Count
    List<Behavior>* behaviors = self->m_Behaviors;  // +0x20
    if (behaviors == null) goto NullRef;
    int behaviorCount = behaviors->Count;  // +0x18
    if (behaviorCount == 0) return null;

    // ── Get the top-scored behavior (index 0 after sort) ────────────────
    // FUN_180cca560(list, index, elementClass) = List[index] element getter
    // The list has been sorted descending by score already (in Evaluate).
    Behavior* topBehavior = List_GetAt(behaviors, 0, BehaviorClass);  // lVar4
    if (topBehavior == null) goto NullRef;

    // ── WEIGHTS check ────────────────────────────────────────────────────
    AIWeightsTemplate* weights = DebugVisualization.WEIGHTS;
    if (weights == null) goto NullRef;

    // ── Compute score threshold (30% of top behavior score) ─────────────
    // FUN_1804bad80() here is called with no explicit args visible — likely reads
    // topBehavior's score via an inlined accessor.
    // iVar3 = max(1, (int)(topScore × 0.3))
    // This is the cutoff: any behavior scoring less than 30% of the top is excluded.
    float topScore = GetBehaviorScore(topBehavior);  // fVar10
    int threshold = (int)(topScore * 0.3f);
    if (threshold < 1) threshold = 1;  // iVar3

    // ── Check if this is a deployment phase (randomised pick path) ───────
    // FUN_180537140(0, 0) = IsDeploymentPhase() or equivalent global check
    // Returns true during deployment, enabling a different (randomised) pick path.
    bool isDeployment = FUN_180537140(0, 0);

    if (isDeployment) {
        // ── DEPLOYMENT PATH: weighted random pick ────────────────────────
        // During deployment, a behavior pick event is constructed and dispatched.
        // This allows external systems (UI, player input?) to influence the pick.

        // Check if the tactical state is player-turn (TacticalState->+0x60 != 0)
        bool isPlayerTurn = (TacticalState.s_Singleton->field_0x60 != 0);

        if (isPlayerTurn) {
            for (int i = 0; i < behaviorCount; i++) {
                // Build a "pick event" object (type DAT_1839413d0, allocated via FUN_180426ed0)
                // The event has up to 5 slots filled in:
                //   +0x20 = lVar4 (current top behavior)
                //   +0x28 = uVar7 (behavior at index i, via vtable +0x188 = GetScore())
                //   +0x30 = DAT_183997c40 (some constant/class ref)
                //   +0x38 = uVar7 (boxed int score, via FUN_181b5ef10)
                //   +0x40 = DAT_18394b058 (another constant/class ref)
                // FUN_1819c8350(event, 0) = dispatch/fire the event
                var pickEvent = AllocateEvent(EventClass, 5);
                pickEvent->slot0 = topBehavior;
                pickEvent->slot1 = GetBehaviorScore(behaviors[i]);  // vtable +0x188
                pickEvent->slot2 = SomeConstant;
                pickEvent->slot3 = BoxInt(behaviors[i]->baseScore);
                pickEvent->slot4 = AnotherConstant;
                var result = DispatchEvent(pickEvent);

                // After dispatch: check if score meets threshold
                // FUN_1804bad80() = powf — applies some scaling to the post-event score
                float postEventScore = powf(result, someExponent);
                if (postEventScore >= (float)threshold) {
                    // Apply decoration behavior if needed:
                    // FUN_1819c88f0(topBehavior, DAT_183948538, 0) = decorate/wrap behavior
                    topBehavior = DecorateBehavior(topBehavior, DecorationClass);
                }
            }
        }
    }

    // ── STANDARD PATH: score-threshold pick with optional player-dispatch ─
    // Accumulate total score of behaviors meeting threshold
    int totalScore = 0;
    iVar8 = 0;
    for (int i = 0; i < behaviorCount; i++) {
        Behavior* b = List_GetAt(behaviors, i, BehaviorClass);
        if (b == null) goto NullRef;

        // FUN_1804bad80() = get/compute this behavior's score
        float score = GetBehaviorScore(b);
        if ((int)score < threshold) break;  // behaviors are sorted; stop when below threshold

        totalScore += (int)score;
        iVar8++;
    }

    // ── Weighted random selection ────────────────────────────────────────
    // self->m_Random (+0x40) = PseudoRandom instance
    // FUN_18053dbd0(m_Random, 1, totalScore, 0) = PseudoRandom.Next(1, totalScore)
    // Selects a random value in [1, totalScore], then walks the behavior list
    // subtracting each score until the random value is exhausted.
    if (self->m_Random == null) goto NullRef;
    int randomValue = PseudoRandom_Next(self->m_Random, 1, totalScore, 0);  // iVar3
    //                                   ^^^ +0x40

    for (int i = 0; i < behaviorCount; i++) {
        Behavior* b = List_GetAt(behaviors, i, BehaviorClass);
        if (b == null) goto NullRef;

        float score = GetBehaviorScore(b);
        if (randomValue <= (int)score) {
            // ── Optional player-dispatch for non-deployment ──────────────
            // FUN_180537140(0,0) = IsDeploymentPhase() — if false (normal turn):
            // FUN_18071b670(self, 0) = Agent.IsDeploymentPhase() — secondary check
            // If both say not deployment: build and fire a 7-slot pick event,
            // writing result to self->m_QueuedDebugString (+0x70)
            if (!IsDeploymentPhase() && !self->IsDeploymentPhase()) {
                var fullPickEvent = AllocateEvent(EventClass, 7);
                fullPickEvent->slot0 = SomeFlag;
                fullPickEvent->slot1 = topBehavior;
                fullPickEvent->slot2 = SomeConstant2;
                fullPickEvent->slot3 = GetBehaviorScore(behaviors[i]);  // vtable +0x188
                fullPickEvent->slot4 = SomeConstant3;
                fullPickEvent->slot5 = BoxInt(behaviors[i]->baseScore);
                fullPickEvent->slot6 = AnotherConstant2;
                var eventResult = DispatchEvent(fullPickEvent);
                self->m_QueuedDebugString = eventResult;  // +0x70
                WriteBarrier(self->m_QueuedDebugString, eventResult);

                // Player-controlled unit check:
                // FUN_180511a50(0) = some global state accessor
                // If result->+0x50 == self->m_Actor: this agent is player-controlled
                // → clear m_QueuedDebugString and fire a UI notification instead
                var globalState = GetGlobalState(0);
                if (globalState != null &&
                    globalState->field_0x50 == self->m_Actor) {
                    // FUN_182948890(debugString, 0) = log or UI display call
                    LogOrDisplay(self->m_QueuedDebugString);
                    self->m_QueuedDebugString = null;
                    WriteBarrier(self->m_QueuedDebugString, null);
                }
            }

            // Return the selected behavior
            return List_GetAt(behaviors, i, BehaviorClass);
        }

        randomValue -= (int)score;
    }

    // No behavior selected (all scores below threshold after random walk)
    return null;

NullRef:
    NullReferenceException();
}
```

### PickBehavior — design notes

**Selection algorithm is weighted random, not greedy.** Rather than always taking the highest-scoring behavior, `PickBehavior` uses a weighted lottery across all behaviors scoring at least 30% of the top behavior's score. This introduces deliberate unpredictability: a behavior with 60% of the top score has a 60/(60+100) = 37.5% chance of being selected even when another scores higher.

**The 30% threshold** (`topScore × 0.3`, floored at 1) is the participation cutoff. Behaviors below this are excluded from the lottery entirely. This prevents very weak behaviors from ever being selected while still allowing sub-optimal but reasonable choices to compete.

**Deployment path uses event dispatch.** During deployment, behavior selection fires a pick event with up to 5 parameters, allowing external systems (UI overlays, player-influence hooks) to observe or modify the selection. The post-event score is compared against threshold again before committing.

**`m_QueuedDebugString` (+0x70)** receives the event result for non-deployment turns, enabling debug logging of what behavior was selected and why. For player-controlled agents, this is immediately passed to a logging/display function and cleared — it's not retained.

**`PseudoRandom` is per-agent** (`m_Random` at `+0x40`). Each agent has its own RNG state, ensuring selection choices are independently reproducible per-agent without cross-contamination between agents in the same frame.
## 14. Agent.Evaluate — 0x180719860

### Annotated reconstruction (full function — 1100+ lines of Ghidra output)

```c
void Agent_Evaluate(Agent* self)
{
    // ═══════════════════════════════════════════════════════════════
    // PHASE 0: RESET
    // ═══════════════════════════════════════════════════════════════

    self->m_Score         = 0;     // +0x30
    self->m_ActiveBehavior = null; // +0x28  (also releases GC ref via FUN_180426e50)
    self->m_State         = 0;     // +0x3C  (State.None)

    // ═══════════════════════════════════════════════════════════════
    // PHASE 1: GUARDS
    // ═══════════════════════════════════════════════════════════════

    // m_Tiles must exist
    if (self->m_Tiles == null) NullReferenceException();  // +0x58

    // ── Double-buffer swap ───────────────────────────────────────
    // Clear the tile dictionary, then assign m_Tiles reference to m_TilesToBeUsed.
    // FUN_18136c890 = Dictionary.Clear()
    // After this, m_TilesToBeUsed and m_Tiles point to the same dictionary.
    // Criterions write into m_TilesToBeUsed; DrawHeatmap reads from m_Tiles.
    Dictionary_Clear(self->m_Tiles, TileScore_class);        // FUN_18136c890
    self->m_TilesToBeUsed = self->m_Tiles;                   // +0x60 = +0x58
    WriteBarrier(self->m_TilesToBeUsed);                     // FUN_180426e50

    // ── Actor liveness ───────────────────────────────────────────
    Actor* actor = self->m_Actor;  // +0x18
    if (actor == null) NullReferenceException();

    // actor->+0x48 = IsActive flag (non-zero = active)
    // actor->+0x15C = IsDead flag (non-zero = dead)
    if (!actor->IsActive || actor->IsDead) return;

    // FlaggedForDeactivation (+0x78) — if set, skip this agent
    if (self->FlaggedForDeactivation) return;  // +0x78

    // ── TacticalState singleton guard ────────────────────────────
    TacticalState* state = TacticalState.s_Singleton;
    if (state == null) NullReferenceException();

    // ── Iteration budget ─────────────────────────────────────────
    // TacticalState->+0xb8 = m_IsStandalone
    // If standalone: skip budget check (editor/test mode, uncapped evaluation).
    // Otherwise: increment m_Iterations and check against MAX_ITERATIONS (16).
    if (!state->m_IsStandalone) {  // +0xb8
        int iterations = ++self->m_Iterations;  // +0x48
        if (iterations >= 17) {
            // Over budget: log debug string, force sleep, bail.
            // FUN_182948700 = some logging/debug call
            // FUN_1805e76f0(actor, true) = actor.SetSleeping(true)
            Log(debugString);
            actor.SetSleeping(true);
            return;
        }
    }

    // ── Sleep check ──────────────────────────────────────────────
    // m_SleepUntil (+0x4C) vs m_Faction clock (m_Faction+0x38)
    // If current time < sleep-until time, this agent is still resting.
    float currentTime = self->m_Faction->clock;  // +0x38 on AIFaction
    if (self->m_SleepUntil > currentTime) return;  // +0x4C

    // ── Actor movement check ─────────────────────────────────────
    // vtable +1000 (decimal) on actor = some state accessor (GetCurrentTile or similar)
    // FUN_1806f3c30 = IsMoving() or CanBeEvaluated()
    // If actor is currently in motion, yield one cooperative frame and retry.
    // FUN_181bde4c0(1) = yield/wait one frame (cooperative scheduling)
    iteration_start:
    var actorStateObj = actor->vtable[1000/8](actor, actor->vtableArg_0x3f0);
    if (actorStateObj == null) NullReferenceException();
    bool actorIsMoving = FUN_1806f3c30(actorStateObj, 0);
    if (actorIsMoving) {
        YieldOneFrame();  // FUN_181bde4c0(1)
        goto iteration_start;
    }

    // ── Deployment phase check ───────────────────────────────────
    // TacticalState->+0x60 == 0: no turns elapsed (deployment phase)
    // AND self->m_IsDeployed (+0x50): this unit is already placed
    // → skip to scoring phase (LAB_18071a5b9)
    //
    // FUN_1805df7e0(actor) = actor.IsDeploymentPhase()
    // If true: also skip to scoring phase.
    if (state->field_0x60 == 0 && self->m_IsDeployed) goto STATE_SCORED;
    if (actor.IsDeploymentPhase()) goto STATE_SCORED;

    // ═══════════════════════════════════════════════════════════════
    // PHASE 2: STATE 1 — EVALUATING
    // ═══════════════════════════════════════════════════════════════

    self->m_State = 1;  // State.Evaluating

    // ── Criterion Pass 1 ─────────────────────────────────────────
    // S_CRITERIONS = static list (DAT_18394e828 class static → static field +0x00)
    // FUN_180cbab80 = GetEnumerator on List<Criterion>
    // FUN_1814f4770 = MoveNext() on enumerator
    // For each Criterion c:
    //   vtable +0x178 = c.IsApplicable(actor, c.defaultArg)  → bool
    //   vtable +0x198 = c.Evaluate(actor, m_Tiles)           → void
    foreach (Criterion c in S_CRITERIONS) {
        bool applicable = c->vtable[0x178](c, actor, c->defaultArg);  // IsApplicable
        if (applicable) {
            c->vtable[0x198](c, actor, self->m_Tiles);  // Evaluate(actor, tiles)
        }
    }

    // ── Behavior list construction (Move pass) ───────────────────
    // FUN_1804608d0(DAT_1839a2890) = create new BehaviorList
    // FUN_1805567d0(list, self, MoveFilter) = populate with move-phase behaviors
    // FUN_18188c930(m_Behaviors, list, sortClass) = sort into m_Behaviors
    var moveBehaviorList = new BehaviorList();
    FilterBehaviors(moveBehaviorList, self, MoveFilter_class);
    self->m_Behaviors.Sort(moveBehaviorList, SortClass);  // +0x20

    // ── Threading split computation ──────────────────────────────
    // iVar4 = Dictionary.Count(m_Tiles)
    // vtable +0x188 = Criterion.GetTileCount() — tiles-per-thread budget
    //   (result stored in local_148, iVar5)
    // If actor is a vehicle (m_Faction->field_0x40 >= 2): iVar5 /= 2
    int tileCount = Dictionary_Count(self->m_Tiles);
    int tilesPerThread = activeCriterion->vtable[0x188](activeCriterion);
    bool isVehicle = (self->m_Faction->field_0x40 >= 2) && !actor.IsInfantry();
    if (isVehicle) tilesPerThread /= 2;

    // ── Threaded path ─────────────────────────────────────────────
    if (tilesPerThread > 1 && tilesPerThread * 2 < tileCount) {
        int numThreads = tilesPerThread - 1;

        // Schedule thread tasks for all-but-last segment
        // FUN_18071cad0 = ScheduleCriterionEvaluation(self, threadIdx, tileCount/tilesPerThread, criterion)
        // FUN_180002590(m_Tasks, task) = List.Add(task)
        for (int i = 0; i < numThreads; i++) {
            Task t = ScheduleCriterionEvaluation(
                self, i, tileCount / tilesPerThread, activeCriterion);
            self->m_Tasks.Add(t);  // +0x68
        }

        // Handle remainder tiles inline:
        // FUN_180a803d0(enumerator, m_Tiles, tileIndex, TileClass) = get tile at index
        // vtable +0x1a8 = criterion.EvaluateTile(actor, tileScore) — per-tile evaluation
        int remainderStart = numThreads * (tileCount / tilesPerThread);
        for (int i = remainderStart; i < tileCount; i++) {
            TileScore ts = m_Tiles[i];
            activeCriterion->vtable[0x1a8](activeCriterion, actor, ts);  // EvaluateTile
        }

        // Wait for threads:
        // FUN_180cbab80(enumerator, m_Tasks, TaskClass) = enumerate m_Tasks
        // FUN_181bfa040(task) = task.IsComplete()
        // If not complete: FUN_181bde4c0(1) = yield one frame
        do {
            bool allDone = true;
            foreach (Task t in self->m_Tasks) {
                if (!t.IsComplete()) {
                    allDone = false;
                    break;
                }
            }
            if (!allDone) YieldOneFrame();
        } while (!allDone);

        // Reset task list state:
        // *(m_Tasks + 0x1c) += 1  (version/generation counter)
        // *(m_Tasks + 0x18) = 0   (count = 0)
        self->m_Tasks.Reset();

    } else {
        // ── Single-threaded path ──────────────────────────────────
        // Iterate m_Tiles directly
        // vtable +0x1a8 = criterion.EvaluateTile(actor, tileScore) — same slot
        foreach (TileScore ts in self->m_Tiles) {
            activeCriterion->vtable[0x1a8](activeCriterion, actor, ts);  // EvaluateTile
        }
    }

    // ── Enumerate m_Behaviors for tile scoring (mid-pass) ────────
    // FUN_180738d10 = Behavior.ScoreTilesPass1(actor) or similar
    // FUN_180738dc0 = Behavior.ScoreTilesPass2(actor, tiles) or similar
    // plVar11 tracks current best behavior score
    foreach (Behavior b in self->m_Behaviors) {
        b.ScoreTilesPass1(actor);
        if (b.score > 0 && bestBehavior != null) {
            bestScore = bestBehavior->score;
        }
    }

    // ── Move behavior tile evaluation (second inner loop) ─────────
    foreach (TileScore ts in self->m_Tiles) {
        activeCriterion->vtable[0x1a8](activeCriterion, actor, ts);
    }

    // ── PostProcessTileScores ─────────────────────────────────────
    // Called here, between the two criterion passes.
    // Applies POW/Scale pipeline to SafetyScore and UtilityScore.
    // Performs neighbor propagation if m_Flags bit 0 is set.
    PostProcessTileScores(self);  // FUN_18071c450

    // ── Criterion Pass 2 ─────────────────────────────────────────
    // vtable +0x1b8 = c.PostEvaluate(actor, m_Tiles)
    // Different from Pass 1's +0x198 (Evaluate) and +0x1a8 (EvaluateTile).
    // Runs on already-normalized scores.
    foreach (Criterion c in S_CRITERIONS) {
        bool applicable = c->vtable[0x178](c, actor, c->defaultArg);
        if (applicable) {
            c->vtable[0x1b8](c, actor, self->m_Tiles);  // PostEvaluate
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // PHASE 3: STATE 2 — SCORED
    // ═══════════════════════════════════════════════════════════════

    STATE_SCORED:
    self->m_State = 2;  // State.Scored

    // ── Rebuild behavior list (Pick pass) ────────────────────────
    // Uses PickFilter_class (DAT_18396a930) instead of MoveFilter_class (DAT_18396a9f0)
    var pickBehaviorList = new BehaviorList();
    FilterBehaviors(pickBehaviorList, self, PickFilter_class);
    self->m_Behaviors.Sort(pickBehaviorList, SortClass);

    // ── Pick behavior ─────────────────────────────────────────────
    Behavior selected = PickBehavior(self);  // FUN_18071bd20
    self->m_ActiveBehavior = selected;
    WriteBarrier(self->m_ActiveBehavior);

    if (selected != null) {
        // Compute final m_Score:
        // activeBehavior->+0x18 = behavior's base score (int)
        // GetScoreMultForPickingThisAgent returns a float multiplier
        int baseScore = selected->baseScore;  // +0x18
        float mult = GetScoreMultForPickingThisAgent(self);  // FUN_18071ae50
        int finalScore = (int)(mult * (float)baseScore);
        self->m_Score = max(1, finalScore);  // +0x30  — floor at 1

        self->m_State = 3;  // State.Done (uVar12 = 3, committed at function end)
    }

    // ── Final behavior tile scoring ───────────────────────────────
    // Post-pick pass over m_Behaviors
    // FUN_180738e60 = Behavior.FinalizeScore(actor)
    // FUN_180738dc0 = Behavior.ScoreTiles(actor, tiles)
    foreach (Behavior b in self->m_Behaviors) {
        b.FinalizeScore(actor);
        if (b.score > 0) {
            b.ScoreTiles(actor, self->m_Tiles);
        }
    }

    // Commit state
    self->m_State = uVar12;  // 3 (Done) if behavior was picked, else 2 (Scored)
    return;
}
```

---

## 15. Agent.PostProcessTileScores — 0x18071C450

### Annotated reconstruction

```c
void Agent_PostProcessTileScores(Agent* self)
{
    // ── Resolve per-actor role multipliers ───────────────────────────────
    // self->m_Actor (+0x18) vtable +0x398 = GetRoleData() (returns RoleData object)
    // vtable arg at actor vtable +0x3a0
    // RoleData->+0x310 = some nested data object containing per-unit score mults
    // The result lVar5 is the unit-specific coefficient carrier.
    // lVar5+0x14 = unitUtilityMult  (per-actor utility multiplier)
    // lVar5+0x1C = unitSafetyMult   (per-actor safety multiplier)
    Actor* actor = self->m_Actor;
    if (actor == null) NullReferenceException();
    var roleData = actor->vtable[0x398](actor, actor->vtableArg_0x3a0);
    if (roleData == null) NullReferenceException();
    var unitCoeffs = roleData->field_0x310;  // nested coefficient object
    float unitUtilityMult = unitCoeffs->field_0x14;
    float unitSafetyMult  = unitCoeffs->field_0x1C;

    // ── Guard: m_Tiles must exist ────────────────────────────────────────
    if (self->m_Tiles == null) NullReferenceException();

    // ── Resolve AIWeightsTemplate ────────────────────────────────────────
    // DebugVisualization class static (+0xb8) → static field storage
    // static field at +0x08 = WEIGHTS (AIWeightsTemplate instance)
    AIWeightsTemplate* W = DebugVisualization.WEIGHTS;
    if (W == null) NullReferenceException();

    // Faction check vtable call:
    // actor vtable +0x388 = GetFaction() or GetTeam()
    // Used to check if a tile belongs to the actor's faction.
    // The check's result doesn't visibly alter the score pipeline in the
    // decompiled output — may be used for conditional logging or a subtle
    // branch not resolved cleanly by Ghidra.

    // ═══════════════════════════════════════════════════════════════════════
    // PASS 1: Per-tile POW/Scale pipeline
    // ═══════════════════════════════════════════════════════════════════════
    // FUN_18136d8a0 = GetEnumerator on Dictionary<Tile, TileScore>
    // FUN_18152f9b0 = MoveNext() on dictionary enumerator
    // FUN_1817c0ad0 = get current KeyValuePair (Tile key, TileScore value)
    //   → lVar2 = Tile key, lVar7 = TileScore value pointer

    foreach (KeyValuePair<Tile, TileScore> kv in self->m_Tiles) {
        Tile tile = kv.Key;       // lVar2
        TileScore* ts = kv.Value; // lVar7

        // ── UtilityScore pipeline ────────────────────────────────────────
        //
        // Step 1: Merge attack score into utility
        //   ts->+0x30 = UtilityScore
        //   ts->+0x38 = UtilityByAttacksScore
        ts->UtilityScore += ts->UtilityByAttacksScore;
        //  ^^^ +0x30    +=  +0x38

        // Step 2: Apply UtilityPOW
        //   FUN_1804bad80 = powf(value, exponent)
        //   WEIGHTS+0x20 = UtilityPOW
        ts->UtilityScore = powf(ts->UtilityScore, W->UtilityPOW);
        //                                         ^^^ W+0x20

        // Step 3: Scale, re-exponentiate with per-unit multiplier
        //   unitUtilityMult = unitCoeffs->+0x14
        //   WEIGHTS+0x24 = UtilityScale
        //   WEIGHTS+0x28 = UtilityPostPOW
        ts->UtilityScore = powf(
            unitUtilityMult * ts->UtilityScore * W->UtilityScale,
            //                                   ^^^ W+0x24
            W->UtilityPostPOW
            //^^^ W+0x28
        );

        // Step 4: Apply UtilityPostScale
        //   WEIGHTS+0x2C = UtilityPostScale
        //   Read from: *(lVar2 + 0x2c) where lVar2 = *(staticStorage + 8) = WEIGHTS
        ts->UtilityScore *= W->UtilityPostScale;
        //                   ^^^ W+0x2C

        // ── SafetyScore pipeline ─────────────────────────────────────────
        //
        // Step 1: Apply SafetyPOW to raw safety score
        //   ts->+0x28 = SafetyScore (raw, positive at this point)
        //   WEIGHTS+0x30 = SafetyPOW
        ts->SafetyScore = powf(ts->SafetyScore, W->SafetyPOW);
        //  ^^^ +0x28                            ^^^ W+0x30

        // Step 2: Scale, re-exponentiate with per-unit multiplier
        //   unitSafetyMult = unitCoeffs->+0x1C
        //   WEIGHTS+0x34 = SafetyScale
        //   WEIGHTS+0x38 = SafetyPostPOW
        ts->SafetyScore = powf(
            unitSafetyMult * ts->SafetyScore * W->SafetyScale,
            //                                  ^^^ W+0x34
            W->SafetyPostPOW
            //^^^ W+0x38
        );

        // Step 3: NEGATE and multiply by DistanceScale
        //   WEIGHTS+0x40 = DistanceScale
        //   Raw Ghidra: *(float *)(lVar7 + 0x28) = -fVar8 * *(float *)(WEIGHTS + 0x40)
        //   SafetyScore is now NEGATIVE — it is a threat PENALTY in GetScore().
        ts->SafetyScore = -ts->SafetyScore * W->DistanceScale;
        //  ^^^ +0x28      ^                  ^^^ W+0x40
        //                 negation here
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PASS 2: Neighbor propagation (conditional)
    // ═══════════════════════════════════════════════════════════════════════
    // Only runs if:
    //   1. self->m_Flags bit 0 is set (+0x54 & 1 != 0)
    //   2. actor has neighbors: actor vtable +0x458 = GetNeighborCount() > 0

    if ((self->m_Flags & 1) != 0) {
        int neighborCount = actor->vtable[0x458](actor, actor->vtableArg_0x460);
        if (neighborCount > 0) {

            foreach (KeyValuePair<Tile, TileScore> kv in self->m_Tiles) {
                Tile currentTile = kv.Key;   // lVar5 (used for self-check below)
                TileScore* ts    = kv.Value; // lVar2

                TileScore* bestSafetyNeighbor  = ts;  // lVar7 — init to self
                TileScore* bestUtilityNeighbor = ts;  // lVar6 — init to self

                // Check all 8 directional neighbors
                // FUN_180688660(tile, direction, &outNeighborTile, ...) → bool hasNeighbor
                // FUN_181442600(m_Tiles, neighborTile, &outTileScore) → bool found
                for (int dir = 0; dir < 8; dir++) {
                    Tile neighborTile;
                    bool hasNeighbor = GetNeighborTile(
                        currentTile, dir, out neighborTile, 0, 0, 0);
                    //              ^^^  direction index

                    if (hasNeighbor) {
                        TileScore* neighborTS;
                        bool found = m_Tiles.TryGetValue(neighborTile, out neighborTS);

                        if (found) {
                            // Track best safety neighbor
                            // ts->+0x28 = SafetyScore (negative: less negative = safer)
                            if (neighborTS->SafetyScore > ts->SafetyScore) {
                                bestSafetyNeighbor = neighborTS;
                            }
                            // Track best utility neighbor
                            // ts->+0x30 = UtilityScore
                            if (neighborTS->UtilityScore > ts->UtilityScore) {
                                bestUtilityNeighbor = neighborTS;
                            }
                        }
                    }
                }

                // ── Assign HighestSafetyNeighbor if it qualifies ─────────
                // Condition 1: neighbor is not the same tile as self
                //   (bestSafetyNeighbor->+0x10 = Tile reference; compare to lVar5 = currentTile obj)
                // Condition 2: threshold check
                //   If ts->SafetyScore >= 0: threshold = 2.0 (neighbor must be ≥ 2× current)
                //   If ts->SafetyScore <  0: threshold = 0.5 (neighbor must be ≤ 0.5× current)
                //   Because SafetyScore is NEGATIVE, "less negative" = safer.
                //   For negative scores, 0.5× means closer to zero = safer:
                //   e.g., current = -10, threshold = 0.5 × -10 = -5; neighbor must be > -5.
                if (bestSafetyNeighbor->tile != currentTile) {
                    float safetyThreshold = (ts->SafetyScore >= 0.0f) ? 2.0f : 0.5f;
                    if (safetyThreshold * ts->SafetyScore <= bestSafetyNeighbor->SafetyScore) {
                        ts->HighestSafetyNeighbor = bestSafetyNeighbor;  // +0x50
                        WriteBarrier(ts->HighestSafetyNeighbor);
                    }
                }

                // ── Assign HighestUtilityNeighbor if it qualifies ────────
                // Same threshold logic as safety, applied to UtilityScore (+0x30).
                if (bestUtilityNeighbor->tile != currentTile) {
                    float utilityThreshold = (ts->UtilityScore >= 0.0f) ? 2.0f : 0.5f;
                    if (utilityThreshold * ts->UtilityScore <= bestUtilityNeighbor->UtilityScore) {
                        ts->HighestUtilityNeighbor = bestUtilityNeighbor;  // +0x58
                        WriteBarrier(ts->HighestUtilityNeighbor);
                    }
                }
            }
        }
    }
}
```

### PostProcessTileScores — formula summary

```
// UtilityScore pipeline (per tile):
ts.UtilityScore += ts.UtilityByAttacksScore
ts.UtilityScore  = powf(ts.UtilityScore, W.UtilityPOW)
ts.UtilityScore  = powf(unitUtilityMult × ts.UtilityScore × W.UtilityScale, W.UtilityPostPOW)
ts.UtilityScore *= W.UtilityPostScale

// SafetyScore pipeline (per tile):
ts.SafetyScore   = powf(ts.SafetyScore, W.SafetyPOW)
ts.SafetyScore   = powf(unitSafetyMult × ts.SafetyScore × W.SafetyScale, W.SafetyPostPOW)
ts.SafetyScore   = -ts.SafetyScore × W.DistanceScale    ← NEGATED — now a penalty

// Neighbor propagation threshold:
// Qualifies if: threshold × currentScore ≤ neighborScore
// threshold = 2.0 if currentScore ≥ 0, else 0.5
// Only assigned if neighbor tile != self tile
```

---

