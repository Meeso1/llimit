from dataclasses import dataclass
from typing import Any, Callable
from openai import OpenAI
import json


@dataclass
class LlmMessage:
    role: str
    content: str


@dataclass
class FunctionArgument:
    name: str
    type: str
    description: str
    required: bool


@dataclass
class LlmFunctionSpec:
    name: str
    description: str
    parameters: list[FunctionArgument]
    execute: Callable[[dict[str, Any]], Any]


@dataclass
class LlmModel:
    name: str
    description: str
    provider: str


class ArgumentValidationError(Exception):
    """Raised when tool arguments fail validation"""
    pass


class LlmService:
    def __init__(self) -> None:
        self._base_url = "https://openrouter.ai/api/v1"
    
    def _validate_function_arguments(
        self,
        func_spec: LlmFunctionSpec,
        arguments: dict[str, Any]
    ) -> None:
        """
        Validate that function arguments meet requirements.
        Raises ArgumentValidationError if validation fails.
        """
        # Check for required arguments
        required_params = [p for p in func_spec.parameters if p.required]
        for param in required_params:
            if param.name not in arguments:
                raise ArgumentValidationError(
                    f"Missing required argument '{param.name}' for function '{func_spec.name}'"
                )
        
        # Validate argument types
        type_validators = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        for param in func_spec.parameters:
            if param.name in arguments:
                value = arguments[param.name]
                if value is not None:  # Allow None for optional parameters
                    expected_type = type_validators.get(param.type)
                    if expected_type and not isinstance(value, expected_type):
                        raise ArgumentValidationError(
                            f"Argument '{param.name}' for function '{func_spec.name}' must be of type {param.type}, "
                            f"got {type(value).__name__}"
                        )
    
    def _function_spec_to_openai_tool(self, func_spec: LlmFunctionSpec) -> dict[str, Any]:
        """Convert LlmFunctionSpec to OpenAI tool format"""
        properties = {}
        required = []
        
        for param in func_spec.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": func_spec.name,
                "description": func_spec.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
    
    async def get_completion(
        self,
        model: str,
        messages: list[LlmMessage],
        tools: list[LlmFunctionSpec] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        api_key: str | None = None,
    ) -> str:
        """
        Get a completion from the LLM, handling tool calls if provided.
        
        Args:
            model: The model name to use
            messages: List of conversation messages
            tools: Optional list of function specifications for tool calling
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            api_key: OpenRouter API key
            
        Returns:
            The final text response from the model
        """
        if not api_key:
            raise ValueError("API key is required")
        
        client = OpenAI(
            base_url=self._base_url,
            api_key=api_key,
        )
        
        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Prepare tool definitions if provided
        openai_tools = None
        tools_map = {}
        if tools:
            openai_tools = [self._function_spec_to_openai_tool(t) for t in tools]
            tools_map = {t.name: t for t in tools}
        
        # Main conversation loop to handle tool calls
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Prepare request parameters
            request_params: dict[str, Any] = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
            }
            
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            
            if openai_tools:
                request_params["tools"] = openai_tools
            
            # Get completion
            response = client.chat.completions.create(**request_params)
            
            message = response.choices[0].message
            
            # Add assistant message to conversation
            openai_messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls if hasattr(message, 'tool_calls') else None,
            })
            
            # Check if there are tool calls to execute
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args_str = tool_call.function.arguments
                    
                    # Parse arguments
                    try:
                        func_args = json.loads(func_args_str)
                    except json.JSONDecodeError as e:
                        # Return error to the model
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: Invalid JSON arguments: {str(e)}",
                        })
                        continue
                    
                    # Get function spec
                    func_spec = tools_map.get(func_name)
                    if not func_spec:
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: Unknown function '{func_name}'",
                        })
                        continue
                    
                    # Validate arguments
                    try:
                        self._validate_function_arguments(func_spec, func_args)
                    except ArgumentValidationError as e:
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: {str(e)}",
                        })
                        continue
                    
                    # Execute function
                    try:
                        result = func_spec.execute(func_args)
                        result_str = json.dumps({"result": result}) if result is not None else json.dumps({"result": "success"})
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                    
                    # Add function result to conversation
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    })
                
                # Continue loop to get next response
                continue
            
            # No tool calls, return the final response
            return message.content or ""
        
        # If we hit max iterations, return last response
        return "Error: Maximum tool call iterations reached"
    
    async def list_models(self, api_key: str | None = None) -> list[LlmModel]:
        """
        List available models from OpenRouter.
        
        Args:
            api_key: OpenRouter API key
            
        Returns:
            List of available LLM models
        """
        if not api_key:
            raise ValueError("API key is required")
        
        client = OpenAI(
            base_url=self._base_url,
            api_key=api_key,
        )
        
        models_response = client.models.list()
        
        result = []
        for model in models_response.data:
            result.append(LlmModel(
                name=model.id,
                description=getattr(model, 'description', ''),
                provider=getattr(model, 'owned_by', 'unknown'),
            ))
        
        return result