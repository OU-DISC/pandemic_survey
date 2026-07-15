"""Match and rename unmatched PDFs to BibTeX ids; reindex."""
import re
import codecs
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from update_data import update

PDF_DIR = Path("src/data/papers_pdf")
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


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[{}\\]", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def compact(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def load_entries():
    text = codecs.open(BIB, "r", "utf-8-sig").read()
    parts = re.split(r"(?=@\w+\s*\{)", text)[1:]
    entries = []
    ids = set()
    by_title = {}
    by_doi = {}
    by_compact_id = {}
    for e in parts:
        if not e.strip():
            continue
        m = re.match(r"@\w+\s*\{\s*([^,\s]+)", e)
        if not m:
            continue
        eid = m.group(1)
        ids.add(eid)
        title = norm(extract_field(e, "title"))
        doi = extract_field(e, "doi").lower().strip()
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
        url = extract_field(e, "url")
        author = extract_field(e, "author")
        year = extract_field(e, "year").strip()
        first = ""
        if author:
            a0 = author.split(" and ")[0].strip()
            first = (
                a0.split(",")[0].strip().lower()
                if "," in a0
                else a0.split()[-1].strip().lower()
            )
        ent = {
            "id": eid,
            "title": title,
            "doi": doi,
            "url": url.lower(),
            "author": first,
            "year": year,
        }
        entries.append(ent)
        if title:
            by_title.setdefault(title, []).append(eid)
        if doi:
            by_doi[doi] = eid
            # also without punctuation
            by_doi[re.sub(r"[^a-z0-9.]", "", doi)] = eid
        by_compact_id.setdefault(compact(eid), []).append(eid)
        # arxiv from url
        am = re.search(r"arxiv\.org/abs/([\d.]+)", url.lower())
        if am:
            by_doi["arxiv:" + am.group(1)] = eid
            by_doi[am.group(1)] = eid
    return entries, ids, by_title, by_doi, by_compact_id


def filename_title(stem):
    s = stem
    # strip common publisher prefixes
    s = re.sub(r"^1-s2\.0-", "", s, flags=re.I)
    s = re.sub(r"-main$", "", s, flags=re.I)
    s = s.replace("_", " ").replace("-", " ")
    return norm(s)


def extract_doi_from_name(stem):
    # 10-1108_GKMC-01-2021-0006 -> 10.1108/GKMC-01-2021-0006
    m = re.match(r"(10)[-_](\d{4})[-_](.+)$", stem, re.I)
    if m:
        return f"10.{m.group(2)}/{m.group(3).replace('_', '-')}".lower()
    m = re.search(r"(10\.\d{4,}/[^\s]+)", stem.replace("_", "/"), re.I)
    if m:
        return m.group(1).lower().rstrip(".pdf")
    # bare arxiv
    m = re.match(r"^(\d{4}\.\d{4,5})(v\d+)?$", stem)
    if m:
        return m.group(1)
    return ""


def score_title(ft, ent):
    if not ft or not ent["title"]:
        return 0.0
    score = SequenceMatcher(None, ft, ent["title"]).ratio()
    if ent["title"] in ft or ft in ent["title"]:
        score = max(score, 0.9)
    if ent["author"] and ent["author"] in ft:
        score += 0.08
    if ent["year"] and ent["year"] in ft:
        score += 0.05
    return score


def target_path(bib_id):
    return PDF_DIR / f"{bib_id.replace(':', '_')}.pdf"


def is_matched(stem, ids):
    return stem in ids or any(i.replace(":", "_") == stem for i in ids)


def main():
    entries, ids, by_title, by_doi, by_compact_id = load_entries()
    pdfs = sorted(PDF_DIR.glob("*.pdf"))

    renamed = []
    deleted = []
    unmatched = []

    for p in pdfs:
        stem = p.stem
        if is_matched(stem, ids):
            continue

        bib_id = None
        how = None

        # DOI / arxiv from filename
        doi = extract_doi_from_name(stem)
        if doi:
            if doi in by_doi:
                bib_id, how = by_doi[doi], "doi"
            else:
                dcompact = re.sub(r"[^a-z0-9.]", "", doi)
                if dcompact in by_doi:
                    bib_id, how = by_doi[dcompact], "doi"

        # exact title from filename
        ft = filename_title(stem)
        if not bib_id and ft in by_title and len(by_title[ft]) == 1:
            bib_id, how = by_title[ft][0], "exact-title"

        # compact id match
        if not bib_id:
            c = compact(stem)
            if c in by_compact_id and len(by_compact_id[c]) == 1:
                bib_id, how = by_compact_id[c][0], "compact-id"

        # fuzzy title
        if not bib_id and len(ft) > 15:
            ranked = sorted(
                ((score_title(ft, ent), ent) for ent in entries),
                key=lambda x: x[0],
                reverse=True,
            )
            best_score, best = ranked[0]
            second = ranked[1][0] if len(ranked) > 1 else 0
            if best_score >= 0.88 and best_score - second >= 0.03:
                bib_id, how = best["id"], f"fuzzy-title:{best_score:.3f}"
            elif best_score >= 0.95:
                bib_id, how = best["id"], f"fuzzy-title:{best_score:.3f}"

        # fuzzy compact id for short citation-key-like names
        if not bib_id and len(stem) < 50:
            c = compact(stem)
            ranked = sorted(
                ((SequenceMatcher(None, c, compact(i)).ratio(), i) for i in ids),
                reverse=True,
            )
            best_score, best_id = ranked[0]
            second = ranked[1][0] if len(ranked) > 1 else 0
            if best_score >= 0.9 and best_score - second >= 0.04:
                bib_id, how = best_id, f"fuzzy-id:{best_score:.3f}"

        if not bib_id:
            unmatched.append(p.name)
            continue

        dst = target_path(bib_id)
        if dst.exists() and dst.resolve() != p.resolve():
            # duplicate of already-correct PDF
            msg = f"DUP [{how}] delete {p.name} (have {dst.name})"
            print(msg.encode("ascii", "replace").decode("ascii"))
            p.unlink()
            deleted.append(p.name)
            continue

        msg = f"[{how}] {p.name[:70]}\n    -> {dst.name}"
        print(msg.encode("ascii", "replace").decode("ascii"))
        p.rename(dst)
        renamed.append(dst.name)

    print(f"\nRenamed: {len(renamed)}  deleted dups: {len(deleted)}  unmatched: {len(unmatched)}")
    update()

    pdfs = list(PDF_DIR.glob("*.pdf"))
    matched = sum(1 for p in pdfs if is_matched(p.stem, ids))
    print(f"Total PDFs: {len(pdfs)}  matching: {matched}  non-matching: {len(pdfs)-matched}")
    if unmatched:
        print("\nStill unmatched (up to 60):")
        for n in unmatched[:60]:
            # avoid console encoding issues
            print(" ", n.encode("ascii", "replace").decode("ascii"))


if __name__ == "__main__":
    main()
