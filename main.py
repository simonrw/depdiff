import sys
import argparse
from pathlib import Path
from depdiff.orchestrator import DependencyDiffOrchestrator
from depdiff.parser import DiffParser


def main() -> None:
    parser = argparse.ArgumentParser(description="Dependency Diff Hunter")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Path to requirements.txt diff file (defaults to stdin)",
    )
    parser.add_argument("--tui", action="store_true", help="Run in TUI mode")
    parser.add_argument(
        "-j", "--jobs", type=int, help="Number of parallel jobs", default=None
    )

    args = parser.parse_args()

    # Read input
    try:
        if args.input:
            diff_input = args.input.read_text()
        else:
            if sys.stdin.isatty():
                parser.print_help()
                return
            diff_input = sys.stdin.read()
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    if not diff_input:
        print("No input provided.", file=sys.stderr)
        return

    if args.tui:
        # Reconnect stdin to TTY if it was piped so the TUI works
        if not sys.stdin.isatty():
            import os

            try:
                tty = open("/dev/tty")
                os.dup2(tty.fileno(), 0)
                sys.stdin = tty
            except Exception as e:
                print(f"Warning: Could not reconnect to TTY: {e}", file=sys.stderr)

        from depdiff.tui import DepDiffApp

        # Parse changes for the TUI
        diff_parser = DiffParser()
        changes = diff_parser.parse(diff_input)

        # Filter to only version updates as retriever currently only supports them
        updates = [c for c in changes if c.is_update]

        if not updates:
            print("No dependency updates found.", file=sys.stderr)
            return

        app = DepDiffApp(updates, max_workers=args.jobs)
        app.run()
    else:
        orchestrator = DependencyDiffOrchestrator(max_workers=args.jobs)
        report = orchestrator.process_requirements_diff(diff_input)
        print(report)


if __name__ == "__main__":
    main()
