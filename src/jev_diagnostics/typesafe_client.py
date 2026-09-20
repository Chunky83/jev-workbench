"""Send one diagnostic request to the TypeSafe System One endpoint."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TYPESAFE_ENDPOINT = "https://api.typesafe.ai/v1/systemone"


def submit_request(request_body: dict[str, Any], api_key: str) -> dict[str, Any]:
    http_request = Request(
        TYPESAFE_ENDPOINT,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(http_request, timeout=30) as http_response:
            return json.load(http_response)
    except HTTPError as error:
        raise RuntimeError(f"TypeSafe returned HTTP {error.code}. No retry was sent.") from error
    except URLError as error:
        raise RuntimeError("The program could not connect to TypeSafe. No retry was sent.") from error
