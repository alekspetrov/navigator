# Workshop Quickstart — Conference Companion App with Navigator

**Workshop:** Advanced Claude Code — Production Workflows, Subagents, and Autonomous Execution (JSNation, 2026-05-22)

You watched the live demo. This is the path to replicate it on your own machine. Target: working `next dev` skeleton in under 10 minutes.

---

## 0. Prerequisites

- Node.js 20+, pnpm or npm
- Claude Code installed (`claude` on your PATH)
- A terminal, an editor, and 10 free minutes

---

## 1. Install Navigator (one time)

```bash
claude plugin marketplace add petroaleks/jitd-marketplace
claude plugin install navigator@navigator-marketplace
```

Verify:

```bash
claude plugin list | grep navigator
# navigator
#   Version: 6.11.0
```

Auto-update is on by default — every new session, Navigator checks for updates and pulls the latest before you start working.

---

## 2. Start from an empty folder

```bash
mkdir conf-companion && cd conf-companion
pnpm create next-app@latest . \
  --typescript --tailwind --app --eslint \
  --src-dir=false --import-alias='@/*' --use-pnpm
```

This is the only command in the whole workshop that *isn't* Navigator-driven — Navigator deliberately doesn't reimplement `create-next-app`. The point is to use Next.js as the official tool wants it.

---

## 3. Bootstrap Navigator

Open Claude Code in the folder and ask:

```
Initialize Navigator in this project.
```

Navigator detects Next.js + Tailwind + TypeScript, writes `.agent/` (its documentation skeleton), drops a project-specific `CLAUDE.md`, and links `.agent/philosophy/NEXTJS-PATTERNS.md` — the patterns doc grounded in the official Next.js docs.

Then:

```
Start my Navigator session.
```

You'll see the Navigator splash, the token budget, and a prompt asking what you want to build. From here, every request goes through Navigator's workflow check.

---

## 4. Build the Conference Companion App (in 4 chunks)

The spec lives at `workshop/CONFERENCE-APP-SPEC.md`. The four stages from the workshop are still the structure:

### Research

Ask Claude:

```
Research how a mobile-first schedule view should be built in Next.js 16 App Router with Tailwind v4.
```

Claude pulls patterns from the official docs (via the `navigator-research` agent) and writes findings into the knowledge graph. You can re-use them across the next 9 tasks without re-fetching.

### Planning

```
Create a TASK-XX plan for the Conference Companion App. Spec is at workshop/CONFERENCE-APP-SPEC.md. Break it into 10 parallelisable tasks with acceptance criteria.
```

Navigator's `nav-task` skill writes `.agent/tasks/TASK-XX-conf-app.md`. Each subtask is one isolated piece of work — perfect for git-worktree parallel execution.

### Execution

For each subtask, you can either:

**A. Single-threaded (simpler):**
```
Create a Schedule page that lists talks for a mobile-first viewport.
```
The `frontend-component` skill picks `nextjs-page` automatically (it sees `next` in `package.json`), generates `app/schedule/page.tsx` using the templates shipped with Navigator, and writes a co-located `loading.tsx`.

**B. Multi-Claude parallel (the showcase):**
```
Install multi-Claude workflows.
Run multi-agent workflow for TASK-XX-conf-app.
```
Navigator spawns one git worktree per task, dispatches a fresh Claude in each, and merges back when each lands a green PR. See `RELEASE-NOTES-v4.3.0.md`.

Endpoints work the same way:
```
Add an endpoint to toggle favourites.
```
The `backend-endpoint` skill detects Next.js and writes `app/api/favourites/route.ts` with `GET`/`POST`, Zod validation, and `NextResponse`.

### Review & Ship

```
Simplify the changes I just made, then create a commit.
```

`nav-simplify` runs ROI-scored clarity passes on modified files. Tests, lint, types, build are part of the autonomous completion protocol — Navigator only commits when they're green.

Deploy:
```bash
pnpm dlx vercel deploy
```

Share the URL with the room. You're done.

---

## 5. What you have now

- A working Next.js 16 mobile-first app on Vercel
- A `.agent/` directory documenting every decision, every task, and every pattern used
- A knowledge graph that gets smarter every session
- Templates and skills that work for the next project too — Navigator isn't workshop-only scaffolding

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `claude plugin list` says < 6.11.0 | Run `nav-upgrade` or just start a new session — auto-update will pull it. |
| Generated page uses CSS modules instead of Tailwind | `package.json` is missing `"next"` in deps — verify the project was scaffolded with `create-next-app`. |
| `params` errors saying "must await" | You're on Next.js 15+. The skill templates already await; if you wrote one by hand, run `npx @next/codemod@canary next-async-request-api .`. |
| `middleware.ts` warnings | Next.js 16 renamed it to `proxy.ts`. Codemod: `npx @next/codemod@canary middleware-to-proxy .`. |

---

## Reference

- **Patterns doc**: `.agent/philosophy/NEXTJS-PATTERNS.md` (lives in your repo after `nav-init`)
- **Task plan**: `.agent/tasks/TASK-XX-conf-app.md`
- **Workshop spec**: `workshop/CONFERENCE-APP-SPEC.md`
- **Navigator docs**: `https://github.com/petroaleks/jitd-marketplace`

If something breaks during the workshop, ping me — every issue makes Navigator better for the next room.
