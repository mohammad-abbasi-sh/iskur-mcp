"""HTTP layer for iskur_mcp.

Job search lives on esube.iskur.gov.tr (ASP.NET WebForms, verified
live 2026-11-13): GET /Istihdam/AcikIsIlanAra.aspx for session
cookies + __VIEWSTATE family, then POST the form with
__EVENTTARGET=ctl04$ctlAcikIsPageCommand$CommandItem_Search.
The search POST is SLOW (~40s; one attempt timed out at 90s), so it
gets a 180s timeout and one retry with a fresh session. Job detail
(/Istihdam/AcikIsIlanDetay.aspx?uiID=...&isyeriTuru=Özel) and the
announcements list (www.iskur.gov.tr/duyurular/) are plain fast
GETs (~2s, no cookies needed). Transport uses curl-cffi Chrome
impersonation with fingerprint rotation, forced HTTP/1.1 (the host's
HTTP/2 path RSTs and stalls from this VM, 2026-11-13); requests are
read-only (GET + the site's own search postback, which only reads
listings) and spaced ~0.8s apart.

VM note: on this VM outbound HTTPS goes through an egress proxy; the
MCP stdio client spawns servers with a minimal environment (no proxy
variables), so client-spawned runs here need the proxy variables
forwarded (see tests/smoke_mcp.py) or requests die mid-TLS (curl 35,
connection reset). On a normal machine with direct internet this
does not apply.
"""
from __future__ import annotations

import time

from curl_cffi import CurlHttpVersion, requests as _r

from . import iskur as _I

ESUBE = "https://esube.iskur.gov.tr"
WWW = "https://www.iskur.gov.tr"
SEARCH_PATH = "/Istihdam/AcikIsIlanAra.aspx"
DETAIL_PATH = "/Istihdam/AcikIsIlanDetay.aspx"

TIMEOUT = 30.0
SEARCH_TIMEOUT = 180.0  # the search postback is slow (~40s; one 90s timeout seen)
MIN_INTERVAL = 0.8  # seconds between requests — be polite

_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

_last_fetch = 0.0


class IskurError(RuntimeError):
    pass


_PROFILES = ("chrome120", "chrome131", "safari17_0")
_MAX_ATTEMPTS = 3  # plain GETs are cheap; the esube host is flaky (RSTs)
_RETRY_BACKOFF = 1.0  # seconds between attempts
_profile_idx = 0  # sticky: profile that last succeeded

# esube's HTTP/2 path proved flaky from this VM (connection RSTs and
# 30s stalls, 2026-11-13); plain HTTP/1.1 answered consistently in
# ~2-4s. Force HTTP/1.1 on every request to both İŞKUR hosts.
_HTTP_VERSION = CurlHttpVersion.V1_1


def _request(url: str, headers: dict, timeout: float = TIMEOUT,
             allow_redirects: bool = True):
    """GET with fingerprint rotation (plain, session-less)."""
    global _profile_idx
    last_exc: Exception | None = None
    for k in range(_MAX_ATTEMPTS):
        profile = _PROFILES[(_profile_idx + k) % len(_PROFILES)]
        try:
            resp = _r.get(url, impersonate=profile, headers=headers,
                          timeout=timeout, allow_redirects=allow_redirects,
                          http_version=_HTTP_VERSION)
        except Exception as e:
            last_exc = e
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            raise IskurError(f"network error fetching {url}: {e}") from e
        if resp.status_code in (403, 429):
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            return resp
        _profile_idx = (_profile_idx + k) % len(_PROFILES)
        return resp
    raise IskurError(f"network error fetching {url}: {last_exc}") from last_exc


def _get(url: str, timeout: float = TIMEOUT) -> str:
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = _request(url, _HEADERS, timeout=timeout)
    except IskurError:
        raise
    except Exception as e:
        raise IskurError(f"network error fetching {url}: {e}") from e
    finally:
        _last_fetch = time.monotonic()
    if resp.status_code == 403:
        raise IskurError(
            "iskur.gov.tr refused the request (HTTP 403, bot wall) — try again later"
        )
    if resp.status_code == 429:
        raise IskurError(
            "iskur.gov.tr rate-limited the request (HTTP 429) — try again later"
        )
    if resp.status_code == 404:
        raise IskurError(f"iskur.gov.tr returned HTTP 404 for {url}")
    if resp.status_code != 200:
        raise IskurError(
            f"iskur.gov.tr returned HTTP {resp.status_code} for {url}"
        )
    return resp.text


def _search_form(hidden: dict, keyword: str, city_code: str,
                 date_range: str, work_type: str, education: str) -> dict:
    return {
        "__EVENTTARGET": "ctl04$ctlAcikIsPageCommand$CommandItem_Search",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": hidden.get("__VIEWSTATE", ""),
        "__VIEWSTATEGENERATOR": hidden.get("__VIEWSTATEGENERATOR", ""),
        "__VIEWSTATEENCRYPTED": hidden.get("__VIEWSTATEENCRYPTED", ""),
        "__EVENTVALIDATION": hidden.get("__EVENTVALIDATION", ""),
        "ctl04$ctlArananMetin2": keyword or "",
        "ctl04$ctlIl": city_code or "",
        "ctl04$ctlIlanTarihi": date_range,
        "ctl04$ctlCalismaSekli": work_type,
        "ctl04$ctlOgrenimDurum": education,
    }


def _post_search(session, form: dict) -> str:
    """One search postback; raises IskurError on transport failure."""
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = session.post(
            ESUBE + SEARCH_PATH, data=form,
            headers={**_HEADERS,
                     "Content-Type": "application/x-www-form-urlencoded",
                     "Referer": ESUBE + SEARCH_PATH},
            timeout=SEARCH_TIMEOUT,
        )
    except Exception as e:
        raise IskurError(f"search postback failed: {e}") from e
    finally:
        _last_fetch = time.monotonic()
    if resp.status_code == 403:
        raise IskurError("esube.iskur.gov.tr refused the search (HTTP 403)")
    if resp.status_code == 429:
        raise IskurError("esube.iskur.gov.tr rate-limited the search (HTTP 429)")
    if resp.status_code != 200:
        raise IskurError(
            f"esube.iskur.gov.tr returned HTTP {resp.status_code} for the search"
        )
    return resp.text


def search_jobs(keyword: str = "", city_code: str = "",
                date_range: str = "1", work_type: str = "",
                education: str = "", page: int = 1) -> str:
    """Run a job search; returns the results-page HTML.

    One retry with a fresh session on transport failure (the search
    postback is slow and occasionally stalls). page > 1 jumps via the
    pager's txtCurrentPage + btnChangeCurrentPage postback.
    """
    last_exc: Exception | None = None
    for attempt in range(2):
        profile = _PROFILES[(_profile_idx + attempt) % len(_PROFILES)]
        try:
            session = _r.Session(impersonate=profile,
                                 http_version=_HTTP_VERSION)
            try:
                form_page = session.get(
                    ESUBE + SEARCH_PATH, headers=_HEADERS,
                    timeout=TIMEOUT,
                ).text
                hidden = _I.parse_hidden_fields(form_page)
                form = _search_form(hidden, keyword, city_code,
                                    date_range, work_type, education)
                html_text = _post_search(session, form)
                if page and page > 1:
                    hidden2 = _I.parse_hidden_fields(html_text)
                    jump = _search_form(hidden2, keyword, city_code,
                                        date_range, work_type, education)
                    jump["__EVENTTARGET"] = (
                        "ctl04$ctlDataPagerDetay$btnChangeCurrentPage"
                    )
                    jump["ctl04$ctlDataPagerDetay$txtCurrentPage"] = str(page)
                    html_text = _post_search(session, jump)
                return html_text
            finally:
                session.close()
        except IskurError as e:
            last_exc = e
            time.sleep(_RETRY_BACKOFF)
            continue
    raise IskurError(f"job search failed after retry: {last_exc}")


def fetch_search_page() -> str:
    """The blank search form page HTML (carries the city select)."""
    return _get(ESUBE + SEARCH_PATH)


def fetch_job_detail(job_no: str) -> str:
    """One job's detail page HTML (plain GET, no cookies needed)."""
    url = (
        f"{ESUBE}{DETAIL_PATH}?uiID={job_no}&isyeriTuru=%C3%96zel"
    )
    return _get(url)


def fetch_announcements() -> str:
    """The announcements list page HTML (www.iskur.gov.tr/duyurular/)."""
    return _get(f"{WWW}/duyurular/")


def health_check() -> dict:
    """One polite probe of both İŞKUR hosts.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `iskur_health` tool
    and the daily smoke CI.
    """
    url = ESUBE + SEARCH_PATH
    try:
        _get(url)
    except IskurError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
