import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer

from jahids_runtime.auth import OwnerAuthenticator
from jahids_runtime.server import Handler


class FakeGovernor:
    autonomy_level = 0
    BLOCKED_CATEGORIES = {"deploy", "finance", "credentials", "destructive", "legal", "ownership"}


class FakeStore:
    def list(self):
        return []

    def get(self, mission_id):
        return None


class FakeService:
    governor = FakeGovernor()
    store = FakeStore()


class ControlCenterHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.service = FakeService()
        Handler.authenticator = OwnerAuthenticator("c" * 48)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()

    def request(self, path, token=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read()
        result = (response.status, body, dict(response.getheaders()))
        connection.close()
        return result

    def test_control_center_is_served_without_api_credentials(self):
        status, body, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"JAHIDS.AI", body)
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertIn("connect-src 'self'", headers.get("Content-Security-Policy", ""))

    def test_runtime_status_requires_owner_authentication(self):
        status, _, headers = self.request("/v1/status")
        self.assertEqual(status, 401)
        self.assertEqual(headers.get("WWW-Authenticate"), "Bearer")

    def test_runtime_status_reports_governor_without_secrets(self):
        status, body, _ = self.request("/v1/status", "c" * 48)
        self.assertEqual(status, 200)
        self.assertIn(b'"autonomy_level": 0', body)
        self.assertIn(b'"blocked_categories"', body)
        self.assertNotIn(b"API_TOKEN", body)


if __name__ == "__main__":
    unittest.main()
