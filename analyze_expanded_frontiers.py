#!/usr/bin/env python3
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
WORK = ROOT / "work"


def latest_file(pattern):
    matches = sorted(OUT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No files found for {pattern} in {OUT}")
    return matches[0]


THEMES = [
    {
        "theme": "AI 与算法经济：生成式 AI、算法管理、金融 AI",
        "signals": ["generative ai", "artificial intelligence", "machine learning", "algorithmic", "automation", "fintech", "open banking"],
        "question": "AI 如何改变工作效率、组织决策、金融分析、信贷分配和平台竞争。",
        "direction": "可做 AI 采用/披露与企业绩效、劳动替代、分析师行为、算法偏见或金融科技竞争。",
    },
    {
        "theme": "AI 漂洗与技术叙事可信度",
        "signals": ["ai washing", "ai-washing", "artificial intelligence disclosure", "ai disclosure", "generative ai disclosure"],
        "question": "企业是否借 AI 叙事获得资本市场或声誉收益，而没有真实 AI 能力或投入。",
        "direction": "当前英文核心中直接命中少，适合扩展到管理、会计和传播领域，构造 AI 叙事-真实能力偏离指标。",
    },
    {
        "theme": "ESG/绿色漂洗与披露可信度",
        "signals": ["greenwashing", "green hushing", "greenhushing", "esg", "sustainability disclosure", "climate disclosure", "environmental disclosure", "csr disclosure", "taxonomy"],
        "question": "ESG、气候和可持续披露究竟传递真实行动，还是服务于融资、声誉或监管回应。",
        "direction": "可做 ESG 漂洗测度、文本承诺与实际排放/投资偏离、绿色分类标准的资本市场后果。",
    },
    {
        "theme": "耐心资本、长期主义与企业短视",
        "signals": ["patient capital", "long-term capital", "long term capital", "long-termism", "long termism", "short-termism", "short termism", "corporate myopia", "managerial myopia", "investment horizon", "long horizon"],
        "question": "长期资本能否缓解企业短视，促进创新、绿色转型和高质量投资。",
        "direction": "直接用 patient capital 的文献少，可用长期投资者、持股期限、债务期限、基金赎回压力来构造经验研究。",
    },
    {
        "theme": "气候金融、转型风险与碳定价",
        "signals": ["climate risk", "transition risk", "carbon risk", "carbon premium", "carbon returns", "climate finance", "stranded assets", "carbon pricing", "net zero"],
        "question": "气候风险和转型政策如何进入资产价格、银行贷款、企业投资与国际资本流动。",
        "direction": "可做转型风险暴露、碳价格冲击、气候新闻、银行绿色偏好与企业融资成本。",
    },
    {
        "theme": "绿色创新、绿色金融与清洁投资",
        "signals": ["green innovation", "green finance", "green credit", "green bond", "green bonds", "renewable energy investment", "clean investments", "environmental innovation"],
        "question": "绿色金融工具和环境政策是否真正推动清洁投资与绿色创新。",
        "direction": "可做绿色信贷/债券政策、清洁投资新闻冲击、绿色专利质量与企业转型。",
    },
    {
        "theme": "供应链韧性、地缘政治与贸易战",
        "signals": ["supply chain resilience", "supply-chain resilience", "geopolitical risk", "trade war", "tariff risk", "global supply chains", "relational supply chains", "reshoring", "friendshoring"],
        "question": "地缘政治和贸易政策冲击如何重塑供应链、企业融资与国际分工。",
        "direction": "可做贸易战风险、供应链关系融资、供应链韧性披露、出口管制与企业网络调整。",
    },
    {
        "theme": "数字平台、开放银行与金融科技竞争",
        "signals": ["digital platform", "platform economy", "fintech", "open banking", "cashless payments", "blockchain", "cryptocurrency", "decentralized exchange", "tokenomics"],
        "question": "数据开放、平台进入和区块链机制如何改变竞争、信任、金融包容和消费者福利。",
        "direction": "可做开放银行政策、平台数据垄断、去中心化交易流动性和金融科技采用的外部性。",
    },
    {
        "theme": "员工心理健康、倦怠与组织福祉",
        "signals": ["mental health", "employee wellbeing", "employee well-being", "burnout", "emotional exhaustion", "workplace stress"],
        "question": "心理健康和工作压力如何影响生产率、劳动供给、组织行为与家庭决策。",
        "direction": "可做心理健康冲击、员工帮助计划、远程工作压力、组织文化与员工流失。",
    },
]


DIRECT_CONCEPTS = [
    "AI washing",
    "AI-washing",
    "greenwashing",
    "greenhushing",
    "patient capital",
    "long-termism",
    "short-termism",
    "managerial myopia",
    "corporate myopia",
    "generative AI",
    "artificial intelligence",
    "machine learning",
    "ESG",
    "climate disclosure",
    "sustainability disclosure",
    "climate risk",
    "transition risk",
    "carbon premium",
    "carbon returns",
    "green innovation",
    "green finance",
    "trade war",
    "geopolitical risk",
    "supply chain resilience",
    "open banking",
    "fintech",
    "decentralized exchange",
    "mental health",
    "burnout",
]


NON_RESEARCH = re.compile(
    r"^editorial board$|^frontmatter|^backmatter|^contents$|^masthead$|^erratum|^corrigendum|^correction to:|annual report|call for papers|reviewers|referees",
    re.I,
)


STOP = set(ENGLISH_STOP_WORDS).union(
    {
        "paper",
        "study",
        "evidence",
        "using",
        "effect",
        "effects",
        "model",
        "models",
        "analysis",
        "approach",
        "impact",
        "impacts",
        "role",
        "case",
        "new",
        "based",
        "perspective",
        "research",
        "review",
        "examining",
        "exploring",
        "understanding",
        "does",
        "using",
        "evidence",
    }
)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def contains(text, signal):
    return re.search(re.escape(signal), text, flags=re.I) is not None


def hit_theme(text, signals):
    return [s for s in signals if contains(text, s)]


def clean_phrase(phrase):
    phrase = phrase.lower().strip()
    if len(phrase) < 5:
        return None
    words = phrase.split()
    if any(w in STOP for w in (words[0], words[-1])):
        return None
    if re.search(r"\d", phrase):
        return None
    return phrase


def main():
    parser = argparse.ArgumentParser(description="Analyze concrete research frontiers from fetched metadata.")
    parser.add_argument("--all", dest="all_path", default=None, help="All-record CSV from fetch_expanded_frontier_pool.py")
    parser.add_argument("--hits", dest="hits_path", default=None, help="Frontier-hit CSV from fetch_expanded_frontier_pool.py")
    parser.add_argument("--date-range", default=None, help="Human-readable date range for output metadata.")
    args = parser.parse_args()
    all_path = Path(args.all_path) if args.all_path else latest_file("expanded_core_frontier_pool_*.csv")
    hits_path = Path(args.hits_path) if args.hits_path else latest_file("expanded_core_frontier_hits_*.csv")

    all_df = pd.read_csv(all_path)
    df = pd.read_csv(hits_path)
    all_df = all_df[~all_df["title"].fillna("").map(lambda v: bool(NON_RESEARCH.search(str(v).strip())))]
    df = df[~df["title"].fillna("").map(lambda v: bool(NON_RESEARCH.search(str(v).strip())))]
    for frame in (all_df, df):
        frame["publication_date"] = pd.to_datetime(frame["publication_date"], errors="coerce")
        frame["year"] = frame["publication_date"].dt.year
        frame["cited_by_count"] = pd.to_numeric(frame["cited_by_count"], errors="coerce").fillna(0).astype(int)
        frame["text"] = frame["title"].fillna("").map(norm) + ". " + frame["abstract"].fillna("").map(norm)

    theme_rows = []
    rep_rows = []
    for theme in THEMES:
        mask = all_df["text"].map(lambda t, sigs=theme["signals"]: bool(hit_theme(t, sigs)))
        sub = all_df[mask].copy()
        sub["matched_signals"] = sub["text"].map(lambda t, sigs=theme["signals"]: "; ".join(hit_theme(t, sigs)))
        signal_counts = Counter()
        for signals in sub["matched_signals"]:
            for s in str(signals).split("; "):
                if s:
                    signal_counts[s] += 1
        journals = sub["journal"].value_counts().head(6).to_dict() if not sub.empty else {}
        theme_rows.append(
            {
                "theme": theme["theme"],
                "count": int(len(sub)),
                "share_of_expanded_pool": round(float(len(sub) / len(all_df)), 4) if len(all_df) else 0,
                "recent_2025_2026_share": round(float((sub["year"] >= 2025).mean()), 3) if not sub.empty else 0,
                "top_signals": "; ".join(f"{k} ({v})" for k, v in signal_counts.most_common(10)),
                "top_journals": json.dumps(journals, ensure_ascii=False),
                "core_question": theme["question"],
                "research_direction": theme["direction"],
            }
        )
        if not sub.empty:
            sub["title_direct_hit"] = sub["title"].map(lambda t, sigs=theme["signals"]: bool(hit_theme(str(t), sigs)))
            reps = sub.sort_values(["title_direct_hit", "cited_by_count", "publication_date"], ascending=[False, False, False]).head(12)
            for _, row in reps.iterrows():
                rep_rows.append(
                    {
                        "theme": theme["theme"],
                        "title": row["title"],
                        "authors": row["authors"],
                        "journal": row["journal"],
                        "publication_date": row["publication_date"].date().isoformat() if not pd.isna(row["publication_date"]) else "",
                        "doi": row["doi"],
                        "cited_by_count": int(row["cited_by_count"]),
                        "matched_signals": row["matched_signals"],
                        "abstract": row["abstract"],
                    }
                )

    direct_rows = []
    for concept in DIRECT_CONCEPTS:
        mask = all_df["text"].map(lambda t, c=concept: contains(t, c))
        sub = all_df[mask]
        direct_rows.append(
            {
                "concept": concept,
                "count": int(len(sub)),
                "recent_2025_2026_share": round(float((sub["year"] >= 2025).mean()), 3) if len(sub) else 0,
                "top_titles": " | ".join(sub.sort_values("cited_by_count", ascending=False)["title"].head(5)),
            }
        )

    title_vectorizer = CountVectorizer(
        stop_words=sorted(STOP),
        ngram_range=(2, 4),
        min_df=3,
        max_df=0.3,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z-]+\b",
    )
    X = title_vectorizer.fit_transform(df["title"].fillna(""))
    terms = title_vectorizer.get_feature_names_out()
    counts = X.sum(axis=0).A1
    phrase_rows = []
    for term, count in zip(terms, counts):
        phrase = clean_phrase(term)
        if not phrase:
            continue
        idx = X[:, title_vectorizer.vocabulary_[term]].nonzero()[0]
        sub = df.iloc[idx]
        phrase_rows.append(
            {
                "phrase": phrase,
                "count": int(count),
                "recent_2025_2026_share": round(float((sub["year"] >= 2025).mean()), 3),
                "example_titles": " | ".join(sub.sort_values("cited_by_count", ascending=False)["title"].head(3)),
            }
        )
    phrase_df = pd.DataFrame(phrase_rows).sort_values(["count", "recent_2025_2026_share"], ascending=False).head(250)

    theme_df = pd.DataFrame(theme_rows).sort_values(["count", "recent_2025_2026_share"], ascending=False)
    rep_df = pd.DataFrame(rep_rows)
    direct_df = pd.DataFrame(direct_rows).sort_values(["count", "recent_2025_2026_share"], ascending=False)
    phrase_df = phrase_df.fillna("")
    theme_df = theme_df.fillna("")
    rep_df = rep_df.fillna("")
    direct_df = direct_df.fillna("")

    outputs = {
        "theme_summary_csv": OUT / "expanded_concrete_frontier_theme_summary.csv",
        "representatives_csv": OUT / "expanded_concrete_frontier_representatives.csv",
        "direct_concepts_csv": OUT / "expanded_concrete_frontier_direct_concepts.csv",
        "phrases_csv": OUT / "expanded_concrete_frontier_emerging_phrases.csv",
        "report_md": OUT / "expanded_concrete_frontier_report.md",
        "workbook_json": WORK / "expanded_concrete_frontier_workbook_data.json",
    }
    theme_df.to_csv(outputs["theme_summary_csv"], index=False)
    rep_df.to_csv(outputs["representatives_csv"], index=False)
    direct_df.to_csv(outputs["direct_concepts_csv"], index=False)
    phrase_df.to_csv(outputs["phrases_csv"], index=False)

    workbook_data = {
        "summary": theme_df.to_dict(orient="records"),
        "representatives": rep_df.to_dict(orient="records"),
        "direct_concepts": direct_df.to_dict(orient="records"),
        "phrases": phrase_df.to_dict(orient="records"),
        "metadata": {
            "expanded_pool_records": int(len(all_df)),
            "frontier_hit_records": int(len(df)),
            "date_range": args.date_range or all_path.stem.replace("expanded_core_frontier_pool_", "").replace("_to_", " to "),
        },
    }
    outputs["workbook_json"].write_text(json.dumps(workbook_data, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 扩展期刊池：具体新兴研究前沿\n\n"]
    lines.append(f"- 扩展期刊池净记录：{len(all_df)} 条\n")
    lines.append(f"- 定向前沿命中记录：{len(df)} 条\n")
    lines.append("- 说明：这版专门捕捉具体概念和研究对象，而不是按学科大类分类。\n\n")
    lines.append("## 具体前沿\n")
    for _, row in theme_df.iterrows():
        lines.append(f"\n### {row['theme']}\n")
        lines.append(f"- 命中论文：{int(row['count'])} 篇，占扩展池 {row['share_of_expanded_pool']:.1%}\n")
        lines.append(f"- 2025-2026 占比：{row['recent_2025_2026_share']:.1%}\n")
        lines.append(f"- 直接信号：{row['top_signals']}\n")
        lines.append(f"- 核心问题：{row['core_question']}\n")
        lines.append(f"- 可推进方向：{row['research_direction']}\n")
        reps = rep_df[rep_df["theme"] == row["theme"]].head(5)
        if not reps.empty:
            lines.append("- 代表论文：\n")
            for _, paper in reps.iterrows():
                lines.append(f"  - {paper['title']} ({paper['journal']}, {paper['publication_date']}), DOI: {paper['doi']}\n")
    lines.append("\n## 直接概念热度\n")
    for _, row in direct_df.iterrows():
        if int(row["count"]) > 0:
            lines.append(f"- {row['concept']}: {int(row['count'])} 篇，2025-2026 占比 {row['recent_2025_2026_share']:.1%}\n")
    lines.append("\n## 方法提醒\n")
    lines.append("- “AI washing”和“patient capital”在题名/摘要中直接出现仍少，说明它们更像正在进入研究议程的概念，需要结合邻近词构造研究对象。\n")
    lines.append("- “greenwashing/ESG/climate disclosure/sustainable finance”已经有较强文献基础，适合更快落地成综述或实证选题。\n")
    outputs["report_md"].write_text("".join(lines), encoding="utf-8")

    print(json.dumps({k: str(v) for k, v in outputs.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
