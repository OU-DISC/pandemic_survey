"""Apply SurveyII classifications CSV keywords onto references.bib."""
import csv
import re
import codecs
import shutil
import unicodedata
from pathlib import Path
from collections import Counter

BIB = Path("bib/references.bib")
CSV = Path("bib/SurveyII_Classifications - SurveyII_Classifications.csv")
BACKUP = Path("bib/references.bib.before_classifications.bak")

# --- normalization helpers ---

def norm_doi(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    s = s.replace("doi:", "").strip()
    return s.rstrip(".")


def norm_title(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[{}\\]", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def split_multi(val: str):
    if not val:
        return []
    parts = re.split(r"[;|\n]+", val)
    return [p.strip() for p in parts if p.strip()]


# --- field extract / rewrite ---

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


# --- classification -> tags ---

DATA_TYPE_MAP = {
    "tabular data": "data:tabular",
    "time-series data": "data:timeseries",
    "timeseries data": "data:timeseries",
    "geospatial data": "data:geospatial",
    "spatiotemporal data": "data:spatiotemporal",
    "textual data": "data:textual",
    "text data": "data:textual",
    "document data": "data:document",
    "document data (text corpus)": "data:document",
    "documment data": "data:document",
    "event data": "data:event",
    "tree, set, graph/network": "data:network",
    "2d scalar field (imagery data)": "data:imagery",
    "3d+ scalar field (volumn vis)": "data:volume",
    "3d+ scalar field (volume vis)": "data:volume",
    "video data": "data:video",
}

USER_MAP = {
    "public": "user:public",
    "policymakers": "user:policymakers",
    "domain experts": "user:domain_experts",
    "public health experts": "user:public_health",
    "data scientists": "user:data_scientists",
    "epidemiologists": "user:epidemiologists",
    "healthcare experts": "user:healthcare_experts",
    "researchers": "user:researchers",
    "sociological experts": "user:sociological",
    "educators": "user:educators",
    "students": "user:students",
    "economists": "user:economists",
    "musicians": "user:musicians",
    "artists": "user:artists",
    "business analysts": "user:business_analysts",
    "cybersecurity analysts": "user:cybersecurity",
}

CHART_MAP = {
    "line chart": "visual:line",
    "bar chart": "visual:bar",
    "dashboard": "visual:dashboard",
    "scatter plot": "visual:scatter",
    "map": "visual:map",
    "geospatial map": "visual:map",
    "choropleth map": "visual:map",
    "bubble map": "visual:map",
    "heatmap": "visual:heatmap",
    "area chart": "visual:area",
    "table": "visual:table",
    "box plot": "visual:boxplot",
    "node-link graph": "visual:network",
    "pie chart": "visual:pie",
    "wordcloud": "visual:wordcloud",
    "bubble chart": "visual:bubble",
    "forest plot": "visual:forest",
    "image": "visual:image",
    "violin plot": "visual:violin",
    "histogram": "visual:histogram",
    "dot plot": "visual:dot",
    "tree map": "visual:treemap",
    "3d geospatial visualization": "visual:3d",
    "3d visualization": "visual:3d",
    "3d bar chart": "visual:3d",
    "animation": "visual:animation",
}

INTERACTION_MAP = {
    "basic": "interaction:basic",
    "medium": "interaction:medium",
    "advanced": "interaction:advanced",
    "static vis": "interaction:static",
    "immersive": "interaction:immersive",
    "n/a": None,
}

TOOL_MAP = {
    "toolkits": "tool:toolkits",
    "web app": "tool:web_app",
    "software": "tool:software",
    "mobile app": "tool:mobile_app",
    "immersive app": "tool:immersive_app",
    "n/a": None,
}

SEARCH_MAP = {
    "pandemic and visualization": ["pandemic", "visualization"],
    "pandemic & visualization": ["pandemic", "visualization"],
    "healthcare and visualization": ["healthcare", "visualization"],
    "healthcare & visualization": ["healthcare", "visualization"],
    "epidemiological modeling and visualization": [
        "epidemiological_modeling",
        "visualization",
    ],
    "emergency responses and visualization": [
        "emergency_response",
        "visualization",
    ],
}


def tags_from_row(row: dict) -> list:
    tags = []

    search = (row.get("Keyword Search On") or "").strip().lower()
    tags.extend(SEARCH_MAP.get(search, ["visualization"]))

    if (row.get("Pandemic Data Related") or "").strip() == "1":
        tags.append("pandemic_data")

    if (row.get("Domain") or "").strip() == "1":
        tags.append("domain_specific")

    for part in split_multi(row.get("Data- data type") or ""):
        key = part.lower().strip()
        tag = DATA_TYPE_MAP.get(key)
        if tag:
            tags.append(tag)
        else:
            # soft fallback
            if "time" in key and "series" in key:
                tags.append("data:timeseries")
            elif "geo" in key:
                tags.append("data:geospatial")
            elif "spatio" in key:
                tags.append("data:spatiotemporal")
            elif "tabular" in key:
                tags.append("data:tabular")
            elif "text" in key or "document" in key:
                tags.append("data:textual")

    for part in split_multi(row.get("User Group") or ""):
        tag = USER_MAP.get(part.lower().strip())
        if tag:
            tags.append(tag)

    for part in split_multi(row.get("Visual Representations (chart)") or ""):
        key = part.lower().strip()
        tag = CHART_MAP.get(key)
        if tag:
            tags.append(tag)
        elif "map" in key:
            tags.append("visual:map")
        elif "dashboard" in key:
            tags.append("visual:dashboard")

    inter = (row.get("Visual Analytics (Interaction Lv.)") or "").strip().lower()
    itag = INTERACTION_MAP.get(inter)
    if itag:
        tags.append(itag)

    for part in split_multi(row.get("Tools/platform") or ""):
        t = TOOL_MAP.get(part.lower().strip())
        if t:
            tags.append(t)

    if (row.get("Advanced Algorithm (0/1)") or "").strip() == "1":
        tags.append("advanced_algorithms:yes")
    elif (row.get("Advanced Algorithm (0/1)") or "").strip() == "0":
        tags.append("advanced_algorithms:no")
    if (row.get("Public Engagement (0/1)") or "").strip() == "1":
        tags.append("engagement:yes")
    elif (row.get("Public Engagement (0/1)") or "").strip() == "0":
        tags.append("engagement:no")

    size = (row.get("Data- data size") or "").strip()
    size_tag = {
        "0": "size:author_small",
        "1": "size:author_large",
        "2": "size:estimated_small",
        "3": "size:estimated_large",
    }.get(size)
    if size_tag:
        tags.append(size_tag)

    # stable unique order
    seen = set()
    out = []
    for t in tags:
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
    unmatched_csv = set(range(len(rows)))
    tag_freq = Counter()
    new_entries = []

    for e in entries:
        if not e.strip():
            continue
        doi = norm_doi(extract_field(e, "doi") or extract_field(e, "DOI Link"))
        # also try url field for doi.org links
        if not doi:
            url = extract_field(e, "url")
            if "doi.org" in url.lower():
                doi = norm_doi(url)
        title = norm_title(extract_field(e, "title"))

        row = None
        if doi and doi in by_doi:
            row = by_doi[doi]
            matched_doi += 1
        elif title and title in by_title:
            row = by_title[title]
            matched_title += 1

        if row:
            matched += 1
            tags = tags_from_row(row)
            for t in tags:
                tag_freq[t] += 1
            # mark csv row as used
            for i, r in enumerate(rows):
                if r is row:
                    unmatched_csv.discard(i)
                    break
            new_entries.append(set_keywords(e, tags))
        else:
            new_entries.append(e if e.endswith("\n") else e + "\n")

    codecs.open(BIB, "w", "utf-8-sig").write(preamble + "".join(new_entries))

    print(f"CSV papers: {len(rows)}")
    print(f"Bib entries: {len(new_entries)}")
    print(f"Matched: {matched} (doi={matched_doi}, title={matched_title})")
    print(f"CSV unmatched: {len(unmatched_csv)}")
    if unmatched_csv:
        print("Sample unmatched CSV:")
        for i in list(unmatched_csv)[:10]:
            r = rows[i]
            print(f"  {r.get('Paper ID')}: {r.get('Paper Title')[:70]}")
            print(f"    DOI: {r.get('DOI Link')}")
    print("\nTop tags:")
    for t, n in tag_freq.most_common(40):
        print(f"  {n:3d}  {t}")


if __name__ == "__main__":
    main()
