from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import hmac
import re
import secrets
import sqlite3

PBKDF2_ITERATIONS = 310_000
SESSION_TTL = timedelta(days=7)
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,24}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  token TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
"""


@dataclass(frozen=True)
class User:
  id: int
  username: str
  email: str
  created_at: str


class ValidationError(ValueError):
  pass


def utcnow_iso() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_email(email: str) -> str:
  return email.strip().lower()


def hash_password(password: str, salt: bytes | None = None) -> str:
  chosen_salt = salt or secrets.token_bytes(16)
  digest = hashlib.pbkdf2_hmac(
    "sha256",
    password.encode("utf-8"),
    chosen_salt,
    PBKDF2_ITERATIONS,
  )
  return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${chosen_salt.hex()}${digest.hex()}"


def verify_password(stored_password: str, password: str) -> bool:
  algorithm, iteration_text, salt_hex, digest_hex = stored_password.split("$", 3)
  if algorithm != "pbkdf2_sha256":
    return False

  derived = hashlib.pbkdf2_hmac(
    "sha256",
    password.encode("utf-8"),
    bytes.fromhex(salt_hex),
    int(iteration_text),
  )
  return hmac.compare_digest(derived.hex(), digest_hex)


def validate_registration(username: str, email: str, password: str, confirm_password: str) -> None:
  cleaned_username = username.strip()
  if not USERNAME_RE.fullmatch(cleaned_username):
    raise ValidationError("Username must be 3-24 characters and use letters, numbers, or underscores.")

  cleaned_email = normalize_email(email)
  if not EMAIL_RE.fullmatch(cleaned_email):
    raise ValidationError("Enter a valid email address.")

  if len(password) < 8:
    raise ValidationError("Password must be at least 8 characters long.")

  if password != confirm_password:
    raise ValidationError("Passwords do not match.")


class AuthStore:
  def __init__(self, db_path: str | Path):
    self.db_path = str(db_path)
    self.uses_uri = self.db_path.startswith("file:")
    self._keepalive_connection: sqlite3.Connection | None = None
    if not self.uses_uri:
      Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    else:
      self._keepalive_connection = self._create_connection()
    self.initialize()

  def _create_connection(self) -> sqlite3.Connection:
    connection = sqlite3.connect(self.db_path, uri=self.uses_uri)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

  def connect(self) -> sqlite3.Connection:
    return self._create_connection()

  def initialize(self) -> None:
    with closing(self.connect()) as connection, connection:
      connection.executescript(SCHEMA)

  def register_user(self, username: str, email: str, password: str, confirm_password: str) -> User:
    validate_registration(username, email, password, confirm_password)
    cleaned_username = username.strip()
    cleaned_email = normalize_email(email)
    password_hash = hash_password(password)
    created_at = utcnow_iso()

    try:
      with closing(self.connect()) as connection, connection:
        cursor = connection.execute(
          """
          INSERT INTO users (username, email, password_hash, created_at)
          VALUES (?, ?, ?, ?)
          """,
          (cleaned_username, cleaned_email, password_hash, created_at),
        )
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
      message = str(error).lower()
      if "users.username" in message:
        raise ValidationError("That username is already taken.") from error
      if "users.email" in message:
        raise ValidationError("That email is already registered.") from error
      raise

    return self.get_user_by_id(user_id)

  def get_user_by_id(self, user_id: int) -> User:
    with closing(self.connect()) as connection:
      row = connection.execute(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (user_id,),
      ).fetchone()

    if row is None:
      raise ValidationError("User was not found.")

    return User(**dict(row))

  def authenticate_user(self, email: str, password: str) -> User | None:
    cleaned_email = normalize_email(email)
    with closing(self.connect()) as connection:
      row = connection.execute(
        """
        SELECT id, username, email, created_at, password_hash
        FROM users
        WHERE email = ?
        """,
        (cleaned_email,),
      ).fetchone()

    if row is None or not verify_password(row["password_hash"], password):
      return None

    return User(
      id=row["id"],
      username=row["username"],
      email=row["email"],
      created_at=row["created_at"],
    )

  def create_session(self, user_id: int) -> tuple[str, datetime]:
    self.cleanup_expired_sessions()
    token = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + SESSION_TTL

    with closing(self.connect()) as connection, connection:
      connection.execute(
        """
        INSERT INTO sessions (user_id, token, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, token, created_at.strftime("%Y-%m-%dT%H:%M:%SZ"), expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")),
      )

    return token, expires_at

  def get_user_for_session(self, token: str | None) -> User | None:
    if not token:
      return None

    self.cleanup_expired_sessions()
    with closing(self.connect()) as connection:
      row = connection.execute(
        """
        SELECT users.id, users.username, users.email, users.created_at
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token = ?
        """,
        (token,),
      ).fetchone()

    if row is None:
      return None

    return User(**dict(row))

  def delete_session(self, token: str | None) -> None:
    if not token:
      return

    with closing(self.connect()) as connection, connection:
      connection.execute("DELETE FROM sessions WHERE token = ?", (token,))

  def cleanup_expired_sessions(self) -> None:
    with closing(self.connect()) as connection, connection:
      connection.execute(
        "DELETE FROM sessions WHERE expires_at <= ?",
        (utcnow_iso(),),
      )

  def close(self) -> None:
    if self._keepalive_connection is not None:
      self._keepalive_connection.close()
      self._keepalive_connection = None
