#!/usr/bin/env python3
"""
Convert markdown files to HTML for the static website.
"""

import re
import sys
import os
from pathlib import Path


def escape_html(text):
	"""Escape HTML special characters."""
	return (text
		.replace('&', '&amp;')
		.replace('<', '&lt;')
		.replace('>', '&gt;')
		.replace('"', '&quot;')
		.replace("'", '&#39;'))


def parse_inline_formatting(text):
	"""Parse inline formatting like **bold** and *italic*."""
	# Bold: **text** or __text__
	text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
	text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
	# Italic: *text* or _text_
	text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
	text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<em>\1</em>', text)
	# Code: `text`
	text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
	return text


def parse_table(lines):
	"""Parse a markdown table."""
	if not lines or not lines[0].strip().startswith('|'):
		return None, lines
	
	table_lines = []
	remaining_lines = lines
	
	# Collect all table rows
	for i, line in enumerate(lines):
		if line.strip().startswith('|'):
			table_lines.append(line)
		else:
			remaining_lines = lines[i:]
			break
	
	if len(table_lines) < 2:
		return None, lines
	
	# Parse header
	header_line = table_lines[0]
	headers = [cell.strip() for cell in header_line.split('|')[1:-1]]
	
	# Skip separator line (second line)
	# Parse data rows
	rows = []
	for row_line in table_lines[2:]:
		cells = [cell.strip() for cell in row_line.split('|')[1:-1]]
		if cells:
			rows.append(cells)
	
	# Build HTML table
	html = ['<div class="table-container">', '<table class="sortable-table">', '<thead>', '<tr>']
	for header in headers:
		html.append(f'<th class="sortable-header" data-column="{len([h for h in headers if headers.index(h) < headers.index(header)])}">{parse_inline_formatting(escape_html(header))} <span class="sort-indicator"></span></th>')
	html.extend(['</tr>', '</thead>', '<tbody>'])
	
	for row in rows:
		html.append('<tr>')
		for i, cell in enumerate(row):
			# Check if header row was left-aligned (starts with :)
			align = ''
			if i < len(headers) and table_lines[1] if len(table_lines) > 1 else '':
				sep_line = table_lines[1]
				sep_cells = sep_line.split('|')[1:-1]
				if i < len(sep_cells) and sep_cells[i].strip().startswith(':'):
					align = ' style="text-align: left;"'
			html.append(f'<td{align}>{parse_inline_formatting(escape_html(cell))}</td>')
		html.append('</tr>')
	
	html.extend(['</tbody>', '</table>', '</div>'])
	return '\n'.join(html), remaining_lines


def markdown_to_html(markdown_text):
	"""Convert markdown text to HTML."""
	lines = markdown_text.split('\n')
	html_parts = []
	i = 0
	
	while i < len(lines):
		line = lines[i]
		strip_line = line.strip()
		
		# Empty line
		if not strip_line:
			html_parts.append('<p></p>')
			i += 1
			continue
		
		# Headers
		if strip_line.startswith('#'):
			level = len(strip_line) - len(strip_line.lstrip('#'))
			text = strip_line.lstrip('#').strip()
			if level <= 6:
				html_parts.append(f'<h{level}>{parse_inline_formatting(escape_html(text))}</h{level}>')
			i += 1
			continue
		
		# Horizontal rule
		if strip_line in ('---', '***', '___'):
			html_parts.append('<hr>')
			i += 1
			continue
		
		# Table
		if strip_line.startswith('|'):
			table_html, remaining = parse_table(lines[i:])
			if table_html:
				html_parts.append(table_html)
				i += len(lines[i:]) - len(remaining)
				continue
		
		# Unordered list
		if strip_line.startswith('- ') or strip_line.startswith('* '):
			html_parts.append('<ul>')
			while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
				item_text = lines[i].strip()[2:].strip()
				html_parts.append(f'<li>{parse_inline_formatting(escape_html(item_text))}</li>')
				i += 1
			html_parts.append('</ul>')
			continue
		
		# Ordered list
		if re.match(r'^\d+\.\s', strip_line):
			html_parts.append('<ol>')
			while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
				item_text = re.sub(r'^\d+\.\s', '', lines[i].strip())
				html_parts.append(f'<li>{parse_inline_formatting(escape_html(item_text))}</li>')
				i += 1
			html_parts.append('</ol>')
			continue
		
		# Regular paragraph
		paragraph_lines = []
		while i < len(lines) and lines[i].strip() and not (
			lines[i].strip().startswith('#') or
			lines[i].strip().startswith('- ') or
			lines[i].strip().startswith('* ') or
			lines[i].strip().startswith('|') or
			re.match(r'^\d+\.\s', lines[i].strip()) or
			lines[i].strip() in ('---', '***', '___')
		):
			paragraph_lines.append(lines[i])
			i += 1
		
		if paragraph_lines:
			paragraph_text = ' '.join(paragraph_lines).strip()
			if paragraph_text:
				html_parts.append(f'<p>{parse_inline_formatting(escape_html(paragraph_text))}</p>')
			continue
		
		i += 1
	
	return '\n'.join(html_parts)


def generate_html_page(title, content_html, current_page):
	"""Generate a complete HTML page."""
	nav_items = [
		('index.html', 'Home', current_page == 'index'),
		('movies.html', 'Movies', current_page == 'movies'),
		('tv.html', 'TV Shows', current_page == 'tv'),
		('movie-wishlist.html', 'Movie Wishlist', current_page == 'movie-wishlist'),
		('tv-wishlist.html', 'TV Wishlist', current_page == 'tv-wishlist'),
		('missing-episodes.html', 'Missing Episodes', current_page == 'missing-episodes'),
	]
	
	nav_html = '<nav><ul>'
	for href, label, is_active in nav_items:
		active_class = ' class="active"' if is_active else ''
		nav_html += f'<li><a href="{href}"{active_class}>{label}</a></li>'
	nav_html += '</ul></nav>'
	
	# Add search field and JavaScript for movies, TV, and wishlist pages
	javascript = ''
	if current_page in ('movies', 'tv', 'movie-wishlist', 'tv-wishlist'):
		# Insert search field and genre filter before the first table
		search_field = '''<div class="filter-container">
		<input type="text" id="search-input" placeholder="Search..." autocomplete="off">
		<select id="genre-filter">
			<option value="">Filter Genre</option>
		</select>
	</div>'''
		# Find the first table-container and insert search before it
		if '<div class="table-container">' in content_html:
			content_html = content_html.replace('<div class="table-container">', search_field + '\n\t\t<div class="table-container">', 1)
		javascript = '''<script>
(function() {
	const table = document.querySelector('.sortable-table');
	if (!table) return;
	
	const tbody = table.querySelector('tbody');
	const headers = Array.from(table.querySelectorAll('.sortable-header'));
	let currentSort = { column: 0, direction: 'asc' };
	
	// Function to get current rows from DOM
	function getRows() {
		return Array.from(tbody.querySelectorAll('tr'));
	}
	
	// Remove "a" or "the" from beginning of title for sorting
	function getSortKey(text) {
		if (!text) return '';
		const lower = text.toLowerCase().trim();
		if (lower.startsWith('the ')) {
			return lower.substring(4);
		} else if (lower.startsWith('a ')) {
			return lower.substring(2);
		}
		return lower;
	}
	
	// Parse value for sorting
	function parseValue(cellText, columnIndex) {
		const text = cellText.trim();
		
		// For title column, use sort key
		if (columnIndex === 0) {
			return getSortKey(text);
		}
		
		// For size columns (GB, TB, MB, etc.) - check BEFORE numeric to avoid false matches
		const sizeMatch = text.match(/([\\d.]+)\\s*(TB|GB|MB|KB|B)/i);
		if (sizeMatch) {
			const value = parseFloat(sizeMatch[1]);
			const unit = sizeMatch[2].toUpperCase();
			const multipliers = { 'B': 1, 'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024, 'TB': 1024*1024*1024*1024 };
			return value * (multipliers[unit] || 1);
		}
		
		// For percentage columns
		const pctMatch = text.match(/([\\d.]+)%/);
		if (pctMatch) {
			return parseFloat(pctMatch[1]);
		}
		
		// For numeric columns (Year, Episodes, etc.) - check AFTER size to avoid false matches
		const numMatch = text.match(/^\\d+/);
		if (numMatch) {
			return parseFloat(numMatch[0]);
		}
		
		// For Yes/No columns
		if (text.toLowerCase() === 'yes') return 1;
		if (text.toLowerCase() === 'no') return 0;
		
		// Default: string comparison
		return text.toLowerCase();
	}
	
	// Sort rows
	function sortTable(columnIndex, direction) {
		const currentRows = getRows();
		const sortedRows = currentRows.slice().sort((a, b) => {
			const aCells = a.querySelectorAll('td');
			const bCells = b.querySelectorAll('td');
			
			if (columnIndex >= aCells.length || columnIndex >= bCells.length) {
				return 0;
			}
			
			const aVal = parseValue(aCells[columnIndex].textContent, columnIndex);
			const bVal = parseValue(bCells[columnIndex].textContent, columnIndex);
			
			let comparison = 0;
			if (typeof aVal === 'number' && typeof bVal === 'number') {
				comparison = aVal - bVal;
			} else {
				comparison = String(aVal).localeCompare(String(bVal));
			}
			
			return direction === 'asc' ? comparison : -comparison;
		});
		
		// Clear tbody and add sorted rows
		tbody.innerHTML = '';
		sortedRows.forEach(row => tbody.appendChild(row));
		
		// Update sort indicators
		headers.forEach((header, idx) => {
			const indicator = header.querySelector('.sort-indicator');
			if (idx === columnIndex) {
				indicator.textContent = direction === 'asc' ? ' ▲' : ' ▼';
				header.classList.add('sorted');
			} else {
				indicator.textContent = '';
				header.classList.remove('sorted');
			}
		});
		
		currentSort = { column: columnIndex, direction: direction };
	}
	
	// Add click handlers to headers
	headers.forEach((header, index) => {
		header.style.cursor = 'pointer';
		header.addEventListener('click', () => {
			const newDirection = (currentSort.column === index && currentSort.direction === 'asc') ? 'desc' : 'asc';
			sortTable(index, newDirection);
		});
	});
	
	// Initial sort by title (column 0)
	sortTable(0, 'asc');
	
	// Extract genres and populate dropdown
	const genreFilter = document.getElementById('genre-filter');
	const allRows = getRows();
	const genresSet = new Set();
	
	// Find the genres column by looking for "Genres" in header text
	const headerCells = headers.length > 0 ? headers[0].parentElement.querySelectorAll('th') : [];
	let genresColumnIndex = -1;
	for (let i = 0; i < headerCells.length; i++) {
		if (headerCells[i].textContent.toLowerCase().includes('genre')) {
			genresColumnIndex = i;
			break;
		}
	}
	// Fallback to last column if not found
	if (genresColumnIndex === -1) {
		genresColumnIndex = headerCells.length - 1;
	}
	
	allRows.forEach(row => {
		if (row.parentElement === tbody) {
			const cells = row.querySelectorAll('td');
			if (cells[genresColumnIndex]) {
				const genresText = cells[genresColumnIndex].textContent;
				// Split by comma and add each genre
				genresText.split(',').forEach(genre => {
					const trimmed = genre.trim();
					if (trimmed) {
						genresSet.add(trimmed);
					}
				});
			}
		}
	});
	
	// Sort genres and add to dropdown
	const sortedGenres = Array.from(genresSet).sort();
	sortedGenres.forEach(genre => {
		const option = document.createElement('option');
		option.value = genre;
		option.textContent = genre;
		genreFilter.appendChild(option);
	});
	
	// Combined filter function
	function applyFilters() {
		const searchQuery = searchInput ? searchInput.value.trim().toLowerCase() : '';
		const selectedGenre = genreFilter ? genreFilter.value : '';
		
		const currentRows = getRows();
		currentRows.forEach(row => {
			if (row.parentElement === tbody) {
				const cells = row.querySelectorAll('td');
				let showRow = true;
				
				// Apply search filter (title and year only)
				if (searchQuery.length >= 2) {
					const searchText = (cells[0] ? cells[0].textContent.toLowerCase() : '') + ' ' + (cells[1] ? cells[1].textContent.toLowerCase() : '');
					if (!searchText.includes(searchQuery)) {
						showRow = false;
					}
				}
				
				// Apply genre filter
				if (selectedGenre && showRow) {
					const genresText = cells[genresColumnIndex] ? cells[genresColumnIndex].textContent : '';
					const genres = genresText.split(',').map(g => g.trim());
					if (!genres.includes(selectedGenre)) {
						showRow = false;
					}
				}
				
				row.style.display = showRow ? '' : 'none';
			}
		});
	}
	
	// Search functionality
	const searchInput = document.getElementById('search-input');
	if (searchInput) {
		let searchTimeout;
		searchInput.addEventListener('input', (e) => {
			clearTimeout(searchTimeout);
			searchTimeout = setTimeout(() => {
				applyFilters();
			}, 100);
		});
	}
	
	// Genre filter functionality
	if (genreFilter) {
		genreFilter.addEventListener('change', () => {
			applyFilters();
		});
	}
})();
</script>'''
	
	return f'''<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>{escape_html(title)}</title>
	<link rel="stylesheet" href="style.css">
</head>
<body>
	<header>
		<h1>Plex TV Station</h1>
		{nav_html}
	</header>
	<main>
		{content_html}
	</main>
	<footer>
		<p>Generated automatically from Plex library data</p>
	</footer>
	{javascript}
</body>
</html>'''


def filter_table_by_size(lines, size_column_index, exclude_zero=True):
	"""
	Filter a markdown table to exclude or include only zero-size rows.
	
	Args:
		lines: List of lines from markdown content
		size_column_index: Index of the file size column (0-based)
		exclude_zero: If True, exclude zero-size rows; if False, include only zero-size rows
	
	Returns:
		Filtered list of lines
	"""
	if not lines:
		return lines
	
	result = []
	i = 0
	
	while i < len(lines):
		line = lines[i]
		
		# Check if this is the start of a table
		if line.strip().startswith('|') and 'Title' in line:
			# Found table header - include it and separator
			result.append(line)
			i += 1
			
			# Find separator line
			if i < len(lines) and lines[i].strip().startswith('|'):
				result.append(lines[i])
				i += 1
			
			# Now filter data rows
			while i < len(lines) and lines[i].strip().startswith('|'):
				data_line = lines[i]
				cells = [cell.strip() for cell in data_line.split('|')[1:-1]]
				
				if len(cells) > size_column_index:
					size_str = cells[size_column_index].strip()
					# Check if size is zero (0.00 B, 0 B, etc.)
					is_zero = False
					if size_str.startswith('0'):
						# Parse the size value
						try:
							# Extract number part - match patterns like "0.00 B", "0 B", etc.
							size_match = re.match(r'([\d.]+)\s*(TB|GB|MB|KB|B)?', size_str, re.IGNORECASE)
							if size_match:
								size_value = float(size_match.group(1))
								if size_value == 0.0:
									is_zero = True
						except (ValueError, AttributeError):
							pass
					
					# Include or exclude based on filter
					if exclude_zero and not is_zero:
						result.append(data_line)
					elif not exclude_zero and is_zero:
						result.append(data_line)
				else:
					# Malformed row, include it anyway
					result.append(data_line)
				
				i += 1
		else:
			# Not a table line, include as-is
			result.append(line)
			i += 1
	
	return result


def split_library_media(md_content):
	"""Split library media markdown into movies and TV sections, and create wishlist pages."""
	lines = md_content.split('\n')
	
	# Find the header and generated date
	header_lines = []
	generated_line = None
	movies_start = None
	tv_start = None
	storage_start = None
	
	for i, line in enumerate(lines):
		if line.strip().startswith('# Plex Library Report'):
			header_lines.append(line)
		elif line.strip().startswith('Generated on:'):
			generated_line = line
		elif line.strip() == '## Movies':
			movies_start = i
		elif line.strip() == '## TV Shows':
			tv_start = i
		elif line.strip() == '## Storage Statistics':
			storage_start = i
			break
	
	# Extract movies section
	movies_content = []
	movies_wishlist_content = []
	
	if movies_start is not None:
		movies_content.append('# Plex Library Report')
		movies_content.append('')
		if generated_line:
			movies_content.append(generated_line)
			movies_content.append('')
		
		movies_wishlist_content.append('# Movie Wishlist')
		movies_wishlist_content.append('')
		if generated_line:
			movies_wishlist_content.append(generated_line)
			movies_wishlist_content.append('')
		movies_wishlist_content.append('This page shows movies that are represented by empty folders (zero file size).')
		movies_wishlist_content.append('')
		
		# Include everything from Movies to just before TV Shows
		end_idx = tv_start if tv_start is not None else storage_start if storage_start is not None else len(lines)
		movies_section_lines = lines[movies_start:end_idx]
		
		# Filter out zero-size movies from main page (size column is index 3: Title, Year, Watched, File Size, Genres)
		movies_content_lines = filter_table_by_size(movies_section_lines, 3, exclude_zero=True)
		movies_content.extend(movies_content_lines)
		
		# Create wishlist with only zero-size movies
		movies_wishlist_lines = filter_table_by_size(movies_section_lines, 3, exclude_zero=False)
		# Find where the table starts in the wishlist
		wishlist_table_start = None
		for i, line in enumerate(movies_wishlist_lines):
			if line.strip().startswith('|') and 'Title' in line:
				wishlist_table_start = i
				break
		if wishlist_table_start is not None:
			# Find where the table ends
			wishlist_table_end = wishlist_table_start + 1
			while wishlist_table_end < len(movies_wishlist_lines):
				if movies_wishlist_lines[wishlist_table_end].strip().startswith('|'):
					wishlist_table_end += 1
				else:
					break
			# Only include the table in wishlist
			if wishlist_table_end > wishlist_table_start + 2:  # At least header, separator, and one data row
				movies_wishlist_content.append('### Movie Wishlist')
				movies_wishlist_content.append('')
				# Include the filtered table
				movies_wishlist_content.extend(movies_wishlist_lines[wishlist_table_start:wishlist_table_end])
		
		# Add storage statistics related to movies
		if storage_start is not None:
			# Find where Combined Genre Statistics starts
			genre_start = None
			for i in range(storage_start, len(lines)):
				if lines[i].strip() == '## Combined Genre Statistics':
					genre_start = i
					break
			
			if genre_start:
				# Find "Top 10 Largest Movies" section
				movies_storage_lines = []
				in_movies_section = False
				for i in range(storage_start, genre_start):
					line = lines[i]
					if 'Top 10 Largest Movies' in line:
						in_movies_section = True
						movies_storage_lines.append(line)
					elif in_movies_section:
						# Stop when we hit the next ### section (TV Shows)
						if line.strip().startswith('###'):
							break
						movies_storage_lines.append(line)
				
				if movies_storage_lines:
					movies_content.append('')
					movies_content.append('## Storage Statistics')
					movies_content.append('')
					# Include the bullet point before Top 10 Largest Movies
					for i in range(storage_start, genre_start):
						if 'Top 10 Largest Movies' in lines[i]:
							# Include the line before (the bullet point)
							if i > storage_start:
								movies_content.append(lines[i-1])
							break
					movies_content.extend(movies_storage_lines)
	
	# Extract TV section
	tv_content = []
	tv_wishlist_content = []
	
	if tv_start is not None:
		tv_content.append('# Plex Library Report')
		tv_content.append('')
		if generated_line:
			tv_content.append(generated_line)
			tv_content.append('')
		
		tv_wishlist_content.append('# TV Wishlist')
		tv_wishlist_content.append('')
		if generated_line:
			tv_wishlist_content.append(generated_line)
			tv_wishlist_content.append('')
		tv_wishlist_content.append('This page shows TV shows that are represented by empty folders (zero file size).')
		tv_wishlist_content.append('')
		
		# Include everything from TV Shows to just before Storage Statistics
		end_idx = storage_start if storage_start is not None else len(lines)
		tv_section_lines = lines[tv_start:end_idx]
		
		# Filter out zero-size TV shows from main page (size column is index 4: Title, Episodes, Watched, % Watched, Total Size, Avg Episode Size, Genres)
		tv_content_lines = filter_table_by_size(tv_section_lines, 4, exclude_zero=True)
		tv_content.extend(tv_content_lines)
		
		# Create wishlist with only zero-size TV shows
		tv_wishlist_lines = filter_table_by_size(tv_section_lines, 4, exclude_zero=False)
		# Find where the table starts in the wishlist
		wishlist_table_start = None
		for i, line in enumerate(tv_wishlist_lines):
			if line.strip().startswith('|') and 'Title' in line:
				wishlist_table_start = i
				break
		if wishlist_table_start is not None:
			# Find where the table ends
			wishlist_table_end = wishlist_table_start + 1
			while wishlist_table_end < len(tv_wishlist_lines):
				if tv_wishlist_lines[wishlist_table_end].strip().startswith('|'):
					wishlist_table_end += 1
				else:
					break
			# Only include the table in wishlist
			if wishlist_table_end > wishlist_table_start + 2:  # At least header, separator, and one data row
				tv_wishlist_content.append('### TV Wishlist')
				tv_wishlist_content.append('')
				# Include the filtered table
				tv_wishlist_content.extend(tv_wishlist_lines[wishlist_table_start:wishlist_table_end])
		
		# Add storage statistics related to TV
		if storage_start is not None:
			# Find TV-related storage stats
			genre_start = None
			for i in range(storage_start, len(lines)):
				if lines[i].strip() == '## Combined Genre Statistics':
					genre_start = i
					break
			
			if genre_start:
				# Find "Top 10 TV Shows by Average Episode Size" section
				tv_storage_lines = []
				in_tv_section = False
				for i in range(storage_start, genre_start):
					line = lines[i]
					if 'TV Shows by Average Episode Size' in line:
						in_tv_section = True
					if in_tv_section:
						tv_storage_lines.append(line)
					elif line.strip().startswith('###') and in_tv_section:
						break
				
				if tv_storage_lines:
					tv_content.append('')
					tv_content.extend(tv_storage_lines)
	
	return '\n'.join(movies_content), '\n'.join(tv_content), '\n'.join(movies_wishlist_content), '\n'.join(tv_wishlist_content)


def main():
	"""Main function to convert markdown files to HTML."""
	script_dir = Path(__file__).parent
	project_root = script_dir.parent
	logs_dir = project_root / 'logs'
	web_dir = project_root / 'web'
	
	# Create web directory if it doesn't exist
	web_dir.mkdir(exist_ok=True)
	
	# Convert library-media.md into separate movies and TV pages
	library_media_md = logs_dir / 'library-media.md'
	if library_media_md.exists():
		with open(library_media_md, 'r', encoding='utf-8') as f:
			md_content = f.read()
		
		# Split into movies and TV sections, and create wishlists
		movies_md, tv_md, movies_wishlist_md, tv_wishlist_md = split_library_media(md_content)
		
		# Generate movies page
		if movies_md:
			html_content = markdown_to_html(movies_md)
			html_page = generate_html_page('Movies', html_content, 'movies')
			with open(web_dir / 'movies.html', 'w', encoding='utf-8') as f:
				f.write(html_page)
			print(f"Generated movies.html")
		
		# Generate TV page
		if tv_md:
			html_content = markdown_to_html(tv_md)
			html_page = generate_html_page('TV Shows', html_content, 'tv')
			with open(web_dir / 'tv.html', 'w', encoding='utf-8') as f:
				f.write(html_page)
			print(f"Generated tv.html")
		
		# Generate movie wishlist page
		if movies_wishlist_md and movies_wishlist_md.strip():
			html_content = markdown_to_html(movies_wishlist_md)
			html_page = generate_html_page('Movie Wishlist', html_content, 'movie-wishlist')
			with open(web_dir / 'movie-wishlist.html', 'w', encoding='utf-8') as f:
				f.write(html_page)
			print(f"Generated movie-wishlist.html")
		
		# Generate TV wishlist page
		if tv_wishlist_md and tv_wishlist_md.strip():
			html_content = markdown_to_html(tv_wishlist_md)
			html_page = generate_html_page('TV Wishlist', html_content, 'tv-wishlist')
			with open(web_dir / 'tv-wishlist.html', 'w', encoding='utf-8') as f:
				f.write(html_page)
			print(f"Generated tv-wishlist.html")
	else:
		print(f"Warning: {library_media_md} not found", file=sys.stderr)
	
	# Convert missing-episodes.md
	missing_episodes_md = logs_dir / 'missing-episodes.md'
	if missing_episodes_md.exists():
		with open(missing_episodes_md, 'r', encoding='utf-8') as f:
			md_content = f.read()
		html_content = markdown_to_html(md_content)
		html_page = generate_html_page('Missing Episodes', html_content, 'missing-episodes')
		with open(web_dir / 'missing-episodes.html', 'w', encoding='utf-8') as f:
			f.write(html_page)
		print(f"Generated missing-episodes.html")
	else:
		print(f"Warning: {missing_episodes_md} not found", file=sys.stderr)
	
	# Generate index.html
	index_content = '''<h2>Welcome</h2>
<p>This site displays information about your Plex media library.</p>
<ul>
	<li><a href="movies.html">Movies</a> - View your movie library</li>
	<li><a href="tv.html">TV Shows</a> - View your TV show library</li>
	<li><a href="movie-wishlist.html">Movie Wishlist</a> - Movies you want to get (empty folders)</li>
	<li><a href="tv-wishlist.html">TV Wishlist</a> - TV shows you want to get (empty folders)</li>
	<li><a href="missing-episodes.html">Missing Episodes</a> - View missing TV episodes and movies</li>
</ul>'''
	index_html = generate_html_page('Home', index_content, 'index')
	with open(web_dir / 'index.html', 'w', encoding='utf-8') as f:
		f.write(index_html)
	print(f"Generated index.html")


if __name__ == '__main__':
	main()
