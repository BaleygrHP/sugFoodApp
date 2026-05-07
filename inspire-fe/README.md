# inspire-fe

This is the Next.js frontend for SugFoodApp.

The full project setup lives in the root [README.md](/c:/Users/hung.pn/Desktop/Code/sugFoodApp/README.md). Use that document for:
- PostgreSQL setup
- schema/seed/backfill commands
- frontend and AI service startup
- the `/api/v1` flow overview

## Frontend Notes

- Main app URL: `http://localhost:3000`
- Browser traffic should stay on the frontend app; AI chat calls go through `POST /api/v1/ai/chat-suggestions`
- Server-to-server AI traffic uses `AI_SERVICE_BASE_URL`
- Legacy `/api/rooms/*` routes are frozen and should not be used

## Local Env

Copy [`.env.example`](/c:/Users/hung.pn/Desktop/Code/sugFoodApp/inspire-fe/.env.example) to `.env.local` and fill in:
- PostgreSQL connection values
- `NEXT_PUBLIC_APP_URL`
- `SESSION_SECRET`
- `JOB_SECRET`
- `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN`
- `ADMIN_EMAILS`
- `AI_SERVICE_BASE_URL`

## Local Commands

```bash
npm install
npm run db:prepare
npm run dev
```
