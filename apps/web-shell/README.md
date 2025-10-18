# Web Shell - Host Application

The host application (container) for the AI Enterprise Studio microfrontend architecture.

## Architecture

This is a **Module Federation Host** that:

- Orchestrates remote microfrontends
- Provides shared dependencies (React, Router, etc.)
- Handles authentication and global navigation
- Runs on `http://localhost:3000`

## Remote Applications

Current remotes:

- **Analysis** (`http://localhost:3001`) - Chess analysis UI

Future remotes (add as needed):

- **Workspace** (`http://localhost:3002`) - Workspace management
- **Billing** (`http://localhost:3003`) - Billing/pricing UI

## Getting Started

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

## Adding New Remote Apps

1. Create new app in `apps/web-{name}/`
2. Configure it as a remote (see web-analysis example)
3. Add remote to `vite.config.ts`:

```ts
remotes: {
  analysis: 'http://localhost:3001/assets/remoteEntry.js',
  yourapp: 'http://localhost:3002/assets/remoteEntry.js',
}
```

4. Import and use in routes

## Structure

```
src/
├── routes/          # TanStack Router routes
├── components/      # Shell components (nav, layout)
└── main.tsx        # App entry point
```
