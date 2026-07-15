"""Download open-access PDFs for bib entries that have a DOI but no local PDF.

Uses Unpaywall only (legal OA versions). Paywalled papers are skipped.
"""
import re
import codecs
import time
import urllib.request
import urllib.error
import json
from pathlib import Path
from update_data import update

BIB = Path("bib/references.bib")
PDF_DIR = Path("src/data/papers_pdf")
UNPAYWALL_EMAIL = "bash0006@ou.edu"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


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


def norm_doi(s):
    s = (s or "").strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi:\s*", "", s, flags=re.I)
    return s.strip().rstrip(".")


def load_missing():
    text = codecs.open(BIB, "r", "utf-8-sig").read()
    parts = re.split(r"(?=@\w+\s*\{)", text)[1:]
    have = {p.stem for p in PDF_DIR.glob("*.pdf")}
    missing = []
    for e in parts:
        if not e.strip():
            continue
        m = re.match(r"@\w+\s*\{\s*([^,\s]+)", e)
        if not m:
            continue
        eid = m.group(1)
        safe = eid.replace(":", "_")
        if eid in have or safe in have:
            continue
        doi = norm_doi(extract_field(e, "doi"))
        url = extract_field(e, "url")
        if not doi and "doi.org/" in url.lower():
            doi = norm_doi(url)
        if doi:
            missing.append((eid, doi, url))
    return missing


def http_get_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_download(url, dest: Path):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,application/octet-stream,*/*",
            "Referer": "https://doi.org/",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    if data[:4] != b"%PDF":
        raise ValueError(f"not a PDF (size={len(data)})")
    dest.write_bytes(data)
    return len(data)


def unpaywall_pdf_urls(doi):
    api = (
        f"https://api.unpaywall.org/v2/{urllib.request.quote(doi)}"
        f"?email={UNPAYWALL_EMAIL}"
    )
    data = http_get_json(api)
    urls = []
    seen = set()

    def add(u):
        if u and u not in seen:
            seen.add(u)
            urls.append(u)

    locs = []
    if data.get("best_oa_location"):
        locs.append(data["best_oa_location"])
    locs.extend(data.get("oa_locations") or [])
    for loc in locs:
        add(loc.get("url_for_pdf"))
    for loc in locs:
        u = loc.get("url") or ""
        if ".pdf" in u.lower() or "pdf" in u.lower():
            add(u)
        m = re.search(r"ncbi\.nlm\.nih\.gov/pmc/articles/(PMC\d+)", u, re.I)
        if m:
            add(f"https://www.ncbi.nlm.nih.gov/pmc/articles/{m.group(1)}/pdf")
        m = re.search(r"europepmc\.org/articles/(PMC\d+)", u, re.I)
        if m:
            add(f"https://europepmc.org/articles/{m.group(1)}?pdf=render")
    return urls, bool(data.get("is_oa"))


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    missing = load_missing()
    print(f"Missing PDFs with DOI: {len(missing)}")

    downloaded, no_oa, failed = [], [], []

    for i, (eid, doi, url) in enumerate(missing, 1):
        dest = PDF_DIR / f"{eid.replace(':', '_')}.pdf"
        print(f"[{i}/{len(missing)}] {eid}  doi={doi}")
        try:
            candidates = []
            if url and url.lower().endswith(".pdf"):
                candidates.append(url.strip())
            oa_urls, is_oa = unpaywall_pdf_urls(doi)
            candidates.extend(oa_urls)
            if not candidates:
                print("  no OA PDF")
                no_oa.append((eid, doi))
                time.sleep(0.3)
                continue

            last_err = None
            ok = False
            for pdf_url in candidates:
                try:
                    size = http_download(pdf_url, dest)
                    print(f"  OK ({size} bytes)")
                    downloaded.append(eid)
                    ok = True
                    break
                except Exception as e:
                    last_err = e
                    continue
            if not ok:
                raise last_err or RuntimeError("all candidates failed")
        except Exception as e:
            msg = str(e).encode("ascii", "replace").decode("ascii")
            print(f"  FAIL {msg}")
            failed.append((eid, doi, msg))
            if dest.exists() and dest.stat().st_size < 2000:
                dest.unlink(missing_ok=True)
        time.sleep(0.35)

    print("\n=== SUMMARY ===")
    print(f"Downloaded: {len(downloaded)}")
    print(f"No OA version: {len(no_oa)}")
    print(f"Failed: {len(failed)}")
    if no_oa:
        print("\nNo open-access PDF found:")
        for eid, doi in no_oa:
            print(f"  {eid}  https://doi.org/{doi}")
    if failed:
        print("\nFailed (often publisher blocks bots):")
        for eid, doi, msg in failed:
            print(f"  {eid}: {msg}")

    update()

    try:
        import fitz

        IMG = Path("src/data/papers_img")
        created = 0
        for eid in downloaded:
            pdf = PDF_DIR / f"{eid.replace(':', '_')}.pdf"
            out = IMG / f"{eid.replace(':', '_')}.png"
            if not pdf.exists() or out.exists():
                continue
            doc = fitz.open(pdf)
            page = doc.load_page(0)
            zoom = 300 / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            pix.save(str(out))
            doc.close()
            created += 1
        update()
        print(f"Thumbnails created: {created}")
    except Exception as e:
        print("Thumbnail step skipped:", e)


if __name__ == "__main__":
    main()
