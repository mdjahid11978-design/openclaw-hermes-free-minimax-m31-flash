"""Local-first HTTP API and web console; mission data requires owner bearer auth."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .auth import OwnerAuthenticator
from .email import EmailConfigurationError, EmailDeliveryError, SmtpMailer
from .service import MissionService


class Handler(BaseHTTPRequestHandler):
    service = None
    authenticator = None

    def send_json(self, status, payload):
        data = json.dumps(payload, default=str).encode()
        self.send_response(status)
        for key, value in {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(data)),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
        }.items():
            self.send_header(key, value)
        if status == 401:
            self.send_header("WWW-Authenticate", "Bearer")
        self.end_headers()
        self.wfile.write(data)

    def send_console(self):
        default_dir = Path(__file__).resolve().parents[2] / "web"
        console_dir = Path(os.getenv("JAHIDS_WEB_DIR", str(default_dir))).resolve()
        console = console_dir / "index.html"
        try:
            data = console.read_bytes()
        except OSError:
            return self.send_json(503, {"error": "control_center_not_installed"})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(data)

    def authorized(self):
        return self.authenticator is not None and self.authenticator.authenticate(
            self.headers.get("Authorization")
        )

    def body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > 16000:
            raise ValueError("request body exceeds 16000 bytes")
        if length == 0:
            return {}
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            return self.send_console()
        if path == "/healthz":
            return self.send_json(
                200,
                {"status": "ok", "service": "jahids-agent-runtime", "version": "0.2.0"},
            )
        if not self.authorized():
            return self.send_json(401, {"error": "unauthorized"})
        if path == "/v1/status":
            return self.send_json(
                200,
                {
                    "status": "ok",
                    "service": "jahids-agent-runtime",
                    "version": "0.2.0",
                    "autonomy_level": self.service.governor.autonomy_level,
                    "allowed_categories": ["model", "read", "analysis"],
                    "blocked_categories": sorted(self.service.governor.BLOCKED_CATEGORIES),
                    "smtp_configured": SmtpMailer().is_configured(),
                },
            )
        if path == "/v1/missions":
            return self.send_json(200, {"missions": self.service.store.list()})
        if path.startswith("/v1/missions/") and path.endswith("/events"):
            parts = path.strip("/").split("/")
            if len(parts) != 4 or parts[:2] != ["v1", "missions"]:
                return self.send_json(404, {"error": "not_found"})
            mission = self.service.store.get(parts[2])
            if not mission:
                return self.send_json(404, {"error": "not_found"})
            return self.send_json(200, {"events": self.service.store.list_audit_events(parts[2])})
        if path.startswith("/v1/missions/"):
            mission = self.service.store.get(path.rsplit("/", 1)[-1])
            return self.send_json(200 if mission else 404, mission or {"error": "not_found"})
        return self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if not self.authorized():
            return self.send_json(401, {"error": "unauthorized"})
        path = urlparse(self.path).path
        try:
            body = self.body()
            if path == "/v1/email/send":
                try:
                    result = SmtpMailer().send(
                        body.get("to", ""),
                        body.get("subject", ""),
                        body.get("text", ""),
                    )
                    return self.send_json(200, result)
                except PermissionError as exc:
                    return self.send_json(403, {"error": str(exc)})
                except EmailConfigurationError as exc:
                    return self.send_json(503, {"error": str(exc)})
                except (ValueError, EmailDeliveryError) as exc:
                    return self.send_json(400 if isinstance(exc, ValueError) else 502, {"error": str(exc)})
            if path == "/v1/missions":
                mission = self.service.create(
                    body.get("provider", "nvidia-nim"),
                    body.get("prompt", ""),
                    body.get("category", "model"),
                )
                return self.send_json(
                    201,
                    {
                        "mission": mission,
                        "next": "POST /v1/missions/{id}/approve then /execute",
                    },
                )
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["v1", "missions"]:
                if parts[3] == "approve":
                    result = self.service.approve(parts[2])
                elif parts[3] == "execute":
                    result = self.service.execute(parts[2], body.get("approval_id", ""))
                else:
                    result = False
                if result is None or result is False:
                    return self.send_json(404, {"error": "not_found"})
                decision = result.get("decision", {}) if isinstance(result, dict) else {}
                status = 200 if decision.get("allowed", True) else 403
                return self.send_json(status, result)
            return self.send_json(404, {"error": "not_found"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})

    def log_message(self, fmt, *args):
        print("jahids-runtime", self.address_string(), fmt % args)


def main():
    try:
        Handler.authenticator = OwnerAuthenticator.from_environment()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    host = os.getenv("JAHIDS_HOST", "127.0.0.1")
    port = int(os.getenv("JAHIDS_PORT", "8787"))
    if host not in {"127.0.0.1", "localhost"} and os.getenv("JAHIDS_ALLOW_REMOTE_BIND") != "true":
        raise SystemExit("remote bind blocked; expose only behind a trusted TLS reverse proxy")
    Handler.service = MissionService()
    server = ThreadingHTTPServer((host, port), Handler)
    print("JAHIDS.AI Agent Runtime listening on " + host + ":" + str(port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
