from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.routes.chat import router as chat_router
from app.api.routes.completions import router as completions_router
from app.api.routes.health import router as health_router
from app.api.routes.models import router as models_router
from app.core.config import settings


def custom_openapi(app: FastAPI):
    """Custom OpenAPI schema with security schemes for Swagger UI"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "APIKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key for authentication"
        },
        "OpenRouterAPIKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-OpenRouter-API-Key",
            "description": "OpenRouter API Key (required for LLM operations)"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="LLM Gateway Backend with chat threads, memory, and more",
        swagger_ui_parameters={
            "persistAuthorization": True,
        },
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(completions_router)
    app.include_router(models_router)
    
    # Set custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
