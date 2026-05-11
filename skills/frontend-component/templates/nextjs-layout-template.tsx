/**
 * ${COMPONENT_NAME} Layout — ${DESCRIPTION}
 *
 * App Router layout (Server Component).
 * See .agent/philosophy/NEXTJS-PATTERNS.md §A, §I.
 */

import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: { default: '${COMPONENT_NAME}', template: '%s · ${COMPONENT_NAME}' },
  description: '${DESCRIPTION}',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#0a0a0a',
};

type LayoutProps = {
  children: React.ReactNode;
};

export default function ${COMPONENT_NAME}Layout({ children }: LayoutProps) {
  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col">
      {children}
    </div>
  );
}
