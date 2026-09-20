"""Save separate readable files with a manifest committed last."""

import json
import os
from pathlib import Path
from uuid import uuid4

from .workbench_request import build_workbench_request, read_json


def validate_case(case):
    if not isinstance(case, dict) or case.get("schema_version") != 1:
        raise ValueError("This test needs schema_version 1.")
    if not isinstance(case.get("title"), str) or not case["title"].strip():
        raise ValueError("Give the test a name.")
    build_workbench_request(case.get("state"), case.get("primitives"),
                            case.get("instructions"), case.get("model"))
    runner = case.get("runner", {"check": "guest_access_fixture", "iterations": 1})
    if not isinstance(runner, dict) or runner.get("check") != "guest_access_fixture":
        raise ValueError("This version supports the named guest_access_fixture check only.")
    if type(runner.get("iterations")) is not int or not 1 <= runner["iterations"] <= 3:
        raise ValueError("Local checks can repeat between 1 and 3 times.")
    return case


def atomic_text(path, text):
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def json_text(value):
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def save_case(folder, case):
    validate_case(case)
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    revision = "revisions/" + uuid4().hex
    revision_folder = folder / revision
    revision_folder.mkdir(parents=True)
    for name in ("state", "primitives"):
        atomic_text(revision_folder / (name + ".json"), json_text(case[name]))
    atomic_text(revision_folder / "instructions.md", case["instructions"])
    if "runner" in case:
        atomic_text(revision_folder / "runner.json", json_text(case["runner"]))
    manifest = {key: case[key] for key in ("schema_version", "title", "model")}
    manifest["revision"] = revision
    atomic_text(folder / "test.json", json_text(manifest))
    return str(folder)


def load_case(folder):
    folder = Path(folder).resolve()
    manifest = read_json((folder / "test.json").read_text(encoding="utf-8-sig"))
    revision = manifest.get("revision", ".")
    if not isinstance(revision, str):
        raise ValueError("Invalid revision path.")
    revision_folder = (folder / revision).resolve()
    if not revision_folder.is_relative_to(folder):
        raise ValueError("The test references files outside its folder.")
    case = {key: manifest.get(key) for key in ("schema_version", "title", "model")}
    runner_path = revision_folder / "runner.json"
    if runner_path.exists():
        if not runner_path.resolve().is_relative_to(folder) or runner_path.stat().st_size > 250_000:
            raise ValueError("Invalid runner file.")
        case["runner"] = read_json(runner_path.read_text(encoding="utf-8-sig"))
    for name in ("state", "primitives", "instructions"):
        path = revision_folder / (name + (".md" if name == "instructions" else ".json"))
        if not path.resolve().is_relative_to(folder) or path.stat().st_size > 250_000:
            raise ValueError("Test file is outside its folder or too large.")
        content = path.read_text(encoding="utf-8-sig")
        case[name] = content if name == "instructions" else read_json(content)
    return validate_case(case)
