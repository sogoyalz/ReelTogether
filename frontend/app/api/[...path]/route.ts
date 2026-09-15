import { NextRequest, NextResponse } from 'next/server'
import { createHmac, randomUUID, timingSafeEqual } from 'node:crypto'

const BACKEND_BASE_URL =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://127.0.0.1:8000'

async function proxy(request: NextRequest, params: { path: string[] }) {
  const search = request.nextUrl.searchParams.toString()
  const path = params.path.join('/')
  const url = `${BACKEND_BASE_URL}/api/${path}${search ? `?${search}` : ''}`

  const identity = browserIdentity(request)
  const init: RequestInit = {
    method: request.method,
    headers: { ..._forwardHeaders(request), ...(identity ? { 'x-movie-client': identity } : {}) },
  }

  init.cache = 'no-store'
  init.signal = AbortSignal.timeout(30_000)

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.text()
  }

  try {
    const response = await fetch(url, init)
    const contentType = response.headers.get('content-type') || 'application/json'
    const body = await response.text()
    const outgoing = new NextResponse(body, {
      status: response.status,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'private, no-store',
      },
    })
    if (identity) outgoing.cookies.set('movie-client', identity, { httpOnly: true, sameSite: 'lax', secure: process.env.NODE_ENV === 'production', path: '/' })
    for (const cookie of response.headers.getSetCookie()) outgoing.headers.append('Set-Cookie', cookie)
    return outgoing
  } catch {
    return NextResponse.json(
      { detail: 'Backend API is unavailable' },
      { status: 502 },
    )
  }
}

function _forwardHeaders(request: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {}
  const contentType = request.headers.get('content-type')
  if (contentType) {
    headers['Content-Type'] = contentType
  }
  for (const key of ['accept', 'authorization', 'cookie', 'x-admin-key', 'x-request-id', 'origin', 'x-csrf-token']) {
    const value = request.headers.get(key)
    if (value) {
      headers[key] = value
    }
  }
  return headers
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params)
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params)
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params)
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params)
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params)
}


function browserIdentity(request: NextRequest): string | null {
  const secret = process.env.PROXY_SHARED_SECRET
  if (!secret) return null
  const sign = (value: string) => createHmac('sha256', secret).update(value).digest('hex')
  const existing = request.cookies.get('movie-client')?.value || ''
  const [id, signature] = existing.split('.')
  const expected = id ? sign(id) : ''
  if (id?.length === 36 && signature?.length === expected.length &&
      timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return existing
  const next = randomUUID()
  return `${next}.${sign(next)}`
}
