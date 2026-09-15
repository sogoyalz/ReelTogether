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
    await expect(b.getByRole('heading',{name:'Tonight’s pick'})).toBeVisible()
    const response=await guest.request.get('http://127.0.0.1:3011/api/watchlist');expect((await response.json()).total).toBe(0)
    await b.setViewportSize({width:390,height:844});expect(await b.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  }finally{await host.close();await guest.close()}
})
