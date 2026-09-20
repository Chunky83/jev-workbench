# Collect diagnostic evidence

You are collecting evidence for a software issue in the project the user has selected.

Read the repository instructions before you begin. Inspect real logs before you read code or propose a cause.

Your job is to collect evidence. Do not diagnose the issue. Do not propose a fix. Do not repeat a diagnosis from the issue description as a verified fact.

## Inputs

- Issue number or issue URL
- Environment: local, test, or production
- Relevant time window, when known

## Process

1. Read the issue title, description, and comments.
2. Identify each factual claim in the issue.
3. Separate reported behavior from independently verified evidence.
4. Query logs from the environment named in the issue.
5. Find the relevant request, trace, exception, or failed test.
6. Record exact timestamps, durations, statuses, service names, revisions, and trace identifiers.
7. Read source code only after the logs identify the relevant code path.
8. Include only source locations needed to explain the observed execution path.
9. Remove API keys, session values, authorization headers, cookies, personal information, and customer identifiers.
10. Do not include a proposed fix.
11. Do not treat the issue author's diagnosis as verified evidence.
12. State clearly when a claim could not be verified.

## Output

Write one JSON object with this structure:

```json
{
  "issue": {
    "number": 0,
    "title": "",
    "url": ""
  },
  "environment": "local",
  "service": "backend",
  "reported_behavior": "",
  "verified_observations": [
    {
      "id": "E001",
      "source": "cloud_log",
      "observed_at": "",
      "text": ""
    }
  ],
  "unverified_claims": [
    {
      "id": "U001",
      "text": "",
      "reason": ""
    }
  ],
  "source_locations": [
    {
      "path": "",
      "line": 0,
      "reason": ""
    }
  ]
}
```

Use `local`, `test`, or `production` for `environment`. Use `backend` or `frontend` for `service`.

Every verified observation must name its source. Keep observations factual and short. Preserve exact error messages when they contain no confidential information.

Finish after the JSON object. Do not add a diagnosis or recommendation.
