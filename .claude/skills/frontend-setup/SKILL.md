---
name: frontend-setup
description: Initialize the React 19 + Vite + TanStack Router + TanStack Query + Zustand + shadcn/ui + Tailwind + React Hook Form + Zod + Biome frontend project in the frontend/ directory. Use when starting frontend work or when the user says "set up the frontend", "initialize the frontend project", "bootstrap the UI". Produces a working dev server with all quality gates passing.
---

# Frontend Setup

Bootstrap a production-ready React 19 frontend following the architectural standards and quality gates defined in CLAUDE.md.

## 0. Prerequisites
- Node.js >= 20 (for React 19)
- Backend API running at `http://localhost:8000` (or configured via `VITE_API_BASE_URL`)

## 1. Initialize Project
```bash
cd frontend
npm create vite@latest . -- --template react-ts
```

## 2. Install Core Dependencies
```bash
# Framework & Routing
npm install react@19 react-dom@19
npm install @tanstack/react-router @tanstack/react-router-devtools
npm install @tanstack/react-query @tanstack/react-query-devtools

# State Management
npm install zustand

# Forms & Validation
npm install react-hook-form @hookform/resolvers zod

# Styling & Components
npm install tailwindcss@latest @tailwindcss/vite
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react

# Utilities
npm install date-fns
npm install axios

# Dev Dependencies
npm install -D @biomejs/biome
npm install -D @types/react @types/react-dom
npm install -D vite-tsconfig-paths
npm install -D @tanstack/router-plugin
npm install -D @testing-library/react @testing-library/jest-dom vitest jsdom @vitest/ui
npm install -D playwright @playwright/test
```

## 3. Configure shadcn/ui
```bash
npx shadcn@latest init
# Select: TypeScript, Default style, Slate base color, CSS variables, Yes to all prompts
```

Add essential components:
```bash
npx shadcn@latest add button input label textarea select checkbox radio-group switch
npx shadcn@latest add card table dialog dropdown-menu separator avatar badge
npx shadcn@latest add tabs sheet navigation-menu pagination tooltip popover
npx shadcn@latest add form date-picker calendar  # may need custom or use react-day-picker
npx shadcn@latest add command breadcrumb skeleton alert progress
npx shadcn@latest add sidebar  # for persistent navigation
```

## 4. Project Structure
```
frontend/
├── src/
│   ├── app/                    # App-level providers, router
│   │   ├── providers.tsx       # QueryClient, Router, Auth providers
│   │   └── router.tsx          # TanStack Router file-based routes
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components (auto-managed)
│   │   ├── layout/             # Sidebar, Header, PageLayout
│   │   ├── forms/              # Reusable form components
│   │   ├── data-display/       # Tables, Cards, Badges, Status indicators
│   │   └── feedback/           # Toast, Alert, Loading, Empty states
│   ├── features/               # Feature-based modules
│   │   ├── auth/               # Login, token management
│   │   ├── appointments/       # Calendar, Today, Booking, Detail
│   │   ├── patients/           # Directory, Profile, Form
│   │   ├── services/           # Services catalog
│   │   ├── schedules/          # Shifts, Time-off, Availability
│   │   └── staff/              # Staff management
│   ├── hooks/                  # Shared custom hooks
│   ├── lib/                    # Utilities, API client, constants
│   │   ├── api.ts              # Axios instance with interceptors
│   │   ├── auth.ts             # Auth store (Zustand), token handling
│   │   ├── utils.ts            # cn(), formatters, helpers
│   │   └── constants.ts        # Appointment statuses, roles, etc.
│   ├── types/                  # TypeScript types matching backend schemas
│   │   ├── api.ts              # Generated or manual API types
│   │   └── ui.ts               # UI-specific types
│   ├── styles/
│   │   └── globals.css         # Tailwind imports, CSS variables
│   ├── main.tsx                # Entry point
│   └── App.tsx                 # Root component
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── biome.json
├── tailwind.config.ts
├── postcss.config.js
└── playwright.config.ts
```

## 5. Key Configuration Files

### vite.config.ts
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import tanstackRouter from '@tanstack/router-plugin/vite'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    react(),
    tailwindcss(),
    tsconfigPaths(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

### biome.json
```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
  "organizeImports": { "enabled": true },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "correctness": { "noUnusedVariables": "error" },
      "style": { "noNonNullAssertion": "warn" }
    }
  },
  "formatter": { "enabled": true, "indentStyle": "space", "indentWidth": 2 }
}
```

### tailwind.config.ts
```typescript
import type { Config } from 'tailwindcss'
import { fontFamily } from 'tailwindcss/defaultTheme'

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', ...fontFamily.sans],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        // Semantic colors for appointment states
        appointment: {
          scheduled: 'hsl(var(--appointment-scheduled))',
          confirmed: 'hsl(var(--appointment-confirmed))',
          'checked-in': 'hsl(var(--appointment-checked-in))',
          'in-progress': 'hsl(var(--appointment-in-progress))',
          completed: 'hsl(var(--appointment-completed))',
          cancelled: 'hsl(var(--appointment-cancelled))',
          'no-show': 'hsl(var(--appointment-no-show))',
        },
      },
      borderRadius: { lg: 'var(--radius)', md: 'calc(var(--radius) - 2px)', sm: 'calc(var(--radius) - 4px)' },
    },
  },
  plugins: [],
} satisfies Config
```

## 6. Quality Gates
All commits must pass:
```bash
npm run lint        # biome check
npm run format      # biome format --check
npm run typecheck   # tsc --noEmit
npm run test        # vitest run
npm run test:e2e    # playwright test
```

## 7. API Client Setup (`src/lib/api.ts`)
- Axios instance with baseURL from `import.meta.env.VITE_API_BASE_URL`
- Request interceptor: attach Bearer token from auth store
- Response interceptor: handle 401 → redirect to login, 403 → show permission error
- Correlation ID header propagation

## 8. Auth Store (`src/lib/auth.ts`)
Zustand store with:
- `token`, `user`, `role`, `isAuthenticated`
- `login(credentials)`, `logout()`, `refreshToken()`
- Persist to localStorage (token only, not user object)
- Role-based permission helpers

## 9. Acceptance Criteria
- [ ] `npm run dev` starts dev server on port 5173
- [ ] `npm run build` produces production bundle
- [ ] `npm run lint`, `format`, `typecheck`, `test` all pass
- [ ] Backend proxy works: `/api/v1/health` returns 200
- [ ] shadcn/ui components render correctly
- [ ] TanStack Router file-based routing works
- [ ] TanStack Query DevTools available in development
- [ ] Zustand auth store persists token across refresh

## 10. Hand-off
Tell the user: frontend initialized → **clear context** → run `frontend-tech-spec` to create the frontend technical specification, then `frontend-tickets` to break down the UI work.