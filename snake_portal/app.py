from __future__ import annotations

from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs
import json
import mimetypes

from .auth import AuthStore, SESSION_TTL, ValidationError
from .views import render_dashboard_page, render_login_page, render_register_page


@dataclass
class Response:
  status: str
  headers: list[tuple[str, str]]
  body: bytes


def create_app(*, root_dir: str | Path | None = None, db_path: str | Path | None = None) -> "SnakePortalApp":
  base_dir = Path(root_dir) if root_dir else Path(__file__).resolve().parents[1]
  database_path = Path(db_path) if db_path else base_dir / "data" / "app.db"
  return SnakePortalApp(root_dir=base_dir, db_path=database_path)


class SnakePortalApp:
  def __init__(self, *, root_dir: Path, db_path: Path):
    self.root_dir = root_dir
    self.db_path = db_path
    self.auth_store = AuthStore(db_path)
    self.asset_manifest = self._load_asset_manifest()

  def __call__(self, environ: dict, start_response):
    response = self.dispatch(environ)
    start_response(response.status, response.headers)
    return [response.body]

  def dispatch(self, environ: dict) -> Response:
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")
    user = self.current_user(environ)

    if path == "/":
      return self.redirect("/app" if user else "/login")

    if path.startswith("/static/"):
      return self.serve_static(path.removeprefix("/static/"))

    if path == "/health":
      return self.text_response("200 OK", "ok", "text/plain; charset=utf-8")

    if path == "/login":
      if method == "GET":
        if user:
          return self.redirect("/app")
        return self.html_response(render_login_page(styles_href=self.asset_url("styles.css")))
      if method == "POST":
        return self.handle_login(environ)
      return self.method_not_allowed(["GET", "POST"])

    if path == "/register":
      if method == "GET":
        if user:
          return self.redirect("/app")
        return self.html_response(render_register_page(styles_href=self.asset_url("styles.css")))
      if method == "POST":
        return self.handle_register(environ)
      return self.method_not_allowed(["GET", "POST"])

    if path == "/logout":
      if method != "POST":
        return self.method_not_allowed(["POST"])
      return self.handle_logout(environ)

    if path == "/app":
      if not user:
        return self.redirect("/login")
      return self.html_response(
        render_dashboard_page(
          styles_href=self.asset_url("styles.css"),
          snake_script_href=self.asset_url("snake-game.js"),
          user=user,
        )
      )

    return self.text_response("404 Not Found", "Not found", "text/plain; charset=utf-8")

  def handle_login(self, environ: dict) -> Response:
    form = self.parse_form(environ)
    email = form.get("email", "").strip()
    password = form.get("password", "")
    user = self.auth_store.authenticate_user(email, password)

    if user is None:
      return self.html_response(
        render_login_page(
          styles_href=self.asset_url("styles.css"),
          error="Email or password was incorrect.",
          email=email,
        ),
        status="401 Unauthorized",
      )

    token, _expires_at = self.auth_store.create_session(user.id)
    return self.redirect("/app", headers=[("Set-Cookie", self.session_cookie(token))])

  def handle_register(self, environ: dict) -> Response:
    form = self.parse_form(environ)
    try:
      user = self.auth_store.register_user(
        username=form.get("username", ""),
        email=form.get("email", ""),
        password=form.get("password", ""),
        confirm_password=form.get("confirm_password", ""),
      )
    except ValidationError as error:
      return self.html_response(
        render_register_page(
          styles_href=self.asset_url("styles.css"),
          error=str(error),
          username=form.get("username", ""),
          email=form.get("email", ""),
        ),
        status="400 Bad Request",
      )

    token, _expires_at = self.auth_store.create_session(user.id)
    return self.redirect("/app", headers=[("Set-Cookie", self.session_cookie(token))])

  def handle_logout(self, environ: dict) -> Response:
    token = self.session_token(environ)
    self.auth_store.delete_session(token)
    return self.redirect("/login", headers=[("Set-Cookie", self.expired_session_cookie())])

  def current_user(self, environ: dict):
    return self.auth_store.get_user_for_session(self.session_token(environ))

  def session_token(self, environ: dict) -> str | None:
    cookie = SimpleCookie()
    cookie.load(environ.get("HTTP_COOKIE", ""))
    morsel = cookie.get("session_token")
    return morsel.value if morsel else None

  def session_cookie(self, token: str) -> str:
    max_age = int(SESSION_TTL.total_seconds())
    return f"session_token={token}; HttpOnly; Max-Age={max_age}; Path=/; SameSite=Lax"

  def expired_session_cookie(self) -> str:
    return "session_token=; HttpOnly; Max-Age=0; Path=/; SameSite=Lax"

  def parse_form(self, environ: dict) -> dict[str, str]:
    content_length = int(environ.get("CONTENT_LENGTH") or 0)
    raw_body = environ["wsgi.input"].read(content_length) if content_length else b""
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0].strip() for key, values in parsed.items()}

  def serve_static(self, file_name: str) -> Response:
    file_path: Path | None = None
    built_file = self.root_dir / "static" / file_name
    if built_file.exists():
      file_path = built_file
    else:
      source_assets = {
        "styles.css": self.root_dir / "styles.css",
        "snake-game.js": self.root_dir / "src" / "snake-game.js",
        "snake-logic.js": self.root_dir / "src" / "snake-logic.js",
      }
      file_path = source_assets.get(file_name)

    if file_path is None or not file_path.exists():
      return self.text_response("404 Not Found", "Static file not found", "text/plain; charset=utf-8")

    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    return Response(
      status="200 OK",
      headers=[("Content-Type", f"{content_type}; charset=utf-8")],
      body=file_path.read_bytes(),
    )

  def asset_url(self, logical_name: str) -> str:
    return self.asset_manifest.get(logical_name, f"/static/{logical_name}")

  def _load_asset_manifest(self) -> dict[str, str]:
    manifest_path = self.root_dir / "asset-manifest.json"
    if not manifest_path.exists():
      return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))

  def html_response(self, markup: str, *, status: str = "200 OK") -> Response:
    return self.text_response(status, markup, "text/html; charset=utf-8")

  def text_response(self, status: str, content: str, content_type: str) -> Response:
    return Response(
      status=status,
      headers=[("Content-Type", content_type)],
      body=content.encode("utf-8"),
    )

  def redirect(self, location: str, *, headers: list[tuple[str, str]] | None = None) -> Response:
    response_headers = [("Location", location)]
    if headers:
      response_headers.extend(headers)
    return Response(status="303 See Other", headers=response_headers, body=b"")

  def method_not_allowed(self, methods: list[str]) -> Response:
    return Response(
      status="405 Method Not Allowed",
      headers=[("Allow", ", ".join(methods)), ("Content-Type", "text/plain; charset=utf-8")],
      body=b"Method not allowed",
    )
