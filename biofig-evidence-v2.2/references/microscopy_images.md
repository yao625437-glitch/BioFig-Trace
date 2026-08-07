# Experimental raw images

Apply these rules to microscopy, histology, blots/gels, flow cytometry, spectra/chromatograms, proliferation/migration assays, colony/plaque images, electron microscopy, in-vivo imaging, CT, and gross pathology.

## Evidence boundary

- Put directly visible morphology, localization, distribution, band, gate, peak, or signal observations in `qualitative_observations` with image evidence.
- Put author interpretations in `claims` with `reported` status and text evidence.
- Do not invent counts, intensity ratios, segmentation, distances, magnification, molecular size, cell identity, or scale.
- A calibrated/reported measurement may enter `measurements`; a pixel estimate must be approximate, state calibration/tolerance, and trigger review when it affects the conclusion.
- Use `not_applicable` for numeric extraction when a qualitative observation is sufficient. Do not create `VALUE_NOT_RECOVERABLE` merely because digitization was not requested.

## Microscopy, histology, and in-vivo imaging

Record specimen/system, group/treatment, modality, channels/stains/markers, color mapping, scale-bar text/unit, magnification when reported, region/field, time, image selection, and whether the panel is representative.

Flag saturation, clipping, focus, channel ambiguity, absent scale, unequal display settings, non-comparable fields, selective fields, or missing controls when material. H&E/IHC interpretation must remain descriptive unless pathology scoring and criteria are reported.

For IF/confocal/EdU/BrdU/IHC, distinguish signal presence/localization from quantified intensity/positive proportion. For SEM/TEM/Micro-CT/3D reconstruction, spatial claims require reliable scale or calibration.

## Blots, Co-IP, and gels

Record lane order, sample/treatment, target, expected/reported molecular size, ladder, input, IP antibody, IB target, IgG control, loading control, exposure, cropping, normalization, and quantitative method when available.

- A darker band is a visual observation, not a normalized fold change.
- Co-IP requires correct Input/IgG/IP/IB mapping before an interaction claim.
- Quantified Western blot evidence requires an internal/loading control or an explicit alternative normalization.
- Use `MISSING_LANE_METADATA` or `MISSING_CONTROL` when missing mappings affect the requested conclusion.

## Flow cytometry

Record axes/markers/transformation, gate hierarchy, parent population/denominator, quadrant/gate labels, compensation/control, count/percentage, and sample/group.

- A percentage without its parent gate is incomplete; use `MISSING_GATE_OR_DENOMINATOR`.
- Do not identify a cell population from location alone when marker labels or gates are missing.
- A t-SNE/UMAP flow display is a visualization of measured markers, not a statistical test.

## Spectra and chromatograms

For mass spectra, record m/z, intensity, charge/adduct, peak annotation, identification confidence, and matching method when reported. For Sanger traces, record base position, reference/alternate call, strand, quality/ambiguity, and source sequence. Do not name an unlabelled peak or call an ambiguous base by visual guess.

## Assay-result images

For Transwell, colony formation, plaques, IVIS, or other assay images, record group, field/sample selection, stain/signal, visible pattern, count/area/intensity only when reported or reliably calibrated, normalization, and replicate unit. A representative image alone does not establish the group mean.
