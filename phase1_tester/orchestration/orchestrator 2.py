"""Orchestrator: run the conversation loop until summary or limits."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from phase1_tester.config.types import RunReport, Turn
from phase1_tester.config.config import LOGS_API_URL, LOGS_LIMIT

from phase1_tester.persona.persona import persona_context, is_question, stop_condition

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
        user = []
        AI = []


        try:
            for turn_index in range(self.max_turns):
                
                # 1- If timeout : stop
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
                print(
                    f"Turn {turn_index + 1}: user msg (len={len(current_user_message)})"
                )

                
                # 2- start chat send the first message to endpoint - take the chat response assistant_text 
                result = self.chat.send_message(current_user_message, session_id)
                session_id = result.session_id or session_id
                assistant_text = result.assistant_text.strip()
                turns.append(
                    Turn(role="assistant", content=assistant_text, ts=datetime.utcnow())
                )
                

                # Read logs: 
                """
                from phase1_tester.config.config import LOGS_API_URL, LOGS_LIMIT

                logs_payload = self.chat.fetch_logs(LOGS_API_URL, session_id=result.session_id or session_id, limit=LOGS_LIMIT)
                if logs_payload.get("success"):
                    logs = logs_payload.get("logs", [])
                    print(f"  logs_count={len(logs)}")
                 
                
                # check logs
                    if logs:
                        last = logs[0]  
                        print("  last_log_type:", last.get("log_type"))
                else:
                    print("  logs_error:", logs_payload.get("error"))

                    """

                # 3- detrmine if response was Q :generate reply -- summary : stop , print summary
                is_q = is_question(assistant_text)
                stopped = stop_condition(assistant_text)
                print(
                    f"  assistant len={len(assistant_text)}, is_question={is_q}, stop_condition={stopped}, session_id={session_id}"
                )

#                if stopped:
#                    return RunReport(
#                        success=True,
#                        turns=turns,
#                        final_summary=assistant_text,
#                        started_at=started_at,
#                        ended_at=datetime.utcnow(),
#                        error=None,
#                    )
                
                if is_q:
                    recent = turns[-10:] if len(turns) >= 10 else turns
                    current_user_message = self.driver.generate_reply(
                        persona, assistant_text, recent
                    )
                    
                    if not current_user_message:
                        current_user_message = "I'm not sure what to say."
                else:
                    current_user_message = "Okay."



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
