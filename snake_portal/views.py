from __future__ import annotations

from html import escape

from .auth import User


def render_layout(
  *,
  title: str,
  body: str,
  styles_href: str,
  user: User | None = None,
  page_script: str | None = None,
) -> str:
  auth_links = (
    f"""
    <div class="nav-actions">
      <span class="nav-user">Signed in as <strong>{escape(user.username)}</strong></span>
      <form method="post" action="/logout">
        <button type="submit">Log out</button>
      </form>
    </div>
    """
    if user
    else """
    <div class="nav-actions">
      <a href="/login">Login</a>
      <a href="/register">Register</a>
    </div>
    """
  )
  script_tag = f'<script type="module" src="{page_script}"></script>' if page_script else ""
  return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="{styles_href}" />
  </head>
  <body>
    <div class="site-shell">
      <div class="page">
        <header class="site-header">
          <a class="brand" href="/">Aravind's Snake App</a>
          {auth_links}
        </header>
        {body}
      </div>
    </div>
    {script_tag}
  </body>
</html>
"""


def render_login_page(*, styles_href: str, error: str | None = None, email: str = "") -> str:
  notice = f'<p class="notice notice-error">{escape(error)}</p>' if error else ""
  body = f"""
  <main class="auth-shell">
    <section class="auth-card">
      <div>
        <p class="eyebrow">Local build-enabled app</p>
        <h1>Welcome back</h1>
        <p class="subtitle">Sign in to reach the protected Snake dashboard.</p>
      </div>
      {notice}
      <form method="post" action="/login" class="form-stack">
        <label class="field">
          <span>Email</span>
          <input type="email" name="email" value="{escape(email)}" required />
        </label>
        <label class="field">
          <span>Password</span>
          <input type="password" name="password" minlength="8" required />
        </label>
        <button type="submit">Login</button>
      </form>
      <p class="switch-copy">Need an account? <a href="/register">Create one</a>.</p>
    </section>
  </main>
  """
  return render_layout(title="Login", body=body, styles_href=styles_href)


def render_register_page(
  *,
  styles_href: str,
  error: str | None = None,
  username: str = "",
  email: str = "",
) -> str:
  notice = f'<p class="notice notice-error">{escape(error)}</p>' if error else ""
  body = f"""
  <main class="auth-shell">
    <section class="auth-card">
      <div>
        <p class="eyebrow">SQLite-backed authentication</p>
        <h1>Create your account</h1>
        <p class="subtitle">Register, sign in, and then play Snake from the protected dashboard.</p>
      </div>
      {notice}
      <form method="post" action="/register" class="form-stack">
        <label class="field">
          <span>Username</span>
          <input type="text" name="username" value="{escape(username)}" maxlength="24" required />
        </label>
        <label class="field">
          <span>Email</span>
          <input type="email" name="email" value="{escape(email)}" required />
        </label>
        <label class="field">
          <span>Password</span>
          <input type="password" name="password" minlength="8" required />
        </label>
        <label class="field">
          <span>Confirm password</span>
          <input type="password" name="confirm_password" minlength="8" required />
        </label>
        <button type="submit">Register</button>
      </form>
      <p class="switch-copy">Already registered? <a href="/login">Sign in</a>.</p>
    </section>
  </main>
  """
  return render_layout(title="Register", body=body, styles_href=styles_href)


def render_dashboard_page(*, styles_href: str, snake_script_href: str, user: User) -> str:
  body = f"""
  <main class="dashboard">
    <section class="hero-card">
      <div>
        <p class="eyebrow">Protected app area</p>
        <h1>Hi, {escape(user.username)}</h1>
        <p class="subtitle">Your login is stored in SQLite and your session keeps the Snake board behind auth.</p>
      </div>
      <div class="meta-grid">
        <div class="meta-card">
          <span class="meta-label">Database</span>
          <strong>SQLite</strong>
        </div>
        <div class="meta-card">
          <span class="meta-label">Workflow</span>
          <strong>Register → Login → Play</strong>
        </div>
        <div class="meta-card">
          <span class="meta-label">Build</span>
          <strong>`python scripts/build.py`</strong>
        </div>
      </div>
    </section>

    <div class="dashboard-grid">
      <aside class="info-card">
        <h2>Account</h2>
        <dl class="details">
          <div>
            <dt>Username</dt>
            <dd>{escape(user.username)}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{escape(user.email)}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{escape(user.created_at)}</dd>
          </div>
        </dl>
        <p class="helper-copy">The app uses PBKDF2 password hashing, cookie-based sessions, and an automatically initialized local database.</p>
      </aside>

      <section class="game-panel" aria-label="Snake game">
        <header class="game-header">
          <div>
            <h2>Snake</h2>
            <p class="subtitle">Classic grid movement, now inside the authenticated app.</p>
          </div>
          <div class="scoreboard" aria-live="polite">
            <div class="score-item">
              <span class="score-label">Score</span>
              <strong id="score">0</strong>
            </div>
            <div class="score-item">
              <span class="score-label">Best</span>
              <strong id="best-score">0</strong>
            </div>
          </div>
        </header>

        <section class="status-row">
          <p id="status" class="status">Press any arrow key or WASD to start.</p>
          <div class="actions">
            <button id="pause-button" type="button">Pause</button>
            <button id="restart-button" type="button">Restart</button>
          </div>
        </section>

        <div id="board" class="board" role="grid" aria-label="Snake board" tabindex="0"></div>

        <section class="controls" aria-label="Touch controls">
          <button type="button" data-direction="up" aria-label="Move up">Up</button>
          <div class="controls-row">
            <button type="button" data-direction="left" aria-label="Move left">Left</button>
            <button type="button" data-direction="down" aria-label="Move down">Down</button>
            <button type="button" data-direction="right" aria-label="Move right">Right</button>
          </div>
        </section>

        <p class="hint">Controls: Arrow keys or WASD. Press Space or P to pause.</p>
      </section>
    </div>
  </main>
  """
  return render_layout(
    title="Dashboard",
    body=body,
    styles_href=styles_href,
    user=user,
    page_script=snake_script_href,
  )
