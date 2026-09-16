import { test, expect } from '@playwright/test'

test('film remains usable when analytics fails and details are keyboard accessible', async ({ page }) => {
  const catalog = await (await page.request.get('/api/movies/browse?page_size=1')).json()
  const movie = catalog.items[0]
  await page.route('**/api/analytics/**', route => route.fulfill({ status: 503, json: { detail: 'Unavailable' } }))
  await page.goto(`/movies/${movie.slug}`)
  await expect(page.getByRole('heading', { name: movie.title, exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Sign in to save movies' })).toBeVisible()
  const details = page.locator('details.cinema-details')
  await expect(details).not.toHaveAttribute('open', '')
  await details.locator('summary').focus()
  await page.keyboard.press('Enter')
  await expect(details).toHaveAttribute('open', '')
})

test('mobile navigation opens, closes with Escape, and fits the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Your next great movie night.' })).toBeVisible()
  const toggle = page.getByRole('button', { name: 'Open navigation menu' })
  await toggle.click()
  await expect(page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Movie Night' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(toggle).toHaveAttribute('aria-expanded', 'false')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
})
