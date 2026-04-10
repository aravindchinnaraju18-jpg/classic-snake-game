from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
import unittest
from uuid import uuid4

from snake_portal.app import create_app


def request(app, path: str, *, method: str = "GET", form: dict[str, str] | None = None, cookie: str | None = None):
  encoded = urlencode(form or {}).encode("utf-8")
  environ = {
    "REQUEST_METHOD": method,
    "PATH_INFO": path,
    "QUERY_STRING": "",
    "SERVER_NAME": "localhost",
    "SERVER_PORT": "8000",
    "wsgi.version": (1, 0),
    "wsgi.url_scheme": "http",
    "wsgi.input": BytesIO(encoded),
    "wsgi.errors": BytesIO(),
    "wsgi.multithread": False,
    "wsgi.multiprocess": False,
    "wsgi.run_once": False,
    "CONTENT_LENGTH": str(len(encoded)),
    "CONTENT_TYPE": "application/x-www-form-urlencoded",
  }
  if cookie:
    environ["HTTP_COOKIE"] = cookie

  captured: dict[str, object] = {}

  def start_response(status, headers):
    captured["status"] = status
    captured["headers"] = headers

  body = b"".join(app(environ, start_response)).decode("utf-8")
  return captured["status"], captured["headers"], body


class AppTests(unittest.TestCase):
  def setUp(self) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    self.app = create_app(
      root_dir=repo_root,
      db_path=f"file:app-tests-{uuid4().hex}?mode=memory&cache=shared",
    )
    self.addCleanup(self.app.auth_store.close)

  def test_login_page_renders(self) -> None:
    status, _headers, body = request(self.app, "/login")
    self.assertEqual(status, "200 OK")
    self.assertIn("Welcome back", body)

  def test_protected_page_redirects_without_session(self) -> None:
    status, headers, _body = request(self.app, "/app")
    self.assertEqual(status, "303 See Other")
    self.assertIn(("Location", "/login"), headers)

  def test_register_login_logout_flow(self) -> None:
    status, headers, _body = request(
      self.app,
      "/register",
      method="POST",
      form={
        "username": "aravind",
        "email": "aravind@example.com",
        "password": "password123",
        "confirm_password": "password123",
      },
    )
    self.assertEqual(status, "303 See Other")

    cookie_header = next(value for name, value in headers if name == "Set-Cookie")
    session_cookie = cookie_header.split(";", 1)[0]

    status, _headers, body = request(self.app, "/app", cookie=session_cookie)
    self.assertEqual(status, "200 OK")
    self.assertIn("Hi, aravind", body)
    self.assertIn('id="board"', body)

    status, headers, _body = request(self.app, "/logout", method="POST", cookie=session_cookie)
    self.assertEqual(status, "303 See Other")
    self.assertIn(("Location", "/login"), headers)


if __name__ == "__main__":
  unittest.main()
