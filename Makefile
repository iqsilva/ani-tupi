.PHONY: help clean test lint format

help:
	@echo "ani-tupi development commands:"
	@echo ""
	@echo "  make clean          Clean all caches (SQLite, JSON)"
	@echo "  make test           Run all tests"
	@echo "  make lint           Run linters (ruff check)"
	@echo "  make format         Format code with ruff"
	@echo ""
	@echo "UV commands:"
	@echo "  uv sync             Install dependencies"
	@echo "  uv run ani-tupi --query \"anime name\"  Run anime search"
	@echo "  uv run manga_tupi --query \"manga name\" Run manga search"

clean:
	@echo "🧹 Cleaning caches..."
	@uv run scripts/clean_caches.py

test:
	@echo "🧪 Running tests..."
	@uv run pytest -v

lint:
	@echo "🔍 Linting code..."
	@uv run ruff check .

format:
	@echo "📝 Formatting code..."
	@uv run ruff format .
