# SugFoodApp

SugFoodApp is a lunch decision app with a Next.js frontend and a FastAPI AI service.

The app now standardizes on `/api/v1` only:
- `AI chat suggestion` handles freeform food prompts and quick suggestion chips.
- `Ranker engine` makes the final room decision from room context, user preferences, and votes.
- Legacy `/api/rooms/*` endpoints are frozen and return `410 Gone`.

## Repo Layout

- `inspire-fe`: Next.js app, PostgreSQL schema/seed scripts, `/api/v1` routes, ranker logic.
- `inspire-ai-service`: FastAPI service for chat suggestions, with optional full knowledge mode.

## Prerequisites

- Node.js 20+
- npm
- Python 3.11+
- Poetry
- PostgreSQL

## Database Setup

1. Create a local PostgreSQL database. The default project name is `inspire`.
2. Copy [inspire-fe/.env.example](/c:/Users/hung.pn/Desktop/Code/sugFoodApp/inspire-fe/.env.example) to `inspire-fe/.env.local` and fill in the DB credentials.
3. Install frontend dependencies:

```bash
cd inspire-fe
npm install
```

4. Prepare the schema and seed data:

```bash
npm run db:prepare
```

What the DB scripts do in local dev:
- `npm run db:seed` reapplies `database/schema.sql`, clears seeded restaurant/menu data, and inserts the restaurant catalog again.
- `npm run db:backfill` populates v1 ranking/domain tables from the restaurant and menu catalog.
- `npm run db:prepare` runs both commands in sequence.

After pulling the ASCII image rename change, rerun `npm run db:prepare` so seeded restaurant image URLs match the new file names.

## Frontend Setup

1. Stay in `inspire-fe`.
2. Make sure `inspire-fe/.env.local` includes:
- DB settings
- `NEXT_PUBLIC_APP_URL`
- `SESSION_SECRET`
- `JOB_SECRET`
- `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN`
- `ADMIN_EMAILS`
- `AI_SERVICE_BASE_URL`
3. Start the app:

```bash
npm run dev
```

The frontend runs on `http://localhost:3000` by default.

## AI Service Setup

1. Open a second terminal:

```bash
cd inspire-ai-service
poetry install
```

2. Copy [inspire-ai-service/.env.example](/c:/Users/hung.pn/Desktop/Code/sugFoodApp/inspire-ai-service/.env.example) to `inspire-ai-service/.env`.
3. Set at least:
- `AI_SERVICE_MODE=food_chat`
- `LLM__PROVIDER`
- the matching provider API key

4. Start the AI service:

```bash
poetry run dev
```

The AI service runs on `http://localhost:8000` by default.

## How FE Talks To AI

- The browser calls `POST /api/v1/ai/chat-suggestions` on the frontend server.
- The frontend server tries `POST /api/v1/food/chat-suggestions` on the Python AI service.
- If the AI service is unavailable, the frontend falls back to a Vietnamese-first suggestion engine on the server.

## AI Split

`AI chat suggestion`:
- Browser entrypoint: `POST /api/v1/ai/chat-suggestions`
- Python service entrypoint: `POST /api/v1/food/chat-suggestions`
- Used for freeform chat and quick suggestion chips
- Returns conversational suggestion copy plus matched restaurants

`Ranker engine`:
- Runs inside the frontend server during room recommendation and vote-close flows
- Final authority stays in `runRecommendationRanker` and `closeVoteAndFinalize`
- Uses room context, member preferences, shortlist signals, and votes
- Does not call an LLM during ranking or finalization

## Running The Full Stack

1. Start PostgreSQL.
2. Run `npm run db:prepare` inside `inspire-fe`.
3. Run `npm run dev` inside `inspire-fe`.
4. Run `poetry run dev` inside `inspire-ai-service`.
5. Open `http://localhost:3000`.

## Notes

- `/api/rooms/*` is legacy and intentionally frozen.
- The shortlist flow is the only supported "add from Home/Detail" path now.
- FE lint/build was not runnable in this workspace before dependency install because local `node_modules` were missing, so rerun lint/build after `npm install`.
