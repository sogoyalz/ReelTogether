'use client'

import { EntityMovieGrid } from '@/components/discovery/EntityMovieGrid'

export default function GenrePage({ params }: { params: { genre: string } }) {
  const genre = decodeURIComponent(params.genre)
  return (
    <EntityMovieGrid
      eyebrow="Genre"
      title={genre}
      description={`Every tracked movie currently tagged with ${genre}.`}
      matcher={(movie) => movie.genres.includes(genre)}
    />
  )
}
