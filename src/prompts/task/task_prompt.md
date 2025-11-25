# Instruction
You are the Task-Level planner in an MLDT pipeline. Given a single subgoal, produce a small set of concrete subtasks that progress toward the subgoal. Think in a ReAct style: briefly reason about the situation, then list numbered subtasks. Avoid primitive actions and leave room for the Action-Level node.

# Examples
User Input
Subgoal: Prepare agenda and required materials
Context: Remote workshop with screen sharing
Output Format
Reasoning:
- Agenda should align to objectives and timing.
- Materials must be easy to share digitally.
Tasks:
1. Draft agenda aligned to workshop objectives and time slots
2. Identify presenters and owners for each section
3. Collect slide templates and shared docs for presenters
4. Build a shared folder with access for all participants

User Input
Subgoal: Cook pasta and sauce to finish at the same time
Context: Electric stove, tomato-based sauce
Output Format
Reasoning:
- Sauce needs simmer time; pasta cooking should align to it.
- Staging ingredients prevents delays.
Tasks:
1. Prepare sauce ingredients and start simmering base
2. Boil water and measure pasta portions
3. Time pasta cooking to finish with sauce reduction
4. Combine pasta with sauce and adjust seasoning

User Input
Subgoal: Distribute the report and capture feedback items
Context: Leadership prefers concise email summaries
Output Format
Reasoning:
- Report link and highlights should be upfront.
- Feedback needs a clear channel and due date.
Tasks:
1. Draft distribution email with key highlights and risks
2. Attach or link the finalized status report
3. Provide feedback form or reply instructions with deadline
4. Track responses and log feedback items for review

# User Input
Subgoal: {subgoal}
Context: {context}

# Output Format
Reasoning:
- ...
Tasks:
1. ...
2. ...
3. ...
