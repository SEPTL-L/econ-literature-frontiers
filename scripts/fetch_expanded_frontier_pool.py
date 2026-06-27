#!/usr/bin/env python3
import csv
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
WORK = ROOT / "work"
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)


JOURNALS = [
    ("Management Science", "0025-1909"),
    ("Academy of Management Journal", "0001-4273"),
    ("Academy of Management Review", "0363-7425"),
    ("Administrative Science Quarterly", "0001-8392"),
    ("Organization Science", "1047-7039"),
    ("Strategic Management Journal", "0143-2095"),
    ("Journal of Management", "0149-2063"),
    ("Journal of Management Studies", "0022-2380"),
    ("Journal of International Business Studies", "0047-2506"),
    ("The Accounting Review", "0001-4826"),
    ("Journal of Accounting Research", "0021-8456"),
    ("Journal of Accounting and Economics", "0165-4101"),
    ("Contemporary Accounting Research", "0823-9150"),
    ("Review of Accounting Studies", "1380-6653"),
    ("Journal of Finance", "0022-1082"),
    ("Journal of Financial Economics", "0304-405X"),
    ("Review of Financial Studies", "0893-9454"),
    ("Journal of Business Ethics", "0167-4544"),
    ("Business Strategy and the Environment", "0964-4733"),
    ("Corporate Social Responsibility and Environmental Management", "1535-3958"),
    ("Sustainability Accounting, Management and Policy Journal", "2040-8021"),
    ("Accounting, Auditing & Accountability Journal", "0951-3574"),
    ("Energy Economics", "0140-9883"),
    ("Ecological Economics", "0921-8009"),
]


FRONTIER_PATTERNS = [
    ("AI washing / AI disclosure", r"\bAI washing\b|\bAI-washing\b|artificial intelligence disclosure|AI disclosure|generative AI|artificial intelligence|algorithmic management|algorithmic bias"),
    ("ESG / greenwashing / disclosure credibility", r"greenwashing|green hushing|greenhushing|ESG|sustainable finance|sustainability disclosure|climate disclosure|environmental disclosure|CSR disclosure|taxonomy"),
    ("patient capital / long-termism / short-termism", r"patient capital|long-term capital|long term capital|long-termism|long termism|short-termism|short termism|corporate myopia|managerial myopia|long horizon|investment horizon"),
    ("climate finance / transition risk", r"climate risk|transition risk|carbon risk|carbon premium|carbon returns|climate finance|stranded assets|carbon pricing|net zero"),
    ("supply-chain resilience / geopolitics", r"supply chain resilience|supply-chain resilience|geopolitical risk|trade war|tariff risk|global supply chains|relational supply chains|reshoring|friendshoring"),
    ("digital platforms / fintech / open banking", r"digital platform|platform economy|fintech|open banking|cashless payments|blockchain|cryptocurrency|decentralized exchange|tokenomics"),
    ("mental health / employee wellbeing", r"mental health|employee wellbeing|employee well-being|burnout|emotional exhaustion|workplace stress"),
    ("green innovation / green finance", r"green innovation|green finance|green credit|renewable energy investment|clean investments|environmental innovation|green bonds"),
]


def get_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "codex-literature-frontier/0.2 mailto:research@example.com"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def source_by_issn(issn):
    query = urllib.parse.urlencode({"filter": f"issn:{issn}", "per-page": 1})
    data = get_json(f"https://api.openalex.org/sources?{query}")
    results = data.get("results", [])
    return results[0] if results else None


def invert_abstract(index):
    if not index:
        return ""
    pairs = []
    for word, positions in index.items():
        for pos in positions:
            pairs.append((pos, word))
    return " ".join(word for _, word in sorted(pairs))


def clean_doi(doi):
    return (doi or "").replace("https://doi.org/", "").strip()


def author_names(work):
    names = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author") or {}
        if author.get("display_name"):
            names.append(author["display_name"])
    return "; ".join(names)


def journal_name(work):
    return (((work.get("primary_location") or {}).get("source") or {}).get("display_name") or "")


def landing_page(work):
    loc = work.get("primary_location") or {}
    return loc.get("landing_page_url") or work.get("doi") or work.get("id") or ""


def keywords(work):
    vals = []
    for kw in work.get("keywords") or []:
        if kw.get("display_name"):
            vals.append(kw["display_name"])
    if vals:
        return "; ".join(vals[:12])
    concepts = [
        c.get("display_name")
        for c in work.get("concepts", [])
        if c.get("display_name") and c.get("score", 0) >= 0.38
    ]
    return "; ".join(concepts[:12])


def works_for_source(source_id):
    rows = []
    cursor = "*"
    while True:
        params = urllib.parse.urlencode(
            {
                "filter": (
                    f"primary_location.source.id:{source_id},"
                    f"from_publication_date:{FROM_DATE},"
                    f"to_publication_date:{TO_DATE},"
                    "type:article"
                ),
                "per-page": 200,
                "cursor": cursor,
                "select": ",".join(
                    [
                        "id",
                        "doi",
                        "display_name",
                        "publication_date",
                        "authorships",
                        "primary_location",
                        "cited_by_count",
                        "concepts",
                        "keywords",
                        "abstract_inverted_index",
                        "open_access",
                    ]
                ),
            }
        )
        data = get_json(f"https://api.openalex.org/works?{params}")
        rows.extend(data.get("results", []))
        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
        time.sleep(0.15)
    return rows


def match_frontiers(title, abstract):
    text = f"{title}. {abstract}"
    hits = []
    for label, pattern in FRONTIER_PATTERNS:
        if re.search(pattern, text, flags=re.I):
            hits.append(label)
    return hits


def main():
    global FROM_DATE, TO_DATE
    parser = argparse.ArgumentParser(description="Fetch recent frontier literature metadata from OpenAlex.")
    default_to = date.today().isoformat()
    default_from = (date.today() - timedelta(days=730)).isoformat()
    parser.add_argument("--from-date", default=default_from, help="Start publication date, YYYY-MM-DD. Default: about two years ago.")
    parser.add_argument("--to-date", default=default_to, help="End publication date, YYYY-MM-DD. Default: today.")
    args = parser.parse_args()
    FROM_DATE = args.from_date
    TO_DATE = args.to_date
    slug = f"{FROM_DATE}_to_{TO_DATE}"

    source_rows = []
    records = []
    seen = set()
    for expected, issn in JOURNALS:
        source = source_by_issn(issn)
        if not source:
            source_rows.append({"expected": expected, "issn": issn, "source_id": "", "matched": ""})
            continue
        source_id = source["id"].split("/")[-1]
        source_rows.append(
            {"expected": expected, "issn": issn, "source_id": source_id, "matched": source.get("display_name", "")}
        )
        for work in works_for_source(source_id):
            key = work.get("doi") or work.get("id")
            if key in seen:
                continue
            seen.add(key)
            title = work.get("display_name", "")
            abstract = invert_abstract(work.get("abstract_inverted_index"))
            hits = match_frontiers(title, abstract)
            pub_date = work.get("publication_date", "")
            records.append(
                {
                    "title": title,
                    "authors": author_names(work),
                    "journal": journal_name(work),
                    "publication_date": pub_date,
                    "year": pub_date[:4],
                    "doi": clean_doi(work.get("doi", "")),
                    "url": landing_page(work),
                    "cited_by_count": work.get("cited_by_count", 0),
                    "keywords": keywords(work),
                    "abstract": abstract,
                    "frontier_hits": "; ".join(hits),
                    "hit_count": len(hits),
                    "openalex_id": work.get("id", ""),
                    "is_oa": (work.get("open_access") or {}).get("is_oa", False),
                }
            )
        print(f"fetched {expected}", flush=True)
        time.sleep(0.2)

    records.sort(key=lambda r: (r["journal"], r["publication_date"], r["title"]))
    all_path = OUT / f"expanded_core_frontier_pool_{slug}.csv"
    hits_path = OUT / f"expanded_core_frontier_hits_{slug}.csv"
    sources_path = OUT / "expanded_core_frontier_sources_openalex.csv"

    with all_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()) if records else [])
        writer.writeheader()
        writer.writerows(records)
    hit_records = [row for row in records if row["hit_count"]]
    with hits_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()) if records else [])
        writer.writeheader()
        writer.writerows(hit_records)
    with sources_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["expected", "issn", "source_id", "matched"])
        writer.writeheader()
        writer.writerows(source_rows)

    summary = {
        "date_range": {"from": FROM_DATE, "to": TO_DATE},
        "journal_count_requested": len(JOURNALS),
        "journal_count_matched": sum(bool(r["source_id"]) for r in source_rows),
        "record_count": len(records),
        "frontier_hit_count": len(hit_records),
        "outputs": {"all": str(all_path), "hits": str(hits_path), "sources": str(sources_path)},
    }
    (OUT / "expanded_core_frontier_pool_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
