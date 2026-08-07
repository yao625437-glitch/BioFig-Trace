"""Inventory public or explicitly provided sources and assign stable source IDs."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from common import atomic_write_json


KIND_BY_SUFFIX = {
    ".pdf": "paper_pdf",
    ".png": "figure_image",
    ".jpg": "figure_image",
    ".jpeg": "figure_image",
    ".tif": "figure_image",
    ".tiff": "figure_image",
    ".svg": "figure_image",
    ".txt": "text_excerpt",
    ".md": "text_excerpt",
    ".json": "supplement",
    ".csv": "supplement",
    ".tsv": "supplement",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(seed: str) -> str:
    return "src-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def ingest_one(value: str) -> dict[str, Any]:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return {
            "source_id": stable_id(value),
            "kind": "metadata_or_web",
            "access_basis": "public",
            "availability": "not_retrieved",
            "locator": {"uri": value, "path": None, "citation": value, "detail": None},
            "sha256": None,
            "media_type": None,
            "size_bytes": None,
            "visual_inspection": {"status": "not_performed", "page_or_region": None, "dpi": None, "limitations": "此脚本不执行网络下载。"},
        }
    path = Path(value).expanduser()
    resolved = path.resolve(strict=False)
    available = resolved.is_file()
    digest = sha256_file(resolved) if available else None
    suffix = resolved.suffix.lower()
    seed = digest or str(resolved)
    return {
        "source_id": stable_id(seed),
        "kind": KIND_BY_SUFFIX.get(suffix, "other"),
        "access_basis": "user_provided",
        "availability": "available" if available else "unavailable",
        "locator": {
            "uri": resolved.as_uri() if available else None,
            "path": str(resolved),
            "citation": resolved.name,
            "detail": None,
        },
        "sha256": digest,
        "media_type": mimetypes.guess_type(resolved.name)[0],
        "size_bytes": resolved.stat().st_size if available else None,
        "visual_inspection": {"status": "not_performed", "page_or_region": None, "dpi": None, "limitations": None if available else "文件路径不可读。"},
    }


def build_manifest(values: list[str]) -> dict[str, Any]:
    sources = [ingest_one(value) for value in values]
    ids = [source["source_id"] for source in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("重复来源产生相同 source_id；请去重后重试。")
    return {"manifest_version": "3.0.0", "sources": sources}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", help="本地文件路径或公开 http(s) URL")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = build_manifest(args.sources)
        atomic_write_json(args.output, manifest)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    unavailable = sum(source["availability"] != "available" for source in manifest["sources"])
    print(json.dumps({"output": str(args.output), "source_count": len(manifest["sources"]), "not_locally_available": unavailable}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
