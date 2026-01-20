# Configure Zathura Default Zoom to Fit Width

## Summary

Add configuration to make Zathura PDF reader open with "fit width" zoom by default, eliminating the need to manually adjust zoom for each manga chapter.

## User Request

User wants Zathura to open with zoom fit width (largura) by default instead of having to manually zoom every time.

## Current Behavior

- Zathura opens with default zoom settings (typically fit to page or last used zoom)
- Users must manually adjust zoom to fit width for comfortable reading
- No configuration handling for Zathura in the project currently

## Proposed Solution

Add Zathura configuration support to ani-tupi that:
1. Creates/updates `~/.config/zathura/zathurarc` with fit-width default zoom
2. Integrates with existing manga reader configuration system
3. Preserves existing Zathura configurations while adding the default zoom setting
4. Provides user control through environment variables if needed

## Scope

**In Scope:**
- Zathura configuration management
- Default zoom fit-width setting
- Integration with existing PDF reader detection

**Out of Scope:**
- Configuration for other PDF readers (evince, okular, mupdf)
- Advanced Zathura keybindings or theming
- Runtime zoom configuration (only default startup behavior)

## Relationship to Existing Code

This change extends the manga reader functionality in `utils/manga_reader.py` and potentially the configuration system in `models/config.py`. It adds a new capability for managing Zathura-specific configurations while maintaining compatibility with the existing PDF reader detection system.