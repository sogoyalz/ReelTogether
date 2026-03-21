import { Suspense } from 'react'

import { SearchResults } from './search-results'

export default function SearchPage() {
  return (
    <Suspense fallback={<main className="page-shell"><p className="subtle">Loading search...</p></main>}>
      <SearchResults />
    </Suspense>
  )
}
