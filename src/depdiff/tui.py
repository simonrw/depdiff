from typing import Dict, List, Optional
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Header, Footer, ListView, ListItem, Static, Label
from textual.worker import Worker, WorkerState
from textual.binding import Binding
from rich.syntax import Syntax
from rich.text import Text

from depdiff.models import DependencyChange
from depdiff.parallel import ParallelRetriever


class PackageItem(ListItem):
    def __init__(self, change: DependencyChange):
        super().__init__()
        self.change = change
        self.status = "pending"  # pending, loading, done, error
        self.line_count: Optional[int] = None
        self._label = Label(self._get_display_text())

    def _get_display_text(self) -> str:
        status_icon = (
            "⏳"
            if self.status == "pending"
            else "🔄"
            if self.status == "loading"
            else "✅"
            if self.status == "done"
            else "❌"
        )
        line_info = f"  {self.line_count} lines" if self.line_count is not None else ""
        return f"{status_icon} {self.change.name}\n  {self.change.old_version} -> {self.change.new_version}{line_info}"

    def compose(self) -> ComposeResult:
        yield self._label

    def update_status(self, status: str, line_count: Optional[int] = None) -> None:
        self.status = status
        if line_count is not None:
            self.line_count = line_count
        self._label.update(self._get_display_text())


class DiffViewer(VerticalScroll):
    can_focus = True

    def compose(self) -> ComposeResult:
        yield Static(id="diff-content")

    def update_diff(self, diff: str, status: str = "done") -> None:
        content = self.query_one("#diff-content", Static)
        if status == "loading":
            content.update(Text("Loading diff...", style="bold yellow"))
            return
        elif status == "error":
            content.update(Text(diff, style="bold red"))
            return

        if not diff or diff.strip() == "":
            content.update(
                Text("No changes detected in source code.", style="dim italic")
            )
            return

        try:
            syntax = Syntax(diff, "diff", theme="monokai", line_numbers=True)
            content.update(syntax)
        except Exception as e:
            content.update(Text(f"Error rendering diff: {e}", style="bold red"))

        self.scroll_home(animate=False)


class DepDiffApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    Header {
        background: $primary-darken-1;
        color: $text;
        text-style: bold;
    }

    Horizontal {
        height: 1fr;
    }

    #package-list {
        width: 45;
        border-right: tall $primary;
        background: $surface;
    }

    #diff-viewer {
        width: 1fr;
        background: $background;
    }

    #diff-viewer:focus {
        border: tall $accent;
    }

    #diff-content {
        padding: 1;
    }

    ListItem {
        padding: 0 1;
        height: 3;
    }

    ListItem > Label {
        height: 1fr;
        content-align: left middle;
    }

    ListItem.loading {
        background: $accent 20%;
    }

    ListItem.done {
        /* color handled by status icons */
    }

    ListItem.error {
        color: $error;
    }

    #status-bar {
        height: 1;
        background: $primary-darken-2;
        color: $text-disabled;
        padding: 0 1;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
        Binding("u", "scroll_half_up", "Half Up", show=True),
        Binding("d", "scroll_half_down", "Half Down", show=True),
        Binding("space", "scroll_page_down", "Page Down", show=True),
        Binding("b", "scroll_page_up", "Page Up", show=True),
    ]

    def __init__(
        self, changes: List[DependencyChange], max_workers: Optional[int] = None
    ):
        super().__init__()
        self.changes = changes
        self.diffs: Dict[str, str] = {}
        self.statuses: Dict[str, str] = {c.name: "pending" for c in changes}
        self.retriever = ParallelRetriever(max_workers=max_workers)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ListView(*[PackageItem(c) for c in self.changes], id="package-list")
            yield DiffViewer(id="diff-viewer")
        yield Static(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Dependency Diff Hunter"
        self.sub_title = f"Comparing {len(self.changes)} packages"
        self.query_one("#package-list").focus()
        self.action_refresh()

    def action_cursor_up(self) -> None:
        self.query_one("#package-list", ListView).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one("#package-list", ListView).action_cursor_down()

    def action_scroll_half_up(self) -> None:
        viewer = self.query_one("#diff-viewer", DiffViewer)
        step = viewer.size.height // 2
        viewer.scroll_relative(y=-step, animate=False)

    def action_scroll_half_down(self) -> None:
        viewer = self.query_one("#diff-viewer", DiffViewer)
        step = viewer.size.height // 2
        viewer.scroll_relative(y=step, animate=False)

    def action_scroll_page_up(self) -> None:
        viewer = self.query_one("#diff-viewer", DiffViewer)
        viewer.scroll_relative(y=-viewer.size.height, animate=False)

    def action_scroll_page_down(self) -> None:
        viewer = self.query_one("#diff-viewer", DiffViewer)
        viewer.scroll_relative(y=viewer.size.height, animate=False)

    def action_refresh(self) -> None:
        """Refresh all package diffs."""
        self.diffs.clear()
        for item in self.query(PackageItem):
            self.statuses[item.change.name] = "loading"
            self.fetch_diff(item)
        self.query_one("#status-bar", Static).update(
            "Fetching package metadata and diffs..."
        )

    def _update_viewer(self, item: PackageItem) -> None:
        name = item.change.name
        status = self.statuses.get(name, "pending")
        diff = self.diffs.get(name, "")

        viewer = self.query_one("#diff-viewer", DiffViewer)
        if status == "loading":
            viewer.update_diff("", status="loading")
        elif status == "error":
            viewer.update_diff(diff, status="error")
        else:
            viewer.update_diff(diff)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, PackageItem):
            self._update_viewer(item)
            self.query_one("#status-bar", Static).update(
                f"Package: {item.change.name} ({item.change.old_version} -> {item.change.new_version})"
            )

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        item = event.item
        if isinstance(item, PackageItem):
            self._update_viewer(item)
            self.query_one("#status-bar", Static).update(f"Package: {item.change.name}")

    def fetch_diff(self, item: PackageItem) -> None:
        item.update_status("loading")
        item.add_class("loading")
        item.remove_class("done", "error")
        self.run_worker(
            self._get_diff_task(item.change),
            name=f"fetch-{item.change.name}",
            group="fetchers",
        )

    async def _get_diff_task(self, change: DependencyChange) -> tuple[str, str]:
        import asyncio

        loop = asyncio.get_running_loop()

        def _task():
            try:
                return self.retriever._process_single_package(change)
            except Exception as e:
                return f"Error: {e}"

        diff = await loop.run_in_executor(None, _task)
        return change.name, diff

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            result = event.worker.result
            if result is None:
                return
            name, diff = result
            self.diffs[name] = diff

            # Calculate line count for the diff
            line_count = len(diff.splitlines()) if diff else 0

            # Find the item in the list and update its status
            for item in self.query(PackageItem):
                if item.change.name == name:
                    item.remove_class("loading")
                    if diff.startswith("Error:"):
                        self.statuses[name] = "error"
                        item.update_status("error")
                        item.add_class("error")
                    else:
                        self.statuses[name] = "done"
                        item.update_status("done", line_count=line_count)
                        item.add_class("done")

                    # If this item is currently highlighted, update the viewer
                    highlighted_item = self.query_one(
                        "#package-list", ListView
                    ).highlighted_child
                    if highlighted_item == item:
                        self._update_viewer(item)
                    break
        elif event.state == WorkerState.ERROR:
            name = event.worker.name.replace("fetch-", "")
            error_msg = f"Worker Error: {event.worker.error}"
            self.diffs[name] = error_msg
            self.statuses[name] = "error"
            for item in self.query(PackageItem):
                if item.change.name == name:
                    item.remove_class("loading")
                    item.update_status("error")
                    item.add_class("error")
                    # If this item is currently highlighted, update the viewer
                    highlighted_item = self.query_one(
                        "#package-list", ListView
                    ).highlighted_child
                    if highlighted_item == item:
                        self._update_viewer(item)
                    break

    async def action_quit(self) -> None:
        self.retriever.cleanup()
        self.exit()


if __name__ == "__main__":
    from depdiff.parser import DiffParser

    parser = DiffParser()
    # Simple test if run directly
    example_diff = """
- requests==2.25.1
+ requests==2.26.0
- urllib3==1.26.5
+ urllib3==1.26.6
    """
    changes = parser.parse(example_diff)
    app = DepDiffApp(changes)
    app.run()
