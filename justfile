# ani-tupi justfile - Common development tasks

# Run ani-tupi with query
@query query:
    uv run ani-tupi --query "{{query}}"

# Run ani-tupi anilist menu
@anilist:
    uv run ani-tupi anilist

# Run ani-tupi with continue watching
@continue:
    uv run ani-tupi --continue-watching

# Clear anime search cache (query cache and episode cache)
@clear-cache:
    uv run ani-tupi --clear-cache
    uv run scripts/clean_caches.py

# Clear entire cache directory (also clears state)
@clear-cache-full:
    rm -rf ~/.cache/ani-tugo
    rm -rf ~/.local/state/ani-tupi/cache
    echo "✅ Full cache directory removed!"

# Run tests
@test:
    uv run pytest

# Run linter
@lint:
    uv run ruff check .

# Format code
@format:
    uv run ruff format .

# Build standalone executable
@build:
    uv run build.py
    echo "✅ Built: dist/ani-tupi"

# Install as global CLI
@install:
    python3 install-cli.py

# Show help
@help:
    just --list
