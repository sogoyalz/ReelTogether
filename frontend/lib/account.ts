import axios from 'axios'
import { QueryClient, useQuery } from '@tanstack/react-query'
import { api, type MovieSummary } from './api'

export type AuthState = { user: { id: number; username: string }; csrf_token: string }
export type SavedMovie = { movie: MovieSummary; status: 'planned' | 'watched'; added_at: string }
export type Watchlist = { items: SavedMovie[]; total: number; page: number; total_pages: number }

export function useAccount() {
  return useQuery<AuthState | null>({
    queryKey: ['account'],
    queryFn: async () => {
      try { return (await api.get<AuthState>('/api/auth/me')).data }
      catch (error) {
        if (axios.isAxiosError(error) && error.response?.status === 401) return null
        throw error
      }
    },
    retry: false,
    staleTime: 0,
  })
}

export const csrfHeaders = (auth: AuthState) => ({ 'X-CSRF-Token': auth.csrf_token })
export function accountError(error: unknown) {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') return error.response.data.detail
  return 'The request could not be completed. Check your details and try again.'
}


export async function applyAccount(client: QueryClient, auth: AuthState | null) {
  await client.cancelQueries()
  // Keep the account observer attached while clearing data from other users.
  client.removeQueries({ predicate: query => query.queryKey[0] !== 'account' })
  client.setQueryData(['account'], auth)
}
