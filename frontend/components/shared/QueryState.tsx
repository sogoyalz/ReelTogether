'use client'

export function LoadingState({
  title = 'Loading',
  description = 'Fetching the latest data for this section.',
}: {
  title?: string
  description?: string
}) {
  return (
    <div className="panel empty-state" role="status">
      <h3>{title}</h3>
      <p className="subtle">{description}</p>
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'This section could not be loaded right now.',
  onRetry,
}: { title?: string; description?: string; onRetry?: () => void }) {
  return <div className="panel empty-state" role="alert">
    <h3>{title}</h3><p className="subtle">{description}</p>
    {onRetry && <button className="cta-button secondary-button" onClick={onRetry}>Try again</button>}
  </div>
}

export function EmptyState({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="panel empty-state">
      <h3>{title}</h3>
      <p className="subtle">{description}</p>
    </div>
  )
}
