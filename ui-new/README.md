# ui-new (Refinance V2)

React + Vite + TypeScript frontend that runs alongside the legacy Flask/Jinja2 UI.

## Stack

- React 19 + Vite 7 + TypeScript
- Zustand for app state
- React Hook Form + Zod for forms/validation
- Mantine + Tailwind CSS for UI
- ESLint + Prettier for style guide enforcement

## Run

```bash
# from repo root
make dev

# in another terminal
cd ui-new
npm run dev
```

- V2 UI: `http://localhost:5173`
- Legacy UI: `http://localhost:9000`
- API: `http://localhost:8000`

## API integration

- Vite proxy forwards `/api/*` to `http://localhost:8000/*`
- All requests should use `/api` prefix from the browser
- Auth token is sent as `X-Token`

## Component conventions

All components are folder-based:

```text
src/components/ComponentName/
  ComponentName.tsx
  index.ts
```

For grouped components (e.g. list + item), keep them under the same component folder.

Shared UI-kit wrappers live under:

```text
src/components/ui/
```

Example:

```text
src/components/ui/AppCard/
  AppCard.tsx
  index.ts
```

## Style guide

- Function components only (no class components)
- No `component.displayName`
- Prefer named exports; no default exports in app components/modules
- Keep imports via `@/` alias
- Keep props/types explicit

## Scripts

- `npm run dev` - start dev server
- `npm run build` - type-check + production build
- `npm run lint` - strict lint
- `npm run format` - format files
- `npm run format:check` - verify formatting

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
]);
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x';
import reactDom from 'eslint-plugin-react-dom';

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
]);
```
