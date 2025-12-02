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


TASK_NODE_PROMPT = """
# Instruction
You are the Task-Level Planner in the MLDT pipeline.  
Given a single subgoal from the Goal Node, decompose it into **meaningful task steps** the robot must perform.

# Input Components
1. robot_skills  
A list of built-in robot skills.  
Example:
{robot_skill_text}

2. observation  
Information about the objects currently present in the environment.  
Example:
{objects}

3. task_query  
A single subgoal provided by the Goal Node.  
Example:
"{task_query}"

# Principles
- Each step must be a **semantic task**, not a primitive action.
- robot_skills are **reference only**, do not simply repeat them.
- object information is used only to **reason about context**.
- Task steps must be **short, natural, ordered**, and easy to follow.
- Include logically necessary steps (e.g., opening/closing doors) if needed.
- Output must be a **Python list-style string**.

# Few-shot Examples
<Example1>
[Input]
objects: [
    {{"name": "apple", "position": "fridge"}},
    {{"name": "table", "position": "kitchen"}}
]
robot: [
    {{"name": "alice", ""}}
]

CODE:
def bring_apple_to_table():
    Step 1: GoToObject('Fridge')
    Step 2: OpenObject('Fridge')
    Step 3: PickObject('Apple')
    Step 4: GoToObject('Table')
    Step 5: PlaceObject('Apple', 'Table')
    Step 6: CloseObject('Fridge')

Execute SubTask 1:
bring_apple_to_table()

Task bring apple to the table is done.
</Example1>
<Example2>
Task Description: Move the book to the living room sofa.

General Task Decomposition:
This task consists of a single subtask:
SubTask 1: Move the book from the cabinet to the sofa.
Required skills include: GoToObject, PickObject, PlaceObject.

CODE:
def move_book_to_sofa():
    Step 1: GoToObject('Cabinet')
    Step 2: PickObject('Book')
    Step 3: GoToObject('Sofa')
    Step 4: PlaceObject('Book', 'Sofa')

Execute SubTask 1:
move_book_to_sofa()

Task move book to sofa is done.
</Example2>

# Output Format
Return ONLY the structured output that matches the JSON schema below.
{format_instructions}
"""
