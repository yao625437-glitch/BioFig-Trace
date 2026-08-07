---
name: biofig-evidence
description: Extract auditable experimental conditions, key values, relationships, and interpretations from public biomedical paper figures and tables, including statistical and dose-response plots, omics/bioinformatics graphics, clinical/epidemiological figures, microscopy/blot/flow images, workflows/mechanism schematics, and specialized tables or signals. Use when Codex must locate panels in a PDF/image, distinguish observed/reported/depicted/inferred evidence, recover values and uncertainty without guessing, classify figure type, generate type-specific structured result tables, explain figures under the Critical/Consistent/Concise/Clear/Complete (5C) rules, preserve machine-auditable source coverage, quantify confidence, and propose actionable human review.
---

# Biofig Evidence

Produce two synchronized deliverables:

1. `evidence.json`, conforming to `schemas/output_schema.json` (v2.2).
2. `report.md`, generated from that JSON as the concise, academic, human-readable layer.

Do not substitute prose for the JSON or return JSON without the report. When files cannot be written, present the same report sections followed by one complete JSON block.

## Load the minimum references

Always read:

- `references/reporting_5c.md` for scientific reasoning and report language;
- `references/output_profiles.md` for type-specific tables and field applicability;
- `references/review_policy.md` for failures, review severity, and source consumption.

Read `references/figure_taxonomy.md` when classification is unclear. Then read only the applicable functional reference for each panel:

- basic statistics: `references/quantitative_plots.md`;
- omics/bioinformatics: `references/omics_bioinformatics.md`;
- clinical/epidemiological: `references/clinical_epidemiology.md`;
- experimental raw images: `references/microscopy_images.md`;
- mechanism/workflow/schematic: `references/process_diagrams.md`;
- tables/specialized figures: `references/tables_specialized.md`.

## Evidence boundary

- Treat image, caption, Results, Methods, supplement, metadata, and user notes as distinct sources.
- Use `observed` only for directly visible evidence, `reported` only for an author statement, `depicted` for a drawn relation, and `inferred` only for a bounded interpretation.
- Preserve author-reported values when an audit finds a conflict. Add the conflict and review action; never silently correct the paper.
- Never invent unreadable axes, groups, units, values, errors, n, P values, thresholds, scale bars, channels, lanes, gates, controls, workflow transitions, or mechanism links.
- Let confidence measure recoverability and source agreement, not effect size, importance, or statistical significance.
- Keep sample size/replicate records separate from mathematical denominators and physical conditions.

## Workflow

1. **Inventory sources.** Identify document/DOI, figure, PDF and printed pages, caption, relevant Results/Methods/supplement passages, image resolution, and missing sources. Compute SHA-256 when the file is accessible. Create stable source IDs and exact locators.
2. **Inspect visually.** Render the complete relevant PDF page at 300 dpi or higher and inspect it. Do not use extracted text as a substitute for panel geometry. Record panel labels and bounding boxes when recoverable.
3. **Segment before classification.** Enumerate panels in reading order. Split different modalities, endpoints, axes, protocols, or labelled subpanels. Do not hide heterogeneous content inside `mixed`.
4. **Classify on three linked fields.** Search `schemas/figure_registry.json`; set its canonical `figure_category`, `panel_type`, and `result_profile` pair. Choose the scientific use, not merely the geometry: a survival line is `kaplan_meier`, an enrichment bar is `enrichment_bar`, and a fitted pharmacology curve is `dose_response`.
5. **Declare report scope.** Set `reporting_scope=full` when all recovered records are shown. For a reproducible subset or summary, use `selected`/`summary_only`, record displayed/total counts when known, and state the scientific selection rule. Never silently truncate high-dimensional results.
6. **Extract literals first.** Capture labels, axes/scales/units, series mappings, groups, conditions, values, uncertainty, annotations, thresholds, scale/channel/lane/gate metadata, process steps, and explicit relations before interpretation.
7. **Populate the applicable evidence blocks.** Use measurements for numeric/categorical results, qualitative observations for image evidence, process steps for ordered flows, and relationships for mechanism/network edges. Keep compatibility blocks present but empty/not applicable when irrelevant.
8. **Reconstruct conditions.** Use `system`, `factors`, `controls`, `fixed_conditions`, `protocol`, and `time`. Preserve population/cohort, assay, treatment, dose, duration, normalization, model, threshold, and reference group when applicable.
9. **Attach evidence.** Every value, condition, axis/series mapping, observation, step, relationship, claim, conflict, and review reason must cite resolvable sources.
10. **Audit source consumption.** For every selected Methods/Results/supplement fact, create `source_coverage` with one of `consumed`, `partially_consumed`, `not_consumed`, or `unavailable`. Consumed/partial records require real JSON paths; not-consumed/unavailable records require empty paths and a concise reason.
11. **Audit calculations and statistics.** Recompute author-derived values when formula and inputs are available; compare with an explicit tolerance and perform a rounding-interval audit for conflicts. Record n, unit of analysis, replicate type, uncertainty definition, tests/models, P values, multiple-testing method, and comparison only when supported.
12. **Quantify extraction uncertainty.** Mark values `exact`, `approximate`, `bounded`, `not_recoverable`, or `not_applicable`. Approximate numeric values require a positive tolerance and rationale. A categorical coordinate belongs in `value.category`.
13. **Write the 5C synthesis.** Populate `academic_summary` with objective, approach, key finding, critical appraisal, material limitations, and evidence. Keep the conclusion no stronger than the evidence and write report-facing fields in the user's requested language.
14. **Validate atomically.** Initialize validation booleans to false, run the finalizer, and fix all failures before delivery. Never hand-edit the generated report.

## Type applicability

- Quantitative plots: create one measurement per endpoint with separate x/category, y, unit, and error objects.
- Workflow/CONSORT/PRISMA: populate order, input, operation, parameters/counts, output, and predecessors. Use no error bars; the public table must not show variance, x/y, or P-value columns.
- Mechanism/network: create explicit relationships with source, relation, target, direction/sign, optional magnitude, evidence nature, and confidence. A depicted arrow is not experimental validation.
- Images: prefer direct qualitative observations; add calibrated/reported measurements only. Preserve scale/channel/stain, lane/target/control, gate/denominator, or peak/base metadata as applicable.
- Clinical figures: preserve endpoint, population, time horizon, effect-measure type, reference/null, CI, P value, adjustment model, and validation/risk counts.
- Omics/high-dimensional figures: preserve contrast, transformation/normalization, threshold, multiple-testing correction, background/database, cluster/embedding parameters, and explicit selection scope.
- Dose-response: preserve system, drug/stimulus, exposure, dose range/unit, response normalization, IC50/EC50 and CI, fit model/parameters, controls, and fit limitations.

## Machine/public separation

Keep `source_coverage.field_paths`, review/conflict paths and IDs, hashes, raw enums, validation internals, and full provenance in `evidence.json`.

In `report.md`, show the source audit only as:

| 来源 | 已使用信息 | 用途 | 状态 | 限制 |
|---|---|---|---|---|

Translate statuses as:

- `consumed` → `已使用`;
- `partially_consumed` → `部分使用`;
- `not_consumed` → `未使用`;
- `unavailable` → `不可用`.

Never display JSON paths in the report. Translate confidence, severity, evidence nature, error type, comparison status, source type, and figure labels into human terms.

## Required public sections

The generated report must contain these exact sections:

- `## 结构化结果表`
- `## 图表解释`
- `## 原图定位`
- `## 来源消费覆盖`
- `## 冲突与不确定性`
- `## 人工复核建议`

Render one profile-specific table per panel. Omit inapplicable columns instead of filling them with repeated “not applicable” values. Show report selection scope when the panel is selected/summary-only.

## Validation

Run from the skill directory:

```bash
# POSIX
python3 scripts/finalize_output.py evidence.json report.md

# Windows
python -X utf8 scripts/finalize_output.py evidence.json report.md
```

The finalizer performs version-aware schema validation, cross-field scientific/provenance checks, deterministic report generation, 5C/report-profile verification, validation stamping, revalidation, and atomic replacement. If a source prevents a fix, represent the limitation explicitly; never mark invalid output as validated.

## Failure behavior

Set only the affected field not recoverable/unknown and retain everything else. Follow `references/review_policy.md`. Keep panel and top-level review flags aligned with unresolved risk. A missing exact digitization is not a failure unless exact recovery was requested or required for a claim.

## Resources

- Current contract: `schemas/output_schema.json` (v2.2)
- Legacy contract: `schemas/output_schema_v2.1.json`
- Type/category/profile registry: `schemas/figure_registry.json`
- Representative synthetic examples: all JSON files in `examples/`
- Migrate v2.0 or v2.1: `scripts/migrate_to_v22.py`
- Unit helper: `scripts/normalize_units.py`
- Tests: POSIX `python3 -m unittest discover -s tests -v`; Windows `python -X utf8 -m unittest discover -s tests -v`
- Reproducible validation pins: `requirements.lock`; portable range: `requirements.txt`

Examples are synthetic contract demonstrations, not facts or hidden answers for any paper.
