# Raven backend

## Live appointment events (T-011)

The live SSE endpoint is multi-worker capable and uses Redis Pub/Sub as the shared event transport.

Set `REDIS_URL` for the broker (default: `redis://localhost:6379/0`). Redis must be reachable when the application starts; startup fails rather than silently degrading to worker-local event delivery.

For local development, start Redis using your preferred local Redis installation or service, then set `REDIS_URL` in your environment or `.env`.

Events use the `raven:appointment-events:v1` channel. Redis Pub/Sub is transient and does not replay messages missed during disconnection. A slow SSE client receives an `appointment.resync_required` event and should refetch appointment state.

For the cross-worker integration test, start a test Redis instance and set `TEST_REDIS_URL`. The test uses two independent broadcaster instances to verify that an event published through one instance reaches a subscriber on the other.

After changing dependencies, run `uv lock` from the repository root or `uv lock --directory backend` as supported by your installed uv version, then commit the updated `backend/uv.lock`.
