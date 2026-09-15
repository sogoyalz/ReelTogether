import { EntityMovieGrid } from '@/components/discovery/EntityMovieGrid'

export default async function FranchisePage({ params }: { params: Promise<{ franchise: string }> }) {
  const franchise = decodeURIComponent((await params).franchise)
  return (
    <EntityMovieGrid
      eyebrow="Franchise"
      title={franchise}
      description={`Franchise view across current and upcoming titles tied to ${franchise}.`}
      browseParams={{ franchise }}
    />
  )
}
