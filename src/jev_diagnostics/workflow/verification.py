"""Only local assertions may establish a verified fixture outcome."""
def classify(checks):
    observations = checks.get('observations', [])
    passed = checks.get('passed') is True and bool(observations) and all(
        observation.get('passed') is True for observation in observations)
    return {'status': 'passed' if passed else 'failed', 'assertions': observations,
            'scope': 'Synthetic fixture only. Does not verify a real project or an assistant hypothesis.'}
