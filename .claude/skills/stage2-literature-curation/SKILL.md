---
name: stage2-literature-curation
description: 'Review Stage 2 research docs, extract and verify sources, rank academic and practical relevance, update docs/Stage 2 bibliography and tracker artifacts, and turn literature into concrete Smart Energy AI MVP upgrade recommendations. Use when auditing thesis sources, adding papers to BibTeX, generating ranked reading lists, creating APA bibliography outputs, or mapping papers to implementation work.'
argument-hint: 'Describe the docs or research files to audit and whether you want bibliography updates, ranking, APA output, or MVP implementation recommendations.'
user-invocable: true
---

# Stage 2 Literature Curation

## What This Skill Does

Use this skill for the repository's recurring thesis and diploma workflow:

- review research notes, reports, markdown files, and PDFs in `docs/Stage 2/`
- extract candidate sources and verify what is actually usable
- rank sources by academic strength, practical value, recency, and MVP relevance
- update the durable literature artifacts in the repository
- translate literature into concrete development changes for the Smart Energy AI MVP

This skill is project-specific. It assumes the current Stage 2 literature workflow documented in `AGENTS.md` and the repo-specific overlay in `.github/copilot-instructions.md`.

## Canonical Repo Anchors

- `docs/Stage 2/` is the canonical literature workspace.
- `docs/Stage 2/diploma_bibliography.bib` is the machine-friendly citation source of truth.
- `docs/Stage 2/diploma_literature_tracker.md` is the operational tracker for ranking, read order, status, and MVP mapping.
- `docs/Stage 2/diploma_bibliography_apa.md` is the thesis-ready human-readable bibliography companion.
- `docs/Stage 2/README.md` should be refreshed when Stage 2 artifacts change materially.
- `AGENTS.md` is the source of truth for Stage 2 workflow rules.

## When to Use

Use this skill when the user asks to:

- review or audit thesis, diploma, literature, bibliography, or research docs
- find all sources actually used in the MVP or research notes
- rank sources by importance, novelty, peer-review quality, or practical value
- add sources to the BibTeX bibliography and keep the tracker aligned
- create or refresh APA bibliography outputs
- generate a reading shortlist such as "top 5 to read now"
- convert literature findings into concrete development priorities for forecasting, optimization, EMS, HEMS, or battery-control work

Do not use this skill for ordinary runtime debugging, feature implementation without a literature component, or generic code review.

## Workflow

### 1. Start from the repo workflow and working surface

1. Read `AGENTS.md` and `.github/copilot-instructions.md` if the current context does not already contain them.
2. Check the Beads workflow requirement first.
3. If Beads is blocked by local board drift or schema drift, state the blocker clearly and continue with scoped docs work.
4. Treat `docs/Stage 2/` as the default search surface unless the user points to additional files.

### 2. Gather source-bearing materials

Read only enough to identify the local source-bearing artifacts:

- Stage 2 markdown notes
- report-style summaries
- tracked PDFs or PDF-derived notes
- existing bibliography and tracker files
- any user-mentioned files outside the default set

Prefer targeted reads over broad exploration. If a source is only mentioned indirectly in a report, treat it as a candidate until metadata is verified.

### 3. Extract candidate sources and metadata

For each candidate source, capture the strongest verified metadata available:

- authors
- title
- year
- journal, conference, preprint server, or practical publisher
- DOI if available
- stable URL if available
- why the source matters for the MVP or thesis

If metadata is incomplete or parsing is unreliable, do not invent missing fields. Record the limitation explicitly.

### 4. Classify source quality and placement

Use these decision rules consistently:

- Peer-reviewed academic source with strong thesis relevance: keep in the main academic bibliography flow.
- Methodology anchor for decision-focused or predict-then-optimize framing: keep in the academic set even if not domain-specific.
- Supporting academic source that informs context or adjacent methods: keep in supporting sections.
- Preprint, weak-quality journal, unclear venue, or low-confidence metadata: keep provisional and out of the strict main bibliography.
- Legal, regulatory, vendor, tooling, market-news, or other practical material: move to appendix or normative/practical sections.

Never promote a source into the strict core academic set only because a report or note cites it.

### 5. Rank sources for reading and implementation value

Rank sources against the current project need, not in the abstract. Use these factors:

1. direct relevance to replacing or improving the current MVP
2. academic strength and trustworthiness
3. recency when it matters for rapidly moving model families
4. specificity of implementable guidance
5. fit with the repo's current architecture and development path

For Smart Energy AI, prefer sources that improve one or more of these areas:

- price forecasting beyond RandomForest
- decision-aware or value-oriented model selection
- rolling-horizon or richer deterministic optimization
- incentive-aware demand response
- residential EMS or HEMS realism
- battery-state, degradation, or operational realism

### 6. Update the durable repo artifacts

When making changes, keep the artifacts synchronized:

- update `diploma_bibliography.bib` for new or corrected citations
- update `diploma_literature_tracker.md` in the same task
- update `diploma_bibliography_apa.md` when thesis-ready output is needed
- refresh `docs/Stage 2/README.md` when new literature artifacts are added

If the workflow itself changes materially, update `AGENTS.md` or the repo overlay only when warranted.

### 7. Translate literature into concrete engineering action

Do not stop at bibliographic cleanup. Convert strong sources into MVP guidance:

- which source should be read first
- what model, optimizer, or system layer it upgrades
- the smallest practical implementation step
- what payoff the team should expect

Prefer concrete changes over vague statements like "improve the model".

When the user asks for a shortlist, prefer this exact table shape:

| Source with url link | Upgrade Type | Concrete MVP Change | What to implement in practice | Expected payoff |
| --- | --- | --- | --- | --- |
| [ExampleSource](https://doi.org/example) | Model upgrade | Replace RF with a stronger forecasting model | Train and benchmark the new model on the current data pipeline | Better forecast accuracy and stronger arbitrage decisions |

### 8. Validate narrowly

After editing docs, run focused validation on the touched artifacts:

- targeted text search for new keys or sections
- exact readback of inserted blocks when formatting matters
- README entry checks when new files were added

If the task is docs-only, content validation is enough. Do not claim runtime validation you did not run.

## Tracker Status Rules

Keep tracker status fields honest:

- `Read = done` only when the source itself was meaningfully reviewed, not just cited by another note.
- `Discussed = done` only when the source's role in the thesis or MVP was actually analyzed.
- `Cited = done` when the bibliography artifact already contains the source.
- `Implemented = planned` unless code or system behavior has been concretely changed.

When source confidence is weak, prefer `partial` and explain why.

## Known Branching Decisions

### If the source is strong but not directly implementable

Keep it as a review or framing anchor and connect it to thesis structure rather than immediate code changes.

### If the source is promising but venue quality is weak

Keep it in the tracker and appendix as directional evidence only. Use it to discover stronger follow-up literature, not as a main thesis pillar.

### If a PDF is present but not parseable

Record the limitation in the tracker known gaps section and avoid overstating what was verified.

### If the user asks for "what to build next"

Prefer the papers that most directly improve the current repo path instead of the most general review papers.

## Completion Criteria

The task is complete when all requested items are true:

- source additions or corrections are reflected in the bibliography
- tracker classification and read order match the bibliography changes
- provisional and practical sources are kept out of the strict academic core
- any new Stage 2 artifact is discoverable from the Stage 2 README
- the user receives a concrete reading or implementation shortlist when requested
- blockers, unparseable sources, and metadata uncertainty are stated explicitly

## Example Prompts

- `/stage2-literature-curation audit docs/Stage 2 for sources actually used in our MVP and update the bibliography and tracker`
- `/stage2-literature-curation rank the best papers to replace RandomForest forecasting and connect them to implementation tasks`
- `/stage2-literature-curation create a strict APA bibliography and move weak or practical sources to an appendix`
- `/stage2-literature-curation read the new report in docs/Stage 2, extract strong sources, and give me a top 5 table for what to implement next`