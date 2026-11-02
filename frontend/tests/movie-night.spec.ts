import { test, expect } from '@playwright/test'

test('two friends join, vote privately, reveal a winner and save only by choice',async({browser})=>{
  const host=await browser.newContext();const guest=await browser.newContext()
  try{
    const a=await host.newPage();const b=await guest.newPage()
    for(const [context,name] of [[host,'host'],[guest,'guest']] as const){
      const response=await context.request.post('http://127.0.0.1:3011/api/auth/register',{headers:{Origin:'http://127.0.0.1:3011'},data:{username:`night_${name}_${Date.now()}`,password:'movie-night-password-123'}})
      expect(response.status()).toBe(201)
    }
    await a.goto('/movie-night');await a.getByRole('button',{name:'Create room',exact:true}).click()
    const link=a.getByLabel('Invite link');await expect(link).toBeVisible();const invite=await link.inputValue()
    await b.goto(invite);await b.getByRole('button',{name:'Join movie night',exact:true}).click()
    await expect(b.getByRole('heading',{name:'Your taste for tonight'})).toBeVisible()
    await a.getByRole('checkbox',{name:'Science Fiction',exact:true}).check()
    await expect(a.getByText('You have unsaved preferences.')).toBeVisible()
    const start=a.getByRole('button',{name:'Start private voting'});await expect(start).toBeEnabled();await start.click()
    await expect(b.getByRole('heading',{name:'Your private ballot'})).toBeVisible()
    const roomId=new URL(a.url()).searchParams.get('room')
    const saved=await (await host.request.get(`http://127.0.0.1:3011/api/movie-nights/${roomId}`)).json()
    expect(saved.preferences.genres).toEqual(['Science Fiction'])
    await a.getByRole('button',{name:'Return to lobby and clear votes'}).click()
    await expect(a.getByRole('heading',{name:'Your taste for tonight'})).toBeVisible()
    await start.click()
    await expect(b.getByRole('heading',{name:'Your private ballot'})).toBeVisible()
    await expect(b.getByText('Round 2',{exact:true})).toBeVisible()
    for(const page of [a,b]){
      const groups=page.getByRole('group',{name:/Vote on/});await expect(groups).toHaveCount(8)
      for(let i=0;i<8;i++){const yes=groups.nth(i).getByRole('button',{name:'Yes',exact:true});await yes.click();await expect(yes).toHaveAttribute('aria-pressed','true')}
    }
    const reveal=a.getByRole('button',{name:'Reveal group matches'});await expect(reveal).toBeEnabled();await reveal.click()
    const choose=a.getByRole('button',{name:/^Choose /}).first();await expect(choose).toBeVisible();await choose.click()
    await expect(b.getByRole('heading',{name:'Tonight’s pick'})).toBeVisible({timeout:15000})
    const response=await guest.request.get('http://127.0.0.1:3011/api/watchlist');expect((await response.json()).total).toBe(0)
    await b.setViewportSize({width:390,height:844});expect(await b.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  }finally{await host.close();await guest.close()}
})

test('delayed room actions cannot publish another room’s invite or error', async ({ page }) => {
  const origin = 'http://127.0.0.1:3011'
  const registration = await page.request.post('/api/auth/register', {
    headers: { Origin: origin }, data: { username: `switch_${Date.now()}`, password: 'disposable-room-password-123' },
  })
  expect(registration.status()).toBe(201)
  const headers = { Origin: origin, 'X-CSRF-Token': (await registration.json()).csrf_token }
  for (const outcome of ['success', 'failure', 'previous error']) {
    const first = await page.request.post('/api/movie-nights', { headers, data: { title: `First audit room ${outcome}` } })
    const second = await page.request.post('/api/movie-nights', { headers, data: { title: `Second audit room ${outcome}` } })
    expect(first.status()).toBe(201)
    expect(second.status()).toBe(201)
    const roomA = await first.json()
    const roomB = await second.json()
    let release!: () => void
    const held = new Promise<void>(resolve => { release = resolve })
    let observed!: () => void
    const started = new Promise<void>(resolve => { observed = resolve })
    const path = `/api/movie-nights/${roomA.id}/invite`
    await page.route(`**${path}`, async route => {
      const response = await route.fetch()
      observed()
      await held
      if (outcome === 'success') await route.fulfill({ response })
      else await route.fulfill({ status: 503, json: { detail: 'Old room audit failure' } })
    })
    try {
      await page.goto(`/movie-night?room=${roomA.id}`)
      await page.getByRole('button', { name: 'Create new invite link', exact: true }).click()
      await started
      if (outcome === 'previous error') {
        const failed = page.waitForResponse(response => response.url().endsWith(path))
        release()
        await failed
        await expect(page.getByRole('alert').filter({ hasText: 'Old room audit failure' })).toBeVisible()
      }
      await page.getByRole('button', { name: '← All rooms', exact: true }).click()
      await page.getByRole('button', { name: new RegExp(`^Second audit room ${outcome}`) }).click()
      await expect(page.getByRole('heading', { name: `Second audit room ${outcome}`, exact: true })).toBeVisible()
      if (outcome !== 'previous error') {
        const completed = page.waitForResponse(response => response.url().endsWith(path))
        release()
        await completed
      }
      await page.waitForLoadState('networkidle')
      await expect(page.getByLabel('Invite link', { exact: true })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Create new invite link', exact: true })).toBeEnabled()
      await expect(page.getByRole('alert').filter({ hasText: 'Old room audit failure' })).toHaveCount(0)
      expect(new URL(page.url()).searchParams.get('room')).toBe(roomB.id)
      await page.getByRole('button', { name: 'Create new invite link', exact: true }).click()
      await expect(page.getByLabel('Invite link', { exact: true })).toBeVisible()
      const freshLink = new URL(await page.getByLabel('Invite link', { exact: true }).inputValue())
      const token = new URLSearchParams(freshLink.hash.slice(1)).get('invite')
      const joined = await page.request.post('/api/movie-nights/join', { headers, data: { token } })
      expect(joined.status()).toBe(200)
      expect((await joined.json()).id).toBe(roomB.id)
    } finally { release() }
  }
  // Leaving and returning creates a new workspace even when its URL is identical.
  for (const returnToLobby of [false, true]) {
    let releaseCreation!: () => void
    const creationHeld = new Promise<void>(resolve => { releaseCreation = resolve })
    let creationObserved!: () => void
    const creationStarted = new Promise<void>(resolve => { creationObserved = resolve })
    await page.route('**/api/movie-nights', async route => {
      if (route.request().method() !== 'POST') return route.continue()
      const response = await route.fetch()
      creationObserved()
      await creationHeld
      await route.fulfill({ response })
    })
    try {
      await page.goto('/movie-night')
      await page.getByRole('button', { name: 'Create room', exact: true }).click()
      await creationStarted
      await page.getByRole('link', { name: 'Library', exact: true }).first().click()
      await expect(page).toHaveURL(/\/movies$/)
      if (returnToLobby) {
        await page.getByRole('link', { name: 'Movie Night', exact: true }).first().click()
        await expect(page.getByRole('button', { name: 'Create room', exact: true })).toBeEnabled()
      }
      const completed = page.waitForResponse(response => response.url().endsWith('/api/movie-nights') && response.request().method() === 'POST')
      releaseCreation()
      await completed
      await page.waitForLoadState('networkidle')
      await expect(page).toHaveURL(returnToLobby ? /\/movie-night$/ : /\/movies$/)
      if (returnToLobby) await expect(page.getByRole('button', { name: 'Create room', exact: true })).toBeEnabled()
      else await expect(page.getByRole('heading', { name: 'Find your next favourite.', exact: true })).toBeVisible()
    } finally { releaseCreation(); await page.unroute('**/api/movie-nights') }
  }

})
