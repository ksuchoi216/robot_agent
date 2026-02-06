# with-robot-5th/agent-planner 설명

`with-robot-5th/agent-planner`는 사용자의 자연어 명령을 받아 로봇이 수행할 수 있는 작업(Task)으로 분해하고 실행하는 에이전트입니다. 전체 흐름은 **State -> Graph -> Run -> Executor**의 구조를 따릅니다.

## 구조적 설명

1.  **State (상태 정의)**: 에이전트의 현재 상태를 저장하는 저장소입니다. 사용자의 입력(Query), 환경 정보(Objects), 사용 가능한 스킬(Skills), 그리고 생성된 하위 목표(Subgoals)와 작업(Tasks)들이 여기에 담깁니다. 일종의 '입력'이자 '메모리' 역할을 합니다.
2.  **Graph (계획 수립)**: LangGraph를 사용하여 정의된 워크플로우입니다. 각 노드(Node)는 특정 작업(예: 목표 분해, 작업 분해)을 수행하며, 이들은 순서대로 연결되어 있습니다. LLM을 사용하여 입력된 목표를 실제 실행 가능한 단위로 쪼개는 'Planning' 단계입니다.
3.  **Run (실행)**: 정의된 Graph를 실제로 실행하는 단계입니다. 초기 State를 Graph에 주입하고, 각 노드를 거치며 State가 업데이트됩니다. 최종적으로 실행 계획(Task Sequence)이 도출됩니다.
4.  **Executor (명령 수행)**: Graph 실행 결과로 만들어진 구체적인 작업 목록(Task Outputs)을 받아, 실제 로봇이나 시뮬레이터에 명령을 전달하여 물리적인 행동을 수행하는 단계입니다.

---

## 디테일한 설명 (코드 기반)

코드를 바탕으로 각 단계가 어떻게 구현되어 있는지 설명합니다.

### 1. State (`src/state.py`)

`state.py`는 LangGraph에서 흐르는 데이터의 구조(`StateSchema`)와 초기 상태를 만드는 방법을 정의합니다.

특히 `make_object_text` 함수는 시뮬레이터 환경(`url`)의 `/env` 엔드포인트로 요청을 보내 현재 물체(Objects) 정보를 받아옵니다.

```python
def make_object_text(url):
    # 포트를 통해 환경(env) 정보를 받아오는 부분
    response = requests.get(f"{url}/env")
    all = response.json()
    objects = all["objects"]
    print(objects)
    total_object_text = "{{\n"
    for obj in objects:
        object_text = f'"object_name": "{obj}",\n'
        total_object_text += object_text

    total_object_text += "}}"

    return total_object_text
```

이 정보와 스킬 정보(`make_skill_text`)가 `_make_inputs` 함수를 통해 합쳐져 LLM이 이해할 수 있는 텍스트 형태로 State의 `inputs`에 저장됩니다. 이를 통해 LLM은 현재 로봇이 어떤 스킬을 쓸 수 있고, 주변에 어떤 물건이 있는지 알게 됩니다.

### 2. Graph (`src/graph.py`)

`graph.py`는 계획을 수립하는 '뇌'의 구조를 만듭니다. 핵심은 **Goal Decomposition**과 **Task Decomposition** 두 개의 노드입니다.

*   **goal_decomp**: 사용자의 모호한 명령을 명확한 하위 목표(`subgoals`)로 나눕니다.
*   **task_decomp**: 각 하위 목표를 실제 실행 가능한 구체적인 작업(`tasks`)으로 변환합니다. (예: "사과 줘" -> "GoToObject", "PickObject" 등)

```python
    # Goal Decomposition Node
    goal_node = make_llm_node(
        llm=goal_llm,
        prompt_text=prompt_module.GOAL_DECOMP_NODE_PROMPT,
        make_inputs=prompt_module.make_goal_decomp_node_inputs,
        parser_output=prompt_module.GoalDecompNodeParser,
        state_key="subgoals",  # 결과를 state['subgoals']에 저장
        state_append=False,
        node_name="GOAL_DECOMP_NODE",
    )
    
    # Task Decomposition Node
    task_node = make_llm_node(
        llm=task_llm,
        prompt_text=prompt_module.TASK_DECOMP_NODE_PROMPT,
        make_inputs=prompt_module.make_task_decomp_node_inputs,
        parser_output=prompt_module.TaskDecompNodeParser,
        state_key="tasks",    # 결과를 state['tasks']에 저장
        state_append=False,
        node_name="TASK_DECOMP_NODE",
    )
```

이 노드들은 `StateGraph`를 통해 순차적으로 연결됩니다. (`START` -> `goal_decomp` -> `task_decomp` -> `END`)

### 3. Run (`main.py`)

`main.py`는 웹 서버(FastAPI)를 띄우고, 요청이 들어오면 전체 파이프라인을 실행합니다.

*   `state_maker.make(...)`: 초기 상태 생성
*   `runner.invoke(state)`: Graph 실행 (LLM 추론)
*   `task_executor.execute(task_outputs)`: 결과 실행

### 4. Executor (`src/executor.py`)

`executor.py`는 계획된 작업을 실제 세상(시뮬레이터/로봇)에 적용합니다.

Graph 실행 결과로 생성된 `task_outputs`를 순회하며 하나씩 실행합니다. 각 Task의 `skill` 타입에 따라 적절한 메서드를 호출하여 로봇을 제어합니다.

```python
    def execute(self, task_outputs):
        task_sequence = self._make_task_sequence(task_outputs)
        logger.info("Executing task sequence:")
        # ... (생략)

        results = []
        for task in task_sequence:
            logger.info(f"Executing task: {task}")
            # 스킬 타입에 따른 액션 실행분기
            if task["skill"] == "GoToObject":
                target = self.object_map[task["target"]]
                self._go_to_object(target)
            elif task["skill"] == "PickObject":
                target = self.object_map[task["target"]]
                self._pick_object(target)
            elif task["skill"] == "PlaceObject":
                target = self.object_map[task["target"]]
                self._place_object(target)
            else:
                raise ValueError(f"Unknown skill: {task['skill']}")
            
            task_result = task.copy()
            task_result["result"] = "Ok"
            results.append(task_result)

        logger.info("Task sequence execution completed.")
        return results
```

여기서 `_go_to_object` 같은 메서드들은 `requests.post(f"{self.url}/send_action", ...)`를 통해 시뮬레이터 서버로 Python 코드를 전송하여 실제로 로봇을 움직이게 합니다.

---

## 프롬프트 분석 (Prompt Analysis)

Graph의 지능을 담당하는 각 노드는 LLM에게 역할을 부여하는 프롬프트(Prompt)에 의해 동작합니다. `src/prompts.py`에 정의된 두 가지 핵심 프롬프트를 분석합니다.

### 1. Goal Decomposition Prompt (`GOAL_DECOMP_NODE_PROMPT`)

이 프롬프트는 사용자의 자연어 명령을 로봇이 이해할 수 있는 하위 목표들로 분리하는 역할을 합니다.

**핵심 포인트:**
*   **Role**: "Goal-Level Planner"로서 역할을 부여합니다.
*   **Attribute-based Rules**: 색상, 크기 등의 속성에 따라 목표를 그룹화하도록 명시합니다. (예: "빨간 것은 빨간 그릇에")
*   **Input**: 현재 환경의 물체 목록(`object_text`)과 사용자 명령(`user_query`)을 받습니다.

**프롬프트 원문:**
```text
# Instruction
You are the Goal-Level Planner in the MLDT pipeline.  
Your job is to decompose the user's command into independent high-level subgoals.

Definition of Terms:
- High-level goal: A distinct objective expressed without describing detailed actions.  
- Attribute-based decomposition: Splitting goals based on shared attributes of objects such as color, size, or shape.  
- Semantic grouping: Grouping by meaning or shared properties rather than by grammatical structure.

General Rules:
- Each subgoal must represent one independent, meaningful objective.
- If the user input contains multiple intentions, split them by meaning.
- Do not describe movement, manipulation steps, or low-level actions. These will be handled later.
- Keep each subgoal short, natural, and faithful to the original meaning.
- Preserve the user query's order.

Attribute-Based Rules:
- If the user's command involves categorizing, sorting, grouping, matching, or organizing objects based on attributes, then you must apply attribute-based decomposition.
- Extract object attributes from object_text. For example: "object_red_0" has the attribute "red".  
- Detect attribute groups (such as colors) from the object_text and match objects to bowls with the same attribute.
- When attribute-based organization is required, the number of subgoals must match the number of attribute groups.
...
```

**Output Model (`GoalDecompNodeParser`):**
```python
class GoalDecompNodeParser(BaseModel):
    subgoals: List[str] = Field(
        ...,
        description="A list of high-level subgoals decomposed from the user query.",
    )
```

### 2. Task Decomposition Prompt (`TASK_DECOMP_NODE_PROMPT`)

목표 분해 노드에서 나온 하위 목표 하나를 받아, 실제 로봇 스킬(`skill`)들의 시퀀스로 변환합니다.

**핵심 포인트:**
*   **Role**: "Task-Level Planner"입니다.
*   **Constraints**: 반드시 주어진 `skill_text`에 있는 스킬만 사용해야 하며, `object_text`에 있는 물체만 타겟으로 삼아야 합니다.
*   **Output Format**: `skill`과 `target`을 쌍으로 하는 JSON 리스트 형태로 답해야 합니다.

**프롬프트 원문:**
```text
# Role
You are the Task-Level Planner in the MLDT pipeline.
Your job is to convert a single high-level subgoal into an ordered sequence of semantic tasks that the robot can perform using its built-in skills.

Definition of Terms:
- Semantic task: A meaningful, minimal operation that contributes directly toward completing a subgoal.  
- Skill: A predefined robot capability such as moving to an object, picking an object, or placing an object.  
- Target: The object or location to which a skill is applied.

# Task-Level Principles
1. You must interpret the subgoal as a high-level objective that is already attribute-grouped by the Goal-Level Planner.
2. Your output must be a sequence of semantic tasks that use the robot's built-in skills.
3. Do not add new interpretations beyond the subgoal.  
4. Do not infer colors, groups, or attributes beyond what is explicitly present in the subgoal or object_text.
5. Do not describe low-level motion details. You must only specify which skill is used and which object is targeted.

# Required Behavior
- Use only the skills listed in <skill_text>.  
- Select objects only from <object_text>.  
- You may ignore objects that are not relevant to the subgoal.  
- The task steps must be short, natural, logically ordered, and directly connected to the subgoal.
...
```

**Output Model (`TaskDecompNodeParser`):**
```python
class SubTask(BaseModel):
    skill: Literal["GoToObject", "PickObject", "PlaceObject"] = Field(
        ..., description="The robot skill to be used for this task."
    )
    target: str = Field(
        ...,
        description="The target object",
    )


class SubGoal(BaseModel):
    subgoal: str
    tasks: List[SubTask] = Field(
        ...,
        description="An ordered list of semantic tasks to achieve the subgoal.",
    )


class TaskDecompNodeParser(BaseModel):
    task_outputs: List[SubGoal] = Field(
        ...,
        description="A list of subgoals each decomposed into semantic tasks.",
    )
```
