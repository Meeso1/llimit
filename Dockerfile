FROM python:3.13-slim AS base

RUN pip install uv

FROM base

WORKDIR /app

COPY . .
RUN uv pip install --system -r pyproject.toml
RUN mkdir -p data

EXPOSE 8000

CMD ["python", "main.py"]

