# iskur-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/iskur-mcp

Unofficial **read-only** MCP server for İŞKUR (iskur.gov.tr) — Türkiye İş Kurumu, the Turkish Employment Agency. Search the public open-job listings from the esube portal (keyword, city, date range, work type, education, pagination), get one job's detail (description, required skills, occupation, experience, education), list the 81 provinces, and read İŞKUR's official announcements.

> Built by Mohammad Abbasi as part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with İŞKUR or Türkiye İş Kurumu.

**Note:** employer names are hidden behind login on the site and are never returned; the detail page carries no deadline or city — those come from the search results. The search is a WebForms postback and is slow (~40s), so prefer page 1 and narrow filters.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "iskur": {
      "command": "uvx",
      "args": ["iskur-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m iskur_mcp.server` (needs `mcp<2`, `curl-cffi`).

## Tools

| Tool | Description |
|------|-------------|
| `iskur_search_jobs` | Search open job listings — `keyword` (e.g. "garson"), `city` name or code (e.g. "İstanbul" / "34"), `date_range` ("all" / "last_24h" / "last_week" / "last_15d"), `work_type` ("all" / "full" / "part"), `education` ("any" / "illiterate" / "literate" / "primary" / "middle" / "high" / "associate" / "bachelor" / "master" / "phd"), `page` (15/page, total + page_count returned), `limit` 1..15 |
| `iskur_latest_jobs` | Jobs posted in the last 24 hours, optionally in one `city`; `limit` 1..15 |
| `iskur_get_job` | Detail of one listing — `job_no` (e.g. "00009899349"): description, skills, occupation, experience, min/max education |
| `iskur_list_cities` | The 81 provinces — code + name (e.g. "34" İstanbul, "6" Ankara) |
| `iskur_list_announcements` | İŞKUR's official announcements (duyurular); `limit` 1..10 |
| `iskur_health` | Check whether İŞKUR's job portal is reachable (ok / blocked / error) |

Example output (`iskur_search_jobs` / "garson", İstanbul, 2026-11-13):

```json
{"keyword": "garson", "city": "İstanbul", "page": 1, "page_count": 5,
 "total": 63,
 "jobs": [{"job_no": "00009899349", "title": "Servis Elemanı (Garson)",
  "sector": "Özel", "period": "Daimi", "work_type": "Tam Zamanlı",
  "open_positions": 1,
  "location": {"city": "İSTANBUL", "district": "SARIYER"},
  "deadline": "30.11.2026", "days_left": "17 Gün Kaldı",
  "url": "https://esube.iskur.gov.tr/Istihdam/AcikIsIlanDetay.aspx?uiID=00009899349&isyeriTuru=%C3%96zel"}]}
```

## How it works

Job search lives on esube.iskur.gov.tr (`/Istihdam/AcikIsIlanAra.aspx`, classic ASP.NET WebForms): GET the form for session cookies + the `__VIEWSTATE` family, then POST with `__EVENTTARGET=ctl04$ctlAcikIsPageCommand$CommandItem_Search`. Results render in the grid table `ctl04_ctlGridAcikIslerListeDetail`, 15 rows per page; each row has a `PopupJobDetails('<jobno>','Özel','0')` title link, spans for sector / period / work type, `Label9` (open positions), `ctlCalismaYeriDL` ("İl Geneli Başvuru (Çalışma Yeri: İSTANBUL / SARIYER)"), `ctlSonBasvuruTarihi` (deadline) and `ctlSonBasvuruDL` ("17 Gün Kaldı"); "Toplam Kayıt: 63" is the total and the pager jumps via `txtCurrentPage` + `btnChangeCurrentPage`. Job detail is a plain GET (`AcikIsIlanDetay.aspx?uiID=...&isyeriTuru=Özel`, ~2s, no cookies): `ctlGenelSartlar` (description), `ctlGenelSartlar2` (skills), `ctlMeslekLabel` (occupation) + experience spans, `ctlOgrenimAsgari` / `ctlOgrenimAzami` (education). Announcements are a plain GET of `www.iskur.gov.tr/duyurular/` (`<li class="clearfix">` with a `<div class="date">` and a `/duyurular/...` link). Transport uses Chrome TLS impersonation (`curl-cffi`, `chrome120` with rotation); the search postback gets a 180s timeout and one retry with a fresh session; requests are spaced ~0.8s apart; everything is read-only.

## Install

```bash
uvx iskur-mcp==0.1.0   # run directly (needs uv)
# or
pip install iskur-mcp==0.1.0
iskur-mcp    # starts the MCP server on stdio
```

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Offline tests run on recorded fixtures (real pages fetched 2026-11-13); live tests hit esube.iskur.gov.tr and www.iskur.gov.tr (the search postback is slow, ~40s per call — live tests take ~3 minutes). Tests green at build time (see repo for counts) plus an MCP stdio smoke test.

## Roadmap

- Occupation (meslek) autocomplete search (the form's `ctlMeslek` field)
- Kamu (public-sector) listings via the sector radio
- TYP / İŞKUR Gençlik programme listings (IstIupArama / TypArama)

## License

MIT — see [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
