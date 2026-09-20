"""Build requests and render validated Jev decisions."""

from typing import Any

from .primitives import NEXT_CHECK_CHOICES, SUBSYSTEM_CHOICES, build_questions
from .state import DiagnosticState


def build_request(diagnostic_state: DiagnosticState) -> dict[str, Any]:
    return {
        "model": "jev-latest",
        "state": diagnostic_state.to_dictionary(),
        "questions": build_questions(diagnostic_state),
    }


def read_choice(
    response_body: dict[str, Any],
    question_name: str,
    allowed_choices: set[str],
) -> tuple[str, float]:
    answer = response_body.get("answers", {}).get(question_name, {})
    choice = answer.get("choice")
    confidence = answer.get("confidence")

    if choice not in allowed_choices:
        raise ValueError(f"Jev returned an invalid {question_name} choice.")
    if not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
        raise ValueError(f"Jev returned invalid confidence for {question_name}.")
    return choice, float(confidence)


def render_diagnosis(
    response_body: dict[str, Any],
    diagnostic_state: DiagnosticState,
) -> str:
    subsystem, subsystem_confidence = read_choice(
        response_body,
        "subsystem",
        set(SUBSYSTEM_CHOICES),
    )
    next_check, next_check_confidence = read_choice(
        response_body,
        "next_check",
        set(NEXT_CHECK_CHOICES),
    )
    evidence_choices = {"none"}
    evidence_choices.update(
        observation.observation_id for observation in diagnostic_state.verified_observations
    )
    evidence, evidence_confidence = read_choice(
        response_body,
        "evidence",
        evidence_choices,
    )

    review_required = (
        subsystem == "unknown"
        or evidence == "none"
        or subsystem_confidence < 0.8
        or next_check_confidence < 0.8
        or evidence_confidence < 0.8
    )

    report_lines = [
        "Jev diagnosis: hypothesis, not a verified root cause.",
        f"Subsystem: {subsystem} ({subsystem_confidence:.2f})",
        f"Suggested check: {NEXT_CHECK_CHOICES[next_check]}",
        f"Check confidence: {next_check_confidence:.2f}",
        f"Supporting evidence: {evidence} ({evidence_confidence:.2f})",
        "Review required." if review_required else "Evidence review still required before action.",
        f"Model: {response_body.get('model', 'not reported')}",
        "No suggested action was executed.",
    ]
    return "\n".join(report_lines)
