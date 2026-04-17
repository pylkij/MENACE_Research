# Implementation Plan — `GlbLoader` Bug Verification (Discrete Steps)

## Overview

Each scan is a **separate, self-contained plugin**. Run one at a time. After each run, validate the log output against the expected pattern for that step before proceeding to the next. No scan depends on another being loaded simultaneously — dependencies between scans (e.g. Scan 0 gating Scan B) are resolved by reading the log from the prior run, not by runtime coupling.

**Operator workflow per step:**
1. Drop only the relevant plugin `.cs` file into the modpack plugin directory.
2. Launch the game into the target scene ("Tactical" unless noted).
3. Capture the MelonLoader log.
4. Validate against the **Expected output / Log validation** block for that step.
5. Unload / remove the plugin before running the next step.

---

## Test Asset Requirements

These must be prepared before any step is run. All four go in the same modpack's `models/` directory.

| Asset | Filename | Requirements |
|---|---|---|
| **CharacterGLB** | `rmc_test_soldier.glb` | Single skinned mesh, bone names matching a known game skeleton (e.g. `pelvis`, `spine_01`). Single primitive, single material. Non-trivial bone rotations (at least one bone rotated 90° around a single axis in Blender rest pose). |
| **MultiMatGLB** | `test_multimaterial.glb` | Single mesh, exactly two primitives. Primitive 0: pure red material. Primitive 1: pure blue material. No skeleton. |
| **TangentGLB** | `test_tangents.glb` | Flat quad, one directional normal map applied (bump protruding toward camera). Tangent data exported. No skeleton. |
| **KnownRotGLB** | `test_known_rotation.glb` | Single bone, rest pose rotated exactly 90° around X-axis in GLTF space. Documented expected Unity result after correct conversion. |

---

## Shared plugin boilerplate

Each step below is a complete plugin. Substitute the body of `OnSceneLoaded` with the code block shown for that step. The boilerplate does not change between steps.

```csharp
using System;
using System.Collections;
using MelonLoader;
using Menace.ModpackLoader;
using Menace.SDK;
using UnityEngine;

namespace GlbLoaderScanPlugin;

public class Plugin : IModpackPlugin
{
    private MelonLogger.Instance _log;
    private HarmonyLib.Harmony _harmony;

    public void OnInitialize(MelonLogger.Instance logger, HarmonyLib.Harmony harmony)
    {
        _log = logger;
        _harmony = harmony;
        _log.Msg("GlbLoaderScanPlugin loaded.");
    }

    public void OnSceneLoaded(int buildIndex, string sceneName)
    {
        if (sceneName != "Tactical") return;
        // >>> SUBSTITUTE STEP BODY HERE <<<
    }

    public void OnUpdate() { }
    public void OnGUI() { }
    public void OnUnload() { }
}
```

---

## Step 0 — Animation pipeline preflight

**Verifies:** That the game's SMR bone transforms are written through Unity's `Transform` hierarchy during animation, making `localPosition` observable per-frame. This must be run and validated **before Step B** — if it fails, Step B's `moved=False` result is uninterpretable and should not appear in the report without a caveat.

**Prerequisites:** A live game character in the scene whose animator is actively playing a locomotion or idle animation (not a T-pose bind state).

**Step body — substitute into `OnSceneLoaded`:**

```csharp
_log.Msg("=== Step 0: Animation pipeline preflight ===");
try
{
    // Find a native animated character by locating any active Animator
    // with a running state — does not depend on any specific clone name.
    Animator targetAnimator = null;
    foreach (var a in GameObject.FindObjectsOfType<Animator>())
    {
        if (a.enabled && a.runtimeAnimatorController != null && a.isActiveAndEnabled)
        {
            targetAnimator = a;
            break;
        }
    }

    if (targetAnimator == null)
    {
        _log.Error("Step0: No active Animator found in scene — cannot validate animation pipeline.");
        _log.Error("Step0: ENVIRONMENT ISSUE — ensure a live character is present before running this step.");
        return;
    }

    _log.Msg($"Step0: Found Animator on '{targetAnimator.gameObject.name}' " +
             $"(root: '{targetAnimator.transform.root.name}')");

    // Confirm it has an SMR with bones — a pure transform-driven rig is also acceptable
    // but SMR bones are what Step B will be observing, so prefer one.
    var smr = targetAnimator.GetComponentInChildren<SkinnedMeshRenderer>();
    if (smr == null || smr.bones.Length == 0)
    {
        _log.Error("Step0: Animator found but no SMR with bones — cannot sample Transform writes.");
        _log.Error("Step0: ENVIRONMENT ISSUE — target a character with a skinned mesh rig.");
        return;
    }

    _log.Msg($"Step0: SMR '{smr.name}' bone count = {smr.bones.Length}. Starting two-frame sample.");
    MelonCoroutines.Start(Step0_ConfirmTransformWrites(smr.bones));
}
catch (Exception ex)
{
    _log.Error($"Step0 exception: {ex}");
}
```

**Coroutine — add as a method on the Plugin class:**

```csharp
private IEnumerator Step0_ConfirmTransformWrites(Transform[] gameBones)
{
    var pos1 = Array.ConvertAll(gameBones, b => b != null ? b.localPosition : Vector3.zero);

    yield return null;

    bool anyMoved = false;
    for (int i = 0; i < Math.Min(gameBones.Length, 3); i++)
    {
        var curr = gameBones[i] != null ? gameBones[i].localPosition : Vector3.zero;
        bool moved = curr != pos1[i];
        anyMoved |= moved;
        _log.Msg($"Step0: GameBone[{i}] ({gameBones[i]?.name}) frame1={pos1[i]} frame2={curr} moved={moved}");
    }

    if (anyMoved)
        _log.Msg("Step0: PASS — game bones move via Transform writes. Step B motion comparison is valid.");
    else
        _log.Msg("Step0: FAIL — game bones static across frames. FBX pipeline may bypass Transform writes. Step B results are NOT reliable.");
}
```

**Log validation — PASS:**
```
Step0: Animator present=True enabled=True hasController=True
Step0: GameBone[0] (pelvis) frame1=(0.012, 0.941, 0.003) frame2=(0.019, 0.938, -0.001) moved=True
Step0: GameBone[1] (spine_01) frame1=(0.000, 0.102, 0.000) frame2=(0.001, 0.102, 0.001) moved=True
Step0: PASS — game bones move via Transform writes. Step B motion comparison is valid.
```

**Log validation — FAIL (record and proceed to Step A; skip Step B):**
```
Step0: Animator present=True enabled=True hasController=True
Step0: GameBone[0] (pelvis) frame1=(0.012, 0.941, 0.003) frame2=(0.012, 0.941, 0.003) moved=False
Step0: FAIL — game bones static across frames. FBX pipeline may bypass Transform writes. Step B results are NOT reliable.
```

If Step 0 fails, proceed to Step A as normal. Do **not** run Step B. Carry the failure into the report's Open Questions section.

---

## Step A — Shadow skeleton: instance ID comparison

**Verifies:** `SetupBones` creates a parallel bone hierarchy not connected to the game's animated transforms.

**Prerequisites:** `rmc_test_soldier.glb` loaded; a game character of the matching prefab name present in scene. Step 0 does not need to have passed — this step's evidence is independent of animation.

**Step body — substitute into `OnSceneLoaded`:**

```csharp
_log.Msg("=== Step A: Shadow skeleton instance ID comparison ===");
try
{
    var customRoot = GameObject.Find("rmc_test_soldier");
    if (customRoot == null) { _log.Error("StepA: rmc_test_soldier root not found"); return; }

    var customSmr = customRoot.GetComponentInChildren<SkinnedMeshRenderer>();
    if (customSmr == null) { _log.Error("StepA: No SMR on custom prefab"); return; }

    var gameCharacterRoot = GameObject.Find("rmc_default_female_soldier(Clone)");
    if (gameCharacterRoot == null) { _log.Error("StepA: Game character root not found"); return; }

    var gameSmr = gameCharacterRoot.GetComponentInChildren<SkinnedMeshRenderer>();
    if (gameSmr == null) { _log.Error("StepA: No SMR on game character"); return; }

    _log.Msg($"StepA: Custom SMR mesh: {customSmr.sharedMesh?.name}");
    _log.Msg($"StepA: Game SMR mesh: {gameSmr.sharedMesh?.name}");

    _log.Msg($"StepA: Custom SMR bone count: {customSmr.bones.Length}");
    foreach (var b in customSmr.bones)
        _log.Msg($"StepA: CustomBone name={b?.name} instanceID={b?.GetInstanceID()} goID={b?.gameObject.GetInstanceID()}");

    _log.Msg($"StepA: Game SMR bone count: {gameSmr.bones.Length}");
    foreach (var b in gameSmr.bones)
        _log.Msg($"StepA: GameBone name={b?.name} instanceID={b?.GetInstanceID()} goID={b?.gameObject.GetInstanceID()}");

    _log.Msg($"StepA: Custom SMR rootBone name={customSmr.rootBone?.name} instanceID={customSmr.rootBone?.GetInstanceID()}");
    _log.Msg($"StepA: Game SMR rootBone name={gameSmr.rootBone?.name} instanceID={gameSmr.rootBone?.GetInstanceID()}");
}
catch (Exception ex)
{
    _log.Error($"StepA exception: {ex}");
}
```

**Log validation — bug confirmed:**
```
StepA: CustomBone name=pelvis instanceID=11204 goID=11200
StepA: GameBone   name=pelvis instanceID=9844  goID=9840
StepA: Custom SMR rootBone name=pelvis instanceID=11204
StepA: Game SMR   rootBone name=pelvis instanceID=9844
```

Identical bone names; entirely disjoint instance IDs across all entries confirm a shadow hierarchy.

---

## Step B — Bone motion sampling across frames

**Prerequisite: Step 0 must have logged `PASS` before running this step.** If Step 0 failed, skip this step entirely and note the omission in the report.

**Verifies:** Custom bones receive no animation data; game bones animate normally.

**Step body — substitute into `OnSceneLoaded`:**

```csharp
_log.Msg("=== Step B: Bone motion across 2 frames ===");
try
{
    var customRoot = GameObject.Find("rmc_test_soldier");
    if (customRoot == null) { _log.Error("StepB: rmc_test_soldier root not found"); return; }

    var customSmr = customRoot.GetComponentInChildren<SkinnedMeshRenderer>();
    if (customSmr == null) { _log.Error("StepB: No SMR on custom prefab"); return; }

    var gameCharacterRoot = GameObject.Find("rmc_default_female_soldier(Clone)");
    if (gameCharacterRoot == null) { _log.Error("StepB: Game character root not found"); return; }

    var gameSmr = gameCharacterRoot.GetComponentInChildren<SkinnedMeshRenderer>();
    if (gameSmr == null) { _log.Error("StepB: No SMR on game character"); return; }

    MelonCoroutines.Start(StepB_TwoFrameSample(customSmr.bones, gameSmr.bones));
}
catch (Exception ex)
{
    _log.Error($"StepB exception: {ex}");
}
```

**Coroutine — add as a method on the Plugin class:**

```csharp
private IEnumerator StepB_TwoFrameSample(Transform[] customBones, Transform[] gameBones)
{
    var customPos1 = Array.ConvertAll(customBones, b => b != null ? b.localPosition : Vector3.zero);
    var gamePos1   = Array.ConvertAll(gameBones,   b => b != null ? b.localPosition : Vector3.zero);
    _log.Msg("StepB: Frame 1 positions recorded.");

    yield return null;

    for (int i = 0; i < Math.Min(customBones.Length, 3); i++)
    {
        var curr = customBones[i] != null ? customBones[i].localPosition : Vector3.zero;
        _log.Msg($"StepB: CustomBone[{i}] ({customBones[i]?.name}) frame1={customPos1[i]} frame2={curr} moved={curr != customPos1[i]}");
    }

    for (int i = 0; i < Math.Min(gameBones.Length, 3); i++)
    {
        var curr = gameBones[i] != null ? gameBones[i].localPosition : Vector3.zero;
        _log.Msg($"StepB: GameBone[{i}] ({gameBones[i]?.name}) frame1={gamePos1[i]} frame2={curr} moved={curr != gamePos1[i]}");
    }
}
```

**Log validation — bug confirmed:**
```
StepB: CustomBone[0] (pelvis) frame1=(0.0, 0.0, 0.0) frame2=(0.0, 0.0, 0.0) moved=False
StepB: GameBone[0]   (pelvis) frame1=(0.012, 0.941, 0.003) frame2=(0.019, 0.938, -0.001) moved=True
```

---

## Step C — `ConvertRotation` quaternion inversion

**Verifies:** The W negation produces the conjugate (inverse) of the correct rotation.

**Prerequisites:** `test_known_rotation.glb` loaded (one bone, rest pose exactly 90° around X in GLTF space). Does not require a live character.

**Step body — substitute into `OnSceneLoaded`:**

```csharp
_log.Msg("=== Step C: ConvertRotation quaternion inversion ===");
try
{
    var testRoot = GameObject.Find("test_known_rotation");
    if (testRoot == null) { _log.Error("StepC: test_known_rotation root not found"); return; }

    var allTransforms = testRoot.GetComponentsInChildren<Transform>();
    foreach (var t in allTransforms)
    {
        if (t.name == "test_known_rotation" || t.name == "ModelContainer" || t.name == "Armature") continue;
        var q = t.localRotation;
        _log.Msg($"StepC: Bone '{t.name}' localRotation x={q.x:F4} y={q.y:F4} z={q.z:F4} w={q.w:F4}");
        _log.Msg($"StepC: Expected (correct Z-flip of 90 deg X): x=-0.7071 y=0.0000 z=0.0000 w=0.7071");
        _log.Msg($"StepC: Actual W sign negative={q.w < 0} (true = conjugate bug confirmed)");
        break;
    }
}
catch (Exception ex)
{
    _log.Error($"StepC exception: {ex}");
}
```

**Log validation — bug confirmed:**
```
StepC: Bone 'root_bone' localRotation x=0.7071 y=0.0000 z=0.0000 w=-0.7071
StepC: Expected (correct Z-flip of 90 deg X): x=-0.7071 y=0.0000 z=0.0000 w=0.7071
StepC: Actual W sign negative=True (true = conjugate bug confirmed)
```

---

## Step D — Tangent W negation

**Verifies:** Tangent W component is negated on import.

**Prerequisites:** `test_tangents.glb` loaded.

**Step body — substitute into `OnSceneLoaded`:**

```csharp
_log.Msg("=== Step D: Tangent W negation ===");
try
{
    var testRoot = GameObject.Find("test_tangents");
    if (testRoot == null) { _log.Error("StepD: test_tangents root not found"); return; }

    var mf = testRoot.GetComponentInChildren<MeshFilter>();
    if (mf == null || mf.sharedMesh == null) { _log.Error("StepD: No MeshFilter/Mesh found"); return; }

    var tangents = mf.sharedMesh.tangents;
    if (tangents == null || tangents.Length == 0) { _log.Error("StepD: No tangents on mesh"); return; }

    for (int i = 0; i < Math.Min(3, tangents.Length); i++)
        _log.Msg($"StepD: tangent[{i}] x={tangents[i].x:F4} y={tangents[i].y:F4} z={tangents[i].z:F4} w={tangents[i].w:F4}");

    _log.Msg($"StepD: Expected W = +1.0 (GLTF spec default for standard winding)");
    _log.Msg($"StepD: Actual W negative={tangents[0].w < 0} (true = inversion bug confirmed)");
}
catch (Exception ex)
{
    _log.Error($"StepD exception: {ex}");
}
```

**Log validation — bug confirmed:**
```
StepD: tangent[0] x=1.0000 y=0.0000 z=0.0000 w=-1.0000
StepD: Expected W = +1.0 (GLTF spec default for standard winding)
StepD: Actual W negative=True (true = inversion bug confirmed)
```

---

## Step E — Multi-material submesh assignment

**Verifies:** Only the first primitive's material is assigned; `sharedMaterials.Length` is 1 despite `subMeshCount` being 2.

**Prerequisites:** `test_multimaterial.glb` loaded.

**Step body — substitute into `OnSceneLoaded`:**

```csharp
_log.Msg("=== Step E: Multi-material submesh assignment ===");
try
{
    var testRoot = GameObject.Find("test_multimaterial");
    if (testRoot == null) { _log.Error("StepE: test_multimaterial root not found"); return; }

    var mr = testRoot.GetComponentInChildren<MeshRenderer>();
    var mf = testRoot.GetComponentInChildren<MeshFilter>();
    if (mr == null || mf == null) { _log.Error("StepE: No MeshRenderer/MeshFilter found"); return; }

    _log.Msg($"StepE: subMeshCount = {mf.sharedMesh.subMeshCount}");
    _log.Msg($"StepE: sharedMaterials.Length = {mr.sharedMaterials.Length}");
    for (int i = 0; i < mr.sharedMaterials.Length; i++)
        _log.Msg($"StepE: sharedMaterials[{i}].name = {mr.sharedMaterials[i]?.name}");

    _log.Msg($"StepE: Expected sharedMaterials.Length = 2");
    _log.Msg($"StepE: Multi-material bug confirmed = {mf.sharedMesh.subMeshCount > mr.sharedMaterials.Length}");
}
catch (Exception ex)
{
    _log.Error($"StepE exception: {ex}");
}
```

**Log validation — bug confirmed:**
```
StepE: subMeshCount = 2
StepE: sharedMaterials.Length = 1
StepE: sharedMaterials[0].name = mat_red
StepE: Expected sharedMaterials.Length = 2
StepE: Multi-material bug confirmed = True
```

---

## Step F — Shader fallback

**No plugin code required — log capture only.**

Run any session with the GlbLoader active. Capture the MelonLoader log and locate:

```
[GlbLoader] Using shader: Standard
```

Also capture the Unity/HDRP version block at the top of the log, which identifies the render pipeline. If `HDRP/Lit` cannot be found but the game uses HDRP, the log line itself is the evidence.

**Log validation — evidence captured:**
```
[GlbLoader] Using shader: Standard
```
Confirm the render pipeline from the session header and record both in the report.

---

## Step G — `ModelContainer` rotation applied universally

**Verifies:** The `-90°/-90°` rotation is present on a non-weapon GLB.

**Prerequisites:** `rmc_test_soldier.glb` loaded (a character model, not a weapon).

**Step body — substitute into `OnSceneLoaded`:**

```csharp
_log.Msg("=== Step G: ModelContainer rotation on non-weapon GLB ===");
try
{
    var testRoot = GameObject.Find("rmc_test_soldier");
    if (testRoot == null) { _log.Error("StepG: rmc_test_soldier not found"); return; }

    var container = testRoot.transform.Find("ModelContainer");
    if (container == null) { _log.Error("StepG: ModelContainer child not found"); return; }

    var euler = container.localEulerAngles;
    _log.Msg($"StepG: ModelContainer localEulerAngles = {euler}");
    _log.Msg($"StepG: Expected for character model = (0.0, 0.0, 0.0)");
    _log.Msg($"StepG: Weapon rotation applied to non-weapon = {Mathf.Abs(euler.x) > 1f || Mathf.Abs(euler.z) > 1f}");
}
catch (Exception ex)
{
    _log.Error($"StepG exception: {ex}");
}
```

**Log validation — bug confirmed:**
```
StepG: ModelContainer localEulerAngles = (-90.0, 0.0, -90.0)
StepG: Expected for character model = (0.0, 0.0, 0.0)
StepG: Weapon rotation applied to non-weapon = True
```

---

## Step H — `LoadedCount` accumulation

**Verifies:** `_loadedModels` accumulates across repeated `LoadModpackModels` calls with no deduplication.

**Note:** Substitute the actual modpack path for `testModpackPath` before running.

**Step body — substitute into `OnSceneLoaded`:**

```csharp
_log.Msg("=== Step H: LoadedCount accumulation ===");
try
{
    // >>> SUBSTITUTE: actual modpack path used in this test run <<<
    var testModpackPath = "Mods/GlbScanTestPack";

    var countBefore = GlbLoader.LoadedCount;
    _log.Msg($"StepH: LoadedCount before second load call = {countBefore}");

    GlbLoader.LoadModpackModels(testModpackPath);

    var countAfter = GlbLoader.LoadedCount;
    _log.Msg($"StepH: LoadedCount after second load call = {countAfter}");
    _log.Msg($"StepH: Count increased by {countAfter - countBefore} (expected 0 if deduplication exists)");
    _log.Msg($"StepH: Accumulation bug confirmed = {countAfter > countBefore}");
}
catch (Exception ex)
{
    _log.Error($"StepH exception: {ex}");
}
```

**Log validation — bug confirmed:**
```
StepH: LoadedCount before second load call = 4
StepH: LoadedCount after second load call = 8
StepH: Count increased by 4 (expected 0 if deduplication exists)
StepH: Accumulation bug confirmed = True
```

---

## Finding 9 — `IsCharacterPrefabName` false positives

**No plugin scan required — static analysis only.**

Document with a static table derived from the source keyword list, showing which non-character filenames would trigger auto-registration. Mark clearly in the report: **"Verified by source analysis — no runtime scan required."** The maintainer can verify by inspection.

---

## Run order and dependency summary

| Step | Depends on | Notes |
|---|---|---|
| Step 0 | — | Run first. Records PASS/FAIL for Step B gating. |
| Step A | — | Independent. Run in any order after Step 0. |
| Step B | Step 0 PASS | **Skip entirely if Step 0 logged FAIL.** |
| Step C | — | Independent. No live character required. |
| Step D | — | Independent. No live character required. |
| Step E | — | Independent. No live character required. |
| Step F | — | Log capture only. No plugin needed. |
| Step G | — | Independent. |
| Step H | — | Independent. Substitute modpack path before running. |
| Finding 9 | — | Static analysis. No runtime step. |

## Report section checklist

| Report Section | Step | Evidence type |
|---|---|---|
| Animation pipeline validity (preflight) | Step 0 | Transform motion log — gates Step B |
| Shadow skeleton — bones not driven | Steps A + B | Instance ID log + motion log (if Step 0 passed) |
| `ConvertRotation` conjugate error | Step C | Quaternion component log |
| Tangent W inversion | Step D | Tangent array log |
| Multi-material assignment | Step E | `subMeshCount` vs `sharedMaterials.Length` log |
| Shader fallback undisclosed | Step F | Raw MelonLoader session log (capture only) |
| Weapon rotation on all models | Step G | `localEulerAngles` log |
| `LoadedCount` accumulation | Step H | Before/after count log |
| `IsCharacterPrefabName` false positives | None | Static analysis table |

The **Working Implementation** section of the report is intentionally left blank — purpose is verification only. **Open Questions** should carry forward: whether `SetupBones` is intended to be replaced wholesale by a runtime skeleton-binding approach, and whether the `ModelContainer` rotation is meant to be conditional on a model type flag that does not yet exist in the `LoadedModel` API.
