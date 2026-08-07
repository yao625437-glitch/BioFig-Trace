# Omics and bioinformatics figures

Apply these rules to differential expression, matrices, embeddings, enrichment, genomic loci, networks, and multi-omics displays.

## Shared context

Record the assay/omics layer, comparison or phenotype, species/build when relevant, unit of analysis, normalization/transformation, batch correction, feature filtering, database/version, background universe, statistical method, multiple-testing correction, and thresholds. Do not assume Z-score normalization because a heatmap is shown.

## Differential features and genomic loci

- Volcano: recover feature, contrast, log2FC/effect, raw or adjusted P definition, direction, and thresholds. Do not call a point significant from color alone without the legend or method.
- Manhattan/chromosome/lollipop: record chromosome/gene coordinate, reference build, variant/feature, effect or significance, threshold, and annotation.
- Use `feature_significance`; represent author-labelled/key features or a disclosed selected set, and set `reporting_scope` for large result sets.

## Matrices and embeddings

- Heatmap: record row/column objects, displayed value, scale, transformation, clustering method/distance, annotation bars, and whether values are centered or standardized.
- PCA/biplot: record explained variance for displayed components and loading interpretation when available.
- UMAP/t-SNE: record group labels and algorithm parameters when reported. Local visual proximity does not establish effect size, trajectory, or statistical significance.
- Detect batch separation descriptively; do not claim a batch effect without design/context evidence.
- Use `matrix_embedding` and disclose selection/summarization for large matrices or cell-level coordinates.

## Sets and enrichment

- Venn/UpSet: record set definitions, universe, intersection membership/count, and whether counts overlap.
- GO/KEGG bubble/bar: record term, gene ratio/overlap, count, raw P, adjusted P/FDR, database/version, background set, and direction when defined.
- GSEA: record gene-set name, ES/NES, nominal P, FDR, leading edge, ranking metric, and direction.
- A visually large bubble is not automatically more significant; decode size and color separately.

## Networks and flows

- KEGG/pathway/PPI/coexpression/ceRNA: create explicit `relationships` with entities, relation, direction/sign, weight if reported, and evidence nature.
- Circos/chord/Sankey: record source, target, flow/weight, grouping, scale, and filtering rule.
- Distinguish database interaction, computed association, author-depicted relation, and experimentally validated relation. Use `depicted`, `reported`, `observed`, or `inferred` accurately.
- Do not infer biological causation from topology, hub degree, coexpression, or flow layout.

## Review triggers

Use targeted review when normalization, contrast, multiple-testing correction, background universe, database/version, batch handling, cluster identity, or edge semantics are missing and materially affect the requested conclusion. Use `MISSING_NORMALIZATION`, `MISSING_MULTIPLE_TESTING`, `MISSING_MODEL_SPECIFICATION`, or `OTHER` as appropriate.
