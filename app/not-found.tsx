import Link from "next/link";

export default function NotFound() {
  return <main className="not-found"><div className="wrap"><p className="eyebrow">404 · Nothing here</p><h1>This page isn’t<br/><em>in the campaign.</em></h1><p>The page may have moved, or the address may be incomplete.</p><div className="actions"><Link className="button button-primary" href="/">Back to BrandLens <span aria-hidden="true">↗</span></Link><Link className="text-link" href="/features">Explore the innovations →</Link></div></div></main>;
}
