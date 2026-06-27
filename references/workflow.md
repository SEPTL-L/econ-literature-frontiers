# Workflow Notes

## Recommended Run Order

1. Edit journal pools and keyword patterns in the fetch/analyze scripts or use exported database files from the user.
2. Fetch metadata with OpenAlex or read exported records.
3. Save raw records and matched sources.
4. Filter non-research items.
5. Run automatic frontier discovery on the full record pool, using titles, keywords, and abstracts.
6. Read chronological keyword outputs to separate persistent themes from newly appearing terms.
7. Interpret discovered terms: merge synonyms, remove generic method phrases, and name candidate fronts.
8. Run directed keyword analysis only as a second-stage check for user examples or known concepts.
9. Build workbook and Markdown report.
10. If Zotero is requested, create or confirm a dedicated Zotero collection and import records in chunks.

## Zotero Safety

- Always check Zotero status and selected target before importing.
- Ask the user to create/select a dedicated collection if collection creation is not available through the local API.
- Import in chunks when records exceed a few hundred.
- Use DOI-based deduplication where possible.
- Do not attach PDFs by default. First build a题录 library, identify representative papers, then fetch PDFs for the selected subset.

## Common Pitfalls

- OpenAlex may include non-research entries such as editorial boards, front matter, referee lists, annual reports, and calls for papers.
- OpenAlex concepts can be noisy. For concrete frontier extraction, prefer title and abstract over broad concept keywords.
- Do not treat predefined keywords as the discovery method. They are for calibration after the corpus has produced candidate terms.
- Exact terms such as `AI washing` and `patient capital` may have few direct hits. Search nearby operational terms before concluding the topic is absent.
- Broad terms like `AI`, `ESG`, or `risk` can overmatch. Prefer combinations and representative-paper inspection.

## Deliverable Shape

Good outputs usually include:

- `*_pool.csv`: all fetched records.
- `*_hits.csv`: records that hit frontier keywords.
- `discovered_frontier_terms.csv`: automatically extracted candidate phrases.
- `discovered_frontier_terms_chronological.csv`: candidate phrases sorted by first-seen month.
- `discovered_frontier_term_timeline.csv`: long-form monthly counts for candidate phrases.
- `discovered_frontier_clusters.csv`: lightweight groups of related candidate phrases.
- `*_theme_summary.csv`: frontier-level counts and signals.
- `*_representatives.csv`: representative papers by frontier.
- `*_direct_concepts.csv`: exact concept counts.
- `*_emerging_phrases.csv`: title phrases.
- `.xlsx`: readable workbook.
- `.md`: concise report for writing and discussion.
