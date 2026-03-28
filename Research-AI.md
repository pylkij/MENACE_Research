# Research-AI.md — AI Agent Research Guide

This document instructs AI agents on how to conduct reverse engineering investigations into Menace game systems, following the methodology established in the tactical AI investigation. Read this document in full before beginning any research task.

---

## What You Are Doing

You are reverse engineering internal systems of a Unity IL2CPP game called Menace. Your inputs are:

- A `dump.cs` file produced by Il2CppDumper (~32 MB, ~885,000 lines)
- Ghidra decompilation output (raw C pseudocode) provided by the human operator
- Class dumps from the extraction tool
- Previously completed investigation reports in this repository

Your outputs are:
- `REPORT.md` — complete findings: class layouts, field offsets, method addresses, formulas, design inferences, open questions
- `RECONSTRUCTIONS.md` — every Ghidra-decompiled function with its raw output followed by a fully annotated C reconstruction

The standard is: **someone with no prior context on this system should be able to read the report and understand exactly what the code does, without opening Ghidra.**

---

## Part 1 — Orientation

### The binary

- Platform: Windows x64, Unity IL2CPP
- Image base: `0x180000000`
- VA = RVA + `0x180000000`
- All Ghidra addresses are VAs. Use them directly with Go To Address (G key).
- **Never use RVAs from dummy DLL stubs.** Only RVAs from `dump.cs` are accurate.

### IL2CPP patterns

Memorise these. They appear in every function and must be decoded silently — never treat them as unknown.

| Raw Ghidra pattern | Meaning |
|---|---|
| `FUN_180427b00(&DAT_...)` followed by `DAT_... = '\x01'` | `il2cpp_runtime_class_init()` — lazy static initialisation guard. Standard IL2CPP boilerplate. Ignore. |
| `*(DAT_... + 0xe4) == 0` then `il2cpp_runtime_class_init(...)` | Class not yet runtime-initialised. Ignore. |
| `*(DAT_... + 0xb8)` | Pointer to the static field storage block for a class. |
| `**(DAT_... + 0xb8)` or `*(*(DAT_... + 0xb8) + 0x00)` | First static field of that class (often a singleton). |
| `*(staticStorage + 0x08)` | Second static field (in the tactical AI investigation, this is `DebugVisualization.WEIGHTS`). |
| `FUN_180427d90()` with `/* WARNING: Subroutine does not return */` | `NullReferenceException()`. A null guard that throws. |
| `FUN_180427d80()` with `/* WARNING: Subroutine does not return */` | `IndexOutOfRangeException()`. An array bounds check that throws. |
| `FUN_1804bad80(value, exponent)` | `powf(value, exponent)`. Floating-point power. |
| `FUN_180426e50(ptr, value)` | IL2CPP write barrier. GC notification after writing a reference. Ignore semantically. |
| `FUN_18152f9b0(&iterator, class)` | Dictionary/list enumerator `MoveNext()`. Returns bool. |
| `FUN_18136d8a0(&out, collection, class)` | `GetEnumerator()` on a Dictionary. |
| `FUN_180cbab80(&out, collection, class)` | `GetEnumerator()` on a List. |
| `FUN_1814f4770(&iterator, class)` | List enumerator `MoveNext()`. Returns bool. |
| `FUN_1804f7ee0(&iterator, class)` | Enumerator `Dispose()`. End of foreach. |
| `(**(code **)(*ptr + 0xNNN))(ptr, *(undefined8 *)(*ptr + 0xMMM))` | Virtual method call. `ptr->vtable[0xNNN/8](ptr, ptr->vtableArg)`. |
| `FUN_180426ed0(class, slotCount)` | Allocate a new object of a given class with N slots. |
| `FUN_180cca560(list, index, class)` | `List[index]` — get element at index. |
| `FUN_1804608d0(class)` | Allocate/construct a list or collection of the given class. |
| Repeated triple-checked init guard for same DAT | Standard IL2CPP thread-safe lazy init pattern. Collapse all three into one init check. |

### Cross-referencing field offsets

When you see `*(float *)(param_1 + 0x30)` and `param_1` is a known class instance:

1. Look up the class's field table.
2. Find the field at offset `0x30`.
3. Replace `*(float *)(param_1 + 0x30)` with `self->FieldName` in your reconstruction.

Always do this. Never leave offsets as raw hex in a reconstruction without naming them.

### Vtable method identification

When you see `(**(code **)(*plVar + 0x188))(plVar, ...)`:

- The vtable offset is `0x188`.
- Cross-reference with known vtable slots from other reconstructed functions in this investigation.
- If the class type of `plVar` is known from field tables, note what method is at that slot based on context (return type, arguments, surrounding logic).
- If unresolvable: annotate as `// vtable +0x188 — unknown method, likely [best guess based on context]`.

---

## Part 2 — The Research Process

### Step 1: Establish the entry point

The human operator will provide a starting class or system. Before doing anything else:

1. Ask the operator to run `extract_rvas.py` on the target class (or run it yourself if you have shell access).
2. Read the extraction report. Confirm field offsets and method RVAs.
3. Read any existing investigation reports in this repository for cross-reference context.
4. Identify the most informative Ghidra targets. Prioritise functions that are:
   - Short (under 30 lines): always analyse, low cost.
   - Contain the core formula or algorithm for the system.
   - Named in a way that suggests they are the "master" function (e.g. `GetScore`, `Evaluate`, `Execute`).
   - Called by other functions already being analysed.

### Step 2: Provide Ghidra addresses

Convert all target RVAs to VAs (`VA = RVA + 0x180000000`) and present them as a priority-ordered table. Include the method name, VA, and one-sentence rationale for each. The operator will paste Ghidra output back to you.

Format:
```
| Priority | Method | VA | Rationale |
|---|---|---|---|
| 1 | ClassName.MethodName | 0x18XXXXXXXX | [why this first] |
```

### Step 3: Analyse Ghidra output

When the operator provides Ghidra decompilation output:

1. **Identify all field accesses** — cross-reference every `(param_1 + 0xNN)` against the known field table.
2. **Identify all function calls** — resolve known functions (from previous analyses in this session or repo), annotate unknown ones with best-guess purpose.
3. **Decode all IL2CPP boilerplate** silently — do not describe the init guards or write barriers in your analysis prose.
4. **Identify the logical structure** — guards, early-outs, main loop, state machine transitions.
5. **Extract the core algorithm** — the formula, the condition, the side effect that this function actually performs.

State your findings clearly in prose first. Then request additional functions if needed.

### Step 4: Follow the call chain

After analysing a function, identify what remains unknown:

- What populates the inputs this function reads?
- What consumes the outputs this function writes?
- Are there called functions (`FUN_18XXXXXXXX`) whose behaviour is not yet known and is material to understanding this system?

Provide the next batch of Ghidra targets using the same priority table format. Continue until the system is fully understood or a natural boundary is reached (e.g. a virtual dispatch into unknown subclasses, a system outside the investigation scope).

### Step 5: Recognise when to stop

Stop requesting new functions when:

- The core formula and all its inputs are fully resolved.
- All significant unknowns are either resolved or explicitly documented as open questions.
- The remaining unknown functions are either:
  - Boilerplate (constructors, simple accessors, dispose)
  - A separate system that warrants its own investigation
  - Concrete subclasses implementing a known interface (document the interface, defer the implementations)

Do not pursue diminishing returns. A well-scoped investigation with clear open questions is better than an incomplete investigation that chased everything.

---

## Part 3 — Writing REPORT.md

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

## Part 4 — Writing RECONSTRUCTIONS.md

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

## Part 5 — Communication Protocol with the Operator

### When requesting Ghidra output

Always provide:
1. A numbered priority table of VAs with rationale
2. The expected size/complexity of each function (if known from the dump)
3. Whether multiple functions can be batched into one Ghidra export

Format the VA table so the operator can copy it directly into Ghidra's batch export tool.

### When receiving Ghidra output

Immediately confirm:
- How many functions were received vs. requested
- Whether any were truncated
- Whether any were missing (wrong address, not a function boundary)

Then analyse. Do not ask clarifying questions before analysing — make your best determination from the evidence and note uncertainty explicitly.

### When a function is unreadable

If a function is too complex to reconstruct with confidence:

1. Reconstruct what you can, marking uncertain sections: `// [UNCERTAIN: could be X or Y]`
2. Identify specifically what additional context would resolve the uncertainty (another function, a field type, a class dump)
3. Request that context explicitly

Never fabricate behaviour. If a section of code is genuinely ambiguous, say so.

### Flagging discoveries that affect scope

If analysis reveals that the system is larger or more connected than initially scoped, flag it immediately:

> **Scope note:** `FUN_18XXXXXXXX` called from `MethodName` appears to implement [description]. This is outside the current investigation scope. It is documented as an open question. Recommend a separate investigation.

Do not expand scope silently. Always flag and get operator acknowledgement before pursuing a new thread.

---

## Part 6 — Quality Checklist

Before declaring an investigation complete, verify:

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
- [ ] No unexplained jargon — every IL2CPP pattern is either decoded or linked to the pattern table
- [ ] The investigation can be read cold by someone unfamiliar with this system

---

## Part 7 — Worked Example Summary

The tactical AI investigation (`investigations/tactical-ai/`) is the reference implementation of this methodology. When in doubt, consult it.

Key decisions made in that investigation that should be replicated:

- **Started from a debug settings class** (`TacticalStateSettings`) and followed outward to the AI brain (`Agent`). This is a reliable strategy: debug/inspector classes expose the runtime data model and the names of the systems they control.
- **Extracted all classes before starting Ghidra work.** The extraction report gave field offsets that made Ghidra output immediately readable.
- **Batched Ghidra requests by logical group.** All scoring functions together, then all agent lifecycle functions together. This reduces context-switching.
- **Resolved `DAT_` symbols by cross-referencing static field access patterns.** When `*(DAT_18394c3d0 + 0xb8)` appeared in multiple functions, the pattern was identified once (DebugVisualization class static) and applied everywhere.
- **Named the sign inversion explicitly.** `SafetyScore` being stored negative was a non-obvious convention that would have caused confusion downstream. It was identified from `PostProcessTileScores` and called out in both REPORT.md and RECONSTRUCTIONS.md.
- **Did not pursue Criterion subclasses.** The interface was documented (four vtable slots, confirmed purposes), and the concrete implementations were left as open questions. This was the right scope boundary — the scoring model was fully understood without them.
