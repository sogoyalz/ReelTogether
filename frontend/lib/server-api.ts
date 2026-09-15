import 'server-only'

import type { DashboardResponse, MovieSummary } from '@/lib/api'

const BACKEND_BASE_URL =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://127.0.0.1:8000'

export interface HomePagePayload {
  trending: MovieSummary[]
  upcoming: MovieSummary[]
  released: MovieSummary[]
  dashboard: DashboardResponse
}

export async function getHomePagePayload(): Promise<HomePagePayload | null> {
  try {
    const response = await fetch(`${BACKEND_BASE_URL}/api/movies/home`, {
      next: { revalidate: 120 },
    })

    if (!response.ok) {
      return null
    }

    return response.json()
  } catch {
    return null
  }
}
