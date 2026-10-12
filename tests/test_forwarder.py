import json
import unittest

from app import ForwarderSettings, create_app


class FakeResponse:
    def raise_for_status(self):
        pass


class ForwarderTests(unittest.TestCase):
    def setUp(self):
        self.sent = []

        def fake_send(url, **kwargs):
            self.sent.append((url, kwargs))
            return FakeResponse()

        self.client = create_app(
            ForwarderSettings("test-token", "-123", "shared-secret"), http_post=fake_send
        ).test_client()

    def test_anonymous_requests_are_rejected(self):
        self.assertEqual(self.client.post("/forward", data="BTC").status_code, 401)
        self.assertEqual(self.sent, [])

    def test_header_authentication(self):
        response = self.client.post(
            "/forward", data="BTC", headers={"X-Webhook-Token": "shared-secret"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.sent[0][1]["json"]["text"], "BTC")

    def test_body_authentication_strips_relay_secret(self):
        payload = {"relay_secret": "shared-secret", "id": 1, "secret": "user-key"}
        response = self.client.post("/forward", json=payload)
        self.assertEqual(response.status_code, 200)
        result = json.loads(self.sent[0][1]["json"]["text"])
        self.assertNotIn("relay_secret", result)
        self.assertEqual(result["secret"], "user-key")

    def test_unconfigured_forwarder_does_not_send(self):
        client = create_app(ForwarderSettings("", "", "")).test_client()
        self.assertEqual(client.post("/forward").status_code, 503)

    def test_oversize_is_rejected(self):
        response = self.client.post(
            "/forward", data="x" * 9000, headers={"X-Webhook-Token": "shared-secret"}
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
