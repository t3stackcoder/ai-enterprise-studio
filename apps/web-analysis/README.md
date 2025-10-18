# Web Analysis - Remote Microfrontend

Chess position analysis UI - exposed as a remote microfrontend.

## Architecture

This is a **Module Federation Remote** that:

- Exposes analysis UI components to the shell
- Connects to `ws://localhost:8765` (analysis-server)
- Can run standalone or as part of the host shell
- Runs on `http://localhost:3001`

## Exposed Components

```typescript
// Available to host shell
import AnalysisApp from "analysis/AnalysisApp";
import AnalysisRoutes from "analysis/AnalysisRoutes";
```

## Getting Started

```bash
# Install dependencies
npm install

# Start dev server (standalone)
npm run dev

# Or run as part of the shell
cd ../web-shell
npm run dev
```

## WebSocket Integration

Connects to the analysis server:

- **URL**: `ws://localhost:8765`
- **Protocol**: WebSocket for real-time chess analysis
- **Engines**: Stockfish and Leela Chess Zero

## Structure

```
src/
├── components/      # Analysis UI components
├── hooks/          # WebSocket hooks, analysis state
├── App.tsx         # Main analysis app
└── routes.tsx      # Analysis routes
```

## Independent Development

This remote can be developed independently:

1. Start analysis-server: `cd apps/analysis-server && python server.py`
2. Start this remote: `npm run dev`
3. Access at `http://localhost:3001`
