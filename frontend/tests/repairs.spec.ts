import { test, expect } from '@playwright/test'

async function signIn(page: import('@playwright/test').Page) {
  const response=await page.request.post('/api/auth/register',{headers:{Origin:'http://127.0.0.1:3011'},data:{username:`repair_${Date.now()}`,password:'repair-test-password-123'}})
  expect(response.status()).toBe(201)
  return (await response.json()).csrf_token as string
}

test('deleting the only movie on the last watchlist page uses the canonical page',async({page})=>{
  const csrf=await signIn(page)
  const catalog=await (await page.request.get('/api/movies/browse?page_size=25')).json()
  for(const movie of catalog.items){
    const saved=await page.request.put(`/api/watchlist/${movie.id}`,{headers:{Origin:'http://127.0.0.1:3011','X-CSRF-Token':csrf}})
    expect(saved.status()).toBe(200)
  }
  await page.goto('/watchlist')
  await page.getByRole('button',{name:'Next',exact:true}).click()
  await expect(page.getByText('Page 2 of 2')).toBeVisible()
  await page.getByRole('button',{name:/^Remove /}).click()
  await expect(page.getByText('24 saved movies.',{exact:false})).toBeVisible()
  await expect(page.getByRole('navigation',{name:'Movie result pages'})).toHaveCount(0)
  await expect(page.locator('.saved-movie')).toHaveCount(24)
  await page.reload()
  await expect(page.locator('.saved-movie')).toHaveCount(24)
})

test('proxy forwards authentication retry hints and request identifiers',async({browser})=>{
  const context=await browser.newContext()
  try{
    let finalResponse
    for(let i=0;i<11;i++)finalResponse=await context.request.post('http://127.0.0.1:3011/api/auth/login',{headers:{Origin:'http://127.0.0.1:3011'},data:{username:'quota_missing_user',password:'not-a-real-password-123'}})
    expect(finalResponse!.status()).toBe(429)
    expect(Number(finalResponse!.headers()['retry-after'])).toBeGreaterThan(0)
    expect(finalResponse!.headers()['x-request-id']).toBeTruthy()
  }finally{await context.close()}
})


test('malformed identity cookies are replaced without crashing the proxy',async({request})=>{
  for(const signature of ['é'.repeat(64),'0'.repeat(64)+'.extra']){
    const response=await request.get('/api/auth/me',{headers:{Cookie:`movie-client=${encodeURIComponent('11111111-1111-1111-1111-111111111111.'+signature)}`}})
    expect(response.status()).toBe(401)
    expect(response.headers()['set-cookie']).toContain('movie-client=')
  }
})


test('concurrent catalog requests keep the fixture responsive',async({request})=>{
  for(let batch=0;batch<10;batch++){
    const responses=await Promise.all(Array.from({length:8},(_,i)=>request.get(i%2?'/api/movies/browse?genre=Drama&page_size=24':'/api/movies/browse?page_size=24')))
    for(const response of responses){expect(response.status()).toBe(200);expect((await response.json()).items.length).toBeGreaterThan(0)}
  }
  expect((await request.get('/api/auth/me')).status()).toBe(401)
})
