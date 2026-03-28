"""
extract_rvas.py
---------------
Extracts RVAs, field offsets, and method metadata from a standard
Il2CppDumper dump.cs file.

Format this parser targets:
    // Namespace: Some.Namespace
    public class MyClass : Base // TypeDefIndex: 123
    {
        // Fields
        public bool SomeField; // 0x20

        // Methods
        // RVA: 0xABCD Offset: 0x1234 VA: 0x18000ABCD
        public void SomeMethod() { }

        // Enums
        public const MyEnum Member = 0;
    }

Usage — single class:
    python extract_rvas.py dump.cs --class TacticalStateSettings --namespace Menace.States

Usage — multiple classes:
    python extract_rvas.py dump.cs --class-list targets.txt --out ./output

targets.txt format (namespace optional, omit to auto-detect):
    TacticalStateSettings   Menace.States
    TileScore
    DebugVisualization
    DebugVisualizationFilter
    TacticalState           Menace.States

Output:
    <ClassName>_rvas.json / .csv   per-class
    combined_rvas.json / .csv      all classes
    extraction_report.txt          human-readable summary + warnings
"""

import re
import json
import csv
import argparse
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class MethodEntry:
    name: str
    return_type: str
    parameters: str
    rva: Optional[str] = None
    offset: Optional[str] = None
    va: Optional[str] = None
    slot: Optional[str] = None
    attributes: list = field(default_factory=list)
    raw_signature: str = ""

@dataclass
class FieldEntry:
    name: str
    type_name: str
    offset: Optional[str] = None      # from inline comment  // 0x20
    attributes: list = field(default_factory=list)

@dataclass
class ClassEntry:
    class_name: str
    namespace: str
    base_class: str
    type_def_index: Optional[str] = None
    kind: str = "class"               # class | struct | enum
    methods: list = field(default_factory=list)
    fields: list = field(default_factory=list)
    enum_values: list = field(default_factory=list)  # [(name, int_value)]


# ---------------------------------------------------------------------------
# Compiled patterns  (tuned for standard Il2CppDumper dump.cs)
# ---------------------------------------------------------------------------

# // Namespace: Menace.Tactical.AI
RE_NS = re.compile(r'^// Namespace:\s*([\w\.]*)\s*$')

# public class Foo : Bar // TypeDefIndex: 317
# public enum Foo // TypeDefIndex: 42
# public struct Foo : IBar, IBaz // TypeDefIndex: 99
RE_CLASS_DECL = re.compile(
    r'^(public|private|internal|protected|sealed|abstract|static)'
    r'(?:\s+(?:sealed|abstract|static|partial))*\s+'
    r'(class|struct|enum)\s+(\w+)'
    r'(?:\s*:\s*([\w\.<>, ]+?))?'
    r'\s*(?://\s*TypeDefIndex:\s*(\d+))?'
    r'\s*$'
)

# // RVA: 0x756180 Offset: 0x754F80 VA: 0x180756180
# optional Slot: N at the end
RE_RVA = re.compile(
    r'//\s*RVA:\s*(0x[\dA-Fa-f]+|-1)\s+'
    r'Offset:\s*(0x[\dA-Fa-f]+|-1)\s+'
    r'VA:\s*(0x[\dA-Fa-f]+|-1)'
    r'(?:\s+Slot:\s*(\d+))?'
)

# Method declaration line (ends with { } or ;  — stubs are all { })
# Captures: modifiers, return_type, name, params
RE_METHOD = re.compile(
    r'^(?P<mods>(?:(?:public|private|protected|internal|static|virtual|override'
    r'|abstract|extern|unsafe|new|sealed|async)\s+)*)'
    r'(?P<ret>[\w\.<>\[\], \*\?]+?)\s+'
    r'(?P<name>[\w\.]+)\s*'
    r'\((?P<params>[^)]*)\)\s*'
    r'(?:\{.*\}|;)\s*$'
)

# Field declaration:  public bool ShowFogOfWar; // 0x20
# The inline offset comment is optional (some fields lack it)
RE_FIELD = re.compile(
    r'^(?P<mods>(?:(?:public|private|protected|internal|static|readonly'
    r'|const|volatile|new)\s+)*)'
    r'(?P<type>[\w\.<>\[\], \*\?]+?)\s+'
    r'(?P<name>\w+)\s*;'
    r'(?:\s*//\s*(?P<off>0x[\dA-Fa-f]+))?'
)

# Enum member:  public const DebugVisualization None = 0;
RE_ENUM_MEMBER = re.compile(
    r'^public const \w+\s+(\w+)\s*=\s*(-?\d+)\s*;'
)

# Attribute line:  [Space(20)]  [Header("Debug")]  [CompilerGenerated]  etc.
RE_ATTR = re.compile(r'^\[.+\]$')

# Inline offset on a field comment  (used as fallback)
RE_INLINE_OFF = re.compile(r'//\s*(0x[\dA-Fa-f]+)\s*$')

KEYWORD_BLACKLIST = frozenset({
    "class", "struct", "enum", "interface", "return", "if", "else",
    "new", "base", "this", "true", "false", "null", "default",
    "get", "set", "value", "var",
    # NOTE: "void" intentionally omitted — it is a valid method return type
})


# ---------------------------------------------------------------------------
# Core extractor
# ---------------------------------------------------------------------------

def extract_class(lines: list, class_name: str, namespace: str = "") -> Optional[ClassEntry]:
    """
    Scan lines for the target class and parse its block.
    Returns a ClassEntry or None if not found.
    """
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i].strip()

        # ── Step 1: match a class/struct/enum declaration ──────────────────
        m = RE_CLASS_DECL.match(raw)
        if not m or m.group(3) != class_name:
            i += 1
            continue

        # ── Step 2: find namespace comment above the class declaration ─────
        # Scan upward past attribute lines, blank lines, and other comments
        # (e.g. [DisallowMultipleComponent] may sit between the namespace
        # comment and the class keyword).  Stop at the first non-attribute,
        # non-blank line that isn't itself a namespace comment.
        found_ns = ""
        look = i - 1
        while look >= 0:
            prev = lines[look].strip()
            ns_match = RE_NS.match(prev)
            if ns_match:
                found_ns = ns_match.group(1)
                break
            # Keep scanning through attributes, blank lines, and plain comments
            if prev == "" or prev.startswith("[") or (prev.startswith("//") and "Namespace" not in prev):
                look -= 1
                continue
            # Hit something else (another class, a field, etc.) — stop
            break

        if namespace and found_ns != namespace:
            i += 1
            continue

        kind       = m.group(2)          # class | struct | enum
        found_base = (m.group(4) or "").strip()
        tdi        = m.group(5)

        entry = ClassEntry(
            class_name     = class_name,
            namespace      = found_ns,
            base_class     = found_base,
            kind           = kind,
            type_def_index = tdi,
        )

        # ── Step 3: find opening brace ─────────────────────────────────────
        # It is usually on the same line or the next
        block_start = i
        while block_start < n and '{' not in lines[block_start]:
            block_start += 1
        if block_start >= n:
            i += 1
            continue

        # ── Step 4: walk to matching closing brace ─────────────────────────
        depth = 0
        j     = block_start
        while j < n:
            for ch in lines[j]:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
            if depth == 0:
                break
            j += 1

        block_lines = lines[block_start : j + 1]

        # ── Step 5: parse block ────────────────────────────────────────────
        if kind == "enum":
            _parse_enum(block_lines, entry)
        else:
            _parse_class_body(block_lines, entry)

        return entry

    return None


def _parse_enum(block_lines: list, entry: ClassEntry):
    for line in block_lines:
        raw = line.strip()
        m = RE_ENUM_MEMBER.match(raw)
        if m:
            entry.enum_values.append((m.group(1), int(m.group(2))))


def _parse_class_body(block_lines: list, entry: ClassEntry):
    pending_rva:   Optional[dict] = None   # RVA comment seen, waiting for method
    pending_attrs: list           = []     # [Attr] lines seen, waiting for member
    seen_methods:  set            = set()
    seen_fields:   set            = set()

    for line in block_lines:
        raw    = line.strip()

        # Blank line: flush pending_attrs (orphaned attribute), but keep
        # pending_rva — a blank line between // RVA: and the declaration
        # should not discard the RVA we already captured.
        if not raw:
            pending_attrs = []
            continue

        # Non-RVA comment (section headers like "// Fields", "// Methods",
        # or any other plain comment): skip without touching state.
        if raw.startswith("//") and not RE_RVA.search(raw):
            continue

        # ── RVA comment ────────────────────────────────────────────────────
        rva_m = RE_RVA.search(raw)
        if rva_m:
            pending_rva = {
                "rva":    rva_m.group(1),   # may be "-1" (unresolved)
                "offset": rva_m.group(2),
                "va":     rva_m.group(3),
                "slot":   rva_m.group(4),
            }
            continue

        # ── Attribute line ─────────────────────────────────────────────────
        if RE_ATTR.match(raw):
            pending_attrs.append(raw)
            continue

        # ── Enum member (inside a non-enum class — rare but possible) ──────
        em = RE_ENUM_MEMBER.match(raw)
        if em:
            entry.enum_values.append((em.group(1), int(em.group(2))))
            pending_rva   = None
            pending_attrs = []
            continue

        # ── Method declaration ─────────────────────────────────────────────
        mm = RE_METHOD.match(raw)
        if mm:
            ret    = mm.group("ret").strip()
            name   = mm.group("name").strip()
            params = mm.group("params").strip()

            if name not in KEYWORD_BLACKLIST:
                key = f"{name}|{params}"
                if key not in seen_methods:
                    seen_methods.add(key)
                    rva    = pending_rva["rva"]    if pending_rva else "NO_RVA"
                    offset = pending_rva["offset"] if pending_rva else "NO_RVA"
                    va     = pending_rva["va"]     if pending_rva else "NO_RVA"
                    slot   = pending_rva["slot"]   if pending_rva else None
                    entry.methods.append(MethodEntry(
                        name          = name,
                        return_type   = ret,
                        parameters    = params,
                        rva           = rva,
                        offset        = offset,
                        va            = va,
                        slot          = slot,
                        attributes    = list(pending_attrs),
                        raw_signature = raw,
                    ))
            pending_rva   = None
            pending_attrs = []
            continue

        # ── Field declaration ──────────────────────────────────────────────
        fm = RE_FIELD.match(raw)
        if fm:
            type_name  = fm.group("type").strip()
            field_name = fm.group("name").strip()
            offset     = fm.group("off")

            if field_name not in KEYWORD_BLACKLIST and field_name not in seen_fields:
                seen_fields.add(field_name)
                entry.fields.append(FieldEntry(
                    name       = field_name,
                    type_name  = type_name,
                    offset     = offset,
                    attributes = list(pending_attrs),
                ))
            pending_rva   = None
            pending_attrs = []
            continue

        # ── Anything else resets attribute accumulator ─────────────────────
        # (but not pending_rva — the RVA comment is always immediately
        #  before its method, so we keep it across attribute lines)
        if not RE_ATTR.match(raw):
            pending_attrs = []


# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------

def run_extraction(
    dump_path: Path,
    targets: list,          # [(class_name, namespace), ...]
    out_dir: Path,
) -> tuple:                 # (entries, warnings)

    print(f"[*] Reading {dump_path} ({dump_path.stat().st_size / 1_048_576:.1f} MB)…")
    text  = dump_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    print(f"[*] {len(lines):,} lines loaded.")

    entries:  list = []
    warnings: list = []

    for class_name, namespace in targets:
        ns_hint = f" ({namespace})" if namespace else " (auto-detect ns)"
        print(f"[*] Extracting '{class_name}'{ns_hint}…")

        entry = extract_class(lines, class_name, namespace)
        if entry is None:
            msg = (f"'{class_name}' not found"
                   + (f" in namespace '{namespace}'" if namespace else "")
                   + " — check spelling")
            print(f"  [!] {msg}")
            warnings.append(msg)
            continue

        print(f"  [+] {entry.kind}  {entry.namespace}.{entry.class_name}"
              f"  methods={len(entry.methods)}"
              f"  fields={len(entry.fields)}"
              f"  enums={len(entry.enum_values)}"
              f"  TypeDefIndex={entry.type_def_index}")
        entries.append(entry)

    return entries, warnings


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _to_dict(e: ClassEntry) -> dict:
    d = {
        "class":        e.class_name,
        "namespace":    e.namespace,
        "base":         e.base_class,
        "kind":         e.kind,
        "typeDefIndex": e.type_def_index,
        "methods":      [asdict(m) for m in e.methods],
        "fields":       [asdict(f) for f in e.fields],
    }
    if e.enum_values:
        d["enumValues"] = [{"name": n, "value": v} for n, v in e.enum_values]
    return d


def write_per_class_json(e: ClassEntry, out_dir: Path) -> Path:
    p = out_dir / f"{e.class_name}_rvas.json"
    p.write_text(json.dumps(_to_dict(e), indent=2), encoding="utf-8")
    return p


def write_per_class_csv(e: ClassEntry, out_dir: Path) -> Path:
    p = out_dir / f"{e.class_name}_rvas.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["class", e.class_name, "namespace", e.namespace,
                    "base", e.base_class, "kind", e.kind,
                    "typeDefIndex", e.type_def_index])
        w.writerow([])

        if e.kind == "enum":
            w.writerow(["## ENUM VALUES"])
            w.writerow(["name", "value"])
            for name, val in e.enum_values:
                w.writerow([name, val])
        else:
            w.writerow(["## METHODS"])
            w.writerow(["name", "return_type", "parameters",
                        "rva", "offset", "va", "slot"])
            for m in e.methods:
                w.writerow([m.name, m.return_type, m.parameters,
                            m.rva, m.offset, m.va, m.slot])
            w.writerow([])
            w.writerow(["## FIELDS"])
            w.writerow(["name", "type_name", "field_offset", "attributes"])
            for f in e.fields:
                w.writerow([f.name, f.type_name, f.offset,
                            "; ".join(f.attributes)])
    return p


def write_combined_json(entries: list, out_dir: Path) -> Path:
    p = out_dir / "combined_rvas.json"
    p.write_text(json.dumps([_to_dict(e) for e in entries], indent=2),
                 encoding="utf-8")
    return p


def write_combined_csv(entries: list, out_dir: Path) -> Path:
    p = out_dir / "combined_rvas.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for e in entries:
            w.writerow(["### CLASS", e.class_name, e.namespace,
                        e.base_class, e.kind, e.type_def_index])
            if e.kind == "enum":
                w.writerow(["enum_member", "value"])
                for name, val in e.enum_values:
                    w.writerow([name, val])
            else:
                w.writerow(["method", "return_type", "signature",
                            "rva", "offset", "va", "slot"])
                for m in e.methods:
                    w.writerow(["method", m.return_type,
                                f"{m.name}({m.parameters})",
                                m.rva, m.offset, m.va, m.slot])
                w.writerow(["field", "type", "name",
                            "field_offset", "attributes"])
                for f in e.fields:
                    w.writerow(["field", f.type_name, f.name,
                                f.offset, "; ".join(f.attributes)])
            w.writerow([])
    return p


def write_report(entries: list, warnings: list, out_dir: Path) -> Path:
    p = out_dir / "extraction_report.txt"
    out = ["Il2CppDumper Extraction Report", "=" * 64, ""]

    for e in entries:
        out.append("─" * 64)
        hdr = f"  {e.kind.upper()}  {e.namespace}.{e.class_name}"
        if e.base_class:
            hdr += f" : {e.base_class}"
        out.append(hdr)
        out.append(f"  TypeDefIndex={e.type_def_index}")
        out.append("")

        if e.kind == "enum":
            out.append(f"  Enum members ({len(e.enum_values)}):")
            for name, val in e.enum_values:
                out.append(f"    {val:>6}  {name}")
        else:
            out.append(f"  Methods ({len(e.methods)}):")
            for m in e.methods:
                rva = m.rva or "???"
                off = m.offset or "???"
                flag = ""
                if rva in ("-1", "NO_RVA"):
                    flag = "  [UNRESOLVED]"
                out.append(
                    f"    {m.return_type:<16} {m.name:<34}"
                    f" RVA={rva:<14} Offset={off}{flag}"
                )
            out.append("")
            out.append(f"  Fields ({len(e.fields)}):")
            for f in e.fields:
                off  = f"0x{int(f.offset, 16):03X}" if f.offset else "???"
                tags = [a for a in f.attributes if "NonSerialized" in a
                        or "Header" in a or "Space" in a]
                attr = "  " + "  ".join(tags) if tags else ""
                out.append(f"    [{off}]  {f.type_name:<36} {f.name}{attr}")
        out.append("")

    if warnings:
        out += ["", "WARNINGS", "─" * 40]
        out += [f"  ! {w}" for w in warnings]

    p.write_text("\n".join(out), encoding="utf-8")
    return p


def print_final_summary(entries: list, warnings: list):
    print()
    for e in entries:
        hdr = f"  {e.kind.upper()}  {e.namespace}.{e.class_name}"
        if e.base_class:
            hdr += f" : {e.base_class}"
        print("=" * 64)
        print(hdr)
        print(f"  TypeDefIndex={e.type_def_index}")
        if e.kind == "enum":
            print(f"  Members: " + ", ".join(f"{n}={v}" for n, v in e.enum_values))
        else:
            print(f"  {len(e.methods)} methods, {len(e.fields)} fields")
    if warnings:
        print()
        for w in warnings:
            print(f"  [WARN] {w}")


# ---------------------------------------------------------------------------
# Target list loader
# ---------------------------------------------------------------------------

def load_target_list(path: Path) -> list:
    targets = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        targets.append((parts[0], parts[1] if len(parts) > 1 else ""))
    return targets


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Extract RVAs from a standard Il2CppDumper dump.cs"
    )
    ap.add_argument("dump", type=Path, help="Path to dump.cs")

    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--class",      dest="class_name",
                     help="Single class name")
    grp.add_argument("--class-list", dest="class_list", type=Path,
                     help="Text file: one ClassName [Namespace] per line")

    ap.add_argument("--namespace", default="",
                    help="Namespace for --class (blank = auto-detect)")
    ap.add_argument("--out", type=Path, default=Path("."),
                    help="Output directory (default: current dir)")
    args = ap.parse_args()

    if not args.dump.exists():
        sys.exit(f"[!] Not found: {args.dump}")

    if args.class_list:
        if not args.class_list.exists():
            sys.exit(f"[!] Not found: {args.class_list}")
        targets = load_target_list(args.class_list)
    elif args.class_name:
        targets = [(args.class_name, args.namespace)]
    else:
        targets = [("TacticalStateSettings", "Menace.States")]

    args.out.mkdir(parents=True, exist_ok=True)

    entries, warnings = run_extraction(args.dump, targets, args.out)

    if not entries:
        sys.exit("[!] No classes extracted.")

    for e in entries:
        write_per_class_json(e, args.out)
        write_per_class_csv(e,  args.out)

    cj = write_combined_json(entries, args.out)
    cc = write_combined_csv(entries,  args.out)
    rp = write_report(entries, warnings, args.out)

    print_final_summary(entries, warnings)
    print(f"\n[+] Combined JSON  → {cj}")
    print(f"[+] Combined CSV   → {cc}")
    print(f"[+] Report         → {rp}")
    print(f"\n[✓] Done. {len(entries)}/{len(targets)} classes extracted.")


if __name__ == "__main__":
    main()
