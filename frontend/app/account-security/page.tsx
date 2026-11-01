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
  </section>{auth && <AccountControls auth={auth} />}</main>
}

function AccountControls({ auth }: { auth: AuthState }) {
  const client = useQueryClient()
  const [password, setPassword] = useState('')
  const [nextPassword, setNextPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  async function perform(action: 'password' | 'revoke-other-sessions' | 'delete-account') {
    if (busy) return
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await api.post(`/api/auth/${action}`, { password, ...(action === 'password' ? { new_password: nextPassword } : {}) }, { headers: csrfHeaders(auth) })
      setPassword(''); setNextPassword(''); setConfirmation('')
      if (action === 'password') {
        await applyAccount(client, result.data as AuthState)
        setNotice('Password changed. Other sessions were signed out. Generate a new recovery code above.')
      } else if (action === 'delete-account') await applyAccount(client, null)
      else setNotice(`${result.data.revoked} other sessions signed out.`)
    } catch (cause) { setError(accountError(cause)) }
    finally { setBusy(false) }
  }
  async function download() {
    if (busy) return
    setBusy(true); setError('')
    try {
      const response = await api.get('/api/auth/export', { responseType: 'blob' })
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a'); link.href = url; link.download = 'reeltogether-account.json'; link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setNotice('Your account export has downloaded. Keep it private.')
    } catch (cause) { setError(accountError(cause)) }
    finally { setBusy(false) }
  }
  return <section className="panel account-panel" style={{ marginTop: 24 }}>
    <h2>Manage your account</h2>
    <p>Download your watchlist, preferences and your own movie-night activity.</p>
    <button className="cta-button secondary-button" disabled={busy} onClick={() => void download()}>Download account data</button>
    <form className="account-form" style={{ marginTop: 24 }} onSubmit={event => { event.preventDefault(); void perform('password') }}>
      <label htmlFor="manage-password">Password for account changes</label>
      <input id="manage-password" className="search-input" type="password" autoComplete="current-password" required minLength={12} maxLength={128} value={password} onChange={event => setPassword(event.target.value)} />
      <label htmlFor="new-password">New password</label>
      <input id="new-password" className="search-input" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={nextPassword} onChange={event => setNextPassword(event.target.value)} />
      <button className="cta-button" disabled={busy}>Change password</button>
    </form>
    <p>Enter your current password above to sign out other browsers or delete your account.</p>
    <button className="cta-button secondary-button" disabled={busy || password.length < 12} onClick={() => void perform('revoke-other-sessions')}>Sign out other sessions</button>
    <details style={{ marginTop: 24 }}><summary>Delete account permanently</summary>
      <p>This deletes your watchlist, preferences, sessions and movie nights you host, including other members’ activity in those rooms. This cannot be undone. Download your data first.</p>
      <form className="account-form" onSubmit={event => { event.preventDefault(); if (confirmation === auth.user.username) void perform('delete-account') }}>
        <label htmlFor="delete-confirmation">Type {auth.user.username} to confirm</label>
        <input id="delete-confirmation" className="search-input" autoComplete="off" required value={confirmation} onChange={event => setConfirmation(event.target.value)} />
        <button className="cta-button secondary-button" disabled={busy || password.length < 12 || confirmation !== auth.user.username}>Permanently delete my account</button>
      </form>
    </details>
    {busy && <p role="status">Updating your account…</p>}
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
  </section>
}
