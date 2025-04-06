# Plex Playlist Generator

> **Note**: This documentation was written by Cursor AI and may contain mistakes or inaccuracies. Please verify any information before proceeding.

This script automatically generates a playlist in Plex that includes all unwatched movies and TV shows, starting with the next unwatched episode of each series or movie. The playlist is rebuilt each time the script runs, ensuring it always reflects the current state of your library.

## Features

- Creates a playlist with unwatched movies and TV shows
- Starts with the next unwatched episode of each series
- Alternates between series when adding episodes to the playlist
- Automatically excludes series when all episodes are watched (for 90 days)
- Handles movies as a special "series" type
- Maintains consistent ordering using internal Plex rating keys
- Supports metadata overrides for movies with missing information

## Requirements

- Python 3.x
- Plex Media Server
- Required Python packages (install using `pip install -r requirements.txt`):
  - requests
  - python-dotenv

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and configure your environment variables
4. (Optional) Configure `missing_metadata.json` for movies with missing metadata

## Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Plex server configuration
plex_ip=192.168.1.196        # Your Plex server IP address
plex_port=32400              # Plex server port (default: 32400)
plex_api_token=              # Your Plex API token
user_id=1                    # Plex user ID (default: 1)
max_episodes=50              # Maximum number of episodes in playlist
playlist_name=My Favs TV     # Name of the playlist to create/update
excluded_slugs=              # Comma-separated list of slugs to exclude
```

#### Finding Your Plex API Token

1. Open the Plex web interface
2. Open your browser's developer tools (F12)
3. Look for the `X-Plex-Token` query parameter in any Plex request
4. Copy the token value to your `.env` file

### Missing Metadata Configuration

Some movies might have missing or incorrect metadata in Plex. You can override this information using the `missing_metadata.json` file:

```json
{
    "Movie Title": {
        "year": 1980,
        "slug": "movie-title"
    }
}
```

- `Movie Title`: The exact title as it appears in Plex
- `year`: The correct release year
- `slug`: The Plex slug for the movie (used for sorting)

## Usage

Run the script:

```bash
python robtv.py
```

The script will:
1. Connect to your Plex server
2. Scan your library for unwatched content
3. Create or update the specified playlist
4. Add unwatched episodes and movies in the configured order

## How It Works

1. The script connects to your Plex server using the provided credentials
2. It scans both your Movies and TV Shows libraries
3. For TV Shows:
   - Identifies the next unwatched episode for each series
   - Alternates between series when building the playlist
   - Excludes series where all episodes are watched (for 90 days)
4. For Movies:
   - Treats all movies as a single "series"
   - Adds unwatched movies to the playlist
   - Uses the `missing_metadata.json` file to correct any missing information
5. The playlist is updated with the new content order

## Troubleshooting

- If you see "Error: Movie with no year" messages, add the movie to `missing_metadata.json`
- Ensure your Plex API token is correct and has the necessary permissions
- Check that your Plex server is accessible at the configured IP and port
- Verify that the user ID has access to the required libraries 