from typing import Callable

import pytest
from textual.pilot import Pilot

from depdiff.models import DependencyChange
from depdiff.tui import DepDiffApp, DiffViewer, PackageItem


class MockDepDiffApp(DepDiffApp):
    """A testable version of DepDiffApp that doesn't auto-fetch on mount."""

    def on_mount(self) -> None:
        self.title = "Dependency Diff Hunter"
        self.sub_title = f"Comparing {len(self.changes)} packages"
        self.query_one("#package-list").focus()
        # Skip self.action_refresh() to avoid network calls


@pytest.fixture
def sample_changes() -> list[DependencyChange]:
    """Create sample dependency changes for testing."""
    return [
        DependencyChange("requests", old_version="2.25.1", new_version="2.26.0"),
        DependencyChange("urllib3", old_version="1.26.5", new_version="1.26.6"),
        DependencyChange("flask", old_version="2.0.0", new_version="2.1.0"),
    ]


@pytest.fixture
def sample_diff() -> str:
    """A simple diff for testing."""
    return """\
diff --git a/example.py b/example.py
index 1234567..abcdefg 100644
--- a/example.py
+++ b/example.py
@@ -1,5 +1,5 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
     return True
"""


@pytest.fixture
def large_diff() -> str:
    """A larger diff for testing scrolling and large content rendering."""
    lines = [
        "diff --git a/large_file.py b/large_file.py",
        "index 1234567..abcdefg 100644",
        "--- a/large_file.py",
        "+++ b/large_file.py",
        "@@ -1,100 +1,100 @@",
    ]
    for i in range(1, 101):
        lines.append(f"-    old_line_{i} = {i}")
        lines.append(f"+    new_line_{i} = {i * 2}")
    return "\n".join(lines)


@pytest.fixture
def app_with_diff(
    sample_changes: list[DependencyChange], sample_diff: str
) -> MockDepDiffApp:
    """Create an app with pre-populated diffs."""
    app = MockDepDiffApp(sample_changes)
    for change in sample_changes:
        app.diffs[change.name] = sample_diff
        app.statuses[change.name] = "done"
    return app


@pytest.fixture
def app_with_large_diff(
    sample_changes: list[DependencyChange], large_diff: str
) -> MockDepDiffApp:
    """Create an app with a large diff for testing."""
    app = MockDepDiffApp(sample_changes)
    app.diffs["requests"] = large_diff
    app.statuses["requests"] = "done"
    return app


class TestPackageItem:
    """Unit tests for PackageItem widget."""

    def test_display_text_pending(self, sample_changes: list[DependencyChange]) -> None:
        item = PackageItem(sample_changes[0])
        assert item.status == "pending"
        text = item._get_display_text()
        assert "requests" in text
        assert "2.25.1" in text
        assert "2.26.0" in text

    def test_display_text_with_line_count(
        self, sample_changes: list[DependencyChange]
    ) -> None:
        item = PackageItem(sample_changes[0])
        item.update_status("done", line_count=42)
        text = item._get_display_text()
        assert "42 lines" in text

    def test_status_icons(self, sample_changes: list[DependencyChange]) -> None:
        item = PackageItem(sample_changes[0])

        item.status = "pending"
        assert "⏳" in item._get_display_text()

        item.status = "loading"
        assert "🔄" in item._get_display_text()

        item.status = "done"
        assert "✅" in item._get_display_text()

        item.status = "error"
        assert "❌" in item._get_display_text()


class TestSnapshots:
    """Snapshot tests for TUI visual output."""

    def test_initial_render(
        self,
        snap_compare: Callable[..., bool],
        app_with_diff: MockDepDiffApp,
    ) -> None:
        """Snapshot test of initial app render with pending items."""
        assert snap_compare(app_with_diff)

    def test_with_large_diff(
        self,
        snap_compare: Callable[..., bool],
        app_with_large_diff: MockDepDiffApp,
    ) -> None:
        """Snapshot test with a large diff content."""

        def setup_viewer(pilot: Pilot[MockDepDiffApp]) -> None:
            # Update the first item's line count
            for item in pilot.app.query(PackageItem):
                if item.change.name == "requests":
                    item.update_status("done", line_count=205)
                    break

        assert snap_compare(app_with_large_diff, run_before=setup_viewer)

    def test_navigation_down(
        self,
        snap_compare: Callable[..., bool],
        app_with_diff: MockDepDiffApp,
    ) -> None:
        """Snapshot after navigating down with j."""
        assert snap_compare(app_with_diff, press=["j"])

    def test_navigation_multiple(
        self,
        snap_compare: Callable[..., bool],
        app_with_diff: MockDepDiffApp,
    ) -> None:
        """Snapshot after navigating down twice then up."""
        assert snap_compare(app_with_diff, press=["j", "j", "k"])

    def test_loading_state(
        self,
        snap_compare: Callable[..., bool],
        sample_changes: list[DependencyChange],
    ) -> None:
        """Snapshot of loading state."""
        app = MockDepDiffApp(sample_changes)
        app.statuses["requests"] = "loading"

        def set_loading(pilot: Pilot[MockDepDiffApp]) -> None:
            for item in pilot.app.query(PackageItem):
                if item.change.name == "requests":
                    item.update_status("loading")
                    break

        assert snap_compare(app, run_before=set_loading)

    def test_error_state(
        self,
        snap_compare: Callable[..., bool],
        sample_changes: list[DependencyChange],
    ) -> None:
        """Snapshot of error state."""
        app = MockDepDiffApp(sample_changes)
        app.diffs["requests"] = "Error: Failed to fetch package"
        app.statuses["requests"] = "error"

        def set_error(pilot: Pilot[MockDepDiffApp]) -> None:
            for item in pilot.app.query(PackageItem):
                if item.change.name == "requests":
                    item.update_status("error")
                    break
            viewer = pilot.app.query_one("#diff-viewer", DiffViewer)
            viewer.update_diff("Error: Failed to fetch package", status="error")

        assert snap_compare(app, run_before=set_error)

    def test_empty_diff(
        self,
        snap_compare: Callable[..., bool],
        sample_changes: list[DependencyChange],
    ) -> None:
        """Snapshot when diff is empty."""
        app = MockDepDiffApp(sample_changes)
        app.diffs["requests"] = ""
        app.statuses["requests"] = "done"

        def show_empty(pilot: Pilot[MockDepDiffApp]) -> None:
            for item in pilot.app.query(PackageItem):
                if item.change.name == "requests":
                    item.update_status("done", line_count=0)
                    break
            viewer = pilot.app.query_one("#diff-viewer", DiffViewer)
            viewer.update_diff("")

        assert snap_compare(app, run_before=show_empty)


class TestDepDiffAppBehavior:
    """Behavioral tests for app interactions."""

    @pytest.mark.asyncio
    async def test_quit_action(self, sample_changes: list[DependencyChange]) -> None:
        """Test that q quits the app."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test() as pilot:
            await pilot.press("q")
            await pilot.pause()
            assert app._exit

    @pytest.mark.asyncio
    async def test_scroll_commands(
        self, large_diff: str, sample_changes: list[DependencyChange]
    ) -> None:
        """Test scroll commands don't raise errors."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test() as pilot:
            app.diffs["requests"] = large_diff
            app.statuses["requests"] = "done"

            await pilot.press("enter")
            await pilot.pause()

            # These should not raise
            await pilot.press("d")
            await pilot.press("u")
            await pilot.press("space")
            await pilot.press("b")
            await pilot.pause()
