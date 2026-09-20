"""Command-line entry point for Jev Diagnostics."""

import argparse
import json
from pathlib import Path

from .api_key import load_api_key
from .diagnosis import build_request, render_diagnosis
from .evidence import load_evidence
from .typesafe_client import submit_request


def parse_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser(description="Review evidence with TypeSafe Jev.")
    argument_parser.add_argument("--evidence", required=True, type=Path)
    action_group = argument_parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--preview", action="store_true")
    action_group.add_argument("--send", action="store_true")
    return argument_parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    diagnostic_state = load_evidence(arguments.evidence)
    request_body = build_request(diagnostic_state)

    if arguments.preview:
        print(json.dumps(request_body, indent=2))
        print("\nPreview only. Nothing was sent to TypeSafe.")
        return

    response_body = submit_request(request_body, load_api_key())
    print(render_diagnosis(response_body, diagnostic_state))


if __name__ == "__main__":
    main()
