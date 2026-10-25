import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import { DM_Sans, Instrument_Serif } from "next/font/google";
import { SiteFooter, SiteHeader, ToastProvider } from "@/app/ui";
import { SiteStructuredData } from "@/app/structured-data";
import { PrivacyConsentProvider } from "@/app/privacy-consent";
import { siteConfig } from "@/site.config";
import "./globals.css";

const sans = DM_Sans({ variable: "--font-sans", subsets: ["latin"] });
const display = Instrument_Serif({ variable: "--font-display", subsets: ["latin"], weight: "400" });

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.url),
  title: { default: "Brand governance for every channel", template: "%s | BrandLens" },
  description: siteConfig.description,
  alternates: { canonical: "/" },
  openGraph: { type: "website", siteName: siteConfig.name, title: "Brand governance for every channel", description: siteConfig.description, locale: "en_US", url: "/", images: ["/opengraph-image"] },
  twitter: { card: "summary_large_image", title: "Brand governance for every channel", description: siteConfig.description, images: ["/opengraph-image"] },
  icons: { icon: [{ url: "/icon.svg", type: "image/svg+xml" }, { url: "/favicon.ico" }], apple: "/apple-touch-icon.png" },
};

export const viewport: Viewport = { colorScheme: "light dark", themeColor: [{ media: "(prefers-color-scheme: light)", color: "#f7f5ef" }, { media: "(prefers-color-scheme: dark)", color: "#171a18" }] };

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  await headers();
  return <html lang="en" suppressHydrationWarning className={`${sans.variable} ${display.variable}`}><body><SiteStructuredData/><PrivacyConsentProvider><ToastProvider><a className="skip-link" href="#main-content">Skip to content</a><SiteHeader/><div id="main-content" className="site-content">{children}</div><SiteFooter/></ToastProvider></PrivacyConsentProvider></body></html>;
}
