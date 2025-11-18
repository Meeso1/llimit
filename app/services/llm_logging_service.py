import os
from datetime import datetime, timezone

from app.services.llm.config.llm_config import LlmConfig
from app.services.llm.llm_service_base import LlmLogger, LlmMessage


class TaskLlmLogger(LlmLogger):
    """Logger for task-specific LLM interactions"""
    
    def __init__(self, task_id: str, logs_dir: str = "logs") -> None:
        self.task_id = task_id
        self.logs_dir = logs_dir
        self.log_file_path = os.path.join(logs_dir, f"task-{task_id}.log")
    
    def log_request(
        self,
        model: str,
        messages: list[LlmMessage],
        additional_requested_data: dict[str, str] | None,
        temperature: float,
        config: LlmConfig,
    ) -> None:
        """Log an LLM request"""
        os.makedirs(self.logs_dir, exist_ok=True)
        
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now(timezone.utc).isoformat()

            f.write(f"REQUEST [{timestamp}]\n")
            
            f.write(f"Model: {model} (temperature: {temperature})\n")
            
            f.write(f"Config:\n")
            f.write(f"\tReasoning: {config.reasoning.effort if config.reasoning else 'None'}\n")
            f.write(f"\tWeb Search: Exa: {config.web_search.use_exa_search}, Native: {config.web_search.use_native_search}\n")
            
            if additional_requested_data:
                f.write(f"\nAdditional Requested Data:\n")
                for key, description in additional_requested_data.items():
                    f.write(f"\t{key}: {description}\n")
            
            f.write(f"\nMessages:\n")
            for i, msg in enumerate(messages, 1):
                f.write(f"--- Message {i} (Role: {msg.role}) ---\n")
                f.write(msg.content)
                f.write("\n")
                
                if msg.additional_data:
                    f.write(f"Additional Data:\n")
                    for key, value in msg.additional_data.items():
                        f.write(f"{key}:\n{value}\n")
            
            f.write("\n")
    
    def log_response(
        self,
        model: str,
        response: LlmMessage,
        config: LlmConfig,
    ) -> None:
        """Log an LLM response"""
        os.makedirs(self.logs_dir, exist_ok=True)
        
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            f.write(f"RESPONSE [{timestamp}]\n")
            
            f.write(f"Model: {model}\n")
            
            f.write(f"Config:\n")
            f.write(f"\tReasoning: {config.reasoning.effort if config.reasoning else 'None'}\n")
            f.write(f"\tWeb Search: Exa: {config.web_search.use_exa_search}, Native: {config.web_search.use_native_search}\n")
            
            f.write(f"\nRole: {response.role}\n")
            f.write(f"{response.content}\n")
            
            if response.additional_data:
                f.write(f"Additional Data:\n")
                for key, value in response.additional_data.items():
                    f.write(f"{key}:\n{value}\n")
            
            f.write("\n")


class LlmLoggingService:
    """Service for creating LLM loggers"""
    
    def __init__(self, logs_dir: str = "logs") -> None:
        self.logs_dir = logs_dir
    
    def create_for_task(self, task_id: str) -> TaskLlmLogger:
        """Create a logger for a specific task"""
        return TaskLlmLogger(task_id, self.logs_dir)
