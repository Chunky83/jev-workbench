"""Load a reviewed evidence file into diagnostic state."""

import json
from pathlib import Path
from typing import Any

from .state import (
    DiagnosticState,
    IssueReference,
    SourceLocation,
    UnverifiedClaim,
    VerifiedObservation,
)


def load_evidence(evidence_path: Path) -> DiagnosticState:
    evidence_text = evidence_path.read_text(encoding="utf-8")
    evidence_data: dict[str, Any] = json.loads(evidence_text)

    issue_data = evidence_data["issue"]
    diagnostic_state = DiagnosticState(
        issue=IssueReference(
            number=int(issue_data["number"]),
            title=str(issue_data["title"]),
            url=str(issue_data["url"]),
        ),
        environment=str(evidence_data["environment"]),
        service=str(evidence_data["service"]),
        reported_behavior=str(evidence_data["reported_behavior"]),
        verified_observations=tuple(
            VerifiedObservation(
                observation_id=str(observation["id"]),
                source=str(observation["source"]),
                observed_at=str(observation["observed_at"]),
                text=str(observation["text"]),
            )
            for observation in evidence_data["verified_observations"]
        ),
        unverified_claims=tuple(
            UnverifiedClaim(
                claim_id=str(claim["id"]),
                text=str(claim["text"]),
                reason=str(claim["reason"]),
            )
            for claim in evidence_data.get("unverified_claims", [])
        ),
        source_locations=tuple(
            SourceLocation(
                path=str(location["path"]),
                line=int(location["line"]),
                reason=str(location["reason"]),
            )
            for location in evidence_data.get("source_locations", [])
        ),
    )
    diagnostic_state.validate()
    return diagnostic_state
