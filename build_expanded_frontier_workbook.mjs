import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const scriptDir = path.dirname(new URL(import.meta.url).pathname);
const root = path.resolve(scriptDir, "..");
const inputPath = path.join(root, "work/expanded_concrete_frontier_workbook_data.json");
const outputPath = path.join(root, "outputs/expanded_concrete_frontier_workbook.xlsx");

const raw = JSON.parse(await fs.readFile(inputPath, "utf8"));

function valuesFromRows(rows, columns) {
  return [
    columns.map((c) => c.header),
    ...rows.map((row) => columns.map((c) => row[c.key] ?? "")),
  ];
}

function styleTable(sheet, rangeAddress, headerAddress) {
  sheet.showGridLines = false;
  const range = sheet.getRange(rangeAddress);
  range.format.font.name = "Arial";
  range.format.font.size = 10;
  range.format.wrapText = true;
  range.format.borders = { preset: "inside", style: "thin", color: "#E6EAF0" };
  const header = sheet.getRange(headerAddress);
  header.format.fill.color = "#1F4E78";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  header.format.horizontalAlignment = "center";
  header.format.verticalAlignment = "middle";
}

function writeSheet(workbook, name, rows, columns, widths = {}) {
  const sheet = workbook.worksheets.add(name);
  const matrix = valuesFromRows(rows, columns);
  const endCol = String.fromCharCode(64 + columns.length);
  const endRow = matrix.length;
  sheet.getRange(`A1:${endCol}${endRow}`).values = matrix;
  styleTable(sheet, `A1:${endCol}${endRow}`, `A1:${endCol}1`);
  sheet.freezePanes.freezeRows(1);
  columns.forEach((col, idx) => {
    const width = widths[col.key] ?? col.width ?? 18;
    sheet.getRangeByIndexes(0, idx, endRow, 1).format.columnWidth = width;
  });
  sheet.getRange(`A1:${endCol}1`).format.rowHeight = 28;
  return sheet;
}

const workbook = Workbook.create();

const summaryRows = [
  { metric: "扩展期刊池净记录", value: raw.metadata.expanded_pool_records, note: "24 本管理、会计、金融、商业伦理、可持续、能源/生态经济期刊" },
  { metric: "定向前沿命中记录", value: raw.metadata.frontier_hit_records, note: "题名或摘要命中具体前沿关键词" },
  { metric: "时间范围", value: raw.metadata.date_range, note: "按 publication_date 过滤" },
  { metric: "分析目标", value: "具体研究前沿", note: "不是按学科分类，而是按可发展为选题的研究对象/概念归纳" },
];

writeSheet(
  workbook,
  "Overview",
  summaryRows,
  [
    { key: "metric", header: "Metric", width: 24 },
    { key: "value", header: "Value", width: 22 },
    { key: "note", header: "Note", width: 80 },
  ],
);

writeSheet(
  workbook,
  "Frontier Summary",
  raw.summary,
  [
    { key: "theme", header: "具体前沿", width: 36 },
    { key: "count", header: "命中论文数", width: 12 },
    { key: "share_of_expanded_pool", header: "扩展池占比", width: 12 },
    { key: "recent_2025_2026_share", header: "2025-2026占比", width: 14 },
    { key: "top_signals", header: "直接信号", width: 52 },
    { key: "top_journals", header: "主要期刊", width: 44 },
    { key: "core_question", header: "核心问题", width: 62 },
    { key: "research_direction", header: "可推进方向", width: 70 },
  ],
  { count: 12, share_of_expanded_pool: 12, recent_2025_2026_share: 14 },
);

writeSheet(
  workbook,
  "Direct Concepts",
  raw.direct_concepts,
  [
    { key: "concept", header: "直接概念", width: 26 },
    { key: "count", header: "命中数", width: 10 },
    { key: "recent_2025_2026_share", header: "2025-2026占比", width: 14 },
    { key: "top_titles", header: "高引用/代表题名", width: 100 },
  ],
);

writeSheet(
  workbook,
  "Representative Papers",
  raw.representatives,
  [
    { key: "theme", header: "具体前沿", width: 34 },
    { key: "title", header: "题名", width: 68 },
    { key: "authors", header: "作者", width: 38 },
    { key: "journal", header: "期刊", width: 30 },
    { key: "publication_date", header: "发表日期", width: 13 },
    { key: "doi", header: "DOI", width: 30 },
    { key: "cited_by_count", header: "OpenAlex引用", width: 12 },
    { key: "matched_signals", header: "命中信号", width: 38 },
    { key: "abstract", header: "摘要", width: 100 },
  ],
);

writeSheet(
  workbook,
  "Emerging Phrases",
  raw.phrases,
  [
    { key: "phrase", header: "题名短语", width: 30 },
    { key: "count", header: "出现次数", width: 10 },
    { key: "recent_2025_2026_share", header: "2025-2026占比", width: 14 },
    { key: "example_titles", header: "示例题名", width: 110 },
  ],
);

for (const sheet of [
  "Frontier Summary",
  "Direct Concepts",
  "Representative Papers",
  "Emerging Phrases",
]) {
  const ws = workbook.worksheets.getItem(sheet);
  const used = ws.getUsedRange();
  used.format.verticalAlignment = "top";
}

const inspect = await workbook.inspect({
  kind: "sheet",
  include: "name",
  maxChars: 2000,
});
console.log(inspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 200 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath }));
