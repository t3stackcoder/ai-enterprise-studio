# @ai-enterprise-studio/shared

Shared utilities, types, and constants for AI Enterprise Studio.

## Contents

- **types.ts**: TypeScript type definitions for chess analysis, WebSocket communication, and more
- **utils.ts**: Common utility functions for FEN validation, evaluation formatting, etc.

## Usage

```typescript
import {
  AnalysisRequest,
  isValidFEN,
  formatEvaluation
} from '@ai-enterprise-studio/shared';

// Validate FEN
const isValid = isValidFEN('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');

// Format evaluation
const evalStr = formatEvaluation(150); // "+1.50"
```

## Building

```bash
npm run build
```
