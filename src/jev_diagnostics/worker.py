"""One request on stdin, one JSON response on stdout. No shell execution."""

import json
import os
import sys
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .api_key import load_api_key
from .case_store import atomic_text, json_text, load_case, save_case, validate_case
from .local_checks import run_guest_fixture
from .typesafe_client import submit_request
from .workbench_request import build_workbench_request, read_json, validate_response


def request_for(case):
    validate_case(case)
    return build_workbench_request(case["state"], case["primitives"],
                                    case["instructions"], case["model"])


def run_case(message):
    case = message["case"]
    request = request_for(case)
    mode = message.get("mode")
    if mode not in ("local", "live"):
        raise ValueError("Choose Local checks or Live Jev.")
    run_root = Path(message["runs_folder"]).resolve()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    folder = run_root / run_id
    folder.mkdir(parents=True)
    for name in ("state", "primitives"):
        atomic_text(folder / (name + ".json"), json_text(case[name]))
    atomic_text(folder / "instructions.md", case["instructions"])
    runner = case.get("runner", {"check": "guest_access_fixture", "iterations": 1})
    atomic_text(folder / "runner.json", json_text(runner))
    atomic_text(folder / "test.json", json_text({key: case[key] for key in ("schema_version", "title", "model")}))
    atomic_text(folder / "request.json", json_text(request))
    result = {"run_id": run_id, "title": case["title"], "mode": mode,
              "folder": str(folder), "status": "running", "verification": "Not performed"}
    atomic_text(folder / "result.json", json_text(result))
    start = time.monotonic()
    try:
        if mode == "local":
            iterations = []
            for iteration in range(runner["iterations"]):
                checks = run_guest_fixture()
                iterations.append({"iteration": iteration + 1, **checks})
                if not checks["passed"]:
                    break
            result.update(checks=checks, verification="Passed" if checks["passed"] else "Failed",
                          iterations=iterations,
                          summary="Local synthetic checks completed. No AI request was sent.")
        else:
            key = message.get("api_key") or load_api_key()
            if not isinstance(key, str) or not key.strip():
                raise ValueError("Set the TypeSafe key in API settings.")
            response = submit_request(request, key)
            validate_response(response, request["questions"])
            result.update(response=response, summary="Jev judgments are hypotheses. Verify against evidence.")
        result["status"] = "completed"
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        result.update(status="failed", error=str(error), summary="Run failed. No automatic retry was sent.")
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    atomic_text(folder / "result.json", json_text(result))
    return result


def _dispatch(message):
    action = message.get("action")
    if action == "workflow":
        from .workflow.desktop_service import dispatch as workflow_dispatch
        return workflow_dispatch(message)
    if action == "open":
        return {"case": load_case(message["folder"]), "folder": message["folder"]}
    if action == "save":
        return {"folder": save_case(message["folder"], message["case"])}
    if action == "preview":
        return {"request": request_for(message["case"])}
    if action == "run":
        return {"result": run_case(message)}
    if action == "history":
        root = Path(message["runs_folder"])
        records = []
        for path in sorted(root.glob("*/result.json"), reverse=True)[:100]:
            try:
                records.append(read_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return {"runs": records}
    raise ValueError("Unknown worker action.")


def dispatch(message):
    from .activity import trace
    database = message.get('activity_database') or (message.get('database') if message.get('action') == 'workflow' else None)
    if not database or (message.get('action') == 'workflow' and message.get('operation') == 'inbox'):
        return _dispatch(message)
    operation = message.get('operation') if message.get('action') == 'workflow' else message.get('action')
    return trace(database, 'worker', operation, lambda: _dispatch(message),
                 message.get('request_id', ''), message.get('case_id', ''))

def main():
    try:
        raw = sys.stdin.buffer.readline(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("Worker input is too large.")
        message = read_json(raw.decode("utf-8"))
        if not isinstance(message, dict):
            raise ValueError("Worker input must be an object.")
        response = {"ok": True, **dispatch(message)}
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error) as error:
        response = {"ok": False, "error": str(error)}
    sys.stdout.buffer.write(json_text(response).encode("utf-8"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
