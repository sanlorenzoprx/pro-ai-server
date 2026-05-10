from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from droidshield.diagnostics import build_diagnostics_report
from droidshield.ide import detect_continue_extension_status, detect_ide_clis
from droidshield.ollama import assess_ollama_server_status, build_ollama_tags_command
from droidshield.status import build_status_report
from droidshield.termux_scripts import generate_termux_scripts, write_termux_scripts


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_KNOWLEDGE_API_BASE = "http://127.0.0.1:8766"

mimetypes.add_type("application/manifest+json", ".webmanifest")


@dataclass(frozen=True)
class UiActionResult:
    ok: bool
    message: str
    output: str = ""


def build_status_payload(api_base: str = "http://localhost:11434") -> dict[str, Any]:
    from droidshield import cli

    adb = cli.resolve_adb()
    adb_devices_output = cli.run_optional_command([adb, "devices"]) if adb else None
    adb_forward_output = cli.run_optional_command([adb, "forward", "--list"]) if adb else None
    tags_output = cli.run_optional_command(list(build_ollama_tags_command(api_base)))
    ollama_status = assess_ollama_server_status(tags_output)
    ide_statuses = tuple(detect_continue_extension_status(ide) for ide in detect_ide_clis())
    report = build_status_report(
        adb_devices_output,
        adb_forward_output,
        ollama_status,
        ide_statuses,
        adb_path=adb,
    )
    return {
        "ok": report.ok,
        "items": [asdict(item) for item in report.items],
        "models": list(ollama_status.model_names),
        "warnings": list(ollama_status.warnings),
    }


def build_endpoints_payload(
    ollama_api_base: str = "http://127.0.0.1:11434",
    native_api_base: str | None = None,
) -> dict[str, Any]:
    from droidshield import cli

    ollama_base = ollama_api_base.rstrip("/")
    tags_output = cli.run_optional_command(list(build_ollama_tags_command(ollama_base)))
    ollama_status = assess_ollama_server_status(tags_output)
    payload: dict[str, Any] = {
        "ollama": {
            "base": ollama_base,
            "modelsUrl": f"{ollama_base}/api/tags",
            "generateUrl": f"{ollama_base}/api/generate",
            "ok": ollama_status.ok,
            "models": list(ollama_status.model_names),
            "warnings": list(ollama_status.warnings),
        },
        "native": None,
    }

    if native_api_base:
        native_base = native_api_base.rstrip("/")
        health_output = cli.run_optional_command(list(cli._build_native_endpoint_health_command(native_base)))
        models_output = cli.run_optional_command(list(cli._build_native_endpoint_models_command(native_base)))
        payload["native"] = {
            "base": native_base,
            "healthUrl": f"{native_base}/health",
            "modelsUrl": f"{native_base}/v1/models",
            "completionUrl": f"{native_base}/completion",
            "ok": cli._native_llamacpp_health_ok(health_output),
            "loading": cli._native_llamacpp_health_loading(health_output),
            "models": list(cli._native_llamacpp_model_names(models_output)),
            "healthResponse": health_output.strip(),
        }

    return payload


def create_usb_tunnel(serial: str | None = None) -> UiActionResult:
    from droidshield import cli

    adb = cli.resolve_adb()
    if not adb:
        return UiActionResult(False, "adb was not found.")
    try:
        selected_serial = cli.select_device_serial(adb, serial or None)
        outputs = [
            cli.run_command(cli.adb_command(adb, ["forward", "tcp:11434", "tcp:11434"], selected_serial)),
            cli.run_command(cli.adb_command(adb, ["forward", "tcp:8766", "tcp:8766"], selected_serial)),
        ]
    except Exception as exc:  # noqa: BLE001 - UI action should return a visible failure.
        return UiActionResult(False, str(exc))
    return UiActionResult(True, f"USB tunnel active for {selected_serial}.", "\n".join(filter(None, outputs)))


def generate_scripts_action(mode: str, profile: str, output_dir: str) -> UiActionResult:
    try:
        bundle = generate_termux_scripts(profile_name_to_chat(profile), profile_name_to_autocomplete(profile), mode=mode)
        written = write_termux_scripts(bundle, root=Path(output_dir))
    except Exception as exc:  # noqa: BLE001 - UI action should return a visible failure.
        return UiActionResult(False, str(exc))
    output = "\n".join(str(path) for path in written)
    return UiActionResult(True, f"Generated {len(written)} Termux files for {mode} mode.", output)


def profile_name_to_chat(profile: str) -> str:
    from droidshield.models import model_plan_for_profile

    return model_plan_for_profile(profile).chat_model


def profile_name_to_autocomplete(profile: str) -> str:
    from droidshield.models import model_plan_for_profile

    return model_plan_for_profile(profile).autocomplete_model


def build_diagnostics_payload() -> dict[str, str]:
    from droidshield import cli

    return {"text": build_diagnostics_report(cli.resolve_adb()).text}


def build_knowledge_payload(api_base: str = DEFAULT_KNOWLEDGE_API_BASE) -> dict[str, Any]:
    base = api_base.rstrip("/")
    try:
        payload = _request_phone_knowledge_json(f"{base}/api/knowledge/status")
    except OSError as exc:
        return {
            "ok": False,
            "hostedOn": "phone",
            "apiBase": base,
            "message": f"Phone knowledge server is not reachable: {exc}",
        }
    payload["apiBase"] = base
    return payload


def trigger_phone_knowledge_ingest(api_base: str = DEFAULT_KNOWLEDGE_API_BASE) -> dict[str, Any]:
    base = api_base.rstrip("/")
    try:
        return _request_phone_knowledge_json(f"{base}/api/knowledge/ingest", method="POST")
    except OSError as exc:
        return {"ok": False, "message": f"Phone knowledge ingest failed: {exc}"}


def add_phone_knowledge_source(
    filename: str,
    content: str,
    api_base: str = DEFAULT_KNOWLEDGE_API_BASE,
) -> dict[str, Any]:
    base = api_base.rstrip("/")
    if not filename.lower().endswith(".md"):
        return {"ok": False, "message": "Choose a markdown file ending in .md."}
    if not content.strip():
        return {"ok": False, "message": "The selected markdown file is empty."}
    try:
        return _request_phone_knowledge_json(
            f"{base}/api/knowledge/sources",
            method="POST",
            body={"filename": filename, "content": content, "ingest": True},
        )
    except OSError as exc:
        return {"ok": False, "message": f"Phone knowledge upload failed: {exc}"}


def add_phone_quick_capture(
    content: str,
    api_base: str = DEFAULT_KNOWLEDGE_API_BASE,
) -> dict[str, Any]:
    base = api_base.rstrip("/")
    if not content.strip():
        return {"ok": False, "message": "Capture text is required."}
    try:
        return _request_phone_knowledge_json(
            f"{base}/api/knowledge/captures",
            method="POST",
            body={"content": content},
        )
    except OSError as exc:
        return {"ok": False, "message": f"Phone quick capture failed: {exc}"}


def trigger_phone_knowledge_feedback(
    kind: str,
    api_base: str = DEFAULT_KNOWLEDGE_API_BASE,
) -> dict[str, Any]:
    base = api_base.rstrip("/")
    if kind not in {"daily", "weekly"}:
        return {"ok": False, "message": "Unknown feedback kind."}
    try:
        return _request_phone_knowledge_json(f"{base}/api/knowledge/{kind}", method="POST")
    except OSError as exc:
        return {"ok": False, "message": f"Phone {kind} feedback failed: {exc}"}


def read_phone_knowledge_page(
    path: str,
    api_base: str = DEFAULT_KNOWLEDGE_API_BASE,
) -> dict[str, Any]:
    base = api_base.rstrip("/")
    if not path.strip():
        return {"ok": False, "message": "Page path is required."}
    try:
        return _request_phone_knowledge_json(f"{base}/api/knowledge/pages?path={quote(path, safe='')}")
    except OSError as exc:
        return {"ok": False, "message": f"Phone knowledge page read failed: {exc}"}


def _request_phone_knowledge_json(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, method=method)
    if body is not None:
        request.add_header("content-type", "application/json")
    with urlopen(request, timeout=4) as response:  # noqa: S310 - local phone-forwarded control API.
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {"ok": False, "message": "Unexpected phone response."}


def serve_ui(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *, open_browser: bool = True) -> str:
    server = ThreadingHTTPServer((host, port), UiRequestHandler)
    url = f"http://{host}:{server.server_port}"
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        print(f"DroidShield UI running at {url}")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return url


class UiRequestHandler(BaseHTTPRequestHandler):
    server_version = "DroidShieldUI/0.1"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature.
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            query = parse_qs(parsed.query)
            api_base = _first_query_value(query, "apiBase", "http://localhost:11434")
            self._send_json(build_status_payload(api_base))
            return
        if parsed.path == "/api/endpoints":
            query = parse_qs(parsed.query)
            ollama_base = _first_query_value(query, "ollamaApiBase", "http://127.0.0.1:11434")
            native_base = _optional_query_value(query, "nativeApiBase")
            self._send_json(build_endpoints_payload(ollama_base, native_base))
            return
        if parsed.path == "/api/diagnostics":
            self._send_json(build_diagnostics_payload())
            return
        if parsed.path == "/api/knowledge":
            query = parse_qs(parsed.query)
            api_base = _first_query_value(query, "apiBase", DEFAULT_KNOWLEDGE_API_BASE)
            self._send_json(build_knowledge_payload(api_base))
            return
        if parsed.path == "/api/knowledge/page":
            query = parse_qs(parsed.query)
            api_base = _first_query_value(query, "apiBase", DEFAULT_KNOWLEDGE_API_BASE)
            path = _first_query_value(query, "path", "")
            self._send_json(read_phone_knowledge_page(path, api_base))
            return
        self._send_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self._read_json_body()
        if parsed.path == "/api/actions/tunnel":
            self._send_json(asdict(create_usb_tunnel(body.get("serial") or None)))
            return
        if parsed.path == "/api/actions/generate-scripts":
            mode = str(body.get("mode") or "usb")
            profile = str(body.get("profile") or "professional")
            output_dir = str(body.get("outputDir") or ".")
            self._send_json(asdict(generate_scripts_action(mode, profile, output_dir)))
            return
        if parsed.path == "/api/actions/knowledge-ingest":
            api_base = str(body.get("apiBase") or DEFAULT_KNOWLEDGE_API_BASE)
            self._send_json(trigger_phone_knowledge_ingest(api_base))
            return
        if parsed.path == "/api/actions/knowledge-add-source":
            filename = str(body.get("filename") or "")
            content = str(body.get("content") or "")
            api_base = str(body.get("apiBase") or DEFAULT_KNOWLEDGE_API_BASE)
            self._send_json(add_phone_knowledge_source(filename, content, api_base))
            return
        if parsed.path == "/api/actions/knowledge-quick-capture":
            content = str(body.get("content") or "")
            api_base = str(body.get("apiBase") or DEFAULT_KNOWLEDGE_API_BASE)
            self._send_json(add_phone_quick_capture(content, api_base))
            return
        if parsed.path == "/api/actions/knowledge-feedback":
            kind = str(body.get("kind") or "")
            api_base = str(body.get("apiBase") or DEFAULT_KNOWLEDGE_API_BASE)
            self._send_json(trigger_phone_knowledge_feedback(kind, api_base))
            return
        self._send_json({"ok": False, "message": "Unknown action."}, HTTPStatus.NOT_FOUND)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0") or "0")
        if length == 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _send_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        if ".." in Path(relative).parts:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        resource = files("droidshield") / "ui" / relative
        if not resource.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = resource.read_bytes()
        content_type = mimetypes.guess_type(relative)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def _first_query_value(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key)
    return values[0] if values and values[0] else default


def _optional_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    return values[0] if values and values[0] else None
