import type { MovieSummary } from '@/lib/api'

export function inferBrand(movie: MovieSummary) {
  const haystack = [
    movie.franchise || '',
    ...movie.studios,
    movie.title,
  ].join(' ').toLowerCase()

  if (haystack.includes('marvel')) {
    return 'Marvel'
  }
  if (haystack.includes('dc')) {
    return 'DC'
  }
  if (haystack.includes('pixar')) {
    return 'Pixar'
  }
  if (haystack.includes('disney')) {
    return 'Disney'
  }
  if (haystack.includes('warner')) {
    return 'Warner Bros.'
  }
  if (haystack.includes('sony')) {
    return 'Sony'
  }
  if (haystack.includes('universal')) {
    return 'Universal'
  }

  return 'Other'
}

export function parseImdbRating(value: string | null) {
  return value ? Number(value) || 0 : 0
}
