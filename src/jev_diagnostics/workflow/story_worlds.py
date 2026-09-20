"""Bundled fictional cases and their fixed, offline decision checks."""

import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4


WORLD_RUNNERS = {
    "astral-post-office": "astral_post_office_fixture",
    "lantern-room": "lantern_room_fixture",
    "museum-of-tiny-planets": "museum_of_tiny_planets_fixture",
    "pocket-weather-bureau": "pocket_weather_bureau_fixture",
}
RUNNER_WORLDS = {runner: world for world, runner in WORLD_RUNNERS.items()}


def registered_check_ids():
    return {"guest_access_fixture", *RUNNER_WORLDS}


def is_registered(check_id):
    return check_id in registered_check_ids()


def _data_root():
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "test-kits" / "four-worlds"
        if candidate.is_dir():
            return candidate
    raise ValueError("The bundled story-world data is unavailable. Keep the complete Workbench package together.")


def _read_object(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("The bundled story-world data is unreadable.") from error
    if not isinstance(value, dict):
        raise ValueError("The bundled story-world data must contain JSON objects.")
    return value


def load(world_id, include_oracle=False):
    if world_id not in WORLD_RUNNERS:
        raise ValueError("Choose one of the four registered story worlds.")
    folder = _data_root() / world_id
    case = _read_object(folder / "case.json")
    runner_id = case.get("implementation", {}).get("runner_id")
    if (case.get("schema_version") != "story-world-v1" or case.get("world_id") != world_id
            or case.get("case_version") != 1 or runner_id != WORLD_RUNNERS[world_id]):
        raise ValueError("The bundled story-world case does not match its registered fixture.")
    if include_oracle:
        oracle = _read_object(folder / "oracle.json")
        if oracle.get("world_id") != world_id or oracle.get("case_version") != case["case_version"]:
            raise ValueError("The bundled story-world oracle does not match its case.")
        card_ids = {card["id"] for card in case["cards"]}
        if set(oracle.get("expected_decisions", {})) != card_ids:
            raise ValueError("The bundled story-world oracle does not cover the exact card set.")
        return case, oracle
    return case


def workbench_case(world_id):
    source = load(world_id)
    contract = source["decision_contract"]
    choices = contract["values"]
    questions = {}
    for card in source["cards"]:
        questions[card["id"]] = {
            "type": "choice",
            "instructions": "Choose the rulebook decision for " + card["name"] + ".",
            "criteria": choices,
        }
    state = {
        "story_world": {
            "world_id": source["world_id"],
            "case_version": source["case_version"],
            "tagline": source["tagline"],
            "story": source["story"],
            "rulebook": source["rulebook"],
            "decision_contract": contract,
            "cards": source["cards"],
        }
    }
    instructions = "\n".join(source["assistant_instructions"] + [
        "Jev answers and assistant rationales are hypotheses until the named local fixture verifies every decision."
    ])
    return {
        "schema_version": 1,
        "title": source["title"],
        "model": "jev-latest",
        "state": state,
        "primitives": questions,
        "instructions": instructions,
        "runner": {"check": source["implementation"]["runner_id"], "iterations": 1},
    }


def fixture_digest(world_id):
    case, oracle = load(world_id, include_oracle=True)
    encoded = json.dumps([case, oracle], ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _matches_registered_world(case, expected):
    return all(case.get(name) == expected[name]
               for name in ("state", "primitives", "instructions", "runner"))


def _registered_pristine_copy(store, world_id, expected, canonical):
    from ..case_store import load_case
    from .library import metadata

    root = canonical.parent.resolve()
    prefix = world_id + "-"
    with store.transaction() as db:
        sources = [row["source"] for row in
                   db.execute("SELECT id, source FROM cases ORDER BY rowid DESC").fetchall()
                   if not metadata(db, row["id"]).get("archived", False)]
    for source in sources:
        folder = Path(source).resolve()
        if folder == canonical or folder.parent != root or not folder.name.startswith(prefix):
            continue
        try:
            case = load_case(folder)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if _matches_registered_world(case, expected):
            return folder, case
    return None


def create_saved_case(store, world_id):
    from ..case_store import load_case, save_case
    from .library import register

    expected = workbench_case(world_id)
    folder = (store.path.parent / "story-worlds" / world_id).resolve()
    if (folder / "test.json").is_file():
        case = load_case(folder)
        if not _matches_registered_world(case, expected):
            replacement = _registered_pristine_copy(store, world_id, expected, folder)
            if replacement:
                folder, case = replacement
            else:
                folder = folder.with_name(world_id + "-" + uuid4().hex[:8])
                case = expected
                save_case(folder, case)
    else:
        case = expected
        save_case(folder, case)
    register(store, folder, case, sample=True)
    return {"folder": str(folder), "case": case}


def scope(check_id):
    if check_id == "guest_access_fixture":
        return "Synthetic localhost fixture only; no project files or external hosts"
    case = load(RUNNER_WORLDS[check_id])
    return case["decision_contract"]["scope"]


def _bounded_text(value, label, maximum):
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > maximum:
        raise ValueError(label + " must be nonempty text within the fixture limit.")
    return value


def validate_proposal_inputs(snapshot, check_id, decisions, rationale):
    if check_id == "guest_access_fixture":
        if decisions is not None or rationale is not None:
            raise ValueError("The guest-access fixture does not accept story-world decisions.")
        return None
    if check_id not in RUNNER_WORLDS:
        raise ValueError("This check is not registered.")
    if snapshot.get("runner", {}).get("check") != check_id:
        raise ValueError("The proposed check does not match the shared case's named fixture.")
    world_id = RUNNER_WORLDS[check_id]
    source = load(world_id)
    registered = workbench_case(world_id)
    for name in ("state", "primitives", "instructions", "runner"):
        if snapshot.get(name) != registered[name]:
            raise ValueError("This story-world case was edited. Open the bundled world again before requesting its registered fixture.")
    shared_world = snapshot.get("state", {}).get("story_world", {})
    if (shared_world.get("world_id") != world_id
            or shared_world.get("case_version") != source["case_version"]):
        raise ValueError("The shared story world does not match the registered fixture version.")
    card_ids = [card["id"] for card in source["cards"]]
    cards = {card["id"]: card for card in source["cards"]}
    allowed = set(source["decision_contract"]["values"])
    if (not isinstance(decisions, dict) or set(decisions) != set(card_ids)
            or any(not isinstance(value, str) or value not in allowed for value in decisions.values())):
        raise ValueError("Decisions must contain one allowed value for every story card and no extra cards.")
    if not isinstance(rationale, list) or len(rationale) != len(card_ids):
        raise ValueError("Provide one rationale entry for every story card.")
    normalized = []
    seen = set()
    for item in rationale:
        if not isinstance(item, dict) or item.get("card_id") not in card_ids:
            raise ValueError("Each rationale needs a registered card_id.")
        card_id = item["card_id"]
        if card_id in seen:
            raise ValueError("Each story card may appear in the rationale once.")
        seen.add(card_id)
        evidence = item.get("evidence")
        if (not isinstance(evidence, list) or not 1 <= len(evidence) <= 10
                or any(not isinstance(value, str) or not value.strip()
                       or len(value.encode("utf-8")) > 500 for value in evidence)):
            raise ValueError("Each rationale needs one to ten short evidence citations.")
        if any(value not in cards[card_id]["facts"] for value in evidence):
            raise ValueError("Rationale citations must exactly match facts supplied on that story card.")
        normalized.append({
            "card_id": card_id,
            "evidence": list(evidence),
            "summary": _bounded_text(item.get("summary"), "Rationale summary", 1000),
        })
    if seen != set(card_ids):
        raise ValueError("Provide rationale for every story card.")
    result = {
        "world_id": world_id,
        "case_version": source["case_version"],
        "fixture_digest": fixture_digest(world_id),
        "decisions": {card_id: decisions[card_id] for card_id in card_ids},
        "rationale": normalized,
    }
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 32000:
        raise ValueError("Story-world proposal inputs must stay below 32 KB.")
    return result


def run_fixture(check_id, inputs):
    if check_id not in RUNNER_WORLDS:
        raise ValueError("This story-world check is not registered.")
    world_id = RUNNER_WORLDS[check_id]
    case, oracle = load(world_id, include_oracle=True)
    if (not isinstance(inputs, dict) or inputs.get("world_id") != world_id
            or inputs.get("case_version") != case["case_version"]):
        raise ValueError("The approved proposal does not contain this fixture's exact inputs.")
    if inputs.get("fixture_digest") != fixture_digest(world_id):
        raise ValueError("The registered story fixture changed after proposal review. Request a fresh proposal.")
    decisions = inputs.get("decisions")
    card_ids = {card["id"] for card in case["cards"]}
    allowed = set(case["decision_contract"]["values"])
    if (not isinstance(decisions, dict) or set(decisions) != card_ids
            or any(value not in allowed for value in decisions.values())):
        raise ValueError("The approved proposal has no valid complete decision set.")
    observations = []
    for card in case["cards"]:
        card_id = card["id"]
        expected = oracle["expected_decisions"][card_id]
        actual = decisions.get(card_id)
        observations.append({
            "id": card_id,
            "name": card["name"],
            "decision": actual,
            "expected_decision": expected,
            "passed": actual == expected,
        })
    return {
        "source": "Bundled fictional " + case["title"] + " oracle; no network or real project access",
        "world_id": world_id,
        "observations": observations,
        "passed": all(item["passed"] for item in observations),
    }
