# 5C scientific reporting

Apply this guide to every report-facing field and to the final `report.md`. Treat 5C as a scientific reasoning gate, not a grammar pass.

## Critical

- Separate what is visible (`observed`), what the authors state (`reported`), what the diagram merely depicts (`depicted`), and what is inferred (`inferred`).
- State the strongest conclusion supported by the cited evidence and state what the evidence does not establish.
- Do not convert association to causation, visual separation to significance, a schematic arrow to experimental support, or a model attribution to a biological mechanism.
- Keep contradictory values, missing controls, uncertain mappings, and failed audits visible. Never write around a conflict.
- In `academic_summary.critical_appraisal`, evaluate the evidential boundary; do not repeat `key_finding`.

Use these evidence-bound phrases when helpful:

- `图中可见……` for direct visual observations.
- `作者报告……` for statements or values transcribed from text.
- `基于现有证据可推断……` for bounded inference.
- `该图仅示意……，不能单独证明……` for mechanism or workflow graphics.

## Consistent

- Use one canonical `panel_type`, `figure_category`, and `result_profile` from `schemas/figure_registry.json`.
- Preserve the source's endpoint names, group labels, effect-measure types, units, and statistical definitions. Do not alternate between HR, OR, RR, risk, and odds.
- Use `95% CI`, `SD`, `SEM`, `FDR`, `log2FC`, `IC50`, and `EC50` consistently. Define a less common abbreviation at first use.
- Keep precision consistent with the source and extraction method. Do not add digits beyond the visible tick spacing or reported precision.
- Write report-facing summaries, rationales, coverage facts, limitations, and review actions in the user's requested report language. Preserve original wording only in `sources[].quote` or when a technical label must remain verbatim.

## Concise

- Keep `academic_summary.key_finding` to one or two evidence-bearing sentences.
- Keep `critical_appraisal` to one or two sentences focused on support, limitation, or alternative interpretation.
- Omit empty metadata and inapplicable columns from `report.md`; retain the corresponding audit fields in `evidence.json`.
- Do not display SHA hashes, internal IDs, raw enums, booleans, JSON paths, validation internals, or repeated source prose in the human report.
- Do not restate the same number in the table, explanation, uncertainty section, and review section unless each occurrence serves a distinct purpose.
- For high-dimensional results, never silently truncate. Set `reporting_scope.mode` to `selected` or `summary_only`, give `displayed_count`, `total_count` when known, and a reproducible `selection_rule`.

## Clear

- Lead with the scientific object and comparison, then the result, then the evidential boundary.
- Use profile-specific column names from `references/output_profiles.md`; never force a workflow, image, or mechanism into x/y/error columns.
- Give every value its unit and every interval its meaning. Distinguish a confidence interval, SD, SEM, range, interquartile range, and box-plot whisker.
- Use human locators such as `图注（第 4 页，面板 B）`; keep source IDs and bounding-box JSON in `evidence.json`.
- Write review actions as the smallest decisive check: obtain the vector figure, inspect the uncropped image, confirm the parent gate, retrieve the risk table, or compare against raw data.

## Complete

For each panel, ensure the human report exposes all scientifically material items that apply:

- research objective or figure purpose;
- comparison, population/system, treatment, dose/time, controls, and fixed conditions;
- endpoint, key values, uncertainty, sample size, and test/model when applicable;
- qualitative observation, scale/channel/lane/gate, workflow parameter, or mechanism relation when applicable;
- original location and consumed source summary;
- confidence, evidence boundary, unresolved conflict, limitation, and actionable review advice;
- explicit report selection scope for a subset or summary.

Completeness does not mean filling every universal field. Use a sparse, type-appropriate report and keep machine-only audit fields in the JSON.

## Required panel synthesis

Populate `academic_summary` before rendering:

- `objective`: the question or purpose, or `null` when genuinely unavailable.
- `approach`: the analysis, assay, model, or visual encoding needed to interpret the result, or `null` when unavailable.
- `key_finding`: the principal evidence-backed result or depicted sequence.
- `critical_appraisal`: what the evidence supports and does not support.
- `limitations`: only material limitations; avoid generic caveats.
- `evidence_ids`: sources supporting the synthesis.

Keep `chart_explanation` as a concise legacy-compatible panel summary. It must not introduce a claim absent from `academic_summary`, measurements, observations, relationships, steps, or claims.

## Public/machine boundary

Keep these in `evidence.json` and out of `report.md`:

- `field_paths`, `field_path`, source/coverage/conflict internal IDs;
- raw status and severity enums;
- validation flags, validator names, timestamps, and SHA-256 hashes;
- raw bounding-box objects;
- empty or `not_applicable` structures.

Translate these into human form in `report.md`:

- status, confidence, severity, error type, comparison status, and evidence nature;
- source locator, panel type, and functional category;
- conflict description, consequence, current disposition, and review action.

## Final 5C gate

Before finalization, ask:

1. Critical: Is each conclusion no stronger than its evidence?
2. Consistent: Do terms, units, precision, statuses, and effect measures agree throughout?
3. Concise: Can any sentence, column, or repeated detail be removed without losing meaning?
4. Clear: Can a domain reader understand the comparison, result, source, and limitation without reading JSON?
5. Complete: Are all applicable conditions, values, uncertainties, locations, conflicts, and review actions present?

If any answer is no, revise `evidence.json` and regenerate. Never hand-edit the report.
