# Plex TV Station

> **Note**: This documentation was written by Cursor AI and may contain mistakes or inaccuracies. Please verify any information before proceeding.

This repository contains two main scripts:

1. **tvstation.py**: Automatically generates a playlist in Plex that includes all unwatched movies and TV shows, starting with the next unwatched episode of each series or movie.
2. **media_library_analyzer.py**: Analyzes your local media library and compares it with online databases to identify missing episodes and movies.

## tvstation.py Features

- Creates a playlist with unwatched movies and TV shows
- Starts with the next unwatched episode of each series
- Alternates between series when adding episodes to the playlist
- Automatically excludes series when all episodes are watched (for the configured rewatch delay period)
- Handles movies as a special "series" type
- Maintains consistent ordering using internal Plex rating keys
- Supports metadata overrides for movies with missing information
- Automatically fetches missing movie years from OMDB API
- Configurable rewatch delay for both movies and TV shows
- Automatically marks content as unwatched after the rewatch delay period
- Groups movies by series (e.g., Star Wars, John Wick) to maintain chronological order
- Supports seasonal content restrictions (e.g., Christmas movies only in December)
- Comprehensive logging system that tracks all operations
- Automatically marks watched content as unwatched when unwatched content falls below 33%

## media_library_analyzer.py Features

- Scans your local TV show and movie directories
- Compares local content with OMDB database to identify missing episodes
- Generates a detailed markdown report of missing content
- Provides a summary of missing episodes and movies
- Automatically cleans up old log files
- Helps identify incomplete TV show seasons and missing movies

## Requirements

- Python 3.x
- Plex Media Server
- Required Python packages (install using `pip install -r requirements.txt`):
  - requests
  - python-dotenv
  - tabulate (for media_library_analyzer.py)

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

# Media library paths (for media_library_analyzer.py)
tv_shows_path=/mnt/g/plex/TV Shows  # Path to your TV shows directory
movies_path=/mnt/g/plex/Movies      # Path to your movies directory
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
    "defaultRewatchDelay": {
        "movies": "180 days",
        "tv": "90 days"
    },
    "excluded_slugs": ["example-series-1", "example-series-2"],
    "metadata": [
        {
            "slug": "movie-title",
            "title": "Movie Title",  # Optional: Alternative title to use for IMDB lookup
            "year": 1980,
            "rewatchDelay": "1 year"
        }
    ],
    "movie_series_slugs": ["star-wars", "john-wick", "indiana-jones"],
    "restricted_play_months": {
        "december": ["christmas", "santa", "elf"],
        "october": ["halloween", "ghost", "vampire"]
    }
}
```

- `defaultRewatchDelay`: Default duration before content is marked as unwatched
  - `movies`: Duration for movies (default: "180 days")
  - `tv`: Duration for TV shows (default: "90 days")
  - Values can be specified as integers (for backward compatibility) or strings in the format "{number} {unit}" where unit is one of: day, days, month, months, year, years
  - Examples: "7 days", "1 month", "1 year", "3 years"
  - If an invalid format is provided, it will default to "1 year"
- `excluded_slugs`: Array of slugs to exclude from the playlist
- `metadata`: Array of metadata overrides
  - `slug`: The Plex slug for the content
  - `title`: (Optional) Alternative title to use for IMDB lookup if the Plex title doesn't match
  - `year`: The correct release year
  - `rewatchDelay`: Custom rewatch delay for this specific content (same format as defaultRewatchDelay)
- `movie_series_slugs`: Array of movie series slugs to group together chronologically
- `restricted_play_months`: Dictionary mapping months to movie slugs that should only play during that month
  - Keys are month names in lowercase (e.g., "december", "october")
  - Values are arrays of movie slugs that should only play during that month
  - Movies with matching slugs will be excluded from the playlist unless it's currently that month
  - This only affects movies, not TV shows

## Usage

### tvstation.py

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
5. Log to both the console and a log file in the `logs` directory

### media_library_analyzer.py

Run the script:

```bash
python media_library_analyzer.py
```

The script will:
1. Scan your local TV show and movie directories
2. Compare with OMDB database to identify missing episodes
3. Generate a markdown report in the `logs` directory

### cleanup_logs.py

Run the script:

```bash
python cleanup_logs.py
```

The script will:
1. Delete log files older than 3 days from the `logs` directory
2. Log its execution to `cron.log`
3. Create the `logs` directory if it doesn't exist

## How tvstation.py Works

1. The script connects to your Plex server using the provided credentials
2. It scans both your Movies and TV Shows libraries
3. For TV Shows:
   - Identifies the next unwatched episode for each series
   - Alternates between series when building the playlist
   - Excludes series where all episodes are watched (for the configured rewatch delay period)
   - Automatically marks all episodes as unwatched after the rewatch delay period
4. For Movies:
   - Treats all movies as a single "series"
   - Adds unwatched movies to the playlist
   - Groups movies by series to maintain chronological order
   - If at least two-thirds of movies are marked as watched, watched movies will be marked as unwatched after the rewatch delay period
   - Uses OMDB API to fetch missing movie years
   - Applies seasonal restrictions based on the current month
5. The playlist is updated with the new content order
6. Messages are logged to both the console and a log file

## How media_library_analyzer.py Works

1. The script scans your local TV show and movie directories
2. For TV Shows:
   - Identifies all seasons and episodes in your local library
   - Queries OMDB API to get information about each show
   - Compares local episodes with OMDB data to identify missing episodes
3. For Movies:
   - Checks for empty folders or folders without MKV files
4. Generates a detailed markdown report with:
   - A table of all missing episodes and movies
   - A summary section organized by show
   - Information about missing seasons and individual episodes
5. Cleans up old log files to prevent accumulation

## Logging

Both scripts maintain comprehensive logging systems:
- Logs are stored in the `logs` directory
- tvstation.py creates a new log file named `tvstation.log` for each run
- media_library_analyzer.py creates a markdown report named `missing_episodes.md`
- Logs include timestamps for all operations
- Both console output and file logging are synchronized
- Logs track playlist creation, content marking, and any errors or warnings

## Troubleshooting

- If you see "Warning: Could not determine year for movie" messages, add the movie to `local_config.json` or provide an OMDB API key
- Ensure your Plex API token is correct and has the necessary permissions
- Check that your Plex server is accessible at the configured IP and port
- Verify that the user ID has access to the required libraries
- If the script is marking content as unwatched too frequently or not often enough, change the rewatch delay in `local_config.json`
- Check the log files in the `logs` directory for detailed information about script execution
- If seasonal content isn't appearing when expected, verify the month names in `restricted_play_months` are lowercase
- For media_library_analyzer.py, ensure your TV show and movie paths are correctly set in the .env file 