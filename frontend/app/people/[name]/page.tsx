import { EntityMovieGrid } from '@/components/discovery/EntityMovieGrid'

export default function PersonPage({ params }: { params: { name: string } }) {
  const name = decodeURIComponent(params.name)
  return (
    <EntityMovieGrid
      eyebrow="People"
      title={name}
      description={`Movies in the tracked catalog connected to ${name} as cast or director.`}
      browseParams={{ q: name }}
    />
  )
}
