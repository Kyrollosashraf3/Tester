# phase2_tester/logs_reader.py
from __future__ import annotations

from typing import Any, Optional

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

    def get_logs(
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

        # Return only required fields (no prompt/response/metadata)
        out: list[dict[str, Optional[str]]] = []
        for l in new_logs:
            lt = l.get("log_type")
            em = l.get("error_message")

            out.append(
                {
                    "log_type": lt if isinstance(lt, str) else None,
                    "error_message": em if isinstance(em, str) and em.strip() else None,
                }
            )

        return out


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
            logs_api_url = "http://localhost:8000/logs/api"
            timeout = 30
            retry = 3

        client = LogsApiClient(logs_api_url=logs_api_url, timeout_sec=timeout, retry_count=retry)
        _reader_singleton = LogsReader(client)

    return _reader_singleton.get_logs(user_id=user_id, session_id=session_id)
