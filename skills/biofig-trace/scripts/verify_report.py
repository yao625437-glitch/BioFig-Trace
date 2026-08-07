"""Verify public-report completeness, profile tables, scope disclosure and leakage."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from common import SCHEMA_ROOT, load_json
from render_report import (
    HASH_RE,
    INTERNAL_ID_RE,
    JSON_POINTER_RE,
    POSIX_PRIVATE_PATH_RE,
    URI_RE,
    WINDOWS_PATH_RE,
    _md,
    markdown_table,
    public_projection,
    report_language,
    render,
)


REPORT_PROFILE_PATH = SCHEMA_ROOT / "report_profile_v3.json"
RAW_ENUM_RE = re.compile(
    r"\b(?:consumed|partially_consumed|not_consumed|unavailable|not_recoverable|not_applicable|"
    r"observed|reported|depicted|inferred|summary_only|single_source|minor_conflict|major_conflict)\b",
    re.I,
)
RAW_ENUM_RE_EN = re.compile(
    r"\b(?:consumed|partially_consumed|not_consumed|not_recoverable|not_applicable|not_performed|"
    r"not_possible|summary_only|single_source|minor_conflict|major_conflict)\b",
    re.I,
)
DANGEROUS_QUERY_RE = re.compile(r"[?&](?:token|api[_-]?key|key|secret|signature|sig|auth|password)=", re.I)


def _issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _section(report: str, heading: str, next_heading: str | None) -> str:
    marker = f"## {heading}\n"
    start = report.find(marker)
    if start < 0:
        return ""
    end = report.find(f"## {next_heading}\n", start + len(marker)) if next_heading else len(report)
    return report[start:end if end >= 0 else len(report)]


def _dangerous_uri_issues(report: str) -> list[str]:
    issues: list[str] = []
    for match in URI_RE.finditer(report):
        token = match.group(0).rstrip(".,;，；。)]}")
        try:
            parsed = urlsplit(token)
        except ValueError:
            issues.append(token)
            continue
        if parsed.scheme.casefold() == "file" or parsed.query or parsed.fragment or parsed.username or parsed.password:
            issues.append(token)
    return issues


def verify(data: dict[str, Any], report: str, *, require_exact_render: bool = True) -> list[dict[str, str]]:
    profile = load_json(REPORT_PROFILE_PATH)
    language = report_language(data)
    language_profile = profile["languages"][language]
    sections = list(language_profile["required_sections"])
    structured_section, interpretation_section, location_section, coverage_section, uncertainty_section, review_section = sections
    issues: list[dict[str, str]] = []

    headings = re.findall(r"^## ([^\r\n]+)$", report, flags=re.M)
    if headings != sections:
        issues.append(_issue("SECTION_ORDER", f"二级标题必须恰好按顺序出现一次: {sections}"))

    projection = public_projection(data)
    blocks = {
        section: _section(report, section, sections[index + 1] if index + 1 < len(sections) else None)
        for index, section in enumerate(sections)
    }
    for panel in projection["panels"]:
        heading = f"### {panel['title']}"
        for section in (structured_section, interpretation_section, uncertainty_section, review_section):
            if heading not in blocks.get(section, ""):
                issues.append(_issue("PANEL_COVERAGE", f"{panel['short_name']} 未出现在“{section}”中"))
        location_prefix = f"| {panel['short_name']} |"
        if location_prefix not in blocks.get(location_section, ""):
            issues.append(_issue("PANEL_LOCATION", f"{panel['short_name']} 缺少公开定位行"))
        expected_header = markdown_table(panel["headers"], [], language)[0]
        if expected_header not in blocks.get(structured_section, ""):
            issues.append(_issue("TEMPLATE_HEADER", f"{panel['short_name']} 未使用 {panel['template']} 专用表头"))
        confidence_text = (
            f"Panel confidence: {_md(panel['confidence'], language)}"
            if language == "en"
            else f"面板置信度：{_md(panel['confidence'], language)}"
        )
        if confidence_text not in blocks.get(interpretation_section, "") or confidence_text not in blocks.get(uncertainty_section, ""):
            issues.append(_issue("PANEL_CONFIDENCE", f"{panel['short_name']} 缺少置信度及理由"))
        classification_text = (
            f"Figure classification: {_md(panel['classification'], language)}"
            if language == "en"
            else f"图型分类：{_md(panel['classification'], language)}"
        )
        if classification_text not in blocks.get(interpretation_section, ""):
            issues.append(_issue("PANEL_CLASSIFICATION", f"{panel['short_name']} 缺少分类状态和依据"))
        if panel["classification_provisional"] and _md(panel["classification"], language) not in blocks.get(uncertainty_section, ""):
            issues.append(_issue("PANEL_CLASSIFICATION", f"{panel['short_name']} 未披露暂定分类的不确定性"))
        if panel["scope_mode"] in {"selected", "summary_only"}:
            public_scope = _md(panel["scope"], language)
            if public_scope not in blocks.get(structured_section, "") or public_scope not in blocks.get(interpretation_section, ""):
                issues.append(_issue("HIGH_DIMENSION_SCOPE", f"{panel['short_name']} 未完整披露展示数、总数和选择规则"))

    location_header = markdown_table(language_profile["location_table"]["columns"], [], language)[0]
    if location_header not in blocks.get(location_section, ""):
        issues.append(_issue("LOCATION_COLUMNS", "原图定位表未使用当前报告语言的公开列"))
    source_header = markdown_table(language_profile["source_table"]["columns"], [], language)[0]
    if source_header not in blocks.get(coverage_section, ""):
        issues.append(_issue("SOURCE_COLUMNS", "来源表必须且只能使用五个公开列"))
    for row in projection["coverage"]:
        expected_row = markdown_table(language_profile["source_table"]["columns"], [row], language)[2]
        if expected_row not in blocks.get(coverage_section, ""):
            issues.append(_issue("SOURCE_ROW", f"来源消费行缺失或未按报告语言呈现: {row[0]}"))
    if any(panel["review_required"] for panel in projection["panels"]) or projection["global_review_required"]:
        review_header = markdown_table(language_profile["review_table"]["columns"], [], language)[0]
        if review_header not in blocks.get(review_section, ""):
            issues.append(_issue("REVIEW_COLUMNS", "人工复核表未使用当前报告语言的公开列"))

    lower_report = report.casefold()
    for token in profile.get("forbidden_machine_tokens", []):
        if str(token).casefold() in lower_report:
            issues.append(_issue("MACHINE_TOKEN", f"报告泄露机器字段标记: {token}"))
    if INTERNAL_ID_RE.search(report):
        issues.append(_issue("INTERNAL_ID", "报告泄露内部 ID"))
    if JSON_POINTER_RE.search(report) or re.search(r"\$\.[A-Za-z_]", report):
        issues.append(_issue("JSON_POINTER", "报告泄露 JSON Pointer 或内部字段路径"))
    if HASH_RE.search(report):
        issues.append(_issue("HASH_LEAK", "报告泄露 64 位摘要"))
    if WINDOWS_PATH_RE.search(report) or POSIX_PRIVATE_PATH_RE.search(report):
        issues.append(_issue("ABSOLUTE_PATH", "报告泄露本地绝对路径"))
    dangerous_uris = _dangerous_uri_issues(report)
    if dangerous_uris or DANGEROUS_QUERY_RE.search(report):
        issues.append(_issue("DANGEROUS_URI", "报告泄露 URI 凭据、query、fragment 或 file URI"))
    raw_enum_pattern = RAW_ENUM_RE_EN if language == "en" else RAW_ENUM_RE
    if raw_enum_pattern.search(report):
        issues.append(_issue("RAW_ENUM", "报告泄露未翻译的机器枚举"))

    if require_exact_render:
        expected = render(data)
        if report != expected:
            issues.append(_issue("NON_DETERMINISTIC_REPORT", "报告不是当前 evidence 的确定性允许字段投影"))

    validation = data.get("validation", {})
    if validation.get("state") == "validated":
        actual_hash = hashlib.sha256(report.encode("utf-8")).hexdigest()
        if validation.get("report_sha256") != actual_hash:
            issues.append(_issue("REPORT_DIGEST", "报告摘要与验证戳不一致"))
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in issues:
        key = (item["code"], item["message"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        data = load_json(args.evidence)
        report = args.report.read_text(encoding="utf-8")
        issues = verify(data, report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        issues = [_issue("INPUT", str(exc))]
    if args.as_json:
        print(json.dumps({"passed": not issues, "errors": issues}, ensure_ascii=False, indent=2))
    elif issues:
        for item in issues:
            print(f"[{item['code']}] {item['message']}")
    else:
        print("BioFig Trace public report verification passed.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
