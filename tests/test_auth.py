import unittest
from uuid import uuid4

from snake_portal.auth import AuthStore, ValidationError, hash_password, verify_password


class AuthStoreTests(unittest.TestCase):
  def setUp(self) -> None:
    self.store = AuthStore(f"file:auth-tests-{uuid4().hex}?mode=memory&cache=shared")
    self.addCleanup(self.store.close)

  def test_hash_round_trip(self) -> None:
    hashed = hash_password("password123")
    self.assertTrue(verify_password(hashed, "password123"))
    self.assertFalse(verify_password(hashed, "wrong-password"))

  def test_register_and_authenticate(self) -> None:
    user = self.store.register_user("aravind", "aravind@example.com", "password123", "password123")
    authenticated = self.store.authenticate_user("aravind@example.com", "password123")

    self.assertEqual(user.username, "aravind")
    self.assertIsNotNone(authenticated)
    self.assertEqual(authenticated.email, "aravind@example.com")

  def test_reject_duplicate_email(self) -> None:
    self.store.register_user("aravind", "aravind@example.com", "password123", "password123")

    with self.assertRaisesRegex(ValidationError, "already registered"):
      self.store.register_user("aravind2", "aravind@example.com", "password123", "password123")

  def test_create_and_resolve_session(self) -> None:
    user = self.store.register_user("aravind", "aravind@example.com", "password123", "password123")
    token, _expires_at = self.store.create_session(user.id)
    session_user = self.store.get_user_for_session(token)

    self.assertIsNotNone(session_user)
    self.assertEqual(session_user.username, "aravind")

    self.store.delete_session(token)
    self.assertIsNone(self.store.get_user_for_session(token))

  def test_validation_rejects_short_password(self) -> None:
    with self.assertRaisesRegex(ValidationError, "at least 8 characters"):
      self.store.register_user("aravind", "aravind@example.com", "short", "short")


if __name__ == "__main__":
  unittest.main()
