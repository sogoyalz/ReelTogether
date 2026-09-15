export function Pagination({ page, totalPages, onChange }: {
  page: number; totalPages: number; onChange: (page: number) => void
}) {
  if (totalPages <= 1) return null
  return <nav aria-label="Movie result pages" className="hero-actions" style={{ marginTop: 24 }}>
    <button className="cta-button secondary-button" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
    <span aria-live="polite">Page {page} of {totalPages}</span>
    <button className="cta-button secondary-button" disabled={page >= totalPages} onClick={() => onChange(page + 1)}>Next</button>
  </nav>
}
