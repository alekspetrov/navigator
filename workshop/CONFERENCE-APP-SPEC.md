# Conference Companion App — Workshop Build Spec

**Workshop:** JSNation 2026-05-22 — Advanced Claude Code
**Build target:** Mobile-first conference app, deployed to Vercel by end of session

This is the spec the workshop builds against, live, using Navigator. The same spec is given to **Pilot** (autonomous agent) in a separate repo — at the end we open both side by side.

---

## What we're building

A mobile-first web app attendees open on their phones during the conference. Read-only schedule + speaker info, plus client-side favourites stored in `localStorage`. No accounts, no backend persistence (workshop scope) — but the Route Handlers exist for the moment we add a real DB.

---

## Stack (locked, not a decision point during the workshop)

| Layer | Choice | Why |
|---|---|---|
| Framework | Next.js 16 (App Router) | Server Components, Route Handlers, App Router conventions |
| Styling | Tailwind v4 | Mobile-first utility classes, no config |
| Language | TypeScript (strict) | Required by `create-next-app` template |
| Validation | Zod | Single source of truth for request and form schemas |
| Persistence | `localStorage` (favourites only) | No backend in workshop scope |
| Deploy | Vercel | Fastest path from `next dev` to public URL |
| Tooling | Navigator (this plugin) | The reason we're all here |

---

## Pages (App Router routes)

| Route | File | Type | Purpose |
|---|---|---|---|
| `/` | `app/page.tsx` | Server | Home — featured talks + nav to /schedule and /speakers |
| `/schedule` | `app/schedule/page.tsx` | Server | Full schedule, filterable client-side |
| `/schedule/[id]` | `app/schedule/[id]/page.tsx` | Server | Single talk detail + speaker + favourite button |
| `/speakers` | `app/speakers/page.tsx` | Server | All speakers grid |
| `/speakers/[id]` | `app/speakers/[id]/page.tsx` | Server | Speaker bio + their talks |
| `/favourites` | `app/favourites/page.tsx` | Client | The user's starred talks (reads `localStorage`) |
| `/search` | `app/search/page.tsx` | Server | Searchable list across talks + speakers |

Every route gets a co-located `loading.tsx`. Routes with fetch get an `error.tsx`.

---

## Components

| Component | File | Type | Notes |
|---|---|---|---|
| `TalkCard` | `app/components/talk-card.tsx` | Server | Title, time, room, speaker — no interactivity |
| `SpeakerCard` | `app/components/speaker-card.tsx` | Server | Photo (`next/image`), name, role |
| `FavouriteButton` | `app/components/favourite-button.tsx` | Client | `'use client'`, reads/writes `localStorage` |
| `ScheduleFilters` | `app/components/schedule-filters.tsx` | Client | Track/day filters, URL searchParams sync |
| `SearchBar` | `app/components/search-bar.tsx` | Client | Debounced input → updates URL |
| `RootLayout` | `app/layout.tsx` | Server | Metadata, viewport, Tailwind globals import |

---

## API Routes (placeholder, no DB)

| Path | Method | Purpose | Status in workshop |
|---|---|---|---|
| `/api/talks` | GET | List talks | Returns mocked JSON from file |
| `/api/talks/[id]` | GET | Single talk | Mocked |
| `/api/speakers` | GET | List speakers | Mocked |
| `/api/favourites` | GET, POST | Read/toggle favourite | Stub — TODO: persist when DB added |

These exist so the demo shows **Route Handler generation** even though favourites live in `localStorage` for the workshop.

---

## Server Action

| Action | File | Purpose |
|---|---|---|
| `submitFeedback` | `app/actions/feedback.ts` | `'use server'`, accepts FormData, validates with Zod, currently logs to console. Demonstrates Server Actions vs. Route Handlers. |

---

## Mobile-first constraints

- Base styles target **375px width** (iPhone SE / 13 mini)
- Tailwind responsive at `sm: 640px`, `md: 768px`, `lg: 1024px`
- Tap targets ≥ 44×44 px (accessibility)
- All long lists virtualise-friendly but **no actual virtualisation library** for workshop scope (keep dep tree thin)
- Test on real phone (Vercel preview URL, scan QR) before claiming "done"

---

## Data shape

```ts
// app/lib/types.ts
export type Talk = {
  id: string;
  title: string;
  abstract: string;
  speakerId: string;
  startsAt: string;   // ISO
  endsAt: string;     // ISO
  room: string;
  track: 'frontend' | 'backend' | 'ai' | 'platform';
};

export type Speaker = {
  id: string;
  name: string;
  role: string;
  bio: string;
  avatarUrl: string;
  social: { twitter?: string; github?: string };
};
```

Seed data: `app/lib/data/talks.json`, `app/lib/data/speakers.json` (≈20 talks, ≈15 speakers). Generated once at the start of the workshop, committed.

---

## Acceptance criteria (for the demo to "ship")

- [ ] `pnpm dev` runs without errors at `http://localhost:3000`
- [ ] All 7 routes render
- [ ] Favouriting a talk persists across reload (`localStorage`)
- [ ] Schedule filter narrows by track and day
- [ ] Search finds talks by title and speakers by name
- [ ] Lighthouse mobile score ≥ 90 (Performance, Accessibility)
- [ ] Deployed to Vercel, URL shared in chat
- [ ] All commits follow `type(scope): description` convention
- [ ] No commit mentions Claude Code or Navigator (per repo CLAUDE.md)

---

## Out of scope (don't demo these)

- Auth / accounts
- Backend persistence
- Real-time updates / websockets
- Internationalisation
- Offline / PWA install banner (nice-to-have if there's time, otherwise skip)
- Analytics

---

## The parallel build (Pilot autonomous)

Pilot gets this exact spec at workshop start, builds in a separate repo, no human in the loop. At the end we diff:
- Time-to-deploy
- PR count and shape
- Lighthouse scores
- Bugs caught in review

Outcome doesn't matter for the workshop's *core* lesson (preparation > execution). The comparison is the bonus: human+Claude vs. fully autonomous, same spec.
