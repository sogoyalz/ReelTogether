import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'

export function SectionHeading({ number, eyebrow, title, description, href, action }: { number?: string; eyebrow?: string; title: string; description?: string; href?: string; action?: string }) {
  return <div className="section-header editorial-heading"><div>{eyebrow && <span className="eyebrow">{number && <span className="section-number">{number}</span>}{eyebrow}</span>}<h2>{title}</h2>{description && <p>{description}</p>}</div>{href && <Link className="text-action" href={href}>{action ?? 'Explore'}<ArrowUpRight size={16} /></Link>}</div>
}
