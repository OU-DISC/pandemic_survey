"""Add SurVis keywords to BibTeX entries from thematic search terms."""
import re
import codecs
import shutil
from pathlib import Path

BIB = Path("bib/references.bib")
BACKUP = Path("bib/references.bib.bak")
SOURCE = BACKUP if BACKUP.exists() else BIB

TAG_RULES = [
    ("pandemic", [
        r"\bpandemics?\b",
        r"\bcovid(?:[-\s]?19)?\b",
        r"\bcorona\s*virus(?:es)?\b",
        r"\bcoronavirus(?:es)?\b",
        r"\bsars[-\s]?cov[-\s]?2\b",
        r"\bepidemics?\b",
    ]),
    ("visualization", [
        r"\bvisuali[sz]ations?\b",
        r"\bvisuali[sz]e[ds]?\b",
        r"\bvisuali[sz]ing\b",
        r"\bvisual analytics\b",
        r"\bvisual analysis\b",
        r"\binformation visualization\b",
        r"\bdata visualization\b",
        r"\bdashboards?\b",
        r"\bvisualiz\w*\b",
    ]),
    ("healthcare", [
        r"\bhealth[-\s]?care\b",
        r"\bhealth care\b",
        r"\bmedical\b",
        r"\bclinical\b",
        r"\bpublic health\b",
        r"\bhospitals?\b",
    ]),
    ("epidemiological_modeling", [
        r"\bepidemiolog\w*\b",
        r"\bepidemic model\w*\b",
        r"\bcompartmental model\w*\b",
        r"\bsir model\b",
        r"\bseir\b",
        r"\bdisease model\w*\b",
        r"\btransmission model\w*\b",
    ]),
    ("emergency_response", [
        r"\bemergency response\b",
        r"\bemergency management\b",
        r"\bcrisis response\b",
        r"\bdisaster response\b",
        r"\boutbreak response\b",
        r"\bpublic health emergency\b",
        r"\bemergency\b",
    ]),
]


def strip_braces(s: str) -> str:
    return re.sub(r"[{}]", "", s)


def extract_field(entry: str, field: str) -> str:
    """Extract a BibTeX braced field, allowing one level of nested braces."""
    m = re.search(
        rf"{field}\s*=\s*\{{",
        entry,
        re.I,
    )
    if not m:
        return ""
    start = m.end()
    depth = 1
    i = start
    while i < len(entry) and depth:
        ch = entry[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return entry[start : i - 1]


def searchable_text(entry: str) -> str:
    parts = []
    for field in ("title", "abstract", "booktitle", "journal"):
        val = extract_field(entry, field)
        if val:
            parts.append(val)
    return strip_braces(" ".join(parts))


def infer_tags(entry: str) -> list:
    blob = searchable_text(entry)
    tags = []
    for tag, patterns in TAG_RULES:
        if any(re.search(p, blob, re.I) for p in patterns):
            tags.append(tag)
    return tags


def strip_existing_keywords(entry: str) -> str:
    # Remove keywords fields carefully without touching other fields
    out = []
    i = 0
    lower = entry.lower()
    while True:
        idx = lower.find("keywords", i)
        if idx < 0:
            out.append(entry[i:])
            break
        # ensure it's a field assignment
        m = re.match(r"keywords\s*=\s*\{", entry[idx:], re.I)
        if not m:
            out.append(entry[i : idx + 8])
            i = idx + 8
            continue
        # drop from previous newline if only whitespace
        chunk_start = idx
        if chunk_start > 0 and entry[chunk_start - 1] in "\n\t ":
            while chunk_start > 0 and entry[chunk_start - 1] in "\t ":
                chunk_start -= 1
            if chunk_start > 0 and entry[chunk_start - 1] == "\n":
                chunk_start -= 1
        out.append(entry[i:chunk_start])
        # skip braced value
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
        lower = entry.lower()  # unchanged; indices still on original
    return "".join(out)


def insert_keywords(entry: str, tags: list) -> str:
    if not tags:
        return entry if entry.endswith("\n") else entry + "\n"
    kw = ", ".join(tags)
    entry = entry.rstrip()
    if entry.endswith("}"):
        body = entry[:-1].rstrip()
        if not body.endswith(","):
            body += ","
        return body + f"\n\tkeywords = {{{kw}}},\n}}\n\n"
    return entry + "\n"


def main():
    text = codecs.open(SOURCE, "r", "utf-8-sig").read()
    if SOURCE == BIB and not BACKUP.exists():
        shutil.copyfile(BIB, BACKUP)

    parts = re.split(r"(?=@\w+\s*\{)", text)
    preamble = parts[0]
    entries = parts[1:]

    stats = {t: 0 for t, _ in TAG_RULES}
    stats["untagged"] = 0
    new_entries = []
    untagged_titles = []

    for e in entries:
        if not e.strip():
            continue
        e2 = strip_existing_keywords(e)
        tags = infer_tags(e2)
        for t in tags:
            stats[t] += 1
        if not tags:
            stats["untagged"] += 1
            title = strip_braces(extract_field(e2, "title"))[:70]
            eid = re.match(r"@\w+\s*\{\s*([^,\s]+)", e2)
            untagged_titles.append((eid.group(1) if eid else "?", title))
        new_entries.append(insert_keywords(e2, tags))

    codecs.open(BIB, "w", "utf-8-sig").write(preamble + "".join(new_entries))
    print("Source:", SOURCE)
    print("Wrote", BIB)
    print("Stats:", stats)
    print("Total entries:", len(new_entries))
    print("With at least one tag:", len(new_entries) - stats["untagged"])
    if untagged_titles:
        print("\nSample untagged:")
        for u in untagged_titles[:12]:
            print(" -", u[0], ":", u[1])


if __name__ == "__main__":
    main()
