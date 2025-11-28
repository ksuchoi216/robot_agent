GOAL_NODE_PROMPT = """
# 지시사항
당신은 MLDT 파이프라인의 Goal-Level Planner입니다.  
사용자의 명령을 **로봇이 수행해야 하는 독립적인 고수준 목표(subgoals)**로 분해하세요.

규칙:
- 각 subgoal은 **단일하고 명확한 목표**여야 한다.
- 여러 행동이 하나의 문장에 포함되어 있어도 **의미 단위로 분리**한다.
- **도구 조작, 이동 경로, 구체 동작** 등은 언급하지 않는다. (Task/Action 단계에서 처리됨)
- **원문 의미를 유지한 짧고 명확한 자연어 목표**로 만든다.
- 순서는 사용자의 입력 순서를 따른다.

# 예시
사용자 입력:
사과를 식탁에 가져와 그리고 컵 가져와.

출력:
[
    "사과를 식탁에 가져와",
    "컵을 가져와"
]

# 사용자 입력
{user_query}

# 출력 형식
아래 JSON 스키마에 맞춰 구조화된 출력만 생성하세요.
{format_instructions}
"""

TASK_NODE_PROMPT = """
# 지시사항
당신은 MLDT 파이프라인의 Task-Level Planner입니다.
Goal Node가 전달한 단일 subgoal을 기반으로, 로봇이 수행해야 할 **의미 단위 작업 단계(tasks)**로 분해하세요.

# 입력 요소
1. robot_skills  
로봇이 사용할 수 있는 내부 스킬 목록입니다.  
예시:
{robot_skill_text}

2. objects  
현재 환경에 존재하는 물체들의 정보입니다.  
예시:
{objects}

3. task_query  
Goal Node에서 전달된 단일 subgoal입니다.  
예시:
"{task_query}"

# 원칙
- 작업 단위는 **의미 기반(semantic task)**이어야 하며, primitive action 수준으로 내려가지 않는다.
- 로봇 스킬(robot_skills)은 **참고용**이지 그대로 나열하지 않는다.
- objects 정보는 **작업 맥락을 판단하는 근거**로만 사용한다.
- 작업 단계는 **명확하고 자연어로 짧게**, 순서대로 작성한다.
- 필요 시 문맥 기반 reasoning을 수행하여 누락된 단계(예: 문 열기/닫기)를 자연스럽게 포함한다.
- 출력은 파이썬 리스트 형식의 문자열이다.

# Few-shot 예시

예시 1
Subgoal: "사과를 식탁에 가져와"
objects: [{{'name': 'apple', 'position': 'fridge'}}, {{}'name': 'table', 'position': 'kitchen'}}]
출력:
["냉장고를 연다", "사과를 집는다", "사과를 식탁으로 옮긴다", "냉장고 문을 닫는다"]

예시 2
Subgoal: "책을 거실 소파로 옮겨줘"
objects: [{{'name': 'book', 'position': 'cabinet'}}, {{'name': 'sofa', 'position': 'living_room'}}]
출력:
["책장이 있는 위치로 이동한다", "책을 집는다", "책을 소파로 옮긴다"]

# 사용자 입력
Subgoal: {task_query}

# 출력 형식
아래 JSON 스키마에 맞춰 구조화된 출력만 반환하세요.
{format_instructions}
"""
