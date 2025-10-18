# Module Federation Architecture

Complete microfrontend architecture using Module Federation with React and TanStack Router.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    web-shell (Host)                     │
│                  http://localhost:3000                  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Loads remote apps dynamically                  │  │
│  │  Provides shared dependencies                   │  │
│  │  Handles auth, nav, global state                │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  Remote Apps:                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐   │
│  │  analysis    │  │  workspace   │  │  billing  │   │
│  │  :3001       │  │  :3002       │  │  :3003    │   │
│  └──────────────┘  └──────────────┘  └───────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Current Setup

### Host Application: `web-shell`
- **Port**: 3000
- **Purpose**: Container for all remote apps
- **Exposes**: Shared React, Router, and common dependencies

### Remote Applications

#### 1. `web-analysis` (Chess Analysis)
- **Port**: 3001
- **Purpose**: Chess position analysis UI
- **Connects to**: `ws://localhost:8765` (analysis-server)
- **Exposes**: 
  - `analysis/AnalysisApp` - Main analysis component
  - `analysis/AnalysisRoutes` - Analysis routes

#### 2. Future Remotes (Add as needed)
- `web-workspace` (Port: 3002) - Workspace management
- `web-billing` (Port: 3003) - Billing/pricing UI
- `web-admin` (Port: 3004) - Admin dashboard

## Quick Start

### Development Mode

**Option 1: Run everything**
```bash
npm run dev:web
```

**Option 2: Run specific apps**
```bash
# Terminal 1: Host shell
cd apps/web-shell
npm run dev

# Terminal 2: Analysis remote
cd apps/web-analysis
npm run dev
```

### Production Build

```bash
# Build all frontend apps
npm run build

# Or build specific app
cd apps/web-shell
npm run build
```

## Project Structure

```
apps/
├── web-shell/           # Host application (container)
│   ├── src/
│   │   ├── routes/      # TanStack Router routes
│   │   ├── components/  # Shell components (nav, layout)
│   │   └── main.tsx     # Entry point
│   ├── vite.config.ts   # Federation config (host)
│   └── package.json
│
├── web-analysis/        # Remote app (chess analysis)
│   ├── src/
│   │   ├── components/  # Analysis components
│   │   ├── hooks/       # WebSocket hooks
│   │   ├── App.tsx      # Exposed component
│   │   └── routes.tsx   # Exposed routes
│   ├── vite.config.ts   # Federation config (remote)
│   └── package.json
│
└── analysis-server/     # Python WebSocket server
    └── server.py        # Connects to chess engines

packages/
├── ui/                  # Shared React components
│   ├── src/
│   │   ├── components/  # Button, Card, Layout, etc.
│   │   └── index.ts     # Barrel exports
│   └── package.json
│
└── config/              # Shared configs
    ├── tsconfig.base.json
    └── package.json
```

## Adding a New Remote Application

### 1. Create the Remote App

```bash
mkdir -p apps/web-{name}
cd apps/web-{name}
```

### 2. Create `package.json`

```json
{
  "name": "@ai-enterprise-studio/web-{name}",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --port 3002",
    "build": "tsc && vite build"
  },
  "dependencies": {
    "@tanstack/react-router": "^1.75.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@originjs/vite-plugin-federation": "^1.3.6",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.7.2",
    "vite": "^6.0.1"
  }
}
```

### 3. Create `vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import federation from '@originjs/vite-plugin-federation'

export default defineConfig({
  plugins: [
    react(),
    federation({
      name: '{name}',
      filename: 'remoteEntry.js',
      exposes: {
        './{Name}App': './src/App.tsx',
        './{Name}Routes': './src/routes.tsx',
      },
      shared: {
        react: { singleton: true },
        'react-dom': { singleton: true },
        '@tanstack/react-router': { singleton: true },
      },
    }),
  ],
  server: { port: 3002 },
  build: {
    modulePreload: false,
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
  },
})
```

### 4. Update Host Shell

Edit `apps/web-shell/vite.config.ts`:

```typescript
remotes: {
  analysis: 'http://localhost:3001/assets/remoteEntry.js',
  {name}: 'http://localhost:3002/assets/remoteEntry.js', // ADD THIS
}
```

### 5. Install and Run

```bash
cd apps/web-{name}
npm install
npm run dev
```

## How It Works

### Module Federation

**Host (web-shell):**
- Loads remote apps dynamically at runtime
- Provides shared dependencies (React, Router)
- Each remote is lazy-loaded only when needed

**Remote (web-analysis, etc):**
- Exposes specific components/routes
- Can run standalone or as part of host
- Shares dependencies with host (no duplication)

### Shared Dependencies

All remotes share these from the host:
- `react` (singleton)
- `react-dom` (singleton)
- `@tanstack/react-router` (singleton)

This means:
- Only ONE copy of React in browser
- Consistent versions across all apps
- Smaller bundle sizes

### Independent Development

Each remote can be developed independently:

```bash
# Develop analysis remote alone
cd apps/web-analysis
npm run dev
# Access at http://localhost:3001

# Or develop as part of shell
cd apps/web-shell
npm run dev
# Shell loads remote from http://localhost:3001
```

## Integration with Backend

### Analysis Server Connection

The `web-analysis` remote connects to the Python WebSocket server:

```typescript
// In web-analysis
const ws = new WebSocket('ws://localhost:8765')

// Send chess position
ws.send(JSON.stringify({
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  depth: 20
}))

// Receive analysis
ws.onmessage = (event) => {
  const analysis = JSON.parse(event.data)
  // Update UI with analysis
}
```

### Running Full Stack

```bash
# Terminal 1: Analysis server (Python)
cd apps/analysis-server
python server.py

# Terminal 2: Host shell (React)
cd apps/web-shell
npm run dev

# Terminal 3: Analysis remote (React)
cd apps/web-analysis
npm run dev
```

Access at: `http://localhost:3000`

## Shared Components

Use components from `@ai-enterprise-studio/ui`:

```typescript
// In any remote or host
import { Button, Card, Layout } from '@ai-enterprise-studio/ui'

function MyComponent() {
  return (
    <Layout>
      <Card>
        <Button>Click me</Button>
      </Card>
    </Layout>
  )
}
```

## Troubleshooting

### Remote Not Loading

1. **Check remote is running:**
   ```bash
   curl http://localhost:3001/assets/remoteEntry.js
   ```

2. **Check console for CORS errors**
   - Remotes must be on different ports
   - Check Vite server.cors settings

3. **Verify remote URL in host config**
   ```typescript
   // web-shell/vite.config.ts
   remotes: {
     analysis: 'http://localhost:3001/assets/remoteEntry.js'
   }
   ```

### Version Conflicts

If you see "Shared module is not available":
- Ensure all apps use same React version
- Check `shared` config in vite.config.ts
- Set `singleton: true` for React/Router

### Build Issues

```bash
# Clean build
npm run clean
rm -rf node_modules
npm install
npm run build
```

## Best Practices

1. **Keep remotes independent**: Each should work standalone
2. **Share wisely**: Only share React, Router, and truly global libs
3. **Version consistency**: Use exact versions for shared deps
4. **Lazy load**: Load remotes only when needed
5. **Error boundaries**: Wrap remote imports in error boundaries
6. **Testing**: Test each remote both standalone and in shell

## Production Deployment

### Build All Apps

```bash
npm run build
```

### Deploy Strategy

1. **Deploy remotes first** (analysis, workspace, etc)
2. **Deploy host last** (web-shell)
3. **Update remote URLs** to production URLs in host config

### Environment Variables

```typescript
// vite.config.ts
remotes: {
  analysis: import.meta.env.VITE_ANALYSIS_URL || 'http://localhost:3001/assets/remoteEntry.js'
}
```

```bash
# .env.production
VITE_ANALYSIS_URL=https://analysis.yourapp.com/assets/remoteEntry.js
```

## Next Steps

1. **Add React code**: Drop your components into `web-shell/src/` and `web-analysis/src/`
2. **Set up routing**: Configure TanStack Router routes
3. **Add more remotes**: Create `web-workspace`, `web-billing`, etc.
4. **Shared UI**: Build components in `packages/ui/`
5. **State management**: Add Zustand/Redux if needed
6. **Authentication**: Implement in shell, share context with remotes

## Resources

- [Module Federation Docs](https://module-federation.io/)
- [TanStack Router](https://tanstack.com/router)
- [Vite Plugin Federation](https://github.com/originjs/vite-plugin-federation)
