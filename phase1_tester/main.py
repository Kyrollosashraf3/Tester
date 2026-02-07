"""
Phase 1: AI-driven end-to-end conversation tester.

Run:
  Put OPENAI_API_KEY in .env (or export OPENAI_API_KEY=...)
  python -m phase1_tester.main
"""

from dotenv import load_dotenv

load_dotenv()

from phase1_tester.config import (
    API_URL,
    USER_ID,
    OPENAI_MODEL,
    TIMEOUT_SEC,
    RETRY_COUNT,
    MAX_TURNS,
    MAX_TOTAL_SECONDS,
    INITIAL_USER_MESSAGE,
)
from phase1_tester.client import ChatClient
from phase1_tester.driver import LLMDriver
from phase1_tester.orchestration import Orchestrator


def main() -> int:
    chat = ChatClient(API_URL, USER_ID, TIMEOUT_SEC, RETRY_COUNT)
    driver = LLMDriver(OPENAI_MODEL, api_key_env="OPENAI_API_KEY")
    orchestrator = Orchestrator(chat, driver, MAX_TURNS, MAX_TOTAL_SECONDS)
    report = orchestrator.run(INITIAL_USER_MESSAGE)

    print("\n" + "=" * 60)
    print("TRANSCRIPT")
    print("=" * 60)
    #for t in report.turns:
    #    print("done")
        #print(f"[{t.role}] {t.content[:200]}{'...' if len(t.content) > 200 else ''}")
    print("=" * 60)
    if report.final_summary:
        print("FINAL SUMMARY")
        print("=" * 60)
        print(report.final_summary)
        print("=" * 60)
    print("METRICS")
    print("=" * 60)
    print(f"success: {report.success}")
    print(f"turns: {len(report.turns)}")
    print(f"started_at: {report.started_at}")
    print(f"ended_at: {report.ended_at}")
    if report.error:
        print(f"error: {report.error}")
    print("=" * 60)

    return 0 if report.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
