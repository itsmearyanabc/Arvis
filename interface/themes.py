from rich.theme import Theme
from rich.style import Style

# Jarvis 0.0.1 Theme - Premium Dark Mode with Neon Highlights
JARVIS_THEME = Theme({
    "info": "bright_cyan",
    "warning": "bright_yellow",
    "danger": "bright_red",
    "success": "bright_green",
    "system": "bold cyan italic",
    "input.prompt": "bold magenta",
    "header": "bold white on dark_blue",
    "code.border": "cyan",
    "arvis.name": "bold sky_blue3",
    "arvis.thought": "italic grey50",
    "arvis.action": "bold orange3",
})

# Neon styles for panels and borders
BORDER_STYLE = "cyan"
TITLE_STYLE = "bold cyan"
HIGHLIGHT_STYLE = "bold magenta"
