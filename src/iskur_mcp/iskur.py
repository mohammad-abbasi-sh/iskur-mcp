"""Stdlib parsing for iskur.gov.tr / esube.iskur.gov.tr (İŞKUR — Türkiye
İş Kurumu, the Turkish Employment Agency).

Verified live 2026-11-13 against real pages (fixtures in tests/):
- Job search is classic ASP.NET WebForms on esube.iskur.gov.tr
  (/Istihdam/AcikIsIlanAra.aspx): GET the page (cookies + __VIEWSTATE,
  __VIEWSTATEGENERATOR, __VIEWSTATEENCRYPTED, __EVENTVALIDATION), then
  POST the form with __EVENTTARGET =
  ctl04$ctlAcikIsPageCommand$CommandItem_Search. The search POST is
  SLOW (~40s; one attempt timed out at 90s) — the transport retries
  once with a fresh session. Results render in the grid table
  ctl04_ctlGridAcikIslerListeDetail, 15 rows per page; each row has a
  PopupJobDetails('<jobno>','Özel','0') title link, spans
  ctlIsverenTurDL / ctlCalismaPeriyotDL / ctlCalismaSekliDL (sector /
  permanent-temporary / full-part time), Label9 (open positions),
  ctlCalismaYeriDL ("İl Geneli Başvuru (Çalışma Yeri: İSTANBUL /
  SARIYER)"), ctlSonBasvuruTarihi (deadline dd.mm.yyyy) and
  ctlSonBasvuruDL ("17 Gün Kaldı"). "Toplam Kayıt: 63" is the total;
  the pager carries txtCurrentPage ("1 / 5") and btnNext/btnLast
  postbacks (jump to page N via txtCurrentPage + btnChangeCurrentPage).
  Search filters on the form: ctlArananMetin2 (keyword),
  ctlIl (province code, 81), ctlIlanTarihi (1 all / 2 last 24h /
  3 last week / 4 last 15 days), ctlCalismaSekli ("" all / 1 full /
  2 part time), ctlOgrenimDurum (education codes).
- Job detail is a plain GET:
  /Istihdam/AcikIsIlanDetay.aspx?uiID=<jobno>&isyeriTuru=Özel
  (no cookies needed, ~2s). Sections: ctlGenelSartlar (job
  description paragraphs), ctlGenelSartlar2 (skills paragraphs),
  repeaterMeslek ctlMeslekLabel (occupation) +
  ctlMeslekDeneyimSuresiLabel / ...LabelAy (experience years/months),
  ctlOgrenimAsgari / ctlOgrenimAzami (min/max education). The detail
  page carries NO deadline, city or employer name — those come from
  the search grid; employer names are hidden behind login ("İşyeri
  adını görmek için Sisteme Üye Girişi yapmanız gerekmektedir.") and
  are never returned by this server.
- Announcements: www.iskur.gov.tr/duyurular/ — plain server-rendered
  list; each <li class="clearfix"> has a <div class="date"> (day +
  "<span>Mon yyyy</span>") and an <a href="/duyurular/..."> title.
"""
from __future__ import annotations

import html as _html
import re
from urllib.parse import quote

ESUBE = "https://esube.iskur.gov.tr"
WWW = "https://www.iskur.gov.tr"

_WS = re.compile(r"\s+")

# Search-page filter values (from the live form, 2026-11-13).
DATE_RANGES = {
    "all": "1",
    "last_24h": "2",
    "last_week": "3",
    "last_15d": "4",
}
WORK_TYPES = {"all": "", "full": "1", "part": "2"}
EDUCATION = {
    "any": "",
    "illiterate": "5",
    "literate": "6",
    "primary": "8",
    "middle": "4",
    "high": "3",
    "associate": "7",
    "bachelor": "1",
    "master": "2",
    "phd": "10",
}

# The 81 provinces, code -> name (from the live ctlIl select,
# 2026-11-13). Fallback when the live select cannot be parsed.
CITIES = {
    "1": "ADANA", "2": "ADIYAMAN", "3": "AFYONKARAHİSAR", "4": "AĞRI",
    "68": "AKSARAY", "5": "AMASYA", "6": "ANKARA", "7": "ANTALYA",
    "75": "ARDAHAN", "8": "ARTVİN", "9": "AYDIN", "10": "BALIKESİR",
    "74": "BARTIN", "72": "BATMAN", "69": "BAYBURT", "11": "BİLECİK",
    "12": "BİNGÖL", "13": "BİTLİS", "14": "BOLU", "15": "BURDUR",
    "16": "BURSA", "17": "ÇANAKKALE", "18": "ÇANKIRI", "19": "ÇORUM",
    "20": "DENİZLİ", "21": "DİYARBAKIR", "81": "DÜZCE", "22": "EDİRNE",
    "23": "ELAZIĞ", "24": "ERZİNCAN", "25": "ERZURUM", "26": "ESKİŞEHİR",
    "27": "GAZİANTEP", "28": "GİRESUN", "29": "GÜMÜŞHANE", "30": "HAKKARİ",
    "31": "HATAY", "76": "IĞDIR", "32": "ISPARTA", "34": "İSTANBUL",
    "35": "İZMİR", "46": "KAHRAMANMARAŞ", "78": "KARABÜK", "70": "KARAMAN",
    "36": "KARS", "37": "KASTAMONU", "38": "KAYSERİ", "71": "KIRIKKALE",
    "39": "KIRKLARELİ", "40": "KIRŞEHİR", "79": "KİLİS", "41": "KOCAELİ",
    "42": "KONYA", "43": "KÜTAHYA", "44": "MALATYA", "45": "MANİSA",
    "47": "MARDİN", "33": "MERSİN", "48": "MUĞLA", "49": "MUŞ",
    "50": "NEVŞEHİR", "51": "NİĞDE", "52": "ORDU", "80": "OSMANİYE",
    "53": "RİZE", "54": "SAKARYA", "55": "SAMSUN", "56": "SİİRT",
    "57": "SİNOP", "58": "SİVAS", "63": "ŞANLIURFA", "73": "ŞIRNAK",
    "59": "TEKİRDAĞ", "60": "TOKAT", "61": "TRABZON", "62": "TUNCELİ",
    "64": "UŞAK", "65": "VAN", "77": "YALOVA", "66": "YOZGAT",
    "67": "ZONGULDAK",
}
# Turkish-aware lowercase folding for city-name matching.
_TR_FOLD = str.maketrans({"İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ",
                          "Ü": "ü", "Ö": "ö", "Ç": "ç"})


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return _WS.sub(" ", _html.unescape(text)).strip()


def _strip_tags(fragment: str) -> str:
    return _clean(re.sub(r"<[^>]+>", " ", fragment))


def _paragraphs(fragment: str) -> list[str]:
    """<p>...</p> items of a section, cleaned; falls back to plain text."""
    items = [_strip_tags(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", fragment, re.S)]
    items = [i for i in items if i]
    if items:
        return items
    text = _strip_tags(fragment)
    return [text] if text else []


def _span(html_text: str, suffix: str) -> str | None:
    """Text of the <span id="...<suffix>">...</span>, or None."""
    m = re.search(
        r'<span[^>]*id="[^"]*' + re.escape(suffix) + r'"[^>]*>(.*?)</span>',
        html_text, re.S,
    )
    return _strip_tags(m.group(1)) if m else None


def city_code(city: str) -> str | None:
    """Province name (Turkish, any case) or numeric code -> code, or None."""
    city = city.strip()
    if not city:
        return None
    if re.fullmatch(r"\d+", city) and city in CITIES:
        return city
    folded = city.translate(_TR_FOLD).lower()
    for code, name in CITIES.items():
        if name.translate(_TR_FOLD).lower() == folded:
            return code
    return None


def parse_hidden_fields(page_html: str) -> dict:
    """The WebForms hidden fields needed for a search postback."""
    fields = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR",
                 "__VIEWSTATEENCRYPTED", "__EVENTVALIDATION"):
        m = re.search(
            r'name="%s"[^>]*value="([^"]*)"' % re.escape(name), page_html
        )
        fields[name] = _html.unescape(m.group(1)) if m else ""
    return fields


def parse_cities(page_html: str) -> list[dict]:
    """Provinces from the live ctlIl select: [{code, name}]."""
    m = re.search(
        r'<select[^>]*name="ctl04\$ctlIl"[^>]*>(.*?)</select>',
        page_html, re.S,
    )
    if not m:
        return [{"code": c, "name": n} for c, n in CITIES.items()]
    cities = []
    for value, name in re.findall(
        r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)</option>', m.group(1)
    ):
        name = _clean(name)
        if value and name:
            cities.append({"code": value, "name": name})
    return cities or [{"code": c, "name": n} for c, n in CITIES.items()]


def _parse_location(raw: str) -> dict:
    """'İl Geneli Başvuru (Çalışma Yeri: İSTANBUL / SARIYER)' ->
    {scope, city, district, raw}."""
    text = _clean(raw)
    m = re.search(r"Çalışma Yeri:\s*([^)]+)", text)
    city = district = None
    if m:
        parts = [p.strip() for p in m.group(1).split("/")]
        city = parts[0] or None
        district = parts[1] if len(parts) > 1 else None
    scope_m = re.match(r"^([^(]+?)\s*(?:\(|$)", text)
    return {
        "scope": _clean(scope_m.group(1)) if scope_m else None,
        "city": city,
        "district": district,
        "raw": text,
    }


def parse_search_results(page_html: str) -> dict:
    """Jobs from a search-result page.

    Returns {"jobs": [...], "total": int|None, "page": int,
    "page_count": int|None, "has_next": bool}. Each job: job_no,
    title, sector, period, work_type, open_positions, location
    {scope, city, district, raw}, deadline, days_left, url.
    Employer names are login-gated on the site and never included.
    """
    html_text = _html.unescape(page_html)
    jobs: list[dict] = []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, re.S)
    for row in rows:
        if "PopupJobDetails(" not in row:
            continue
        m = re.search(
            r"PopupJobDetails\('(\d+)','([^']*)','0'\)", row
        )
        if not m:
            continue
        job_no, sector = m.group(1), m.group(2)
        title_m = re.search(
            r"PopupJobDetails\('" + job_no + r"','" + re.escape(sector) +
            r"','0'\);return false;\"[^>]*>([^<]*)</a>", row
        )
        title = _clean(title_m.group(1)) if title_m else None
        loc_raw = _span(row, "ctlCalismaYeriDL") or ""
        open_m = re.search(r"Label9\">(\d+)<", row)
        jobs.append({
            "job_no": job_no,
            "title": title,
            "sector": _span(row, "ctlIsverenTurDL"),
            "period": _span(row, "ctlCalismaPeriyotDL"),
            "work_type": _span(row, "ctlCalismaSekliDL"),
            "open_positions": int(open_m.group(1)) if open_m else None,
            "location": _parse_location(loc_raw),
            "deadline": _span(row, "ctlSonBasvuruTarihi"),
            "days_left": _span(row, "ctlSonBasvuruDL"),
            "url": (
                f"{ESUBE}/Istihdam/AcikIsIlanDetay.aspx"
                f"?uiID={job_no}&isyeriTuru={quote(sector)}"
            ),
        })
    total_m = re.search(r"Toplam Kayıt:\s*([\d\.]+)", html_text)
    total = (
        int(total_m.group(1).replace(".", "")) if total_m else None
    )
    page_m = re.search(
        r'txtCurrentPage"[^>]*value="(\d+)"[^>]*/>\s*/\s*(\d+)', html_text
    )
    page = int(page_m.group(1)) if page_m else 1
    page_count = int(page_m.group(2)) if page_m else None
    next_m = re.search(
        r'id="ctl04_ctlDataPagerDetay_btnNext"[^>]*', html_text
    )
    has_next = bool(next_m) and "aspNetDisabled" not in next_m.group(0)
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "page_count": page_count,
        "has_next": has_next,
    }


def parse_job_detail(page_html: str) -> dict:
    """Detail of one job: description, skills, occupation, experience,
    education. Returns {}-ish fields (all None/empty) when the page
    carries no detail — callers treat that as "not found"."""
    html_text = _html.unescape(page_html)
    desc_m = re.search(
        r'<span[^>]*id="[^"]*ctlGenelSartlar"[^>]*>(.*?)</span>',
        html_text, re.S,
    )
    skills_m = re.search(
        r'<span[^>]*id="[^"]*ctlGenelSartlar2"[^>]*>(.*?)</span>',
        html_text, re.S,
    )
    exp_y = _span(html_text, "ctlMeslekDeneyimSuresiLabel")
    exp_m = _span(html_text, "ctlMeslekDeneyimSuresiLabelAy")
    return {
        "description": (
            "\n".join(_paragraphs(desc_m.group(1))) if desc_m else None
        ),
        "skills": _paragraphs(skills_m.group(1)) if skills_m else [],
        "occupation": _span(html_text, "ctlMeslekLabel"),
        "experience_years": exp_y if exp_y else None,
        "experience_months": exp_m if exp_m else None,
        "education_min": _span(html_text, "ctlOgrenimAsgari"),
        "education_max": _span(html_text, "ctlOgrenimAzami"),
    }


def parse_announcements(page_html: str) -> list[dict]:
    """Announcements from www.iskur.gov.tr/duyurular/.

    Returns [{date, title, url}] in page order."""
    items: list[dict] = []
    for li in re.findall(
        r'<li class="clearfix">(.*?)</li>', page_html, re.S
    ):
        date_m = re.search(
            r'<div class="date">\s*(\d+)\s*<span>([^<]+)</span>',
            li, re.S,
        )
        link_m = re.search(
            r'<a\s+href="(/duyurular/[^"]+)"[^>]*>(.*?)</a>', li, re.S
        )
        if not link_m:
            continue
        date = None
        if date_m:
            date = f"{date_m.group(1)} {_clean(date_m.group(2))}"
        items.append({
            "date": date,
            "title": _strip_tags(link_m.group(2)),
            "url": f"{WWW}{link_m.group(1)}",
        })
    return items
