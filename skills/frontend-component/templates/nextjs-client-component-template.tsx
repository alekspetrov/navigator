'use client';

/**
 * ${COMPONENT_NAME} — ${DESCRIPTION}
 *
 * Client Component. Use for state, effects, browser APIs, event handlers.
 * 'use client' MUST be the first line, above all imports.
 * See .agent/philosophy/NEXTJS-PATTERNS.md §B, §C.
 */

import { useState } from 'react';

${PROPS_INTERFACE_BLOCK}

export function ${COMPONENT_NAME}({ children, className, ...props }: ${PROPS_INTERFACE}) {
  const [active, setActive] = useState(false);

  return (
    <div
      className={`flex flex-col gap-2 rounded-lg border p-4 ${className ?? ''}`}
      {...props}
    >
      <button
        type="button"
        onClick={() => setActive((v) => !v)}
        className="self-start rounded-md bg-neutral-900 px-3 py-1.5 text-sm text-white sm:text-base"
      >
        {active ? 'Active' : 'Inactive'}
      </button>
      {children}
    </div>
  );
}
