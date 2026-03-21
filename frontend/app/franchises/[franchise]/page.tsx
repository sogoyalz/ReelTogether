import { EntityMovieGrid } from '@/components/discovery/EntityMovieGrid'

export default function FranchisePage({ params }: { params: { franchise: string } }) {
  const franchise = decodeURIComponent(params.franchise)
  return (
    <EntityMovieGrid
      eyebrow="Franchise"
      title={franchise}
      description={`Franchise view across current and upcoming titles tied to ${franchise}.`}
      browseParams={{ franchise }}
    />
  )
}
