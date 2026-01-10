# TUI Testing Plan

Testing approaches for the Textual TUI in this project.

## 1. Pilot Testing (Primary Approach)

Textual provides an async testing API via `app.run_test()`:

```python
import pytest
from textual.pilot import Pilot

@pytest.mark.asyncio
async def test_app_interaction():
    app = MyApp()
    async with app.run_test() as pilot:
        # Simulate keypresses
        await pilot.press("j")  # Move down
        await pilot.press("enter")

        # Click on widgets
        button = app.query_one("#my-button")
        await pilot.click(button)

        # Assert on widget state
        assert app.query_one("#status").renderable == "Expected text"
```

## 2. Snapshot Testing

Textual supports visual regression testing with `snap_compare`:

```python
def test_app_appearance(snap_compare):
    assert snap_compare("path/to/app.py")
```

This generates SVG screenshots and compares them against previous runs.

## 3. Unit Testing Widgets

Test widgets in isolation by instantiating them directly and checking their state/output.

## 4. Recording HTTP Responses with VCR

Use `pytest-recording` (already in dev dependencies) to record and replay HTTP responses:

```python
@pytest.mark.asyncio
@pytest.mark.vcr
async def test_diff_viewer():
    app = DepDiffApp(changes)
    async with app.run_test() as pilot:
        # First run records HTTP responses to cassettes/test_diff_viewer.yaml
        # Subsequent runs replay from the cassette
        await pilot.press("j")
        # assertions...
```

Cassettes are stored in `tests/cassettes/` and should be committed to the repo.

## Requirements

- `pytest-asyncio` for async test support
- `pytest-recording` for VCR cassette recording (already installed)

## Current State

No TUI tests exist yet. All 62 existing tests cover other modules. The existing test patterns (fixtures, mocking, temp directories) transfer well to TUI tests.

## References

- [Textual Testing Guide](https://textual.textualize.io/guide/testing/)
