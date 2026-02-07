# phase2_tester/logs_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests


@dataclass
class LogsApiResponse:
    success: bool
    logs: list[dict[str, Any]]
    count: int = 0
    error: Optional[str] = None


class LogsApiClient:
    """
    Thin client for the real_estate logs endpoint: GET /logs/api
    Query params: user_id, session_id, limit, (optional) log_type
    """

    def __init__(self, logs_api_url: str, timeout_sec: int = 30, retry_count: int = 1):
        self.logs_api_url = logs_api_url
        self.timeout_sec = timeout_sec
        self.retry_count = retry_count

    def fetch_logs(
        self,
        user_id: str,
        session_id: str,
        limit: int = 200,
        log_type: Optional[str] = None,
    ) -> LogsApiResponse:
        
        params: dict[str, Any] = {"user_id": user_id, "session_id": session_id, "limit": limit}
        #if log_type:
        #    params["log_type"] = log_type

        last_error: Optional[Exception] = None
        for _ in range(self.retry_count):
            try:
                resp = requests.get(self.logs_api_url, params=params, timeout=self.timeout_sec)
                resp.raise_for_status()
                data = resp.json()

                if not isinstance(data, dict):
                    return LogsApiResponse(False, [], error="Invalid JSON shape (not dict).")

                success = bool(data.get("success"))
                logs = data.get("logs") or []
                if not isinstance(logs, list):
                    logs = []

                return LogsApiResponse(
                    success=success,
                    logs=logs,
                    count=int(data.get("count") or len(logs)),
                    error=data.get("error"),
                )
            except Exception as e:
                last_error = e

        return LogsApiResponse(False, [], error=str(last_error) if last_error else "Unknown error")
