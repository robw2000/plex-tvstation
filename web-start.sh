#!/bin/bash
# Start a local web server to host the static website

cd "$HOME/repos/plex-tvstation" || exit 1

PORT=${1:-8000}

echo "Starting web server on port $PORT..."
echo "Open http://localhost:$PORT in your browser"
echo "Press Ctrl+C to stop the server"
echo ""

cd web
python3 -m http.server "$PORT"
