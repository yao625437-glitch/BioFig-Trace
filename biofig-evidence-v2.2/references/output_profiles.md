# Output profiles

Choose the canonical `panel_type`; obtain its required `result_profile` from `schemas/figure_registry.json`. The profile determines the public table. Keep non-applicable machine fields empty or explicitly not applicable, but do not show meaningless columns in `report.md`.

## Profile matrix

| Profile | Primary JSON blocks | Human table focus | Never force into the table |
|---|---|---|---|
| `group_comparison` | measurements, statistics | group/condition, endpoint, result, uncertainty, n/test | axes that add no interpretive value |
| `continuous_series` | axes, series, measurements | series, dose/time/x, endpoint, result, uncertainty | workflow fields |
| `association` | measurements, statistics | variables X/Y, group, r/model/P or agreement limits | causal wording |
| `distribution_composition` | measurements, conditions | category/group, distribution or fraction, denominator, statistics | error bars when none apply |
| `multivariate` | measurements, conditions | object, dimension, value/coordinate, comparison | one universal scalar summary |
| `feature_significance` | measurements, thresholds, statistics | feature, contrast, effect, direction, P/FDR, threshold | unadjusted P presented as FDR |
| `matrix_embedding` | axes, series, measurements, conditions | row/column or dimension, value/coordinate, cluster/group, transformation | thousands of rows without scope disclosure |
| `enrichment_set` | measurements, conditions, statistics | term/set, ratio or ES/NES, count, P/FDR, direction | enrichment without background or database context |
| `survival_outcome` | measurements, statistics | group, time, survival/event, CI, HR/SHR, risk counts, test | ordinary error-bar language for CI |
| `diagnostic_prediction` | measurements, statistics | model, AUC/metric, CI, threshold/time, validation cohort | accuracy without cohort/threshold context |
| `effect_estimate` | measurements, statistics | variable/comparison, HR/OR/RR/coefficient, 95% CI, P, adjustment | mixed effect-measure types in one value field |
| `dose_response` | axes, measurements, model conditions | drug/stimulus, system, dose range, response, IC50/EC50, CI, fit | exact fit parameters reconstructed from pixels |
| `image_observation` | qualitative observations, optional measurements | sample/group, modality/feature, direct observation, comparison, scale limitation | x/y/error columns for qualitative evidence |
| `band_lane` | observations, optional measurements | lane/group, target, treatment/control, band, normalization/quantitation | conclusions without lane/target/control mapping |
| `cytometry_gate` | observations, measurements, conditions | population/gate, markers, parent gate/denominator, count/percentage | percentages without a parent population |
| `spectrum_trace` | axes, measurements, observations | peak/variant, position, intensity/result, identification | unlabelled peak identity guesses |
| `workflow_flow` | process steps | order, input, operation, parameters, output, predecessor/branch | variance, P value, x/y, or effect claims |
| `mechanism_relationship` | relationships | source entity, relation, target, direction/sign, evidence nature, weight | interpreting depicted arrows as experimental proof |
| `structured_table` | measurements, statistics | variable, group/model, value, interval/dispersion, missingness/statistic | reproducing decorative cells |
| `model_explanation` | measurements, conditions | feature/model, attribution or importance, rank, cohort/model context | causal interpretation of SHAP attribution |
| `signal_trajectory` | axes, measurements, conditions | signal/subject, time/event, response, preprocessing, uncertainty | variance for a single trace unless repeated data support it |
| `mixed` | two or more applicable blocks | one subtable per block | a single universal table |

## Shared quantitative representation

- Create one measurement per endpoint.
- Use `point.x` for the independent coordinate or category and `point.y` for the endpoint value.
- For a categorical coordinate, set `value.category` and leave `numeric` null.
- Put CI/SD/SEM/range only in `point.error` when the source defines it.
- Put additional dose, time, model, threshold, channel, cohort, or assay settings in `at_conditions` or `experiment`.
- Keep `measurement.origin` separate from `extraction_method`.

## Workflow and clinical flow

- Put every visible node in `process_steps`.
- Populate `input`, `label` as the operation, `parameters`, `output`, and `predecessor_ids`.
- Record participant/document counts as parameters or quantitative records tied to the exact step; do not call them sample-size statistics for the diagram.
- Use readable predecessor labels in the report, never internal step IDs.
- Set the error-bar kind to `none`; the public table must contain no variance or P-value column.

## Mechanism and network relations

- Create one `relationship` per explicit edge.
- Record source entity, relation text, target entity, direction, sign, optional magnitude, epistemic status, evidence, and confidence.
- Use `depicted` for a drawn arrow, `reported` for an author statement, `observed` only for direct visual experimental evidence, and `inferred` for bounded synthesis.
- An omics network may contain weights or statistics; a conceptual mechanism diagram normally does not.

## Images, lanes, and gates

- Store visible morphology/localization/bands/gates in `qualitative_observations`.
- Add measurements only for values genuinely reported or calibrated; a pixel estimate must be approximate with tolerance.
- For a blot or gel, identify lane/group, target, expected molecular size, input/IP/IB/control, and normalization when available.
- For flow cytometry, identify axes/markers, gate hierarchy, parent denominator, count/percentage, and control.
- For spatial images, record modality, stain/channel/marker, scale bar, magnification when reported, and comparability limitations.

## High-dimensional output scope

Use `reporting_scope` for volcano plots, heatmaps, embeddings, networks, tables, and other large outputs:

- `full`: all recovered structured records are shown; counts must match.
- `selected`: show a reproducible subset and state the selection rule and total count when known.
- `summary_only`: show an aggregate or key finding and state how it was summarized.

Never use a hard-coded top-N without recording the scientific selection rule, such as author-labelled features, prespecified pathways, FDR threshold, largest absolute effect under a declared cutoff, or user-requested targets.
