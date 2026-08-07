# Basic statistical plots

Apply these rules to the `basic_statistics` category and to shared quantitative components in other categories.

## Extraction order

1. Record each axis independently: role, literal label, unit, scale, readable range, and evidence.
2. Resolve each series from direct labels or legend marks. Use `ambiguous` rather than assigning a color or symbol by guesswork.
3. Create one measurement per endpoint and map it to one y/y2/color/size axis. A dual-axis panel normally has at least two measurements.
4. Create scalar points. Keep the independent coordinate/category in `x`, the endpoint in `y`, displayed uncertainty in `error`, and additional settings in `at_conditions`.
5. Separate printed values (`exact`) from graph estimates (`approximate`). Choose an estimate tolerance consistent with tick spacing and image quality.
6. Record sample size, unit of analysis, replicate type, error definition, test, comparison, and P value only when the source supports them.

## Type-specific checks

- **Bar/horizontal bar**: identify whether height encodes an absolute value, change, or floating interval. An absolute-magnitude bar should have a zero baseline; a non-zero baseline is not automatically wrong for a difference/floating bar but must be interpreted explicitly.
- **Line/time course/dual axis**: preserve time/dose order, missing time points, interpolation status, and series-to-axis mapping. A connecting line does not prove continuous measurement.
- **Scatter/bubble**: record both variables, group, regression/correlation method, r or coefficient, P value, and bubble-size/color meanings. Do not infer causality.
- **Box/violin/dot/beeswarm**: distinguish median, quartiles, whisker rule, density, and raw points. Never label IQR or whiskers as SD/SEM error bars.
- **Histogram/density/ridgeline**: record bin width or density method when reported and do not recover exact observations from a smooth density.
- **Pie/donut/stacked/area/stream**: record the denominator/population scope and verify components sum consistently within rounding tolerance.
- **Radar/parallel coordinates**: record normalization and axis direction; visual polygon area or line crossing is not a validated aggregate score.

## Prohibited encodings

- Do not store two endpoints or units in one scalar string.
- Do not use sample size as a mathematical denominator or an x-condition.
- Do not map a series to an axis solely because they share a color unless the graphic or caption establishes the mapping.
- Do not infer significance from visual separation or error-bar overlap.
- Do not force categorical labels into numeric values; use `value.category`.

## Derived values

Use a symbol-safe expression containing only numbers, symbols, `+ - * / **`, and parentheses. Record all inputs, tolerances, units, and evidence. Compare the evaluator result with the author-reported value using a justified tolerance.

For a conflict, populate `rounding_interval_check`. Do not attribute a discrepancy to display rounding without explicit input intervals and a recomputed endpoint interval. If precision is unavailable, use `not_evaluable` and keep the conflict visible.

If displayed error bars belong to a calculated endpoint, record whether propagation was reported. A calculated result with displayed uncertainty cannot use `error_propagation.status=not_applicable`.

## Origin versus extraction

- `direct_measurement`: directly acquired endpoint.
- `calculated`: formula/model-derived endpoint.
- `author_reported`: text-only author result.
- `unknown`: generation mode not established.

Separately use `image_estimate`, `text_transcription`, `direct_report`, or `calculated_from_evidence` for recovery method. A point read from pixels is `image_estimate` even if the paper says the underlying quantity was measured.

## Statistics

- `descriptive`: summary without a test-based claim.
- `inferential`: test/model-based comparison or significance claim.
- `not_applicable`: no statistical summary applies.
- `unclear`: insufficient source information.

Assign a specific replicate type only when raw text or cited evidence explicitly supports it. “Measured three times” gives a count, not a biological/technical/independent classification.

Only an inferential/significance claim can justify `MISSING_STATISTICS`. Preserve P-value relations and attach each P value to a readable comparison. A star without a threshold mapping is not a P value.
