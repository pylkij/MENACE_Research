# Handoff-AI.md — Stage Artefacts, Handoff and Collation Guide

Load this file when a stage boundary is reached. It covers writing stage artefacts,
producing the handoff prompt, and collating all stages into the final deliverable.

When invoked at a stage boundary, produce the following in this order:

**1. Stage REPORT.md**
Complete report for this stage only, following Part 1 of this file exactly.
Saved by the operator to: `[system-name]/stage-[N]/REPORT.md`

**2. Stage RECONSTRUCTIONS.md**
Complete reconstructions for all functions analysed this stage, following Part 2 of this file exactly.
Saved by the operator to: `[system-name]/stage-[N]/RECONSTRUCTIONS.md`

**3. Handoff prompt**
Invoke the **research-handoff** skill to produce this. The skill generates a compact block covering:
- Resolved FUN_ and DAT_ symbol maps (cumulative across all stages)
- Field offset tables (cumulative across all stages)
- VA status list (cumulative)
- Extraction report for the namespace
- Open questions with concrete next steps
- Next priority VA table

The handoff prompt does NOT contain REPORT.md or RECONSTRUCTIONS.md content.
Those live on disk. The handoff prompt is structurally small at every stage boundary.

---

## Part 1 — Writing REPORT.md

The report is the permanent reference. Write it as if the reader has never seen the game, the binary, or the dump. Every section should be self-contained.

### Required sections (in order)

**1. Header block**
- Game name, platform, binary details (image base), source material
- Investigation status (Complete / In Progress / Partial)

**2. Table of contents**

**3. Investigation Overview**
- What system is being investigated and why
- What was achieved (bullet list — be specific)
- What was NOT investigated (explicit scope boundary — name the things left out)

**4. Tooling**
- How `extract_rvas.py` was used for this investigation
- Any issues encountered with the tool and how they were resolved
- The specific commands used

**5. Class Inventory**
- Table: class name, namespace, TypeDefIndex, one-line role description
- One row per class that was extracted and analysed

**6. The Core Finding** *(rename to match the system)*
- The formula, algorithm, or model that is the primary result of the investigation
- Written in clean pseudocode or mathematical notation
- Followed by plain-English explanation of what it means
- Include any non-obvious conventions (e.g. sign inversions, units, normalization)

**7. Full Pipeline / System Flow** *(if applicable)*
- ASCII diagram or step-by-step description of the end-to-end flow
- Should be readable without consulting individual class sections

**8. One section per class**

Each class section must contain:

- **Namespace, TypeDefIndex, base class, role** (one paragraph)
- **Fields table**: offset | type | name | notes
- **Methods table**: method name | RVA | VA | notes
- **Behavioural notes**: anything inferred or confirmed about how the class operates at runtime that isn't obvious from the field/method lists

**9. Ghidra Address Reference**
- Complete table of all VAs analysed, split into "fully analysed" and "secondary targets not yet analysed"
- Format: VA | method | class | one-line notes

**10. Key Inferences and Design Notes**
- Non-obvious design decisions that the code reveals
- Anything that would surprise someone familiar with the codebase
- Sign conventions, dual-use of a field, coupling between systems, etc.

**11. Open Questions**
- Numbered list
- Each item: the question, why it matters, the concrete next step to answer it (e.g. "Extract class X", "Analyse function at VA Y", "Check dump.cs around line Z")

### Writing standards

- **Be exhaustive on field tables.** Every field with its offset. If the offset is unknown, say so.
- **Name every formula term.** Never write `(x + y) * z` when you can write `(SafetyScore + UtilityScore) * DistanceScale`.
- **Explain sign conventions explicitly.** If a score is stored negative, say so and explain why.
- **Note where field meanings were inferred vs confirmed.** Use "confirmed" when Ghidra code directly writes/reads the field. Use "inferred" when derived from naming, type, or context.
- **Do not editorialize.** State what the code does. Design opinions belong in "Design Notes," clearly labelled.
- **Include all warnings from the extraction tool.** If `extract_rvas.py` flagged anything, note it.

---

## Part 2 — Writing RECONSTRUCTIONS.md

Every function for which Ghidra output was provided must appear in RECONSTRUCTIONS.md, without exception.

### Required structure per function

```markdown
## N. ClassName.MethodName — 0x18XXXXXXXX

### Raw Ghidra output
```c
[paste the raw Ghidra decompilation verbatim, unmodified]
```

### Annotated reconstruction
```c
[fully annotated C-style reconstruction]
```

### [MethodName] — design notes  *(optional, include when the function has non-obvious behaviour)*
[prose notes on anything surprising or important]
```

### Rules for the annotated reconstruction

**Always:**
- Replace every `param_1 + 0xNN` with the named field: `self->FieldName`
- Replace every known `FUN_18XXXXXXXX` with the method's real name or a descriptive alias
- Replace every known `DAT_18XXXXXXXX` with what it refers to (e.g. `DebugVisualization_class`, `WEIGHTS`)
- Expand vtable calls to named methods where known: `c->vtable[0x178](c, actor)  // IsApplicable`
- Collapse all IL2CPP init guards to a single comment: `// IL2CPP lazy init — omitted`
- Collapse all write barriers to inline comment: `// write barrier`
- Add a comment on every line that accesses a field: `// +0x30 = UtilityScore`
- Document every early-out and what condition triggers it
- Annotate every loop: what collection is being iterated, what the loop variable represents

**Never:**
- Leave a raw `FUN_18XXXXXXXX` call without annotation if it appears in any other reconstruction in the same document
- Leave a raw `param_1 + 0xNN` offset without naming it if the class is known
- Remove or simplify the logic — represent it faithfully, annotated
- Add behaviour that isn't in the raw output

**For truncated functions** (Ghidra output cut off mid-function):
- Note clearly: `// [TRUNCATED at line N — remaining logic not analysed]`
- Reconstruct as far as the data allows
- List what the truncated section likely contains based on context

### Ordering

Functions must appear in the document in logical order:
1. Simple leaf functions first (functions that call nothing else in the investigation)
2. Then functions that call the leaf functions
3. Then the top-level entry points last

This means a reader can follow the document linearly without forward references.

### Document header

```markdown
# [Game] [System] — Annotated Function Reconstructions

**Source:** Ghidra decompilation of [Game] ([platform], [binary type])
**Image base:** 0x180000000
**Format:** Each function shows the raw Ghidra output followed by a fully annotated
C-style reconstruction with all offsets resolved.
```

Include a quick-reference offset table at the top for every class whose fields are referenced in the reconstructions.

---

## Part 3 — Quality Checklist

Run this checklist before delivering stage artefacts.

**REPORT.md**
- [ ] All classes have complete field offset tables (no missing offsets)
- [ ] All methods have both RVA and VA listed
- [ ] The core formula or algorithm is stated explicitly in clean notation
- [ ] All non-obvious sign conventions and units are explained
- [ ] All inferences are labelled as inferred vs. confirmed
- [ ] Open questions section exists and each item has a concrete next step
- [ ] Scope boundaries are explicit — what was NOT investigated is listed

**RECONSTRUCTIONS.md**
- [ ] Every function from Ghidra output appears, without exception
- [ ] Every `param_1 + 0xNN` is resolved to a named field
- [ ] Every known `FUN_18XXXXXXXX` is named or aliased
- [ ] Every `DAT_18XXXXXXXX` is identified
- [ ] IL2CPP boilerplate is collapsed to comments, not described as logic
- [ ] Functions appear in leaf-first order
- [ ] Truncated functions are clearly marked
- [ ] Raw Ghidra output is included verbatim for every function

**General**
- [ ] No fabricated behaviour — everything stated is derivable from the raw data
- [ ] No unexplained jargon — every IL2CPP pattern is either decoded or linked to the pattern table in Research-AI.md
- [ ] The investigation can be read cold by someone unfamiliar with this system

---

## Part 4 — Producing the Handoff Prompt

After stage artefacts pass the quality checklist, produce the handoff prompt using the
research-handoff skill. The handoff prompt contains only:

- Resolved FUN_ and DAT_ symbol maps (cumulative across all stages)
- Field offset tables (cumulative across all stages)
- VA status list (cumulative)
- Extraction report for the namespace
- Open questions with concrete next steps
- Next priority VA table

It does NOT contain REPORT.md or RECONSTRUCTIONS.md content. Those live on disk.

---

## Part 5 — Collation (Final Stage Only)

When the last VA in the namespace has been analysed, do not produce a handoff prompt.
Write the final stage artefacts, then open a collation session with the following inputs:

- Research-AI.md and Handoff-AI.md
- All stage REPORT.md files (attached)
- All stage RECONSTRUCTIONS.md files (attached)
- The extraction report

Produce a single unified REPORT.md and RECONSTRUCTIONS.md applying these rules:

- **Field tables:** Deduplicate. One table per class, combining entries from all stages. Where the same field appears in multiple stages, use the most specific description.
- **Symbol maps:** Merge all FUN_ and DAT_ resolutions. Remove duplicates.
- **RECONSTRUCTIONS.md ordering:** Enforce leaf-first order across all stages combined. A function from Stage 3 may appear before a function from Stage 1 if it is a leaf that the Stage 1 function calls.
- **REPORT.md narrative:** Write as one coherent investigation. Do not reference stage numbers — the reader should not see the stage structure.
- **Open questions:** Resolve any questions answered in later stages. Carry remaining unresolved questions forward.
- **Scope boundaries:** Consolidate all scope boundary decisions from all stages into one definitive list.

The collation session produces the permanent deliverable. Stage artefacts are archived
and not referenced after collation is complete.

---

## Part 6 — Worked Example Summary

The tactical AI investigation (`investigations/tactical-ai/`) is the reference implementation. When in doubt, consult it.

Key decisions made in that investigation that should be replicated:

- **Started from a debug settings class** (`TacticalStateSettings`) and followed outward to the AI brain (`Agent`). This is a reliable strategy: debug/inspector classes expose the runtime data model and the names of the systems they control.
- **Extracted all classes before starting Ghidra work.** The extraction report gave field offsets that made Ghidra output immediately readable.
- **Batched Ghidra requests by logical group.** All scoring functions together, then all agent lifecycle functions together. This reduces context-switching.
- **Resolved `DAT_` symbols by cross-referencing static field access patterns.** When `*(DAT_18394c3d0 + 0xb8)` appeared in multiple functions, the pattern was identified once (DebugVisualization class static) and applied everywhere.
- **Named the sign inversion explicitly.** `SafetyScore` being stored negative was a non-obvious convention that would have caused confusion downstream. It was identified from `PostProcessTileScores` and called out in both REPORT.md and RECONSTRUCTIONS.md.
- **Did not pursue Criterion subclasses.** The interface was documented (four vtable slots, confirmed purposes), and the concrete implementations were left as open questions. This was the right scope boundary — the scoring model was fully understood without them.
