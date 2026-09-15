import { EntityMovieGrid } from '@/components/discovery/EntityMovieGrid'

export default async function StudioPage({ params }: { params: Promise<{ studio: string }> }) {
  const studio = decodeURIComponent((await params).studio)
  return (
    <EntityMovieGrid
      eyebrow="Studio"
      title={studio}
      description={`Tracked titles currently associated with ${studio}.`}
      browseParams={{ studio }}
    />
  )
}
