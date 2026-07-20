"""Export Flourish-ready treemap CSVs for all classification dimensions."""
import re
import codecs
import csv
import collections
from pathlib import Path

bib = codecs.open("bib/references.bib", "r", "utf-8-sig").read()
parts = re.split(r"(?=@\w+\s*\{)", bib)[1:]


def extract(entry, field):
    m = re.search(rf"{field}\s*=\s*\{{", entry, re.I)
    if not m:
        return ""
    start = m.end()
    depth = 1
    i = start
    while i < len(entry) and depth:
        if entry[i] == "{":
            depth += 1
        elif entry[i] == "}":
            depth -= 1
        i += 1
    return entry[start : i - 1]


GROUPS = {
    "Search themes": [
        "pandemic",
        "healthcare",
        "epidemiological_modeling",
        "emergency_response",
        "visualization",
    ],
    "Data type": None,
    "Data size": None,
    "Users": None,
    "Visual representations": None,
    "Interaction": None,
    "Advanced algorithms": None,
    "Engagement": None,
    "Tools": None,
    "Visualization level": None,
    "Task": None,
    "Other flags": ["pandemic_data", "domain_specific"],
}

PREFIX = {
    "Data type": "data:",
    "Data size": "size:",
    "Users": "user:",
    "Visual representations": "visual:",
    "Interaction": "interaction:",
    "Advanced algorithms": "advanced_algorithms:",
    "Engagement": "engagement:",
    "Tools": "tool:",
    "Visualization level": "level:",
    "Task": "task:",
}

def pretty(tag):
    if ":" in tag:
        return tag.split(":", 1)[1].replace("_", " ")
    return tag.replace("_", " ")


def slug(name):
    return name.lower().replace(" ", "_").replace("-", "_")


counts = collections.Counter()  # (category, leaf) -> n
group_totals = collections.Counter()
n_papers = 0

for e in parts:
    if not e.strip():
        continue
    tags = set(t.strip() for t in extract(e, "keywords").split(",") if t.strip())
    if not tags:
        continue
    n_papers += 1
    seen_groups = set()
    for group, exact in GROUPS.items():
        if exact is not None:
            matched = [t for t in exact if t in tags]
        else:
            pref = PREFIX[group]
            matched = [t for t in tags if t.startswith(pref)]
        for t in matched:
            leaf = pretty(t)
            counts[(group, leaf)] += 1
            seen_groups.add(group)
    for g in seen_groups:
        group_totals[g] += 1

out = Path("bib/cooccurrence/flourish")
out.mkdir(exist_ok=True)

# Nested overview: Category | Code | Number of Papers
nested = out / "treemap_all_classifications.csv"
with nested.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Category", "Code", "Number of Papers"])
    for (g, leaf), n in sorted(counts.items(), key=lambda x: (x[0][0], -x[1], x[0][1])):
        w.writerow([g, leaf, n])

# Per-category focused treemaps
for group in GROUPS:
    rows = [(leaf, n) for (g, leaf), n in counts.items() if g == group]
    if not rows:
        continue
    path = out / f"treemap_{slug(group)}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Code", "Number of Papers"])
        for leaf, n in sorted(rows, key=lambda x: -x[1]):
            w.writerow([leaf, n])

# Category-level summary (good for a high-level treemap)
summary = out / "treemap_categories.csv"
with summary.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Category", "Number of Papers", "Number of Codes"])
    for g, n in sorted(group_totals.items(), key=lambda x: -x[1]):
        leaves = sum(1 for (gg, _) in counts if gg == g)
        w.writerow([g, n, leaves])

print("papers", n_papers)
print("Wrote", nested.name, "with", len(counts), "rows")
print("Category sizes (papers with any code in group):")
for g, n in sorted(group_totals.items(), key=lambda x: -x[1]):
    leaves = sum(1 for (gg, _) in counts if gg == g)
    print(f"  {g}: {n} papers, {leaves} codes")

