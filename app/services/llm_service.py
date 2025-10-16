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

    def _find_safe_content_end(self, buffer: str, tag_prefix: str) -> int:
        """
        Find the safe end position in buffer that doesn't split a tag.
        Returns the index where we can safely yield content without splitting a tag.
        """
        for i in range(1, min(len(tag_prefix) + 1, len(buffer) + 1)):
            if buffer.endswith(tag_prefix[:i]):
                return len(buffer) - i
        return len(buffer)
    
    def _process_opening_tag_state(
        self, 
        buffer: str, 
        current_tag_name: str | None, 
        tag_content: str
    ) -> tuple[str, bool, str | None, str, list[StreamedChunk]]:
        """
        Process buffer when not currently inside a tag.
        Returns: (remaining_buffer, in_tag, current_tag_name, tag_content, chunks_to_yield)
        """
        chunks_to_yield: list[StreamedChunk] = []
        
        # Look for complete opening tag
        match = re.search(r'<additional_data name="([^"]+)">', buffer)
        if match:
            # Found complete opening tag
            before_tag = buffer[:match.start()]
            if before_tag:
                chunks_to_yield.append(StreamedChunk(content=before_tag))
            new_tag_name = match.group(1)
            remaining_buffer = buffer[match.end():]
            return remaining_buffer, True, new_tag_name, "", chunks_to_yield
        
        # Check if buffer ends with partial opening tag
        safe_end = self._find_safe_content_end(buffer, '<additional_data')
        if safe_end > 0:
            # Yield safe content and keep partial tag in buffer
            chunks_to_yield.append(StreamedChunk(content=buffer[:safe_end]))
            return buffer[safe_end:], False, current_tag_name, tag_content, chunks_to_yield
        
        # No tag found, yield all content
        if buffer:
            chunks_to_yield.append(StreamedChunk(content=buffer))
        return "", False, current_tag_name, tag_content, chunks_to_yield
    
    def _process_closing_tag_state(
        self, 
        buffer: str, 
        current_tag_name: str | None, 
        tag_content: str
    ) -> tuple[str, bool, str | None, str, list[StreamedChunk]]:
        """
        Process buffer when currently inside a tag.
        Returns: (remaining_buffer, in_tag, current_tag_name, tag_content, chunks_to_yield)
        """
        chunks_to_yield: list[StreamedChunk] = []
        close_tag = '</additional_data>'
        close_index = buffer.find(close_tag)
        
        if close_index != -1:
            # Found complete closing tag
            tag_content += buffer[:close_index]
            chunks_to_yield.append(StreamedChunk(
                content=tag_content,
                additional_data_key=current_tag_name,
            ))
            remaining_buffer = buffer[close_index + len(close_tag):]
            return remaining_buffer, False, None, "", chunks_to_yield
        
        # Check if buffer ends with partial closing tag
        safe_end = self._find_safe_content_end(buffer, '</additional_data')
        if safe_end > 0:
            # Add safe content to tag and keep partial closing tag in buffer
            tag_content += buffer[:safe_end]
            return buffer[safe_end:], True, current_tag_name, tag_content, chunks_to_yield
        
        # No closing tag found, add all content to tag
        tag_content += buffer
        return "", True, current_tag_name, tag_content, chunks_to_yield

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
        current_tag_name: str | None = None
        tag_content = ""
        
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta is None:
                continue
            
            buffer += delta
            
            # Process buffer until no more complete tags can be found
            while buffer:
                if not in_tag:
                    buffer, in_tag, current_tag_name, tag_content, chunks_to_yield = self._process_opening_tag_state(
                        buffer, current_tag_name, tag_content
                    )
                    # Yield any chunks from processing
                    for chunk in chunks_to_yield:
                        yield chunk
                    # If we have remaining buffer, continue processing
                    if not buffer:
                        break
                else:
                    buffer, in_tag, current_tag_name, tag_content, chunks_to_yield = self._process_closing_tag_state(
                        buffer, current_tag_name, tag_content
                    )
                    # Yield any chunks from processing
                    for chunk in chunks_to_yield:
                        yield chunk
                    # If we have remaining buffer, continue processing
                    if not buffer:
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