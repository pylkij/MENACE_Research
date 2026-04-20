import re
import sys
from pathlib import Path

DUMP_PATH = Path("dump.cs")  # Change this to your dump.cs path if needed

if len(sys.argv) > 1:
    DUMP_PATH = Path(sys.argv[1])

if not DUMP_PATH.exists():
    print(f"Error: Could not find dump file at {DUMP_PATH}")
    sys.exit(1)

print(f"Reading dump from {DUMP_PATH}...")
text = DUMP_PATH.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()

# -------------------------------------------------------------------------
# 1. Find all enums with negative values
# -------------------------------------------------------------------------
print("\n" + "="*60)
print("ENUMS CONTAINING NEGATIVE VALUES")
print("="*60)

enum_pattern = re.compile(r'^\s*public enum (\w+)')
const_pattern = re.compile(r'^\s*public const \w+ (\w+) = (-\d+);')

current_enum = None
current_namespace = None
namespace_pattern = re.compile(r'^// Namespace: (.+)')
negative_enums = {}

for i, line in enumerate(lines):
    ns_match = namespace_pattern.match(line)
    if ns_match:
        current_namespace = ns_match.group(1)

    enum_match = enum_pattern.match(line)
    if enum_match:
        current_enum = enum_match.group(1)
        current_ns_for_enum = current_namespace

    if current_enum:
        neg_match = const_pattern.match(line)
        if neg_match:
            field_name = neg_match.group(1)
            value = int(neg_match.group(2))
            key = (current_ns_for_enum, current_enum)
            if key not in negative_enums:
                negative_enums[key] = []
            negative_enums[key].append((field_name, value))

if negative_enums:
    for (ns, enum_name), fields in negative_enums.items():
        print(f"\nNamespace: {ns}")
        print(f"Enum: {enum_name}")
        for field, val in fields:
            print(f"  {field} = {val}")
else:
    print("No enums with negative values found.")

# -------------------------------------------------------------------------
# 2. Find classes/structs with a field named "PropertyType"
# -------------------------------------------------------------------------
print("\n" + "="*60)
print("CLASSES/STRUCTS CONTAINING 'PropertyType' FIELD")
print("="*60)

class_pattern = re.compile(r'^\s*public (class|struct) (\w+)')
field_pattern = re.compile(r'PropertyType')

current_class = None
current_class_ns = None
found_classes = {}

for i, line in enumerate(lines):
    ns_match = namespace_pattern.match(line)
    if ns_match:
        current_namespace = ns_match.group(1)

    class_match = class_pattern.match(line)
    if class_match:
        current_class = class_match.group(2)
        current_class_ns = current_namespace

    if current_class and field_pattern.search(line):
        key = (current_class_ns, current_class)
        if key not in found_classes:
            found_classes[key] = []
        found_classes[key].append((i + 1, line.strip()))

if found_classes:
    for (ns, class_name), hits in found_classes.items():
        print(f"\nNamespace: {ns}")
        print(f"Class/Struct: {class_name}")
        for lineno, content in hits:
            print(f"  Line {lineno}: {content}")
else:
    print("No classes with 'PropertyType' field found.")

# -------------------------------------------------------------------------
# 3. Find specific values -2 and -15 as enum constants anywhere
# -------------------------------------------------------------------------
print("\n" + "="*60)
print("ALL ENUM CONSTANTS WITH VALUE -2 OR -15")
print("="*60)

specific_pattern = re.compile(r'^\s*public const \w+ (\w+) = (-2|-15);')
current_enum = None
current_enum_ns = None

for i, line in enumerate(lines):
    ns_match = namespace_pattern.match(line)
    if ns_match:
        current_namespace = ns_match.group(1)

    enum_match = enum_pattern.match(line)
    if enum_match:
        current_enum = enum_match.group(1)
        current_enum_ns = current_namespace

    if current_enum:
        spec_match = specific_pattern.match(line)
        if spec_match:
            print(f"  Namespace: {current_enum_ns} | Enum: {current_enum} | {spec_match.group(1)} = {spec_match.group(2)}")

print("\nDone.")
