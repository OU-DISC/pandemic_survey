"""Rename visualizations: tag prefix to visual:"""
import re
import codecs
from pathlib import Path

BIB = Path("bib/references.bib")


def extract_field(entry, field):
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


def strip_keywords(entry):
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


def set_keywords(entry, tags):
    entry = strip_keywords(entry).rstrip()
    if not tags:
        return entry + ("\n" if not entry.endswith("\n") else "")
    kw = ", ".join(tags)
    if entry.endswith("}"):
        body = entry[:-1].rstrip()
        if not body.endswith(","):
            body += ","
        return body + f"\n\tkeywords = {{{kw}}},\n}}\n\n"
    return entry + "\n"


def main():
    text = codecs.open(BIB, "r", "utf-8-sig").read()
    parts = re.split(r"(?=@\w+\s*\{)", text)
    preamble, entries = parts[0], parts[1:]
    changed = renamed = 0
    new = []
    for e in entries:
        if not e.strip():
            continue
        kw = extract_field(e, "keywords")
        if not kw:
            new.append(e if e.endswith("\n") else e + "\n")
            continue
        tags = [t.strip() for t in kw.split(",") if t.strip()]
        updated = []
        did = False
        for t in tags:
            if t.startswith("visualizations:"):
                updated.append("visual:" + t[len("visualizations:") :])
                renamed += 1
                did = True
            else:
                updated.append(t)
        if did:
            changed += 1
            new.append(set_keywords(e, updated))
        else:
            new.append(e if e.endswith("\n") else e + "\n")

    codecs.open(BIB, "w", "utf-8-sig").write(preamble + "".join(new))
    print("entries", changed, "tags", renamed)

    for p in [
        Path("src/data/authorized_tags.js"),
        Path("src/data/tag_categories.js"),
        Path("apply_classifications.py"),
        Path("apply_combined_classifications.py"),
    ]:
        t = p.read_text(encoding="utf-8")
        t = t.replace("visualizations:", "visual:")
        t = t.replace('"visualizations"', '"visual"')
        p.write_text(t, encoding="utf-8")
        print("updated", p.name)


if __name__ == "__main__":
    main()
