import fs from 'fs'
import path from 'path'

export async function getMarkdownContent(filename: string): Promise<string> {
	const filePath = path.join(process.cwd(), 'content', filename)
	try {
		const content = await fs.promises.readFile(filePath, 'utf8')
		return content
	} catch (error) {
		console.error(`Error reading markdown file ${filename}:`, error)
		return ''
	}
}

export function extractSummary(content: string): string {
	// Extract the first paragraph or section after the title
	const lines = content.split('\n')
	const summaryLines: string[] = []
	let foundContent = false

	for (const line of lines) {
		if (line.startsWith('# ')) {
			foundContent = true
			continue
		}
		if (foundContent && line.trim() !== '') {
			summaryLines.push(line)
			if (line.trim().endsWith('.')) {
				break
			}
		}
	}

	return summaryLines.join(' ')
}

export function extractTableHeaders(content: string): string[] {
	const lines = content.split('\n')
	const headers: string[] = []
	let inTable = false

	for (const line of lines) {
		if (line.startsWith('|')) {
			if (!inTable) {
				inTable = true
				const headerCells = line
					.split('|')
					.filter(cell => cell.trim() !== '')
					.map(cell => cell.trim())
				headers.push(...headerCells)
			}
		} else if (inTable && !line.startsWith('|')) {
			break
		}
	}

	return headers
}

export function extractSummarySection(content: string): string {
	const lines = content.split('\n')
	const summaryLines: string[] = []
	let inSummary = false

	for (const line of lines) {
		if (line.startsWith('## Summary')) {
			inSummary = true
			continue
		}
		if (inSummary) {
			if (line.startsWith('##')) {
				break
			}
			if (line.trim() !== '') {
				summaryLines.push(line)
			}
		}
	}

	return summaryLines.join('\n')
}

export function extractStorageStats(content: string): string {
	const lines = content.split('\n')
	const statsLines: string[] = []
	let inStats = false

	for (const line of lines) {
		if (line.startsWith('## Storage Statistics')) {
			inStats = true
			statsLines.push(line)
			continue
		}
		if (inStats) {
			if (line.startsWith('##')) {
				break
			}
			if (line.trim() !== '') {
				statsLines.push(line)
			}
		}
	}

	return statsLines.join('\n')
} 