from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
STATIC_DIR = BUILD_DIR / "static"


def compact_text(content: str) -> str:
  return "\n".join(line.rstrip() for line in content.splitlines() if line.strip()) + "\n"


def build_asset(logical_name: str, source_path: Path, content: str) -> str:
  digest = sha256(content.encode("utf-8")).hexdigest()[:10]
  built_name = f"{source_path.stem}.{digest}{source_path.suffix}"
  (STATIC_DIR / built_name).write_text(content, encoding="utf-8")
  return f"/static/{built_name}"


def main() -> None:
  if BUILD_DIR.exists():
    shutil.rmtree(BUILD_DIR)

  STATIC_DIR.mkdir(parents=True)
  shutil.copy2(ROOT / "app.py", BUILD_DIR / "app.py")
  shutil.copytree(
    ROOT / "snake_portal",
    BUILD_DIR / "snake_portal",
    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
  )

  logic_source = compact_text((ROOT / "src" / "snake-logic.js").read_text(encoding="utf-8"))
  logic_url = build_asset("snake-logic.js", ROOT / "src" / "snake-logic.js", logic_source)
  logic_file_name = logic_url.removeprefix("/static/")

  game_source = (ROOT / "src" / "snake-game.js").read_text(encoding="utf-8")
  built_game_source = compact_text(game_source.replace("./snake-logic.js", f"./{logic_file_name}"))
  game_url = build_asset("snake-game.js", ROOT / "src" / "snake-game.js", built_game_source)

  styles_source = compact_text((ROOT / "styles.css").read_text(encoding="utf-8"))
  styles_url = build_asset("styles.css", ROOT / "styles.css", styles_source)

  manifest = {
    "snake-game.js": game_url,
    "snake-logic.js": logic_url,
    "styles.css": styles_url,
  }
  (BUILD_DIR / "asset-manifest.json").write_text(
    json.dumps(manifest, indent=2),
    encoding="utf-8",
  )

  print("Build complete.")
  for name, url in manifest.items():
    print(f"- {name}: {url}")


if __name__ == "__main__":
  main()
