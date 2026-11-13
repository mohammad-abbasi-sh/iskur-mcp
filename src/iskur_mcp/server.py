"""MCP server: unofficial read-only access to İŞKUR (iskur.gov.tr) —
Türkiye İş Kurumu, the Turkish Employment Agency: open job listings
from the public esube portal, job details, provinces, and official
announcements."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import http as _http
from . import iskur as _I

mcp = FastMCP("iskur-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for İŞKUR (iskur.gov.tr) — Türkiye
İş Kurumu, the Turkish Employment Agency. iskur_search_jobs searches
the public open-job listings (keyword, city name or province code,
date range, work type, education, page — 15 jobs per page, total and
page_count are returned); iskur_latest_jobs lists jobs posted in the
last 24 hours, optionally in one city; iskur_get_job returns one
job's detail (description, required skills, occupation, experience,
min/max education) by its job number (e.g. "00009899349"); use
iskur_list_cities for the 81 province names and codes;
iskur_list_announcements lists İŞKUR's official announcements.
Employer names are hidden behind login on the site and are never
returned; the detail page carries no deadline or city — those come
from the search results. Data comes from the site's own pages — no
login, no API key. Read-only; the search is a WebForms postback and
is slow (~40s), so prefer page 1 and narrow filters. Transport uses
Chrome TLS impersonation; requests are spaced ~0.8s apart.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Turkey MCP
factory.\
"""


_SOURCE = "iskur.gov.tr / esube.iskur.gov.tr"
_DISCLAIMER = "Unofficial read-only data from İŞKUR (Türkiye İş Kurumu); employer names are login-gated on the site and never returned — verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _limit(limit: int, cap: int = 15) -> int:
    return max(1, min(int(limit), cap))


@mcp.tool()
def iskur_search_jobs(keyword: str = "", city: str = "",
                      date_range: str = "all", work_type: str = "all",
                      education: str = "any", page: int = 1,
                      limit: int = 15) -> str:
    """Search İŞKUR's open job listings.

    keyword: Turkish job/occupation text (e.g. "garson", "aşçı") —
    empty means all jobs. city: province name (e.g. "İstanbul",
    "Ankara") or code (e.g. "34") — empty means all provinces.
    date_range: "all" (default), "last_24h", "last_week", "last_15d".
    work_type: "all" (default), "full" (Tam Zamanlı), "part"
    (Kısmi Zamanlı). education: "any" (default), "illiterate",
    "literate", "primary", "middle", "high", "associate",
    "bachelor", "master", "phd". page: results page (15 jobs per
    page; total and page_count are returned). limit: 1..15 jobs
    returned. Each job: job_no, title, sector, period, work_type,
    open_positions, location {scope, city, district}, deadline
    (dd.mm.yyyy), days_left, url. The search postback is slow
    (~40s); prefer page 1 and narrow filters."""
    if date_range not in _I.DATE_RANGES:
        return _ok({"error": f"unknown date_range {date_range!r}",
                    "known_date_ranges": list(_I.DATE_RANGES)})
    if work_type not in _I.WORK_TYPES:
        return _ok({"error": f"unknown work_type {work_type!r}",
                    "known_work_types": list(_I.WORK_TYPES)})
    if education not in _I.EDUCATION:
        return _ok({"error": f"unknown education {education!r}",
                    "known_education": list(_I.EDUCATION)})
    code = ""
    if city and city.strip():
        code = _I.city_code(city)
        if code is None:
            return _ok({"error": f"unknown city {city!r} — try "
                        "iskur_list_cities for province names/codes",
                        "city": city})
    try:
        html_text = _http.search_jobs(
            keyword.strip(), code, _I.DATE_RANGES[date_range],
            _I.WORK_TYPES[work_type], _I.EDUCATION[education], page)
    except _http.IskurError as e:
        return _ok({"error": str(e)})
    result = _I.parse_search_results(html_text)
    jobs = result["jobs"][:_limit(limit)]
    return _ok({"keyword": keyword.strip() or None, "city": city or None,
                "date_range": date_range, "work_type": work_type,
                "education": education, "page": result["page"],
                "page_count": result["page_count"],
                "total": result["total"], "has_next": result["has_next"],
                "count": len(jobs), "jobs": jobs})


@mcp.tool()
def iskur_latest_jobs(city: str = "", limit: int = 15) -> str:
    """Jobs posted on İŞKUR in the last 24 hours.

    city: province name (e.g. "İstanbul") or code (e.g. "34") —
    empty means all provinces. limit: 1..15 jobs returned. Each job:
    job_no, title, sector, period, work_type, open_positions,
    location {scope, city, district}, deadline, days_left, url."""
    code = ""
    if city and city.strip():
        code = _I.city_code(city)
        if code is None:
            return _ok({"error": f"unknown city {city!r} — try "
                        "iskur_list_cities for province names/codes",
                        "city": city})
    try:
        html_text = _http.search_jobs("", code, _I.DATE_RANGES["last_24h"],
                                      "", "", 1)
    except _http.IskurError as e:
        return _ok({"error": str(e)})
    result = _I.parse_search_results(html_text)
    jobs = result["jobs"][:_limit(limit)]
    return _ok({"city": city or None, "date_range": "last_24h",
                "page": result["page"], "page_count": result["page_count"],
                "total": result["total"], "has_next": result["has_next"],
                "count": len(jobs), "jobs": jobs})


@mcp.tool()
def iskur_get_job(job_no: str) -> str:
    """Detail of one İŞKUR job listing.

    job_no: the listing number from a search result (e.g.
    "00009899349"). Returns description, required skills, occupation,
    experience (years/months), min/max education, and the detail URL.
    The detail page carries no deadline or city — those come from
    iskur_search_jobs — and no employer name (login-gated on the
    site)."""
    job_no = job_no.strip()
    if not re.fullmatch(r"\d+", job_no):
        return _ok({"error": f"job_no must be numeric, got {job_no!r}",
                    "job_no": job_no})
    try:
        html_text = _http.fetch_job_detail(job_no)
    except _http.IskurError as e:
        return _ok({"error": str(e), "job_no": job_no})
    detail = _I.parse_job_detail(html_text)
    if not detail["description"] and not detail["occupation"]:
        return _ok({"error": f"no detail found for job {job_no!r} — "
                    "unknown job number or the listing was removed",
                    "job_no": job_no})
    return _ok({"job_no": job_no,
                "url": f"{_I.ESUBE}/Istihdam/AcikIsIlanDetay.aspx"
                       f"?uiID={job_no}&isyeriTuru=%C3%96zel",
                **detail})


@mcp.tool()
def iskur_list_cities() -> str:
    """The 81 Turkish provinces İŞKUR searches by — code + name.

    Use the code (e.g. "34" for İstanbul) or the name in
    iskur_search_jobs / iskur_latest_jobs. Parsed live from the
    search form; falls back to the built-in list if the form cannot
    be read."""
    try:
        cities = _I.parse_cities(_http.fetch_search_page())
    except _http.IskurError as e:
        return _ok({"error": str(e)})
    return _ok({"count": len(cities), "cities": cities})


@mcp.tool()
def iskur_list_announcements(limit: int = 10) -> str:
    """İŞKUR's official announcements (duyurular).

    limit: 1..10 announcements returned (the site lists ~10 per
    page). Each announcement: date, title, url."""
    try:
        items = _I.parse_announcements(_http.fetch_announcements())
    except _http.IskurError as e:
        return _ok({"error": str(e)})
    return _ok({"count": len(items[:_limit(limit, 10)]),
                 "announcements": items[:_limit(limit, 10)]})


@mcp.tool()
def iskur_health() -> str:
    """Check whether İŞKUR's job portal is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not run a search."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    import sys

    sys.exit(main())
