'use client'

import { FormEvent, useState } from 'react'
import Link from 'next/link'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { accountError, applyAccount, csrfHeaders, useAccount, type AuthState } from '@/lib/account'

export default function AccountSecurity() {
  const account = useAccount()
  if (account.isPending) return <main className="page-shell"><p role="status">Loading your account…</p></main>
  if (account.isError) return <main className="page-shell"><p role="alert">Could not load your account.</p><button className="cta-button" onClick={() => account.refetch()}>Try again</button></main>
  return <SecurityForm key={account.data?.user.id ?? 'guest'} auth={account.data ?? null} />
}

function SecurityForm({ auth }: { auth: AuthState | null }) {
  const client = useQueryClient()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [generated, setGenerated] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError(''); setGenerated('')
    try {
      if (auth) {
        const response = await api.post<{ recovery_code: string }>('/api/auth/recovery-code', { password }, { headers: csrfHeaders(auth) })
        setGenerated(response.data.recovery_code)
      } else {
        await api.post('/api/auth/recover', { username, password, recovery_code: code.trim() })
        await applyAccount(client, null)
        setDone(true); setCode('')
      }
      setPassword('')
    } catch (cause) { setError(accountError(cause)) }
    finally { setBusy(false) }
  }
  return <main className="page-shell"><section className="panel account-panel">
    <span className="eyebrow">Account security</span>
    <h1>{auth ? 'Save a recovery code' : 'Reset your password'}</h1>
    <p className="subtle">{auth ? 'Keep this code in your password manager. It can reset your password if you lose access. Generating a new code replaces your previous one.' : 'Enter the recovery code you saved earlier. A successful reset signs out every session and uses up the code.'}</p>
    {done ? <p role="status">Password reset. Sign in with your new password, then generate a new recovery code.</p> : <form className="account-form" onSubmit={submit}>
      {!auth && <><label htmlFor="recovery-user">Username</label><input className="search-input" id="recovery-user" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required minLength={3} maxLength={32} />
        <label htmlFor="recovery-code">Recovery code</label><input className="search-input" id="recovery-code" autoComplete="off" spellCheck={false} value={code} onChange={e => setCode(e.target.value)} required minLength={32} maxLength={128} /></>}
      <label htmlFor="recovery-password">{auth ? 'Current password' : 'New password'}</label><input className="search-input" id="recovery-password" type="password" autoComplete={auth ? 'current-password' : 'new-password'} value={password} onChange={e => setPassword(e.target.value)} required minLength={12} maxLength={128} />
      <small>Use a unique password of at least 12 characters.</small>
      <button className="cta-button" disabled={busy}>{busy ? 'Please wait…' : auth ? 'Generate recovery code' : 'Reset password'}</button>
    </form>}
    {error && <p role="alert">{error}</p>}
    {generated && <div role="status"><p>Save this code now. It is shown only here and will disappear when you leave.</p><code style={{ overflowWrap: 'anywhere', userSelect: 'all' }}>{generated}</code><p><button className="cta-button secondary-button" onClick={() => setGenerated('')}>I saved it — hide code</button></p></div>}
    {!auth && !done && <p>No saved code? This account cannot be recovered through this form.</p>}
    <p><Link href="/watchlist">{auth ? 'Back to watchlist' : 'Back to sign in'}</Link></p>
  </section></main>
}
