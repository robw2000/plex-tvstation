import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownContentProps {
    content: string
}

export default function MarkdownContent({ content }: MarkdownContentProps) {
    return (
        <div className="prose prose-lg max-w-none">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    table: ({ children }) => (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                {children}
                            </table>
                        </div>
                    ),
                    th: ({ children }) => (
                        <th className="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            {children}
                        </th>
                    ),
                    td: ({ children }) => (
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {children}
                        </td>
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    )
} 