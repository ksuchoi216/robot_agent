<<<<<<< Updated upstream
# robot-agent
<<<<<<< HEAD
=======

## reference
git@github.com:marc1198/chat-hsr.git
>>>>>>> release/0.0.1
=======
# Robot Agent Source Code

This directory contains the core source code for the robot planning agent. The system uses a hierarchical planning approach to break down complex robot tasks into executable actions.

## Overview

The robot agent decomposes user commands through three levels:
1. **Goal Level** - Breaks user input into high-level subgoals
2. **Task Level** - Converts subgoals into semantic task steps
3. **Action Level** - Translates tasks into executable robot actions

## Directory Structure

```
src/
├── common/          # Shared utilities and definitions
├── config/          # Configuration management
├── prompts/         # LLM prompt templates
├── rag/             # Retrieval-augmented generation (placeholder)
├── runner/          # Main execution pipeline
├── tools/           # External tools integration (placeholder)
└── utils/           # Helper functions
```

## Components

### 📁 common/
Core shared components used throughout the application.

- **`enums.py`** - Model name definitions (GPT-4, GPT-5 variants)
- **`errors.py`** - Custom exception classes with structured error handling
- **`logger.py`** - Centralized logging with file rotation support

### 📁 config/
Configuration files and loaders.

- **`config.py`** - Configuration schema and loader using Pydantic
- **`config.yaml`** - Main configuration file defining:
  - Output and prompt directories
  - Robot skills (GoToObject, PickObject, PlaceObject, etc.)
  - Task and action templates
  - Model settings for each planning node

**Example Configuration:**
```yaml
runner:
  goal_node:
    model_name: gpt41mini
  task_node:
    model_name: gpt41mini
  action_node:
    model_name: gpt41mini

skills:
  - name: robot1
    skills: ['GoToObject', 'PickObject', 'PlaceObject']
```

### 📁 prompts/
LLM prompt templates for the planning pipeline.

- **`planning_prompt.py`** - Contains three main prompts:
  - `GOAL_NODE_PROMPT` - Decomposes user commands into subgoals
  - `TASK_NODE_PROMPT` - Breaks subgoals into task steps
  - Includes few-shot examples for better AI understanding

**Example Flow:**
```
User: "Bring the apple to the table"
↓
Goal: ["Bring the apple to the table"]
↓
Tasks: ["Open the fridge", "Pick up the apple", "Move to table", "Place apple"]
↓
Actions: [MoveAhead, PickObject, MoveAhead, PlaceObject, Done]
```

### 📁 runner/
The main execution engine that orchestrates the planning workflow.

- **`state.py`** - Defines the planning state structure
  - `PlannerState` - TypedDict containing user_query, subgoals, tasks
  - `PlannerStateMaker` - Factory for creating initial states

- **`graph.py`** - LangGraph-based pipeline implementation
  - Creates LLM chains with prompts and parsers
  - Manages model initialization and caching
  - Handles token usage tracking and rate limits

- **`runner.py`** - Main runner class
  - `Runner` - Base class with graph building logic
  - `PlanRunner` - Specialized runner for planning tasks
  - Manages LLM instances and execution

- **`text.py`** - Text formatting utilities
  - `make_object_text()` - Fetches and formats environment objects
  - `make_skill_text()` - Formats robot skills for prompts

### 📁 utils/
General-purpose utility functions.

- **`file.py`** - File I/O operations
  - `load()` - Load files (txt, json, yaml, csv, pkl)
  - `save()` - Save data to files with automatic directory creation
  - Supports multiple formats with error handling

### 📁 rag/
Placeholder for retrieval-augmented generation features.

### 📁 tools/
Placeholder for external tool integrations.

## How It Works

### 1. Initialize Configuration
```python
from src.config.config import load_config

config = load_config()  # Loads config.yaml
```

### 2. Create Initial State
```python
from src.runner.state import PlannerStateMaker

state_maker = PlannerStateMaker(config, url="http://127.0.0.1:8800")
initial_state = state_maker.make(user_query="Bring me a cup")
```

### 3. Run the Pipeline
```python
from src.runner.runner import PlanRunner

runner = PlanRunner(config)
final_state = runner.invoke(initial_state)
```

### 4. Access Results
```python
print(final_state["subgoals"])  # High-level goals
print(final_state["tasks"])     # Task decomposition
```

## Key Features

### ✅ Hierarchical Planning
Three-level decomposition ensures clear separation of concerns and easier debugging.

### ✅ Flexible Configuration
YAML-based configuration allows easy switching between models and modifying robot skills.

### ✅ Structured Error Handling
Custom exceptions with error codes, status codes, and detailed context for better debugging.

### ✅ Logging System
Rotating file logs organized by module with configurable verbosity.

### ✅ LLM Integration
Built on LangChain and LangGraph with support for:
- Multiple OpenAI models (GPT-4, GPT-5)
- Prompt caching for efficiency
- Token usage tracking
- Rate limit monitoring

### ✅ Type Safety
Uses Pydantic for configuration validation and TypedDict for state management.

## Data Flow

```
User Query
    ↓
[PlannerStateMaker] → Creates initial state with environment info
    ↓
[Goal Node] → Decomposes into subgoals
    ↓
[Task Node] → Converts each subgoal into tasks
    ↓
[Action Node] → Translates tasks into robot actions
    ↓
Final State (subgoals, tasks, actions)
```

## Environment Integration

The system connects to a robot simulation server to fetch:
- Object locations and groupings
- Available robot skills
- Environment state

This information is formatted into text prompts for the LLM to understand the current context.

## Error Handling

All custom errors inherit from `BaseServiceError` and include:
- **Error Code** - Machine-readable identifier
- **Status Code** - HTTP-style status (400, 500, etc.)
- **Domain** - Component where error occurred
- **Details** - Additional context as dictionary

Common errors:
- `ConfigError` - Invalid configuration
- `ParsingError` - Failed to parse LLM output
- `LLMError` - LLM API failures
- `GraphExecutionError` - Pipeline execution failures

## Best Practices

1. **Always load config first** - Ensures all settings are available
2. **Use the logger** - All modules should call `get_logger(__name__)`
3. **Handle errors gracefully** - Catch specific exceptions and log context
4. **Validate state** - Use Pydantic models for type safety
5. **Cache LLM instances** - Runner maintains a cache to avoid recreating models

## Dependencies

- **LangChain** - LLM orchestration framework
- **LangGraph** - Graph-based workflow management
- **Pydantic** - Data validation and settings
- **PyYAML** - Configuration file parsing
- **OpenAI** - LLM API access

## Future Enhancements

- Complete RAG implementation for knowledge retrieval
- Add more robot skills and actions
- Implement action-level planning
- Add validation and verification steps
- Support for multiple robots coordination
>>>>>>> Stashed changes
