# TASK-22: Simple Console Logger

**Status**: ✅ Complete
**Priority**: Low
**Assignee**: Claude

## Context

Create a simple TypeScript utility function that logs formatted messages to console with timestamp and level.

## Requirements

1. Create `src/utils/logger.ts` with a `log()` function
2. Function should accept message and optional level (info/warn/error)
3. Include ISO timestamp in output
4. Add basic tests in `src/utils/__tests__/logger.test.ts`
5. Keep it simple - just console output, no files

## Acceptance Criteria

- [ ] Function accepts message string and optional level
- [ ] Outputs formatted: `[timestamp] [LEVEL] message`
- [ ] Tests cover all log levels
- [ ] TypeScript types properly defined

## Example Usage

```typescript
import { log } from './utils/logger';

log('Application started'); // [2025-01-31T10:30:00.000Z] [INFO] Application started
log('Warning message', 'warn'); // [2025-01-31T10:30:00.000Z] [WARN] Warning message
log('Error occurred', 'error'); // [2025-01-31T10:30:00.000Z] [ERROR] Error occurred
```
