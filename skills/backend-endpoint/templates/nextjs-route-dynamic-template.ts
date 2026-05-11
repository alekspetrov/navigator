/**
 * ${RESOURCE_NAME} Route Handler — single resource endpoint (dynamic segment)
 *
 * @route ${HTTP_METHOD} ${ROUTE_PATH}
 *
 * Place at app/api/${RESOURCE_NAME_PLURAL}/[id]/route.ts.
 * For a collection endpoint without [id], use nextjs-route-template.ts.
 * See .agent/philosophy/NEXTJS-PATTERNS.md §E, §H.
 */

import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

const ${RESOURCE_NAME}UpdateSchema = z.object({
  // TODO: define updatable fields
  id: z.string(),
}).partial();

type RouteContext = {
  // params is a Promise in Next.js 15+ — always await.
  params: Promise<{ id: string }>;
};

export async function GET(_req: NextRequest, { params }: RouteContext) {
  try {
    const { id } = await params;
    // TODO: load ${RESOURCE_NAME_LOWER} by id
    const ${RESOURCE_NAME_LOWER} = { id };

    return NextResponse.json({ data: ${RESOURCE_NAME_LOWER} });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

export async function PATCH(req: NextRequest, { params }: RouteContext) {
  try {
    const { id } = await params;
    const body = await req.json();
    const parsed = ${RESOURCE_NAME}UpdateSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Validation failed', details: parsed.error.flatten() },
        { status: 400 }
      );
    }

    // TODO: persist update for ${RESOURCE_NAME_LOWER} `id`
    return NextResponse.json({ data: { id, ...parsed.data } });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

export async function DELETE(_req: NextRequest, { params }: RouteContext) {
  try {
    const { id } = await params;
    // TODO: delete ${RESOURCE_NAME_LOWER} by id
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
