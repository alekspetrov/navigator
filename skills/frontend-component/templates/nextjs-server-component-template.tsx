/**
 * ${COMPONENT_NAME} — ${DESCRIPTION}
 *
 * Server Component. Async, fetches data directly.
 * No 'use client' directive — runs only on the server.
 * See .agent/philosophy/NEXTJS-PATTERNS.md §B, §D.
 */

${PROPS_INTERFACE_BLOCK}

export async function ${COMPONENT_NAME}({ className, ...props }: ${PROPS_INTERFACE}) {
  // SSR by default — fetch is uncached in Next.js 15+, so this re-runs on every request.
  // Opt into other strategies only when you mean it:
  //   { next: { revalidate: 60 } }     // ISR — revalidate every 60s
  //   { cache: 'force-cache' }          // static — never revalidate
  const res = await fetch('https://api.example.com/items', { cache: 'no-store' });
  const items = (await res.json()) as Array<{ id: string; name: string }>;

  return (
    <ul className={`flex flex-col gap-2 ${className ?? ''}`} {...props}>
      {items.map((item) => (
        <li key={item.id} className="rounded-md border p-3 text-sm sm:text-base">
          {item.name}
        </li>
      ))}
    </ul>
  );
}
