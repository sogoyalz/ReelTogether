import { EntityMovieGrid } from '@/components/discovery/EntityMovieGrid'

export default function StudioPage({ params }: { params: { studio: string } }) {
  const studio = decodeURIComponent(params.studio)
  return (
    <EntityMovieGrid
      eyebrow="Studio"
      title={studio}
      description={`Tracked titles currently associated with ${studio}.`}
      browseParams={{ studio }}
    />
  )
}
