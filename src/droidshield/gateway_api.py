from __future__ import annotations

import json
import threading
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from droidshield.gateway import NodeRegistration, SandboxGateway


class GatewayApiServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        gateway: SandboxGateway | None = None,
    ) -> None:
        super().__init__(server_address, GatewayApiHandler)
        self.gateway = gateway or SandboxGateway()


def serve_gateway_api(
    host: str = "127.0.0.1",
    port: int = 8770,
    *,
    gateway: SandboxGateway | None = None,
) -> str:
    server = GatewayApiServer((host, port), gateway)
    url = f"http://{host}:{server.server_port}"
    try:
        print(f"DroidShield gateway API running at {url}")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return url


def start_gateway_api_thread(
    host: str = "127.0.0.1",
    port: int = 0,
    *,
    gateway: SandboxGateway | None = None,
) -> tuple[GatewayApiServer, str]:
    server = GatewayApiServer((host, port), gateway)
    url = f"http://{host}:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, url


class GatewayApiHandler(BaseHTTPRequestHandler):
    server_version = "DroidShieldGateway/0.1"

    @property
    def gateway(self) -> SandboxGateway:
        return self.server.gateway  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature.
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/v1/tasks/"):
            job_id = parsed.path.removeprefix("/api/v1/tasks/").strip("/")
            job = self.gateway.get_job(job_id)
            if job is None:
                self._send_json({"error": "job not found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(job.to_api_response())
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self._read_json_body()
        if parsed.path == "/api/v1/tasks":
            if not isinstance(body.get("command"), str) or not body["command"].strip():
                self._send_json({"error": "command is required"}, HTTPStatus.BAD_REQUEST)
                return
            job = self.gateway.submit_api_task(body)
            self._send_json({"job_id": job.job_id, "status": job.status}, HTTPStatus.ACCEPTED)
            return
        if parsed.path == "/api/v1/nodes/register":
            registration = self._parse_registration(body)
            if registration is None:
                self._send_json({"error": "node_id, device_model, runtime, and capabilities are required"}, HTTPStatus.BAD_REQUEST)
                return
            node = self.gateway.register_node(registration)
            self._send_json({"node_id": node.node_id, "status": "registered", "capabilities": list(node.capabilities)})
            return
        if parsed.path.startswith("/api/v1/jobs/") and parsed.path.endswith("/kill"):
            job_id = parsed.path.removeprefix("/api/v1/jobs/").removesuffix("/kill").strip("/")
            reason = str(body.get("reason") or "manual_operator_action")
            job = self.gateway.kill_job(job_id, reason)
            if job is None:
                self._send_json({"error": "job not found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json({"job_id": job.job_id, "status": job.status, "reason": job.kill_reason})
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0") or "0")
        if length == 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _parse_registration(self, payload: dict[str, Any]) -> NodeRegistration | None:
        capabilities = payload.get("capabilities")
        if not isinstance(capabilities, list) or not all(isinstance(item, str) for item in capabilities):
            return None
        required = (payload.get("node_id"), payload.get("device_model"), payload.get("runtime"))
        if not all(isinstance(value, str) and value.strip() for value in required):
            return None
        return NodeRegistration(
            node_id=str(payload["node_id"]),
            device_model=str(payload["device_model"]),
            runtime=str(payload["runtime"]),
            capabilities=tuple(capabilities),
        )

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def node_registration_from_api(payload: dict[str, Any]) -> NodeRegistration:
    return NodeRegistration(
        node_id=str(payload["node_id"]),
        device_model=str(payload["device_model"]),
        runtime=str(payload["runtime"]),
        capabilities=tuple(str(capability) for capability in payload["capabilities"]),
    )


def registration_to_api(registration: NodeRegistration) -> dict[str, Any]:
    payload = asdict(registration)
    payload["capabilities"] = list(registration.capabilities)
    return payload
