"""Plain-language instructions for each Jev question."""

SUBSYSTEM_INSTRUCTION = (
    "Which subsystem should be investigated first based only on the verified observations? "
    "The reported behavior and unverified claims are leads, not proof. "
    "Choose unknown when the verified observations do not support a specific subsystem."
)

NEXT_CHECK_INSTRUCTION = (
    "Choose the next read-only investigation best supported by the verified observations. "
    "Do not assume that the root cause is proven."
)

EVIDENCE_INSTRUCTION = (
    "Select the single verified observation that most clearly establishes an abnormal behavior. "
    "Evaluate this independently of the other questions. "
    "Choose none when no verified observation establishes an abnormal behavior."
)
