# Research-AI.md — AI Agent Research Guide

You are reverse engineering internal systems of a Unity IL2CPP game called Menace. Your inputs are:

- A `dump.cs` file produced by Il2CppDumper (~32 MB, ~885,000 lines)
- Ghidra decompilation output (raw C pseudocode) provided by the human operator
- Class dumps from the extraction tool
- Previously completed investigation reports in this repository

Your outputs are:
- `REPORT.md` — complete findings: class layouts, field offsets, method addresses, formulas, design inferences, open questions
- `RECONSTRUCTIONS.md` — every Ghidra-decompiled function with its raw output followed by a fully annotated C reconstruction

The standard is: **someone with no prior context on this system should be able to read the report and understand exactly what the code does, without opening Ghidra.**

When a stage boundary is reached, request Handoff-AI.md from the operator to execute the stage boundary sequence.

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

## Part 3 — Communication Protocol with the Operator

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
