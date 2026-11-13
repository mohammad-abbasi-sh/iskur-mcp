"""Live tests for iskur_mcp — real requests to esube.iskur.gov.tr and
www.iskur.gov.tr.

Requires network. The search postback is SLOW (~40s; one attempt
timed out at 90s), so this file takes ~3 minutes. Run:
    python -m unittest discover -s tests -v

Job listings rotate, so tests assert structure and sane ranges, not
exact listings — except the pinned detail check, which re-searches
first and details whatever job comes back first.
"""
import unittest

from iskur_mcp import http as H
from iskur_mcp import iskur as I


class TestLiveSearch(unittest.TestCase):
    def test_search_garson_istanbul(self):
        html_text = H.search_jobs("garson", "34", "1", "", "", 1)
        result = I.parse_search_results(html_text)
        self.assertGreater(len(result["jobs"]), 0)
        self.assertGreater(result["total"], 0)
        self.assertEqual(result["page"], 1)
        self.assertGreaterEqual(result["page_count"], 1)
        job = result["jobs"][0]
        self.assertTrue(job["job_no"] and job["title"])
        self.assertEqual(job["location"]["city"], "İSTANBUL")
        self.assertTrue(job["deadline"])

    def test_search_page2(self):
        html_text = H.search_jobs("garson", "34", "1", "", "", 2)
        result = I.parse_search_results(html_text)
        self.assertEqual(result["page"], 2)
        self.assertGreater(len(result["jobs"]), 0)
        self.assertGreater(result["total"], 0)

    def test_latest_jobs(self):
        html_text = H.search_jobs("", "", "2", "", "", 1)
        result = I.parse_search_results(html_text)
        self.assertIsNotNone(result["total"])
        for job in result["jobs"]:
            self.assertTrue(job["job_no"] and job["title"])

    def test_search_and_detail(self):
        html_text = H.search_jobs("garson", "34", "1", "", "", 1)
        result = I.parse_search_results(html_text)
        self.assertGreater(len(result["jobs"]), 0)
        job_no = result["jobs"][0]["job_no"]
        detail = I.parse_job_detail(H.fetch_job_detail(job_no))
        self.assertTrue(detail["description"])
        self.assertTrue(detail["occupation"])


class TestLiveDetail(unittest.TestCase):
    def test_bogus_job_not_found(self):
        detail = I.parse_job_detail(H.fetch_job_detail("99999999999"))
        self.assertIsNone(detail["description"])
        self.assertIsNone(detail["occupation"])


class TestLiveLists(unittest.TestCase):
    def test_cities(self):
        cities = I.parse_cities(H.fetch_search_page())
        self.assertEqual(len(cities), 81)
        by_code = {c["code"]: c["name"] for c in cities}
        self.assertEqual(by_code["34"], "İSTANBUL")

    def test_announcements(self):
        items = I.parse_announcements(H.fetch_announcements())
        self.assertGreaterEqual(len(items), 1)
        self.assertTrue(all(i["title"] and i["url"] for i in items))


class TestLiveHealth(unittest.TestCase):
    def test_health_ok(self):
        result = H.health_check()
        self.assertEqual(result["status"], "ok", result)


if __name__ == "__main__":
    unittest.main()
