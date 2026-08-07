# Clinical and epidemiological figures

Apply these rules to participant/document flows, survival/event outcomes, diagnostic/prediction performance, effect estimates, agreement, matching, and repeated measures.

## Population and model context

Record study design, population/cohort, inclusion/exclusion, endpoint definition, time origin/horizon, censoring or competing event, analysis population, sample size, missingness, adjustment variables/model, internal/external validation, and reference group when reported.

## CONSORT and PRISMA flows

- Use `process_steps`, not a quantitative error table.
- Record count entering each stage, exclusions/dropouts with reasons, branch allocation, analysis set, and predecessor/next destination.
- Check arithmetic across branches while preserving author values. A mismatch becomes a source/calculation conflict.
- Do not label participant/document counts as variance, uncertainty, or replicate statistics.

## Survival and competing risks

- Kaplan–Meier: record groups, endpoint, time unit/range, survival probabilities or median survival, numbers at risk, log-rank P, and HR with 95% CI when reported.
- Cumulative incidence: record the competing event and use the reported SHR/cause-specific HR correctly.
- Time-dependent/survival ROC: record horizon, AUC and 95% CI, cohort, censoring method when reported.
- Absence of a risk table is a review issue when it blocks interpretation; use `MISSING_RISK_TABLE`.

## Diagnostic and prediction performance

- ROC: record positive class, AUC, 95% CI, threshold, sensitivity, specificity, cohort, and validation type.
- Calibration: record horizon, observed versus predicted definition, calibration intercept/slope or error when reported.
- Decision curve: record threshold range, net-benefit definition, comparator strategies, and cohort.
- Nomogram: record predictors, scoring direction, predicted outcome/horizon, and validation/calibration evidence. The graphic alone does not establish clinical utility.

## Effect estimates

- Forest/regression/subgroup: preserve effect-measure type (HR, OR, RR, coefficient, mean difference), reference group, point estimate, 95% CI, P value, adjustment model, interaction P for subgroup claims, and null value (1 for ratios; 0 for differences).
- Do not compare HR, OR, and RR as if interchangeable.
- Do not call subgroup effects different solely because one subgroup is significant and another is not; require an interaction comparison.

## Agreement, matching, and repeated measures

- ICC: record ICC type/model, confidence interval, and unit/replicates.
- Bland–Altman: record bias, limits of agreement, transformation, repeated observations, and clinical acceptability threshold when defined.
- PSM balance: record matching method/caliper, pre/post sample sizes, SMD threshold, and variables. A P value is not a substitute for balance diagnostics.
- Repeated measures: retain subject pairing, time points, missing observations, model/test, and within-subject uncertainty.

## Review triggers

Use `MISSING_MODEL_SPECIFICATION`, `MISSING_RISK_TABLE`, `MISSING_STATISTICS`, `AMBIGUOUS_COMPARISON`, `MISSING_DENOMINATOR`, or `SOURCE_CONFLICT` when the missing/conflicting item affects interpretation. Make the action specific: retrieve the risk table, model footnote, validation cohort definition, or analysis population.
