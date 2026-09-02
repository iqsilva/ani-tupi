# ani-tupi justfile - Common development tasks

push:
  git pull --rebase && git push

# Run the API server
@serve:
    uv run ani-tupi

# Clear anime search cache (query cache only)
@clear-search-cache:
    rm -rf ~/.local/state/ani-tupi/cache
    echo "✅ Search cache cleared!"

# Clear anime search cache (query cache and episode cache)
@clear-cache:
    just clear-search-cache
    uv run python -c "from utils.cache_manager import clear_cache_all; from utils.scraper_cache import clear_cache; clear_cache_all(); clear_cache(); print('✅ Episode cache cleared!')"

# Clear entire cache directory (also clears state)
@clear-cache-full:
    rm -rf ~/.cache/ani-tugo
    rm -rf ~/.local/state/ani-tupi/cache
    echo "✅ Full cache directory removed!"

# Clear watch history
@clear-history:
    rm -f ~/.local/state/ani-tupi/history.json
    echo "✅ Watch history cleared!"

# Clear everything (cache + history)
@clear-all:
    just clear-cache-full
    just clear-history

# Run tests
@test:
    uv run pytest

# Install Scrapling browser dependencies (needed for dynamic scrapers)
@scrapling-install:
    uv run scrapling install

# Run linter
@lint:
    uv run ruff check .

# Format code
@format:
    uv run ruff format .

# Show help
@help:
    just --list
