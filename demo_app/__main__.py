"""python -m demo_app [--host 127.0.0.1] [--port 8000] [--offline] [--no-warm]"""

from __future__ import annotations

import argparse
import sys

import uvicorn

from .server import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m demo_app", description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--offline", action="store_true", help="safety-net mode: no Azure at all")
    parser.add_argument("--no-warm", action="store_true", help="do not pre-run the five personas at startup")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Starting the demo app (checking Azure OpenAI first, this takes a few seconds)...")
    app = create_app(offline=args.offline, warm=not args.no_warm)
    health = app.state.service.health()
    label = ("Azure OpenAI live: chat=%s, embeddings=%s" % (health["deployments"]["chat"], health["deployments"]["embeddings"])
             if health["mode"] == "azure" else "OFFLINE MODE - no Azure")
    print(f"Mode: {label}")
    if health.get("degraded_reason"):
        print(f"Note: {health['degraded_reason']}")
    print(f"Open http://{args.host}:{args.port}  (Ctrl+C to stop)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
