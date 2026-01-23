# Pitfall: Auth Session Test Breakage

## Summary
Auth changes often break session tests due to token invalidation

## Context
Discovered during TASK-29 when updating auth flow

## Details
Auth changes often break session tests due to token invalidation

## Recommended Approach
Always run session tests after auth changes

## Related
- TASK-29
- TASK-12

---
**Captured**: 2026-01-23
**Confidence**: 90%
**Concepts**: authentication, testing
