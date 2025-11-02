# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "bibtexparser",
#     "requests",
#     "tqdm",
# ]
# ///
# to run this script using uv, run: 
# uv run fetch_orcid.py 
# this will automatically create a virtual environment with the required dependencies if not already present.
import json
import requests
from tqdm import tqdm
from datetime import datetime, timedelta
from pathlib import Path
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
import re
from bibtexparser.bibdatabase import BibDatabase

ORCID_ID = "0009-0008-0363-6748"  # <--- enter your ORCID here
OUTFILE = "publications.bib"

CACHEFILE = Path(".cache/orcid_cache.json")
MAX_AGE_DAYS = 1

# --- Helpers: year extraction for sorting ---
def _extract_year(value):
    """Return a 4-digit year as int if present, else None.
    Accepts int, str (e.g., "2024", "{2024}", "2024-05").
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1000 <= value <= 9999 else None
    if isinstance(value, str):
        m = re.search(r"(1\d{3}|20\d{2})", value)
        return int(m.group(1)) if m else None
    return None

def _extract_year_from_bibtex_string(bibtex_str):
    """Try to extract year from a BibTeX entry string."""
    if not isinstance(bibtex_str, str):
        return None
    m = re.search(r"year\s*=\s*[{\"]?\s*(1\d{3}|20\d{2})", bibtex_str, re.IGNORECASE)
    return int(m.group(1)) if m else None

# --- Check cache ---
if CACHEFILE.exists():
    try:
        cache = json.loads(CACHEFILE.read_text())
        last_fetch = datetime.fromisoformat(cache.get("last_fetch"))
        if datetime.now() - last_fetch < timedelta(days=MAX_AGE_DAYS):
            print(f"🟢 ORCID cache is up to date (last fetched {last_fetch.date()}) – no fetch needed.")
            exit(0)
    except Exception as e:
        print("⚠️ Cache could not be read, fetching fresh:", e)
# --- End cache check ---

base_url = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
headers = {"Accept": "application/json"}

# Fetch all works (contains only metadata + put-codes)
works = requests.get(base_url, headers=headers).json().get("group", [])

bib_entries = []  # list of entry strings (for logging)
bib_entries_years = []  # list of tuples: (year:int|None, entry_string)

for group in tqdm(works, desc="Fetching ORCID citations"):
    work_summary = group["work-summary"][0]
    put_code = work_summary["put-code"]

    # Retrieve details for this work
    resp = requests.get(f"https://pub.orcid.org/v3.0/{ORCID_ID}/work/{put_code}", headers=headers)
    resp.raise_for_status()
    work_detail = resp.json()

    # Get DOI correctly from external-ids
    external_ids = work_detail.get("external-ids", {}).get("external-id", [])
    doi = None
    url = None
    for ex in external_ids:
        if ex.get("external-id-type", "").lower() == "doi":
            doi = ex.get("external-id-value", "") or ""
            print(f"\t \t 🔗 DOI for work with put-code {put_code} found: {doi}")
            break
        elif ex.get("external-id-type", "").lower() == "url":
            url = ex.get("external-id-value", "") or ""
            print(f"\t \t 🔗 Found URL for work with put-code {put_code}: {url}")


    citation = work_detail.get("citation")
    if citation and citation.get("citation-type", "").lower() == "bibtex":
        print(f"\t \t ✅ BibTeX citation for work with put-code {put_code} found.")
        bibtex = citation.get("citation-value", "") or ""

        # Normalize DOI if it looks like a URL
        if doi and isinstance(doi, str) and doi.lower().startswith(("http://", "https://")):
            doi = doi.split("doi.org/", 1)[-1] if "doi.org/" in doi.lower() else doi.rsplit("/", 1)[-1]
        try:
            db = bibtexparser.loads(bibtex)
            if not db.entries:
                raise ValueError("No entries parsed from BibTeX")

            entry = db.entries[0]
            # Add missing identifiers
            if doi and not entry.get("doi"):
                entry["doi"] = doi
            elif url and not entry.get("url"):
                entry["url"] = url

            writer = BibTexWriter()
            writer.indent = "  "
            writer.comma_first = False
            writer.add_trailing_comma = True  # nicer diffs

            entry_str = writer.write(db).strip()
            bib_entries.append(entry_str)
            yr = _extract_year(entry.get("year"))
            bib_entries_years.append((yr, entry_str))
        except Exception:
            # Fallback to original string if parsing fails
            entry_str = bibtex.strip()
            bib_entries.append(entry_str)
            yr = _extract_year_from_bibtex_string(entry_str)
            bib_entries_years.append((yr, entry_str))
    else:
        # Fallback: simple entry if no BibTeX citation is available
        print(f"\t \t ⚠️ Found no BibTeX citation for work with put-code {put_code}.")

        title = work_detail.get("title", {}).get("title", {}).get("value", "untitled")
        year = work_detail.get("publication-date", {}).get("year", {}).get("value", "")
        contributors = work_detail.get("contributors", {}).get("contributor", [])
        authors = [c.get("credit-name", {}).get("value", "") for c in contributors if c.get("credit-name")]
        journal_title = work_detail.get("journal-title", {}).get("value", "")

        # Build a sanitized citekey
        key = re.sub(r"\W+", "_", title).strip("_") or f"work_{put_code}"

        db = BibDatabase()
        entry = {
            "ENTRYTYPE": "misc",
            "ID": key,
            "title": title,
        }
        if year:
            entry["year"] = str(year)
        if authors:
            entry["author"] = " and ".join(a for a in authors if a)
        if journal_title:
            entry["journal"] = journal_title

        # Prefer DOI over URL if available
        if doi:
            entry["doi"] = doi
        elif url:
            entry["url"] = url

        db.entries = [entry]

        writer = BibTexWriter()
        writer.indent = "  "
        writer.comma_first = False
        writer.add_trailing_comma = True

        string = writer.write(db).strip()
        bib_entries.append(string)
        bib_entries_years.append((_extract_year(year), string))

    print(f"\t \t 🔗 Citation: {bib_entries[-1]}")

# Write everything to a file (sorted by year, newest first; unknown years last)
sorted_entries = sorted(
    bib_entries_years,
    key=lambda x: (x[0] is None, -(x[0] or 0), x[1].lower())
)
with open(OUTFILE, "w", encoding='utf-8') as f:
    f.write("\n\n".join(entry for _, entry in sorted_entries))

# Save cache file with timestamp
CACHEFILE.parent.mkdir(exist_ok=True)
CACHEFILE.write_text(json.dumps({"last_fetch": datetime.now().isoformat()}))

print(f"✅ {len(bib_entries)} Publications from ORCID saved to {OUTFILE}")
