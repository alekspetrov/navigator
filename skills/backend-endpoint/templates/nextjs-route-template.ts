/**
 * ${RESOURCE_NAME} Route Handler — collection endpoint
 *
 * @route ${HTTP_METHOD} ${ROUTE_PATH}
 *
 * Place at app/api/${RESOURCE_NAME_PLURAL}/route.ts.
 * For a single-resource endpoint with [id], use nextjs-route-dynamic-template.ts.
 * See .agent/philosophy/NEXTJS-PATTERNS.md §E.
 */

import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

const ${RESOURCE_NAME}Schema = z.object({
  // TODO: define fields
  id: z.string(),
});

export async function GET(_req: NextRequest) {
  try {
    // TODO: list ${RESOURCE_NAME_PLURAL}
    const ${RESOURCE_NAME_PLURAL}: Array<z.infer<typeof ${RESOURCE_NAME}Schema>> = [];

    return NextResponse.json({ data: ${RESOURCE_NAME_PLURAL} });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const parsed = ${RESOURCE_NAME}Schema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Validation failed', details: parsed.error.flatten() },
        { status: 400 }
      );
    }

    // TODO: persist parsed.data
    return NextResponse.json({ data: parsed.data }, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
