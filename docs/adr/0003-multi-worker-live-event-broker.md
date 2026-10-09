# ADR 0003: Multi-worker live event broker

- **Status:** Accepted
- **Date:** 2026-10-09
- **Decision owner:** Product owner
- **Context:** T-011 must deliver appointment events to active SSE clients when the publishing request and SSE connection are handled by different Uvicorn worker processes. A module-level in-memory broadcaster cannot meet NFR-5 because its queues are process-local.
- **Decision:** Use Redis Pub/Sub as the shared, process-independent transport for appointment live events. Each application worker owns one Redis subscriber task and fans received messages into bounded local queues for its connected SSE clients. Each worker publishes committed appointment events to the shared channel. Configure the broker through `REDIS_URL`; production startup must not silently fall back to local-only delivery.
- **Delivery semantics:** Redis Pub/Sub is transient, at-most-once delivery; it is not a durable event log. During broker disconnection events may be missed. The listener must reconnect with bounded backoff, emit operational logs, and the UI must refetch authoritative appointment state after reconnect/resync. Durable replay and exactly-once delivery are out of scope for T-011.
- **Backpressure:** local subscriber queues are bounded. When a client falls behind, disconnect it or signal resync rather than allowing unbounded memory growth. Never silently pretend that a dropped event was delivered.
- **Transaction boundary:** appointment events are dispatched only after a successful database commit. A rolled-back mutation must not publish an event.
- **SSE resource lifecycle:** authentication's DB session closes before streaming begins; each worker's Redis resources are initialized/shut down in the FastAPI lifespan.
- **Alternatives considered:** (1) process-local queues — rejected because workers cannot communicate; (2) Redis Streams — stronger replay/durability but adds consumer-group and retention complexity not required by this ticket; (3) PostgreSQL LISTEN/NOTIFY — viable but would couple the real-time transport to the application database and consume dedicated DB connections.
- **Consequences:** Redis becomes a required production dependency for T-011; local unit tests use a fake broker and integration tests need Redis. Pub/Sub does not guarantee replay after a worker disconnects, so clients must recover by refetching state.
