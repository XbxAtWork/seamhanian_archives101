#!/usr/bin/env python3
"""
Seamhanian Information Portal (SIP)
- CKAN-style intro
- Resizable Textual UI with tabs (Info, News)
"""

import os, re
import sys
import termios
import tty
from time import sleep
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich import box
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TabbedContent, TabPane, ListView, ListItem, Input
from textual.containers import Horizontal, ScrollableContainer
from textual.screen import Screen
from textual import on
from textual import events
from textual.widget import Widget
import shutil
import httpx

console = Console()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODULES_PATH = os.path.join(PROJECT_ROOT, "Modules")
INFO_PATH = os.path.join(MODULES_PATH, "Info", "Info.txt")
NEWS_PATH = os.path.join(MODULES_PATH, "News")

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/XbxAtWork/seamhanian_archives101/main/Modules/News"

TITLE_ART = r"""
███████    ██    ██████     
██         ██    ██   ██    
███████    ██    ██████     
     ██    ██    ██         
███████ ██ ██ ██ ██      ██ 
"""

NEWS_PATH = os.path.join(MODULES_PATH, "News")
if not os.path.exists(NEWS_PATH):
    os.makedirs(NEWS_PATH)

# ------------------------------------------------------
# Intro with “Press any key to continue”
# ------------------------------------------------------
def wait_key():
    """Wait for a single keypress (cross-platform fallback)."""
    console.print("\n[bold yellow]Press any key to continue...[/bold yellow]")
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def intro():
    """CKAN-style intro animation"""
    console.clear()
    width = console.width
    centered_title = "\n".join(line.center(width) for line in TITLE_ART.splitlines())
    console.print(f"[bold cyan]{centered_title}[/bold cyan]\n")
    console.print(Panel.fit(
        "[bold cyan]Seamhanian Information Portal (SIP)[/bold cyan]\n[dim]Initializing...[/dim]",
        subtitle="v0.4",
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
    wait_key()


# ------------------------------------------------------
# Tabs
# ------------------------------------------------------
class InfoTab(ScrollableContainer):
    """Displays Info.txt"""
    def compose(self):
        if not os.path.exists(INFO_PATH):
            yield Static(f"[red]Missing:[/red] {INFO_PATH}")
        else:
            with open(INFO_PATH, "r", encoding="utf-8") as f:
                yield Static(f"[cyan]{f.read()}[/cyan]")

class NewsDetailScreen(Screen):
    """Full article viewer that hides tabs while reading."""

    BINDINGS = [("q", "pop_screen", "Back"), ("escape", "pop_screen", "Back")]

    def __init__(self, title: str, content: str):
        super().__init__()
        self.title = title
        self.content = content

    def compose(self) -> ComposeResult:
        # Only show article, no tabs
        yield ScrollableContainer(
            Static(f"[bold cyan]{self.title}[/bold cyan]\n\n{self.content}", id="article_content")
        )

class NewsTab(Static):
    """Displays news from GitHub, first line is title, second line is author (hidden)."""

    def compose(self) -> ComposeResult:
        self.article_overlay = Static("", id="article_overlay")
        self.article_overlay.display = False
        self.list_view = ListView(id="news_list")
        yield self.list_view
        yield self.article_overlay

    def on_mount(self):
        self.load_news()

    def load_news(self):
        """Fetch news list from GitHub"""
        self.list_view.clear()
        # Fetch list of files from GitHub API (or hardcode if needed)
        news_files = [
            # Example: just the filenames in the GitHub repo
            "newsTest.txt",
            # Add more dynamically if you query GitHub API
        ]
        if not news_files:
            self.list_view.append(ListItem(Static("[yellow]No news files found.[/yellow]")))
            return

        for filename in news_files:
            try:
                url = f"{GITHUB_RAW_BASE}/{filename}"
                resp = httpx.get(url, timeout=10)
                resp.raise_for_status()
                lines = resp.text.splitlines()
                title = lines[0].strip() if lines else "Untitled"
                timestamp = datetime.utcnow().timestamp()  # fallback
                safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", filename)
                item = ListItem(
                    Static(f"[bold green]{title}[/bold green]\n[dim]{datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')}[/dim]"),
                    id=safe_id
                )
                item.data = {"url": url, "title": title}
                self.list_view.append(item)
            except Exception as e:
                self.list_view.append(ListItem(Static(f"[bold red]Error loading {filename}[/bold red]\n[dim]{e}[/dim]")))

    def on_list_view_selected(self, event: ListView.Selected):
        selected = event.item
        if not hasattr(selected, "data") or not selected.data:
            return
        url = selected.data["url"]
        title = selected.data["title"]

        try:
            resp = httpx.get(url, timeout=10)
            resp.raise_for_status()
            lines = resp.text.splitlines()
            body = "\n".join(lines[2:]) if len(lines) > 2 else ""  # skip title & author
        except Exception as e:
            body = f"[red]Error reading file:[/red] {e}"

        overlay_content = f"[bold cyan]{title}[/bold cyan]\n\n{body}\n\n[dim]Press 'q' to exit article[/dim]"
        self.article_overlay.update(overlay_content)
        self.article_overlay.display = True
        self.list_view.display = False
        self.article_overlay.focus()


class UploadTab(Static):
    """Upload news directly to GitHub (via Personal Access Token)."""

    def compose(self) -> ComposeResult:
        self.file_input = Input(placeholder="Select .txt file (drag or type filename)")
        self.user_input = Input(placeholder="Your username")
        self.token_input = Input(placeholder="GitHub Personal Access Token", password=True)
        self.status = Static("")
        yield self.file_input
        yield self.user_input
        yield self.token_input
        yield self.status

    async def on_input_submitted(self, event: Input.Submitted):
        username = self.user_input.value.strip()
        token = self.token_input.value.strip()
        file_path = self.file_input.value.strip().strip('"').strip("'")

        if not username or not file_path or not token:
            self.status.update("[red]All fields are required![/red]")
            return

        if not os.path.isfile(file_path) or not file_path.lower().endswith(".txt"):
            self.status.update("[red]Invalid file! Must be a .txt[/red]")
            return

        # Read content
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        title = lines[0] if lines else "Untitled"
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""

        # Prepare GitHub API upload
        import base64
        import json

        github_api_url = f"https://api.github.com/repos/<USERNAME>/<REPO>/contents/Modules/News/{title}.txt"
        content_bytes = f"{title}\n{username}\n{body}".encode("utf-8")
        encoded_content = base64.b64encode(content_bytes).decode("utf-8")
        headers = {"Authorization": f"token {token}"}

        # Check if file exists
        import httpx
        resp = httpx.get(github_api_url, headers=headers)
        if resp.status_code == 200:
            sha = resp.json()["sha"]
            data = {"message": f"Update news: {title}", "content": encoded_content, "sha": sha}
        else:
            data = {"message": f"Add news: {title}", "content": encoded_content}

        resp = httpx.put(github_api_url, headers=headers, data=json.dumps(data))
        if resp.status_code in (200, 201):
            self.status.update("[green]Uploaded successfully![/green]")
            news_tab = self.app.tabs.query_one("#news_tab", expect_type=TabPane).query_one(NewsTab)
            news_tab.load_news()
        else:
            self.status.update(f"[red]GitHub upload failed: {resp.text}[/red]")

# ------------------------------------------------------
# Main Application
# ------------------------------------------------------
class SIPApp(App):
    BINDINGS = [
        ("escape", "quit", "Quit App"),        # ESC to quit
        ("q", "close_article", "Close Article") # Q to close news article
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self.tabs = TabbedContent()  # create TabbedContent
        with self.tabs:
            with TabPane("Info", id="info_tab"):
                yield InfoTab()
            with TabPane("News", id="news_tab"):
                yield NewsTab()
            with TabPane("Upload", id="upload_tab"):
                yield UploadTab()
        yield self.tabs
        yield Footer()

    def on_mount(self):
        # Set default active tab after creation
        self.tabs.active = "info_tab"

    def _news_overlay_active(self) -> bool:
        """Check if the news article overlay is currently displayed."""
        try:
            news_tab = self.tabs.query_one("#news_tab", expect_type=TabPane)
            overlay = news_tab.query_one("#article_overlay", expect_type=Static)
            return overlay.display
        except Exception:
            return False

    async def action_close_article(self):
        """Close the news overlay if open (Q key)."""
        if not self._news_overlay_active():
            return
        news_tab = self.tabs.query_one("#news_tab", expect_type=TabPane)
        overlay = news_tab.query_one("#article_overlay", expect_type=Static)
        overlay.display = False
        list_view = news_tab.query_one("#news_list", expect_type=ListView)
        list_view.display = True
        list_view.focus()

def main():
    intro()
    SIPApp().run()


if __name__ == "__main__":
    main()