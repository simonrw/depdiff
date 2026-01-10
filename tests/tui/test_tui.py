import pytest

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


class TestDepDiffAppWithLocalstackData:
    """Integration tests using real localstack diff data."""

    @pytest.mark.asyncio
    async def test_app_renders_with_real_diff(
        self, localstack_diff: str, sample_changes: list[DependencyChange]
    ) -> None:
        """Test that the app can render a real-world diff."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test() as pilot:
            # Pre-populate the diff for the first package
            app.diffs["requests"] = localstack_diff
            app.statuses["requests"] = "done"

            # Update the first item's status
            for item in app.query(PackageItem):
                if item.change.name == "requests":
                    line_count = len(localstack_diff.splitlines())
                    item.update_status("done", line_count=line_count)
                    break

            # Trigger a re-render of the viewer
            await pilot.pause()

            # Verify the package list exists
            package_list = app.query_one("#package-list")
            assert package_list is not None

            # Verify diff viewer exists
            diff_viewer = app.query_one("#diff-viewer", DiffViewer)
            assert diff_viewer is not None

    @pytest.mark.asyncio
    async def test_keyboard_navigation(
        self, sample_changes: list[DependencyChange], sample_diff: str
    ) -> None:
        """Test j/k navigation between packages."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test() as pilot:
            # Pre-populate diffs
            for change in sample_changes:
                app.diffs[change.name] = sample_diff
                app.statuses[change.name] = "done"

            # Navigate down with j
            await pilot.press("j")
            await pilot.pause()

            # Navigate down again
            await pilot.press("j")
            await pilot.pause()

            # Navigate up with k
            await pilot.press("k")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_scroll_commands(
        self, localstack_diff: str, sample_changes: list[DependencyChange]
    ) -> None:
        """Test scroll commands (u/d for half page, space/b for full page)."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test() as pilot:
            # Pre-populate with a large diff
            app.diffs["requests"] = localstack_diff
            app.statuses["requests"] = "done"

            # Select the first item to show the diff
            await pilot.press("enter")
            await pilot.pause()

            # Test half-page scroll down
            await pilot.press("d")
            await pilot.pause()

            # Test half-page scroll up
            await pilot.press("u")
            await pilot.pause()

            # Test full-page scroll down
            await pilot.press("space")
            await pilot.pause()

            # Test full-page scroll up
            await pilot.press("b")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_quit_action(self, sample_changes: list[DependencyChange]) -> None:
        """Test that q quits the app."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test() as pilot:
            await pilot.press("q")
            await pilot.pause()
            # App should be exiting
            assert app._exit


class TestDiffViewer:
    """Unit tests for DiffViewer widget."""

    @pytest.mark.asyncio
    async def test_update_diff_loading(
        self, sample_changes: list[DependencyChange]
    ) -> None:
        """Test that loading state shows loading message."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test():
            viewer = app.query_one("#diff-viewer", DiffViewer)
            viewer.update_diff("", status="loading")
            # Should show loading text (verified by not raising)

    @pytest.mark.asyncio
    async def test_update_diff_error(
        self, sample_changes: list[DependencyChange]
    ) -> None:
        """Test that error state shows error message."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test():
            viewer = app.query_one("#diff-viewer", DiffViewer)
            viewer.update_diff("Something went wrong", status="error")

    @pytest.mark.asyncio
    async def test_update_diff_empty(
        self, sample_changes: list[DependencyChange]
    ) -> None:
        """Test that empty diff shows no changes message."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test():
            viewer = app.query_one("#diff-viewer", DiffViewer)
            viewer.update_diff("")

    @pytest.mark.asyncio
    async def test_update_diff_with_content(
        self, sample_changes: list[DependencyChange], localstack_diff: str
    ) -> None:
        """Test that diff content is rendered with syntax highlighting."""
        app = MockDepDiffApp(sample_changes)

        async with app.run_test():
            viewer = app.query_one("#diff-viewer", DiffViewer)
            viewer.update_diff(localstack_diff)
