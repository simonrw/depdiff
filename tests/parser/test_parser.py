from pathlib import Path

from depdiff.models import DependencyChange
from depdiff.parser import DiffParser


def test_parse_update():
    diff = """
- requests==2.25.1
+ requests==2.26.0
"""
    parser = DiffParser()
    changes = parser.parse(diff)

    assert len(changes) == 1
    assert changes[0] == DependencyChange(
        name="requests", old_version="2.25.1", new_version="2.26.0"
    )


def test_parse_addition():
    diff = """
+ flask==2.0.1
"""
    parser = DiffParser()
    changes = parser.parse(diff)

    assert len(changes) == 1
    assert changes[0] == DependencyChange(
        name="flask", old_version=None, new_version="2.0.1"
    )


def test_parse_removal():
    diff = """
- numpy==1.19.5
"""
    parser = DiffParser()
    changes = parser.parse(diff)

    assert len(changes) == 1
    assert changes[0] == DependencyChange(
        name="numpy", old_version="1.19.5", new_version=None
    )


def test_parse_multiple_changes():
    diff = """
- requests==2.25.1
+ requests==2.26.0
+ flask==2.0.1
- numpy==1.19.5
"""
    parser = DiffParser()
    changes = parser.parse(diff)

    # Sort by name to ensure order for assertion
    changes.sort(key=lambda x: x.name)

    assert len(changes) == 3

    # flask (Addition)
    assert changes[0].name == "flask"
    assert changes[0].is_addition

    # numpy (Removal)
    assert changes[1].name == "numpy"
    assert changes[1].is_removal

    # requests (Update)
    assert changes[2].name == "requests"
    assert changes[2].is_update


def test_parse_ignore_irrelevant_lines():
    diff = """
@@ -1,3 +1,3 @@
 # strict dependency
-requests==2.25.1
+requests==2.26.0
 some unrelated text
"""
    parser = DiffParser()
    changes = parser.parse(diff)

    assert len(changes) == 1
    assert changes[0].name == "requests"


def test_integration():
    source_path = Path(__file__).parent / "examples" / "1.txt"
    contents = source_path.open().read()

    parser = DiffParser()
    changes = parser.parse(contents)

    assert changes == [
        DependencyChange(name="cbor", old_version="5.7.1", new_version="5.8.0"),
        DependencyChange(
            name="certifi", old_version="2025.11.12", new_version="2026.1.4"
        ),
        DependencyChange(name="joserfc", old_version="1.6.0", new_version="1.6.1"),
        DependencyChange(name="jsii", old_version="1.123.0", new_version="1.125.0"),
        DependencyChange(name="json5", old_version="0.12.1", new_version="0.13.0"),
    ]
