import { getMarkdownContent } from '@/utils/markdown'
import Layout from '@/components/Layout'
import MarkdownContent from '@/components/MarkdownContent'

export default async function LibraryPage() {
    const content = await getMarkdownContent('library-media.md')

    return (
        <Layout>
            <div className="space-y-6">
                <h1 className="text-3xl font-bold text-gray-900">Library Report</h1>
                <MarkdownContent content={content} />
            </div>
        </Layout>
    )
} 