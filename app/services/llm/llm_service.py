from typing import AsyncGenerator
from openai import AsyncOpenAI
from fastapi import HTTPException
import re

from app.models.model.models import ModelDescription
from app.services.llm.config.llm_config import LlmConfig
from app.services.llm.config.reasoning_config import ReasoningConfig
from app.services.llm.config.web_search_config import WebSearchConfig
from app.services.llm.llm_service_base import LlmService, StreamedChunk, LlmLogger
from app.services.llm.llm_message import LlmMessage
from app.services.llm.llm_file import LlmFileBase
from app.services.model_cache_service import ModelCacheService
from prompts.llm_base_prompts import BASE_SYSTEM_MESSAGE, ADDITIONAL_DATA_INSTRUCTIONS_TEMPLATE


INTERNAL_REASONING_KEY = "_internal_reasoning"
INTERNAL_REASONING_SUMMARY_KEY = "_internal_reasoning_summary"


# TODO: Handle API errors related to API key (incorrect, no credits, etc.) and return 422 from API
class OpenRouterLlmService(LlmService):
    """OpenRouter implementation of LLM service"""
    
    def __init__(self, model_cache_service: ModelCacheService) -> None:
        self._base_url = "https://openrouter.ai/api/v1"
        self._model_cache_service = model_cache_service
    
    def _build_system_message(self, additional_requested_data: dict[str, str] | None) -> str:
        """Build system message with instructions for additional data format"""
        if additional_requested_data:
            data_instructions = ADDITIONAL_DATA_INSTRUCTIONS_TEMPLATE
            for key, description in additional_requested_data.items():
                data_instructions += f'{key}: {description}\n'
            
            return BASE_SYSTEM_MESSAGE + data_instructions
        
        return BASE_SYSTEM_MESSAGE

    def _build_web_search_config(
        self,
        config: WebSearchConfig,
        model_supports_native: bool,
    ) -> tuple[list[dict] | None, dict | None]:
        """
        Build web search configuration for OpenRouter API.
        Returns: (plugins_config, web_search_options)
        """
        if not config.is_enabled():
            return None, None

        plugins = None
        web_search_options = None

        # Determine which engines to use based on config and model support
        use_exa = config.use_exa_search
        use_native = config.use_native_search and model_supports_native
        
        # If native is requested but not supported, fall back to Exa
        if config.use_native_search and not model_supports_native:
            use_exa = True

        # Build configuration based on engines
        if use_exa:
            plugins = [{
                "id": "web",
                "engine": "exa",
                "max_results": config.max_results,
            }]
            if config.search_prompt:
                plugins[0]["search_prompt"] = config.search_prompt
        
        if use_native:
            web_search_options = {
                "search_context_size": config.search_context_size.value,
            }

        return plugins, web_search_options

    def _validate_additional_requested_data(self, additional_requested_data: dict[str, str] | None) -> None:
        """Validate that reserved keys are not used in additional_requested_data"""
        if additional_requested_data:
            if INTERNAL_REASONING_KEY in additional_requested_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Additional data key '{INTERNAL_REASONING_KEY}' is reserved for internal use"
                )
            if INTERNAL_REASONING_SUMMARY_KEY in additional_requested_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Additional data key '{INTERNAL_REASONING_SUMMARY_KEY}' is reserved for internal use"
                )

    def _validate_supported_inputs(self, messages: list[LlmMessage], model_description: ModelDescription) -> None:
        """Validate that the files in messages are supported by the model"""
        files = []
        for msg in messages:
            files.extend(msg.files)
        
        errors = []
        for file in files:
            validation_error = file.validate(model_description)
            if validation_error:
                errors.append(validation_error)
        
        if errors:
            raise HTTPException(status_code=400, detail="\n".join(errors))

    def _build_reasoning_config(self, reasoning_config: ReasoningConfig, model_supports_reasoning: bool) -> dict | None:
        """Build reasoning configuration for OpenRouter API"""
        if not reasoning_config.is_enabled() or not model_supports_reasoning:
            return None
        
        return {
            "effort": reasoning_config.effort.value
        }

    def _build_extra_body(self, config: LlmConfig | None, model_description: ModelDescription) -> dict | None:
        """Build extra body for OpenRouter API"""
        if config is None:
            return None
        
        extra_body = {}
        
        # Add web search config
        if config.web_search.is_enabled():
            plugins, web_search_options = self._build_web_search_config(
                config.web_search, 
                model_description.supports_native_web_search
            )
            if plugins:
                extra_body["plugins"] = plugins
            if web_search_options:
                extra_body["web_search_options"] = web_search_options
        
        # Add reasoning config
        reasoning_config = self._build_reasoning_config(config.reasoning, model_description.supports_reasoning)
        if reasoning_config:
            extra_body["reasoning"] = reasoning_config
        
        return extra_body if extra_body else None

    def _parse_additional_data(self, content: str) -> tuple[str, dict[str, str]]:
        """Extract additional data tags from content and return cleaned content + data dict"""
        additional_data: dict[str, str] = {}
        
        # Find all additional_data tags (format: <additional_data key=NAME>VALUE</additional_data>)
        pattern = r'<additional_data key=([^>]+)>(.*?)</additional_data>'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for key, value in matches:
            additional_data[key.strip()] = value.strip()
        
        # Remove tags from content
        cleaned_content = re.sub(pattern, '', content, flags=re.DOTALL).strip()
        
        return cleaned_content, additional_data

    def _extract_reasoning_from_message(self, message: any) -> dict[str, str]:
        """Extract reasoning data from a non-streaming message response"""
        reasoning_data: dict[str, str] = {}
        
        # Add simple reasoning field if available (for models that return simple string)
        reasoning = getattr(message, "reasoning", None)
        if reasoning:
            reasoning_data[INTERNAL_REASONING_KEY] = reasoning
        
        # Add structured reasoning_details if available (for advanced use cases)
        reasoning_details = getattr(message, "reasoning_details", None)
        if not reasoning_details:
            return reasoning_data
        
        reasoning_texts = []
        reasoning_summaries = []
        
        for detail in reasoning_details:
            detail_type = getattr(detail, "type", None)
            if detail_type == "reasoning.text":
                text = getattr(detail, "text", None)
                if text:
                    reasoning_texts.append(text)
            elif detail_type == "reasoning.summary":
                summary = getattr(detail, "summary", None)
                if summary:
                    reasoning_summaries.append(summary)
        
        if reasoning_texts:
            # Append to existing reasoning or set new
            if INTERNAL_REASONING_KEY in reasoning_data:
                reasoning_data[INTERNAL_REASONING_KEY] += "\n" + "\n".join(reasoning_texts)
            else:
                reasoning_data[INTERNAL_REASONING_KEY] = "\n".join(reasoning_texts)
        
        if reasoning_summaries:
            reasoning_data[INTERNAL_REASONING_SUMMARY_KEY] = "\n".join(reasoning_summaries)
        
        return reasoning_data

    def _yield_reasoning_chunks_from_delta(self, delta: any) -> list[StreamedChunk]:
        """Extract reasoning chunks from a streaming delta and return list of chunks to yield"""
        reasoning_details = getattr(delta, "reasoning_details", None)
        if not reasoning_details:
            return []
        
        chunks: list[StreamedChunk] = []
        for detail in reasoning_details:
            detail_type = getattr(detail, "type", None)
            
            if detail_type == "reasoning.text":
                text = getattr(detail, "text", None)
                if text:
                    chunks.append(StreamedChunk(
                        content=text,
                        additional_data_key=INTERNAL_REASONING_KEY,
                    ))
            elif detail_type == "reasoning.summary":
                summary = getattr(detail, "summary", None)
                if summary:
                    chunks.append(StreamedChunk(
                        content=summary,
                        additional_data_key=INTERNAL_REASONING_SUMMARY_KEY,
                    ))
        
        return chunks
    
    def _build_messages(self, messages: list[LlmMessage], additional_requested_data: dict[str, str] | None) -> list[dict]:
        openai_messages = []
        
        # Add system message with additional data instructions
        system_msg = self._build_system_message(additional_requested_data)
        openai_messages.append(LlmMessage.system(system_msg).to_dict())
        
        for msg in messages:
            openai_messages.append(msg.to_dict())
        
        return openai_messages
    
    async def get_completion(
        self,
        api_key: str,
        model: str,
        messages: list[LlmMessage],
        additional_requested_data: dict[str, str] | None = None,
        temperature: float = 0.7,
        config: LlmConfig | None = None,
        logger: LlmLogger | None = None,
    ) -> LlmMessage:
        """
        Prompt a model and get an answer using OpenRouter.
        """
        self._validate_additional_requested_data(additional_requested_data)
        
        # Validate model and get description
        model_desc = await self._model_cache_service.get_model_by_id(model)
        if model_desc is None:
            raise HTTPException(status_code=404, detail=f"Model '{model}' not found")
        
        # Validate that files in messages are supported by the model
        self._validate_supported_inputs(messages, model_desc)
        
        if config is None:
            config = LlmConfig.default()
        
        if logger:
            logger.log_request(model, messages, additional_requested_data, temperature, config)
        
        client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=api_key,
        )
        
        openai_messages = self._build_messages(messages, additional_requested_data)
        extra_body = self._build_extra_body(config, model_desc)
        
        response = await client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
            extra_body=extra_body,
        )
        
        # Extract response content
        message = response.choices[0].message
        raw_content = message.content or ""
        
        # Parse additional data
        cleaned_content, additional_data = self._parse_additional_data(raw_content)
        
        # Extract reasoning data
        reasoning_data = self._extract_reasoning_from_message(message)
        additional_data.update(reasoning_data)
        
        response_message = LlmMessage.assistant(cleaned_content, additional_data)
        
        if logger:
            logger.log_response(model, response_message, config)
        
        return response_message

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
        
        # Look for complete opening tag (format: <additional_data key=NAME>)
        match = re.search(r'<additional_data key=([^>]+)>', buffer)
        if match:
            # Found complete opening tag
            before_tag = buffer[:match.start()]
            if before_tag:
                chunks_to_yield.append(StreamedChunk(content=before_tag))
            new_tag_name = match.group(1).strip()
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
        config: LlmConfig | None = None,
    ) -> AsyncGenerator[StreamedChunk, None]:
        """
        Stream completion from OpenRouter, parsing additional data tags on the fly.
        """
        self._validate_additional_requested_data(additional_requested_data)
        
        # Validate model and get description
        model_desc = await self._model_cache_service.get_model_by_id(model)
        if model_desc is None:
            raise HTTPException(status_code=404, detail=f"Model '{model}' not found")
        
        # Validate that files in messages are supported by the model
        self._validate_supported_inputs(messages, model_desc)
        
        # Use default config if not provided
        if config is None:
            config = LlmConfig.default()
        
        client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=api_key,
        )
        
        openai_messages = self._build_messages(messages, additional_requested_data)
        extra_body = self._build_extra_body(config, model_desc)
        
        stream = await client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
            stream=True,
            extra_body=extra_body,
        )
        
        # Buffer for detecting tags
        buffer = ""
        in_tag = False
        current_tag_name: str | None = None
        tag_content = ""
        
        async for chunk in stream:
            delta = chunk.choices[0].delta
            
            # Handle reasoning if present - stream it as it comes in
            reasoning_chunks = self._yield_reasoning_chunks_from_delta(delta)
            for reasoning_chunk in reasoning_chunks:
                yield reasoning_chunk
            
            # Handle content
            content = delta.content
            if content is None:
                continue
            
            buffer += content
            
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