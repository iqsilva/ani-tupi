# Zathura Configuration Management

## ADDED Requirements

### Requirement: Auto-configure Zathura default zoom
The application SHALL automatically configure Zathura to use "fit-width" zoom when opening PDF files for manga reading.

#### Scenario:
When a user opens a manga PDF using Zathura through ani-tupi, the PDF should display with width-fit zoom applied automatically, eliminating the need for manual zoom adjustment.

### Requirement: Preserve existing Zathura configurations  
The application SHALL preserve any existing Zathura user configurations while adding the default zoom setting.

#### Scenario:
If a user already has a `~/.config/zathura/zathurarc` file with custom keybindings or settings, the application should add the zoom configuration without overwriting existing settings.

### Requirement: Create Zathura config directory if needed
The application SHALL create the Zathura configuration directory if it doesn't exist.

#### Scenario:
When first using Zathura through ani-tupi on a system without Zathura configuration, the application should create `~/.config/zathura/` directory and the necessary configuration file.

### Requirement: Handle permission errors gracefully
The application SHALL handle filesystem permission errors when creating Zathura configurations and provide helpful error messages.

#### Scenario:
If the application cannot create or modify Zathura configuration files due to permissions, it should notify the user with clear instructions on how to manually configure the zoom setting.