"""Apply classification-combined-1-2.csv tags onto references.bib (merge with existing)."""
import csv
import re
import codecs
import shutil
import unicodedata
from pathlib import Path
from collections import Counter

BIB = Path("bib/references.bib")
CSV = Path("bib/classification- combined- 1-2.csv")
BACKUP = Path("bib/references.bib.before_combined.bak")

LEVEL_COL = (
    "Visualization Levels (Disseminative visualization, Observational visualization, "
    "Analytical visualization, Model-developmental visualization)"
)


def norm_doi(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    return s.replace("doi:", "").strip().rstrip(".")


def norm_title(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[{}\\]", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_multi(val: str):
    if not val:
        return []
    return [p.strip() for p in re.split(r"[;|\n]+", val) if p.strip()]


def extract_field(entry: str, field: str) -> str:
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


def get_existing_keywords(entry: str):
    val = extract_field(entry, "keywords")
    if not val:
        return []
    return [t.strip() for t in val.split(",") if t.strip()]


def strip_keywords(entry: str) -> str:
    out = []
    i = 0
    while True:
        idx = entry.lower().find("keywords", i)
        if idx < 0:
            out.append(entry[i:])
            break
        m = re.match(r"keywords\s*=\s*\{", entry[idx:], re.I)
        if not m:
            out.append(entry[i : idx + 8])
            i = idx + 8
            continue
        chunk_start = idx
        while chunk_start > 0 and entry[chunk_start - 1] in "\t ":
            chunk_start -= 1
        if chunk_start > 0 and entry[chunk_start - 1] == "\n":
            chunk_start -= 1
        out.append(entry[i:chunk_start])
        j = idx + m.end()
        depth = 1
        while j < len(entry) and depth:
            if entry[j] == "{":
                depth += 1
            elif entry[j] == "}":
                depth -= 1
            j += 1
        if j < len(entry) and entry[j] == ",":
            j += 1
        if j < len(entry) and entry[j] == "\n":
            j += 1
        i = j
    return "".join(out)


def set_keywords(entry: str, tags: list) -> str:
    entry = strip_keywords(entry).rstrip()
    kw = ", ".join(tags)
    if entry.endswith("}"):
        body = entry[:-1].rstrip()
        if not body.endswith(","):
            body += ","
        return body + f"\n\tkeywords = {{{kw}}},\n}}\n\n"
    return entry + "\n"


SEARCH_MAP = {
    "pandemic + visualization": ["pandemic", "visualization"],
    "pandemic and visualization": ["pandemic", "visualization"],
    "pandemic": ["pandemic"],
    "healthcare + visualization": ["healthcare", "visualization"],
    "healthcare and visualization": ["healthcare", "visualization"],
    "healthcare": ["healthcare"],
    "healthcare, emergency response": ["healthcare", "emergency_response"],
    "epidemiological modeling + visualization": [
        "epidemiological_modeling",
        "visualization",
    ],
    "epidemiological modeling": ["epidemiological_modeling"],
    "epidemiology": ["epidemiological_modeling"],
    "emergency responses + visualization": [
        "emergency_response",
        "visualization",
    ],
    "emergency response": ["emergency_response"],
    "emergency responses": ["emergency_response"],
}

LEVEL_MAP = {
    "disseminative visualization": "level:disseminative",
    "observational visualization": "level:observational",
    "analytical visualization": "level:analytical",
    "model-developmental visualization": "level:model_developmental",
}

TASK_MAP = {
    "visualize": "task:visualize",
    "analyze": "task:analyze",
    "model": "task:model",
    "understand": "task:understand",
    "others": "task:other",
}

CHART_MAP = {
    "line chart": "visual:line",
    "time series line chart": "visual:line",
    "line": "visual:line",
    "bar chart": "visual:bar",
    "stacked bar chart": "visual:bar",
    "scatter plot": "visual:scatter",
    "scatter plots": "visual:scatter",
    "dashboard": "visual:dashboard",
    "heatmap": "visual:heatmap",
    "heat map": "visual:heatmap",
    "3d regression heat map": "visual:heatmap",
    "area chart": "visual:area",
    "pi chart": "visual:pie",
    "pie chart": "visual:pie",
    "map": "visual:map",
    "color-coded map": "visual:map",
    "choropleth map": "visual:map",
    "density visualization map": "visual:map",
    "network visualization map": "visual:network",
    "network visualization": "visual:network",
    "network map": "visual:network",
    "tree map": "visual:treemap",
    "treemap": "visual:treemap",
    "histogram": "visual:histogram",
    "timeline": "visual:timeline",
    "table": "visual:table",
    "word clouds": "visual:wordcloud",
    "word cloud": "visual:wordcloud",
    "clusters": "visual:cluster",
    "cluster visualization": "visual:cluster",
}


def infer_users(text: str):
    tags = []
    t = (text or "").lower()
    if "[public]" in t or re.search(r"\bpublic\b", t):
        if "public health" not in t:
            tags.append("user:public")
    if "policymaker" in t:
        tags.append("user:policymakers")
    if "public health" in t:
        tags.append("user:public_health")
    if "epidemiolog" in t:
        tags.append("user:epidemiologists")
    if "researcher" in t:
        tags.append("user:researchers")
    if "healthcare" in t or "health professional" in t:
        tags.append("user:healthcare_experts")
    if "domain subtype" in t or "domain expert" in t:
        tags.append("user:domain_experts")
    if "data scientist" in t or "analyst" in t:
        tags.append("user:data_scientists")
    if "modeler" in t or "modeling scientist" in t:
        tags.append("user:epidemiologists")
    return tags


def infer_data(text: str):
    tags = []
    t = (text or "").lower()
    if "time" in t and "series" in t:
        tags.append("data:timeseries")
    if "geo" in t or "spatial" in t or "map" in t:
        tags.append("data:geospatial")
    if "spatio" in t:
        tags.append("data:spatiotemporal")
    if "tabular" in t or "table" in t:
        tags.append("data:tabular")
    if "text" in t or "twitter" in t or "document" in t or "corpus" in t:
        tags.append("data:textual")
    if "network" in t or "graph" in t:
        tags.append("data:network")
    if "epidemiolog" in t or "pandemic" in t or "covid" in t:
        tags.append("pandemic_data")
    if "image" in t or "imagery" in t:
        tags.append("data:imagery")
    if "video" in t:
        tags.append("data:video")
    return tags


def tags_from_row(row: dict) -> list:
    tags = []

    search = (row.get("Keyword Search On") or "").strip().lower()
    tags.extend(SEARCH_MAP.get(search, []))
    if not any(t in ("pandemic", "healthcare", "epidemiological_modeling", "emergency_response", "visualization") for t in tags):
        # default keep visualization if search unknown
        if search and search not in ("?",):
            tags.append("visualization")

    # visualization levels (may be comma-separated)
    raw_level = row.get(LEVEL_COL) or ""
    for part in re.split(r"[,;/]+", raw_level):
        key = part.strip().lower()
        key = key.lstrip("b") if key.startswith("bservational") else key  # typo fix
        if key.startswith("servational"):
            key = "observational visualization"
        tag = LEVEL_MAP.get(key)
        if tag:
            tags.append(tag)
        else:
            for lk, lv in LEVEL_MAP.items():
                if lk in key:
                    tags.append(lv)

    for part in split_multi(row.get("Tasks Labels") or ""):
        tag = TASK_MAP.get(part.lower().strip())
        if tag:
            tags.append(tag)

    # users from both columns
    users_blob = " ".join(
        [
            row.get("Users") or "",
            row.get("Users lables") or "",
        ]
    )
    tags.extend(infer_users(users_blob))

    tags.extend(infer_data(row.get("Data") or ""))

    for part in split_multi(row.get("Visual Representations") or ""):
        key = part.lower().strip()
        tag = CHART_MAP.get(key)
        if tag:
            tags.append(tag)
        elif "map" in key:
            tags.append("visual:map")
        elif "network" in key:
            tags.append("visual:network")
        elif "heat" in key:
            tags.append("visual:heatmap")
        elif "line" in key:
            tags.append("visual:line")
        elif "bar" in key:
            tags.append("visual:bar")

    seen = set()
    out = []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def merge_tags(existing, new):
    seen = set()
    out = []
    for t in list(existing) + list(new):
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def main():
    shutil.copyfile(BIB, BACKUP)

    with CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    by_doi = {}
    by_title = {}
    for row in rows:
        doi = norm_doi(row.get("DOI Link") or "")
        title = norm_title(row.get("Paper Title") or "")
        if doi:
            by_doi[doi] = row
        if title:
            by_title[title] = row

    text = codecs.open(BIB, "r", "utf-8-sig").read()
    parts = re.split(r"(?=@\w+\s*\{)", text)
    preamble, entries = parts[0], parts[1:]

    matched = 0
    matched_doi = 0
    matched_title = 0
    used_csv = set()
    tag_freq = Counter()
    new_entries = []

    for e in entries:
        if not e.strip():
            continue
        doi = norm_doi(extract_field(e, "doi"))
        if not doi:
            url = extract_field(e, "url")
            if "doi.org" in url.lower():
                doi = norm_doi(url)
        title = norm_title(extract_field(e, "title"))

        row = None
        how = None
        if doi and doi in by_doi:
            row = by_doi[doi]
            how = "doi"
            matched_doi += 1
        elif title and title in by_title:
            row = by_title[title]
            how = "title"
            matched_title += 1

        if row:
            matched += 1
            for i, r in enumerate(rows):
                if r is row:
                    used_csv.add(i)
                    break
            new_tags = tags_from_row(row)
            tags = merge_tags(get_existing_keywords(e), new_tags)
            for t in new_tags:
                tag_freq[t] += 1
            new_entries.append(set_keywords(e, tags))
        else:
            new_entries.append(e if e.endswith("\n") else e + "\n")

    codecs.open(BIB, "w", "utf-8-sig").write(preamble + "".join(new_entries))

    unmatched = [i for i in range(len(rows)) if i not in used_csv]
    print(f"CSV papers: {len(rows)}")
    print(f"Bib entries: {len(new_entries)}")
    print(f"Matched: {matched} (doi={matched_doi}, title={matched_title})")
    print(f"CSV unmatched: {len(unmatched)}")
    if unmatched:
        print("Sample unmatched CSV:")
        for i in unmatched[:8]:
            r = rows[i]
            print(f"  {(r.get('Paper Title') or '')[:75]}")
            print(f"    DOI: {r.get('DOI Link')}")
    print("\nTop new tags applied:")
    for t, n in tag_freq.most_common(35):
        print(f"  {n:3d}  {t}")


if __name__ == "__main__":
    main()
