export function MovieGridSkeleton({ title, count = 8, ranked = false }: { title: string; count?: number; ranked?: boolean }) {
  return <div aria-busy="true"><p role="status" className="meta">{title}</p><div className={ranked?'section-grid ranked-rail skeleton-grid':'section-grid skeleton-grid'} aria-hidden="true">{Array.from({length:count},(_,i)=><div className="skeleton-film" key={i}><div className="skeleton-art"/><span/><span/></div>)}</div></div>
}
