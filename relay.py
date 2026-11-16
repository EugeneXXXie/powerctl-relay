import hashlib
import hmac
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return "pbkdf2_sha256$200000$%s$%s" % (salt.hex(), digest.hex())


def password_matches(password, stored):
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def magic_packet(mac):
    parts = mac.replace("-", ":").split(":")
    if len(parts) != 6:
        raise ValueError("mac must have 6 bytes")
    hardware = bytes(int(part, 16) for part in parts)
    return b"\xff" * 6 + hardware * 16


def handle_request(method, path, headers, body, password_hash, machines, probe_health, send_magic, send_shutdown):
    if not _authorized(headers, password_hash):
        return 401, json.dumps({"ok": False})
    if method == "GET" and path == "/status":
        return 200, json.dumps({"machines": [_status(machine, probe_health) for machine in machines]})
    if method == "POST" and path == "/power":
        command = json.loads(body or "{}")
        machine = next((item for item in machines if item["id"] == command.get("id")), None)
        if machine is None:
            return 404, json.dumps({"ok": False})
        action = command.get("action")
        if action == "on":
            send_magic(machine["mac"])
            return 200, json.dumps({"ok": True, "id": machine["id"], "action": "on"})
        if action == "off":
            send_shutdown(machine)
            return 200, json.dumps({"ok": True, "id": machine["id"], "action": "off"})
        return 400, json.dumps({"ok": False})
    return 404, json.dumps({"ok": False})


def _status(machine, probe_health):
    health = probe_health(machine)
    if not health:
        return {"id": machine["id"], "name": machine["name"], "state": "off", "os": None}
    return {
        "id": machine["id"],
        "name": machine["name"],
        "state": "on",
        "os": health.get("os"),
    }


def _authorized(headers, password_hash):
    header = ""
    for key, value in headers.items():
        if key.lower() == "authorization":
            header = value
            break
    prefix = "Bearer "
    if not header.startswith(prefix):
        return False
    return password_matches(header[len(prefix):], password_hash)


def probe_health(machine):
    request = urllib.request.Request(
        machine["agent_url"].rstrip("/") + "/health",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def send_magic(mac):
    packet = magic_packet(mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, ("255.255.255.255", 9))


def send_shutdown(machine):
    payload = b"{}"
    request = urllib.request.Request(
        machine["agent_url"].rstrip("/") + "/shutdown",
        data=payload,
        headers={
            "Authorization": "Bearer %s" % machine["agent_secret"],
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        response.read()


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not data.get("password_hash") or data["password_hash"] == "change-me":
        raise SystemExit("set password_hash in %s" % path)
    return data


def serve(config):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._dispatch(None)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            self._dispatch(raw)

        def _dispatch(self, body):
            status, payload = handle_request(
                self.command,
                self.path.split("?", 1)[0],
                self.headers,
                body,
                config["password_hash"],
                config["machines"],
                probe_health,
                send_magic,
                send_shutdown,
            )
            encoded = payload.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, fmt, *args):
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    server = ThreadingHTTPServer((config.get("listen", "0.0.0.0"), int(config.get("port", 8787))), Handler)
    print("relay listening on %s:%s" % (config.get("listen", "0.0.0.0"), config.get("port", 8787)))
    server.serve_forever()


def main(argv):
    if len(argv) >= 2 and argv[1] == "--hash":
        print(hash_password(argv[2] if len(argv) > 2 else sys.stdin.readline().strip()))
        return
    config_path = "/data/config.json"
    if "--config" in argv:
        config_path = argv[argv.index("--config") + 1]
    serve(load_config(config_path))


if __name__ == "__main__":
    main(sys.argv)
