# Config Package

Shared configuration files for all frontend apps.

## Exports

- `@ai-enterprise-studio/config/eslint` - ESLint configuration
- `@ai-enterprise-studio/config/typescript` - Base TypeScript config
- `@ai-enterprise-studio/config/vite` - Base Vite config

## Usage

**TypeScript:**

```json
{
  "extends": "@ai-enterprise-studio/config/typescript",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

**ESLint:**

```js
import baseConfig from "@ai-enterprise-studio/config/eslint";
export default baseConfig;
```

**Vite:**

```ts
import { defineConfig } from "vite";
import baseConfig from "@ai-enterprise-studio/config/vite";
export default defineConfig({
  ...baseConfig,
  // Your overrides
});
```
