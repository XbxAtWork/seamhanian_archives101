#!/usr/bin/env python3
"""
Seamhanian Information Portal (SIP)
- CKAN-style intro
- Resizable Textual UI with tabs (Info, News)
"""

import os
from time import sleep
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich import box
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TabbedContent, TabPane
from textual.containers import ScrollableContainer

console = Console()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODULES_PATH = os.path.join(PROJECT_ROOT, "Modules")
INFO_PATH = os.path.join(MODULES_PATH, "Info", "Info.txt")
NEWS_PATH = os.path.join(MODULES_PATH, "News")

TITLE_ART = r"""
███████    ██    ██████     
██         ██    ██   ██    
███████    ██    ██████     
     ██    ██    ██         
███████ ██ ██ ██ ██      ██ 
"""

def intro():
    """CKAN-style intro animation"""
    console.clear()
    width = console.width
    centered_title = "\n".join(line.center(width) for line in TITLE_ART.splitlines())
    console.print(f"[bold cyan]{centered_title}[/bold cyan]\n")
    console.print(Panel.fit(
        "[bold cyan]Seamhanian Information Portal (SIP)[/bold cyan]\n[dim]Initializing...[/dim]",
        subtitle="v0.3",
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
        for _ in range(100):
            sleep(0.01)
            progress.update(task, advance=1)
    console.print("[bold green]✔ Ready.[/bold green]\n")
    sleep(0.35)


class InfoTab(ScrollableContainer):
    """Displays Info.txt"""
    def compose(self):
        if not os.path.exists(INFO_PATH):
            yield Static(f"[red]Missing:[/red] {INFO_PATH}")
        else:
            with open(INFO_PATH, "r", encoding="utf-8") as f:
                yield Static(f"[cyan]{f.read()}[/cyan]")


class NewsTab(ScrollableContainer):
    """Displays list of .txt files in News"""
    def compose(self):
        if not os.path.exists(NEWS_PATH):
            yield Static(f"[red]Missing folder:[/red] {NEWS_PATH}")
            return

        files = [f for f in os.listdir(NEWS_PATH) if f.endswith(".txt")]
        if not files:
            yield Static("[yellow]No news files found.[/yellow]")
            return

        yield Static("[bold cyan]Available News Files:[/bold cyan]\n")
        for f in sorted(files, reverse=True):
            path = os.path.join(NEWS_PATH, f)
            date = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
            yield Static(f"[green]{f}[/green] — [dim]{date}[/dim]")


class SIPApp(App):
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Info"):
                yield InfoTab()
            with TabPane("News"):
                yield NewsTab()
        yield Footer()


def main():
    intro()
    SIPApp().run()


if __name__ == "__main__":
    main()