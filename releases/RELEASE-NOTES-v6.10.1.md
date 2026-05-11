# Navigator v6.10.1 Release Notes

**Release Date**: 2026-05-11
**Type**: Patch (bug fixes — code generators, hook filename, stale test)

---

## Summary

Four bug fixes surfaced during a full workshop-prep audit of every Navigator flow. Two were silent demo killers in code generators (broken TypeScript output); one was a filename mismatch that would have caused token-monitoring hooks to silently fail in fresh installs; one was a stale unit-test assertion. No new features. No behavior changes for working flows.

If you've never used `frontend-component` or `backend-endpoint` to generate code, you wouldn't have noticed — but anyone doing live demos with these skills would.

---

## Fixes

### `skills/frontend-component/templates/component-simple-template.tsx` + `functions/component_generator.py`

**Before**: the template used `${PROPS_INTERFACE}` in two roles — once as the block where the interface definition belongs, once as the type reference in `React.FC<...>`. The generator substituted the *name* in both places, leaving a bare identifier as a free-floating statement and no interface body:

```tsx
import styles from './UserProfile.module.css';

UserProfileProps   // ← bare identifier, no interface, broken TS

export const UserProfile: React.FC<UserProfileProps> = ...
```

**After**: placeholder split into `${PROPS_INTERFACE_BLOCK}` (full body) and `${PROPS_INTERFACE}` (name only). Generator emits a minimal interface block by default:

```tsx
import styles from './UserProfile.module.css';

interface UserProfileProps {
  children?: React.ReactNode;
  className?: string;
}

export const UserProfile: React.FC<UserProfileProps> = ...
```

### `skills/backend-endpoint/templates/express-route-template.ts` + `functions/endpoint_generator.py`

**Before**: the template contained a JavaScript-style ternary inside a `${}` placeholder, expecting some evaluation layer to resolve it:

```ts
router.get(
  '/api/users/:id',
  ${MIDDLEWARE_CHAIN ? MIDDLEWARE_CHAIN + ',' : ''}   // ← never evaluated
  async (req, res, next) => { ... }
);
```

The Python generator does literal string substitution — the ternary leaked verbatim into every generated route.

**After**: generator pre-computes the middleware line and substitutes `${MIDDLEWARE_BLOCK}` as either `"  authMiddleware, validateUser,\n"` or an empty string. Output for both branches is now clean.

### `hooks/monitor-tokens.py` → `hooks/token_monitor.py`

**Before**: the hook file was named with hyphens (`monitor-tokens.py`) while every other hook in the project uses underscores (`workflow_enforcer.py`, `nav_session_start.py`, `nav_pre_compact.py`, `nav_post_compact.py`). The new in-tree settings template at `templates/claude-settings-hooks.json` already referenced the underscore form — so fresh installs would have configured Claude Code to call a file that didn't exist, and token monitoring would silently never run.

**After**: file renamed to match the template and the project convention. `.claude/settings.json` updated in lockstep.

### `skills/nav-loop/functions/test_exit_gate.py`

`exit_gate.py` defines `TOTAL_INDICATORS = 6`. The `test_empty_dict` test was still asserting `total == 5` — left over from when the indicator set was smaller. The assertion has been synced to 6. All 19 tests in the file now pass.

---

## Upgrade

```
nav-upgrade
```

Auto-update on session start will pick this up the next time you start a session.

---

## Verifying the fixes

After installing v6.10.1:

```bash
# Frontend component generator should emit a clean interface block:
python3 ~/.claude/plugins/cache/navigator-marketplace/navigator/6.10.1/skills/frontend-component/functions/component_generator.py \
  --name UserProfile --type simple \
  --props-interface UserProfileProps \
  --template ~/.claude/plugins/cache/navigator-marketplace/navigator/6.10.1/skills/frontend-component/templates/component-simple-template.tsx

# Backend endpoint generator should not leak template syntax:
python3 ~/.claude/plugins/cache/navigator-marketplace/navigator/6.10.1/skills/backend-endpoint/functions/endpoint_generator.py \
  --path /api/users/:id --method GET --resource user --framework express \
  --template ~/.claude/plugins/cache/navigator-marketplace/navigator/6.10.1/skills/backend-endpoint/templates/express-route-template.ts

# nav-loop tests all pass:
python3 ~/.claude/plugins/cache/navigator-marketplace/navigator/6.10.1/skills/nav-loop/functions/test_exit_gate.py
```
