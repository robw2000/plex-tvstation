import { getMarkdownContent } from '@/utils/markdown'
import Layout from '@/components/Layout'
import MarkdownContent from '@/components/MarkdownContent'

export default async function MissingPage() {
    const content = await getMarkdownContent('missing-episodes.md')

    return (
        <Layout>
            <div className="space-y-6">
                <h1 className="text-3xl font-bold text-gray-900">Missing Content Report</h1>
                <MarkdownContent content={content} />
            </div>
        </Layout>
    )
} 