# TASK-22: Simple Console Logger - Implementation Plan

**Task ID**: TASK-22
**Created**: 2025-10-31
**Status**: Planning
**Priority**: Low

---

## 1. Feature Description

Simple TypeScript utility function for formatted console logging with timestamps and severity levels.

**Core functionality**:
- Single `log()` function with message and optional level parameter
- ISO 8601 timestamp formatting
- Three severity levels: info (default), warn, error
- Type-safe TypeScript implementation
- Console-only output (no file persistence)

**Output format**: `[timestamp] [LEVEL] message`

---

## 2. Implementation Steps

### Step 1: Create Logger Utility (src/utils/logger.ts)

**File**: `src/utils/logger.ts`

**Implementation**:
```typescript
// Type definitions
export type LogLevel = 'info' | 'warn' | 'error';

export interface LogOptions {
  level?: LogLevel;
}

// Main logging function
export function log(message: string, level: LogLevel = 'info'): void {
  const timestamp = new Date().toISOString();
  const levelUpper = level.toUpperCase();
  const formattedMessage = `[${timestamp}] [${levelUpper}] ${message}`;

  // Route to appropriate console method
  switch (level) {
    case 'error':
      console.error(formattedMessage);
      break;
    case 'warn':
      console.warn(formattedMessage);
      break;
    case 'info':
    default:
      console.log(formattedMessage);
      break;
  }
}
```

**Key decisions**:
- Use native `Date.toISOString()` for timestamp (no dependencies)
- Route to appropriate console method (error → console.error, etc.)
- Default to 'info' level when not specified
- Simple union type for level validation

---

### Step 2: Create Test Suite (src/utils/__tests__/logger.test.ts)

**File**: `src/utils/__tests__/logger.test.ts`

**Test coverage**:
1. Default behavior (info level)
2. Explicit info level
3. Warn level
4. Error level
5. Timestamp format validation
6. Message formatting

**Implementation**:
```typescript
import { log, LogLevel } from '../logger';

describe('logger', () => {
  let consoleLogSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('logs info level by default', () => {
    log('Test message');

    expect(consoleLogSpy).toHaveBeenCalledTimes(1);
    expect(consoleLogSpy).toHaveBeenCalledWith(
      expect.stringMatching(/^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] \[INFO\] Test message$/)
    );
  });

  it('logs info level explicitly', () => {
    log('Info message', 'info');

    expect(consoleLogSpy).toHaveBeenCalledTimes(1);
    expect(consoleLogSpy).toHaveBeenCalledWith(
      expect.stringMatching(/^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] \[INFO\] Info message$/)
    );
  });

  it('logs warn level', () => {
    log('Warning message', 'warn');

    expect(consoleWarnSpy).toHaveBeenCalledTimes(1);
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      expect.stringMatching(/^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] \[WARN\] Warning message$/)
    );
  });

  it('logs error level', () => {
    log('Error message', 'error');

    expect(consoleErrorSpy).toHaveBeenCalledTimes(1);
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringMatching(/^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\] \[ERROR\] Error message$/)
    );
  });

  it('formats timestamp in ISO 8601 format', () => {
    log('Timestamp test');

    const call = consoleLogSpy.mock.calls[0][0];
    const timestampMatch = call.match(/^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\]/);

    expect(timestampMatch).toBeTruthy();
    expect(() => new Date(timestampMatch[1])).not.toThrow();
  });

  it('formats message correctly', () => {
    log('Custom message', 'warn');

    expect(consoleWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining('[WARN] Custom message')
    );
  });
});
```

---

### Step 3: Verify TypeScript Configuration

**Check**: Ensure `tsconfig.json` includes `src/utils/` in compilation

**Action**:
- Verify `include` patterns cover `src/**/*`
- Confirm `strict` mode enabled for type safety
- No changes needed if standard TS config exists

---

### Step 4: Run Tests

**Command**:
```bash
npm test src/utils/__tests__/logger.test.ts
```

**Expected**: All 6 tests pass

---

## 3. Files to Modify

### New Files (2)

1. **src/utils/logger.ts** (~30 lines)
   - Export `LogLevel` type
   - Export `log()` function
   - Timestamp formatting
   - Console routing

2. **src/utils/__tests__/logger.test.ts** (~80 lines)
   - 6 test cases
   - Console spy setup/teardown
   - Regex matchers for timestamp validation

### Modified Files (0)

No existing files modified - isolated utility.

---

## 4. Expected Outcome

### Functionality
- ✅ `log(message)` outputs `[timestamp] [INFO] message` to console.log
- ✅ `log(message, 'warn')` outputs `[timestamp] [WARN] message` to console.warn
- ✅ `log(message, 'error')` outputs `[timestamp] [ERROR] message` to console.error
- ✅ Timestamp in ISO 8601 format (YYYY-MM-DDTHH:mm:ss.sssZ)
- ✅ TypeScript types prevent invalid log levels

### Testing
- ✅ 6 tests passing (100% coverage)
- ✅ Default behavior verified
- ✅ All log levels verified
- ✅ Timestamp format validated
- ✅ Message formatting verified

### Code Quality
- ✅ TypeScript strict mode compliant
- ✅ No external dependencies
- ✅ Simple, maintainable implementation
- ✅ Clear type definitions
- ✅ Proper console method routing

### Integration
- ✅ Importable from any project file: `import { log } from './utils/logger'`
- ✅ Ready for use in application code
- ✅ No configuration required

---

## 5. Non-Goals

- ❌ File logging (console only)
- ❌ Log rotation
- ❌ Remote logging
- ❌ Custom formatters
- ❌ Log levels beyond info/warn/error
- ❌ Performance optimization
- ❌ Browser compatibility (Node.js focused)

---

## 6. Technical Decisions

### Why ISO 8601 Timestamps?
- Standard format (2025-01-31T10:30:00.000Z)
- Sortable
- Timezone-aware (UTC)
- No dependencies (native `Date.toISOString()`)

### Why Union Type for LogLevel?
- Type safety at compile time
- IDE autocomplete
- Prevents typos
- Simple and clear

### Why Separate Console Methods?
- Native browser/Node.js styling (errors red, warnings yellow)
- Proper log level filtering in dev tools
- Better debugging experience

### Why No Advanced Features?
- Keep it simple (KISS principle)
- Task requirements specify "simple console logger"
- Advanced features can be added later if needed

---

## 7. Testing Strategy

### Unit Tests (6 cases)
1. **Default behavior**: Message without level → [INFO]
2. **Explicit info**: Message with 'info' → [INFO]
3. **Warn level**: Message with 'warn' → [WARN]
4. **Error level**: Message with 'error' → [ERROR]
5. **Timestamp format**: Regex validation of ISO 8601
6. **Message formatting**: Full output format verification

### Test Approach
- Mock console methods (avoid actual output during tests)
- Use regex matchers for timestamp flexibility
- Verify correct console method called
- Validate timestamp is valid Date

---

## 8. Risks & Mitigations

### Risk: src/utils/ directory doesn't exist
**Mitigation**: Create directory structure before writing files

### Risk: Jest not configured
**Mitigation**: Check package.json for jest config before running tests

### Risk: TypeScript config doesn't cover src/utils/
**Mitigation**: Verify tsconfig.json includes src/** pattern

---

## 9. Acceptance Criteria Validation

From TASK-22:

- ✅ **Function accepts message string and optional level**
  - Implementation: `log(message: string, level: LogLevel = 'info')`

- ✅ **Outputs formatted: `[timestamp] [LEVEL] message`**
  - Implementation: Template string with timestamp, level, message

- ✅ **Tests cover all log levels**
  - Tests: Default (info), explicit info, warn, error

- ✅ **TypeScript types properly defined**
  - Types: `LogLevel` union type, typed parameters

---

## 10. Post-Implementation Checklist

After completing implementation:

- [ ] All 6 tests passing
- [ ] No TypeScript compilation errors
- [ ] Code follows project formatting standards
- [ ] Logger works when imported in other files
- [ ] Manual verification with example from task description
- [ ] Ready for autonomous completion protocol (commit, archive, marker)

---

**Estimated Effort**: 30 minutes
**Complexity**: Low
**Dependencies**: None
