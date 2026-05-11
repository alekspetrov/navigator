/**
 * ${COMPONENT_NAME} — ${DESCRIPTION}
 *
 * App Router page (Server Component by default).
 * See .agent/philosophy/NEXTJS-PATTERNS.md §B, §D, §H.
 */

import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '${COMPONENT_NAME}',
};

type PageProps = {
  // In Next.js 15+, params and searchParams are Promises — always await.
  params?: Promise<Record<string, string>>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ${COMPONENT_NAME}Page({ params, searchParams }: PageProps) {
  const resolvedParams = params ? await params : undefined;
  const resolvedSearch = searchParams ? await searchParams : undefined;

  // SSR by default in Next.js 15+ (fetch is uncached unless you opt in).
  // const res = await fetch('https://api.example.com/...', { cache: 'no-store' });
  // const data = await res.json();

  return (
    <main className="flex flex-col gap-4 p-4 sm:p-6 md:p-8">
      <h1 className="text-2xl font-semibold sm:text-3xl">${COMPONENT_NAME}</h1>
      <p className="text-sm text-neutral-600 sm:text-base">
        Server-rendered. Mobile-first Tailwind layout.
      </p>
    </main>
  );
}
