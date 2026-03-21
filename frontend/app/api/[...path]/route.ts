import { NextRequest, NextResponse } from 'next/server'

const BACKEND_BASE_URL =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://127.0.0.1:8000'

async function proxy(request: NextRequest, params: { path: string[] }) {
  const search = request.nextUrl.searchParams.toString()
  const path = params.path.join('/')
  const url = `${BACKEND_BASE_URL}/api/${path}${search ? `?${search}` : ''}`

  const init: RequestInit = {
    method: request.method,
    headers: {
      'Content-Type': request.headers.get('content-type') || 'application/json',
    },
    cache: 'no-store',
  }

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.text()
  }

  try {
    const response = await fetch(url, init)
    const contentType = response.headers.get('content-type') || 'application/json'
    const body = await response.text()
    return new NextResponse(body, {
      status: response.status,
      headers: {
        'Content-Type': contentType,
      },
    })
  } catch {
    return NextResponse.json(
      { detail: 'Backend API is unavailable' },
      { status: 502 },
    )
  }
}

export async function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params)
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params)
}

export async function PUT(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params)
}

export async function PATCH(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params)
}

export async function DELETE(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params)
}
