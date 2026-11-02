import Link from 'next/link'
import Image from 'next/image'

export default function AboutPage() {
  return <main className="page-shell"><section className="panel">
    <span className="eyebrow">About ReelTogether</span>
    <h1>Good films. Clear information.</h1>
    <p>ReelTogether helps you explore films, keep a private watchlist and choose a movie with friends.</p>
    <h2>Sources and credits</h2>
    <a href="https://www.themoviedb.org/" rel="noreferrer"><Image src="/tmdb-logo.svg" alt="The Movie Database" width={150} height={20} style={{height:'auto'}} /></a>
    <p>Movie metadata and artwork may come from <a href="https://www.themoviedb.org/" rel="noreferrer">TMDB</a>. This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
    <p>Optional ratings and reported box office come from <a href="https://www.omdbapi.com/" rel="noreferrer">OMDb</a>. Trailer observations come from YouTube when that provider is configured. Watch-provider availability data from TMDB is supplied by JustWatch. Availability varies by region and date; provider names in the catalog do not guarantee you can stream a title.</p>
    <p><a href="https://www.justwatch.com/" rel="noreferrer">Check regional availability on JustWatch</a> · <a href="https://www.themoviedb.org/about/logos-attribution" rel="noreferrer">TMDB logos and attribution</a></p>
    <h2>Demo data and estimates</h2>
    <p>Without provider credentials, the app uses an illustrative demo catalog. These records, dates and scores are not verified movie facts. Attention scores and revenue estimates are labeled separately from sourced observations. Forecasts are experimental and are not validated predictions.</p>
    <h2>Your account</h2>
    <p>Your watchlist and recommendation preferences belong to your account. Movie-night members can see member names and room progress; votes remain private until the reveal. Rooms expire after 24 hours.</p>
    <p>You can change your password, sign out other browsers, download your data and permanently delete your account in <Link href="/account-security">Account security</Link>. Deletion also removes rooms you host. Backups may retain earlier copies until the operator’s backup retention period ends. Recovery must reapply account deletions before the service resumes.</p>
    <p>Save a recovery code after creating your account. Without a saved code, the app cannot recover a forgotten password.</p>
    <p><Link href="/movies" className="cta-button">Explore the library</Link></p>
  </section></main>
}
