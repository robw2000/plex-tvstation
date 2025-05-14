import { getMarkdownContent } from '@/utils/markdown'
import Layout from '@/components/Layout'
import MarkdownContent from '@/components/MarkdownContent'

export default async function TVStationPage() {
    const content = await getMarkdownContent('tv-station.md')

    return (
        <Layout>
            <div className="space-y-6">
                <h1 className="text-3xl font-bold text-gray-900">TV Station Report</h1>
                <MarkdownContent content={content} />
            </div>
        </Layout>
    )
} 