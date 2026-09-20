"""Bounded Jev choices used by the diagnostic program."""

from typing import Any

from .instructions import (
    EVIDENCE_INSTRUCTION,
    NEXT_CHECK_INSTRUCTION,
    SUBSYSTEM_INSTRUCTION,
)
from .state import DiagnosticState


SUBSYSTEM_CHOICES = {
    "authentication": "A missing, expired, or rejected identity or session is evident.",
    "authorization": "An authenticated caller lacks permission for an operation.",
    "database": "A query, schema, constraint, or database connection failure is evident.",
    "upstream_service": "A call to an external service failed or delayed the operation.",
    "application": "An application exception or invalid application state is evident.",
    "performance": "A long request or deadline mismatch is evident.",
    "environment": "Local infrastructure, configuration, or build dependencies failed.",
    "unknown": "The verified observations do not support a specific subsystem.",
}

NEXT_CHECK_CHOICES = {
    "inspect_session": "Inspect the rejected request and its authentication session.",
    "inspect_permission": "Compare the denied operation with the caller permissions.",
    "inspect_database": "Inspect the schema, query, or connection named in the evidence.",
    "inspect_upstream": "Inspect the external request and provider response named in the evidence.",
    "inspect_stack": "Inspect the application frame named in the traceback.",
    "inspect_latency": "Compare the request duration with client and proxy deadlines.",
    "inspect_environment": "Inspect the unavailable service or configuration named in the evidence.",
    "collect_more_evidence": "Collect more existing evidence before selecting an investigation.",
}


def build_questions(diagnostic_state: DiagnosticState) -> dict[str, dict[str, Any]]:
    evidence_choices = {
        "none": "No verified observation directly supports a specific investigation."
    }
    for observation in diagnostic_state.verified_observations:
        evidence_choices[observation.observation_id] = observation.text

    return {
        "subsystem": {
            "type": "choice",
            "instructions": SUBSYSTEM_INSTRUCTION,
            "criteria": SUBSYSTEM_CHOICES,
        },
        "next_check": {
            "type": "choice",
            "instructions": NEXT_CHECK_INSTRUCTION,
            "criteria": NEXT_CHECK_CHOICES,
        },
        "evidence": {
            "type": "choice",
            "instructions": EVIDENCE_INSTRUCTION,
            "criteria": evidence_choices,
        },
    }
