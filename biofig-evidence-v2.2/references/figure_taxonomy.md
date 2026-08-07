# Biomedical figure taxonomy

Classify each panel along three linked fields:

1. `figure_category`: scientific function, restricted to six categories.
2. `panel_type`: the most specific canonical type.
3. `result_profile`: the public table profile fixed by the registry.

`schemas/figure_registry.json` is normative. Search it for the canonical type and copy its category/profile pair; do not invent or freely override a profile.

## Selection rules

- Split a multi-panel figure by modality, endpoint, axis, or protocol before classifying. Do not use `mixed` to avoid segmentation.
- Classify by scientific use, not geometry alone. A generic line is `line`; a survival line is `kaplan_meier`; a dose-fit line is `dose_response`; a training line is `learning_curve`.
- Use domain-specific types instead of a generic visual alias: `enrichment_bar` rather than `bar`, `confusion_matrix` rather than `heatmap`, and `flow_scatter` rather than `scatter`.
- If a single panel genuinely contains inseparable heterogeneous evidence, use `mixed`, explain why, add `MIXED_PANEL_NOT_SEGMENTED` when segmentation is still needed, and render one subtable per block.
- Use `other` only after checking the registry. Describe the unsupported type and add review when it affects a requested result.

## 1. Basic statistics

Canonical types: `bar`, `horizontal_bar`, `line`, `scatter`, `bubble`, `box`, `violin`, `dot_strip`, `histogram`, `density`, `ridgeline`, `beeswarm`, `pie_donut`, `stacked_bar`, `area_stream`, `radar`, `parallel_coordinates`, `time_course`, and `dual_axis`.

Use for ordinary group comparison, distribution, trajectory, association, composition, or multivariate display. If the scientific use is omics, clinical, imaging, or model evaluation, prefer the corresponding specific type below.

## 2. Omics and bioinformatics

Canonical types: `volcano`, `heatmap`, `pca`, `umap`, `tsne`, `biplot`, `venn`, `upset`, `go_kegg_bubble`, `enrichment_bar`, `gsea_curve`, `kegg_pathway`, `manhattan`, `chromosome_plot`, `circos`, `chord`, `sankey`, `ppi_network`, `coexpression_network`, `cerna_network`, `gene_structure_lollipop`, and `trait_module_heatmap`.

Distinguish differential-feature evidence, matrices/embeddings, enrichment/sets, genomic loci, and networks. Record the transformation, contrast, threshold, background, database/version, and multiple-testing method when applicable.

## 3. Clinical and epidemiological

Canonical types: `consort_flow`, `prisma_flow`, `kaplan_meier`, `roc_curve`, `forest_plot`, `nomogram`, `calibration_plot`, `decision_curve`, `time_dependent_roc`, `repeated_measures`, `survival_roc`, `cumulative_incidence`, `icc_plot`, `bland_altman`, and `psm_balance`.

Keep population, endpoint, time horizon, effect-measure type, confidence interval, adjustment model, validation cohort, and risk/flow counts explicit.

## 4. Experimental raw images

Canonical types: `western_blot`, `co_ip`, `agarose_gel`, `sds_page`, `southern_blot`, `northern_blot`, `eastern_blot`, `mass_spectrum`, `sanger_chromatogram`, `immunofluorescence`, `confocal_microscopy`, `edu_brdu`, `he_histology`, `immunohistochemistry`, `tissue_microarray`, `transwell`, `colony_formation`, `flow_histogram`, `flow_scatter`, `flow_tsne`, `cell_viability_curve`, `colony_plaque_count`, `sem`, `tem`, `ivis`, `micro_ct`, `gross_pathology`, plus the compatible generic types `microscopy`, `histology`, `oct`, `flow_cytometry`, and `image_series`.

Treat image evidence as qualitative unless the source supplies a calibrated or reported measurement. Require the appropriate channel/stain/scale, lane/target/control, gate/denominator, or spectral/sequence annotation.

## 5. Mechanism, workflow, and schematic

Canonical types: `mechanism_diagram`, `pathway_diagram`, `process_diagram`, `workflow_diagram`, `research_framework`, `graphical_abstract`, `multi_panel`, `anatomy_schematic`, `surgery_schematic`, `device_schematic`, `molecular_structure`, `molecular_docking`, `cytoskeleton_schematic`, `subcellular_schematic`, `conceptual_model`, `geographic_map`, `reconstruction_3d`, `schematic`, and `mixed`.

Use process steps for ordered operations and relationships for entity graphs. A drawn relation is `depicted`; it is not experimental evidence unless a cited result supports it.

## 6. Tables and specialized figures

Canonical types: `baseline_table`, `statistical_summary_table`, `multivariable_regression_table`, `subgroup_table`, `drug_sensitivity_ic50`, `immune_infiltration`, `tmb_msi`, `shap_plot`, `learning_curve`, `confusion_matrix`, `dose_response`, `calcium_trace`, `electrophysiology_trace`, `tracking_plot`, and `other`.

Use dedicated clinical effect, dose-response, model explanation, matrix, or signal profiles rather than a generic table layout.

## Ambiguous cases

- A CCK-8/MTT plot is `cell_viability_curve` when the focus is assay response over time or treatment; use `dose_response` when a fitted concentration-response relation and IC50/EC50 are central.
- An IC50 box plot comparing risk groups is `drug_sensitivity_ic50`; an individual fitted curve is `dose_response`.
- A clinical covariate heatmap is not automatically omics. Use a specific table/specialized type when available and document the classification limit otherwise.
- A Sankey diagram is `sankey` even though its public profile is relation/flow oriented; a CONSORT/PRISMA diagram uses ordered flow steps.
- A multi-panel figure is a layout. Classify each labelled panel independently; reserve `multi_panel` for an inseparable composite panel.
