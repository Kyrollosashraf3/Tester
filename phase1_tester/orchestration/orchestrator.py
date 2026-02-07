"""Orchestrator: run the conversation loop until summary or limits."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from phase1_tester.config.types import RunReport, Turn
from phase1_tester.config.config import LOGS_API_URL, LOGS_LIMIT

from phase1_tester.persona.persona import persona_context, is_question, stop_condition

from phase2_tester.logs_client import LogsApiClient
from phase2_tester.logs_reader import LogsReader

if TYPE_CHECKING:
    from phase1_tester.client.chat_client import ChatClient
    from phase1_tester.driver.llm_driver import LLMDriver


class Orchestrator:
    """Runs the chat loop: send user message, get assistant, decide next or stop."""

    def __init__(
        self,
        chat: "ChatClient",
        driver: "LLMDriver",
        max_turns: int,
        max_total_seconds: int,
    ):
        self.chat = chat
        self.driver = driver
        self.max_turns = max_turns
        self.max_total_seconds = max_total_seconds

    def run(self, initial_user_message: str) -> RunReport:
        """Run the conversation until stop condition or limits. Return RunReport."""
        started_at = datetime.utcnow()
        turns: list[Turn] = []
        session_id: Optional[str] = None
        persona = persona_context()
        current_user_message = initial_user_message

        # --- NEW: init logs reader once ---
        # reuse chat client's timeout/retry  
        timeout_sec = getattr(self.chat, "timeout_sec", 30)
        retry_count = getattr(self.chat, "retry_count", 1)

        logs_client = LogsApiClient(
            logs_api_url=LOGS_API_URL,
            timeout_sec=timeout_sec,
            retry_count=retry_count,
        )
        logs_reader = LogsReader(logs_client)

        try:
            for turn_index in range(self.max_turns):

                # 1) If timeout: stop
                elapsed = (datetime.utcnow() - started_at).total_seconds()
                if elapsed >= self.max_total_seconds:
                    return RunReport(
                        success=False,
                        turns=turns,
                        final_summary=None,
                        started_at=started_at,
                        ended_at=datetime.utcnow(),
                        error="max_total_seconds exceeded",
                    )

                turns.append(Turn(role="user", content=current_user_message, ts=datetime.utcnow()))
                print(f"Turn {turn_index + 1}: user msg (len={len(current_user_message)})")

                # 2) send message (SSE)
                result = self.chat.send_message(current_user_message, session_id )
                session_id = result.session_id or session_id

                assistant_text = result.assistant_text.strip()
                print("assistant_text: " , assistant_text)

                turns.append(Turn(role="assistant", content=assistant_text, ts=datetime.utcnow()))

                # --- read logs for THIS message only ---
                # We rely on cursor-by-max-id. Since session starts new (session_id=None),
                # first call should safely return logs for first message too, so prime_if_first_time=False.
                try:
                    user_id = getattr(self.chat, "user_id", None)
                    if user_id and session_id:
                        new_logs = logs_reader.get_logs(
                            user_id=user_id,
                            session_id=session_id,
                            limit=LOGS_LIMIT,
                            prime_if_first_time=False if turn_index == 0 else True,
                        )

                        if new_logs:
                            print("  logs:")
                            for item in new_logs:
                                lt = item.get("log_type")
                                em = item.get("error_message")
                                if em:
                                    print(f"    - {lt} | error: {em}")
                                else:
                                    print(f"    - {lt}")
                        else:
                            print("  logs: (no new logs)")
                    else:
                        print("  logs: (missing user_id or session_id)")
                except Exception as _e:

                    print("  logs: (failed to read logs)")

                # 3) determine if response is Q or stop
                is_q = is_question(assistant_text)
                stopped = stop_condition(assistant_text)
                print(
                    f"  assistant len={len(assistant_text)}, is_question={is_q}, "
                    f"stop_condition={stopped}, session_id={session_id}"
                )

                # if stopped:
                #     return RunReport(
                #         success=True,
                #         turns=turns,
                #         final_summary=assistant_text,
                #         started_at=started_at,
                #         ended_at=datetime.utcnow(),
                #         error=None,
                #     )

                if is_q:
                    recent = turns[-10:] if len(turns) >= 10 else turns
                    current_user_message = self.driver.generate_reply(persona, assistant_text, recent)
                    if not current_user_message:
                        current_user_message = "I'm not sure what to say."
                else:
                    current_user_message = "Okay."

                print("current_user_message: ", current_user_message)
                print("+*+*+*+*+*+**+*+*+*+*+*+*+*+*+*+*+*+*+*+*********")

            return RunReport(
                success=False,
                turns=turns,
                final_summary=None,
                started_at=started_at,
                ended_at=datetime.utcnow(),
                error="max_turns exceeded",
            )
        except Exception as e:
            return RunReport(
                success=False,
                turns=turns,
                final_summary=None,
                started_at=started_at,
                ended_at=datetime.utcnow(),
                error=str(e),
            )
