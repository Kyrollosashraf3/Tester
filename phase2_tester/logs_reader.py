# phase2_tester/logs_reader.py
from __future__ import annotations

from typing import Any, Optional
import json
from phase2_tester.logs_client import LogsApiClient


class LogsReader:
    """
    Keeps a per-(user_id, session_id) cursor of the last max log id seen.
    get_logs() returns ONLY new records since last call, but only:
      - log_type
      - error_message (if present)
    """

    def __init__(self, client: LogsApiClient):
        self._client = client
        self._last_max_id: dict[tuple[str, str], int] = {}

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            # Handles "4647" as well
            return int(str(value))
        except Exception:
            return None

    def  get_logs(
        self,
        user_id: str,
        session_id: str,
        limit: int = 200,
        prime_if_first_time: bool = True,
    ) -> list[dict[str, Optional[str]]]:
        """
        Returns:
          [{"log_type": str|None,   "error_message": str|None}, ...]

        - By default, first call for (user_id, session_id) primes cursor and returns [].
          This prevents returning historic logs.
        - Next calls return only what's new (id > last_seen_max_id).
        """
        key = (user_id, session_id)

        resp = self._client.fetch_logs(user_id=user_id, session_id=session_id, limit=limit)
        if not resp.success or not resp.logs:
            return []

        # Collect ids present in the payload
        ids: list[int] = []
        for l in resp.logs:
            log_id = self._safe_int(l.get("id"))
            if log_id is not None:
                ids.append(log_id)

        if not ids:
            return []

        current_max_id = max(ids)
        prev_max_id = self._last_max_id.get(key)

        # Update cursor immediately
        self._last_max_id[key] = current_max_id

        # Prime on first call (default behavior)
        if prev_max_id is None and prime_if_first_time:
            return []

        # If prev_max_id is None but we don't want priming, treat it as 0
        if prev_max_id is None:
            prev_max_id = 0

        # Filter only NEW logs
        new_logs: list[dict[str, Any]] = []
        for l in resp.logs:
            log_id = self._safe_int(l.get("id"))
            if log_id is not None and log_id > prev_max_id:
                new_logs.append(l)

        if not new_logs:
            return []

        # Sort ascending by id for stable chronological output
        new_logs.sort(key=lambda x: self._safe_int(x.get("id")) or 0)
        
        out = self.prepere_logs(new_logs)

        return out 

    def prepere_logs(self, new_logs) -> dict[str, Any]:

        
        #
        intent_response: str | None = None
        extraction_answers: list[str] = []
        error_messages: list[str] = []

        for l in new_logs:
            logtype = l.get("log_type")
            raw_resp = l.get("response")
            log_error = l.get("error_message")

            # -------- collect error_message from ANY log --------
            if isinstance(log_error, str) and log_error.strip():
                error_messages.append(log_error.strip())

            
            # -------- intent_classifier (always expected) --------
            if logtype == "intent_classifier":
                if isinstance(raw_resp, str) and raw_resp.strip():
                    intent_response = raw_resp.strip()
                continue

            # -------- extraction_model (optional) --------
            if logtype == "extraction_model":
                if not isinstance(raw_resp, str) or not raw_resp.strip():
                    continue

                try:
                    data = json.loads(raw_resp)
                except Exception:
                    continue

                answers = data.get("answers")
                if not isinstance(answers, list) or len(answers) == 0:
                    continue  
                for a in answers:
                    if isinstance(a, dict) and a.get("answer") is not None:
                        extraction_answers.append(str(a["answer"]))

        # -------- build final output --------
        out: dict[str, Any] = {
            "log_type": ["main_model", "intent_classifier"],
            "intent_classifier": intent_response,
        }

        if extraction_answers:
            out["log_type"].append("extraction_model")
            out["extraction_answers"] = extraction_answers

        if error_messages:
            out["log_type"].append("error")
             
            out["error_message"] = " | ".join(dict.fromkeys(error_messages))
        

        # default: include type once
        if logtype not in out["log_type"]:
                out["log_type"].append(logtype if isinstance(logtype, str) else "unknown")
        
        
        
        
        print("+++ out : ", out)
        return [out]
    


# Convenience singleton function: def get_logs()
_reader_singleton: Optional[LogsReader] = None


def get_logs(user_id: str, session_id: str) -> list[dict[str, Optional[str]]]:
    """
    Drop-in helper returning only:
      [{"log_type": ..., "error_message": ...}, ...]
    For NEW logs since last call for same (user_id, session_id).
    """
    global _reader_singleton

    if _reader_singleton is None:
        try:
            from phase1_tester.config.config import LOGS_API_URL, TIMEOUT_SEC, RETRY_COUNT  # type: ignore

            logs_api_url = LOGS_API_URL
            timeout = TIMEOUT_SEC
            retry = RETRY_COUNT
        except Exception:
            timeout = 30
            retry = 3

        client = LogsApiClient(logs_api_url=logs_api_url, timeout_sec=timeout, retry_count=retry)
        _reader_singleton = LogsReader(client)

    return _reader_singleton.get_logs(user_id=user_id, session_id=session_id)
