---
name: econ-literature-frontiers
description: Economic and management literature frontier review workflow. Use when Codex needs to search recent English core journals, build Zotero-ready literature libraries, automatically discover frontier terms from titles, keywords, and abstracts, cluster concrete research fronts, or produce Excel/Markdown reports with representative papers and research directions.
---

# econ-literature-frontiers

Use this skill to run a repeatable literature-frontier workflow for economics, finance, management, accounting, sustainability, and adjacent social-science research.

## Workflow

1. **Clarify scope**
   - Time range, usually the last 2-5 years.
   - Journal pool: economics core, expanded management/accounting/finance, or custom.
   - Output target: Zotero import, Excel workbook, Markdown report, or all.
   - Whether the user wants broad discipline mapping or concrete frontier concepts.

2. **Choose a journal pool, not a conclusion**
   - Read `references/journal_pools.md` when selecting or editing journal pools.
   - Do not require the user to name frontiers such as `AI washing`, `patient capital`, or `greenwashing` up front.
   - Read `references/frontier_keywords.md` only after automatic discovery, when calibrating labels, merging synonyms, or checking user-specified concepts.
   - Prefer OpenAlex for open metadata. Use Web of Science, Scopus, EconLit, CNKI, or school databases only when the user provides exported files or authenticated access.

3. **Fetch metadata**
   - Use `scripts/fetch_expanded_frontier_pool.py` for OpenAlex journal-pool searches.
   - Outputs are CSV files under `outputs/` relative to the skill folder.
   - Expected fields: title, authors, journal, publication date, DOI, URL, citation count, keywords, abstract, frontier hits.

4. **Import into Zotero only after confirming the target collection**
   - If Zotero is involved, use the Zotero skill/tooling first.
   - Always verify the selected collection before importing.
   - Prefer importing RIS chunks into a new collection, not the user’s active working collection.
   - Treat Zotero writes as explicit library modifications.

5. **Discover concrete frontiers before directed keyword checks**
   - First use `scripts/discover_frontier_terms.py` on the all-record CSV to extract candidate frontier phrases from titles, keywords, and abstracts without a predefined keyword list.
   - Rank candidates by frequency, recent lift, title salience, cross-journal breadth, and citation signal.
   - Also inspect chronological outputs: first-seen month, latest-seen month, peak month, and monthly counts.
   - Treat the output as candidate fronts requiring interpretation: merge synonyms, remove generic methods, and name clusters in economic language.
   - Then use `scripts/analyze_expanded_frontiers.py` only for second-stage calibration, exact concept checks, representative papers, or user-specified topics.
   - Distinguish direct concepts from adjacent concepts:
     - Direct: terms appear in title/abstract, e.g. `greenwashing`, `generative AI`, `managerial myopia`.
     - Adjacent: terms do not appear directly but can be operationalized, e.g. `patient capital` via investor horizon, debt maturity, fund flow pressure.
   - Do not report only broad fields like “finance” or “labor economics” when the user asks what scholars are recently doing.

6. **Generate deliverables**
   - Use `scripts/build_expanded_frontier_workbook.mjs` to build a workbook from `work/expanded_concrete_frontier_workbook_data.json`.
   - If using the spreadsheet runtime, follow the Spreadsheets skill: load workspace dependencies, symlink `node_modules`, export `.xlsx`, and visually verify key sheets.
   - Also provide a Markdown report when the user wants readable synthesis.

## Output Standards

For concrete-frontier reports, include:

- Automatically discovered candidate terms and clusters, with the scoring logic stated.
- A chronological keyword table showing when candidate terms first appear, peak, and persist.
- Frontiers ranked by recent lift, title salience, journal breadth, and hit count.
- Direct concept counts.
- Representative papers with journal, date, DOI, and citation count where available.
- A short explanation of whether a term is already established or still an adjacent/emerging construct.
- Practical research directions: research question, possible variables, data source, and identification strategy when useful.

## Interpretation Rules

- Be explicit about database limits. OpenAlex metadata is useful for discovery but not a substitute for Web of Science/Scopus indexing decisions.
- Filter non-research records such as editorial boards, front matter, referee lists, calls for papers, annual reports, and corrections.
- Avoid overclaiming novelty from raw frequency. A term with few direct hits may still be a good research opportunity if adjacent constructs are active.
- If a user asks for examples like “AI washing” or “patient capital,” search both the exact term and operational neighbors.
- Do not let user examples become the search frame unless the user explicitly asks for a directed search. In exploratory mode, examples are sanity checks, not filters.

## Bundled Resources

- `scripts/fetch_expanded_frontier_pool.py`: OpenAlex metadata fetcher for expanded journal pools and frontier keyword hits.
- `scripts/discover_frontier_terms.py`: unsupervised candidate-frontier extractor from titles, keywords, and abstracts, including chronological keyword outputs.
- `scripts/analyze_expanded_frontiers.py`: concrete-frontier analyzer that produces CSV, JSON, and Markdown outputs.
- `scripts/build_expanded_frontier_workbook.mjs`: workbook builder for final Excel output.
- `scripts/import_ris_chunks_to_selected_zotero.py`: helper pattern for importing RIS chunks into the currently selected Zotero collection after verification.
- `references/journal_pools.md`: editable journal-pool guidance.
- `references/frontier_keywords.md`: editable keyword and concept guidance.
- `references/workflow.md`: detailed implementation notes and common pitfalls.
