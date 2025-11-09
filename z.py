#!/usr/bin/env python3
"""
Seamhanian Information Portal (SIP)
- CKAN-style intro
- Resizable Textual UI with tabs (Info, News, Upload)
- News stored via Discord bot on a private server
"""

import os
import sys
import termios
import tty
import requests
from time import sleep
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich import box
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TabbedContent, TabPane, ListView, ListItem, Input
from textual.containers import ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")  # Channel ID where news is stored

console = Console()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODULES_PATH = os.path.join(PROJECT_ROOT, "Modules")
INFO_PATH = os.path.join(MODULES_PATH, "Info", "Info.txt")

TITLE_ART = r"""
███████    ██    ██████     
██         ██    ██   ██    
███████    ██    ██████     
     ██    ██    ██         
███████ ██ ██ ██ ██      ██ 
"""

# ------------------------------------------------------
# Intro
# ------------------------------------------------------
def wait_key():
    console.print("\n[bold yellow]Press any key to continue...[/bold yellow]")
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def intro():
    console.clear()
    width = console.width
    centered_title = "\n".join(line.center(width) for line in TITLE_ART.splitlines())
    console.print(f"[bold cyan]{centered_title}[/bold cyan]\n")
    console.print(Panel.fit(
        "[bold cyan]Seamhanian Information Portal (SIP)[/bold cyan]\n[dim]Initializing...[/dim]",
        subtitle="v0.5",
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
    def compose(self):
        if not os.path.exists(INFO_PATH):
            yield Static(f"[red]Missing:[/red] {INFO_PATH}")
        else:
            with open(INFO_PATH, "r", encoding="utf-8") as f:
                yield Static(f"[cyan]{f.read()}[/cyan]")

class NewsDetailScreen(Screen):
    BINDINGS = [("q", "pop_screen", "Back"), ("escape", "pop_screen", "Back")]

    def __init__(self, title: str, content: str):
        super().__init__()
        self.title = title
        self.content = content

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static(f"[bold cyan]{self.title}[/bold cyan]\n\n{self.content}", id="article_content")
        )

class NewsTab(Static):
    """Fetches news from Discord channel, newest first."""
    
    def compose(self) -> ComposeResult:
        self.article_overlay = Static("", id="article_overlay")
        self.article_overlay.display = False
        self.list_view = ListView()
        yield self.list_view
        yield self.article_overlay

    def on_mount(self):
        self.load_news()

    def load_news(self):
        # Destroy old ListView to avoid ID conflicts
        if hasattr(self, "list_view") and self.list_view in self.children:
            self.list_view.remove()

        # Recreate fresh ListView
        self.list_view = ListView()
        self.mount(self.list_view, before=self.article_overlay)

        if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
            self.list_view.append(ListItem(Static("[red]Discord token or channel ID not set in .env[/red]")))
            return

        url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages?limit=50"
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            messages = resp.json()

            # Sort messages newest first
            messages.sort(key=lambda m: m.get("timestamp", ""), reverse=True)

            for msg in messages:
                content = msg.get("content", "").strip()
                if not content:
                    continue

                lines = content.splitlines()
                title = lines[0] if len(lines) > 0 else "Untitled"
                author = lines[1] if len(lines) > 1 else "Unknown"
                body = "\n".join(lines[2:]) if len(lines) > 2 else ""

                timestamp_display = ""
                timestamp_str = msg.get("timestamp", "")
                if timestamp_str:
                    try:
                        dt = datetime.fromisoformat(timestamp_str.rstrip("Z"))
                        timestamp_display = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass

                # Always generate a new unique ID per widget
                import uuid
                safe_id = f"msg_{uuid.uuid4().hex}"

                item = ListItem(
                    Static(f"[bold green]{title}[/bold green] by [cyan]{author}[/cyan]\n[dim]{timestamp_display}[/dim]"),
                    id=safe_id
                )

                item.data = {
                    "title": title,
                    "author": author,
                    "body": body,
                    "discord_id": msg["id"]
                }

                self.list_view.append(item)

        except Exception as e:
            self.list_view.append(ListItem(Static(f"[red]Error fetching news: {e}[/red]")))

    def on_list_view_selected(self, event: ListView.Selected):
        selected = event.item
        if not hasattr(selected, "data") or not selected.data:
            return
        overlay_content = f"[bold cyan]{selected.data['title']}[/bold cyan]\n\n{selected.data['body']}\n\n[dim]Press 'q' to exit article[/dim]"
        self.article_overlay.update(overlay_content)
        self.article_overlay.display = True
        self.list_view.display = False
        self.article_overlay.focus()

class UploadTab(Static):
    """Upload, edit, or delete news on Discord."""
    def compose(self) -> ComposeResult:
        self.file_input = Input(placeholder="Select .txt file (drag or type filename)")
        self.user_input = Input(placeholder="Your username")
        self.delete_toggle = Button("Delete Mode: OFF", id="delete_toggle")
        self.status = Static("")
        yield self.file_input
        yield self.user_input
        yield self.delete_toggle
        yield self.status

        self.delete_mode = False

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "delete_toggle":
            self.delete_mode = not self.delete_mode
            event.button.label = f"Delete Mode: {'ON' if self.delete_mode else 'OFF'}"

    async def on_input_submitted(self, event: Input.Submitted):
        username = self.user_input.value.strip()
        file_path = self.file_input.value.strip().strip('"').strip("'")
        if not username or not file_path:
            self.status.update("[red]Username and file are required![/red]")
            return
        if not os.path.isfile(file_path) or not file_path.lower().endswith(".txt"):
            self.status.update("[red]Invalid file! Must be a .txt[/red]")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        title = lines[0] if len(lines) > 0 else "Untitled"
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""

        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        get_url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages?limit=50"
        try:
            # Fetch existing messages to check for edits/deletes
            resp = requests.get(get_url, headers=headers, timeout=10)
            resp.raise_for_status()
            messages = resp.json()

            target_msg = None
            for msg in messages:
                content = msg.get("content", "")
                if not content.strip():
                    continue
                lines_existing = content.splitlines()
                existing_title = lines_existing[0] if len(lines_existing) > 0 else ""
                existing_author = lines_existing[1] if len(lines_existing) > 1 else ""
                if existing_title == title and existing_author == username:
                    target_msg = msg
                    break

            if self.delete_mode:
                if target_msg:
                    delete_url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages/{target_msg['id']}"
                    del_resp = requests.delete(delete_url, headers=headers, timeout=10)
                    del_resp.raise_for_status()
                    self.status.update(f"[green]Deleted news: {title} by {username}[/green]")
                else:
                    self.status.update("[red]No matching news to delete[/red]")
            else:
                # Edit if exists
                if target_msg:
                    edit_url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages/{target_msg['id']}"
                    data = {"content": f"{title}\n{username}\n{body}"}
                    edit_resp = requests.patch(edit_url, headers=headers, json=data, timeout=10)
                    edit_resp.raise_for_status()
                    self.status.update(f"[green]Edited news: {title} by {username}[/green]")
                else:
                    # Create new
                    post_url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
                    data = {"content": f"{title}\n{username}\n{body}"}
                    post_resp = requests.post(post_url, headers=headers, json=data, timeout=10)
                    post_resp.raise_for_status()
                    self.status.update(f"[green]Uploaded news: {title} by {username}[/green]")

            # Refresh news tab
            news_tab = self.app.tabs.query_one("#news_tab", expect_type=TabPane).query_one(NewsTab)
            news_tab.load_news()

        except Exception as e:
            self.status.update(f"[red]Error: {e}[/red]")

# ------------------------------------------------------
# Main App
# ------------------------------------------------------
class SIPApp(App):
    BINDINGS = [
        ("escape", "quit", "Quit App"),
        ("q", "close_article", "Close Article"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self.tabs = TabbedContent()
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
        self.tabs.active = "info_tab"

    def _news_overlay_active(self) -> bool:
        try:
            news_tab = self.tabs.query_one("#news_tab", expect_type=TabPane)
            overlay = news_tab.query_one("#article_overlay", expect_type=Static)
            return overlay.display
        except Exception:
            return False

    async def action_close_article(self):
        if not self._news_overlay_active():
            return
        news_tab = self.tabs.query_one("#news_tab", expect_type=TabPane)
        overlay = news_tab.query_one("#article_overlay", expect_type=Static)
        overlay.display = False
        list_view = news_tab.query_one("#news_list", expect_type=ListView)
        list_view.display = True
        list_view.focus()

    async def action_refresh(self):
        """Refresh the news tab when 'r' is pressed."""
        try:
            news_tab = self.tabs.query_one("#news_tab", expect_type=TabPane).query_one(NewsTab)
            news_tab.load_news()
        except Exception as e:
            console.print(f"[red]Error refreshing news: {e}[/red]")

def main():
    intro()
    SIPApp().run()

if __name__ == "__main__":
    main()