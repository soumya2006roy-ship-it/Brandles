import { SiteFooter, SiteHeader } from "@/app/ui";

export default function MarketingLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <><a className="skip-link" href="#main-content">Skip to content</a><SiteHeader/><div id="main-content" className="site-content">{children}</div><SiteFooter/></>;
}
