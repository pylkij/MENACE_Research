"""
enumerate_namespace.py
----------------------
Enumerates all classes (class / struct / enum) within a given namespace
in a standard Il2CppDumper dump.cs file.

Usage:
    python enumerate_namespace.py dump.cs --namespace Menace.Tactical.AI.Behaviors.Criterions
    python enumerate_namespace.py dump.cs --namespace Menace.Tactical.AI.Behaviors.Criterions --verbose
    python enumerate_namespace.py dump.cs --namespace Menace.Tactical.AI.Behaviors.Criterions --out targets.txt

Output modes:
    default   — one class name per line (ready to pipe into extract_rvas.py --class-list)
    --verbose — full table: kind, name, base, TypeDefIndex, method count, field count
    --out     — write class-list file compatible with extract_rvas.py --class-list
"""

import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Patterns (matches Il2CppDumper dump.cs format)
# ---------------------------------------------------------------------------

RE_NS = re.compile(r'^// Namespace:\s*([\w\.]*)\s*$')

RE_CLASS_DECL = re.compile(
    r'^(?:public|private|internal|protected|sealed|abstract|static)'
    r'(?:\s+(?:sealed|abstract|static|partial))*\s+'
    r'(class|struct|enum)\s+(\w+)'
    r'(?:\s*:\s*([\w\.<>, ]+?))?'
    r'\s*(?://\s*TypeDefIndex:\s*(\d+))?'
    r'\s*$'
)

RE_RVA = re.compile(r'//\s*RVA:\s*(0x[\dA-Fa-f]+|-1)')
RE_FIELD = re.compile(
    r'^(?:public|private|protected|internal|static|readonly|const|volatile|new)'
    r'(?:\s+(?:public|private|protected|internal|static|readonly|const|volatile|new))*'
    r'\s+[\w\.<>\[\], \*\?]+?\s+\w+\s*;'
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ClassSummary:
    kind:          str            # class | struct | enum
    name:          str
    namespace:     str
    base:          str
    type_def_index: Optional[str]
    method_count:  int = 0
    field_count:   int = 0


# ---------------------------------------------------------------------------
# Core scan
# ---------------------------------------------------------------------------

def enumerate_namespace(dump_path: Path, target_ns: str) -> list[ClassSummary]:
    """
    Single-pass scan of dump.cs.
    Returns one ClassSummary per class/struct/enum whose namespace matches
    target_ns exactly.
    """
    lines = dump_path.read_text(encoding="utf-8", errors="replace").splitlines()
    n = len(lines)
    results: list[ClassSummary] = []

    i = 0
    while i < n:
        raw = lines[i].strip()

        # ── Match a class/struct/enum declaration ──────────────────────────
        m = RE_CLASS_DECL.match(raw)
        if not m:
            i += 1
            continue

        # ── Find namespace comment above ───────────────────────────────────
        found_ns = ""
        look = i - 1
        while look >= 0:
            prev = lines[look].strip()
            ns_m = RE_NS.match(prev)
            if ns_m:
                found_ns = ns_m.group(1)
                break
            if prev == "" or prev.startswith("[") or (
                prev.startswith("//") and "Namespace" not in prev
            ):
                look -= 1
                continue
            break   # hit something else — stop

        if found_ns != target_ns:
            i += 1
            continue

        kind  = m.group(1)
        name  = m.group(2)
        base  = (m.group(3) or "").strip()
        tdi   = m.group(4)

        summary = ClassSummary(
            kind=kind, name=name, namespace=found_ns,
            base=base, type_def_index=tdi
        )

        # ── Walk the class body to count methods and fields ────────────────
        block_start = i
        while block_start < n and '{' not in lines[block_start]:
            block_start += 1

        depth = 0
        j = block_start
        while j < n:
            for ch in lines[j]:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
            if depth == 0:
                break
            # Count RVA lines as method proxies (one RVA comment → one method)
            stripped = lines[j].strip()
            if RE_RVA.match(stripped):
                summary.method_count += 1
            elif RE_FIELD.match(stripped):
                summary.field_count += 1
            j += 1

        results.append(summary)
        i = j + 1  # skip past the closing brace

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_simple(results: list[ClassSummary]):
    """One class name per line — pipe-friendly."""
    for r in results:
        print(r.name)


def print_verbose(results: list[ClassSummary], namespace: str):
    if not results:
        print(f"[!] No classes found in namespace: {namespace}")
        return

    col_name = max(len(r.name) for r in results)
    col_base = max((len(r.base) for r in results), default=0)
    col_name = max(col_name, 4)
    col_base = max(col_base, 4)

    header = (
        f"{'Kind':<7}  {'Name':<{col_name}}  {'Base':<{col_base}}  "
        f"{'TDI':>6}  {'Methods':>7}  {'Fields':>6}"
    )
    print(f"\nNamespace: {namespace}")
    print(f"Classes found: {len(results)}\n")
    print(header)
    print("─" * len(header))
    for r in results:
        tdi = r.type_def_index or "?"
        print(
            f"{r.kind:<7}  {r.name:<{col_name}}  {r.base:<{col_base}}  "
            f"{tdi:>6}  {r.method_count:>7}  {r.field_count:>6}"
        )
    print()


def write_class_list(results: list[ClassSummary], out_path: Path, namespace: str):
    """
    Write a targets.txt compatible with extract_rvas.py --class-list.
    Format: ClassName    Namespace
    """
    lines = [f"# Namespace: {namespace}", f"# Classes: {len(results)}", ""]
    for r in results:
        lines.append(f"{r.name:<50} {r.namespace}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[+] Class list written → {out_path}")
    print(f"    Pass to extract_rvas.py with:  --class-list {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Enumerate all classes in a namespace from an Il2CppDumper dump.cs"
    )
    ap.add_argument("dump", type=Path, help="Path to dump.cs")
    ap.add_argument(
        "--namespace", "-n", required=True,
        help="Exact namespace to enumerate (e.g. Menace.Tactical.AI.Behaviors.Criterions)"
    )
    ap.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print full table (kind, base, TypeDefIndex, method/field counts)"
    )
    ap.add_argument(
        "--out", "-o", type=Path, default=None,
        help="Write a class-list file compatible with extract_rvas.py --class-list"
    )
    args = ap.parse_args()

    if not args.dump.exists():
        sys.exit(f"[!] File not found: {args.dump}")

    results = enumerate_namespace(args.dump, args.namespace)

    if args.verbose or args.out:
        print_verbose(results, args.namespace)
    else:
        if not results:
            print(f"[!] No classes found in namespace: {args.namespace}", file=sys.stderr)
            sys.exit(1)
        print_simple(results)

    if args.out:
        write_class_list(results, args.out, args.namespace)


if __name__ == "__main__":
    main()
