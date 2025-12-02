from typing import Callable, List

from pydantic import BaseModel


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
    subgoals: List[str]


def make_task_node_inputs(
    state,
):
    def make_subgoals_text(subgoals):
        return "\n".join([f"{i+1}. {subgoal}" for i, subgoal in enumerate(subgoals)])

    inputs = state.get("inputs", {})
    subgoals_text = make_subgoals_text(state.get("subgoals", []))

    return {
        "skill_text": inputs.get("skill_text", ""),
        "object_text": inputs.get("object_text", ""),
        "subgoals_text": subgoals_text,
    }


TASK_NODE_PROMPT = """
# Role
You are the Task-Level Planner in the MLDT pipeline.  
Given a single subgoal from the Goal Node, decompose it into **meaningful task steps** the robot must perform.

# Process
1. Analyze the provided subgoal carefully.
2. Find objects mentioned in the subgoal using the object information.
3. Devise a sequence of task steps using the available robot skills to achieve the subgoal
4. Ensure each step is a **semantic task**, not a primitive action.


# Instructions
- Each step must be a **semantic task**, not a primitive action.
- robot_skills are **reference only**, do not simply repeat them.
- object information is used only to **reason about context**.
- Task steps must be **short, natural, ordered**, and easy to follow.
- Include logically necessary steps (e.g., opening/closing doors) if needed.
- Output must be a **Python list-style string**.

# Few-shot Examples
<Example1>
[Input]
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
['put the fork in the bowl']
</subgoals_text>

[Output]
[
    {{'skill': 'GoToObject', 'object': 'object_fork_0'}},
    {{'skill': 'PickObject', 'object': 'object_fork_0'}},
    {{'skill': 'GoToObject', 'object': 'object_bowl_0'}},
    {{'skill': 'PlaceObject', 'object': 'object_bowl_0'}}
]

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
    skill: str
    object: str


class TaskNodeParser(BaseModel):
    tasks: List[SubTask]


# 3. groups
# Information about object groupings in the environment.
# <groups_text>
# {groups_text}
# </groups_text>
