#!/usr/bin/env python3
"""
Seamhanian Archives — minimal launcher
- Shows a CKAN-style intro loading screen
- Simple menu with one tab: Info
- Info reads Modules/Info/Info.txt (local file)
"""

import os
from time import sleep
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
from textual.app import App, ComposeResult
# textual import compatibility (try multiple locations for ScrollView)
try:
    # common case: ScrollView exported directly
    from textual.widgets import Header, Footer, Static, ScrollView
except Exception:
    try:
        # some versions moved ScrollView into a submodule
        from textual.widgets import Header, Footer, Static
    except Exception:
        try:
            # some versions expose a module object named scroll_view
            from textual.widgets import Header, Footer, Static, scroll_view
            ScrollView = scroll_view.ScrollView
        except Exception:
            # final fallback: we'll still import Header/Footer/Static if possible
            try:
                from textual.widgets import Header, Footer, Static
            except Exception:
                raise ImportError(
                    "Could not import textual widgets (Header/Footer/Static). "
                    "Please make sure 'textual' is installed in your .venv."
                )
            ScrollView = None  # we'll check later and raise a helpful message

console = Console()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
INFO_PATH = os.path.join(PROJECT_ROOT, "Modules", "Info", "Info.txt")

TITLE_ART = r"""
███████    ██    ██████     
██         ██    ██   ██    
███████    ██    ██████     
     ██    ██    ██         
███████ ██ ██ ██ ██      ██ 
                            
                            
"""

def intro():
    console.clear()
    console.print(f"[bold cyan]{TITLE_ART}[/bold cyan]")
    console.print(Panel.fit(
        "[bold cyan]Seamhanian Information Portal (SIP)[/bold cyan]\n[dim]Initializing...[/dim]",
        subtitle="v0.2",
        box=box.ROUNDED,
    ))
    with Progress(
        SpinnerColumn(style="bold green"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("Loading modules...", total=100)
        for i in range(100):
            sleep(0.01)
            progress.update(task, advance=1)
    console.print("[bold green]✔ Ready.[/bold green]\n")
    sleep(0.35)


class InfoView(ScrollView):
    """Scrollable view that displays Info.txt contents."""

    def __init__(self):
        super().__init__()
        self.file_text = self.load_info()

    def load_info(self):
        if not os.path.exists(INFO_PATH):
            return f"[red]Missing:[/red] {INFO_PATH}\nCreate this file and restart SIP."
        with open(INFO_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def on_mount(self):
        self.update(f"[bold cyan]{self.file_text}[/bold cyan]")


class SIPApp(App):
    CSS_PATH = None
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield InfoView()
        yield Footer()


if __name__ == "__main__":
    app = SIPApp()
    app.run()