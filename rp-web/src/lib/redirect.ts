import { NextResponse } from 'next/server';

/**
 * A 303 redirect with a relative Location. Absolute URLs built from the request
 * can switch the host (127.0.0.1 and localhost), and the session cookies would
 * then not be sent.
 */
export function seeOther(path: string): NextResponse {
  return new NextResponse(null, { status: 303, headers: { Location: path } });
}
