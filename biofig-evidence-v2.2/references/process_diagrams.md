# Mechanism, workflow, and schematic figures

Apply these rules to experimental workflows, clinical/document flows, research frameworks, graphical abstracts, mechanism/pathway diagrams, anatomical/device/surgical schematics, conceptual models, maps, docking/structure diagrams, and inseparable composites.

## Workflows

- Preserve step order, branches, loops, inputs, outputs, durations, temperatures, concentrations, equipment, sample counts, and decision points exactly when readable.
- Put each node in `process_steps` with stable ID, order, input, operation label, parameters, output, predecessor IDs, evidence, and confidence.
- Resolve predecessor IDs to human step labels in the report.
- Do not invent missing transitions or treat a stylized arrow as experimental efficacy.
- Set displayed error bars to none. The public workflow table must not contain x/y, variance, CI, or P-value columns.
- Record diagram/Methods conflicts instead of choosing one silently.

## Mechanisms and networks

- Put each explicit edge in `relationships`: source entity, relation text, target entity, direction, sign, optional magnitude, epistemic status, evidence, and confidence.
- Use `depicted` for a drawn relation. Upgrade to `reported` or `observed` only when corresponding text or direct result evidence is cited.
- Distinguish activation, inhibition, binding, association, containment, and flow; use `unknown` when arrowhead/sign semantics are unclear.
- Do not fill a missing mechanistic link with background knowledge unless the user explicitly requests a separate literature synthesis; such synthesis remains `inferred` and must not be attributed to the paper.

## Specialized schematics

- Anatomy/surgery/device: record structures/components, orientation, sequence, dimensions/settings, and intended function. A drawing may not be to scale.
- Molecular structure/docking: record ligand/receptor, pose/site, interaction labels, score/unit, and computational method when reported. A docking pose does not prove binding in vivo.
- Geographic map: record geography, time, denominator/rate definition, legend scale, and missing regions.
- 3D reconstruction: record source modality, segmentation/reconstruction method, scale, orientation, and whether geometry is measured or illustrative.
- Graphical abstract/research framework: separate question, input, method, result, and proposed conclusion; identify which elements are results and which are narrative synthesis.

## Composite panels

Split labelled or spatially separable components into distinct panels. If the panel remains `mixed`, populate each applicable block and explain the inseparability. Add `MIXED_PANEL_NOT_SEGMENTED` when unresolved mixing could hide conditions, values, or evidence status.
