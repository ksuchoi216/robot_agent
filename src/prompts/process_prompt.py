from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def make_intent_node_inputs(state):
    user_queries = state.get("user_queries", [])
    return {
        "user_query": user_queries[-1] if user_queries else "",
    }


INTENT_NODE_PROMPT = """
SYSTEM:
You are the Intent Understander node in a robot-planning system.
Given a single user input `query`, output ONE of: "stop", "accept", or "new".
Return STRICT JSON ONLY with the shape: {{"intent":"stop|accept|new"}}.
Do not include any extra fields, text, or punctuation.

--- DECISION RULES ---
1) "stop": user expresses cancel/hold/exit.
   Examples (KR/EN): "그만", "중단", "나중에", "멈춰", "stop", "cancel", "not now", "pause".
2) "accept": user agrees to proceed with the current plan/suggestion.
   Examples (KR/EN): "좋아", "오케이", "그대로 진행", "바로 실행", "1번으로", "제안대로", "ok", "go ahead", "proceed", "sounds good".
   - If the message contains both acceptance and additional changes, treat as NOT accept → go to rule 3.
3) "new": any new or changed instruction/goal, or any message that is not clearly stop/accept.
   Examples: target/location/order/constraints 변경, 새로운 목표 제시, 질문/의견/요청 등.
   Defaults: ambiguous/unclear/neutral messages → "new".

Priority for mixed signals: accept < stop < new
(If acceptance appears together with modifications or new goal, choose "new". If acceptance appears with clear stop, choose "stop".)

--- EXAMPLES ---
Input: "그대로 진행해"            → {{"intent":"accept"}}
Input: "오케이 ㄱㄱ"              → {{"intent":"accept"}}
Input: "지금은 그만하자"          → {{"intent":"stop"}}
Input: "나중에 하자"              → {{"intent":"stop"}}
Input: "knife 말고 가위로 해줘"   → {{"intent":"new"}}
Input: "먼저 서랍 열고 봐"        → {{"intent":"new"}}
Input: "성공률이 몇 퍼야?"        → {{"intent":"new"}}
Input: "좋아, 근데 가위로 바꿔"   → {{"intent":"new"}}

--- INPUT ---
query: {user_query}

--- OUTPUT FORMAT ---
{format_instructions}
"""


class IntentParser(BaseModel):
    intent: Literal["stop", "accept", "new"] = Field(
        ...,
        description='One of "stop", "accept", or "new" based on user intent analysis.',
    )


def route_intent(state):
    intent = state.get("intent_result", {}).get("intent")
    if intent == "stop":
        return "end"
    elif intent == "accept":
        return "accept"
    elif intent == "new":
        return "new"
    else:
        raise ValueError(f"Unknown intent: {intent}")


def create_user_queries_text(
    user_queries: List[str],
) -> str:
    """Create a numbered list text from a list of user queries."""
    return "\n".join([f"{i+1}. {query}" for i, query in enumerate(user_queries)])


def make_supervisor_node_inputs(state):
    inputs = state.get("inputs", {})
    user_queries = state.get("user_queries", [])
    return {
        "user_queries_text": create_user_queries_text(user_queries),
        "object_text": inputs.get("object_text", ""),
        "group_list_text": inputs.get("group_list_text", ""),
        "skill_text": inputs.get("skill_text", ""),
    }


SUPERVISOR_NODE_PROMPT = """

SYSTEM:
You are the SUPERVISOR node in a robot-planning system.

Your jobs:
1) Combine the list `user_queries` into ONE final unified query (`user_final_query`).
2) Judge whether this unified query is feasible using the available objects, groups, and skills.
3) Output STRICT JSON matching format_instructions. 
j
------------------------------------------------
## RULES FOR BUILDING user_final_query

You MUST generate ONE natural-language Korean mission string.

### 1) Merge partial intents
Combine information from all user_queries:
- Identify target object (latest override wins: e.g., “사과 말고 레몬” → 레몬)
- Identify target location (latest specification wins)
- Identify action (e.g., “옮겨줘”, “꺼내줘”, “가져와줘” → keep the latest)
- When location is missing but needed → leave as-is (feasibility will handle)

### 2) Handle overrides
If a query modifies the previous one (e.g., “사과 말고 레몬”), use the updated content.

### 3) Output ONE mission string
- Do NOT output multiple options.
- Must be in natural Korean.
- Examples:
  - ["사과를 옮겨줘", "아일랜드 식탁에 옮겨줘", "사과말고 레몬"]
    → "레몬을 아일랜드 식탁에 옮겨줘."

### 4) This unified query is the ONLY query used for feasibility judgment.

------------------------------------------------
## RULES FOR is_feasible
Return true only if:
- Required object exists in object_text
- Its group is reachable
- Required skills exist
- No contradictions with env_state
- No unsafe failures in history_logs

If false:
- reasons: 1-2 short blockers
------------------------------
## INPUTS
You receive:
- user_queries: the user's current mission instruction
{user_queries_text}
- object_text: list of objects and their group locations
{object_text}
- group_list_text: allowed reachable groups in the environment
{group_list_text}
- skill_text: robot skills available
{skill_text}

These are for reasoning only. Do NOT rewrite them.
------------------------------
## OUTPUT FORMAT (STRICT)
{format_instructions}
"""


class SupervisorParser(BaseModel):
    """Feasibility judgment + final unified query produced by the Supervisor."""

    is_feasible: bool = Field(
        ...,
        description=(
            "True if the mission can proceed with current objects, groups, skills, and environment; "
            "False otherwise."
        ),
    )

    reasons: List[str] = Field(
        default_factory=list,
        description=(
            "Short blockers or confirmations. "
            "If is_feasible=False, include 1-2 core blockers explaining why the original user intent cannot execute."
        ),
    )

    user_final_query: str = Field(
        ...,
        description=(
            "The final normalized query derived from the list of user_queries. "
            "Combine partial intents, replace objects/locations if overridden, "
            "and produce ONE complete Korean mission string representing the user's most recent intent."
        ),
    )


def route_supervisor(state):
    is_feasible = state.get("supervisor_result", {}).get("is_feasible")
    if is_feasible is True:
        return "feasible"
    elif is_feasible is False:
        return "not_feasible"
    else:
        raise ValueError(f"Unknown is_feasible value: {is_feasible}")


def make_feedback_node_inputs(state):
    inputs = state.get("inputs", {})
    supervisor_result = state.get("supervisor_result", {})
    user_final_query = supervisor_result.get("user_final_query", "")
    reasons = supervisor_result.get("reasons", [])
    reason_text = "\n".join([f"- {reason}" for reason in reasons])
    return {
        "user_final_query": user_final_query,
        "object_text": inputs.get("object_text", ""),
        "group_list_text": inputs.get("group_list_text", ""),
        "skill_text": inputs.get("skill_text", ""),
        "reason_text": reason_text,
    }


FEEDBACK_NODE_PROMPT = """
SYSTEM:
You are the FEEDBACK node in a robot-planning system.

Your ONLY tasks:
1) Return a LIST of short reasons why the original `query` is not feasible.
2) Return ONE final `suggestion`: a minimally edited, executable mission string.

RULES FOR reason
- Start from supervisor_output.reasons.
- Keep each item short (phrase or one short sentence).
- You may add ONE extra reason if it clarifies feasibility failure (e.g., missing skill).

RULES FOR suggestion
- Produce ONE Korean mission string that is executable NOW.
- Preserve the user's original intent as much as possible.
- Repair using ONLY available resources:
  - Missing object → replace with a similar/available object.
  - Missing/unspecified location → choose a reachable group.
  - Missing skill → rephrase to use only available skills (e.g., replace OpenObject with GoToObject).
  - Order needed → bake a simple preliminary step into natural language.
- No lists, no alternatives, no explanation—just the final best single query.

--------------------------------
EXAMPLES (illustrative only; do NOT echo):
- query: "사과를 꺼내줘." & apple missing, lemon exists in island group
  → reason: ["사과가 없습니다.", "사과를 놓을/꺼낼 위치가 비어 있습니다."]
  → suggestion: "레몬을 아일랜드 식탁에 꺼내줘."

- query: "냉장고 문 열어줘." & OpenObject missing; GoToObject available
  → reason: ["OpenObject 스킬이 없습니다."]
  → suggestion: "냉장고 앞까지 이동해줘."


------------------------------------------------
## INPUTS
You receive:
- user_queries: the user's current mission instruction
{user_final_query}
- object_text: list of objects and their group locations
{object_text}
- group_list_text: allowed reachable groups in the environment
{group_list_text}
- skill_text: robot skills available
{skill_text}
- reason_text: feasibility blockers from Supervisor
{reason_text}

These are for reasoning only. DO NOT repeat them.

------------------------------------------------
## OUTPUT FORMAT (STRICT JSON)
{format_instructions}
"""


class FeedbackParser(BaseModel):
    """Actionable fix produced by the Feedback node when a mission is not feasible."""

    suggestion: str = Field(
        ...,
        description="A single natural-language mission string that is executable now. Preserve intent; repair object/location/skill/order using only available resources.",
    )
    reason: List[str] = Field(
        ...,
        description="One or more short reasons explaining why the original query was not feasible (mirrors Supervisor reasons; you may add 1 extra if needed).",
    )
