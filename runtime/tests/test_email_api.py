import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from jahids_runtime.auth import OwnerAuthenticator
from jahids_runtime.server import Handler


class EmailApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.service = object()
        Handler.authenticator = OwnerAuthenticator("e" * 48)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()

    def post(self, token, body):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        connection.request("POST", "/v1/email/send", json.dumps(body), headers)
        response = connection.getresponse()
        payload = response.read()
        status = response.status
        connection.close()
        return status, payload

    def test_email_endpoint_requires_owner_token(self):
        status, _ = self.post(None, {"to": "owner@example.test", "subject": "Hi", "text": "Hello"})
        self.assertEqual(status, 401)

    @patch("jahids_runtime.server.SmtpMailer.send")
    def test_email_endpoint_uses_configured_smtp_adapter(self, send):
        send.return_value = {"status": "sent", "to": "owner@example.test", "from": "admin@example.test"}
        status, payload = self.post("e" * 48, {"to": "owner@example.test", "subject": "Hi", "text": "Hello"})
        self.assertEqual(status, 200)
        self.assertIn(b'"status": "sent"', payload)
        send.assert_called_once_with("owner@example.test", "Hi", "Hello")


if __name__ == "__main__":
    unittest.main()
