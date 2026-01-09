import sys
from typing import Dict
from depdiff.parser import DiffParser
from depdiff.retriever import HybridRetriever
from depdiff.comparator import SourceComparator
from depdiff.reporter import ReportGenerator


def main() -> None:
    # 1. Read input (e.g., from stdin)
    try:
        diff_input = sys.stdin.read()
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    if not diff_input:
        print("No input provided.", file=sys.stderr)
        return

    # 2. Parse changes
    parser = DiffParser()
    changes = parser.parse(diff_input)

    if not changes:
        print("No dependency changes found.", file=sys.stderr)
        return

    # 3. Process changes (Retrieve diffs)
    comparator = SourceComparator()
    retriever = HybridRetriever(comparator=comparator)
    diffs: Dict[str, str] = {}

    for change in changes:
        # We only care about updates or maybe additions/removals depending on requirements.
        # For now, let's process all.
        print(f"Processing {change.name}...", file=sys.stderr)
        try:
            diff = retriever.get_diff(change)
            diffs[change.name] = diff
        except Exception as e:
            # Log error but continue with other packages
            print(f"Failed to retrieve diff for {change.name}: {e}", file=sys.stderr)
            diffs[change.name] = f"Error retrieving diff: {e}"

    # 4. Generate Report
    reporter = ReportGenerator()
    report = reporter.generate_report(diffs)

    # 5. Output
    print(report)


if __name__ == "__main__":
    main()
