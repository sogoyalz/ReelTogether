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
    refetchOnWindowFocus: true,
  })
}

export const csrfHeaders = (auth: AuthState) => ({ 'X-CSRF-Token': auth.csrf_token })
export function accountError(error: unknown) {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') return error.response.data.detail
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    const labels: Record<string,string> = { username:'Username', password:'Password', recovery_code:'Recovery code', title:'Room name', genres:'Genres', favorites:'Favourite movies', round_id:'Voting round' }
    if (Array.isArray(detail)) {
      const messages = detail.slice(0,3).map(item => {
        const field = Array.isArray(item?.loc) ? labels[item.loc.at(-1)] : undefined
        if (!field) return ''
        if (item.type === 'string_too_short') return `${field} is too short.`
        if (item.type === 'string_too_long') return `${field} is too long.`
        if (item.type === 'string_pattern_mismatch') return `${field} contains unsupported characters.`
        if (item.type === 'missing') return `${field} is required.`
        return `${field} needs a valid value.`
      }).filter(Boolean)
      if (messages.length) return messages.join(' ')
    }
    if (!error.response) return 'Connection lost. Your unsaved choices are still here; reconnect and try again.'
  }
  return 'The request could not be completed. Check your details and try again.'
}


export const ACCOUNT_EVENT = 'reeltogether-account-change'

export async function applyAccount(client: QueryClient, auth: AuthState | null, broadcast = true) {
  await client.cancelQueries()
  // Keep the account observer attached while clearing data from other users.
  client.removeQueries({ predicate: query => query.queryKey[0] !== 'account' })
  client.setQueryData(['account'], auth)
  if (broadcast && typeof window !== 'undefined') {
    // Only a random invalidation marker crosses tabs; credentials stay in memory.
    try { window.localStorage.setItem(ACCOUNT_EVENT, crypto.randomUUID()) } catch { /* Storage may be disabled. Focus revalidation still works. */ }
  }
}
