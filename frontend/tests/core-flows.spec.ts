import { expect, test } from '@playwright/test'
import { formatReleaseDate } from '../lib/formatters'

test('release dates do not shift in Chicago', () => {
  expect(formatReleaseDate('2030-01-01')).toBe('Jan 1, 2030')
})

test('home to upcoming preserves query shapes and supports later pages', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await page.getByRole('link', { name: 'Upcoming', exact: true }).first().click()
  await expect(page.getByText('60 titles currently listed.')).toBeVisible()
  await page.getByRole('button', { name: 'Next', exact: true }).click()
  await expect(page.getByText('Page 2 of 2')).toBeVisible()
  expect(errors).toEqual([])
})

test('detail renders complete analysis with honest empty evidence', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/movies/fixture-0')
  await expect(page.getByRole('heading', { name: 'Fixture Movie 00', exact: true }).first()).toBeVisible()
  await page.locator('details.cinema-details > summary').click()
  await expect(page.getByText('No sourced critics discussion is stored for this title.').first()).toBeVisible()
  expect(errors).toEqual([])
})

test('director pages paginate and remain usable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/people/Jane%20Doe')
  await expect(page.getByText('60 matching movies in the current catalog.')).toBeVisible()
  await page.getByRole('button', { name: 'Next', exact: true }).click()
  await expect(page.getByText('Page 2 of 2')).toBeVisible()
})

test('proxy does not publicly cache maintenance errors', async ({ request }) => {
  const response = await request.post('/api/analytics/refresh')
  expect(response.status()).toBe(503)
  expect(response.headers()['cache-control']).toContain('no-store')
})

test('account watchlist survives reload, updates status, and signs out', async ({ page }) => {
  await page.goto('/watchlist')
  await page.getByRole('button', { name: 'New here? Create an account' }).click()
  await page.getByLabel('Username', { exact: true }).fill(`reader_${Date.now()}`)
  await page.getByLabel('Password', { exact: true }).fill('a-long-private-test-password')
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Your watchlist', exact: true })).toBeVisible()
  const session = (await page.context().cookies()).find(cookie => cookie.name === 'movie-session')
  expect(session?.httpOnly).toBe(true)
  expect(session?.sameSite).toBe('Strict')
  await page.goto('/movies/fixture-0')
  await page.getByRole('button', { name: 'Save to watchlist', exact: true }).click()
  await expect(page.getByText('Saved to your private watchlist')).toBeVisible()
  await page.goto('/watchlist')
  await page.getByLabel('Watch status').selectOption('watched')
  await expect(page.getByLabel('Watch status')).toHaveValue('watched')
  await page.reload()
  await expect(page.getByLabel('Watch status')).toHaveValue('watched')
  await page.getByRole('button', { name: 'Remove Fixture Movie 00', exact: true }).click()
  await expect(page.getByText('0 saved movies. Only your account can access this list.')).toBeVisible()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in to your watchlist' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Sign in to your watchlist' })).toBeVisible()
})
