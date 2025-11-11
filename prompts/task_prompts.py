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
   - The step type: either "normal" for regular execution steps, or "reevaluate" for a reevaluation point where the plan can be adjusted based on results so far (optional, defaults to "normal")
   - The complexity level: {complexity_levels}
   - Required model capabilities (only specify if actually needed): {capabilities}
4. The final step's output will be treated as the final output of the task, and will be shown to the user. This means that usually it's a good idea for the last step to summarize and combine all necessary information from previous steps.

Important notes about step execution:
- When a step is executed, all previous steps' prompts and outputs will be automatically provided to the model
- Steps can naturally reference previous steps (e.g., "use the information from step 3", "based on the previous analysis")
- Later steps can build upon earlier outputs without special syntax

About reevaluation steps:
- Use "reevaluate" step type when you want to pause and reassess the plan based on intermediate results
- Reevaluation steps allow the system to generate new steps dynamically based on what has been learned
- Reevaluation steps are quite common and useful, especially when:
  * You need to make one step for each "something" in previous output (e.g., each proposed solution)
  * The next actions depend heavily on results from previous steps
  * The task involves exploring multiple approaches and choosing the best one
- Don't put steps after a reevaluate step, as they will be replaced by the reevaluation anyway
- Reevaluate steps only need a prompt - no complexity or capabilities

Simple tasks:
- If the task is simple and doesn't require multiple steps, return a single step representing the entire task
- The prompt can either be the same as the user's request, or rephrased to be clearer and more actionable for an LLM

Example (multi-step):
If I ask to "research the population of France and then create a comparison chart with Germany":
- Step 1: "Find the current population of France" (step_type: normal, complexity: low, capabilities: [web_search])
- Step 2: "Find the current population of Germany" (step_type: normal, complexity: low, capabilities: [web_search])
- Step 3: "Create a comparison chart showing the populations of France and Germany based on the previous findings" (step_type: normal, complexity: medium, capabilities: [])

Example (simple task):
If I ask to "write a poem about cats":
- Step 1: "Write a creative and engaging poem about cats" (step_type: normal, complexity: low, capabilities: [])

Now, please decompose this task:
{user_prompt}"""

# Additional data descriptions for task decomposition

# Concise task title (3-8 words)
TASK_TITLE_DESCRIPTION = "A concise title (3-8 words) that summarizes the task"

# Steps description template for task decomposition
# Template variables: {complexity_levels}, {capabilities}
TASK_STEPS_DESCRIPTION_TEMPLATE = """JSON array of step objects. Each object must have:
- "prompt": string describing the step task (can reference previous steps naturally, e.g. "analyze the results from step 2")
- "step_type": string, either "normal" or "reevaluate" (optional, defaults to "normal" if not specified)

For normal steps only:
- "complexity": string, one of: {complexity_levels}
- "required_capabilities": array of strings from: {capabilities} (only include capabilities that are actually needed; can be empty array if no special capabilities required)

For reevaluate steps, only prompt and step_type are needed.

Example: [{{"prompt": "Research X", "step_type": "normal", "complexity": "low", "required_capabilities": ["web_search"]}}, {{"prompt": "Reevaluate next steps based on research", "step_type": "reevaluate"}}]"""

# Task step execution context template
# Template variables: {task_title_or_prompt}, {previous_steps}, {step_number}, {step_prompt}
TASK_STEP_CONTEXT_TEMPLATE = """
Please complete the next step in the task, based on previous completed steps and their outputs.
The result of this step should be returned in the "output" field of "additional_data" in the response. 
This output should be independent of the rest of the response, and not reference it.
The rest of the response can contain reasoning, justifications, or anything else, or it can be skipped entirely (in which case only the "output" field should be returned).

Task: {task_title_or_prompt}

{previous_steps}
Current step (Step {step_number}):
{step_prompt}
"""

# Format for previous step in context
# Template variables: {step_number}, {step_prompt}, {step_output}
TASK_PREVIOUS_STEP_FORMAT = """Step {step_number}: {step_prompt}
Output: {step_output}
"""

# Format for reevaluate step in context
# Template variables: {step_number}, {step_prompt}
TASK_REEVALUATE_STEP_FORMAT = """Step {step_number} (Reevaluate): {step_prompt}
"""

# Additional data descriptions for task step execution

# Concise output of a task step
TASK_STEP_OUTPUT_DESCRIPTION = (
    "Result of this step that can be used by subsequent steps, or shown to the user if this is the final step. "
    "Include all essential information, without referencing the rest of the response. "
    "The output should be independent of the rest of the response, and not reference it. "
    "It should not include information that is not necessary for the next step or the user (e.g. reasoning, excessive justifications, etc.)."
)

# Task reevaluation prompt template
# Template variables: {original_prompt}, {task_title}, {previous_steps}, {complexity_levels}, {capabilities}
TASK_REEVALUATION_PROMPT_TEMPLATE = """You are reevaluating a task's execution plan based on the results of previous steps.

Original task prompt: {original_prompt}
Task title: {task_title}

{previous_steps}

Based on the task, the title, and the results so far, generate a new sequence of steps to complete the remaining work.
Follow these guidelines:
1. Break the remaining work into clear, sequential steps
2. Each step should be self-contained and actionable
3. For each step, specify:
   - A clear prompt that describes what needs to be done
   - The step type: either "normal" for regular execution steps, or "reevaluate" for another reevaluation point (optional, defaults to "normal")
   
For normal steps only:
   - The complexity level: {complexity_levels}
   - Required model capabilities (only specify if actually needed): {capabilities}

For reevaluate steps, only prompt and step_type are needed.

4. The final step's output will be treated as the final output of the task, and will be shown to the user
5. Steps can naturally reference previous steps (e.g., "use the information from step 3", "based on the previous analysis")

Note: If you include a "reevaluate" step, avoid putting additional steps after it, as they will be replaced by the reevaluation anyway.

Generate the new steps to complete the task based on what has been accomplished so far."""

# Steps description template for task reevaluation
# Template variables: {complexity_levels}, {capabilities}
TASK_REEVALUATION_STEPS_DESCRIPTION_TEMPLATE = """JSON array of step objects. Each object must have:
- "prompt": string describing the step task (can reference previous steps naturally, e.g. "analyze the results from step 2")
- "step_type": string, either "normal" or "reevaluate" (optional, defaults to "normal" if not specified)

For normal steps only:
- "complexity": string, one of: {complexity_levels}
- "required_capabilities": array of strings from: {capabilities} (only include capabilities that are actually needed; can be empty array if no special capabilities required)

For reevaluate steps, only prompt and step_type are needed.

Example: [{{"prompt": "Research X", "step_type": "normal", "complexity": "low", "required_capabilities": ["web_search"]}}, {{"prompt": "Reevaluate approach based on findings", "step_type": "reevaluate"}}]"""

