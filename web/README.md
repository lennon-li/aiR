# aiR — Web Frontend

Next.js frontend for [air.biostats.ai](https://air.biostats.ai). Sends chat and session requests to `air-api` on Cloud Run.

See the [root README](../README.md) for the full architecture.

## Development

```bash
npm install
npm run dev       # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` to point at a local or staging `air-api` instance.

## Structure

```
src/app/
  page.tsx        Main workspace (chat, console, plot panes)
  api.ts          API client (sessions, chat, execute)
  globals.css     Global styles
e2e/              Playwright end-to-end tests
```

## Deployment

Deployed to Cloud Run as `air-web`. See `../docs/DEPLOYMENT.md`.
