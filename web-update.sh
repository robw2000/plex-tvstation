# Copy content to web
mkdir -p web/content

cp logs/tv-station.md web/content/tv-station.md
cp logs/library-media.md web/content/library-media.md
cp logs/missing-episodes.md web/content/missing-episodes.md

# Commit and push
git stash
git add web/content
git commit -m "Update web content"
git push
git stash apply
