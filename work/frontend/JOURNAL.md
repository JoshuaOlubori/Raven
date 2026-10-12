# Frontend Journal

## Setup — 2026-10-11

### Stack
- **Framework**: React 19 with Vite 6
- **Router**: TanStack Router (file-based routes)
- **State/Data**: TanStack Query v5, Zustand
- **UI**: shadcn/ui primitives (Radix UI), Tailwind CSS v4
- **Forms**: React Hook Form + Zod
- **API**: openapi-typescript generated types, custom fetch client
- **Mocking**: MSW v2 for development
- **Testing**: Vitest + React Testing Library, Playwright for E2E
- **Linting/Formatting**: Biome v2
- **Type Checking**: TypeScript 5.8 (project references)

### Design System (from Stitch exports)
- **Primary**: #086141 (Deep Sage Green)
- **Secondary**: #126d27 (Vivid Mint)
- **Tertiary**: #824500 (Amber)
- **Typography**: Plus Jakarta Sans (headings), Inter (body/data)
- **Spacing**: 8pt grid system
- **Border Radius**: 4px (sm) to 24px (xl), full for pills
- **Shadows**: 3 elevation levels with soft atmospheric shadows

### Project Structure
```
frontend/
├── src/
│   ├── app/                 # Providers, router setup
│   ├── routes/              # TanStack file-based routes
│   │   ├── __root.tsx       # Root layout with sidebar
│   │   ├── sign-in.tsx      # Public sign-in page
│   │   ├── today.tsx        # Today's operations dashboard
│   │   ├── patients.tsx     # Patient directory
│   │   ├── patients/
│   │   │   ├── $new.tsx     # Create patient
│   │   │   ├── $id.tsx      # Patient profile/history
│   │   │   └── $id.edit.tsx # Edit patient
│   │   ├── my-schedule.tsx  # Dentist workspace
│   │   ├── appointments.tsx # Appointments calendar
│   │   ├── appointments/
│   │   │   └── $id.tsx      # Appointment detail/audit
│   │   ├── services.tsx     # Dental services catalog
│   │   ├── provider-schedules.tsx # Provider schedules & time off
│   │   ├── staff.tsx        # Staff management
│   │   ├── __not-found.tsx
│   │   └── __error.tsx
│   ├── components/
│   │   ├── ui/              # shadcn primitives (to be generated)
│   │   └── shared/          # Layout, feedback components
│   ├── features/            # Domain modules (hooks, schemas, UI)
│   ├── lib/
│   │   ├── api-client.ts    # Fetch wrapper with auth
│   │   ├── query-client.ts  # TanStack Query config
│   │   ├── hooks.ts         # TanStack Query hooks
│   │   ├── auth-store.ts    # Zustand auth store
│   │   └── utils.ts         # cn() helper
│   ├── mocks/
│   │   ├── handlers.ts      # MSW handlers
│   │   └── browser.ts       # Worker registration
│   └── types/
│       └── api.d.ts         # Generated OpenAPI types (run `npm run generate:api`)
├── scripts/
│   └── generate-api-types.ts
├── biome.json
├── vite.config.ts
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
└── package.json
```

### Routes & Roles (from screens.md audit)

| Route | Roles | Description |
|-------|-------|-------------|
| `/sign-in` | public | Staff sign-in |
| `/today` | ADMIN, RECEPTIONIST | Today's operations dashboard |
| `/patients` | ADMIN, RECEPTIONIST, DENTIST (read) | Patient directory |
| `/patients/new` | ADMIN, RECEPTIONIST | Create patient |
| `/patients/:id` | ADMIN, RECEPTIONIST, DENTIST (read) | Patient profile & history |
| `/patients/:id/edit` | ADMIN, RECEPTIONIST | Edit patient |
| `/my-schedule` | DENTIST | Dentist workspace |
| `/appointments` | ADMIN, RECEPTIONIST, DENTIST (own) | Appointments calendar |
| `/appointments/:id` | ADMIN, RECEPTIONIST, DENTIST | Appointment detail & audit |
| `/services` | ADMIN (CRUD), RECEPTIONIST/DENTIST (read) | Services catalog |
| `/provider-schedules` | ADMIN (CRUD), RECEPTIONIST/DENTIST (read) | Provider schedules & time off |
| `/staff` | ADMIN only | Staff management |

### API Contract Source
- **OpenAPI**: `http://localhost:8000/openapi.json` (when backend running)
- **Fallback**: `work/specs/*.md` (approved backend specifications dated 2026-10-03)
- **Generation**: `npm run generate:api` → `src/types/api.d.ts`

### Key Contract Facts Verified
- Trailing slashes on `/patients/`, `/services/`, `/staff/` collections; no trailing slash on `/appointments`
- Authenticated SSE at `/api/v1/appointments/live` requires fetch-based client (EventSource can't set auth headers)
- No token refresh endpoint in current contract
- Appointment list has no pagination; supports dentist_id, patient_id, status, startDate, endDate filters
- Patient search is paginated, excludes inactive by default
- Staff list filters by role, active_only=true by default

### Quality Gates
```bash
npm run lint      # Biome lint
npm run format    # Biome format check
npm run typecheck # TypeScript build-mode check
npm run test      # Vitest + RTL
npm run test:e2e  # Playwright
npm run build     # Vite production build
npm run generate:api # Generate OpenAPI types
```

### Mock Mode
- Enabled via `VITE_MOCK_MODE=true` in `.env.local`
- MSW handlers in `src/mocks/handlers.ts` conform to OpenAPI types
- Mock data covers all screen audit requirements
- Worker registered in `src/mocks/browser.ts`

### Next Steps
1. Run `npm run generate:api` after starting backend to generate TypeScript types
2. Generate shadcn/ui primitives: `npx shadcn@latest add button input label card table dialog...`
3. Implement remaining UI components (forms, tables, modals, etc.)
4. Add E2E tests for critical flows
5. Run `frontend-tech-spec` skill to create detailed implementation specifications