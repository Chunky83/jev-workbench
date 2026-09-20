"""Load the TypeSafe key without storing it in source code."""

import os


def load_api_key() -> str:
    api_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set TYPESAFE_API_KEY in the current terminal.")
    return api_key
