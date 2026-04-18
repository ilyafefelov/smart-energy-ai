from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "docs" / "Stage 2" / "literature_access_registry.json"
OUTPUT_PATH = REPO_ROOT / "docs" / "Stage 2" / "literature_pdf_links.md"
DEFAULT_RENDER_COMMAND = ".venv\\Scripts\\python.exe scripts\\render_stage2_literature_links.py"


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def effective_url(entry: dict[str, Any]) -> str:
    return entry.get("direct_pdf_url") or entry.get("fallback_url") or entry["canonical_url"]


def validate_registry(registry: dict[str, Any]) -> None:
    entries = registry["entries"]
    if registry["expected_entry_count"] != len(entries):
        raise ValueError(
            f"expected_entry_count={registry['expected_entry_count']} does not match entries={len(entries)}"
        )

    citation_keys = [entry["citation_key"] for entry in entries]
    if len(citation_keys) != len(set(citation_keys)):
        raise ValueError("Duplicate citation_key values found in literature_access_registry.json")


def render_front_matter(registry: dict[str, Any]) -> list[str]:
    return [
        "---",
        'title: "Stage 2 — Literature PDF links (canonical)"',
        f'version: {registry["version"]}',
        f'created: {registry["created"]}',
        'owner: user',
        f'source_bib: {registry["source_bib"]}',
        f'description: "{registry["description"]}"',
        "---",
        "",
    ]


def render_summary(registry: dict[str, Any], entries: list[dict[str, Any]]) -> list[str]:
    status_counts = Counter(entry["access_status"] for entry in entries)
    source_counts = Counter(entry["source_type"] for entry in entries)
    lines = [
        "# Literature PDF Links — Stage 2 (canonical)",
        "",
        "Generated file: update `literature_access_registry.json` and rerun the renderer instead of editing this file directly.",
        "",
        "## Workflow",
        "",
        f"- Registry source: `{REGISTRY_PATH.relative_to(REPO_ROOT).as_posix()}`",
        f"- Render command: `{registry.get('render_command', DEFAULT_RENDER_COMMAND)}`",
        f"- Canonical entry count: {len(entries)}",
        "",
        "## Registry Summary",
        "",
        "Source types:",
        "",
    ]
    for source_type, count in sorted(source_counts.items()):
        lines.append(f"- `{source_type}`: {count}")
    lines.extend(["", "Access statuses:", ""])
    for access_status, count in sorted(status_counts.items()):
        lines.append(f"- `{access_status}`: {count}")
    lines.append("")
    return lines


def render_code_block(header: str, body: str) -> list[str]:
    return [header, "", "```text", body, "```", ""]


def render_lists(entries: list[dict[str, Any]]) -> list[str]:
    urls = [effective_url(entry) for entry in entries]
    lines = [
        "## Canonical URL Exports",
        "",
    ]
    lines.extend(render_code_block("Comma-separated:", ", ".join(urls)))
    lines.extend(render_code_block("Newline-separated:", "\n".join(urls)))
    lines.extend(render_code_block("Space-separated:", " ".join(urls)))
    return lines


def render_registry_table(entries: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Normalized Registry",
        "",
        "| citation_key | source_type | access_status | effective_url | needs_followup | notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        lines.append(
            "| {citation_key} | {source_type} | {access_status} | {effective_url} | {needs_followup} | {notes} |".format(
                citation_key=entry["citation_key"],
                source_type=entry["source_type"],
                access_status=entry["access_status"],
                effective_url=effective_url(entry),
                needs_followup=str(entry["needs_followup"]).lower(),
                notes=entry.get("notes", "").replace("|", "/"),
            )
        )
    lines.append("")
    return lines


def render_official_refs(registry: dict[str, Any]) -> list[str]:
    lines = ["## Official law / regulatory links", ""]
    for item in registry.get("official_references", []):
        lines.append(f'- {item["label"]}: {item["url"]} ({item["relation"]})')
    lines.append("")
    return lines


def render_followups(entries: list[dict[str, Any]]) -> list[str]:
    unresolved = [entry for entry in entries if entry.get("needs_followup")]
    lines = [
        "## Unresolved / follow-up queue",
        "",
        "Entries with `needs_followup=true` still need direct PDF, accepted manuscript, or repository checks.",
        "",
    ]
    for entry in unresolved:
        lines.append(f'- `{entry["citation_key"]}`: {entry["canonical_url"]}')
    lines.append("")
    return lines


def render_changelog(registry: dict[str, Any]) -> list[str]:
    lines = ["## Changelog", ""]
    for item in registry.get("changelog", []):
        lines.append(f'- {item["version"]} ({item["date"]}): {item["summary"]}')
    lines.append("")
    return lines


def render() -> str:
    registry = load_registry()
    validate_registry(registry)
    entries = registry["entries"]
    parts: list[str] = []
    parts.extend(render_front_matter(registry))
    parts.extend(render_summary(registry, entries))
    parts.extend(render_lists(entries))
    parts.extend(render_registry_table(entries))
    parts.extend(render_official_refs(registry))
    parts.extend(render_followups(entries))
    parts.extend(render_changelog(registry))
    return "\n".join(parts).rstrip() + "\n"


def write_output() -> str:
    content = render()
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    return content


def check_output() -> bool:
    expected = render()
    existing = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    return existing == expected


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Stage 2 literature links markdown from the access registry.")
    parser.add_argument("--check", action="store_true", help="Fail if the rendered markdown is out of date.")
    args = parser.parse_args()

    if args.check:
        is_current = check_output()
        print("up-to-date" if is_current else "out-of-date")
        return 0 if is_current else 1

    write_output()
    print(
        f"Rendered {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()} from {REGISTRY_PATH.relative_to(REPO_ROOT).as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
