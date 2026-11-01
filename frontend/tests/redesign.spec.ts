import { test, expect } from '@playwright/test'
import { expectReadableText } from './contrast'

test('search is a keyboard-accessible modal and restores focus on Escape', async ({ page }) => {
  await page.goto('/')
  const trigger=page.getByRole('button',{name:'Open search',exact:true})
  await trigger.click()
  const dialog=page.getByRole('dialog',{name:'What’s on your mind?'})
  await expect(dialog).toBeVisible()
  const input=dialog.getByRole('textbox',{name:'Search movies'})
  await expect(input).toBeFocused()
  await input.fill('Fixture')
  await dialog.getByRole('button',{name:'Clear search'}).click()
  await expect(input).toHaveValue('')
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(trigger).toBeFocused()
  await page.keyboard.press('Control+k')
  await expect(dialog).toBeVisible()
  await input.fill('Fixture')
  await dialog.getByRole('button',{name:'Search',exact:true}).click()
  await expect(page).toHaveURL(/\/search\?q=Fixture/)
  await expect(dialog).toBeHidden()
})

test('spotlight controls switch real catalog links without autoplay', async ({ page }) => {
  await page.goto('/')
  const caption=page.locator('.caption-film')
  await expect(caption).toBeVisible()
  const first=await caption.getAttribute('href')
  await page.getByRole('button',{name:'Next featured film'}).click()
  await expect(caption).not.toHaveAttribute('href',first!)
  await page.getByRole('button',{name:'Previous featured film'}).click()
  await expect(caption).toHaveAttribute('href',first!)
  await expectReadableText(page.getByRole('link',{name:'Find your next film',exact:true}))
})

test('mobile filters preserve working API filters and fit a narrow screen', async ({ page }) => {
  await page.setViewportSize({width:360,height:800})
  await page.goto('/movies')
  const genre=page.getByRole('combobox',{name:'Genre',exact:true})
  await expect(genre).toBeHidden()
  await page.getByRole('button',{name:'Refine your search'}).click()
  await genre.selectOption('Science Fiction')
  await expect(page.locator('.movie-card h3').first()).toContainText('Chat Movie')
  await expect(page.locator('.movie-card')).toHaveCount(10)
  await page.getByRole('button',{name:'Hide filters'}).click()
  await expect(genre).toBeHidden()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
})

test('reduced motion leaves all editorial content readable', async ({ page }) => {
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.goto('/')
  await expect(page.getByRole('heading',{name:'Great stories. Better together.'})).toBeVisible()
  expect(await page.locator('.reveal[data-pending]').count()).toBe(0)
  expect(await page.locator('.cinema-hero-art').evaluate(element=>getComputedStyle(element).animationName)).toBe('none')
})


test('closed detail defers every optional analysis request', async ({ page }) => {
  const requests:string[]=[]
  page.on('request',request=>{if (/\/api\/(analytics|ai)\//.test(request.url())) requests.push(request.url())})
  await page.goto('/movies/fixture-0')
  await expect(page.getByRole('heading',{name:'Fixture Movie 00',exact:true})).toBeVisible()
  expect(requests).toHaveLength(0)
  await page.locator('details.cinema-details > summary').click()
  await expect(page.getByText('No sourced critics discussion is stored for this title.').first()).toBeVisible()
  expect(requests.some(url=>url.includes('/api/analytics/movie/'))).toBe(true)
  expect(requests.some(url=>url.includes('/api/ai/movie/'))).toBe(true)
})


test('recommendation artwork keeps poster proportions at desktop and mobile widths', async ({ page }) => {
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/recommendations')
    const artwork = page.locator('.match-hero-poster .film-artwork').first()
    await expect(artwork).toBeVisible()
    const size = await artwork.evaluate(element => ({ width: (element as HTMLElement).offsetWidth, height: (element as HTMLElement).offsetHeight }))
    expect(size.height / size.width).toBeCloseTo(1.5, 1)
  }
})
