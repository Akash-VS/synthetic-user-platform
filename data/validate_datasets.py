

import csv, itertools, os, re, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PERSONAS = os.path.join(HERE, "persona_profiles.csv")
SOURCES = os.path.join(HERE, "research_sources.csv")

REQUIRED_PERSONA = [
    "persona_id", "persona_label", "role", "experience_level", "relevant_skills",
    "product_familiarity", "goals", "motivations", "preferences", "working_style",
    "behavioral_traits", "confidence_level", "learning_preferences", "usability_needs",
    "assumptions_and_limitations", "creation_timestamp", "update_timestamp",
    "persona_status", "evidence_type"]
REQUIRED_SOURCE = [
    "source_id", "source_title", "source_url", "source_type", "access_date",
    "research_topic", "key_finding_or_summary", "relevance_to_milestone",
    "limitations", "evidence_type"]
EXPERIENCE = {"beginner", "intermediate", "advanced", "expert"}
CONFIDENCE = {"low", "medium", "high"}
STATUS = {"draft", "active", "archived"}

errors, warnings = [], []

def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)

def ts(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")

pcols, personas = load(PERSONAS)
scols, sources = load(SOURCES)

# --- structure and completeness
for col in REQUIRED_PERSONA:
    if col not in pcols:
        errors.append(f"persona_profiles.csv missing column {col}")
for col in REQUIRED_SOURCE:
    if col not in scols:
        errors.append(f"research_sources.csv missing column {col}")

for row in personas:
    for col in REQUIRED_PERSONA:
        if not (row.get(col) or "").strip():
            errors.append(f"{row.get('persona_id')}: empty {col}")
for row in sources:
    for col in REQUIRED_SOURCE:
        if not (row.get(col) or "").strip():
            errors.append(f"{row.get('source_id')}: empty {col}")

# --- unique ids
for name, rows, key in (("persona", personas, "persona_id"), ("source", sources, "source_id")):
    ids = [r[key] for r in rows]
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate {name} ids")
for row in personas:
    if not re.fullmatch(r"P\d{3}", row["persona_id"]):
        errors.append(f"bad persona_id format {row['persona_id']}")

# --- enumerations, timestamps, flags
for row in personas:
    pid = row["persona_id"]
    if row["experience_level"] not in EXPERIENCE:
        errors.append(f"{pid}: bad experience_level")
    if row["confidence_level"] not in CONFIDENCE:
        errors.append(f"{pid}: bad confidence_level")
    if row["persona_status"] not in STATUS:
        errors.append(f"{pid}: bad persona_status")
    if row.get("is_synthetic") != "true":
        errors.append(f"{pid}: is_synthetic must be 'true'")
    try:
        if ts(row["update_timestamp"]) < ts(row["creation_timestamp"]):
            errors.append(f"{pid}: update_timestamp before creation_timestamp")
    except ValueError:
        errors.append(f"{pid}: unparseable timestamp")

# --- source links resolve
known = {r["source_id"] for r in sources}
for row in personas:
    for sid in row["source_ids"].split(";"):
        if sid.strip() not in known:
            errors.append(f"{row['persona_id']}: unknown source id {sid}")
used = {s.strip() for r in personas for s in r["source_ids"].split(";")}
for sid in sorted(known - used):
    warnings.append(f"{sid} is not referenced by any persona (fine if used only for methodology)")
for row in sources:
    if not row["source_url"].startswith("http"):
        errors.append(f"{row['source_id']}: url is not http(s)")

# --- internal consistency rules
for row in personas:
    pid = row["persona_id"]
    if row["experience_level"] == "beginner" and row["confidence_level"] == "high":
        errors.append(f"{pid}: beginner with high confidence")
    if row["experience_level"] == "expert" and row["confidence_level"] == "low":
        errors.append(f"{pid}: expert with low confidence")

# --- diversity: pairwise word overlap across the descriptive fields
def words(row):
    text = " ".join(row[c] for c in ("role", "relevant_skills", "goals", "preferences",
                                      "behavioral_traits", "usability_needs")).lower()
    return set(re.findall(r"[a-z]{4,}", text))

worst = (0.0, None, None)
for a, b in itertools.combinations(personas, 2):
    wa, wb = words(a), words(b)
    j = len(wa & wb) / len(wa | wb)
    if j > worst[0]:
        worst = (j, a["persona_id"], b["persona_id"])
    if j > 0.30:
        warnings.append(f"{a['persona_id']} and {b['persona_id']} overlap strongly (Jaccard {j:.2f})")

# --- report
print(f"personas: {len(personas)}   sources: {len(sources)}")
for field in ("experience_level", "confidence_level", "persona_status"):
    counts = {}
    for r in personas:
        counts[r[field]] = counts.get(r[field], 0) + 1
    print(f"{field}: {counts}")
print(f"most similar pair: {worst[1]} / {worst[2]}  Jaccard={worst[0]:.2f}")
for w in warnings:
    print("WARN ", w)
for e in errors:
    print("ERROR", e)
print("RESULT:", "FAIL" if errors else "PASS (structural checks only)")
sys.exit(1 if errors else 0)
