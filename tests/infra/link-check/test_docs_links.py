"""Link-check and docs-portal tests for Feature 10 (Docs portal)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = REPO_ROOT / "docs"
SITE_DIR = DOCS_DIR / "site"

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _iter_markdown_files() -> list[Path]:
    if not DOCS_DIR.is_dir():
        return []
    return sorted(DOCS_DIR.rglob("*.md"))


def test_docs_site_config_and_index_exist() -> None:
    """Docs portal must define a valid mkdocs.yml and landing index.md."""
    mkdocs_path = SITE_DIR / "mkdocs.yml"
    index_path = SITE_DIR / "index.md"
    assert mkdocs_path.is_file(), f"Missing MkDocs config: {mkdocs_path}"
    assert index_path.is_file(), f"Missing docs landing page: {index_path}"

    config = yaml.safe_load(mkdocs_path.read_text(encoding="utf-8"))
    assert isinstance(config, dict), "mkdocs.yml must parse to a YAML mapping"
    assert config.get("site_name"), "mkdocs.yml must set site_name"
    assert config.get("nav"), "mkdocs.yml must define nav"


def test_style_guide_exists() -> None:
    """Documentation style guide must exist under docs/guides/style-guide.md."""
    style_guide = DOCS_DIR / "guides" / "style-guide.md"
    assert style_guide.is_file(), f"Missing style guide: {style_guide}"
    first_line = style_guide.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("# "), "style-guide.md must begin with an H1 heading"


def test_no_broken_relative_links_in_docs() -> None:
    """Every relative Markdown link in docs/ must resolve to an existing file."""
    md_files = _iter_markdown_files()
    assert md_files, "Expected at least one Markdown file under docs/"

    broken: list[str] = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_RE.finditer(content):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (md_file.parent / target_path).resolve()
            if not resolved.exists():
                broken.append(f"{md_file.relative_to(REPO_ROOT)} -> {target}")

    assert not broken, f"Broken relative links found: {broken}"
