'use client'

import { useParams } from 'next/navigation'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'

import { BoxOfficeHistoryChart } from '@/components/movies/BoxOfficeHistoryChart'
import { CriticAudienceDashboard } from '@/components/movies/CriticAudienceDashboard'
import { ForecastConfidenceCard } from '@/components/movies/ForecastConfidenceCard'
import { HypeGauge } from '@/components/movies/HypeGauge'
import { InterestChart } from '@/components/movies/InterestChart'
import { MovieHero } from '@/components/movies/MovieHero'
import { ScoreBreakdownCard } from '@/components/movies/ScoreBreakdownCard'
import { TrendChart } from '@/components/movies/TrendChart'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/QueryState'
import { movieApi } from '@/lib/api'
import { formatCompactNumber, formatCurrency } from '@/lib/formatters'

export default function MoviePage() {
  const params = useParams<{ slug: string }>()
  const movieQuery = useQuery({
    queryKey: ['movie', params.slug],
    queryFn: () => movieApi.getMovieBySlug(params.slug),
  })

  const analyticsQuery = useQuery({
    queryKey: ['movie-analytics', movieQuery.data?.id],
    queryFn: () => movieApi.getAnalytics(movieQuery.data!.id),
    enabled: Boolean(movieQuery.data?.id),
  })
  const historyQuery = useQuery({
    queryKey: ['movie-history', movieQuery.data?.id],
    queryFn: () => movieApi.getAnalyticsHistory(movieQuery.data!.id),
    enabled: Boolean(movieQuery.data?.id),
  })
  const aiQuery = useQuery({
    queryKey: ['movie-ai', movieQuery.data?.id],
    queryFn: () => movieApi.getMovieAI(movieQuery.data!.id),
    enabled: Boolean(movieQuery.data?.id),
  })

  if (movieQuery.isLoading) {
    return (
      <main className="page-shell">
        <LoadingState title="Loading your movie" description="Finding the story, cast, and details." />
      </main>
    )
  }

  if (movieQuery.isError) {
    return (
      <main className="page-shell">
        <ErrorState title="Movie detail unavailable" description="This movie page could not be loaded right now." />
      </main>
    )
  }

  if (!movieQuery.data) {
    return (
      <main className="page-shell">
        <EmptyState title="Movie not found" description="The requested movie is not in the current catalog." />
      </main>
    )
  }

  const movie = movieQuery.data
  const analytics = analyticsQuery.data
  const history = historyQuery.data
  const ai = aiQuery.data
  const analyticsUnavailable = analyticsQuery.isError || !analytics
  const predictionFactors = analytics
    ? [
        {
          label: 'Trailer reach',
          value: formatCompactNumber(analytics.youtube_views),
          description: 'Trailer views, likes, and comments are used as the strongest top-of-funnel demand signal.',
        },
        {
          label: 'Conversation volume',
          value: formatCompactNumber(analytics.social_mentions),
          description: 'Cross-platform discussion volume helps estimate opening-weekend momentum and awareness.',
        },
        {
          label: 'Search demand',
          value: `${Math.round(analytics.google_trends_score)}`,
          description: 'Search interest acts as a proxy for broad intent beyond core fandom.',
        },
        {
          label: 'Sentiment',
          value: `${Math.round(analytics.sentiment_score * 100)}%`,
          description: 'Audience positivity affects how efficiently early buzz can convert into stronger legs.',
        },
      ]
    : []

  return (
    <main className="page-shell">
      <Link className="eyebrow" href="/">
        Back to home
      </Link>
      <MovieHero movie={movie} />
      <section className="cinema-film-facts" aria-label="Film details">
        {movie.directors.length > 0 && <div><span>Directed by</span><p>{movie.directors.map((person, index) => <span key={person}>{index > 0 && ', '}<Link href={`/people/${encodeURIComponent(person)}`}>{person}</Link></span>)}</p></div>}
        {movie.cast.length > 0 && <div><span>Starring</span><p>{movie.cast.slice(0, 5).join(' · ')}</p></div>}
        {movie.streaming_on.length > 0 && <div><span>Streaming platforms</span><p>{movie.streaming_on.join(' · ')}</p><small>Availability varies by region.</small></div>}
      </section>
      {movie.trailer_embed_url && <section className="cinema-trailer"><div className="section-header"><h2>A first look</h2></div><div className="video-shell"><iframe loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen src={movie.trailer_embed_url} title={`${movie.title} trailer`} /></div></section>}
      {movie.warnings.length > 0 && <p className="meta cinema-source-note">{movie.warnings[0]}</p>}
      <details className="cinema-details">
        <summary>Go deeper <span>Audience insights, film context &amp; detailed analytics</span></summary>
        <p className="meta">Attention scores and forecasts may be estimates. Source notes and methodology are included below.</p>
      <div className="detail-grid" style={{ marginTop: 28 }}>
        <div className="stack">
          {ai ? (
            <div className="panel">
              <div className="section-header" style={{ marginTop: 0 }}>
                <div>
                  <h3>Movie insights</h3>
                  <p>Stored sentiment, prediction confidence, and summary outputs generated from the current movie data.</p>
                </div>
              </div>
              <div className="overview-grid">
                <div className="metric-card">
                  <div className="metric-label">Audience Sentiment</div>
                  <div className="metric-value overview-title">{Math.round(ai.sentiment.sentiment_score * 100)}%</div>
                  <p className="meta">{ai.sentiment.sample_size} scored discussion samples</p>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Prediction Confidence</div>
                  <div className="metric-value overview-title">Unvalidated</div>
                  <p className="meta">{ai.prediction.model_version}</p>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Opening Forecast</div>
                  <div className="metric-value overview-title">{ai.prediction.forecast_status === 'modeled' ? formatCurrency(ai.prediction.predicted_opening_weekend_usd) : 'Unavailable'}</div>
                  <p className="meta">{ai.prediction.forecast_note}</p>
                </div>
              </div>
            </div>
          ) : aiQuery.isLoading ? (
            <LoadingState title="Loading movie insights" description="Pulling generated sentiment, forecasts, and summaries." />
          ) : (
            <SectionNotice
              description="The movie record loaded, but the summary layer has not been generated for this title yet."
              title="Movie insights unavailable"
            />
          )}
          {analytics ? (
            <InterestChart analytics={analytics} />
          ) : analyticsQuery.isLoading ? (
            <LoadingState title="Loading interest signals" description="Fetching live trailer and conversation metrics." />
          ) : (
            <SectionNotice
              description="Trailer, social, and forecast metrics could not be loaded right now."
              title="Interest signals unavailable"
            />
          )}
          {history ? (
            <TrendChart history={history} />
          ) : historyQuery.isLoading ? (
            <LoadingState title="Loading trend history" description="Pulling historical buzz and hype points." />
          ) : (
            <SectionNotice
              description="Historical snapshots are missing for this title, so the trend chart is hidden for now."
              title="Trend history unavailable"
            />
          )}
          <BoxOfficeHistoryChart movie={movie} />
          <div className="panel">
            <div className="section-header" style={{ marginTop: 0 }}>
              <div>
                <h3>Cross-Platform Detail</h3>
                <p>Expanded detail for trailer performance, creative team, streaming, and projected demand.</p>
              </div>
            </div>
            <table className="table">
              <tbody>
                <tr>
                  <td>Franchise</td>
                  <td>{movie.franchise ? <Link href={`/franchises/${encodeURIComponent(movie.franchise)}`}>{movie.franchise}</Link> : 'Standalone'}</td>
                </tr>
                <tr>
                  <td>Studios</td>
                  <td>{movie.studios.map((studio) => <Link className="inline-chip" href={`/studios/${encodeURIComponent(studio)}`} key={studio}>{studio}</Link>)}</td>
                </tr>
                <tr>
                  <td>Directors</td>
                  <td>{movie.directors.map((person) => <Link className="inline-chip" href={`/people/${encodeURIComponent(person)}`} key={person}>{person}</Link>)}</td>
                </tr>
                <tr>
                  <td>Writers</td>
                  <td>{movie.writers.join(', ') || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Lead Cast</td>
                  <td>{movie.cast.map((person) => <Link className="inline-chip" href={`/people/${encodeURIComponent(person)}`} key={person}>{person}</Link>)}</td>
                </tr>
                <tr>
                  <td>Streaming</td>
                  <td>{movie.streaming_on.join(', ') || 'Not available'}</td>
                </tr>
                <tr>
                  <td>IMDb Rating</td>
                  <td>{movie.imdb_rating ? `${movie.imdb_rating}/10` : 'Not available'}</td>
                </tr>
                <tr>
                  <td>Rotten Tomatoes</td>
                  <td>{movie.rotten_tomatoes || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Runtime</td>
                  <td>{movie.runtime || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Rated</td>
                  <td>{movie.rated || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Awards</td>
                  <td>{movie.awards || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Reported Box Office</td>
                  <td>{movie.box_office || 'Not available'}</td>
                </tr>
                <tr>
                  <td>YouTube Likes</td>
                  <td>{analytics ? formatCompactNumber(analytics.youtube_likes) : 'Not available'}</td>
                </tr>
                <tr>
                  <td>YouTube Comments</td>
                  <td>{analytics ? formatCompactNumber(analytics.youtube_comments) : 'Not available'}</td>
                </tr>
                <tr>
                  <td>X Mentions</td>
                  <td>{analytics ? formatCompactNumber(analytics.x_mentions) : 'Not available'}</td>
                </tr>
                <tr>
                  <td>Reddit Mentions</td>
                  <td>{analytics ? formatCompactNumber(analytics.reddit_mentions) : 'Not available'}</td>
                </tr>
                <tr>
                  <td>Predicted Domestic Total</td>
                  <td>{analytics ? formatCurrency(analytics.predicted_domestic_total_usd) : 'Not available'}</td>
                </tr>
                <tr>
                  <td>IMDb Votes</td>
                  <td>{movie.imdb_votes || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Metascore</td>
                  <td>{movie.metascore || 'Not available'}</td>
                </tr>
                <tr>
                  <td>Trailer</td>
                  <td>
                    {analytics?.trailer_url ? (
                      <a href={analytics.trailer_url} rel="noopener noreferrer" target="_blank">
                        Watch on YouTube
                      </a>
                    ) : 'Trailer not available'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {ai ? (
            <>
              <div className="panel">
                <div className="section-header" style={{ marginTop: 0 }}>
                  <div>
                    <h3>Audience Summary</h3>
                    <p>Stored summary blocks and discussion themes for this title.</p>
                  </div>
                </div>
                <div className="stack">
                  <div className="metric-card">
                    <div className="metric-label">Audience Read</div>
                    <p className="subtle">{ai.summary.audience_summary}</p>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Critic Read</div>
                    <p className="subtle">{ai.summary.critic_summary}</p>
                  </div>
                  <div className="genre-list">
                    {ai.summary.key_themes.map((theme) => (
                      <span className="genre-tag" key={theme}>{theme}</span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="panel">
                <div className="section-header" style={{ marginTop: 0 }}>
                  <div>
                    <h3>What Critics Are Saying</h3>
                    <p>Professional-review posture based on critic-side discussion, ratings context, and prestige signals.</p>
                  </div>
                </div>
                <div className="stack">
                  <div className="metric-card">
                    <div className="metric-label">Critical Read</div>
                    <p className="subtle">{ai.critic_vs_audience.critics.summary}</p>
                  </div>
                  <div className="compare-stat-grid">
                    <div className="metric-card">
                      <div className="metric-label">Positive Drivers</div>
                      <div>{ai.critic_vs_audience.critics.positive_drivers.join(', ') || 'n/a'}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Negative Drivers</div>
                      <div>{ai.critic_vs_audience.critics.negative_drivers.join(', ') || 'n/a'}</div>
                    </div>
                  </div>
                  {ai.critic_vs_audience.critics.top_themes.length ? (
                    <div className="genre-list">
                      {ai.critic_vs_audience.critics.top_themes.map((theme) => (
                        <span className="genre-tag" key={theme}>{theme}</span>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
              <div className="panel">
                <div className="section-header" style={{ marginTop: 0 }}>
                  <div>
                    <h3>What Audiences Are Saying</h3>
                    <p>Normal viewer reaction summarized from Reddit and YouTube-style discussion, with theme extraction and sentiment.</p>
                  </div>
                </div>
                <div className="stack">
                  <div className="metric-card">
                    <div className="metric-label">Audience Read</div>
                    <p className="subtle">{ai.critic_vs_audience.audience.summary}</p>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Public Opinion Read</div>
                    <p className="subtle">{ai.public_opinion.overall_summary}</p>
                  </div>
                  <div className="overview-grid">
                    <div className="metric-card">
                      <div className="metric-label">Positive</div>
                      <div className="metric-value overview-title">{ai.public_opinion.positive_count}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Neutral</div>
                      <div className="metric-value overview-title">{ai.public_opinion.neutral_count}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Negative</div>
                      <div className="metric-value overview-title">{ai.public_opinion.negative_count}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">Average Sentiment</div>
                      <div className="metric-value overview-title">{Math.round(ai.public_opinion.average_sentiment * 100)}%</div>
                    </div>
                  </div>
                  {ai.critic_vs_audience.audience.top_themes.length ? (
                    <div className="genre-list">
                      {ai.critic_vs_audience.audience.top_themes.map((theme) => (
                        <span className="genre-tag" key={theme}>{theme}</span>
                      ))}
                    </div>
                  ) : null}
                  {ai.public_opinion.highlighted_quotes.length ? (
                    <div className="stack">
                      {ai.public_opinion.highlighted_quotes.map((quote, index) => (
                        <div className="metric-card" key={`${index}-${quote.slice(0, 24)}`}>
                          <div className="metric-label">Viewer Highlight</div>
                          <p className="subtle">{quote}</p>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
              <CriticAudienceDashboard ai={ai} />
            </>
          ) : null}
          {movie.wikipedia_summary ? (
            <div className="panel">
              <div className="section-header" style={{ marginTop: 0 }}>
                <div>
                  <h3>Wikipedia Context</h3>
                  <p>Extra background context pulled in for a cleaner editorial read on the movie.</p>
                </div>
              </div>
              <div className="stack">
                <div className="metric-card">
                  <p className="subtle">{movie.wikipedia_summary}</p>
                  {movie.wikipedia_url ? (
                    <a href={movie.wikipedia_url} rel="noopener noreferrer" target="_blank">
                      Read full article on Wikipedia
                    </a>
                  ) : null}
                </div>
                {movie.wikipedia_categories.length ? (
                  <div className="genre-list">
                    {movie.wikipedia_categories.map((category) => (
                      <span className="genre-tag" key={category}>{category}</span>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}
          {movie.wikidata_description || movie.wikidata_instance_of.length || movie.wikidata_genres.length ? (
            <div className="panel">
              <div className="section-header" style={{ marginTop: 0 }}>
                <div>
                  <h3>Wikidata Signals</h3>
                  <p>Structured facts pulled from Wikidata for cleaner classification and linking.</p>
                </div>
              </div>
              <div className="stack">
                {movie.wikidata_description ? (
                  <div className="metric-card">
                    <div className="metric-label">Description</div>
                    <p className="subtle">{movie.wikidata_description}</p>
                    {movie.wikidata_url ? (
                      <a href={movie.wikidata_url} rel="noopener noreferrer" target="_blank">
                        Open Wikidata entry
                      </a>
                    ) : null}
                  </div>
                ) : null}
                {movie.wikidata_instance_of.length ? (
                  <div>
                    <div className="metric-label">Instance Of</div>
                    <div className="genre-list" style={{ marginTop: 10 }}>
                      {movie.wikidata_instance_of.map((item) => (
                        <span className="genre-tag" key={item}>{item}</span>
                      ))}
                    </div>
                  </div>
                ) : null}
                {movie.wikidata_genres.length ? (
                  <div>
                    <div className="metric-label">Wikidata Genres</div>
                    <div className="genre-list" style={{ marginTop: 10 }}>
                      {movie.wikidata_genres.map((item) => (
                        <span className="genre-tag" key={item}>{item}</span>
                      ))}
                    </div>
                  </div>
                ) : null}
                {movie.wikidata_countries.length ? (
                  <div>
                    <div className="metric-label">Countries</div>
                    <div className="genre-list" style={{ marginTop: 10 }}>
                      {movie.wikidata_countries.map((item) => (
                        <span className="genre-tag" key={item}>{item}</span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}
          {ai ? (
            <div className="panel">
              <div className="section-header" style={{ marginTop: 0 }}>
                <div>
                  <h3>Discussion Signals</h3>
                  <p>Recent stored discussion items that feed the sentiment and summary layer.</p>
                </div>
              </div>
              <div className="stack">
                {ai.discussions.map((item) => (
                  <div className="metric-card" key={`${item.source}-${item.title}`}>
                    <div className="title-row">
                      <div>
                        <h4>{item.title}</h4>
                        <p className="meta">{item.source} • {item.author || 'unknown author'}</p>
                      </div>
                      <div className="score-pill">{Math.round(item.engagement_score)}</div>
                    </div>
                    <p className="subtle" style={{ marginTop: 12 }}>{item.body}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {movie.backdrops.length ? (
            <div className="panel">
              <div className="section-header" style={{ marginTop: 0 }}>
                <div>
                  <h3>Image Gallery</h3>
                  <p>TMDB backdrop stills pulled into the detail page for richer visual context.</p>
                </div>
              </div>
              <div className="poster-strip">
                {movie.backdrops.map((backdrop) => (
                  <img alt={`${movie.title} backdrop`} className="gallery-image" key={backdrop} src={backdrop} />
                ))}
              </div>
            </div>
          ) : null}
        </div>
        <div className="stack">
          {analytics ? <HypeGauge analytics={analytics} /> : null}
          {analytics ? <ScoreBreakdownCard analytics={analytics} /> : null}
          {analyticsUnavailable ? (
            <SectionNotice
              description="The right-rail score modules are hidden until analytics data is available again."
              title="Score cards unavailable"
            />
          ) : null}
          {ai ? <ForecastConfidenceCard ai={ai} /> : null}
          {ai ? (
            <div className="panel">
              <div className="section-header" style={{ marginTop: 0 }}>
                <div>
                  <h3>Prediction Method</h3>
                  <p>Feature-level interpretation behind the current opening weekend and domestic forecast.</p>
                </div>
              </div>
              <div className="stack">
                <div className="metric-card">
                  <div className="metric-label">Current Forecast</div>
                  <div className="metric-value overview-title">{ai.prediction.forecast_status === 'modeled' ? formatCurrency(ai.prediction.predicted_opening_weekend_usd) : 'Unavailable'}</div>
                  <p className="meta">
                    Domestic total forecast {formatCurrency(ai.prediction.predicted_domestic_total_usd)}. Experimental estimate; accuracy has not been validated.
                  </p>
                </div>
                {predictionFactors.length ? (
                  <div className="stack">
                    {predictionFactors.map((factor) => (
                      <div className="metric-card" key={factor.label}>
                        <div className="title-row">
                          <div>
                            <div className="metric-label">{factor.label}</div>
                            <p className="subtle" style={{ marginTop: 8 }}>{factor.description}</p>
                          </div>
                          <div className="score-pill">{factor.value}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
                <div className="metric-card">
                  <div className="metric-label">Model Layer</div>
                  <p className="subtle">{ai.prediction.methodology}</p>
                </div>
              </div>
            </div>
          ) : null}
          <div className="panel">
            <div className="section-header" style={{ marginTop: 0 }}>
              <div>
                <h3>Quick Read</h3>
                <p>A faster scan for the movie’s critical and commercial context.</p>
              </div>
            </div>
            <div className="compare-stat-grid">
              <div>
                <div className="metric-label">Reported Box Office</div>
                <div>{movie.box_office || 'n/a'}</div>
              </div>
              <div>
                <div className="metric-label">Awards</div>
                <div>{movie.awards || 'n/a'}</div>
              </div>
              <div>
                <div className="metric-label">Metascore</div>
                <div>{movie.metascore || 'n/a'}</div>
              </div>
              <div>
                <div className="metric-label">IMDb Votes</div>
                <div>{movie.imdb_votes || 'n/a'}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      </details>
    </main>
  )
}

function SectionNotice({ title, description }: { title: string; description: string }) {
  return (
    <div className="panel">
      <div className="section-header" style={{ marginTop: 0 }}>
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>
    </div>
  )
}
