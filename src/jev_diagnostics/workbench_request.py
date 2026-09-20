"""Validate editable questions and assemble the exact Jev request."""

import json
import math


def read_json(text):
    def reject_constant(value):
        raise ValueError(f"{value} is not a JSON number.")
    return json.loads(text, parse_constant=reject_constant)


def build_workbench_request(state, questions, instructions, model):
    if not isinstance(state, (dict, list, str)) or not state:
        raise ValueError("State must be a nonempty JSON object, array, or string.")
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 20:
        raise ValueError("Primitives must contain between 1 and 20 named questions.")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("Write the common instructions before running.")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("A model name is required.")
    prepared = {}
    for name, question in questions.items():
        if not name.strip() or not isinstance(question, dict):
            raise ValueError("Each question needs a name and an object definition.")
        kind = question.get("type")
        if kind not in ("choice", "score", "noul"):
            raise ValueError(f"{name}: type must be choice, score, or noul.")
        prompt = question.get("instructions")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{name}: write a question in instructions.")
        criteria = question.get("criteria")
        if kind == "choice":
            if not isinstance(criteria, dict) or len(criteria) < 2:
                raise ValueError(f"{name}: Choice needs at least two named options.")
            if any(not key.strip() or (value is not None and not isinstance(value, str))
                   for key, value in criteria.items()):
                raise ValueError(f"{name}: option descriptions must be text or null.")
        if kind == "score":
            if not isinstance(criteria, list) or not 2 <= len(criteria) <= 10:
                raise ValueError(f"{name}: Score needs 2 to 10 ordered descriptions.")
            if any(not isinstance(value, str) or not value.strip() for value in criteria):
                raise ValueError(f"{name}: each score level needs a description.")
        if kind == "noul" and criteria is not None:
            if not isinstance(criteria, dict) or set(criteria) != {"true", "false"}:
                raise ValueError(f"{name}: Noul criteria must describe true and false.")
            if any(not isinstance(value, str) for value in criteria.values()):
                raise ValueError(f"{name}: Noul descriptions must be text.")
        prepared[name] = {"type": kind, "instructions": instructions + "\n\n" + prompt}
        if criteria is not None:
            prepared[name]["criteria"] = criteria
    request = {"model": model.strip(), "state": state, "questions": prepared}
    if len(json.dumps(request).encode("utf-8")) > 200_000:
        raise ValueError("Request exceeds the workbench's 200 KB evidence budget.")
    return request


def valid_number(value, maximum=1):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum


def validate_response(response, questions):
    if not isinstance(response, dict) or not isinstance(response.get("model"), str):
        raise ValueError("Jev returned an invalid response envelope.")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError("Jev did not return exactly the requested answers.")
    for name, question in questions.items():
        answer = answers[name]
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise ValueError(f"{name}: response type does not match the question.")
        if kind == "noul":
            if not valid_number(answer.get("noul")):
                raise ValueError(f"{name}: invalid Noul value.")
            continue
        if not valid_number(answer.get("confidence")):
            raise ValueError(f"{name}: invalid confidence.")
        expected = set(question["criteria"]) if kind == "choice" else {
            str(index) for index in range(len(question["criteria"]))}
        probabilities = answer.get("probabilities")
        if (not isinstance(probabilities, dict) or set(probabilities) != expected
                or not all(valid_number(value) for value in probabilities.values())
                or abs(sum(probabilities.values()) - 1) > 0.02):
            raise ValueError(f"{name}: invalid answer distribution.")
        if kind == "choice" and answer.get("choice") not in expected:
            raise ValueError(f"{name}: unknown choice.")
        if kind == "score":
            if not valid_number(answer.get("score"), len(expected) - 1):
                raise ValueError(f"{name}: invalid score.")
            if answer.get("legend") != dict(enumerate(question["criteria"])):
                legend = {str(index): value for index, value in enumerate(question["criteria"])}
                if answer.get("legend") != legend:
                    raise ValueError(f"{name}: score legend does not match the rubric.")
    usage = response.get("usage")
    if not isinstance(usage, dict) or any(type(usage.get(key)) is not int or usage[key] < 0
                                        for key in ("input_tokens", "output_tokens")):
        raise ValueError("Jev returned invalid token usage.")
    return response
