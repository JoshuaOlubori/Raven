# Backend question bank

Use as a map of branches, not a script. Ask only what the idea makes relevant, one question at a time, each with a recommended answer.

## 1. Problem and users
- What problem does this solve, and for whom? What happens today without it?
- Who are the actors (human roles, other services, schedulers)? What can each do and never do?
- What does success look like in 3 months, in measurable terms?
- Who consumes the API (own frontend, mobile, third parties, internal services)?

## 2. Domain model
- What are the core entities and how do they relate (1:1, 1:N, N:M)? Who owns each?
- What is each entity's lifecycle? Which states exist and which transitions are legal?
- Which business rules must always hold (invariants, caps, ordering of dates, uniqueness)?
- What is soft-deleted vs hard-deleted? Is history/audit required?
- Which terms are ambiguous? (→ glossary)

## 3. API behaviour
- Which operations exist per entity (create, read, list, update, transition, bulk, export)?
- Listing: filters, sorting, pagination style, expected page sizes?
- Idempotency: which writes can be retried safely? Need idempotency keys?
- Error expectations: validation messages, conflict handling, partial failure?
- Versioning and backwards-compatibility promises?

## 4. AuthN / AuthZ
- Identity source (OAuth2/OIDC provider, API keys, service tokens)? Token lifetime?
- Roles and permissions matrix: who can read, create, change, approve, delete what?
- Row-level rules (owner only, same tenant, same team, state-dependent)?
- Multi-tenancy: shared schema with tenant id, schema per tenant, or single-tenant?

## 5. Data
- Expected volumes now and in 12 months (rows, requests/sec, payload sizes)?
- Read/write ratio and hot paths? Consistency needs (can a read be stale)?
- Retention, archival, deletion rights, backups, restore objectives?
- Migrations: existing data to import? Zero-downtime requirement?
- Reporting/analytics needs that shape the schema?

## 6. Async, streaming, background work
- Any long-running or CPU-heavy operation? Must the caller wait?
- Does any client need live updates? Receive-only (SSE) or two-way (WebSocket)?
- Scheduled jobs, retries, dead-letter handling, ordering guarantees?
- Fan-out calls to other systems that should run concurrently?

## 7. Integrations
- External systems called or calling in (payments, email, identity, data warehouse)?
- Their failure modes: timeouts, rate limits, outages — what should degrade gracefully?
- Webhooks/events emitted or consumed? Contract owner?

## 8. Non-functional
- Latency targets (p95) and availability target?
- Scale model: multiple workers/instances? Any shared state that must be consistent?
- Observability: logs, metrics, traces, correlation ids, alert conditions?
- Rate limiting and abuse protection?

## 9. Security and compliance
- Data classification: PII/health/financial fields? Encryption needs?
- Applicable regulation (e.g. GDPR, NDPA, HIPAA, SOC2)? Lawful basis, consent, DSAR flows?
- Audit trail: which actions must be recorded, by whom, for how long?
- Secrets and configuration management expectations?

## 10. Delivery and scope
- Hard deadline or phase boundaries? What is the smallest slice that proves the idea?
- What is explicitly out of scope for v1?
- Deployment target and environments (local, staging, prod)? CI expectations?
- Who reviews and signs off?
