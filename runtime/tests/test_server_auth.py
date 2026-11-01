import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer

from jahids_runtime.auth import OwnerAuthenticator
from jahids_runtime.server import Handler

class FakeStore:
    def list(self):
        return []
    def get(self, mission_id):
        return None

class FakeService:
    store = FakeStore()

class HttpOwnerAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.service = FakeService()
        Handler.authenticator = OwnerAuthenticator("t" * 48)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()

    def request(self, method, path, token=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        status = response.status
        response_headers = dict(response.getheaders())
        connection.close()
        return status, payload, response_headers

    def test_health_is_minimal_and_public(self):
        status, payload, headers = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertIn(b'"status": "ok"', payload)
        self.assertEqual(headers.get("Cache-Control"), "no-store")

    def test_mission_reads_require_owner_token(self):
        status, _, headers = self.request("GET", "/v1/missions")
        self.assertEqual(status, 401)
        self.assertEqual(headers.get("WWW-Authenticate"), "Bearer")
        status, payload, _ = self.request("GET", "/v1/missions", "t" * 48)
        self.assertEqual(status, 200)
        self.assertIn(b'"missions": []', payload)

    def test_mission_writes_require_owner_token(self):
        status, _, _ = self.request("POST", "/v1/missions", body='{"prompt":"test"}')
        self.assertEqual(status, 401)

if __name__ == "__main__":
    unittest.main()
