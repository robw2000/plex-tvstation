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
- Automatically fetches missing movie years from OMDB API
- Configurable rewatch delay for both movies and TV shows
- Automatically marks content as unwatched after the rewatch delay period
- Groups movies by series (e.g., Star Wars, John Wick) to maintain chronological order

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
4. (Optional) Copy `local_config-example.json` to `local_config.json` and customize for your needs

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

# OMDB API configuration (optional)
omdb_api_key=                # Your OMDB API key (for fetching movie years)
omdb_api_url=http://www.omdbapi.com/  # OMDB API URL
```

#### Finding Your Plex API Token

1. Open the Plex web interface
2. Open your browser's developer tools (F12)
3. Look for the `X-Plex-Token` query parameter in any Plex request
4. Copy the token value to your `.env` file

### Local Configuration

Create a `local_config.json` file in the root directory to customize rewatch delays and metadata. You can use the provided `local_config-example.json` as a starting point:

```json
{
    "defaultRewatchDelayDays": {
        "movies": 180,
        "tv": 90
    },
    "excluded_slugs": ["example-series-1", "example-series-2"],
    "metadata": [
        {
            "slug": "movie-title",
            "title": "Movie Title",  # Optional: Alternative title to use for IMDB lookup
            "year": 1980,
            "rewatchDelayDays": 365
        }
    ],
    "restricted_play_months": {
        "december": ["christmas", "santa", "elf"],
        "october": ["halloween", "ghost", "vampire"]
    }
}
```

- `defaultRewatchDelayDays`: Default number of days before content is marked as unwatched
  - `movies`: Days for movies (default: 180)
  - `tv`: Days for TV shows (default: 90)
- `excluded_slugs`: Array of slugs to exclude from the playlist
- `metadata`: Array of metadata overrides
  - `slug`: The Plex slug for the content
  - `title`: (Optional) Alternative title to use for IMDB lookup if the Plex title doesn't match
  - `year`: The correct release year
  - `rewatchDelayDays`: Custom rewatch delay for this specific content
- `restricted_play_months`: Dictionary mapping months to movie slugs that should only play during that month
  - Keys are month names in lowercase (e.g., "december", "october")
  - Values are arrays of movie slugs that should only play during that month
  - Movies with matching slugs will be excluded from the playlist unless it's currently that month
  - This only affects movies, not TV shows

## Usage

Run the script:

```bash
python tvstation.py
```

Or specify a custom playlist name:

```bash
python tvstation.py -p "My Custom Playlist"
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
   - Excludes series where all episodes are watched (for the configured rewatch delay period)
4. For Movies:
   - Treats all movies as a single "series"
   - Adds unwatched movies to the playlist
   - Groups movies by series to maintain chronological order
   - If at least two-thirds of movies are marked as watched, watched movies will be marked as unwatched after the rewatch delay period
   - Uses OMDB API to fetch missing movie years
5. The playlist is updated with the new content order

## Troubleshooting

- If you see "Warning: Could not determine year for movie" messages, add the movie to `local_config.json` or provide an OMDB API key
- Ensure your Plex API token is correct and has the necessary permissions
- Check that your Plex server is accessible at the configured IP and port
- Verify that the user ID has access to the required libraries
- If the script is marking content as unwatched too frequently or not often enough, change the rewatch delay in `local_config.json` 