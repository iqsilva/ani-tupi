#!/usr/bin/env python3
"""
Test if AnimesDigital plugin is integrated with ani-tupi pipeline.

Run with:
  uv run test_plugin_integration.py
"""

from scrapers.loader import load_plugins
from services.repository import Repository

# Get repo
repo = Repository()

print("=" * 70)
print("Plugin Integration Test")
print("=" * 70)

# Load all plugins (pt-br)
print("\nLoading plugins for pt-br...")
load_plugins({'pt-br'})

# Check what got loaded
sources = repo.get_active_sources()
print(f"\n✓ Loaded {len(sources)} plugin(s):\n")

for source in sources:
    print(f"  ✓ {source}")
    if source == "animesdigital":
        print("    ↳ Status: ✅ INTEGRATED")

# Verify AnimesDigital is in the list
if "animesdigital" in sources:
    print("\n" + "=" * 70)
    print("SUCCESS: AnimesDigital plugin is integrated!")
    print("=" * 70)
    print("""
The plugin will be used automatically when:
1. User searches for anime: ani-tupi --query "..."
2. User continues watching
3. Multiple sources are queried in parallel

No additional configuration needed - it's ready to use!
""")
else:
    print("\n⚠ AnimesDigital plugin not found in loaded plugins")
    print("Possible issues:")
    print("  - File not in scrapers/plugins/")
    print("  - Language mismatch")
    print("  - Plugin import error")
