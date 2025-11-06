from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    prompt: str = Field(..., description="The complex prompt to be broken down into steps")
    
    # TODO: ???
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Research the latest AI trends, write a summary report, create visualizations, and prepare a presentation"
                }
            ]
        }
    }

