'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { api } from '@/lib/api'
import { ACCOUNT_EVENT, accountChangeChannel, applyAccount, type AuthState } from '@/lib/account'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
          },
        },
      })
  )

  useEffect(() => {
    let lastMarker: string | null = null
    const receive = (marker: unknown) => {
      if (typeof marker !== 'string' || marker === lastMarker) return
      lastMarker = marker
      void applyAccount(queryClient, null, false).then(() => queryClient.invalidateQueries({ queryKey: ['account'] }))
    }
    const changed = (event: StorageEvent) => { if (event.key === ACCOUNT_EVENT) receive(event.newValue) }
    const broadcastChanged = (event: MessageEvent) => receive(event.data)
    const channel = accountChangeChannel()
    channel?.addEventListener('message', broadcastChanged)
    window.addEventListener('storage', changed)
    // Match failures to the session that sent the request, never a later login.
    const requestSessions = new WeakMap<object, string | undefined>()
    const requestInterceptor = api.interceptors.request.use(config => {
      requestSessions.set(config, queryClient.getQueryData<AuthState | null>(['account'])?.csrf_token)
      return config
    })
    const interceptor = api.interceptors.response.use(response => response, error => {
      if (isAxiosError(error) && error.response?.status === 401 && ['Sign in to use your watchlist', 'Account no longer exists'].includes(error.response?.data?.detail) && error.config && requestSessions.get(error.config) && requestSessions.get(error.config) === queryClient.getQueryData<AuthState | null>(['account'])?.csrf_token) {
        void applyAccount(queryClient, null)
      }
      return Promise.reject(error)
    })
    return () => { window.removeEventListener('storage', changed); channel?.removeEventListener('message', broadcastChanged); api.interceptors.response.eject(interceptor); api.interceptors.request.eject(requestInterceptor) }
  }, [queryClient])

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
