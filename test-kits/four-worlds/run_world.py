#!/usr/bin/env python3
"""Offline terminal runner for the Jev Workbench Story Worlds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Could not find {path}.") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is not valid JSON: {error.msg}.") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def available_worlds() -> list[Path]:
    return sorted(
        directory
        for directory in ROOT.iterdir()
        if directory.is_dir() and (directory / "case.json").is_file()
    )


def load_world(world_id: str) -> tuple[dict, dict, Path]:
    directory = ROOT / world_id
    if directory not in available_worlds():
        choices = ", ".join(path.name for path in available_worlds())
        raise ValueError(f"Unknown world {world_id!r}. Choose one of: {choices}.")
    return read_json(directory / "case.json"), read_json(directory / "oracle.json"), directory


def print_world_list() -> None:
    print("Jev Workbench Story Worlds")
    print()
    for directory in available_worlds():
        case = read_json(directory / "case.json")
        implementation = case["implementation"]["primary"]
        print(f"  {case['title']}")
        print(f"    {case['tagline']}")
        print(f"    Best for: {implementation}")
        print(f"    Run: python test-kits/four-worlds/run_world.py story {case['world_id']}")
        print()


def print_story(case: dict, directory: Path) -> None:
    story = case["story"]
    contract = case["decision_contract"]
    print(case["title"])
    print("=" * len(case["title"]))
    print(case["tagline"])
    print()
    print(f"Cover art: {directory / case['cover_art']}")
    print(f"Primary implementation: {case['implementation']['primary']}")
    print(f"Secondary implementation: {case['implementation']['secondary']}")
    print()
    print(f"Protagonist: {story['protagonist']['name']} — {story['protagonist']['role']}")
    print(f"Antagonist: {story['antagonist']['name']} — {story['antagonist']['nature']}")
    print()
    print("Opening")
    print(story["opening"])
    print()
    print("Your decision vocabulary")
    for value, description in contract["values"].items():
        print(f"  {value}: {description}")
    print()
    print("Story cards")
    for card in case["cards"]:
        print(f"  {card['icon']} {card['id']}: {card['name']}")
        for fact in card["facts"]:
            print(f"     • {fact}")
    print()
    print("The terminal can validate a decision payload without revealing the oracle:")
    print(f"  python test-kits/four-worlds/run_world.py check {case['world_id']} result.json")


def read_decisions(path: Path) -> dict:
    payload = read_json(path)
    decisions = payload.get("decisions")
    if not isinstance(decisions, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in decisions.items()
    ):
        raise ValueError(f"{path} needs a decisions object whose keys and values are text.")
    return decisions


def check_world(case: dict, oracle: dict, decisions: dict, source: str) -> int:
    allowed = set(case["decision_contract"]["values"])
    cards = {card["id"]: card for card in case["cards"]}
    expected = oracle["expected_decisions"]
    expected_ids = set(expected)
    supplied_ids = set(decisions)

    print(case["title"])
    print("=" * len(case["title"]))
    print(f"Checking {source}")
    print()

    passed = True
    for card_id, card in cards.items():
        actual = decisions.get(card_id)
        wanted = expected[card_id]
        if actual is None:
            print(f"  ◌ {card['icon']} {card['name']}: incomplete — no decision supplied")
            passed = False
        elif actual not in allowed:
            print(f"  ✗ {card['icon']} {card['name']}: invalid value {actual!r}")
            passed = False
        elif actual == wanted:
            print(f"  ✓ {card['icon']} {card['name']}: {actual}")
        else:
            print(f"  ✗ {card['icon']} {card['name']}: chose {actual}; rulebook expects {wanted}")
            passed = False

    extras = supplied_ids - expected_ids
    if extras:
        passed = False
        print()
        print("Unexpected card identifiers: " + ", ".join(sorted(extras)))

    print()
    if passed:
        print("Result: passed — every decision follows this world's fictional rulebook.")
        return 0
    print("Result: needs review — this is not a real-world failure; inspect the named cards above.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Explore and validate the offline Jev Workbench Story Worlds."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List every world and its intended implementation.")

    story = commands.add_parser("story", help="Show a world without revealing its oracle.")
    story.add_argument("world_id")

    check = commands.add_parser("check", help="Validate a decisions JSON payload.")
    check.add_argument("world_id")
    check.add_argument(
        "decisions_file",
        type=Path,
        nargs="?",
        help="A JSON file containing a decisions object.",
    )
    check.add_argument(
        "--demo",
        action="store_true",
        help="Run the bundled expected decisions to verify the local fixture.",
    )
    return parser


def main() -> int:
    configure_output()
    args = build_parser().parse_args()
    try:
        if args.command == "list":
            print_world_list()
            return 0

        case, oracle, directory = load_world(args.world_id)
        if args.command == "story":
            print_story(case, directory)
            return 0

        if args.demo:
            decisions = oracle["expected_decisions"]
            source = "the bundled local fixture"
        elif args.decisions_file is not None:
            decisions = read_decisions(args.decisions_file)
            source = str(args.decisions_file)
        else:
            raise ValueError("Give a decisions file or add --demo.")
        return check_world(case, oracle, decisions, source)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
