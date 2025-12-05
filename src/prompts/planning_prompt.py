from typing import Callable, List

from pydantic import BaseModel, Field


def make_goal_node_inputs(state):
    return {
        "user_query": state["user_query"],
    }


GOAL_NODE_PROMPT = """
# Instruction
You are the Goal-Level Planner in the MLDT pipeline.  
Your job is to decompose the user's command into **independent high-level subgoals** that the robot must achieve.

Rules:
- Each subgoal should represent **one distinct, clear objective**.
- If the user input contains multiple intentions, **split them by meaning**.
- Do NOT describe **motion paths, tool manipulation, or detailed actions**.  
  (They will be handled in the Task/Action levels.)
- Keep each subgoal **short, natural, and faithful to the original meaning**.
- Preserve the user's original order.

# Example
User input:
"Bring the apple to the table and also bring me a cup."

Output:
[
    "Bring the apple to the table",
    "Bring me a cup"
]

# User Input
{user_query}

# Output Format
Return ONLY the structured output that matches the JSON schema below.
{format_instructions}
"""


class GoalNodeParser(BaseModel):
    subgoals: List[str] = Field(
        ...,
        description="A list of high-level subgoals decomposed from the user query.",
    )


def make_task_node_inputs(
    state,
):
    def make_subgoals_text(subgoals):
        subgoals = subgoals.get("subgoals", [])

        return "\n".join([f"{i+1}. {subgoal}" for i, subgoal in enumerate(subgoals)])

    inputs = state.get("inputs", {})
    subgoals_text = make_subgoals_text(state.get("subgoals", []))
    print(f"Subgoals Text:\n{subgoals_text}\n")

    return {
        "skill_text": inputs.get("skill_text", ""),
        "object_text": inputs.get("object_text", ""),
        "subgoals_text": subgoals_text,
    }


TASK_NODE_PROMPT = """
# Role
You are the Task-Level Planner in the MLDT pipeline.  
Given a single subgoal from the Goal Node, your job is to decompose it into an ordered sequence of **semantic tasks** that the robot can perform using its built-in skills.
# Process
1. Analyze the provided subgoal carefully.
2. Find objects mentioned in the subgoal using <object_text>.
    no need to use all objects, only those relevant to the subgoal.
3. Devise a sequence of task steps using the available robot skills to achieve the subgoal
    provided in <skill_text>.
4. Each task step must specify:
    - the skill to use,
    - the target(object or group) for that skill.,

# Instructions
- robot_skills are defined in <skill_text>.
- objects are used in <object_text>.
- Task steps must be **short, natural, ordered**, and easy to follow.

# Few-shot Examples
## Example 1
### Input
<skill_text>
["from robot1.skills import GoToObject, PickObject, PlaceObject"]
</skill_text>

<object_text>
[
    {{'object_name' : 'object_bowl_0', 'object_in_group': 'counter_1_left_group'}}, 
    {{'object_name' : 'object_fork_0', 'object_in_group': 'island_left_group'}}
]
</object_text>

<subgoals_text>
1. put the fork in the bowl
</subgoals_text>

### Output
[{{
    "task": 'put the fork in the bowl',
    "subtasks": [
        {{'skill': 'GoToObject', 'target': 'object_fork_0'}},
        {{'skill': 'PickObject', 'target': 'object_fork_0'}},
        {{'skill': 'GoToObject', 'target': 'object_bowl_0'}},
        {{'skill': 'PlaceObject', 'target': 'object_bowl_0'}}
    ]
}}]

## Example 2
### Input
<skill_text>
["from robot1.skills import GoToObject, PickObject, PlaceObject"]
</skill_text>

<object_text>
[
    {{'object_name' : 'object_apple_0', 'object_in_group': 'island_right_group'}}, 
]
</object_text>

<subgoals_text>
1. put the apple on the island table
</subgoals_text>

### Output
[{{
    "task": 'put the apple on the island table',
    "subtasks": [
        {{'skill': 'GoToObject', 'target': 'object_apple_0'}},
        {{'skill': 'PickObject', 'target': 'object_apple_0'}},
        {{'skill': 'GoToObject', 'target': 'island_right_group'}},
        {{'skill': 'PlaceObject', 'target': 'island_right_group'}}
    ]
}}]

# Input Components
1. robot_skills  
A list of built-in robot skills.  
<skill_text>
{skill_text}
</skill_text>

2. observation  
Information about the objects currently present in the environment.  
<object_text>
{object_text}
</object_text>

3. subgoals
sub-goals provided by the Goal Node.
<subgoals_text>
{subgoals_text}
</subgoals_text>

# Output Format
Return ONLY the structured output that matches the JSON schema below.
{format_instructions}
"""


class SubTask(BaseModel):
    skill: str = Field(..., description="The robot skill to be used for this task.")
    target: str = Field(
        ...,
        description="The target object or group for the skill to act upon.",
    )


class SubGoal(BaseModel):
    subgoal: str
    tasks: List[SubTask] = Field(
        ...,
        description="An ordered list of semantic tasks to achieve the subgoal.",
    )


class TaskNodeParser(BaseModel):
    tasks: List[SubGoal] = Field(
        ...,
        description="A list of subgoals each decomposed into semantic tasks.",
    )


# 3. groups
# Information about object groupings in the environment.
# <groups_text>
# {groups_text}
# </groups_text>
