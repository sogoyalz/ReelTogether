import { test, expect } from '@playwright/test'
import { expectReadableText } from './contrast'

const origin = 'http://127.0.0.1:3011'
const password = 'implementation-test-password-123'
async function register(page: import('@playwright/test').Page, username: string) {
  const response = await page.request.post('/api/auth/register', { headers: { Origin: origin }, data: { username, password } })
  expect(response.status()).toBe(201)
  return (await response.json()).csrf_token as string
}

test('signing out clears another tab’s private watchlist immediately', async ({ page, context }) => {
  const csrf = await register(page, `tabs_${Date.now()}`)
  const catalog = await (await page.request.get('/api/movies/browse?page_size=1')).json()
  await page.request.put(`/api/watchlist/${catalog.items[0].id}`, { headers: { Origin: origin, 'X-CSRF-Token': csrf } })
  await page.goto('/watchlist')
  const other = await context.newPage()
  await other.goto('/watchlist')
  await expect(other.locator('.saved-movie')).toHaveCount(1)
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(other.getByRole('heading', { name: 'Sign in to your watchlist' })).toBeVisible()
  await expect(other.locator('.saved-movie')).toHaveCount(0)
})

test('movie-night invitation survives guest registration without exposing it in query parameters', async ({ page, browser }) => {
  const csrf = await register(page, `host_${Date.now()}`)
  const room = await (await page.request.post('/api/movie-nights', { headers: { Origin: origin, 'X-CSRF-Token': csrf }, data: { title: 'Continuation test' } })).json()
  const guest = await browser.newContext()
  try {
    const invitee = await guest.newPage()
    await invitee.goto(`${origin}/movie-night#invite=${encodeURIComponent(room.invite_token)}`)
    await invitee.getByRole('link', { name: 'Sign in to join' }).click()
    expect(new URL(invitee.url()).search).toBe('')
    await invitee.getByRole('button', { name: 'New here? Create an account' }).click()
    await invitee.getByLabel('Username', { exact: true }).fill(`guest_${Date.now()}`)
    await invitee.getByLabel('Password', { exact: true }).fill(password)
    await invitee.getByRole('button', { name: 'Create account', exact: true }).click()
    await expect(invitee.getByRole('heading', { name: 'You’re invited' })).toBeVisible()
    await invitee.getByRole('button', { name: 'Join movie night', exact: true }).click()
    await expect(invitee.getByRole('heading', { name: 'Continuation test', exact: true })).toBeVisible()
  } finally { await guest.close() }
})

test('account controls export data, change the password and delete only after confirmation', async ({ page }) => {
  const username = `controls_${Date.now()}`
  await register(page, username)
  await page.goto('/account-security')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download account data' }).click()
  expect((await download).suggestedFilename()).toBe('reeltogether-account.json')
  await page.locator('#manage-password').fill(password)
  await page.getByLabel('New password', { exact: true }).fill('replacement-private-password-123')
  await page.getByRole('button', { name: 'Change password', exact: true }).click()
  await expect(page.getByText('Password changed.', { exact: false })).toBeVisible()
  await page.locator('#manage-password').fill('replacement-private-password-123')
  await page.getByText('Delete account permanently', { exact: true }).click()
  await expect(page.getByRole('button', { name: 'Permanently delete my account' })).toBeDisabled()
  await page.getByLabel(`Type ${username} to confirm`).fill(username)
  await page.getByRole('button', { name: 'Permanently delete my account' }).click()
  await expect(page.getByRole('heading', { name: 'Reset your password', exact: true })).toBeVisible()
})

test('public responses carry security headers and chunked oversized JSON is rejected', async ({ request }) => {
  const response = await request.get('/movies')
  expect(response.headers()['x-content-type-options']).toBe('nosniff')
  expect(response.headers()['content-security-policy']).toContain("frame-ancestors 'none'")
  const oversized = await request.post('/api/assistant/chat', { data: { message: 'x'.repeat(70_000) } })
  expect(oversized.status()).toBe(413)
})

test('detail defers optional insights until they are opened', async ({ page }) => {
  let insights = 0
  page.on('request', request => { if (request.url().includes('/api/ai/movie/')) insights += 1 })
  await page.goto('/movies/fixture-0')
  await expect(page.getByRole('heading', { name: 'Fixture Movie 00', exact: true }).first()).toBeVisible()
  expect(insights).toBe(0)
  await page.locator('details.cinema-details > summary').click()
  await expect(page.getByText('Insufficient evidence', { exact: true })).toBeVisible()
  expect(insights).toBe(1)
})

test('account controls and source credits remain usable on mobile', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await register(page, `mobile_${Date.now()}`)
  await page.goto('/account-security')
  await expect(page.getByRole('heading', { name: 'Manage your account' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expectReadableText(page.locator('.account-form small').first())
  await page.screenshot({ path: testInfo.outputPath('account-security-mobile.png'), fullPage: true })
  await page.goto('/about')
  await expect(page.getByRole('heading', { name: 'Sources and credits' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('about-mobile.png'), fullPage: true })
})
