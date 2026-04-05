import time
import sys
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from interface.themes import JARVIS_THEME, BORDER_STYLE, TITLE_STYLE

console = Console(theme=JARVIS_THEME)

class ArvisCLI:
    """
    Premium Codespace-style CLI for Arvis.
    Features: Multi-pane layout, animated status, real-time logs.
    """
    def __init__(self):
        self.layout = Layout()
        self.output_logs = []
        self._setup_layout()

    def _setup_layout(self):
        """Creates a Jarvis-inspired UI layout."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        self.layout["main"].split_row(
            Layout(name="chat", ratio=3),
            Layout(name="system_status", ratio=1)
        )

    def generate_header(self) -> Panel:
        """Header showing Arvis's version and status."""
        grid = Text.assemble(
            (" ARVIS ", "bold sky_blue3"),
            (" v0.0.1 ", "italic white"),
            (" | SYSTEM STATUS: ", "white"),
            (" ONLINE ", "bold green")
        )
        return Panel(grid, style=BORDER_STYLE)

    def generate_footer(self) -> Panel:
        """Instruction / hint area."""
        return Panel(Text("Press Ctrl+C to Exit | Type '/help' for options", justify="center"), style=BORDER_STYLE)

    def generate_chat_panel(self, messages: list) -> Panel:
        """Main chat window showing conversation with Arvis."""
        chat_text = Text()
        for msg in messages:
            chat_text.append(f"{msg['role'].upper()}: {msg['content']}\n", style=msg.get("style", "white"))
        return Panel(chat_text, title="[bold cyan]CORE DIALOGUE[/]", border_style=BORDER_STYLE)

    def generate_status_panel(self, stats: dict) -> Panel:
        """Real-time system statistics (CPU, RAM, Evolution Progress)."""
        status_text = Text()
        status_text.append(f"CPU: {stats.get('cpu', '0%')}\n", style="info")
        status_text.append(f"RAM: {stats.get('ram', '0%')}\n", style="info")
        status_text.append("\n[bold sky_blue3]EVO PROGRESS[/]\n")
        status_text.append(f"Version: {stats.get('version', '0.0.1')}\n")
        status_text.append(f"Evo-Stage: {stats.get('stage', 'IDLE')}\n", style="italic")
        return Panel(status_text, title="[bold cyan]MONITOR[/]", border_style=BORDER_STYLE)

    def run(self):
        """Starts the main CLI loop (mock version)."""
        messages = [{"role": "system", "content": "INITIALIZING CORE SYSTEMS...", "style": "system"}]
        stats = {"cpu": "12%", "ram": "2.4GB", "version": "0.0.1", "stage": "COLLECTING DATA"}

        with Live(self.layout, refresh_per_second=4, screen=True) as live:
            # Simple simulation of loading
            for i in range(5):
                time.sleep(0.5)
                self.layout["header"].update(self.generate_header())
                self.layout["chat"].update(self.generate_chat_panel(messages))
                self.layout["system_status"].update(self.generate_status_panel(stats))
                self.layout["footer"].update(self.generate_footer())

            # Real implementation would wait for user input here
            messages.append({"role": "arvis", "content": "Greeting, user. I am online and ready.", "style": "arvis.name"})
            live.update(self.layout)
            time.sleep(2)

if __name__ == "__main__":
    cli = ArvisCLI()
    cli.run()
