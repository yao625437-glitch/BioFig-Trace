# Tables and specialized figures

Apply these rules to baseline/regression/subgroup tables, drug sensitivity, immune/TMB/MSI summaries, model explanation/training/confusion matrices, dose-response fits, physiological signals, and tracking plots.

## Tables

- Preserve headers, units, group definitions, footnotes, missingness, denominators, summary statistic type, reference categories, and adjustment sets.
- Baseline table: distinguish mean ± SD, median [IQR], n (%), missing values, SMD, and P value. Do not treat SMD as a P value.
- Regression/subgroup table: preserve coefficient/effect type, estimate, 95% CI, P value, reference group, adjustment model, and interaction P where applicable.
- Use `reporting_scope` if only requested variables or key rows are extracted; state the selection rule.

## Drug sensitivity and dose-response

- Distinguish a group-comparison IC50 plot (`drug_sensitivity_ic50`) from an individual fitted response curve (`dose_response`).
- Record drug/stimulus, system, exposure time, dose unit/range, response endpoint/normalization, vehicle/control, fit model, Top/Bottom, Hill slope, IC50/EC50, 95% CI, replicate information, and fit quality when reported.
- Never derive exact IC50/EC50 or Hill slope by eye. Graph estimates require tolerance; a fitted parameter should be author-reported or recomputed from sufficient numeric evidence.
- Use `MISSING_FIT_INFORMATION` when model, interval, or fit context is needed but absent.

## Immune infiltration, TMB, and MSI

Record algorithm/version, input data, cell-type definitions, normalization/denominator, score unit, cohort/group, statistical comparison, and multiple-testing correction. A deconvolution fraction is a model estimate, not a direct cell count.

## Model evaluation and explanation

- SHAP: record model, cohort/split, feature, SHAP definition/scale, direction, aggregation, and ranking. SHAP attribution is not causal.
- Learning curve: record training/validation metric, x-axis definition, split/cross-validation, smoothing, and overfitting interpretation.
- Confusion matrix: record true/predicted class, count or normalized proportion, positive class, threshold, and derived sensitivity/specificity/precision only when denominators are clear.
- Separate development, internal validation, and external validation performance.

## Physiological signals and tracking

Record subject/sample, channel, sampling rate, filter/baseline/preprocessing, time/event alignment, amplitude/unit, detected feature, aggregation, and repeat structure.

- A single calcium/electrophysiology/trajectory trace has no inherent variance. Show uncertainty only for supported repeated/aggregated data.
- Do not infer an event or movement state from a trace without an annotation rule or source statement.
- For tracking, preserve coordinate system, frame rate, arena scale, missing frames, smoothing, and derived speed/distance method.
