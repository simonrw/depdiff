# Project Plan: Dependency Diff Hunter

## 1. Project Overview

**Goal:** Create a security auditing tool that accepts a unified diff of a `requirements.txt` file (showing version bumps). It generates a unified diff of the actual source code between the old and new versions of every changed package. This allows for rapid scanning of code changes in dependencies to detect supply chain attacks or vulnerabilities.

## 2. High-Level Architecture

The system operates as a linear pipeline with a hybrid retrieval strategy. It prioritizes using Git for cleaner diffs but includes a robust fallback to downloading artifacts (wheels/tarballs) if Git tags are missing.

### Workflow Diagram

    graph TD
        A[Input: requirements.txt Diff] -->|Parse| B(Module A: Diff Parser)
        B --> C{Module B: Retriever}

        subgraph "Retrieval Logic"
        C -->|Strategy 1| D[Check PyPI Metadata for Git URL]
        D --> E{Git Repo Found?}
        E -->|Yes| F[Clone Repo]
        F --> G{Tags Exist?}
        G -->|Yes| H[Git Diff: old_tag vs new_tag]

        E -->|No| I[Strategy 2: Artifact Fallback]
        G -->|No| I
        I --> J[Download .tar.gz / .whl]
        J --> K[Extract & Normalize Dirs]
        K --> L[File-by-File Diff]
        end

        H --> M(Module C: Diff Aggregator)
        L --> M
        M --> N[Module D: Report Generator]
        N --> O[Output: Consolidated Source Diff]

---

## 3. Module Breakdown

### Module A: Diff Parser

**Responsibility:** Parse the input stream (stdin/file) to identify package changes.

- **Input:** Unified diff string.
- **Logic:**
  - Identify lines starting with `+` or `-`.
  - Parse standard Python requirement specifiers (e.g., `requests==2.25.1`).
  - Pair removals and additions to determine a "Version Transition" (e.g., `2.25.1` -> `2.26.0`).
- **Output:** List of `DependencyChange` objects `{name, old_version, new_version}`.

### Module B: The Hybrid Retriever

**Responsibility:** Obtain the diff using the best available source.

#### Strategy 1: The Git Path (Priority)

1.  **Metadata Fetch:** Query PyPI JSON API for `project_urls` (Source/Repository/Home).
2.  **Cloning:** If a valid Git URL is found, clone to a temporary cache.
3.  **Tag Resolution:** Convert version strings to Git tags.
    - _Logic:_ Try exact match (`1.0.3`) first. If missing, try prefix match (`v1.0.3`).
4.  **Native Diff:** Execute `git diff <old_tag> <new_tag>`.

#### Strategy 2: The Artifact Path (Fallback)

_Triggered if: No Git URL found, Git clone fails, or Tags are missing._

1.  **Download:** Fetch `.tar.gz` (preferred) or `.whl` from PyPI for both versions.
2.  **Extraction:** Unzip/Untar to temp directories.
3.  **Normalization:** Handle top-level directory variations (e.g., `package-1.0.0/src/...` vs `src/...`).

### Module C: Source Comparator (Fallback Engine)

**Responsibility:** If the Git path failed, this module performs the diff on the extracted directories.

- **Recursive Walk:** Match files between `Dir_Old` and `Dir_New`.
- **Comparison:** Generate unified diffs for text files.
- **Binary Handling:** Detect and ignore binary files (don't print garbage characters).

### Module D: Report Generator

**Responsibility:** Format the output for human readability.

- **Headers:** Add visual separators between packages (e.g., `=== DIFF FOR PACKAGE: REQUESTS ===`).
- **Filtering:** Optional filtering of "noise" files (docs, tests, existing git metadata).

---

## 4. Implementation Checklist

### Phase 1: Input Parsing

- [ ] **Input Reader:** Implement reading from `stdin` or file path.
- [ ] **Regex Parsing:** Logic to parse lines like `- package==1.0.0` and `+ package==1.0.1`.
- [ ] **Transition Logic:** Group the `-` and `+` lines to form a complete update object.

### Phase 2a: Repository Discovery & Git Integration

- [ ] **Metadata Client:** Function to fetch JSON from `pypi.org/pypi/<name>/json`.
- [ ] **URL Extractor:** Parse `project_urls` to find valid GitHub/GitLab/Bitbucket URLs.
- [ ] **Git Cloner:** Implement `subprocess` calls to `git clone` (consider `--bare` or `--filter=blob:none` for speed).
- [ ] **Tag Matcher:** Implement the logic: `check tag "ver" -> if fail -> check tag "v{ver}"`.
- [ ] **Git Diff Wrapper:** Run `git diff` between resolved tags and capture stdout.

### Phase 2b: Artifact Fallback (The Safety Net)

- [ ] **Fallback Trigger:** Try/Except block around Phase 2a to catch missing tags/repos.
- [ ] **Downloader:** Logic to download sdist/wheels to temp folders.
- [ ] **Extractor:** `zipfile` and `tarfile` handling.
- [ ] **Dir Diff:** Implementation of a recursive directory comparison to generate unified diff text.

### Phase 3: Orchestration & Output

- [ ] **Main Loop:** Iterate through parsed changes, attempt Git Diff, fallback to Artifact Diff.
- [ ] **Output Formatter:** Specific headers to separate package streams.
- [ ] **Cleanup:** Ensure temp directories are deleted after execution.

---

## 5. Testing Strategy

### Unit Testing "The Parser"

- **Test:** Standard version bump.
- **Test:** New dependency added (no old version).
- **Test:** Dependency removed (no new version).
- **Test:** Malformed or commented input in requirements.txt.

### Unit Testing "The Retriever" (Mocked)

- **Test: Git URL Discovery:** Provide mock PyPI JSON, verify correct GitHub URL extraction.
- **Test: Tag Resolution:**
  - Mock `git tag` output containing `v1.0.0`.
  - Request `1.0.0`.
  - Assert `v1.0.0` is returned.
- **Test: Tag Failure:**
  - Mock `git tag` output missing the specific version.
  - Assert function returns `None` (signaling fallback).

### Unit Testing "The Comparator"

- **Test: Content Change:** Create two temp files, verify diff output format.
- **Test: Binary File:** Ensure binary files result in "Binary files differ" or skip, not crashes.
- **Test: New File:** Ensure a file present in New but not Old appears as 100% added lines.

### Integration Testing

- **Dry Run:** Point the tool at a local dummy repository instead of the internet to verify the full `Parse -> Clone -> Diff` pipeline.
