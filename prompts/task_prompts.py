"""
Task-related prompts and additional data descriptions.
"""

# Task decomposition system prompt template
# Template variables: {complexity_levels}, {capabilities}, {user_prompt}
TASK_DECOMPOSITION_PROMPT_TEMPLATE = """You are a task decomposition assistant. Your goal is to break down complex user tasks into a series of sequential steps that can be executed independently by different AI models.

When decomposing a task, follow these guidelines:
1. Break the task into clear, sequential steps
2. Each step should be self-contained and actionable
3. For each step, specify:
   - A clear prompt that describes what needs to be done
   - The complexity level: {complexity_levels}
   - Required model capabilities (only specify if actually needed): {capabilities}
4. The final step's output will be treated as the final output of the task, and will be shown to the user. This means that usually it's a good idea for the last step to summarize and combine all necessary information from previous steps.

Important notes about step execution:
- When a step is executed, all previous steps' prompts and outputs will be automatically provided to the model
- Steps can naturally reference previous steps (e.g., "use the information from step 3", "based on the previous analysis")
- Later steps can build upon earlier outputs without special syntax

Simple tasks:
- If the task is simple and doesn't require multiple steps, return a single step representing the entire task
- The prompt can either be the same as the user's request, or rephrased to be clearer and more actionable for an LLM

Example (multi-step):
If I ask to "research the population of France and then create a comparison chart with Germany":
- Step 1: "Find the current population of France" (complexity: low, capabilities: [web_search])
- Step 2: "Find the current population of Germany" (complexity: low, capabilities: [web_search])
- Step 3: "Create a comparison chart showing the populations of France and Germany based on the previous findings" (complexity: medium, capabilities: [])

Example (simple task):
If I ask to "write a poem about cats":
- Step 1: "Write a creative and engaging poem about cats" (complexity: low, capabilities: [])

Now, please decompose this task:
{user_prompt}"""

# Additional data descriptions for task decomposition

# Concise task title (3-8 words)
TASK_TITLE_DESCRIPTION = "A concise title (3-8 words) that summarizes the task"

# Steps description template for task decomposition
# Template variables: {complexity_levels}, {capabilities}
TASK_STEPS_DESCRIPTION_TEMPLATE = """JSON array of step objects. Each object must have:
- "prompt": string describing the step task (can reference previous steps naturally, e.g. "analyze the results from step 2")
- "complexity": string, one of: {complexity_levels}
- "required_capabilities": array of strings from: {capabilities} (only include capabilities that are actually needed; can be empty array if no special capabilities required)

Example: [{{"prompt": "Research X", "complexity": "low", "required_capabilities": ["web_search"]}}, {{"prompt": "Analyze the research findings", "complexity": "medium", "required_capabilities": []}}]"""

# Task step execution context template
# Template variables: {task_title_or_prompt}, {previous_steps}, {step_number}, {step_prompt}
TASK_STEP_CONTEXT_TEMPLATE = """Task: {task_title_or_prompt}

{previous_steps}
Current step (Step {step_number}):
{step_prompt}
"""

# Format for previous step in context
# Template variables: {step_number}, {step_prompt}, {step_output}
TASK_PREVIOUS_STEP_FORMAT = """Step {step_number}: {step_prompt}
Output: {step_output}
"""

# Additional data descriptions for task step execution

# Concise output of a task step
TASK_STEP_OUTPUT_DESCRIPTION = (
    "Concise result of this step that can be used by subsequent steps, or shown to the user if this is the final step. "
    "Include all essential information, without referencing the rest of the response."
)

