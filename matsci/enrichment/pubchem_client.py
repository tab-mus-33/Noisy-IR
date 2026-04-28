"""
Retrieves chemical synonyms from PubChem for a given material name.

PubChem REST API — no API key required, rate limit 5 requests/second.
For each entity: name → CID → synonym list → filtered useful synonyms.

Filtering removes:
  - InChI and InChIKey strings
  - SMILES strings
  - CAS registry numbers (pure digit-hyphen strings)
  - Synonyms longer than max_synonym_length (usually database codes)
"""

import re
import time

import requests

from matsci.config import CONFIG


_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_RATE_LIMIT_DELAY = 0.2   # 5 requests/second max
_TIMEOUT = 10             # seconds per request


def _get(url: str) -> dict | None:
    """GET with timeout and graceful failure."""
    try:
        r = requests.get(url, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        return None
    except requests.RequestException:
        return None


def _is_useful_synonym(s: str) -> bool:
    """Return True if the synonym is likely to appear in scientific text."""
    if len(s) > CONFIG["max_synonym_length"]:
        return False
    # InChI strings
    if s.startswith("InChI=") or s.startswith("InChIKey="):
        return False
    # SMILES: contain brackets, =, #, @
    if re.search(r"[=#@\[\]]", s):
        return False
    # Pure CAS numbers: digits separated by hyphens only
    if re.fullmatch(r"\d+-\d+-\d+", s):
        return False
    # Database identifiers: all caps + digits, length > 8
    if re.fullmatch(r"[A-Z0-9]{8,}", s):
        return False
    return True


def name_to_cid(name: str) -> int | None:
    """Look up PubChem CID for a chemical name."""
    url = f"{_BASE}/compound/name/{requests.utils.quote(name)}/cids/JSON"
    time.sleep(_RATE_LIMIT_DELAY)
    data = _get(url)
    if data and "IdentifierList" in data:
        cids = data["IdentifierList"].get("CID", [])
        return cids[0] if cids else None
    return None


def cid_to_synonyms(cid: int) -> list[str]:
    """Fetch all synonyms for a PubChem CID."""
    url = f"{_BASE}/compound/cid/{cid}/synonyms/JSON"
    time.sleep(_RATE_LIMIT_DELAY)
    data = _get(url)
    if data and "InformationList" in data:
        info = data["InformationList"].get("Information", [])
        if info:
            return info[0].get("Synonym", [])
    return []


def get_synonyms(name: str) -> list[str]:
    """
    Main entry point: given a material name, return filtered synonyms.

    Returns empty list if the name is not found in PubChem.
    """
    cid = name_to_cid(name)
    if cid is None:
        return []

    raw = cid_to_synonyms(cid)
    filtered = [s for s in raw if _is_useful_synonym(s)]
    return filtered[: CONFIG["max_synonyms_per_entity"]]


if __name__ == "__main__":
    for test in ["alumina", "titania", "barium titanate", "tin oxide"]:
        syns = get_synonyms(test)
        print(f"\n{test} ({len(syns)} synonyms):")
        for s in syns:
            print(f"  {s}")
