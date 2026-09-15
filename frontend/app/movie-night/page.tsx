'use client'
import { useState, useSyncExternalStore } from 'react'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Users, Copy, Check, Minus, Ban } from 'lucide-react'
import { api, movieApi } from '@/lib/api'
import { useAccount, csrfHeaders, accountError, type AuthState } from '@/lib/account'
import { MovieArtwork } from '@/components/shared/MovieArtwork'
import { WatchlistButton } from '@/components/movies/WatchlistButton'

type Film = { id:number; slug:string; title:string; poster_url:string|null; year:number; genres:string[] }
type Result = { movie_id:number; yes:number; vetoes:number; eligible:boolean; top_match:boolean; reason:string }
type Room = { id:string; title:string; state:string; is_host:boolean; expired:boolean; expires_at:string; winner_id:number|null; members:{username:string;is_host:boolean;complete:boolean}[]; preferences:{genres:string[];favorites:number[]}; favorite_movies:{id:number;title:string}[]; movies:Film[]; my_votes:Record<string,string>; results:Result[] }
const genres=['Action','Adventure','Animation','Comedy','Crime','Documentary','Drama','Family','Fantasy','History','Horror','Music','Mystery','Romance','Science Fiction','Thriller','War','Western']

function subscribeUrl(callback:()=>void){window.addEventListener('popstate',callback);window.addEventListener('hashchange',callback);return()=>{window.removeEventListener('popstate',callback);window.removeEventListener('hashchange',callback)}}

export default function MovieNightPage(){
  const account=useAccount()
  if(account.isPending)return <main className="page-shell"><p role="status">Opening movie night…</p></main>
  if(account.isError)return <main className="page-shell"><p role="alert">Could not load your account.</p><button className="cta-button" onClick={()=>account.refetch()}>Retry</button></main>
  return <NightWorkspace key={account.data?.user.id??'guest'} auth={account.data??null}/>
}
function NightWorkspace({auth}:{auth:AuthState|null}){
  const client=useQueryClient()
  const location=useSyncExternalStore(subscribeUrl,()=>window.location.search+window.location.hash,()=> '')
  const roomId=new URLSearchParams(location.split('#')[0]).get('room')??''
  const invite=new URLSearchParams(location.split('#')[1]??'').get('invite')??''
  const [share,setShare]=useState('')
  const [title,setTitle]=useState('Friday movie night')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const rooms=useQuery({queryKey:['movie-nights',auth?.user.id],enabled:!!auth,queryFn:async()=>(await api.get<{items:{id:string;title:string;state:string;expired:boolean}[]}>('/api/movie-nights')).data})
  const room=useQuery({queryKey:['movie-night',auth?.user.id,roomId],enabled:!!auth&&!!roomId,queryFn:async()=>(await api.get<Room>(`/api/movie-nights/${roomId}`)).data,retry:false,refetchInterval:q=>q.state.error||q.state.data?.expired||q.state.data?.state==='selected'?false:3000})
  function open(id:string){setShare('');setNotice('');window.history.replaceState(null,'',id?`/movie-night?room=${encodeURIComponent(id)}`:'/movie-night');window.dispatchEvent(new PopStateEvent('popstate'))}
  function shareToken(token:string){setShare(`${window.location.origin}/movie-night#invite=${encodeURIComponent(token)}`)}
  async function act(path:string,payload:unknown={},method:'post'|'put'='post'){
    if(!auth||busy)return
    setBusy(true);setError('');setNotice('')
    try{const response=await api[method](path,payload,{headers:csrfHeaders(auth)});await client.invalidateQueries({queryKey:['movie-night']});await client.invalidateQueries({queryKey:['movie-nights']});return response.data}
    catch(e){setError(accountError(e))}finally{setBusy(false)}
  }
  const data=room.data
  const frozen=busy||!!data?.expired
  const complete=data?.members.every(m=>m.complete)
  return <main className="page-shell night-page">
    <header className="night-heading"><div><p className="eyebrow"><Users size={16}/> MOVIE NIGHT</p><h1>Good films.<br/><em>Better company.</em></h1><p className="subtle">Pick something everyone wants to watch. Invite, vote privately, and reveal your group’s favourites.</p></div><div className="night-steps"><span>01 · Gather your people</span><span>02 · Vote without the pressure</span><span>03 · Make it a movie night</span></div></header>
    {!auth?<section className="panel"><h2>Bring your people together</h2><p>Sign in to create or join a room. If you have an invitation, return to this link after signing in.</p><Link className="cta-button" href="/watchlist">Sign in to join</Link></section>:<>
      {error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
      {invite&&<section className="panel night-invite"><h2>You’re invited</h2><p>Join with your account. Invitations expire after 24 hours; new guests cannot join once voting starts.</p><button className="cta-button" disabled={busy} onClick={async()=>{const result=await act('/api/movie-nights/join',{token:invite});if(result)open(result.id)}}>Join movie night</button></section>}
      {!roomId&&!invite&&<div className="night-start"><section className="panel"><h2>Host a movie night</h2><form className="account-form" onSubmit={async e=>{e.preventDefault();const result=await act('/api/movie-nights',{title});if(result){open(result.id);shareToken(result.invite_token)}}}><label htmlFor="night-title">Room name</label><input className="search-input" id="night-title" value={title} onChange={e=>setTitle(e.target.value)} required maxLength={80}/><button className="cta-button" disabled={busy}>Create room</button></form><p className="meta">2–8 people · Eight-film shortlist · 24-hour room</p></section><section className="panel"><h2>Your rooms</h2>{rooms.isPending&&<p role="status">Loading rooms…</p>}{rooms.isError&&<p role="alert">Could not load your rooms. <button onClick={()=>rooms.refetch()}>Retry</button></p>}{rooms.data?.items.length===0&&<p className="subtle">Your next movie night starts here.</p>}{rooms.data?.items.map(r=><button className="night-room-link" key={r.id} onClick={()=>open(r.id)}>{r.title}<span>{r.expired?'Expired':r.state}</span></button>)}</section></div>}
      {roomId&&<>
        <button className="night-back" onClick={()=>open('')}>← All rooms</button>
        {room.isPending&&<p role="status">Loading room…</p>}{room.isError&&<p role="alert">{accountError(room.error)} <button onClick={()=>room.refetch()}>Retry</button></p>}
        {data&&<><section className="panel night-room-head"><div><span className="eyebrow">{data.expired?'EXPIRED':data.state.toUpperCase()}</span><h2>{data.title}</h2><p className="meta">{data.members.length}/8 people · Room closes {new Date(data.expires_at).toLocaleString()}</p></div><div className="night-people">{data.members.map(m=><span key={m.username}>{m.username}{m.is_host?' · host':''}{data.state==='voting'?(m.complete?' · ready':' · voting'):''}</span>)}</div></section>
        {data.expired?<p role="status">This room has expired. Its results are read-only. Create a new room to plan another night.</p>:<>
        {data.state==='lobby'&&<>
          {data.is_host&&<section className="night-invite panel"><h3>Invite your friends</h3><p className="meta">Anyone with the link can join while the lobby is open. Share it with your group.</p>{share?<><label htmlFor="night-share">Invite link</label><input id="night-share" className="search-input" value={share} readOnly/><button className="cta-button secondary-button" onClick={async()=>{try{await navigator.clipboard.writeText(share);setNotice('Invite link copied.')}catch{setNotice('Select the invite link and copy it manually.')}}}><Copy size={15}/> Copy invite</button></>:<button className="cta-button secondary-button" disabled={busy} onClick={async()=>{const result=await act(`/api/movie-nights/${roomId}/invite`);if(result)shareToken(result.invite_token)}}>Create new invite link</button>}<p className="meta">Creating a new link invalidates previous links. Existing members stay in the room.</p></section>}
          <PreferencesEditor key={roomId} data={data} busy={busy} onSave={async p=>{const result=await act(`/api/movie-nights/${roomId}/preferences`,p,'put');if(result)setNotice('Your preferences are saved.')}}/>
          <section className="night-stage-action"><p className="subtle">Everyone can save their own preferences. The shortlist balances shared genre interests; favourites are excluded. Starting freezes membership and preferences.</p>{data.is_host?<button className="cta-button" disabled={frozen||data.members.length<2} onClick={()=>act(`/api/movie-nights/${roomId}/start`)}>Start private voting</button>:<p>Waiting for the host to start voting.</p>}</section>
        </>}
        {data.state==='voting'&&<section><h2>Your private ballot</h2><p className="subtle">Yes means you’d watch it. Pass is neutral. A single veto excludes a film. Choose one on every card; you can change votes until the reveal.</p><div className="night-films">{data.movies.map(movie=><article className="night-film" key={movie.id}><Link href={`/movies/${movie.slug}`}><MovieArtwork src={movie.poster_url} title={movie.title}/><h3>{movie.title}</h3></Link><p className="meta">{movie.year} · {movie.genres.slice(0,2).join(' / ')}</p><div className="night-votes" role="group" aria-label={`Vote on ${movie.title}`}>{([{value:'yes',label:'Yes',icon:Check},{value:'pass',label:'Pass',icon:Minus},{value:'veto',label:'Veto',icon:Ban}] as const).map(({value,label,icon:Icon})=><button key={value} aria-pressed={data.my_votes[movie.id]===value} disabled={frozen} onClick={()=>act(`/api/movie-nights/${roomId}/vote`,{movie_id:movie.id,choice:value},'put')}><Icon size={14}/>{label}</button>)}</div></article>)}</div><div className="night-stage-action"><p role="status">{data.members.filter(m=>m.complete).length} of {data.members.length} ballots complete. Only completion status is shared.</p>{data.is_host&&<button className="cta-button" disabled={frozen||!complete} onClick={()=>act(`/api/movie-nights/${roomId}/reveal`)}>Reveal group matches</button>}</div></section>}
        </>}
        {(data.state==='revealed'||data.state==='selected')&&<section><h2>{data.state==='selected'?'Tonight’s pick':'Your group matches'}</h2><p className="subtle">Most yes votes wins among films with no veto. Equal scores are tied; the host chooses between top matches.</p>{data.results.every(r=>!r.eligible)&&<p role="status">Every film was vetoed. There is no winner—start another room with different preferences.</p>}<div className="night-films">{data.results.filter(r=>data.state!=='selected'||r.movie_id===data.winner_id).map(result=>{const movie=data.movies.find(m=>m.id===result.movie_id);return movie&&<article className="night-film" key={movie.id}><Link href={`/movies/${movie.slug}`}><MovieArtwork src={movie.poster_url} title={movie.title}/><h3>{movie.title}</h3></Link>{result.top_match&&<span className="eyebrow">Top match</span>}<p className="meta">{result.reason}</p>{data.is_host&&data.state==='revealed'&&result.top_match&&<button className="cta-button" disabled={frozen} onClick={()=>act(`/api/movie-nights/${roomId}/select`,{movie_id:movie.id})}>Choose {movie.title}</button>}{data.state==='selected'&&<><WatchlistButton movieId={movie.id}/><p className="meta">Optional. Saves to your watchlist only.</p></>}</article>})}</div></section>}
        </>}
      </>}
    </>}
  </main>
}
function PreferencesEditor({data,busy,onSave}:{data:Room;busy:boolean;onSave:(p:{genres:string[];favorites:number[]})=>Promise<void>}){
  const [selected,setSelected]=useState(data.preferences.genres)
  const [favorites,setFavorites]=useState(data.favorite_movies)
  const [search,setSearch]=useState('')
  const [term,setTerm]=useState('')
  const suggestions=useQuery({queryKey:['night-favorite-search',term],enabled:term.length>=2,queryFn:()=>movieApi.searchSuggestions(term)})
  return <section className="panel night-preferences"><h2>Your taste for tonight</h2><p className="meta">Optional: up to five genres and five released favourites. Your choices stay private.</p><fieldset disabled={busy}><legend>Genres</legend><div className="night-genres">{genres.map(genre=><label key={genre}><input type="checkbox" checked={selected.includes(genre)} disabled={!selected.includes(genre)&&selected.length>=5} onChange={()=>setSelected(selected.includes(genre)?selected.filter(g=>g!==genre):[...selected,genre])}/>{genre}</label>)}</div></fieldset><form className="night-favorite-search" onSubmit={e=>{e.preventDefault();setTerm(search.trim())}}><label htmlFor="night-favorite">Favourite film</label><input className="search-input" id="night-favorite" value={search} onChange={e=>setSearch(e.target.value)} minLength={2} maxLength={100}/><button className="cta-button secondary-button" disabled={busy}>Find film</button></form>{suggestions.isFetching&&<p role="status">Searching…</p>}{suggestions.isError&&<p role="alert">Search failed. Try again.</p>}{suggestions.data?.filter(m=>m.release_date.slice(0,10)<=new Date().toISOString().slice(0,10)&&!favorites.some(f=>f.id===m.id)).map(movie=><button className="night-room-link" key={movie.id} disabled={busy||favorites.length>=5} onClick={()=>{setFavorites([...favorites,{id:movie.id,title:movie.title}]);setTerm('');setSearch('')}}>Add {movie.title}</button>)}<div className="night-people">{favorites.map(f=><button key={f.id} disabled={busy} onClick={()=>setFavorites(favorites.filter(v=>v.id!==f.id))}>Remove {f.title} ×</button>)}</div><button className="cta-button" disabled={busy} onClick={()=>onSave({genres:selected,favorites:favorites.map(f=>f.id)})}>Save my preferences</button></section>
}
