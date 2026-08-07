# Review and failure policy

Fail visibly and locally. Every review reason must identify the affected machine field, explain the scientific consequence in report-facing language, cite evidence when available, and request the smallest decisive action.

## Review codes

- `MISSING_CAPTION`: caption unavailable or incomplete.
- `UNREADABLE_AXIS`: label, ticks, scale, or unit cannot be read reliably.
- `UNREADABLE_LEGEND`: group-to-mark mapping cannot be resolved.
- `LOW_IMAGE_QUALITY`: crop, resolution, saturation, focus, or compression blocks recovery.
- `VALUE_NOT_RECOVERABLE`: a requested or scientifically necessary value cannot be recovered without guessing.
- `MISSING_STATISTICS`: an inferential/significance claim lacks statistics needed to support it.
- `UNMAPPED_SIGNIFICANCE`: statistical symbols lack a readable threshold mapping.
- `AMBIGUOUS_COMPARISON`: a test/result cannot be linked to a specific comparison.
- `SOURCE_CONFLICT`: image, caption, Results, Methods, supplement, or recomputation disagree beyond tolerance.
- `UNSUPPORTED_FIGURE`: reliable interpretation requires a method outside the supported workflow.
- `AMBIGUOUS_CONDITION`: a factor, level, control, or fixed condition cannot be assigned securely.
- `AMBIGUOUS_SERIES_MAPPING`: series-to-mark or series-to-axis mapping is insecure.
- `MISSING_DENOMINATOR`: a percentage, fraction, or conditional probability lacks its denominator/population scope.
- `UNSPECIFIED_ERROR_PROPAGATION`: a derived endpoint has uncertainty but the propagation method is not reported.
- `MISSING_SCALE_BAR`: a spatial image requires scale but no reliable scale bar is available.
- `MISSING_NORMALIZATION`: normalization/transformation required for interpretation is missing.
- `MISSING_MULTIPLE_TESTING`: multiple-testing correction or adjusted-P definition is missing.
- `MISSING_RISK_TABLE`: survival interpretation requires a missing risk table.
- `MISSING_MODEL_SPECIFICATION`: statistical/prediction model, adjustment, horizon, or validation setting is incomplete.
- `MISSING_CONTROL`: a key negative, positive, loading, vehicle, IgG, or other control is absent or ambiguous.
- `MISSING_CHANNEL_MAPPING`: imaging channel, stain, marker, or color mapping is missing.
- `MISSING_GATE_OR_DENOMINATOR`: a flow gate, parent population, or percentage denominator is missing.
- `MISSING_LANE_METADATA`: lane, target, molecular size, IP/IB, or loading-control mapping is missing.
- `MISSING_FIT_INFORMATION`: dose-response or other fitted result lacks required model/interval/fit context.
- `MIXED_PANEL_NOT_SEGMENTED`: heterogeneous components remain merged and may hide type-specific evidence.
- `OTHER`: material issue not covered above.

## Severity and flags

- `critical`: likely changes an axis, group, unit, direction, effect-measure type, or headline conclusion.
- `major`: affects a key value, uncertainty, derivation, model interpretation, or reproducibility.
- `minor`: localized metadata or presentation limitation that does not change the main conclusion.

Set panel/top-level `review_required=true` for critical or major reasons and unresolved/caveated conflicts. A minor reason may also justify review when the user requested that field; explain it explicitly. `extraction_status` describes completeness, whereas review flags describe unresolved risk.

For a source conflict, retain all reported values, show calculation/tolerance, use `reported_with_caveat` or `unresolved`, and request the smallest decisive check: raw data, vector graphic, uncropped image, supplement, model footnote, or author clarification.

## Source-consumption audit

For each selected Methods, Results, or supplement source, create one or more `source_coverage` facts. Use exactly four v2.2 statuses:

- `consumed`: the fact is represented at one or more valid `field_paths`.
- `partially_consumed`: only part of the fact is represented; list represented paths and explain the residual limitation.
- `not_consumed`: a relevant fact is intentionally excluded; use no paths and explain why.
- `unavailable`: a cited source/fact is unreadable or missing; use no paths and explain the access limitation.

Do not silently omit a relevant selected source. Every consumed/partially consumed path must resolve to an existing JSON value. Fixed conditions such as dose, duration, device dimensions, assay setup, model, or threshold must point to the corresponding field or carry an exclusion reason and review action.

Legacy v2.1 `not_applicable` records migrate to `not_consumed` with an explicit “not relevant to this extraction” reason.

## Human source summary

Keep coverage IDs, raw scopes/statuses, and all JSON paths in `evidence.json`. In `report.md`, show only:

| 来源 | 已使用信息 | 用途 | 状态 | 限制 |
|---|---|---|---|---|

Translate statuses as `已使用`, `部分使用`, `未使用`, and `不可用`. For consumed sources with no residual limitation, write `无`. Do not place machine audit language such as “represented at field path” in the limitation column.

## Local failure behavior

- Mark only the affected value/field not recoverable; retain all other evidence.
- Do not downgrade an entire multi-panel figure because one panel is unreadable.
- A missing exact digitization is not a failure unless exact recovery was requested or required for a claim.
- A descriptive panel without a P value is not automatically incomplete.
- A workflow/mechanism/image does not need variance merely because the universal JSON contains a statistics object.
