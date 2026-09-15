'use client'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { accountError, csrfHeaders, useAccount } from '@/lib/account'

export function WatchlistButton({ movieId }: { movieId: number }) {
  const account = useAccount()
  const client = useQueryClient()
  const saved = useQuery({
    queryKey: ['saved-movie', account.data?.user.id, movieId], enabled: Boolean(account.data),
    queryFn: async () => (await api.get<{ saved: boolean }>(`/api/watchlist/${movieId}`)).data,
  })
  const toggle = useMutation({
    mutationFn: () => {
      if (!account.data) throw new Error('Sign in first')
      return saved.data?.saved ? api.delete(`/api/watchlist/${movieId}`, { headers: csrfHeaders(account.data) }) : api.put(`/api/watchlist/${movieId}`, {}, { headers: csrfHeaders(account.data) })
    },
    onSuccess: async () => { await client.invalidateQueries({ queryKey: ['saved-movie'] }); await client.invalidateQueries({ queryKey: ['watchlist'] }) },
  })
  if (account.isPending) return null
  if (account.isError) return <p role="alert">Watchlist unavailable. <Link href="/watchlist">Try signing in again</Link></p>
  if (!account.data) return <Link className="cta-button" href="/watchlist">Sign in to save movies</Link>
  return <div style={{ marginTop: 18 }}>
    <button className="cta-button" disabled={saved.isPending || saved.isError || toggle.isPending} onClick={() => toggle.mutate()}>{toggle.isPending ? 'Saving…' : saved.data?.saved ? 'Remove from watchlist' : 'Save to watchlist'}</button>
    <span role="status" className="meta" style={{ marginLeft: 12 }}>{saved.data?.saved ? 'Saved to your private watchlist' : ''}</span>
    {toggle.isError || saved.isError ? <p role="alert">{accountError(toggle.error || saved.error)}</p> : null}
  </div>
}
