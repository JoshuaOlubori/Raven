# Review T-015 round 1 — changes requested

Gates: ruff ✓ · format ✓ · mypy ✓ · pytest ✓ (172 passed, 2 skipped)

## Spec — findings

- **Major — `backend/src/app/config.py:75`**. The ticket requires settings to reject a production secret "below the documented minimum strength" and accept a "sufficiently strong" secret (`work/tickets/T-015-fail-closed-jwt-secret.md:20-21`). Validation only checks `len(jwt_secret_key) >= 32`, so a trivially predictable value such as 32 repeated `A` characters passes. Character count is not a strength check. Define and enforce a configuration contract that rejects weak keys (or constrain deployment to securely generated keys with an enforceable format), and cover a weak-but-long secret in tests.

## Standards — findings

No additional findings. The validator is centralized in `Settings`, fails closed outside development, and avoids including the secret in its validation messages.

## Tests — findings

- The tests cover the default and a short secret, but do not cover a weak secret that meets the length threshold. The current `_STRONG_SECRET` fixture is a readable phrase, and its passing assertion does not demonstrate key strength. Add tests proving low-entropy/weak values are rejected and valid generated-format secrets are accepted.

## Summary

Counts: 0 blocker, 1 major, 0 minor, 0 nit. Worst issue: a predictable 32-character production key is accepted. Quality gates pass; two tests were skipped.

**Verdict: Changes requested**
