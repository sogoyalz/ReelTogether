import { EntityMovieGrid } from '@/components/discovery/EntityMovieGrid'

export default async function GenrePage({ params }: { params: Promise<{ genre: string }> }) {
  const genre = decodeURIComponent((await params).genre)
  return (
    <EntityMovieGrid
      eyebrow="Genre"
      title={genre}
      description={`Every tracked movie currently tagged with ${genre}.`}
      browseParams={{ genre }}
    />
  )
}
