from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.dependencies import get_database, get_user_repo, get_api_key_service, initialize_services, dispose_services
from app.api.routes.api_keys import router as api_keys_router
from app.api.routes.chat import router as chat_router
from app.api.routes.completions import router as completions_router
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.models import router as models_router
from app.api.routes.sse import router as sse_router
from app.api.routes.task import router as task_router
from app.settings import settings


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application startup and shutdown"""
    await initialize_services()
    yield
    await dispose_services()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="LLM Gateway Backend with chat threads, memory, and more",
        swagger_ui_parameters={
            "persistAuthorization": True,
        },
        lifespan=lifespan,
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
    app.include_router(files_router)
    app.include_router(models_router)
    app.include_router(sse_router)
    app.include_router(task_router)
    app.include_router(api_keys_router)
    
    # Set custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)
    
    return app


# Initialize database schema before creating app
database = get_database()
database.setup()

app = create_app()

# Seed default user with API key
user_repo = get_user_repo()
api_key_service = get_api_key_service()

# Check if default user exists
if user_repo.get_user_by_id("default") is None:
    user_repo.create_user("default")
    
    # Create default API key for the user
    result = api_key_service.create_api_key(
        user_id="default",
        name="Default API Key",
        key_value=settings.api_key,
    )
    
    if result.plaintext_key != settings.api_key:
        print(f"Default user created with API key: {result.plaintext_key}")
        print("Save this key securely - it won't be shown again!")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
