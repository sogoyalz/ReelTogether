import { test, expect } from '@playwright/test'

const dialogName = 'What’s on your mind?'

test('editing a search cannot leave clickable results for the previous query', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: dialogName })
  const input = dialog.getByRole('textbox', { name: 'Search movies' })
  await input.fill('Fixture Movie 00')
  await expect(dialog.locator('.suggestion-row')).toHaveCount(1)
  await page.clock.install()
  await page.clock.pauseAt(new Date(Date.now() + 1000))
  await input.fill('Chat')
  await expect(dialog.locator('.suggestion-row')).toHaveCount(0)
  await input.fill('')
  await expect(dialog.locator('.search-suggestions')).toHaveCount(0)
})

test('clearing search preserves keyboard input focus', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: dialogName })
  const input = dialog.getByRole('textbox', { name: 'Search movies' })
  await input.fill('Fixture')
  await dialog.getByRole('button', { name: 'Clear search' }).click()
  await expect(input).toBeFocused()
  await page.keyboard.type('Chat')
  await expect(input).toHaveValue('Chat')
})

test('query-only Back and Forward dismiss an open search', async ({ page }) => {
  await page.goto('/search?q=Fixture')
  await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: dialogName })
  await dialog.getByRole('textbox', { name: 'Search movies' }).fill('Chat')
  await dialog.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page).toHaveURL(/q=Chat$/)
  await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
  await page.goBack()
  await expect(page).toHaveURL(/q=Fixture$/)
  await expect(dialog).toBeHidden()
  await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
  await page.goForward()
  await expect(page).toHaveURL(/q=Chat$/)
  await expect(dialog).toBeHidden()
})

test('dialog padding is inside the modal while the backdrop dismisses it', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: dialogName })
  await dialog.click({ position: { x: 2, y: 2 } })
  await expect(dialog).toBeVisible()
  await page.mouse.click(2, 2)
  await expect(dialog).toBeHidden()
})

test('encoded path separators cannot escape the API proxy namespace', async ({ request }) => {
  for (const path of ['..%2Fhealth', '..%5Chealth', 'movies%2F..%2F..%2Fhealth']) {
    const response = await request.get(`/api/${path}`)
    expect(response.status(), path).toBe(400)
    expect(response.headers()['cache-control']).toContain('no-store')
  }
  const valid = await request.get('/api/movies/browse?q=Fixture%20Movie%2000')
  expect(valid.status()).toBe(200)
  expect((await valid.json()).items[0].slug).toBe('fixture-0')
})

test('a delayed failure from a previous session cannot sign out a new account', async ({ page }) => {
  async function register(username: string) {
    await page.getByRole('button', { name: 'New here? Create an account' }).click()
    await page.getByLabel('Username', { exact: true }).fill(username)
    await page.getByLabel('Password', { exact: true }).fill('disposable-audit-password-123')
    await page.getByRole('button', { name: 'Create account', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Your watchlist', exact: true })).toBeVisible()
  }
  await page.goto('/watchlist')
  await register(`audit_a_${Date.now()}`)
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  let observed!: () => void
  const started = new Promise<void>(resolve => { observed = resolve })
  await page.route('**/api/watchlist/1', async route => {
    if (route.request().method() !== 'GET') return route.continue()
    observed()
    await held
    await route.fulfill({ status: 401, json: { detail: 'Sign in to use your watchlist' } })
  })
  await page.goto('/movies/fixture-0')
  await started
  await page.getByRole('link', { name: /^Watchlist/ }).first().click()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in to your watchlist' })).toBeVisible()
  const nextUser = `audit_b_${Date.now()}`
  await register(nextUser)
  const staleResponse = page.waitForResponse(response => response.url().endsWith('/api/watchlist/1') && response.status() === 401)
  release()
  await staleResponse
  await page.waitForLoadState('networkidle')
  await expect(page.getByRole('heading', { name: 'Your watchlist', exact: true })).toBeVisible()
  await expect(page.getByText(`Private collection · ${nextUser}`, { exact: true })).toBeVisible()
})

test('search recovers from failed requests and announces empty results', async ({ page }) => {
  let unavailable = true
  let failures = 0
  await page.route('**/api/movies/browse?**', async route => {
    if (new URL(route.request().url()).searchParams.get('q') === 'Fixture' && unavailable) {
      failures++
      return route.fulfill({ status: 503, json: { detail: 'Temporary audit outage' } })
    }
    return route.continue()
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: dialogName })
  const input = dialog.getByRole('textbox', { name: 'Search movies' })
  await input.fill('Fixture')
  await expect(dialog.getByRole('alert')).toContainText('Search is unavailable', { timeout: 15000 })
  expect(failures).toBeLessThanOrEqual(4)
  unavailable = false
  await dialog.getByRole('button', { name: 'Retry search' }).click()
  await expect(dialog.locator('.suggestion-row')).toHaveCount(6)
  await input.fill('zzzz_no_catalog_match')
  await expect(dialog.getByRole('status')).toContainText('No quick matches found.')
  await input.fill('   ')
  const before = page.url()
  await dialog.getByRole('button', { name: 'Search', exact: true }).click()
  expect(page.url()).toBe(before)
  await expect(dialog).toBeVisible()
})

test('search keeps page controls inert and remains usable across mobile and desktop resizing', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.setViewportSize({ width: 320, height: 800 })
  await page.goto('/')
  for (let attempt = 0; attempt < 3; attempt++) {
    await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: dialogName })
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Tab')
      // Native dialogs may tab through browser chrome (activeElement is BODY).
      // Focus must never move into an interactive control behind the modal.
      expect(await dialog.evaluate(element => element.matches(':modal') && (document.activeElement === document.body || element.contains(document.activeElement)))).toBe(true)
    }
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
    await expect(page.getByRole('button', { name: 'Open search — ⌘ K', exact: true })).toBeFocused()
  }
  await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
  await page.setViewportSize({ width: 1440, height: 1000 })
  const dialog = page.getByRole('dialog', { name: dialogName })
  await dialog.getByRole('textbox', { name: 'Search movies' }).fill('Fixture Movie 00')
  const result = dialog.locator('.suggestion-row').filter({ hasText: 'Fixture Movie 00' })
  const bounds = await result.boundingBox()
  expect(bounds).not.toBeNull()
  await page.mouse.dblclick(bounds!.x + bounds!.width / 2, bounds!.y + bounds!.height / 2)
  await expect(page).toHaveURL(/\/movies\/fixture-0$/)
  await expect(dialog).toBeHidden()
  expect(errors).toEqual([])
})

test('missing films are distinguished from a temporary catalog outage', async ({ page }) => {
  await page.goto('/movies/unknown-audit-title')
  await expect(page.getByRole('heading', { name: 'Movie not found', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Try again', exact: true })).toHaveCount(0)
})


test('recommendation actions keep their visible words in their accessible names', async ({ page }) => {
  await page.goto('/recommendations')
  for (const label of ['Make me laugh', 'Explore other worlds', 'A little romance', 'Skip the scares']) {
    await expect(page.getByRole('button', { name: label, exact: true })).toBeVisible()
  }
  await expect(page.getByRole('button', { name: 'Start over: start a new chat', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'ReelTogether THE GOOD FILM CLUB', exact: true })).toBeVisible()
  await expect(page.getByRole('group', { name: 'Explore movies from the catalog' })).toBeVisible()
  await page.goto('/')
  await expect(page.getByRole('region', { name: /Your people/ })).toHaveAccessibleName(/Your people/)
})

test('comparison sharing never claims an obsolete selection is copied', async ({ page }) => {
  for (const outcome of ['success', 'denied']) {
    await page.goto('/compare?ids=1,2')
    await page.evaluate(mode => {
      Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
        writeText: async () => { if (mode === 'denied') throw new Error('Clipboard denied by audit fixture') },
      } })
    }, outcome)
    await page.getByRole('button', { name: 'Share comparison', exact: true }).click()
    if (outcome === 'success') await expect(page.getByRole('button', { name: 'Link copied', exact: true })).toBeVisible()
    else await expect(page.getByLabel('Copy this comparison link')).toBeVisible()
    await page.locator('.compare-picker').getByRole('button', { name: 'Fixture Movie 02', exact: true }).click()
    await expect(page).toHaveURL(/ids=1%2C2%2C3$/)
    await expect(page.getByRole('button', { name: 'Share comparison', exact: true })).toBeVisible()
    await expect(page.getByLabel('Copy this comparison link')).toHaveCount(0)
    await page.getByRole('button', { name: 'Share comparison', exact: true }).click()
    if (outcome === 'denied') {
      const value = await page.getByLabel('Copy this comparison link').inputValue()
      expect(new URL(value).searchParams.get('ids')).toBe('1,2,3')
    }
  }
})

test('obsolete slow search requests are cancelled without duplicate replacement requests', async ({ page }) => {
  let observed!: () => void
  const started = new Promise<void>(resolve => { observed = resolve })
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  const requests: string[] = []
  page.on('request', request => {
    if (request.url().includes('/api/movies/browse?')) requests.push(new URL(request.url()).searchParams.get('q') || '')
  })
  await page.route('**/api/movies/browse?**', async route => {
    if (new URL(route.request().url()).searchParams.get('q') !== 'Fixture') return route.continue()
    const response = await route.fetch()
    observed()
    await held
    if (!route.request().failure()) await route.fulfill({ response })
  })
  try {
    await page.goto('/')
    await page.getByRole('button', { name: 'Open search — ⌘ K', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: dialogName })
    const input = dialog.getByRole('textbox', { name: 'Search movies' })
    await input.fill('Fixture')
    await started
    const cancelled = page.waitForEvent('requestfailed', request => new URL(request.url()).searchParams.get('q') === 'Fixture')
    await input.fill('Chat')
    await cancelled
    await expect(dialog.locator('.suggestion-row')).toHaveCount(6)
    expect(await dialog.locator('.suggestion-row').allTextContents()).toEqual(expect.arrayContaining([expect.stringContaining('Chat Movie')]))
    expect(requests.filter(q => q === 'Fixture')).toHaveLength(1)
    expect(requests.filter(q => q === 'Chat')).toHaveLength(1)
  } finally { release() }
})

test('long provider titles stay text and fit narrow cards', async ({ page }) => {
  const title = '<img src=x onerror="window.auditInjected=true">' + 'LongTitle'.repeat(40)
  await page.route('**/api/movies/browse?**', async route => {
    const response = await route.fetch()
    const data = await response.json()
    if (data.items.length) data.items[0].title = title
    await route.fulfill({ response, json: data })
  })
  await page.setViewportSize({ width: 320, height: 800 })
  await page.goto('/movies')
  await expect(page.locator('.movie-card h3').first()).toHaveText(title)
  await expect(page.locator('.movie-card h3 img')).toHaveCount(0)
  expect(await page.evaluate(() => 'auditInjected' in window)).toBe(false)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
