import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NFS Index",
  description: "Track collector car prices",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}