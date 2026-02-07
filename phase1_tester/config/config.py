"""Configuration constants for Phase 1 tester."""

# production
API_URL: str = "https://ai-class-production-01cd.up.railway.app/chat/fast"

# stage
#API_URL: str = "https://ai-class-staging.up.railway.app/chat/fast"

USER_ID: str = "510b6e88-b314-4d66-9fd6-2406d87a8039"
OPENAI_MODEL: str = "gpt-4o"
TIMEOUT_SEC: int = 40
RETRY_COUNT: int = 3
MAX_TURNS: int = 3
MAX_TOTAL_SECONDS: int = 2000
INITIAL_USER_MESSAGE: str = "hello i need to buy a new property for stability"


LOGS_API_URL: str = "https://ai-class-production-01cd.up.railway.app/logs/api"
LOGS_LIMIT: int = 50
