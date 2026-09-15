import { EntityMovieGrid } from '@/components/discovery/EntityMovieGrid'

export default async function PersonPage({ params }: { params: Promise<{ name: string }> }) {
  const name = decodeURIComponent((await params).name)
  return (
    <EntityMovieGrid
      eyebrow="People"
      title={name}
      description={`Movies in the tracked catalog connected to ${name} as cast or director.`}
      browseParams={{ q: name }}
    />
  )
}
