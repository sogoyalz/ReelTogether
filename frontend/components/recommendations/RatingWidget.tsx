'use client'

export function RatingWidget({ compact = false }: { movieId: number; compact?: boolean }) {
  return (
    <div className={compact ? 'rating-widget rating-widget-compact' : 'panel'} style={{ marginTop: compact ? 12 : 18 }}>
      <p className="meta" style={{ margin: 0 }}>
        Ratings are disabled in the simplified frontend.
      </p>
    </div>
  )
}
