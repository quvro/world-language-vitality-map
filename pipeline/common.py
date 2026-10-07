# -*- coding: utf-8 -*-
"""Shared helpers for the data pipeline.

Notes on this host's network (measured, not assumed):
  * github.com and raw.githubusercontent.com are UNREACHABLE
  * api.github.com IS reachable -> use the git blob API (base64, <=100MB)
  * wikimedia.org/api/rest_v1 IS reachable
  * meta.wikimedia.org IS reachable
  * *.wikipedia.org is NOT reachable
  * query.wikidata.org is reachable but rate-limited to ~1 req/min
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# --------------------------------------------------------------------------- paths
PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PIPELINE_DIR)
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")
WALS_DIR = os.path.join(RAW, "wals")
WIKIMEDIA_DIR = os.path.join(RAW, "wikimedia")
XREF_DIR = os.path.join(RAW, "xref")
PROCESSED = os.path.join(DATA, "processed")

for _d in (DATA, RAW, WALS_DIR, WIKIMEDIA_DIR, XREF_DIR, PROCESSED):
    os.makedirs(_d, exist_ok=True)

UA = "CourseProject-LanguageVitality/0.1 (student coursework)"

WALS_FILES = [
    "values.csv",
    "languages.csv",
    "parameters.csv",
    "codes.csv",
    "genealogy.csv",
    "language_names.csv",
]


# --------------------------------------------------------------------------- logging
def log(msg: str = "") -> None:
    try:
        print(msg, flush=True)
    except Exception:  # noqa: BLE001
        pass


def banner(title: str) -> None:
    log("")
    log("=" * 74)
    log(f"  {title}")
    log("=" * 74)


# --------------------------------------------------------------------------- http
def http_get(url: str, *, timeout: int = 180, accept: str = "*/*",
             retries: int = 3, backoff: float = 4.0) -> bytes:
    """GET with retries on network errors and 5xx.

    Client errors (4xx) are re-raised as HTTPError immediately so the caller can
    inspect the status code (e.g. 404 = no data, 429 = back off). Wrapping them
    in RuntimeError would hide the status and defeat that handling.
    """
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise
            last = exc
            log(f"    [retry {attempt}/{retries}] HTTP {exc.code}")
            if attempt < retries:
                time.sleep(backoff * attempt)
        except Exception as exc:  # noqa: BLE001
            last = exc
            log(f"    [retry {attempt}/{retries}] {type(exc).__name__}: {str(exc)[:90]}")
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise RuntimeError(f"GET failed after {retries} attempts: {url}") from last


def http_json(url: str, **kw) -> dict:
    return json.loads(http_get(url, accept="application/json", **kw))


# --------------------------------------------------------------------------- github
def github_blob(repo: str, path: str) -> bytes:
    """Fetch a file from a GitHub repo via the blob API (works when raw is blocked)."""
    meta = http_json(
        f"https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(path)}")
    blob = http_json(meta["git_url"])
    if blob.get("encoding") != "base64":
        raise RuntimeError(f"unexpected blob encoding: {blob.get('encoding')}")
    return base64.b64decode(blob["content"])


def github_list(repo: str, path: str = "") -> list[dict]:
    return http_json(f"https://api.github.com/repos/{repo}/contents/{path}")


# --------------------------------------------------------------------------- io
def write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)


def write_json(path: str, obj) -> None:
    """Write JSON that browsers can actually parse.

    ``allow_nan=False`` is deliberate: Python's json writes bare ``NaN`` /
    ``Infinity`` tokens, which are invalid JSON and make ``JSON.parse`` reject
    the WHOLE file, producing a blank page with no obvious cause. pandas turns
    missing numeric values into NaN, so this is easy to hit. Raising here keeps
    the failure at build time instead of in the browser.
    """
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)


def records(df) -> list[dict]:
    """DataFrame -> list of dicts with NaN/NaT replaced by None.

    ``df.where(..., None)`` alone does not work on float columns (None is
    coerced back to NaN), so cast to object first.
    """
    import pandas as pd  # local import: only needed by pipeline builders

    return df.astype(object).where(pd.notna(df), None).to_dict(orient="records")


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def exists(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0


def human(n: int) -> str:
    return f"{n:,}"


def norm_month(ts: str) -> str:
    """Normalise a timestamp to YYYYMM.

    The two Wikimedia endpoints disagree on format:
      pageviews -> "2015070100"                (compact)
      edits     -> "2015-07-01T00:00:00.000Z"  (ISO)
    Joining on the raw value silently produces keys like "2015-0".
    """
    digits = "".join(ch for ch in str(ts) if ch.isdigit())
    return digits[:6] if len(digits) >= 6 else str(ts)


# --------------------------------------------------------------------------- wikidata
WDQS = "https://query.wikidata.org/sparql"


def wdqs(query: str, *, retries: int = 6, wait: float = 75.0) -> list[dict]:
    """Run one SPARQL query. WDQS is degraded: ~1 req/min, long Retry-After."""
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            data = json.loads(http_get(
                url, accept="application/sparql-results+json", timeout=180,
                retries=1))
            return data["results"]["bindings"]
        except Exception as exc:  # noqa: BLE001
            last = exc
            log(f"    [wdqs retry {attempt}/{retries}] {type(exc).__name__}: "
                f"{str(exc)[:80]}")
            if attempt < retries:
                time.sleep(wait)
    raise RuntimeError("WDQS query failed") from last
