import { ProductShell } from "@/app/app/product-shell";

export const metadata = { title: "Workspace", robots: { index: false, follow: false } };

export default function ProductLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <ProductShell>{children}</ProductShell>;
}
