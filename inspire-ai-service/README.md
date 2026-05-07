# inspire-ai-service

This is the FastAPI AI service for SugFoodApp.

The full project setup lives in the root [README.md](/c:/Users/hung.pn/Desktop/Code/sugFoodApp/README.md). Use that document for the complete FE + DB + AI startup flow.

## Modes

`food_chat`
- Default local-dev mode
- Powers `POST /api/v1/food/chat-suggestions`
- Skips eager knowledge/vector-store initialization
- Needs only LLM configuration

`full`
- Optional knowledge/RAG mode
- Keeps the broader helpdesk/knowledge endpoints available
- Requires vector-store and task-queue infrastructure to be configured

## Local Env

Copy [`.env.example`](/c:/Users/hung.pn/Desktop/Code/sugFoodApp/inspire-ai-service/.env.example) to `.env`.

Minimum config for this project:
- `AI_SERVICE_MODE=food_chat`
- `APP_HOST`
- `APP_PORT`
- `LLM__PROVIDER`
- the matching provider API key

Optional full-mode config:
- `INFRA__VECTOR_STORE__*`
- `INFRA__TASK_QUEUE__*`
- `AI_SERVICE__URL` callback settings

## Local Commands

```bash
poetry install
poetry run dev
```

Default local URL: `http://localhost:8000`
