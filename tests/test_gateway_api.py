import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from droidshield.gateway import SandboxGateway
from droidshield.gateway_api import start_gateway_api_thread
from droidshield.monitoring import AuditLog


def test_gateway_api_registers_node_and_accepts_task(tmp_path):
    gateway = SandboxGateway(nodes=(), audit_log=AuditLog(tmp_path / "audit.jsonl"))
    server, url = start_gateway_api_thread(gateway=gateway)
    try:
        registration = post_json(
            f"{url}/api/v1/nodes/register",
            {
                "node_id": "pixel4a-01",
                "device_model": "Pixel 4a",
                "runtime": "termux-proot",
                "capabilities": ["shell", "git", "python", "node"],
            },
        )
        assert registration["status"] == "registered"

        created = post_json(
            f"{url}/api/v1/tasks",
            {
                "agent": "codex",
                "repo": "example/repo",
                "task_type": "shell",
                "command": "git status",
                "working_dir": "/workspace/project",
                "policy": "default",
                "timeout_seconds": 120,
            },
        )

        assert created["status"] == "queued"
        job = get_json(f"{url}/api/v1/tasks/{created['job_id']}")
        assert job == {
            "job_id": created["job_id"],
            "status": "queued",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "policy_violations": [],
        }
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_api_reports_blocked_command(tmp_path):
    gateway = SandboxGateway(audit_log=AuditLog(tmp_path / "audit.jsonl"))
    server, url = start_gateway_api_thread(gateway=gateway)
    try:
        created = post_json(
            f"{url}/api/v1/tasks",
            {
                "agent": "codex",
                "repo": "example/repo",
                "task_type": "shell",
                "command": "rm -rf ~/.ssh",
                "working_dir": "/workspace/project",
            },
        )

        assert created["status"] == "blocked"
        job = get_json(f"{url}/api/v1/tasks/{created['job_id']}")
        assert job["status"] == "blocked"
        assert job["policy_violations"]
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_api_kills_job(tmp_path):
    gateway = SandboxGateway(audit_log=AuditLog(tmp_path / "audit.jsonl"))
    server, url = start_gateway_api_thread(gateway=gateway)
    try:
        created = post_json(f"{url}/api/v1/tasks", {"agent": "cursor", "command": "pytest"})
        killed = post_json(
            f"{url}/api/v1/jobs/{created['job_id']}/kill",
            {"reason": "manual_operator_action"},
        )

        assert killed == {
            "job_id": created["job_id"],
            "status": "killed",
            "reason": "manual_operator_action",
        }
        assert get_json(f"{url}/api/v1/tasks/{created['job_id']}")["status"] == "killed"
        assert gateway.audit_log.tail()[-1]["event_type"] == "job.killed"
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_api_rejects_missing_command(tmp_path):
    gateway = SandboxGateway(audit_log=AuditLog(tmp_path / "audit.jsonl"))
    server, url = start_gateway_api_thread(gateway=gateway)
    try:
        try:
            post_json(f"{url}/api/v1/tasks", {"agent": "codex"})
        except HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read().decode("utf-8"))
            assert payload["error"] == "command is required"
        else:
            raise AssertionError("missing command should fail")
    finally:
        server.shutdown()
        server.server_close()


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, method="POST", headers={"content-type": "application/json"})
    with urlopen(request, timeout=4) as response:  # noqa: S310 - local test server.
        return json.loads(response.read().decode("utf-8"))


def get_json(url):
    with urlopen(url, timeout=4) as response:  # noqa: S310 - local test server.
        return json.loads(response.read().decode("utf-8"))
