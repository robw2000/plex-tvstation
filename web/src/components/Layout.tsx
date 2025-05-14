import Link from 'next/link'
import { ReactNode } from 'react'

interface LayoutProps {
    children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
    return (
        <div className="min-h-screen bg-gradient-to-b from-primary-50 to-primary-100">
            <nav className="bg-white shadow-lg border-b border-primary-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex">
                            <div className="flex-shrink-0 flex items-center">
                                <Link href="/" className="text-xl font-bold text-primary-600 hover:text-primary-700 transition-colors">
                                    Plex TV Station
                                </Link>
                            </div>
                            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                                <Link href="/" className="nav-link inline-flex items-center px-1 pt-1 text-sm font-medium">
                                    Home
                                </Link>
                                <Link href="/library" className="nav-link inline-flex items-center px-1 pt-1 text-sm font-medium">
                                    Library
                                </Link>
                                <Link href="/tv-station" className="nav-link inline-flex items-center px-1 pt-1 text-sm font-medium">
                                    TV Station
                                </Link>
                                <Link href="/missing" className="nav-link inline-flex items-center px-1 pt-1 text-sm font-medium">
                                    Missing Content
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    {children}
                </div>
            </main>
        </div>
    )
} 