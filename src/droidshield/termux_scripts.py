from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Mapping


VALID_MODES = {"usb", "lan", "tailscale"}
USB_OLLAMA_HOST = "127.0.0.1:11434"
NETWORK_OLLAMA_HOST = "0.0.0.0:11434"
DEFAULT_SCRIPT_DIR = Path("generated") / "termux"
WIDGET_SHORTCUT_PATH = Path(".shortcuts") / "Start DroidShield"
WIDGET_ICON_PATH = Path(".shortcuts") / "icons" / "Start DroidShield.png"
DEBIAN_OLLAMA_SETUP_SCRIPT = "setup-ollama-debian.sh"
KNOWLEDGE_SERVER_SCRIPT = "pro-ai-knowledge-server.py"
KNOWLEDGE_SERVER_PORT = 8766


@dataclass(frozen=True)
class TermuxScriptBundle:
    mode: str
    ollama_host: str
    files: Mapping[Path, str | bytes]


def ollama_host_for_mode(mode: str) -> str:
    normalized = mode.lower()
    if normalized not in VALID_MODES:
        modes = ", ".join(sorted(VALID_MODES))
        raise ValueError(f"Unsupported Termux mode '{mode}'. Expected one of: {modes}.")
    if normalized == "usb":
        return USB_OLLAMA_HOST
    return NETWORK_OLLAMA_HOST


def android_battery_optimization_checklist() -> list[str]:
    return [
        "Open Android Settings.",
        "Open Apps.",
        "Open Termux.",
        "Open Battery.",
        "Set battery usage to Unrestricted.",
        "OEM battery management can still vary; this checklist reduces interruptions but cannot guarantee background behavior on every phone.",
    ]


def termux_widget_instructions() -> str:
    return (
        "Install Termux:Widget, then place the generated shortcut at "
        "~/.shortcuts/Start DroidShield and its icon at "
        "~/.shortcuts/icons/Start DroidShield.png. Add the Termux:Widget shortcut "
        "manually to the Android home screen and choose Start DroidShield. "
        "If the icon was added after the shortcut, remove and add the shortcut again."
    )


def generate_bootstrap_script() -> str:
    return "\n".join(
        [
            "#!/data/data/com.termux/files/usr/bin/bash",
            "set -euo pipefail",
            "",
            "pkg update -y",
            "pkg install -y proot-distro curl termux-api python",
            "proot-distro install debian",
            "",
            'echo "Debian is installed."',
            'echo "Next, install Ollama inside Debian with:"',
            f'echo "  proot-distro login debian -- bash /data/data/com.termux/files/home/{DEBIAN_OLLAMA_SETUP_SCRIPT}"',
            'echo "Then start the server with:"',
            'echo "  ~/start-droidshield.sh"',
            "",
        ]
    )


def generate_debian_ollama_setup_script() -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "apt-get update",
            "apt-get install -y curl ca-certificates",
            "curl -fsSL https://ollama.com/install.sh | sh",
            "",
            'echo "Ollama installed inside Debian."',
            'echo "Exit Debian, then run ~/start-droidshield.sh from Termux."',
            "",
        ]
    )


def generate_start_script(mode: str = "usb") -> str:
    ollama_host = ollama_host_for_mode(mode)
    knowledge_host = "127.0.0.1" if mode == "usb" else "0.0.0.0"
    return "\n".join(
        [
            "#!/data/data/com.termux/files/usr/bin/bash",
            "set -euo pipefail",
            "",
            "if ! command -v termux-wake-lock >/dev/null 2>&1; then",
            '  echo "Missing termux-wake-lock from Termux:API." >&2',
            '  echo "Install it in Termux with: pkg install termux-api" >&2',
            '  echo "Also install the Termux:API Android app from the same source as Termux." >&2',
            "  exit 1",
            "fi",
            "",
            "if ! termux-wake-lock; then",
            '  echo "Unable to acquire wake lock through Termux:API / termux-wake-lock." >&2',
            '  echo "Confirm the Termux:API Android app is installed and accessible." >&2',
            "  exit 1",
            "fi",
            "",
            "mkdir -p \"$HOME/droidshield/logs\"",
            f"python \"$HOME/{KNOWLEDGE_SERVER_SCRIPT}\" --host {knowledge_host} --port {KNOWLEDGE_SERVER_PORT} "
            "> \"$HOME/droidshield/logs/knowledge-server.log\" 2>&1 &",
            "KNOWLEDGE_PID=$!",
            f"proot-distro login debian -- bash -lc 'export OLLAMA_HOST={ollama_host}; ollama serve' || true",
            "kill \"$KNOWLEDGE_PID\" >/dev/null 2>&1 || true",
            "",
        ]
    )


def generate_install_models_script(chat_model: str, autocomplete_model: str) -> str:
    models = list(dict.fromkeys([chat_model, autocomplete_model]))
    commands = [f"proot-distro login debian -- bash -lc 'ollama pull {model}'" for model in models]
    return "\n".join(
        [
            "#!/data/data/com.termux/files/usr/bin/bash",
            "set -euo pipefail",
            "",
            *commands,
            "",
        ]
    )


def generate_widget_shortcut_script() -> str:
    return "\n".join(
        [
            "#!/data/data/com.termux/files/usr/bin/bash",
            "set -euo pipefail",
            "",
            "~/start-droidshield.sh",
            "",
        ]
    )


def generate_knowledge_server_script() -> str:
    return r'''#!/data/data/com.termux/files/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


HOME = Path.home()
VAULT = HOME / "pro-ai-knowledge"
INBOX = VAULT / "inbox"
RAW = VAULT / "raw"
WIKI = VAULT / "wiki"
DB_PATH = VAULT / "knowledge.sqlite3"
BRAIN_PROFILE = VAULT / "PRO_AI_BRAIN.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def ensure_vault() -> None:
    for directory in (
        INBOX,
        RAW,
        WIKI,
        WIKI / "sources",
        WIKI / "entities",
        WIKI / "concepts",
        WIKI / "questions",
        WIKI / "ideas",
        WIKI / "projects",
        WIKI / "daily",
        WIKI / "weekly",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    if not BRAIN_PROFILE.exists():
        BRAIN_PROFILE.write_text(
            "# Pro AI 2nd Brain\n\n"
            "## Who I Am\n\n"
            "Name: \n"
            "Work: \n"
            "Focus: \n"
            "Goals: \n\n"
            "## Current Projects\n\n"
            "Active: \n"
            "Stuck on: \n"
            "Next milestone: \n\n"
            "## What I Want From This Brain\n\n"
            "- Surface connections I have not noticed.\n"
            "- Challenge stale assumptions.\n"
            "- Flag contradictions across sources and notes.\n"
            "- Turn saved material into daily and weekly thinking prompts.\n",
            encoding="utf-8",
        )
    (WIKI / "index.md").write_text(
        "# Pro AI Knowledge Wiki\n\n"
        "This phone-hosted wiki is maintained from immutable files in `raw/`.\n\n"
        "## Source Summaries\n\n",
        encoding="utf-8",
    ) if not (WIKI / "index.md").exists() else None
    (WIKI / "maintenance-log.md").write_text("# Maintenance Log\n\n", encoding="utf-8") if not (
        WIKI / "maintenance-log.md"
    ).exists() else None


def connect() -> sqlite3.Connection:
    ensure_vault()
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        "CREATE TABLE IF NOT EXISTS sources ("
        "id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE, title TEXT NOT NULL, "
        "sha256 TEXT NOT NULL, imported_at TEXT NOT NULL)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS chunks ("
        "id TEXT PRIMARY KEY, source_id TEXT NOT NULL, chunk_index INTEGER NOT NULL, "
        "content TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES sources(id))"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS pages ("
        "path TEXT PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5("
        "content, source_id UNINDEXED, chunk_id UNINDEXED)"
    )
    db.commit()
    return db


def chunk_text(text: str, size: int = 900) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > size:
            chunks.append(current)
            current = paragraph
        else:
            current = paragraph if not current else current + "\n\n" + paragraph
    if current:
        chunks.append(current)
    return chunks or ([text.strip()] if text.strip() else [])


def title_from_path(path: Path) -> str:
    first_line = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
    if first_line and first_line[0].startswith("#"):
        return first_line[0].lstrip("#").strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def summarize(text: str, max_chars: int = 700) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rsplit(" ", 1)[0] + "..."


def ingest_raw_file(path: Path) -> dict[str, object]:
    ensure_vault()
    text = path.read_text(encoding="utf-8", errors="ignore")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    source_id = digest[:16]
    title = title_from_path(path)
    source_page = WIKI / "sources" / f"{slugify(title)}.md"
    chunks = chunk_text(text)
    now = utc_now()

    with connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO sources(id, path, title, sha256, imported_at) VALUES (?, ?, ?, ?, ?)",
            (source_id, str(path.relative_to(VAULT)), title, digest, now),
        )
        db.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
        db.execute("DELETE FROM chunk_fts WHERE source_id = ?", (source_id,))
        for index, chunk in enumerate(chunks):
            chunk_id = f"{source_id}-{index}"
            db.execute(
                "INSERT INTO chunks(id, source_id, chunk_index, content) VALUES (?, ?, ?, ?)",
                (chunk_id, source_id, index, chunk),
            )
            db.execute(
                "INSERT INTO chunk_fts(content, source_id, chunk_id) VALUES (?, ?, ?)",
                (chunk, source_id, chunk_id),
            )
        db.execute(
            "INSERT OR REPLACE INTO pages(path, title, kind, updated_at) VALUES (?, ?, ?, ?)",
            (str(source_page.relative_to(VAULT)), title, "source", now),
        )

    source_page.write_text(
        f"# {title}\n\n"
        f"Source: [[raw/{path.name}]]\n\n"
        f"Imported: {now}\n\n"
        "## Summary\n\n"
        f"{summarize(text)}\n\n"
        "## Claims And Notes\n\n"
        "- Pending LLM expansion.\n\n"
        "## Citations\n\n"
        f"- Source file: `raw/{path.name}`\n",
        encoding="utf-8",
    )
    append_index(title, source_page)
    append_log(f"Ingested {path.name} into {source_page.relative_to(VAULT)}")
    return {"sourceId": source_id, "title": title, "chunks": len(chunks), "page": str(source_page.relative_to(VAULT))}


def add_source(filename: str, content: str, ingest: bool = True) -> dict[str, object]:
    ensure_vault()
    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".md"):
        safe_name = f"{slugify(Path(safe_name).stem)}.md"
    if not safe_name or safe_name == ".md":
        safe_name = f"source-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
    path = RAW / safe_name
    path.write_text(content, encoding="utf-8", newline="\n")
    append_log(f"Added raw source {safe_name}")
    payload: dict[str, object] = {"ok": True, "path": str(path.relative_to(VAULT)), "bytes": len(content.encode("utf-8"))}
    if ingest:
        payload["ingest"] = ingest_raw_file(path)
    return payload


def quick_capture(content: str) -> dict[str, object]:
    ensure_vault()
    now = datetime.now(timezone.utc)
    filename = f"quick-capture-{now.strftime('%Y%m%d-%H%M%S')}.md"
    path = INBOX / filename
    text = content.strip()
    path.write_text(
        "# Quick Capture\n\n"
        f"Date: {utc_now()}\n"
        "Source: Desktop quick capture\n\n"
        f"{text}\n",
        encoding="utf-8",
        newline="\n",
    )
    append_log(f"Captured inbox note {filename}")
    return {"ok": True, "path": str(path.relative_to(VAULT)), "bytes": len(text.encode("utf-8"))}


def append_index(title: str, source_page: Path) -> None:
    index = WIKI / "index.md"
    entry = f"- [[{source_page.relative_to(VAULT).as_posix()}|{title}]]\n"
    current = index.read_text(encoding="utf-8")
    if entry not in current:
        index.write_text(current + entry, encoding="utf-8")


def append_log(message: str) -> None:
    log = WIKI / "maintenance-log.md"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"- {utc_now()} - {message}\n")


def ingest_all() -> list[dict[str, object]]:
    ensure_vault()
    results = []
    for path in sorted(RAW.glob("*.md")):
        results.append(ingest_raw_file(path))
    return results


def search(query: str, limit: int = 8) -> list[dict[str, object]]:
    if not query.strip():
        return []
    with connect() as db:
        rows = db.execute(
            "SELECT sources.title, sources.path, chunk_fts.content "
            "FROM chunk_fts JOIN sources ON sources.id = chunk_fts.source_id "
            "WHERE chunk_fts MATCH ? LIMIT ?",
            (query, limit),
        ).fetchall()
    return [{"title": title, "path": path, "excerpt": summarize(content, 260)} for title, path, content in rows]


def recent_sources(limit: int = 8) -> list[dict[str, str]]:
    with connect() as db:
        rows = db.execute(
            "SELECT title, path, imported_at FROM sources ORDER BY imported_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"title": title, "path": path, "importedAt": imported_at} for title, path, imported_at in rows]


def latest_page(kind: str) -> str | None:
    with connect() as db:
        row = db.execute(
            "SELECT path FROM pages WHERE kind = ? ORDER BY updated_at DESC LIMIT 1",
            (kind,),
        ).fetchone()
    return str(row[0]) if row else None


def source_snapshots(limit: int = 5) -> list[tuple[str, str, str]]:
    with connect() as db:
        rows = db.execute(
            "SELECT sources.title, sources.path, chunks.content "
            "FROM sources JOIN chunks ON chunks.source_id = sources.id "
            "WHERE chunks.chunk_index = 0 "
            "ORDER BY sources.imported_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [(title, path, content) for title, path, content in rows]


def make_daily_brief() -> dict[str, object]:
    ensure_vault()
    now = datetime.now(timezone.utc)
    page = WIKI / "daily" / f"{now.strftime('%Y-%m-%d')}.md"
    snapshots = source_snapshots()
    inbox_files = sorted(INBOX.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)[:5]
    source_lines = [
        f"- [[{path}|{title}]] - {summarize(content, 180)}"
        for title, path, content in snapshots
    ] or ["- No sources have been ingested yet."]
    inbox_lines = [f"- [[inbox/{path.name}|{path.stem}]]" for path in inbox_files] or ["- No quick captures yet."]
    connection_lines = []
    for index, (title, path, content) in enumerate(snapshots[:3], start=1):
        connection_lines.append(
            f"{index}. [[{path}|{title}]] may connect to your current work because it emphasizes: "
            f"{summarize(content, 140)}"
        )
    if not connection_lines:
        connection_lines.append("1. Add a few sources to start surfacing connections.")
    page.write_text(
        f"# Daily Brief - {now.strftime('%Y-%m-%d')}\n\n"
        "## Recent Sources\n\n"
        + "\n".join(source_lines)
        + "\n\n## Quick Captures\n\n"
        + "\n".join(inbox_lines)
        + "\n\n## Connections\n\n"
        + "\n".join(connection_lines)
        + "\n\n## Pattern\n\n"
        "Your 2nd Brain is beginning to reveal recurring themes across recent captures. "
        "As more notes arrive, this section should become sharper and more opinionated.\n\n"
        "## Question\n\n"
        "What idea keeps reappearing across what you are saving, and what would change if you acted on it this week?\n",
        encoding="utf-8",
    )
    now_text = utc_now()
    with connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO pages(path, title, kind, updated_at) VALUES (?, ?, ?, ?)",
            (str(page.relative_to(VAULT)), page.stem, "daily", now_text),
        )
    append_log(f"Created daily brief {page.relative_to(VAULT)}")
    return {"ok": True, "page": str(page.relative_to(VAULT))}


def make_weekly_synthesis() -> dict[str, object]:
    ensure_vault()
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    page = WIKI / "weekly" / f"{year}-W{week:02d}.md"
    snapshots = source_snapshots(10)
    source_lines = [
        f"- [[{path}|{title}]] - {summarize(content, 160)}"
        for title, path, content in snapshots
    ] or ["- No sources have been ingested yet."]
    page.write_text(
        f"# Weekly Synthesis - {year}-W{week:02d}\n\n"
        "## Emerging Thesis\n\n"
        "The strongest thesis will emerge as the vault accumulates more sources and quick captures.\n\n"
        "## Recent Evidence\n\n"
        + "\n".join(source_lines)
        + "\n\n## Contradictions To Check\n\n"
        "- Review recent sources against older assumptions in PRO_AI_BRAIN.md and project notes.\n\n"
        "## Knowledge Gaps\n\n"
        "- Add sources that challenge the current pattern, not only sources that confirm it.\n\n"
        "## One Action\n\n"
        "- Pick one recurring idea from this week and turn it into a project note or next step.\n",
        encoding="utf-8",
    )
    now_text = utc_now()
    with connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO pages(path, title, kind, updated_at) VALUES (?, ?, ?, ?)",
            (str(page.relative_to(VAULT)), page.stem, "weekly", now_text),
        )
    append_log(f"Created weekly synthesis {page.relative_to(VAULT)}")
    return {"ok": True, "page": str(page.relative_to(VAULT))}


def status() -> dict[str, object]:
    with connect() as db:
        source_count = db.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        chunk_count = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        page_count = db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    return {
        "ok": True,
        "hostedOn": "phone",
        "vault": str(VAULT),
        "database": str(DB_PATH),
        "sources": source_count,
        "chunks": chunk_count,
        "pages": page_count,
        "recentSources": recent_sources(),
        "latestDaily": latest_page("daily"),
        "latestWeekly": latest_page("weekly"),
    }


def read_page(relative_path: str) -> tuple[dict[str, object], HTTPStatus]:
    ensure_vault()
    if not relative_path or relative_path.startswith("/") or ".." in Path(relative_path).parts:
        return {"ok": False, "message": "Invalid page path."}, HTTPStatus.BAD_REQUEST
    page = (VAULT / relative_path).resolve()
    vault = VAULT.resolve()
    if vault not in page.parents or page.suffix.lower() != ".md":
        return {"ok": False, "message": "Invalid page path."}, HTTPStatus.BAD_REQUEST
    if not page.exists() or not page.is_file():
        return {"ok": False, "message": "Page not found."}, HTTPStatus.NOT_FOUND
    content = page.read_text(encoding="utf-8")
    title = page.stem
    for line in content.splitlines():
        if line.startswith("# "):
            title = line[2:].strip() or title
            break
    return {
        "ok": True,
        "path": str(page.relative_to(vault)),
        "title": title,
        "content": content,
    }, HTTPStatus.OK


class Handler(BaseHTTPRequestHandler):
    server_version = "ProAiKnowledge/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/knowledge/status":
            self.send_json(status())
            return
        if parsed.path == "/api/knowledge/search":
            query = parse_qs(parsed.query).get("q", [""])[0]
            self.send_json({"ok": True, "results": search(query)})
            return
        if parsed.path == "/api/knowledge/pages":
            path = parse_qs(parsed.query).get("path", [""])[0]
            payload, status_code = read_page(path)
            self.send_json(payload, status_code)
            return
        self.send_json({"ok": False, "message": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/knowledge/sources":
            payload = self.read_json()
            filename = str(payload.get("filename") or "source.md")
            content = payload.get("content")
            if not isinstance(content, str) or not content.strip():
                self.send_json({"ok": False, "message": "Markdown content is required."}, HTTPStatus.BAD_REQUEST)
                return
            ingest = bool(payload.get("ingest", True))
            self.send_json(add_source(filename, content, ingest))
            return
        if parsed.path == "/api/knowledge/captures":
            payload = self.read_json()
            content = payload.get("content")
            if not isinstance(content, str) or not content.strip():
                self.send_json({"ok": False, "message": "Capture text is required."}, HTTPStatus.BAD_REQUEST)
                return
            self.send_json(quick_capture(content))
            return
        if parsed.path == "/api/knowledge/daily":
            self.send_json(make_daily_brief())
            return
        if parsed.path == "/api/knowledge/weekly":
            self.send_json(make_weekly_synthesis())
            return
        if parsed.path == "/api/knowledge/ingest":
            self.send_json({"ok": True, "results": ingest_all()})
            return
        self.send_json({"ok": False, "message": "Not found"}, HTTPStatus.NOT_FOUND)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("content-length", "0") or "0")
        if length <= 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def send_json(self, payload: dict[str, object], status_code: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    ensure_vault()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Pro AI phone knowledge server running at http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
'''


def generate_termux_scripts(
    chat_model: str,
    autocomplete_model: str,
    mode: str = "usb",
    script_dir: Path = DEFAULT_SCRIPT_DIR,
) -> TermuxScriptBundle:
    normalized = mode.lower()
    ollama_host = ollama_host_for_mode(normalized)
    files = {
        script_dir / "bootstrap.sh": generate_bootstrap_script(),
        script_dir / DEBIAN_OLLAMA_SETUP_SCRIPT: generate_debian_ollama_setup_script(),
        script_dir / KNOWLEDGE_SERVER_SCRIPT: generate_knowledge_server_script(),
        script_dir / "start-droidshield.sh": generate_start_script(normalized),
        script_dir / "install-models.sh": generate_install_models_script(chat_model, autocomplete_model),
        script_dir / WIDGET_SHORTCUT_PATH: generate_widget_shortcut_script(),
        script_dir / WIDGET_ICON_PATH: _widget_icon_png(),
        script_dir / "ANDROID_OPTIMIZATION_CHECKLIST.txt": "\n".join(android_battery_optimization_checklist()) + "\n",
        script_dir / "TERMUX_WIDGET_INSTRUCTIONS.txt": termux_widget_instructions() + "\n",
    }
    return TermuxScriptBundle(mode=normalized, ollama_host=ollama_host, files=files)


def write_termux_scripts(bundle: TermuxScriptBundle, root: Path = Path(".")) -> list[Path]:
    written: list[Path] = []
    for relative_path, content in bundle.files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def _widget_icon_png() -> bytes:
    return (files("droidshield") / "ui" / "droidshield.png").read_bytes()
