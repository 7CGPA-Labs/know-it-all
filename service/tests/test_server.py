import unittest

try:
    from fastapi.testclient import TestClient
    from service.server import app
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False

class TestServerEndpoints(unittest.TestCase):
    def setUp(self):
        if HAS_TESTCLIENT:
            self.client = TestClient(app)

    def test_health(self):
        if not HAS_TESTCLIENT:
            self.skipTest("FastAPI TestClient unavailable in base environment")
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "gedit-research-daemon")

    def test_render_md(self):
        if not HAS_TESTCLIENT:
            self.skipTest("FastAPI TestClient unavailable in base environment")
        payload = {"markdown": "# Heading 1\n- Item A\n- Item B"}
        response = self.client.post("/render-md", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("html", data)
        self.assertIn("Heading 1", data["html"])
        self.assertIn("<li>Item A</li>", data["html"])

    def test_scrape_and_summarize_invalid_url(self):
        if not HAS_TESTCLIENT:
            self.skipTest("FastAPI TestClient unavailable in base environment")
        payload = {"url": "https://invalid-non-existent-domain-12345.org", "query": "Test"}
        response = self.client.post("/scrape-and-summarize", json=payload)
        self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main()
