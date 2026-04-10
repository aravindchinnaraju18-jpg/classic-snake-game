from argparse import ArgumentParser
from pathlib import Path
from wsgiref.simple_server import make_server

from snake_portal.app import create_app


def main() -> None:
  parser = ArgumentParser(description="Run Aravind's Snake App.")
  parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
  parser.add_argument("--port", default=8000, type=int, help="Port to listen on.")
  parser.add_argument(
    "--db",
    default=str(Path("data") / "app.db"),
    help="SQLite database path.",
  )
  args = parser.parse_args()

  app = create_app(root_dir=Path(__file__).resolve().parent, db_path=args.db)

  with make_server(args.host, args.port, app) as server:
    print(f"Serving Aravind's Snake App on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
  main()
