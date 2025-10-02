# LLimit - LLM Gateway Backend

A backend service for LLM interactions with chat threads, persistent memory, async operations, and authentication.

## Getting Started

### Installation

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd llimit
uv sync
```

### Run the Server

```bash
python main.py
```

Or using uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

The server will start at `http://localhost:8000`

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Authentication

All endpoints (except `/health`) require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: dev-api-key-12345" http://localhost:8000/chat/threads
```

For development, use: `dev-api-key-12345`
