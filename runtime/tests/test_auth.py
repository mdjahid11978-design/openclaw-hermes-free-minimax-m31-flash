import unittest
from jahids_runtime.auth import AuthenticationConfigurationError, OwnerAuthenticator

class OwnerAuthenticationTests(unittest.TestCase):
    def test_accepts_only_exact_owner_bearer_secret(self):
        token = "x" * 48
        auth = OwnerAuthenticator(token)
        self.assertTrue(auth.authenticate("Bearer " + token))
        self.assertFalse(auth.authenticate("bearer " + token))
        self.assertFalse(auth.authenticate(token))
        self.assertFalse(auth.authenticate("Bearer " + token + "x"))
        self.assertFalse(auth.authenticate(None))

    def test_rejects_missing_short_and_placeholder_secrets(self):
        for token in ("", "short", "replace-with-a-long-random-secret"):
            with self.subTest(token=token), self.assertRaises(AuthenticationConfigurationError):
                OwnerAuthenticator(token)

if __name__ == "__main__":
    unittest.main()
