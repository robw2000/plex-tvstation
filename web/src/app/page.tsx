import { getMarkdownContent, extractSummarySection, extractTableHeaders, extractStorageStats } from '@/utils/markdown'
import Layout from '@/components/Layout'
import MarkdownContent from '@/components/MarkdownContent'

export default async function Home() {
    const libraryContent = await getMarkdownContent('src/content/library/library-media.md')
    const tvStationContent = await getMarkdownContent('src/content/tv-station/tv-station.md')
    const missingContent = await getMarkdownContent('src/content/missing/missing-episodes.md')

    const libraryStats = extractStorageStats(libraryContent)
    const tvStationSummary = extractSummarySection(tvStationContent)
    const missingSummary = extractSummarySection(missingContent)

    const libraryHeaders = extractTableHeaders(libraryContent)

    return (
        <Layout>
            <div className="space-y-8">
                <h1 className="text-3xl font-bold text-primary-700">Plex TV Station Dashboard</h1>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div className="card p-6 bg-gradient-to-br from-primary-50 to-white">
                        <h2 className="text-xl font-semibold mb-4 text-primary-600">Library Overview</h2>
                        <div className="markdown-content">
                            <MarkdownContent content={libraryStats} />
                        </div>
                    </div>

                    <div className="card p-6 bg-gradient-to-br from-secondary-50 to-white">
                        <h2 className="text-xl font-semibold mb-4 text-secondary-600">TV Station Status</h2>
                        <div className="markdown-content">
                            <MarkdownContent content={tvStationSummary} />
                        </div>
                    </div>

                    <div className="card p-6 bg-gradient-to-br from-accent-50 to-white">
                        <h2 className="text-xl font-semibold mb-4 text-accent-600">Missing Content</h2>
                        <div className="markdown-content">
                            <MarkdownContent content={missingSummary} />
                        </div>
                    </div>
                </div>

                <div className="card p-6 bg-gradient-to-br from-primary-50 to-white">
                    <h2 className="text-xl font-semibold mb-4 text-primary-600">Library Report Sections</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {libraryHeaders.map((header, index) => (
                            <div key={index} className="p-4 bg-white rounded-lg shadow-sm border border-primary-100 hover:border-primary-300 transition-colors">
                                <h3 className="font-medium text-primary-700">{header}</h3>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </Layout>
    )
} 