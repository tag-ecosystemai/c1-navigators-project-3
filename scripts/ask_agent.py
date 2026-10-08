"""Ask an analyst-assistant questions about the policies and the golden cases (needs Azure OpenAI).

    python scripts/ask_agent.py                                   # interactive, type 'exit' to quit
    python scripts/ask_agent.py -q "Why was CUST-GOLD-002 declined? Cite the policy."

The agent answers only from its tools (search_policies, check_policy_compliance, get_case_report),
cites rule codes, and never changes the decision. It uses function calling, so there is no offline mode.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_engineering.demo.agent import MAX_TOOL_LOOPS, new_conversation, run_turn  # noqa: E402
from ai_engineering.demo.session import PreflightFailed, start_session  # noqa: E402
from ai_engineering.rag.azure_errors import AzureCallError  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-q", "--question", help="ask one question and exit")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        session = start_session(require_azure=True)
    except PreflightFailed as exc:
        print("The analyst agent requires Azure OpenAI (it uses function calling); there is no offline mode.\n"
              "Run `python -m ai_engineering.rag.cli doctor` after filling in .env.\n", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 2

    print(f"{session.banner}\nAnalyst assistant (answers only from policy/report tools; max {MAX_TOOL_LOOPS} tool rounds per question).")
    messages = new_conversation()

    def ask(question: str) -> None:
        try:
            print("\n" + run_turn(session.llm.client, session.llm.model, messages, question) + "\n")
        except AzureCallError as exc:
            print(f"\nAzure OpenAI error: {exc}\n", file=sys.stderr)

    if args.question:
        ask(args.question)
        return 0
    while True:
        try:
            question = input("analyst> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in {"exit", "quit"}:
            return 0
        if question:
            ask(question)


if __name__ == "__main__":
    sys.exit(main())
