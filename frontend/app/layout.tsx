import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Manavrachna University Assistant',
  description: 'Chat with our college assistant',
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