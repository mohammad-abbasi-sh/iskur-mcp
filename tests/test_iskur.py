"""Offline tests for iskur_mcp — recorded fixtures (real pages fetched
2026-11-13). No network.

Run: python -m unittest discover -s tests -v
"""
import unittest
from pathlib import Path

from iskur_mcp import iskur as I

FIX = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8", errors="ignore")


class TestHiddenFields(unittest.TestCase):
    def test_search_page_fields(self):
        fields = I.parse_hidden_fields(_read("search-page.html"))
        for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR",
                     "__EVENTVALIDATION"):
            self.assertTrue(fields[name], name)
        # __VIEWSTATEENCRYPTED exists on the form but is empty on the
        # live page (the browser posts it empty too).
        self.assertIn("__VIEWSTATEENCRYPTED", fields)
        self.assertEqual(fields["__VIEWSTATEENCRYPTED"], "")

    def test_empty_html(self):
        fields = I.parse_hidden_fields("")
        self.assertEqual(fields["__VIEWSTATE"], "")


class TestCities(unittest.TestCase):
    def test_parse_cities_live_select(self):
        cities = I.parse_cities(_read("search-page.html"))
        self.assertEqual(len(cities), 81)
        by_code = {c["code"]: c["name"] for c in cities}
        self.assertEqual(by_code["34"], "İSTANBUL")
        self.assertEqual(by_code["6"], "ANKARA")
        self.assertEqual(by_code["81"], "DÜZCE")
        self.assertEqual(by_code["1"], "ADANA")

    def test_parse_cities_fallback(self):
        cities = I.parse_cities("<html></html>")
        self.assertEqual(len(cities), 81)

    def test_city_code(self):
        self.assertEqual(I.city_code("İstanbul"), "34")
        self.assertEqual(I.city_code("istanbul"), "34")
        self.assertEqual(I.city_code("İSTANBUL"), "34")
        self.assertEqual(I.city_code("34"), "34")
        self.assertEqual(I.city_code("Ankara"), "6")
        self.assertEqual(I.city_code("Şanlıurfa"), "63")
        self.assertIsNone(I.city_code("zzz-no-such-city"))
        self.assertIsNone(I.city_code(""))
        self.assertIsNone(I.city_code("999"))


class TestSearchResults(unittest.TestCase):
    def test_garson_istanbul(self):
        result = I.parse_search_results(_read("search-garson-istanbul.html"))
        self.assertEqual(result["total"], 63)
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["page_count"], 5)
        self.assertTrue(result["has_next"])
        self.assertEqual(len(result["jobs"]), 15)
        job = result["jobs"][0]
        self.assertEqual(job["job_no"], "00009899349")
        self.assertEqual(job["title"], "Servis Elemanı (Garson)")
        self.assertEqual(job["sector"], "Özel")
        self.assertEqual(job["period"], "Daimi")
        self.assertEqual(job["work_type"], "Tam Zamanlı")
        self.assertEqual(job["open_positions"], 1)
        self.assertEqual(job["location"]["city"], "İSTANBUL")
        self.assertEqual(job["location"]["district"], "SARIYER")
        self.assertEqual(job["deadline"], "30.11.2026")
        self.assertEqual(job["days_left"], "17 Gün Kaldı")
        self.assertIn("uiID=00009899349", job["url"])
        self.assertIn("esube.iskur.gov.tr", job["url"])
        # every job has the required fields
        for j in result["jobs"]:
            self.assertTrue(j["job_no"] and j["title"] and j["deadline"])
            self.assertTrue(j["location"]["city"])
            self.assertTrue(j["url"].startswith("https://"))

    def test_blank_search_page_has_no_jobs(self):
        result = I.parse_search_results(_read("search-page.html"))
        self.assertEqual(result["jobs"], [])
        self.assertIsNone(result["total"])
        self.assertEqual(result["page"], 1)

    def test_empty_html(self):
        result = I.parse_search_results("")
        self.assertEqual(result["jobs"], [])
        self.assertIsNone(result["total"])


class TestJobDetail(unittest.TestCase):
    def test_garson_detail(self):
        d = I.parse_job_detail(_read("detail-00009899349.html"))
        self.assertIn("İzzet Baysal Huzurevinin", d["description"])
        self.assertIn("Hijyen belgesi", d["description"])
        self.assertEqual(len(d["skills"]), 9)
        self.assertIn("Takım çalışmasına yatkın", d["skills"])
        self.assertEqual(d["occupation"], "Servis Elemanı (Garson)")
        self.assertEqual(d["education_min"], "İlköğretim")
        self.assertFalse(d["education_max"])  # empty on the site

    def test_not_found_detail(self):
        d = I.parse_job_detail(_read("detail-not-found.html"))
        self.assertIsNone(d["description"])
        self.assertIsNone(d["occupation"])
        self.assertEqual(d["skills"], [])

    def test_empty_html(self):
        d = I.parse_job_detail("")
        self.assertIsNone(d["description"])
        self.assertIsNone(d["occupation"])


class TestAnnouncements(unittest.TestCase):
    def test_duyurular(self):
        items = I.parse_announcements(_read("duyurular.html"))
        self.assertGreaterEqual(len(items), 10)
        first = items[0]
        self.assertTrue(first["title"])
        self.assertTrue(first["url"].startswith(
            "https://www.iskur.gov.tr/duyurular/"))
        self.assertTrue(first["date"])
        for item in items:
            self.assertTrue(item["title"] and item["url"])

    def test_empty_html(self):
        self.assertEqual(I.parse_announcements(""), [])


class TestMappings(unittest.TestCase):
    def test_date_ranges(self):
        self.assertEqual(I.DATE_RANGES["all"], "1")
        self.assertEqual(I.DATE_RANGES["last_24h"], "2")
        self.assertEqual(I.DATE_RANGES["last_week"], "3")
        self.assertEqual(I.DATE_RANGES["last_15d"], "4")

    def test_work_types(self):
        self.assertEqual(I.WORK_TYPES["full"], "1")
        self.assertEqual(I.WORK_TYPES["part"], "2")

    def test_education(self):
        self.assertEqual(I.EDUCATION["bachelor"], "1")
        self.assertEqual(I.EDUCATION["phd"], "10")


if __name__ == "__main__":
    unittest.main()
