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
Return STRICT JSON ONLY with the shape: {{"intent":"stop|accept|new|question"}}.
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
4) "question": user asks for information, clarification, or a factual answer.
   Examples: 
   - 위치 질문: "사과는 어딨어?", "냉장고 어디야?"
   - 가능 여부 질문: "열 수 있어?", "가져올 수 있어?"
   - 정보 요청: "스킬 뭐 있어?", "지금 상태가 어때?", "이거 어떻게 작동해?"
   - 일반적인 의문문: sentences ending with "?", "~니?", "~어?" (except polite commands like "사과 좀 가져와줄래?")

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
Input: "사과는 어딨어?"          → {{"intent":"question"}}
Input: "아일랜드 식탁이 있어?" → {{"intent":"question"}}
Input: "과일을 슬라이스 할 수 있어? → {{"intent":"question"}}

--- INPUT ---
query: {user_query}

--- OUTPUT FORMAT ---
{format_instructions}
"""


class IntentParser(BaseModel):
    intent: Literal["stop", "accept", "new", "question"] = Field(
        ...,
        description='One of "stop", "accept", "new", or "question" based on user intent analysis.',
    )


def route_intent(state):
    intent = state.get("intent_result", {}).get("intent")
    if intent == "stop":
        return "end"
    elif intent == "accept":
        return "accept"
    elif intent == "new":
        return "new"
    elif intent == "question":
        return "question"
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
1) Combine the list `user_queries` into ONE final unified mission string (`user_final_query`).
2) Decide whether this mission is feasible using objects, groups, and skills.
3) Output STRICT JSON matching format_instructions. No extra text.

------------------------------------------------
## RULES FOR BUILDING user_final_query

You MUST generate ONE natural-language Korean mission string.

### STRICT NO-INFERENCE RULE (MANDATORY)
You MUST NOT guess, infer, hallucinate, or fill in ANY missing information.
This includes destinations, container names, object identities, skills, or locations.
If the user does NOT explicitly specify a detail, you must NOT add it.
The final `user_final_query` MUST contain ONLY information explicitly present in user_queries.

### 1) Merge partial intents
Combine information from all user_queries:
- Identify target object (latest override wins)
- Identify target location ONLY if explicitly stated by the user
- Identify action (latest override wins)
- If destination is not specified by user: leave it missing

### 2) Handle overrides
If later queries modify earlier ones (e.g., "사과 말고 레몬"), use the updated content.

### 3) Output ONE mission string
Do not output alternatives.
Use only what the user explicitly stated.
only use user_queries content. don't infer or add new details.
Example:
["사과를 옮겨줘", "아일랜드 식탁에 옮겨줘", "사과말고 레몬"]
→ "레몬을 아일랜드 식탁에 옮겨줘."

### 4) The final unified query is the ONLY content used for feasibility judgment.

------------------------------------------------
## RULES FOR is_feasible

`is_feasible` MUST be true ONLY if ALL of the following are satisfied:

1) The required object exists in object_text.
2) The required object's group is known and reachable.
3) The required destination (if needed) is explicitly specified AND is in group_list_text.
4) All required robot skills exist in skill_text.
5) No contradictions with env_state.
6) No unsafe failures in history_logs.

If ANY of these conditions fail:
- Set is_feasible = false
- Provide 1–2 short blockers in `reasons`

------------------------------------------------
## HARD RULES FOR DESTINATION-REQUIRED ACTIONS

Transport/move/take-out/place actions (e.g., "옮겨줘", "가져와줘", "놓아줘", "두어줘", "move", "bring", "place", "put")
REQUIRE a destination.

If the user did NOT explicitly specify a destination:
- You MUST set is_feasible = false.
- You MUST NOT propose, infer, or fabricate any destination.
- A valid reason example: "목표 위치가 지정되지 않았습니다."

Similarly, actions like "꺼내줘" (take out) REQUIRE a placement destination.
If missing → is_feasible=false with a reason.

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


def make_question_answer_node_inputs(state):
    inputs = state.get("inputs", {})
    user_queries = state.get("user_queries", [])
    return {
        "recent_user_query": user_queries[-1] if user_queries else "",
        "object_text": inputs.get("object_text", ""),
        "group_list_text": inputs.get("group_list_text", ""),
        "skill_text": inputs.get("skill_text", ""),
    }


QUESTION_ANSWER_NODE_PROMPT = """
SYSTEM:
You are the QUESTION node in a robot-planning system.

You ONLY answer three types of robot-related questions:
1) Object LOCATION questions (e.g., "사과 어디 있어?")
2) Object EXISTENCE questions (e.g., "레몬 있어?")
3) Capability / FEASIBILITY questions based on available skills (e.g., "문 열 수 있어?")

Any question that does NOT belong to these three categories must return:
{{"answer": "해당 질문은 로봇 작업과 관련된 허용된 질문이 아닙니다."}}

You MUST output STRICT JSON ONLY in the form:
{{"answer": "..."}}

No explanation, no markdown, no commentary.


------------------------------------------------------------
QUESTION CLASSIFICATION RULES

1) LOCATION QUESTIONS:
   Trigger patterns:
     - "어디", "어딨어", "어디야"
     - questions ending with "?" indicating location
   Behavior:
     - If object exists in object_text: return its group
     - If object does NOT exist: return that it does not exist

2) EXISTENCE QUESTIONS:
   Trigger patterns:
     - "있어?", "존재해?", "있는지?"
   Behavior:
     - If object exists: say it exists
     - Else: say it does not exist

3) CAPABILITY QUESTIONS:
   Trigger patterns:
     - "할 수 있어?", "가능해?", "~할 수 있니?"
     - Examples: "집을 수 있어?", "열 수 있어?", "옮길 수 있어?"
   Behavior:
     - Identify the required skill from the question
     - If skill exists in skill_text: answer that it is possible
     - If missing: answer that the robot cannot perform it
    - Action-based capability questions (e.g., "사과를 자를 수 있어?", "빵을 썰 수 있어?"):
    Map the action verb to a required skill and check if that skill exists in skill_text.
------------------------------------------------------------
INVALID QUESTION RULE:
If the question does NOT match any of the above three categories:
Return:
{{"answer": "해당 질문은 로봇 작업과 관련된 허용된 질문이 아닙니다."}}

Examples of INVALID questions:
- "왜 실패했어?"
- "어떻게 작동해?"
- "로그 보여줘"
- "너 누구야?"
- "무슨 원리야?"

------------------------------------------------------------
INPUTS (for reasoning only; DO NOT echo them)

## INPUTS
You receive:
- recent_user_query: the user's current mission instruction
{recent_user_query}
- object_text: list of objects and their group locations
{object_text}
- group_list_text: allowed reachable groups in the environment
{group_list_text}
- skill_text: robot skills available
{skill_text}

------------------------------------------------------------
OUTPUT FORMAT (STRICT JSON)
{format_instructions}
"""


class QuestionAnswerParser(BaseModel):
    """Answer produced by the Question Answer node when user asks a question."""

    answer: str = Field(
        ...,
        description="A concise and accurate answer to the user's question.",
    )
