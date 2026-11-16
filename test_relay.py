import json
import unittest

from relay import handle_request, hash_password, magic_packet


class RelayTest(unittest.TestCase):
    def setUp(self):
        self.secret_hash = hash_password("secret")
        self.machines = [
            {
                "id": "desktop",
                "name": "台式机",
                "mac": "AA:BB:CC:DD:EE:FF",
                "agent_url": "http://192.0.2.10:8790",
                "agent_secret": "agent-secret",
            }
        ]
        self.sent = []

    def handle(self, method, path, headers, body=None, health=None):
        return handle_request(
            method,
            path,
            headers,
            body,
            password_hash=self.secret_hash,
            machines=self.machines,
            probe_health=health or (lambda machine: {"ok": True, "os": "windows"}),
            send_magic=lambda mac: self.sent.append(("wol", mac)),
            send_shutdown=lambda machine: self.sent.append(("off", machine["id"])),
        )

    def test_status_uses_agent_health(self):
        status, body = self.handle("GET", "/status", {"Authorization": "Bearer secret"})
        self.assertEqual(200, status)
        machine = json.loads(body)["machines"][0]
        self.assertEqual("on", machine["state"])
        self.assertEqual("windows", machine["os"])

    def test_unreachable_agent_is_off(self):
        status, body = self.handle(
            "GET",
            "/status",
            {"Authorization": "Bearer secret"},
            health=lambda machine: None,
        )
        machine = json.loads(body)["machines"][0]
        self.assertEqual(200, status)
        self.assertEqual("off", machine["state"])
        self.assertIsNone(machine["os"])

    def test_wrong_password_is_rejected(self):
        status, _ = self.handle("GET", "/status", {"Authorization": "Bearer no"})
        self.assertEqual(401, status)

    def test_power_on_sends_a_magic_packet(self):
        status, _ = self.handle(
            "POST",
            "/power",
            {"Authorization": "Bearer secret"},
            json.dumps({"id": "desktop", "action": "on"}),
        )
        self.assertEqual(200, status)
        self.assertEqual([("wol", "AA:BB:CC:DD:EE:FF")], self.sent)
        self.assertEqual(b"\xff" * 6 + bytes.fromhex("AABBCCDDEEFF") * 16, magic_packet("AA:BB:CC:DD:EE:FF"))

    def test_power_off_calls_the_agent(self):
        status, _ = self.handle(
            "POST",
            "/power",
            {"Authorization": "Bearer secret"},
            json.dumps({"id": "desktop", "action": "off"}),
        )
        self.assertEqual(200, status)
        self.assertEqual([("off", "desktop")], self.sent)


if __name__ == "__main__":
    unittest.main()
