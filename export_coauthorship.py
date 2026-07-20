"""Export Flourish-ready co-authorship network for prolific author groups."""
import re
import codecs
import csv
import collections
import unicodedata
from pathlib import Path

bib = codecs.open("bib/references.bib", "r", "utf-8-sig").read()
parts = re.split(r"(?=@\w+\s*\{)", bib)[1:]

MAX_AUTHORS_PER_PAPER = 12  # drop consortium / mega-author lists
MIN_PAPERS = 3  # prolific threshold
MIN_JOINT = 1  # keep edges with at least this many joint papers

SKIP = re.compile(r"^(others|et al\.?|others\.)$", re.I)


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


def clean_text(s):
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"Sa.?ed", "Sa'ed", s, flags=re.IGNORECASE)
    s = s.replace("\ufffd", "'")
    return s.strip()


def name_key_parts(last, first):
    def norm(x):
        x = clean_text(x).lower()
        x = re.sub(r"[^a-z0-9\s]", "", x)
        x = re.sub(r"\s+", " ", x).strip()
        return x

    return f"{norm(last)}|{norm(first)}"


def normalize_author(raw):
    p = clean_text(re.sub(r"[\{\}\\]", "", raw))
    p = re.sub(r"\s+", " ", p)
    if not p or SKIP.match(p):
        return None
    if "," in p:
        last, first = [x.strip() for x in p.split(",", 1)]
        display = f"{first} {last}".strip() if first else last
        key = name_key_parts(last, first)
    else:
        toks = p.split()
        if len(toks) >= 2:
            last = toks[-1]
            first = " ".join(toks[:-1])
            display = p
            key = name_key_parts(last, first)
        else:
            display = p
            key = clean_text(p).lower()
    return key, display


author_papers = collections.defaultdict(set)
author_display = {}
paper_authors = []  # list of (pid, [keys])

skipped_mega = 0
n_papers = 0

for e in parts:
    if not e.strip():
        continue
    m = re.match(r"@\w+\s*\{([^,]+)", e)
    pid = m.group(1).strip() if m else "?"
    raw = extract(e, "author")
    authors = []
    seen = set()
    for part in re.split(r"\s+and\s+", raw, flags=re.I):
        r = normalize_author(part)
        if not r:
            continue
        key, display = r
        if key in seen:
            continue
        seen.add(key)
        authors.append((key, display))
    if not authors:
        continue
    n_papers += 1
    if len(authors) > MAX_AUTHORS_PER_PAPER:
        skipped_mega += 1
        continue
    keys = []
    for key, display in authors:
        author_papers[key].add(pid)
        if key not in author_display:
            author_display[key] = display
        elif "Sa'ed" in display and "Sa'ed" not in author_display[key]:
            author_display[key] = display
        elif len(display) > len(author_display[key]) and "\ufffd" not in display:
            author_display[key] = display
        keys.append(key)
    paper_authors.append((pid, keys))

# Prolific authors
prolific = {k for k, papers in author_papers.items() if len(papers) >= MIN_PAPERS}

# Edges among prolific authors
edges = collections.Counter()
for pid, keys in paper_authors:
    prol = sorted(set(k for k in keys if k in prolific))
    for i in range(len(prol)):
        for j in range(i + 1, len(prol)):
            edges[(prol[i], prol[j])] += 1

edges = {e: w for e, w in edges.items() if w >= MIN_JOINT}

linked = set()
for a, b in edges:
    linked.add(a)
    linked.add(b)

parent = {k: k for k in linked}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


for a, b in edges:
    union(a, b)

components = collections.defaultdict(list)
for k in linked:
    components[find(k)].append(k)

comp_rank = sorted(
    components.items(),
    key=lambda kv: -sum(len(author_papers[a]) for a in kv[1]),
)

group_of = {}
group_label = {}
for root, members in comp_rank:
    tops = sorted(members, key=lambda a: (-len(author_papers[a]), author_display[a]))[:2]
    if len(tops) == 1:
        label = f"{author_display[tops[0]]} group"
    else:
        label = f"{author_display[tops[0]]} / {author_display[tops[1]]}"
    for m in members:
        group_of[m] = label
    group_label[root] = label

out = Path("bib/cooccurrence/flourish")
out.mkdir(exist_ok=True)

nodes_path = out / "coauthorship_nodes.csv"
links_path = out / "coauthorship_links.csv"


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


degree = collections.Counter()
for a, b in edges:
    degree[a] += 1
    degree[b] += 1

node_rows = []
for key in sorted(linked, key=lambda k: (-len(author_papers[k]), author_display[k])):
    node_rows.append(
        [
            author_display[key],
            len(author_papers[key]),
            group_of[key],
            degree[key],
        ]
    )
write_csv(nodes_path, ["Author", "Papers", "Group", "Degree"], node_rows)

link_rows = []
for (a, b), weight in sorted(edges.items(), key=lambda x: -x[1]):
    link_rows.append([author_display[a], author_display[b], weight])
write_csv(links_path, ["Source", "Target", "Joint papers"], link_rows)

combo = out / "coauthorship_network.csv"
combo_rows = []
for (a, b), weight in sorted(edges.items(), key=lambda x: -x[1]):
    g = group_of[a] if len(author_papers[a]) >= len(author_papers[b]) else group_of[b]
    combo_rows.append(
        [
            author_display[a],
            author_display[b],
            weight,
            len(author_papers[a]),
            len(author_papers[b]),
            g,
        ]
    )
write_csv(
    combo,
    ["Source", "Target", "Joint papers", "Source papers", "Target papers", "Group"],
    combo_rows,
)

print(f"papers scanned: {n_papers} (skipped {skipped_mega} with >{MAX_AUTHORS_PER_PAPER} authors)")
print(f"prolific authors (>={MIN_PAPERS} papers): {len(prolific)}")
print(f"network nodes (linked): {len(linked)}")
print(f"network links: {len(edges)}")
print(f"groups: {len(comp_rank)}")
print()
for root, members in comp_rank:
    members_sorted = sorted(members, key=lambda a: -len(author_papers[a]))
    print(f"  {group_label[root]} ({len(members)} authors)")
    for a in members_sorted:
        print(f"      {len(author_papers[a]):2d}  {author_display[a]}")
print()
print("Wrote:", nodes_path.name, links_path.name, combo.name)
print("Top links:")
for (a, b), w in sorted(edges.items(), key=lambda x: -x[1])[:10]:
    print(f"  {w}  {author_display[a]} -- {author_display[b]}")
