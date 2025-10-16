from typing import AsyncGenerator
from openai import AsyncOpenAI
import re
import httpx

from app.services.llm_service_base import LlmService, ModelDescription, StreamedChunk, LlmMessage


# TODO: Handle API errors related to API key (incorrect, no credits, etc.) and return 422 from API
class OpenRouterLlmService(LlmService):
    """OpenRouter implementation of LLM service"""
    
    def __init__(self) -> None:
        self._base_url = "https://openrouter.ai/api/v1"
    
    def _build_system_message(self, additional_requested_data: dict[str, str] | None) -> str:
        """Build system message with instructions for additional data format"""
        base_message = "You are a helpful assistant."
        
        if additional_requested_data:
            data_instructions = "\n\nWhen responding, you may optionally include additional structured data using the following format:\n"
            for key, description in additional_requested_data.items():
                data_instructions += f'<additional_data name="{key}">[{description}]</additional_data>\n'
            data_instructions += "\nAll additional data values should be plain text, unless otherwise specified."
            data_instructions += "\nPlease include all requested additional data in your response, unless the description of the field says otherwise."
            return base_message + data_instructions
        
        return base_message
    
    def _parse_additional_data(self, content: str) -> tuple[str, dict[str, str]]:
        """Extract additional data tags from content and return cleaned content + data dict"""
        additional_data: dict[str, str] = {}
        
        # Find all additional_data tags
        pattern = r'<additional_data name="([^"]+)">(.+?)</additional_data>'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for key, value in matches:
            additional_data[key] = value.strip()
        
        # Remove tags from content
        cleaned_content = re.sub(pattern, '', content, flags=re.DOTALL).strip()
        
        return cleaned_content, additional_data
    
    async def get_completion(
        self,
        api_key: str,
        model: str,
        messages: list[LlmMessage],
        additional_requested_data: dict[str, str] | None = None,
        temperature: float = 0.7,
    ) -> LlmMessage:
        """
        Prompt a model and get an answer using OpenRouter.
        """
        client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=api_key,
        )
        
        # Build messages for OpenAI format
        openai_messages = []
        
        # Add system message with additional data instructions
        system_msg = self._build_system_message(additional_requested_data)
        openai_messages.append({"role": "system", "content": system_msg})
        
        for msg in messages:
            openai_messages.append({"role": msg.role, "content": msg.content})
        
        # Make API call
        response = await client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
        )
        
        # Extract response content
        raw_content = response.choices[0].message.content or ""
        
        # Parse additional data
        cleaned_content, additional_data = self._parse_additional_data(raw_content)
        
        return LlmMessage(
            role="assistant",
            content=cleaned_content,
            additional_data=additional_data,
        )
    
    # TODO: Check
    async def get_completion_streamed(
        self,
        api_key: str,
        model: str,
        messages: list[LlmMessage],
        additional_requested_data: dict[str, str] | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[StreamedChunk, None]:
        """
        Stream completion from OpenRouter, parsing additional data tags on the fly.
        """
        client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=api_key,
        )
        
        # Build messages for OpenAI format
        openai_messages = []
        
        # Add system message with additional data instructions
        system_msg = self._build_system_message(additional_requested_data)
        openai_messages.append({"role": "system", "content": system_msg})
        
        for msg in messages:
            openai_messages.append({"role": msg.role, "content": msg.content})
        
        # Make streaming API call
        stream = await client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
            stream=True,
        )
        
        # Buffer for detecting tags
        buffer = ""
        in_tag = False
        current_tag_name = None
        tag_content = ""
        
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta is None:
                continue
            
            buffer += delta
            
            # Try to detect and parse tags
            while buffer:
                if not in_tag:
                    # Look for opening tag
                    match = re.search(r'<additional_data name="([^"]+)">', buffer)
                    if match:
                        # Yield everything before the tag
                        before_tag = buffer[:match.start()]
                        if before_tag:
                            yield StreamedChunk(content=before_tag)
                        
                        current_tag_name = match.group(1)
                        in_tag = True
                        tag_content = ""
                        buffer = buffer[match.end():]
                    else:
                        # No opening tag found, but check if we might be building one
                        if '<additional_data' in buffer[-50:]:  # Keep some buffer
                            # Yield everything except the potential partial tag
                            safe_index = buffer.rfind('<additional_data')
                            if safe_index > 0:
                                yield StreamedChunk(content=buffer[:safe_index])
                                buffer = buffer[safe_index:]
                            break
                        else:
                            # Safe to yield everything
                            if buffer:
                                yield StreamedChunk(content=buffer)
                            buffer = ""
                            break
                else:
                    # Look for closing tag
                    close_tag = '</additional_data>'
                    close_index = buffer.find(close_tag)
                    if close_index != -1:
                        # Found closing tag
                        tag_content += buffer[:close_index]
                        yield StreamedChunk(
                            content=tag_content,
                            additional_data_key=current_tag_name,
                        )
                        in_tag = False
                        current_tag_name = None
                        tag_content = ""
                        buffer = buffer[close_index + len(close_tag):]
                    else:
                        # Keep accumulating tag content, but check if we might be building closing tag
                        if '</additional_data' in buffer[-30:]:
                            safe_index = buffer.rfind('</additional_data')
                            tag_content += buffer[:safe_index]
                            buffer = buffer[safe_index:]
                            break
                        else:
                            # Safe to add to tag content
                            tag_content += buffer
                            buffer = ""
                            break
        
        # Yield any remaining buffer
        if buffer:
            if in_tag:
                yield StreamedChunk(
                    content=tag_content + buffer,
                    additional_data_key=current_tag_name,
                )
            else:
                yield StreamedChunk(content=buffer)
    
    async def get_models(self) -> list[ModelDescription]:
        """
        Get list of available models from OpenRouter.
        """        
        async with httpx.AsyncClient() as client:
            response = await client.get("https://openrouter.ai/api/v1/models")
            response.raise_for_status()
            data = response.json()
        
        models = []
        for model_data in data.get("data", []):
            # Extract pricing information
            pricing = model_data.get("pricing", {})
            input_cost = float(pricing.get("prompt", 0))
            output_cost = float(pricing.get("completion", 0))
            
            # OpenRouter returns cost per token, convert to per million
            input_cost_per_million = input_cost * 1_000_000
            output_cost_per_million = output_cost * 1_000_000
            
            models.append(ModelDescription(
                name=model_data.get("id", ""),
                description=model_data.get("description", ""),
                provider=model_data.get("name", "").split("/")[0] if "/" in model_data.get("name", "") else "",
                context_length=model_data.get("context_length", 0),
                input_cost_per_million=input_cost_per_million,
                output_cost_per_million=output_cost_per_million,
            ))
        
        return models