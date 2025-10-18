# UI Package

Shared React components used across all microfrontends.

## Usage

```typescript
import { Button, Card, Layout } from "@ai-enterprise-studio/ui";
```

## Structure

```
src/
├── components/      # Shared React components
│   ├── Button.tsx
│   ├── Card.tsx
│   └── Layout.tsx
└── index.ts        # Barrel exports
```

## Adding Components

1. Create component in `src/components/`
2. Export from `src/index.ts`
3. Component is now available to all apps
