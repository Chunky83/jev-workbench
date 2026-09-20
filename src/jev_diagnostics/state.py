"""Data structures that describe the evidence Jev receives."""

from dataclasses import asdict, dataclass
from typing import Any


ALLOWED_ENVIRONMENTS = {"local", "test", "production"}
ALLOWED_SERVICES = {"backend", "frontend"}


@dataclass(frozen=True)
class IssueReference:
    number: int
    title: str
    url: str


@dataclass(frozen=True)
class VerifiedObservation:
    observation_id: str
    source: str
    observed_at: str
    text: str


@dataclass(frozen=True)
class UnverifiedClaim:
    claim_id: str
    text: str
    reason: str


@dataclass(frozen=True)
class SourceLocation:
    path: str
    line: int
    reason: str


@dataclass(frozen=True)
class DiagnosticState:
    issue: IssueReference
    environment: str
    service: str
    reported_behavior: str
    verified_observations: tuple[VerifiedObservation, ...]
    unverified_claims: tuple[UnverifiedClaim, ...]
    source_locations: tuple[SourceLocation, ...]

    def validate(self) -> None:
        if self.environment not in ALLOWED_ENVIRONMENTS:
            raise ValueError("Environment must be local, test, or production.")
        if self.service not in ALLOWED_SERVICES:
            raise ValueError("Service must be backend or frontend.")
        if not self.reported_behavior.strip():
            raise ValueError("Reported behavior is required.")
        if not self.verified_observations:
            raise ValueError("At least one verified observation is required.")

        observation_ids: set[str] = set()
        for observation in self.verified_observations:
            if not observation.observation_id.startswith("E"):
                raise ValueError("Verified observation identifiers must start with E.")
            if observation.observation_id in observation_ids:
                raise ValueError("Verified observation identifiers must be unique.")
            if not observation.source.strip() or not observation.text.strip():
                raise ValueError("Every verified observation needs a source and text.")
            observation_ids.add(observation.observation_id)

    def to_dictionary(self) -> dict[str, Any]:
        self.validate()
        result = asdict(self)
        for observation in result["verified_observations"]:
            observation["id"] = observation.pop("observation_id")
        for claim in result["unverified_claims"]:
            claim["id"] = claim.pop("claim_id")
        return result
