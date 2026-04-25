import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'aiR Workspace',
  description: 'Grounded R Data Science Workbench',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
