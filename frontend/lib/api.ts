import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface MovieSummary {
  id: number
  tmdb_id: number
  slug: string
  title: string
  release_date: string
  status: string
  poster_url: string | null
  backdrop_url: string | null
  overview: string | null
  genres: string[]
  tmdb_popularity: number
  buzz_score: number
  hype_score: number
  franchise: string | null
  studios: string[]
  streaming_on: string[]
  directors: string[]
  cast: string[]
  imdb_rating: string | null
  rated: string | null
  runtime: string | null
  rotten_tomatoes: string | null
  logo_url: string | null
}

export interface MovieDetail extends MovieSummary {
  trailer_url: string | null
  trailer_views: number
  social_mentions: number
  google_trends_score: number
  sentiment_score: number
  predicted_opening_weekend_usd: number
  predicted_domestic_total_usd: number
  imdb_id: string | null
  box_office: string | null
  awards: string | null
  metascore: string | null
  imdb_votes: string | null
  omdb_poster_url: string | null
  writers: string[]
  trailer_embed_url: string | null
  box_office_history: {
    label: string
    value_usd: number
  }[]
  backdrops: string[]
  wikipedia_summary: string | null
  wikipedia_url: string | null
  wikipedia_categories: string[]
  wikidata_id: string | null
  wikidata_url: string | null
  wikidata_label: string | null
  wikidata_description: string | null
  wikidata_instance_of: string[]
  wikidata_genres: string[]
  wikidata_countries: string[]
}

export interface CatalogFacets {
  genres: string[]
  franchises: string[]
  studios: string[]
  streaming: string[]
  statuses: string[]
  years: number[]
}

export interface PaginatedMovieResponse {
  items: MovieSummary[]
  total: number
  page: number
  page_size: number
  total_pages: number
  facets: CatalogFacets
}

export interface MovieAnalytics {
  movie_id: number
  movie_title: string
  snapshot_date: string
  youtube_views: number
  youtube_likes: number
  youtube_comments: number
  google_trends_score: number
  x_mentions: number
  reddit_mentions: number
  social_mentions: number
  sentiment_score: number
  sentiment_breakdown: {
    positive: number
    neutral: number
    negative: number
  }
  buzz_score: number
  hype_score: number
  predicted_opening_weekend_usd: number
  predicted_domestic_total_usd: number
  trailer_url: string | null
  updated_at: string
  score_breakdown: {
    youtube_interest: number
    search_interest: number
    social_buzz: number
    sentiment: number
    momentum: number
    release_proximity: number
  }
}

export interface AnalyticsHistoryPoint {
  snapshot_date: string
  buzz_score: number
  hype_score: number
  youtube_views: number
  social_mentions: number
  google_trends_score: number
}

export interface AnalyticsHistoryResponse {
  movie_id: number
  movie_title: string
  points: AnalyticsHistoryPoint[]
}

export interface ComparisonItem {
  movie_id: number
  slug: string
  title: string
  release_date: string
  status: string
  buzz_score: number
  hype_score: number
  youtube_views: number
  social_mentions: number
  google_trends_score: number
  sentiment_score: number
  predicted_opening_weekend_usd: number
  predicted_domestic_total_usd: number
  tmdb_popularity: number
  imdb_rating: string | null
  rotten_tomatoes: string | null
  runtime: string | null
  franchise: string | null
  streaming_on: string[]
  audience_sentiment: number | null
  prediction_confidence: number | null
  key_themes: string[]
}

export interface MovieAIOverview {
  sentiment: {
    movie_id: number
    snapshot_at: string
    positive_count: number
    neutral_count: number
    negative_count: number
    sentiment_score: number
    sample_size: number
    model_version: string
  }
  prediction: {
    movie_id: number
    snapshot_at: string
    predicted_opening_weekend_usd: number
    predicted_domestic_total_usd: number
    confidence_score: number
    feature_version: string
    model_version: string
  }
  summary: {
    movie_id: number
    snapshot_at: string
    audience_summary: string
    critic_summary: string
    key_themes: string[]
    model_version: string
  }
  discussions: {
    source: string
    title: string
    body: string
    author: string | null
    engagement_score: number
    created_at: string
    url: string | null
  }[]
}

export interface ComparisonResponse {
  compared_at: string
  items: ComparisonItem[]
}

export interface DashboardResponse {
  updated_at: string
  trending: MovieSummary[]
  most_hyped: MovieSummary[]
  stats: {
    tracked_movies: number
    average_hype_score: number
    average_buzz_score: number
  }
}

export interface AutocompleteSuggestion {
  id: number
  slug: string
  title: string
  status: string
  release_date: string
}

export interface DashboardBucket {
  label: string
  movie_count: number
  average_hype_score: number
}

export interface DiscoveryDashboardResponse {
  trending_by_genre: DashboardBucket[]
  trending_by_franchise: DashboardBucket[]
  editorial_collections: Record<string, MovieSummary[]>
}

export interface RefreshAnalyticsResponse {
  refreshed_movies: number
  skipped_movies: number
  failed_movies: number
  skipped_reasons: string[]
  failed_reasons: string[]
}

export const movieApi = {
  getCatalog: async (limit = 50) => (await api.get<MovieSummary[]>('/api/movies', { params: { limit } })).data,
  browseCatalog: async (params: Record<string, string | number | undefined>) =>
    (await api.get<PaginatedMovieResponse>('/api/movies/browse', { params })).data,
  getTrending: async (limit = 6) =>
    (await api.get<MovieSummary[]>('/api/movies/trending', { params: { limit } })).data,
  getUpcoming: async (limit = 6) =>
    (await api.get<MovieSummary[]>('/api/movies/upcoming', { params: { limit } })).data,
  getReleased: async (limit = 12) =>
    (await api.get<MovieSummary[]>('/api/movies/released', { params: { limit } })).data,
  getMovieDetails: async (id: number) => (await api.get<MovieDetail>(`/api/movies/${id}`)).data,
  getMovieBySlug: async (slug: string) => (await api.get<MovieDetail>(`/api/movies/slug/${slug}`)).data,
  getMovieAI: async (id: number) => (await api.get<MovieAIOverview>(`/api/ai/movie/${id}`)).data,
  getAnalytics: async (id: number) => (await api.get<MovieAnalytics>(`/api/analytics/movie/${id}`)).data,
  getAnalyticsHistory: async (id: number) =>
    (await api.get<AnalyticsHistoryResponse>(`/api/analytics/movie/${id}/history`)).data,
  getDashboard: async () => (await api.get<DashboardResponse>('/api/analytics/dashboard')).data,
  getDiscoveryDashboard: async () =>
    (await api.get<DiscoveryDashboardResponse>('/api/search/dashboard')).data,
  searchMovies: async (params: Record<string, string | number | undefined>) =>
    (await api.get<PaginatedMovieResponse>('/api/search', { params })).data,
  searchSuggestions: async (query: string) =>
    (await api.get<AutocompleteSuggestion[]>('/api/search/suggest', { params: { q: query } })).data,
  compareMovies: async (movieIds: number[]) =>
    (
      await api.get<ComparisonResponse>('/api/analytics/compare', {
        params: { movie_ids: movieIds.join(',') },
      })
    ).data,
  refreshAnalytics: async () =>
    (await api.post<RefreshAnalyticsResponse>('/api/analytics/refresh')).data,
  refreshMovieAnalytics: async (id: number) =>
    (await api.post<RefreshAnalyticsResponse>(`/api/analytics/movie/${id}/refresh`)).data,
}
