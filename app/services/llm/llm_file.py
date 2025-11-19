
from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
from typing import Any
from app.models.model.models import ModelDescription


class LlmFileBase(ABC):
    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        pass
    
    @abstractmethod
    def validate(self, model_description: ModelDescription) -> str | None:
        pass
    
    
@dataclass
class Pdf(LlmFileBase):
    name: str
    content: bytes
    
    def to_dict(self) -> dict[str, Any]:
        encoded_content = base64.b64encode(self.content).decode('utf-8')
        return {
            "type": "file",
            "file": {
                "filename": self.name,
                "file_data": f"data:application/pdf;base64,{encoded_content}"
            }
        }
        
    def validate(self, model_description: ModelDescription) -> str:
        return None # PDFs work with all models - either natively or via 'mistral-ocr'

  
@dataclass
class PrfUrl(LlmFileBase):
    name: str
    url: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "file",
            "file": {
                "filename": self.name,
                "file_data": self.url
            }
        }
    
    def validate(self, model_description: ModelDescription) -> str | None:
        return None # URLs work with all models


@dataclass
class Image(LlmFileBase):
    type: str # I.e. 'image/jpeg'
    content: bytes
    
    def to_dict(self) -> dict[str, Any]:
        encoded_content = base64.b64encode(self.content).decode('utf-8')
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{self.type};base64,{encoded_content}"
            }
        }
        
    def validate(self, model_description: ModelDescription) -> str | None:
        supproted_types = [f"image/{t}" for t in ["jpeg", "png", "gif", "webp"]]
        
        errors = []
        if self.type not in supproted_types:
            errors.append(f"Unsupported image type: {self.type}")
            
        if "image" not in model_description.architecture.input_modalities:
            errors.append("Model does not support image input")
        
        return "\n".join(errors) if errors else None


@dataclass
class ImageUrl(LlmFileBase):
    url: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "image_url",
            "image_url": {
                "url": self.url
            }
        }
    
    def validate(self, model_description: ModelDescription) -> str | None:
        if "image" not in model_description.architecture.input_modalities:
            return "Model does not support image input"
        
        return None


@dataclass
class Audio(LlmFileBase):
    type: str # I.e. 'wav'
    content: bytes
    
    def to_dict(self) -> dict[str, Any]:
        encoded_content = base64.b64encode(self.content).decode('utf-8')
        return {
            "type": "input_audio",
            "input_audio": {
                "data": encoded_content,
                "format": self.type
            }
        }
        
    def validate(self, model_description: ModelDescription) -> str | None:
        supported_types = ["wav", "mp3"]
        
        errors = []
        if self.type not in supported_types:
            errors.append(f"Unsupported audio type: {self.type}")
            
        if "audio" not in model_description.architecture.input_modalities:
            errors.append("Model does not support audio input")
            
        return "\n".join(errors) if errors else None
        

@dataclass
class Video(LlmFileBase):
    type: str # I.e. 'video/mp4'
    content: bytes
    
    def to_dict(self) -> dict[str, Any]:
        encoded_content = base64.b64encode(self.content).decode('utf-8')
        return {
            "type": "video_url",
            "video_url": {    
                "url": f"data:{self.type};base64,{encoded_content}"
            }
        }
        
    def validate(self, model_description: ModelDescription) -> str | None:
        supported_types = [f"video/{t}" for t in ["mp4", "mov", "mpeg", "webm"]]
        
        errors = []
        if self.type not in supported_types:
            errors.append(f"Unsupported video type: {self.type}")
            
        if "video" not in model_description.architecture.input_modalities:
            errors.append("Model does not support video input")
            
        return "\n".join(errors) if errors else None
        

@dataclass
class VideoUrl(LlmFileBase):
    url: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "video_url",
            "video_url": {
                "url": self.url
            }
        }
        
    def validate(self, model_description: ModelDescription) -> str | None:
        if "video" not in model_description.architecture.input_modalities:
            return "Model does not support video input"
        
        return None
