import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_git_identity.py"
SPEC = importlib.util.spec_from_file_location("check_git_identity", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load the Git identity check")
check_git_identity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_git_identity)


class GitIdentityTests(unittest.TestCase):
    def test_extracts_email_from_git_identity(self):
        identity = "Example User <example@users.noreply.github.com> 1 +0000"
        self.assertEqual(
            check_git_identity.email_from_identity(identity),
            "example@users.noreply.github.com",
        )

    def test_rejects_address_that_caused_wrong_contributor(self):
        reason = check_git_identity.unsafe_reason("noreply@users.noreply.github.com")
        self.assertIn("another account", reason)

    def test_rejects_shared_contributors_address(self):
        reason = check_git_identity.unsafe_reason(
            "contributors@users.noreply.github.com"
        )
        self.assertIn("not tied", reason)

    def test_rejects_unfinished_placeholder(self):
        reason = check_git_identity.unsafe_reason(
            "YOUR_ID+Example@users.noreply.github.com"
        )
        self.assertIn("placeholder", reason)

    def test_accepts_account_specific_no_reply_address(self):
        reason = check_git_identity.unsafe_reason(
            "123456+Example@users.noreply.github.com"
        )
        self.assertIsNone(reason)


if __name__ == "__main__":
    unittest.main()
