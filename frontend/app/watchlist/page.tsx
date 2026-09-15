'use client'

import { FormEvent, useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { accountError, applyAccount, AuthState, csrfHeaders, useAccount, Watchlist } from '@/lib/account'
import { MovieCard } from '@/components/shared/MovieCard'
import { Pagination } from '@/components/shared/Pagination'

export default function WatchlistPage() {
  const account = useAccount()
  if (account.isPending) return <main className="page-shell"><p role="status">Loading your account…</p></main>
  if (account.isError) return <main className="page-shell"><p role="alert">Your account could not be loaded.</p><button className="cta-button" onClick={() => account.refetch()}>Try again</button></main>
  return account.data ? <PrivateWatchlist key={account.data.user.id} auth={account.data} /> : <AccountForm />
}

function AccountForm() {
  const client = useQueryClient()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const mutation = useMutation({
    mutationFn: async () => (await api.post<AuthState>(`/api/auth/${mode}`, { username, password })).data,
    onSuccess: async auth => { await applyAccount(client, auth); setPassword('') },
  })
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); mutation.mutate() }
  return <main className="page-shell">
    <section className="panel account-panel">
      <span className="eyebrow">Your movie collection</span>
      <h1>{mode === 'login' ? 'Sign in to your watchlist' : 'Create your account'}</h1>
      <p className="subtle">Save films for later and keep track of what you’ve watched.</p>
      <form className="account-form" onSubmit={submit}>
        <label htmlFor="username">Username</label>
        <input id="username" className="search-input" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required minLength={3} maxLength={32} pattern="[A-Za-z0-9_]+" aria-describedby="username-help" />
        <small id="username-help">3–32 letters, numbers, or underscores. Usernames are not case-sensitive.</small>
        <label htmlFor="password">Password</label>
        <input id="password" className="search-input" type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} required minLength={12} maxLength={128} aria-describedby="password-help" />
        <small id="password-help">Use a unique password of at least 12 characters. After signing in, save a recovery code in Account security.</small>
        {mutation.isError ? <p role="alert">{accountError(mutation.error)}</p> : null}
        <button className="cta-button" disabled={mutation.isPending}>{mutation.isPending ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
      </form>
      <p><Link href="/account-security">Forgot your password? Use a recovery code</Link></p>
      <button className="cta-button secondary-button" style={{ marginTop: 16 }} disabled={mutation.isPending} onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); mutation.reset() }}>{mode === 'login' ? 'New here? Create an account' : 'Already registered? Sign in'}</button>
    </section>
  </main>
}

function PrivateWatchlist({ auth }: { auth: AuthState }) {
  const client = useQueryClient()
  const [page, setPage] = useState(1)
  const list = useQuery({ queryKey: ['watchlist', auth.user.id, page], queryFn: async () => (await api.get<Watchlist>('/api/watchlist', { params: { page } })).data })
  const edit = useMutation({
    mutationFn: async ({ id, status }: { id: number; status?: 'planned' | 'watched' }) => status
      ? api.patch(`/api/watchlist/${id}`, { status }, { headers: csrfHeaders(auth) })
      : api.delete(`/api/watchlist/${id}`, { headers: csrfHeaders(auth) }),
    onSuccess: async () => { await client.invalidateQueries({ queryKey: ['watchlist'] }); await client.invalidateQueries({ queryKey: ['saved-movie'] }) },
  })
  const logout = useMutation({ mutationFn: () => api.post('/api/auth/logout', {}, { headers: csrfHeaders(auth) }), onSuccess: () => applyAccount(client, null) })
  return <main className="page-shell">
    <section className="hero-panel">
      <span className="eyebrow">Private collection · {auth.user.username}</span>
      <h1>Your watchlist</h1>
      <p className="subtle">{list.data?.total || 0} saved movies. Only your account can access this list.</p>
      <div className="hero-actions"><Link href="/movies" className="cta-button">Find movies</Link><Link href="/account-security" className="cta-button secondary-button">Account security</Link><button className="cta-button secondary-button" disabled={logout.isPending} onClick={() => logout.mutate()}>Sign out</button></div>
    </section>
    {list.isPending ? <p role="status">Loading saved movies…</p> : null}
    {list.isError || edit.isError || logout.isError ? <p role="alert">{accountError(list.error || edit.error || logout.error)}</p> : null}
    {list.data?.items.length === 0 ? <p>No saved movies on this page. Open a movie and select “Save to watchlist”.</p> : null}
    <div className="section-grid">
      {list.data?.items.map(item => <section key={item.movie.id} className="saved-movie">
        <MovieCard movie={item.movie} />
        <div className="saved-movie-controls">
          <label htmlFor={`status-${item.movie.id}`}>Watch status</label>
          <select id={`status-${item.movie.id}`} value={item.status} disabled={edit.isPending} onChange={e => edit.mutate({ id: item.movie.id, status: e.target.value as 'planned' | 'watched' })}><option value="planned">Want to watch</option><option value="watched">Watched</option></select>
          <button className="cta-button secondary-button" disabled={edit.isPending} onClick={() => edit.mutate({ id: item.movie.id })}>Remove {item.movie.title}</button>
        </div>
      </section>)}
    </div>
    <Pagination page={page} totalPages={Math.max(page, list.data?.total_pages || 1)} onChange={setPage} />
  </main>
}
