#!/usr/bin/env python3
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHUNK_DIR = ROOT / "work" / "missing_ris_chunks"
REPORT = ROOT / "outputs" / "zotero_selected_collection_chunk_import_report.json"
BASE = "http://127.0.0.1:23119"
EXPECTED_COLLECTION = "English Econ Core 2024-2026"


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post_connector(path, payload, content_type="application/json", timeout=180):
    data = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method="POST",
        headers={"Content-Type": content_type},
    )
    with opener().open(req, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return response.status, parsed


def get_api(path, timeout=60):
    req = urllib.request.Request(BASE + path, headers={"Zotero-API-Version": "3"})
    with opener().open(req, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, json.loads(body) if body else {}, response.headers


def selected_collection_name():
    status, payload = post_connector("/connector/getSelectedCollection", "{}", timeout=60)
    if status != 200:
        raise RuntimeError(f"Could not read selected collection: {status} {payload}")
    return payload.get("name"), payload


def collection_key_by_name(name):
    start = 0
    while True:
        status, payload, _headers = get_api(f"/api/users/0/collections?limit=100&start={start}")
        if status != 200:
            raise RuntimeError(f"Could not read collections: {status} {payload}")
        for collection in payload:
            data = collection.get("data", {})
            if data.get("name") == name:
                return collection.get("key")
        if len(payload) < 100:
            return None
        start += len(payload)


def collection_count(collection_key):
    status, _payload, headers = get_api(f"/api/users/0/collections/{collection_key}/items?limit=1")
    if status != 200:
        return None
    return int(headers.get("Total-Results", "0"))


def dois_from_ris(text):
    return [match.group(1).strip().lower() for match in re.finditer(r"^DO  - (.+)$", text, re.M)]


def main():
    selected_name, selected_payload = selected_collection_name()
    if selected_name != EXPECTED_COLLECTION:
        raise SystemExit(
            json.dumps(
                {
                    "error": "wrong_selected_collection",
                    "expected": EXPECTED_COLLECTION,
                    "actual": selected_name,
                    "selected": selected_payload,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    collection_key = collection_key_by_name(EXPECTED_COLLECTION)
    before_count = collection_count(collection_key) if collection_key else None
    chunks = sorted(CHUNK_DIR.glob("*.ris"))
    results = []

    for index, path in enumerate(chunks, start=1):
        text = path.read_text(encoding="utf-8")
        dois = dois_from_ris(text)
        session = f"codex-econ-core-selected-{index:03d}"
        started = time.time()
        try:
            status, payload = post_connector(
                f"/connector/import?{urllib.parse.urlencode({'session': session})}",
                text,
                content_type="text/plain",
                timeout=180,
            )
            ok = 200 <= status < 300
            error = None
        except Exception as exc:
            status = None
            payload = {}
            ok = False
            error = repr(exc)
        elapsed = round(time.time() - started, 2)
        row = {
            "chunk": path.name,
            "index": index,
            "records": len(dois),
            "status": status,
            "ok": ok,
            "elapsed_seconds": elapsed,
            "error": error,
        }
        results.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        time.sleep(1.0)

    after_count = collection_count(collection_key) if collection_key else None
    report = {
        "selected_collection": selected_name,
        "collection_key": collection_key,
        "before_count": before_count,
        "after_count": after_count,
        "chunks": len(chunks),
        "records_attempted": sum(row["records"] for row in results),
        "ok_chunks": sum(1 for row in results if row["ok"]),
        "timeout_or_error_chunks": [row for row in results if not row["ok"]],
        "results": results,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
