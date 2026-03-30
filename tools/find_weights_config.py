#!/usr/bin/env python3
"""
WeightsConfig Investigation Script
===================================
Goal: Identify the true IL2CPP class name for the investigation-internal
"WeightsConfig" object, accessed in Ghidra via:
    *(*(DAT_18394c3d0 + 0xb8) + 8)

Known characteristics from the report:
  - Float fields confirmed at: +0x54, +0x78, +0x7C, +0xBC, +0xC0, +0xCC, +0xD0,
    +0xE0, +0xE4, +0xE8, +0xEC, +0xF0, +0xF8, +0xFC, +0x100, +0x10C, +0x118,
    +0x128, +0x12C, +0x13C, +0x148, +0x14C, +0x150, +0x154, +0x15C, +0x168,
    +0x16C, +0x174, +0x17C, +0x180, +0x184, +0x188, +0x18C, +0x190, +0x1A4
  - Int fields at: +0xC4, +0xC8
  - Total field span: +0x54 to +0x1A4 (~340 bytes of data)
  - ~40 fields total
  - Likely namespace: Menace.Tactical.AI (or Menace.Tactical)
  - Primary anchor: four consecutive floats at +0xE4, +0xE8, +0xEC, +0xF0
  - Secondary anchor: float at +0xBC (tagValueScale)
  - Tertiary anchor: float at +0x13C (utilityThreshold)

Strategy:
  1. Find all classes with float/int fields at the anchor offsets
  2. Score each candidate by how many known offsets it matches
  3. Rank and report top candidates
  4. Also search by semantic field name patterns that Unity IL2CPP often preserves
"""

import sys
import re
from collections import defaultdict
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

DUMP_PATH = "dump.cs"          # path to Il2CppDumper dump.cs — edit if needed

# All confirmed/inferred field offsets from the report (decimal)
KNOWN_OFFSETS = {
    0x54,   # movementScoreWeight      float  confirmed
    0x78,   # [scoring weight]         float  inferred NQ-4
    0x7C,   # allyCoFireBonus          float  inferred
    0xBC,   # tagValueScale            float  confirmed  ← anchor
    0xC0,   # baseAttackWeightScale    float  confirmed
    0xC4,   # maxApproachRange         int    confirmed
    0xC8,   # allyInRangeMaxDist       int    confirmed
    0xCC,   # rangePenaltyScale        float  confirmed
    0xD0,   # allyProximityPenaltyScale float confirmed
    0xE0,   # friendlyFirePenaltyWeight float confirmed
    0xE4,   # killWeight               float  confirmed  ← primary anchor
    0xE8,   # killWeight2              float  confirmed  ← primary anchor
    0xEC,   # urgencyWeight            float  confirmed  ← primary anchor
    0xF0,   # buffWeight/allyCoFire    float  confirmed  ← primary anchor
    0xF8,   # proximityBonusCap        float  confirmed
    0xFC,   # minAoeScoreThreshold     float  confirmed
    0x100,  # allyCoFireBonusScale     float  confirmed
    0x10C,  # utilityFromTileMultiplier float confirmed
    0x118,  # suppressionTileMultiplier float confirmed
    0x128,  # finalMovementScoreScale   float confirmed
    0x12C,  # movementWeightScale       float confirmed
    0x13C,  # utilityThreshold          float confirmed  ← anchor
    0x148,  # movementScorePathWeight   float inferred NQ-4
    0x14C,  # pathCostPenaltyWeight     float inferred NQ-5
    0x150,  # minimumImprovementRatio   float confirmed
    0x154,  # deployMovementScoreThreshold float confirmed
    0x15C,  # secondaryPathPenalty      float confirmed
    0x168,  # shortRangePenalty         float confirmed
    0x16C,  # stanceSkillBonus          float confirmed
    0x174,  # buffGlobalScoringScale    float confirmed
    0x17C,  # healScoringWeight         float confirmed
    0x180,  # buffScoringWeight         float confirmed
    0x184,  # suppressScoringWeight     float confirmed
    0x188,  # setupAssistScoringWeight  float confirmed
    0x18C,  # aoeBuffScoringWeight      float confirmed
    0x190,  # aoeHealScoringWeight      float confirmed
    0x1A4,  # aoeAllyBonusThreshold     float confirmed
}

# The four consecutive anchor offsets — must ALL be present for a strong hit
PRIMARY_ANCHORS = {0xE4, 0xE8, 0xEC, 0xF0}

# Secondary anchors — high confidence individual fields
SECONDARY_ANCHORS = {0xBC, 0x13C, 0x128, 0x12C, 0x1A4}

# Namespaces to prioritise (exact match preferred, fallback to any)
PREFERRED_NAMESPACES = [
    "Menace.Tactical.AI",
    "Menace.Tactical",
    "Menace",
]

# ── Parser ───────────────────────────────────────────────────────────────────

# Matches: // 0x1A4  or  // Offset: 0x1A4  (Il2CppDumper style)
OFFSET_RE = re.compile(r"//\s*(?:Offset:\s*)?0x([0-9A-Fa-f]+)")

# Matches class / struct declarations (including nested generics)
CLASS_RE = re.compile(
    r"^\s*(?:public\s+|private\s+|internal\s+|protected\s+|sealed\s+|abstract\s+)*"
    r"(?:class|struct)\s+(\w[\w<>, ]*?)\s*(?::|{)"
)

# Matches namespace declarations
NS_RE = re.compile(r"^\s*namespace\s+([\w.]+)")

def parse_dump(path: str):
    """
    Single-pass parse of dump.cs.
    Returns a list of dicts:
      { name, namespace, typedef_index, offsets: set[int], raw_fields: list[str] }
    """
    classes = []
    current_ns = ""
    current_class = None
    brace_depth = 0
    class_brace_start = None
    in_class = False

    typedef_re = re.compile(r"//\s*TypeDefIndex\s*:\s*(\d+)")

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            stripped = line.strip()

            # Namespace tracking
            ns_m = NS_RE.match(line)
            if ns_m and "{" in line:
                current_ns = ns_m.group(1)
                continue

            # Class / struct start
            cls_m = CLASS_RE.match(line)
            if cls_m and not in_class:
                class_name = cls_m.group(1).strip()
                typedef_m = typedef_re.search(line)
                typedef_idx = int(typedef_m.group(1)) if typedef_m else None
                current_class = {
                    "name": class_name,
                    "namespace": current_ns,
                    "typedef_index": typedef_idx,
                    "offsets": set(),
                    "raw_fields": [],
                    "start_line": lineno,
                }
                in_class = True
                brace_depth = line.count("{") - line.count("}")
                class_brace_start = brace_depth
                continue

            if in_class:
                brace_depth += line.count("{") - line.count("}")

                # Collect offset annotations
                off_m = OFFSET_RE.search(line)
                if off_m:
                    offset_val = int(off_m.group(1), 16)
                    current_class["offsets"].add(offset_val)
                    current_class["raw_fields"].append(line.rstrip())

                # End of class
                if brace_depth <= 0:
                    classes.append(current_class)
                    current_class = None
                    in_class = False
                    brace_depth = 0

    return classes


def score_candidate(cls: dict) -> dict:
    """
    Score a class against all known WeightsConfig characteristics.
    Returns a score dict with breakdown.
    """
    offsets = cls["offsets"]

    # Primary anchor: all four consecutive floats must be present
    primary_hits = len(PRIMARY_ANCHORS & offsets)
    primary_all  = primary_hits == len(PRIMARY_ANCHORS)

    # Secondary anchors
    secondary_hits = len(SECONDARY_ANCHORS & offsets)

    # Total known offset matches
    total_hits = len(KNOWN_OFFSETS & offsets)

    # Coverage ratio
    coverage = total_hits / len(KNOWN_OFFSETS)

    # Namespace bonus
    ns_score = 0
    ns = cls.get("namespace", "")
    for i, preferred in enumerate(PREFERRED_NAMESPACES):
        if ns == preferred:
            ns_score = len(PREFERRED_NAMESPACES) - i
            break
        elif ns.startswith(preferred):
            ns_score = max(ns_score, len(PREFERRED_NAMESPACES) - i - 0.5)

    # Penalty: if class has very few total fields it is probably a partial/nested
    field_count = len(offsets)
    size_ok = field_count >= 20  # WeightsConfig has ~40 fields

    # Composite score
    composite = (
        primary_hits * 10
        + secondary_hits * 3
        + total_hits * 1
        + ns_score * 5
        + (5 if size_ok else 0)
    )

    return {
        "composite": composite,
        "primary_hits": primary_hits,
        "primary_all": primary_all,
        "secondary_hits": secondary_hits,
        "total_hits": total_hits,
        "coverage_pct": coverage * 100,
        "field_count": field_count,
        "ns_score": ns_score,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    dump_path = sys.argv[1] if len(sys.argv) > 1 else DUMP_PATH
    if not Path(dump_path).exists():
        print(f"[ERROR] dump.cs not found at '{dump_path}'")
        print("Usage: python find_weights_config.py [path/to/dump.cs]")
        sys.exit(1)

    print(f"[*] Parsing '{dump_path}' ...")
    classes = parse_dump(dump_path)
    print(f"[*] Parsed {len(classes):,} class/struct definitions.")
    print()

    # ── Phase 1: Primary anchor filter (must have all 4 at 0xE4..0xF0) ──────
    primary_candidates = [
        c for c in classes
        if PRIMARY_ANCHORS.issubset(c["offsets"])
    ]
    print(f"[Phase 1] Classes with ALL primary anchor offsets (0xE4,0xE8,0xEC,0xF0): "
          f"{len(primary_candidates)}")

    # ── Phase 2: Score and rank ───────────────────────────────────────────────
    scored = []
    for cls in primary_candidates:
        s = score_candidate(cls)
        scored.append((s["composite"], cls, s))

    scored.sort(key=lambda x: -x[0])

    if scored:
        print("\n" + "═" * 70)
        print("TOP CANDIDATES (sorted by composite score)")
        print("═" * 70)
        for rank, (composite, cls, s) in enumerate(scored[:10], 1):
            ns  = cls["namespace"] or "(no namespace)"
            print(f"\n[#{rank}] {ns}.{cls['name']}")
            if cls["typedef_index"] is not None:
                print(f"     TypeDefIndex : {cls['typedef_index']}")
            print(f"     Composite    : {composite}")
            print(f"     Primary hits : {s['primary_hits']}/4  ({'ALL PRESENT' if s['primary_all'] else 'partial'})")
            print(f"     Secondary    : {s['secondary_hits']}/{len(SECONDARY_ANCHORS)}")
            print(f"     Total matches: {s['total_hits']}/{len(KNOWN_OFFSETS)}  ({s['coverage_pct']:.1f}%)")
            print(f"     Total fields : {s['field_count']}")
    else:
        print("\n[!] No class matched ALL primary anchors.")
        print("    Falling back to partial primary match (≥2 of 4 anchors) ...\n")

        # Fallback: relax to ≥2 of 4 primary anchors
        fallback = []
        for cls in classes:
            hits = len(PRIMARY_ANCHORS & cls["offsets"])
            if hits >= 2:
                s = score_candidate(cls)
                fallback.append((s["composite"], cls, s))

        fallback.sort(key=lambda x: -x[0])
        print(f"[Fallback] Classes with ≥2 primary anchors: {len(fallback)}")
        for rank, (composite, cls, s) in enumerate(fallback[:10], 1):
            ns = cls["namespace"] or "(no namespace)"
            print(f"\n[#{rank}] {ns}.{cls['name']}")
            if cls["typedef_index"] is not None:
                print(f"     TypeDefIndex : {cls['typedef_index']}")
            print(f"     Primary hits : {s['primary_hits']}/4")
            print(f"     Total matches: {s['total_hits']}/{len(KNOWN_OFFSETS)}  ({s['coverage_pct']:.1f}%)")
            print(f"     Total fields : {s['field_count']}")

    # ── Phase 3: Full field dump for #1 candidate ─────────────────────────────
    if scored:
        _, best_cls, best_s = scored[0]
        print("\n" + "═" * 70)
        print(f"FIELD DUMP — {best_cls['namespace']}.{best_cls['name']}")
        print("  Matched known offsets are flagged with ✓")
        print("═" * 70)

        for field_line in best_cls["raw_fields"]:
            off_m = OFFSET_RE.search(field_line)
            if off_m:
                offset_val = int(off_m.group(1), 16)
                flag = "✓" if offset_val in KNOWN_OFFSETS else " "
                print(f"  [{flag}] {field_line.strip()}")
            else:
                print(f"       {field_line.strip()}")

    # ── Phase 4: Semantic keyword search as cross-check ───────────────────────
    print("\n" + "═" * 70)
    print("SEMANTIC SEARCH — classes with 'weight' or 'config' or 'threshold' in name")
    print("  (in preferred namespaces only)")
    print("═" * 70)
    keywords = re.compile(r"weight|config|threshold|scoring|behaviour|behavior", re.I)
    semantic_hits = [
        c for c in classes
        if keywords.search(c["name"])
        and any(c["namespace"].startswith(p) for p in PREFERRED_NAMESPACES)
    ]
    if semantic_hits:
        for cls in semantic_hits:
            s = score_candidate(cls)
            print(f"  {cls['namespace']}.{cls['name']}"
                  f"  (fields={s['field_count']}, matches={s['total_hits']}, "
                  f"TypeDefIndex={cls.get('typedef_index','?')})")
    else:
        print("  (no hits)")

    print("\n[Done]")


if __name__ == "__main__":
    main()
