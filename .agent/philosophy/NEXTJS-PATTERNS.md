# Next.js App Router Patterns (2026 / v16)

Source: official docs at https://nextjs.org/docs (verified May 2026, Next.js 16.2).
One canonical pattern per topic. Use these in code generators and reviews.

> ⚠️ **Recent changes (15 → 16)**
> - `fetch()` is **no longer cached by default**. You must opt-in to caching.
> - `GET` Route Handlers default to **dynamic**, not static (changed in 15).
> - `params` and `searchParams` are now **Promises** — you must `await` them.
> - `middleware.ts` is **deprecated and renamed to `proxy.ts`** in v16. Codemod: `npx @next/codemod@canary middleware-to-proxy .`

---

## A. File structure

**Rule:** `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`, `route.ts` live inside `app/` segments. `proxy.ts` (formerly `middleware.ts`) lives at project root or `src/`.
**Why:** Folders define URL segments; reserved filenames give Next.js render hooks.

```
app/
├── layout.tsx            # root layout (required, includes <html><body>)
├── page.tsx              # /
├── loading.tsx           # Suspense fallback for /
├── error.tsx             # error boundary for /
├── not-found.tsx         # 404 UI
├── schedule/
│   ├── page.tsx          # /schedule
│   └── [id]/page.tsx     # /schedule/:id
└── api/
    └── favourites/route.ts  # GET/POST /api/favourites
proxy.ts                  # request proxy (was middleware.ts)
```

Source: https://nextjs.org/docs/app/getting-started/project-structure

---

## B. Server Components default

**Rule:** Layouts and pages are Server Components by default. Only opt into `'use client'` when you need state, effects, browser APIs, or event handlers.
**Why:** Less JS shipped, secrets stay server-side, data fetched close to the source.

```tsx
// app/speakers/page.tsx — Server Component, no directive needed
import { db } from '@/lib/db'

export default async function Page() {
  const speakers = await db.speaker.findMany()
  return <ul>{speakers.map(s => <li key={s.id}>{s.name}</li>)}</ul>
}
```

Source: https://nextjs.org/docs/app/getting-started/server-and-client-components

---

## C. Composition rule

**Rule:** `'use client'` goes at the **very top of the file, above all imports**. Server Components can import Client Components. Client Components cannot import Server Components — but they **can receive them as `children` / props**.
**Why:** `'use client'` marks a module-graph boundary; everything imported under it joins the client bundle.

```tsx
// app/components/favourite-modal.tsx
'use client'
import { useState } from 'react'

export function FavouriteModal({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return open ? <div className="modal">{children}</div> : null
}

// app/schedule/[id]/page.tsx — Server Component composes them
import { FavouriteModal } from '@/components/favourite-modal'
import { SpeakerCard } from '@/components/speaker-card' // Server Component

export default function Page() {
  return <FavouriteModal><SpeakerCard /></FavouriteModal>
}
```

Source: https://nextjs.org/docs/app/getting-started/server-and-client-components#interleaving-server-and-client-components

---

## D. Data fetching in Server Components

**Rule:** Make the component `async` and `await` `fetch()` or your ORM directly. **Default to SSR** — `fetch()` is uncached in Next.js 15+, so the page re-renders on every request unless you opt into caching. Use `{ cache: 'no-store' }` to be explicit, `{ next: { revalidate: N } }` for ISR, or `{ cache: 'force-cache' }` for static.
**Why:** No client waterfalls. Identical `fetch` calls in the tree are still memoized per-request. SSR-default keeps data correctness intuitive; caching is an explicit performance opt-in.

```tsx
// app/schedule/page.tsx — SSR by default
export default async function Page() {
  // Fresh on every request (explicit form of the v15+ default)
  const res = await fetch('https://api.conf.dev/talks', { cache: 'no-store' })
  const talks = await res.json()
  return <ul>{talks.map(t => <li key={t.id}>{t.title}</li>)}</ul>
}

// Opt into ISR only when the data tolerates staleness:
//   await fetch(url, { next: { revalidate: 60 } })  // re-render at most once per 60s
```

Source: https://nextjs.org/docs/app/getting-started/fetching-data — "fetch requests are not cached by default."

---

## E. Route Handlers

**Rule:** Place `route.ts` in `app/api/<resource>/` and export named async functions per HTTP method. Use `Response.json()` or `NextResponse`. Dynamic `params` is a Promise.
**Why:** REST-style endpoints for non-mutation needs (webhooks, third-party callers, non-form clients). GET defaults to **dynamic** in v15+.

```ts
// app/api/talks/[id]/route.ts
import { NextRequest } from 'next/server'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const talk = await getTalk(id)
  return Response.json(talk)
}
```

Source: https://nextjs.org/docs/app/api-reference/file-conventions/route

---

## F. Server Actions

**Rule:** For **mutations from the UI**, prefer Server Actions over Route Handlers. Put `'use server'` at the top of a file of action functions, or inline in an async function.
**Why:** Direct call from Server/Client Components, automatic CSRF, no client-side fetch wiring, integrates with `<form action={...}>` and `revalidatePath`.

```ts
// app/actions/favourites.ts
'use server'
import { revalidatePath } from 'next/cache'
import { auth } from '@/lib/auth'

export async function toggleFavourite(formData: FormData) {
  const session = await auth()
  if (!session?.user) throw new Error('Unauthorized')
  await db.favourite.toggle(session.user.id, formData.get('talkId') as string)
  revalidatePath('/schedule')
}

// app/schedule/[id]/page.tsx
import { toggleFavourite } from '@/actions/favourites'
export default function Page() {
  return <form action={toggleFavourite}><button>Star</button></form>
}
```

Source: https://nextjs.org/docs/app/api-reference/directives/use-server

---

## G. Loading & Error states

**Rule:** Co-locate `loading.tsx` and `error.tsx` in the same folder as `page.tsx`. `error.tsx` **must** be a Client Component.
**Why:** Next.js auto-wraps the segment in `<Suspense>` and a React error boundary.

```tsx
// app/schedule/loading.tsx — Server Component
export default function Loading() { return <div className="animate-pulse">Loading…</div> }

// app/schedule/error.tsx — must be Client Component
'use client'
export default function Error({ error, unstable_retry }: {
  error: Error; unstable_retry: () => void
}) {
  return <button onClick={unstable_retry}>Retry — {error.message}</button>
}
```

Source: https://nextjs.org/docs/app/api-reference/file-conventions/error

---

## H. Dynamic segments

**Rule:** `[id]` for single param, `[...slug]` for catch-all, `[[...slug]]` for optional. `params` is a `Promise` — always `await` it. Use `generateStaticParams` to prerender known values.
**Why:** Async params unifies static and runtime routing in v15+.

```tsx
// app/speakers/[id]/page.tsx
export async function generateStaticParams() {
  const speakers = await getSpeakers()
  return speakers.map(s => ({ id: s.id }))
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const speaker = await getSpeaker(id)
  return <h1>{speaker.name}</h1>
}
```

Source: https://nextjs.org/docs/app/api-reference/file-conventions/dynamic-routes

---

## I. Metadata

**Rule:** Export a static `metadata` object or async `generateMetadata` from `layout.tsx`/`page.tsx`. Only works in Server Components. Use a separate `viewport` export for viewport/theme-color.
**Why:** Next.js renders the `<head>` for you; supports streaming for dynamic routes.

```tsx
// app/layout.tsx
import type { Metadata, Viewport } from 'next'

export const metadata: Metadata = {
  title: { default: 'ConfApp', template: '%s · ConfApp' },
  description: 'Your conference companion',
  manifest: '/manifest.json',
}

export const viewport: Viewport = {
  width: 'device-width', initialScale: 1, themeColor: '#0a0a0a',
}
```

Source: https://nextjs.org/docs/app/getting-started/metadata-and-og-images

---

## J. Tailwind v4 setup

**Rule:** Install `tailwindcss` + `@tailwindcss/postcss`, register the PostCSS plugin, `@import 'tailwindcss'` in `app/globals.css`, import once in root `layout.tsx`. No `tailwind.config.js` needed for v4 default content scanning.
**Why:** v4 auto-detects content; PostCSS plugin replaces the v3 CLI/JIT.

```bash
pnpm add -D tailwindcss @tailwindcss/postcss
```

```js
// postcss.config.mjs
export default { plugins: { '@tailwindcss/postcss': {} } }
```

```css
/* app/globals.css */
@import 'tailwindcss';
```

```tsx
// app/layout.tsx
import './globals.css'
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>
}
```

Source: https://nextjs.org/docs/app/getting-started/css

---

## K. Mobile-first responsive

**Rule:** Write base classes for mobile, then layer `sm: md: lg:` for larger viewports. The viewport meta tag is injected automatically; set theme/scale via the `viewport` export (see I).
**Why:** Tailwind breakpoints are min-width — base = smallest, larger = progressive enhancement.

```tsx
<main className="flex flex-col gap-4 p-4 sm:p-6 md:grid md:grid-cols-2 lg:grid-cols-3">
  {talks.map(t => (
    <article key={t.id} className="rounded-lg border p-4 text-sm md:text-base">
      {t.title}
    </article>
  ))}
</main>
```

Sources: https://nextjs.org/docs/app/getting-started/metadata-and-og-images (auto viewport), https://tailwindcss.com/docs/responsive-design

---

## L. Image optimization

**Rule:** Use `next/image`. Provide `width`/`height` for known dimensions, or `fill` + a sized parent. Always set `sizes` for responsive images; use `priority` only for above-the-fold LCP.
**Why:** Next.js generates srcset, lazy-loads, and serves modern formats.

```tsx
import Image from 'next/image'

export function SpeakerAvatar({ src, name }: { src: string; name: string }) {
  return (
    <Image
      src={src}
      alt={name}
      width={200}
      height={200}
      sizes="(max-width: 640px) 50vw, (max-width: 1024px) 25vw, 200px"
      className="rounded-full"
    />
  )
}
```

Source: https://nextjs.org/docs/app/api-reference/components/image

---

## Quick answers (common confusions)

- **Server Actions vs Route Handlers?** Server Actions = mutations from your own UI (forms, buttons). Route Handlers = public HTTP endpoints (webhooks, third-party, non-form clients).
- **Where does `'use client'` go?** First line of the file, **above all imports**. Everything imported below it joins the client bundle.
- **Server importing Client?** ✅ Yes. **Client importing Server?** ❌ No — but you can pass Server Components as `children`/props.
- **`fetch()` default in v15+?** ⚠️ **Uncached** by default (changed from v14). Opt in with `{ next: { revalidate: N } }`, `{ cache: 'force-cache' }`, or `'use cache'`.
- **`middleware.ts`?** ⚠️ Deprecated in v16, renamed to `proxy.ts`. Same matcher API, same `NextRequest`/`NextResponse`.
