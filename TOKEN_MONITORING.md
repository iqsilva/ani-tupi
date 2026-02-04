# AnimesDigital API Token Monitoring Guide

## Objective

Test whether the API token (`c1deb78cd4`) is **permanent** or **temporary** (expires after X days/weeks).

## Current Token Info

```
Token: c1deb78cd4
First Used: 2026-02-04
Status: ACTIVE ✅
```

## What to Monitor

### 1. Log Errors

Watch for HTTP errors when searching:

```bash
# Run with debug logging
uv run ani-tupi --query "test" --log-level debug

# Look for errors like:
# ❌ AnimesDigital API request failed for 'test': 401 Client Error
# ❌ AnimesDigital API request failed for 'test': 403 Forbidden
```

### 2. Automated Monitoring

Add this to your search command history to track failures:

```bash
# Run periodic searches and log results
for query in "dandadan" "jujutsu" "final"; do
  echo "[$(date)] Testing: $query"
  uv run ani-tupi --query "$query" 2>&1 | grep -E "(✅|❌)"
done
```

### 3. Check Logs Over Time

Monitor the application logs for patterns:

```bash
# Follow logs in real-time
tail -f ~/.local/state/ani-tupi/logs/*.log | grep AnimesDigital

# Or parse historical logs
grep "AnimesDigital API" ~/.local/state/ani-tupi/logs/*.log
```

## Expected Behavior

### If Token is Permanent ✅
- Searches continue working indefinitely
- No 401/403 errors appear in logs
- No errors after weeks/months of use

### If Token Expires ❌
- After X days/weeks, searches fail with:
  ```
  401 Unauthorized: Invalid token
  403 Forbidden: Token expired
  ```
- All AnimesDigital searches return empty results
- Error pattern visible in logs

## What to Do If Token Expires

### Option 1: Update Token (Automatic)

If we implement automatic token recovery:

```python
# Auto-extracted from website JavaScript
# Would happen transparently
```

### Option 2: Manual Token Update

1. Open `https://animesdigital.org` in browser
2. Press F12 to open DevTools
3. Go to **Network** tab
4. Search for an anime
5. Find the request to `/func/listanime`
6. Look for `token=...` in the request body
7. Copy the new token value
8. Update `API_TOKEN` in `scrapers/plugins/animesdigital.py`:

```python
API_TOKEN = "new_token_here"
```

9. Test the search works

### Option 3: Fallback to Browser Automation

If tokens become unreliable, revert to the original approach:

```bash
cp scrapers/plugins/animesdigital.py.backup scrapers/plugins/animesdigital.py
uv run ani-tupi --query "test"
```

## Token Extraction (If Needed)

If the token needs to be refreshed automatically, here's the extraction method:

```python
# Extract token from website JavaScript
import requests
from bs4 import BeautifulSoup
import re

def extract_token() -> str | None:
    """Extract fresh API token from AnimesDigital website."""
    try:
        response = requests.get(
            "https://animesdigital.org/animes-legendados-online",
            timeout=10
        )
        soup = BeautifulSoup(response.text, "html.parser")

        # Look for token in JavaScript variables
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                match = re.search(r"token['\"]?\s*[:=]\s*['\"]([a-f0-9]+)['\"]", script.string)
                if match:
                    return match.group(1)
    except Exception as e:
        print(f"Failed to extract token: {e}")

    return None

# Usage:
# token = extract_token()
# if token:
#     API_TOKEN = token
```

## Testing Timeline

| Date | Status | Notes |
|------|--------|-------|
| 2026-02-04 | ✅ WORKING | Initial API implementation, token verified |
| | | |
| | | Add entries as you monitor |

## Summary

- **Token**: `c1deb78cd4`
- **Last Verified**: 2026-02-04
- **Expected Behavior**: If permanent, searches continue indefinitely
- **Monitoring**: Check logs for 401/403 errors
- **Contingency**: Manual token update or fallback to Selenium

---

**Updated**: 2026-02-04
