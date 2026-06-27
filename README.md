# econ-literature-frontiers

Use this skill to run a repeatable literature-frontier workflow for economics, finance, management, accounting, sustainability, and adjacent social-science research.

## Workflow

1. **Clarify scope**
   - Time range, usually the last 2-5 years.
   - Journal pool: economics core, expanded management/accounting/finance, or custom.
   - Output target: Zotero import, Excel workbook, Markdown report, or all.
   - Whether the user wants broad discipline mapping or concrete frontier concepts.

2. **Choose a journal and keyword configuration**
   - Read `references/journal_pools.md` when selecting or editing journal pools.
   - Read `references/frontier_keywords.md` when selecting or editing concrete research-frontier keywords.
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

5. **Analyze concrete frontiers**
   - Use `scripts/analyze_expanded_frontiers.py` after metadata is fetched.
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

- Frontiers ranked by hit count and recent share.
- Direct concept counts.
- Representative papers with journal, date, DOI, and citation count where available.
- A short explanation of whether a term is already established or still an adjacent/emerging construct.
- Practical research directions: research question, possible variables, data source, and identification strategy when useful.

## Interpretation Rules

- Be explicit about database limits. OpenAlex metadata is useful for discovery but not a substitute for Web of Science/Scopus indexing decisions.
- Filter non-research records such as editorial boards, front matter, referee lists, calls for papers, annual reports, and corrections.
- Avoid overclaiming novelty from raw frequency. A term with few direct hits may still be a good research opportunity if adjacent constructs are active.
- If a user asks for examples like “AI washing” or “patient capital,” search both the exact term and operational neighbors.

## Bundled Resources

- `scripts/fetch_expanded_frontier_pool.py`: OpenAlex metadata fetcher for expanded journal pools and frontier keyword hits.
- `scripts/analyze_expanded_frontiers.py`: concrete-frontier analyzer that produces CSV, JSON, and Markdown outputs.
- `scripts/build_expanded_frontier_workbook.mjs`: workbook builder for final Excel output.
- `scripts/import_ris_chunks_to_selected_zotero.py`: helper pattern for importing RIS chunks into the currently selected Zotero collection after verification.
- `references/journal_pools.md`: editable journal-pool guidance.
- `references/frontier_keywords.md`: editable keyword and concept guidance.
- `references/workflow.md`: detailed implementation notes and common pitfalls.
