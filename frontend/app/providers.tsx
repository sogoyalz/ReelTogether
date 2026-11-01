'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { api } from '@/lib/api'
import { ACCOUNT_EVENT, applyAccount } from '@/lib/account'

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
    const changed = (event: StorageEvent) => {
      if (event.key === ACCOUNT_EVENT) {
        void applyAccount(queryClient, null, false).then(() => queryClient.invalidateQueries({ queryKey: ['account'] }))
      }
    }
    window.addEventListener('storage', changed)
    const interceptor = api.interceptors.response.use(response => response, error => {
      if (isAxiosError(error) && error.response?.status === 401 && ['Sign in to use your watchlist', 'Account no longer exists'].includes(error.response?.data?.detail) && queryClient.getQueryData(['account'])) {
        void applyAccount(queryClient, null)
      }
      return Promise.reject(error)
    })
    return () => { window.removeEventListener('storage', changed); api.interceptors.response.eject(interceptor) }
  }, [queryClient])

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
