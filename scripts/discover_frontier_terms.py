#!/usr/bin/env python3
import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
WORK = ROOT / "work"

NON_RESEARCH = re.compile(
    r"^editorial board$|^frontmatter|^backmatter|^contents$|^masthead$|^erratum|^corrigendum|^correction to:|annual report|call for papers|reviewers|referees",
    re.I,
)

STOP = set(ENGLISH_STOP_WORDS).union(
    {
        "article",
        "abstract",
        "based",
        "case",
        "conceptual",
        "computing",
        "cybernetics",
        "data",
        "diafiltration",
        "does",
        "dysgeusia",
        "effect",
        "effects",
        "emperipolesis",
        "empirical",
        "evidence",
        "equation",
        "fiber",
        "framework",
        "gestational",
        "impact",
        "impacts",
        "information",
        "issue",
        "key",
        "literature",
        "liquation",
        "lock",
        "mathematics",
        "model",
        "models",
        "nucleofection",
        "optical",
        "paper",
        "peer",
        "period",
        "perspective",
        "reviewed",
        "research",
        "role",
        "scp",
        "study",
        "structural",
        "systematic",
        "triacetin",
        "type",
        "using",
        "variety",
    }
)

GENERIC_ENDINGS = {
    "analysis",
    "approach",
    "case",
    "equation",
    "effect",
    "effects",
    "evidence",
    "framework",
    "impact",
    "impacts",
    "literature",
    "model",
    "modeling",
    "models",
    "perspective",
    "relationship",
    "research",
    "role",
    "study",
}


def latest_file(pattern):
    matches = sorted(OUT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No files found for {pattern} in {OUT}")
    return matches[0]


def norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_phrase(phrase):
    phrase = re.sub(r"\s+", " ", phrase.lower()).strip(" -:;,.")
    words = phrase.split()
    if not 2 <= len(words) <= 5:
        return None
    if any(len(w) < 3 for w in words):
        return None
    if words[0] in STOP or words[-1] in STOP or words[-1] in GENERIC_ENDINGS:
        return None
    if re.search(r"\d", phrase):
        return None
    if len(set(words)) == 1:
        return None
    return phrase


def phrase_key(phrase):
    words = [w for w in phrase.split() if w not in STOP and w not in GENERIC_ENDINGS]
    return " ".join(words[:3]) if words else phrase


def main():
    parser = argparse.ArgumentParser(
        description="Discover candidate frontier terms from titles, keywords, and abstracts without a predefined keyword list."
    )
    parser.add_argument("--all", dest="all_path", default=None, help="All-record CSV from the metadata fetch step.")
    parser.add_argument("--min-df", type=int, default=4, help="Minimum document frequency for a candidate phrase.")
    parser.add_argument("--top", type=int, default=300, help="Number of discovered terms to keep.")
    parser.add_argument("--recent-days", type=int, default=365, help="Recent window counted back from the newest record.")
    args = parser.parse_args()

    all_path = Path(args.all_path) if args.all_path else latest_file("expanded_core_frontier_pool_*.csv")
    df = pd.read_csv(all_path)
    df = df[~df["title"].fillna("").map(lambda v: bool(NON_RESEARCH.search(str(v).strip())))]
    df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce")
    df = df.dropna(subset=["publication_date"]).copy()
    df["period"] = df["publication_date"].dt.to_period("M").astype(str)
    df["cited_by_count"] = pd.to_numeric(df.get("cited_by_count", 0), errors="coerce").fillna(0).astype(int)
    df["title_text"] = df["title"].fillna("").map(norm)
    df["candidate_text"] = df["title"].fillna("").map(norm) + ". " + df.get("keywords", "").fillna("").map(norm)
    df["body_text"] = (
        df["title"].fillna("").map(norm)
        + ". "
        + df.get("keywords", "").fillna("").map(norm)
        + ". "
        + df["abstract"].fillna("").map(norm)
    )

    newest = df["publication_date"].max()
    recent_cutoff = newest - pd.Timedelta(days=args.recent_days)
    recent_total = int((df["publication_date"] >= recent_cutoff).sum())
    older_total = int((df["publication_date"] < recent_cutoff).sum())

    vectorizer = CountVectorizer(
        lowercase=True,
        stop_words=sorted(STOP),
        ngram_range=(2, 5),
        min_df=args.min_df,
        max_df=0.25,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z-]+\b",
        binary=True,
    )
    X = vectorizer.fit_transform(df["candidate_text"])
    terms = vectorizer.get_feature_names_out()
    support_vectorizer = CountVectorizer(
        lowercase=True,
        vocabulary=vectorizer.vocabulary_,
        ngram_range=(2, 5),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z-]+\b",
        binary=True,
    )
    support_X = support_vectorizer.fit_transform(df["body_text"])
    title_vectorizer = CountVectorizer(
        lowercase=True,
        vocabulary=vectorizer.vocabulary_,
        ngram_range=(2, 5),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z-]+\b",
        binary=True,
    )
    title_X = title_vectorizer.fit_transform(df["title_text"])

    rows = []
    timeline_rows = []
    for term in terms:
        phrase = clean_phrase(term)
        if not phrase:
            continue
        idx = X[:, vectorizer.vocabulary_[term]].nonzero()[0]
        sub = df.iloc[idx]
        support_idx = support_X[:, vectorizer.vocabulary_[term]].nonzero()[0]
        support_sub = df.iloc[support_idx]
        total_count = int(len(sub))
        recent_count = int((sub["publication_date"] >= recent_cutoff).sum())
        older_count = total_count - recent_count
        recent_rate = (recent_count + 1) / max(recent_total + 2, 1)
        older_rate = (older_count + 1) / max(older_total + 2, 1)
        lift = recent_rate / older_rate if older_rate else recent_rate
        recent_share = recent_count / total_count if total_count else 0
        title_count = int(title_X[:, vectorizer.vocabulary_[term]].sum())
        if title_count == 0:
            continue
        journal_breadth = int(sub["journal"].fillna("").nunique())
        support_count = int(len(support_sub))
        monthly_counts = sub["period"].value_counts().sort_index()
        first_seen = str(monthly_counts.index[0]) if len(monthly_counts) else ""
        latest_seen = str(monthly_counts.index[-1]) if len(monthly_counts) else ""
        peak_month = str(monthly_counts.idxmax()) if len(monthly_counts) else ""
        peak_month_count = int(monthly_counts.max()) if len(monthly_counts) else 0
        citation_signal = math.log1p(float(support_sub["cited_by_count"].median())) if support_count else 0
        score = (
            math.log1p(total_count) * 1.2
            + math.log1p(support_count) * 0.6
            + math.log1p(title_count) * 2.2
            + math.log1p(journal_breadth)
            + min(lift, 8) * 0.9
            + recent_share * 2
            + citation_signal * 0.25
        )
        rows.append(
            {
                "phrase": phrase,
                "score": round(score, 4),
                "total_count": total_count,
                "support_count": support_count,
                "recent_count": recent_count,
                "recent_share": round(recent_share, 3),
                "recent_lift": round(lift, 3),
                "first_seen": first_seen,
                "latest_seen": latest_seen,
                "peak_month": peak_month,
                "peak_month_count": peak_month_count,
                "title_count": title_count,
                "journal_breadth": journal_breadth,
                "top_journals": json.dumps(sub["journal"].value_counts().head(5).to_dict(), ensure_ascii=False),
                "example_titles": " | ".join(
                    sub.sort_values(["cited_by_count", "publication_date"], ascending=False)["title"].head(5)
                ),
            }
        )
        for period, count in monthly_counts.items():
            timeline_rows.append(
                {
                    "phrase": phrase,
                    "period": str(period),
                    "count": int(count),
                }
            )

    terms_df = pd.DataFrame(rows)
    if terms_df.empty:
        raise RuntimeError("No candidate phrases found. Try lowering --min-df.")
    terms_df = terms_df.drop_duplicates("phrase").sort_values("score", ascending=False).head(args.top)
    kept_phrases = set(terms_df["phrase"])
    timeline_df = pd.DataFrame(timeline_rows)
    timeline_df = timeline_df[timeline_df["phrase"].isin(kept_phrases)].copy()
    timeline_df = timeline_df.sort_values(["period", "count", "phrase"], ascending=[True, False, True])
    chronological_terms_df = terms_df.sort_values(["first_seen", "score"], ascending=[True, False]).copy()

    clusters = defaultdict(list)
    for row in terms_df.to_dict(orient="records"):
        clusters[phrase_key(row["phrase"])].append(row)
    cluster_rows = []
    for _, items in clusters.items():
        items = sorted(items, key=lambda r: r["score"], reverse=True)
        cluster_rows.append(
            {
                "cluster_label": items[0]["phrase"],
                "cluster_score": round(sum(float(i["score"]) for i in items[:8]), 4),
                "term_count": len(items),
                "top_terms": "; ".join(i["phrase"] for i in items[:10]),
                "total_mentions": int(sum(int(i["total_count"]) for i in items)),
                "recent_mentions": int(sum(int(i["recent_count"]) for i in items)),
                "example_titles": items[0]["example_titles"],
            }
        )
    clusters_df = pd.DataFrame(cluster_rows).sort_values("cluster_score", ascending=False).head(80)

    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    outputs = {
        "terms_csv": OUT / "discovered_frontier_terms.csv",
        "terms_chronological_csv": OUT / "discovered_frontier_terms_chronological.csv",
        "timeline_csv": OUT / "discovered_frontier_term_timeline.csv",
        "clusters_csv": OUT / "discovered_frontier_clusters.csv",
        "report_md": OUT / "discovered_frontier_report.md",
        "workbook_json": WORK / "discovered_frontier_workbook_data.json",
    }
    terms_df.to_csv(outputs["terms_csv"], index=False)
    chronological_terms_df.to_csv(outputs["terms_chronological_csv"], index=False)
    timeline_df.to_csv(outputs["timeline_csv"], index=False)
    clusters_df.to_csv(outputs["clusters_csv"], index=False)
    outputs["workbook_json"].write_text(
        json.dumps(
            {
                "terms": terms_df.to_dict(orient="records"),
                "terms_chronological": chronological_terms_df.to_dict(orient="records"),
                "timeline": timeline_df.to_dict(orient="records"),
                "clusters": clusters_df.to_dict(orient="records"),
                "metadata": {
                    "source_file": str(all_path),
                    "records": int(len(df)),
                    "newest_record": newest.date().isoformat(),
                    "recent_cutoff": recent_cutoff.date().isoformat(),
                    "method": "Unsupervised n-gram discovery from titles, keywords, and abstracts; ranked by frequency, recent lift, title salience, journal breadth, and citation signal.",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = ["# 自动发现的研究前沿候选词\n\n"]
    lines.append(f"- 来源记录：{len(df)} 条\n")
    lines.append(f"- 最近窗口：{recent_cutoff.date().isoformat()} 至 {newest.date().isoformat()}\n")
    lines.append("- 方法：不预设 AI washing、patient capital、greenwashing 等主题词；先从题名、关键词和摘要抽取候选短语，再按近期增长、题名显著性、跨期刊扩散和频次排序。\n\n")
    lines.append("## 按时间出现的候选词\n")
    for _, row in chronological_terms_df.head(40).iterrows():
        lines.append(
            f"- {row['first_seen']}：{row['phrase']}，总出现 {int(row['total_count'])}，"
            f"峰值月份 {row['peak_month']} ({int(row['peak_month_count'])})，近期增长 {row['recent_lift']}\n"
        )
    lines.append("\n")
    lines.append("## 候选前沿簇\n")
    for _, row in clusters_df.head(30).iterrows():
        lines.append(f"\n### {row['cluster_label']}\n")
        lines.append(f"- 簇得分：{row['cluster_score']}\n")
        lines.append(f"- 相关短语：{row['top_terms']}\n")
        lines.append(f"- 近期提及/总提及：{row['recent_mentions']}/{row['total_mentions']}\n")
        lines.append(f"- 代表题名：{row['example_titles']}\n")
    lines.append("\n## 使用提醒\n")
    lines.append("- 这些是自动发现的候选词，不等于最终理论概念；下一步需要人工合并同义词、剔除方法词和过宽泛词。\n")
    lines.append("- 预设关键词适合在自动发现之后做校准和命名，而不是作为第一轮筛选条件。\n")
    outputs["report_md"].write_text("".join(lines), encoding="utf-8")

    print(json.dumps({k: str(v) for k, v in outputs.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
