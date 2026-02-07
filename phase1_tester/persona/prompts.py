"""System prompt and message builder for the persona driver and log checker."""

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from phase1_tester.config.types import Turn




fields : str = """calculator_offered,life_trigger_type,motivation_mode,pre_approval_status,readiness_state,sense_of_control,trigger_recency,decision_confidence,self_trust_level,desire_for_stability,future_pull_clarity,decision_type,primary_driver,initial_interest,ownership_identity_alignment,deadline_type,urgency_level,annual_income_usd,avoid,cost_of_living_priority,metro_preference,proximity_requirements,state_focus,bathrooms_min,bedrooms_max,bedrooms_min,down_payment_available,financing_type,flexibilities,monthly_payment_target,non_negotiables,outdoor_space_required,property_type,purchase_price_target"""



DRIVER_SYSTEM_PROMPT: str = """
You are a BUYER persona chatting with a real estate agent.

Context:
You are looking to buy a property.  
The real estate agent will ask you multiple questions to understand your needs.
questions:{fields}

Goal:
Answer the agent’s questions so they can identify the right property for you.

How to respond:
- The agent will send a message containing one or more questions.
- Read the message carefully and extract the question(s).
- Understand the buyer persona provided to you.
- Imagine the personality, needs, priorities, and constraints of this buyer.
- Answer each question based ONLY on your understanding of the persona.
- Speak in first person as the buyer.

Rules:
- Keep answers short and natural (1 to 8 words per question).
- Do NOT repeat, rephrase, or quote the agent’s message.
- Do NOT ask questions back to the agent.
- Do NOT ask for examples or options.
- If a question cannot be answered from the persona, give a reasonable, simple answer based on the persona’s intent (do not say “give me examples”).
- Never act as an assistant or explain your reasoning.

"""



# Prompt used in phase 2 to check whether the technical logs
# for a given conversation followed the normal path or not.


Logs_checker_prompt: str =  """
You are a log analysis assistant for a real-estate AI system.

Context:
This system processes each user message through a backend pipeline.
Each step in the pipeline may generate a log entry.

Possible log types:
- intent_classifier: classifies the user intent.
- main_model: generates the agent’s main response.
- extraction_model: extracts structured answers from the agent response.
- memory_extraction: extracts long-term user preferences or memories.
- web_search: performs an external web search.
- slow_path: executes background services (optional).
- error:   technical error log

Given:
- the last real agent message,
- the last buyer (user) response,
- a list of backend logs created AFTER this response,
- real_estate questions:{fields}

Goal:
analyze whether the backend followed a normal technical flow or not.

### Task (Expectation-first, then compare):
Step A — Understand the turn:
- Read last_agent_message and last_buyer_message.
- Infer what the agent is doing (asking questions in real_estate questions , giving summary, giving options, etc.)
- Infer what the buyer answered.

Step B — Decide which backend steps SHOULD have happened:
Return an "expected" object with booleans:
- intent_classifier (Always true)
- main_model (Always true)
- extraction_model (true if the user response contains Agent quiestion Answer that should be extracted)
- memory_extraction (true if buyer revealed preferences or personal constraints)
- web_search (true ONLY if the agent response requires external factual info / listings / market data)
- slow_path (true if the expected services imply slow_path orchestration)
Also give a short reason for each expected step.

Important: Do NOT rely on the provided logs in Step B. Decide purely from the messages.


Step C — Compare expected vs actual logs:
- take logs by request_id to understand the actual sequence.
- Build an "actual" object showing which log types are present.
- Compare expected vs actual and decide normal_path:
  - normal_path = true if:
    * no error log exists, AND
    * critical expected steps are present (intent_classifier and/or main_model), AND
    * any missing steps are only optional or reasonably skipped.
  - normal_path = false if:
    * an error log exists, OR
    * any log type is expected but missing, OR (ex web_search is expected but missing AND the response clearly depends on it.)

Errors:
- If any log has log_type == "error"  extract it into Log_error.
- If there is no explicit error log but the flow is broken, create a synthetic Log_error with a meaningful name.

Extraction:
- Preference:
  * If memory_extraction exists, summarize extracted_memories from metadata if present.
  * Else if extraction_model exists, summarize extracted_answers from metadata if present.
  * Else return "none".
- Intent:
  * If intent_classifier exists, use metadata.intent_type if available; otherwise infer from messages.

Need Web:
- Set to "web search" if expected.web_search is true OR a web_search log exists.
- Otherwise "none".

### OUTPUT FORMAT (STRICT JSON ONLY):
Return ONLY one JSON object:

{
  "normal_path": <true|false>,
  
  "Log_error": {
    "name": "<error name>",
    "details": "<key details from error log.response/metadata>" } | null,

  "actual": { "present_log_types": ["..."]  },
  "Lost_expected_log": 
    { "log_type" : <missing expected> , "reason":  description in 10 words } | null
     }


Rules:
- JSON only. No extra text.
- Use null if no Log_error or no Lost_expected_log.
- Never invent logs that are not provided.

"""




def build_driver_messages(
    persona: dict,
    last_assistant: str,
    recent_turns: list["Turn"],
) -> list[dict]:
    """Build messages for the GPT-4o driver: system + persona context + recent turns + last assistant."""
    messages = [
        {"role": "system", "content": DRIVER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Persona (use only this when answering):\n"
            + "\n".join(f"- {k}: {v}" for k, v in persona.items()),
        },
        {
            "role": "assistant",
            "content": "Understood. I'll answer only what the agent asks, briefly and in character.",
        },
    ]
    for t in recent_turns:
        messages.append({"role": t.role, "content": t.content})
    messages.append({"role": "assistant", "content": last_assistant})
    return messages


def build_Logs_checker_prompt(
    last_real_message: str,
    user_response: str,
    logs: list[dict[str, Any]],
) -> list[dict]:
    """Build messages for GPT-4o log checker (phase 2)."""
    pretty_logs = json.dumps(logs, ensure_ascii=False, indent=2)
    user_content = (
        "Last real agent message:\n"
        f"{last_real_message}\n\n"
        "User response:\n"
        f"{user_response}\n\n"
        "Logs (JSON list):\n"
        f"{pretty_logs}\n"
    )
    return [
        {"role": "system", "content": Logs_checker_prompt},
        {"role": "user", "content": user_content},
    ]
