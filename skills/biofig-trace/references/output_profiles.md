# 结构化结果模板

本文件规定 `results.template` 对应的最低字段和公开表格列。字段状态和证据性质遵循全局证据契约；领域解释规则由相应领域参考资料规定。

## 通用记录规则

- 每条记录必须有唯一 `record_id`、`measurement_origin`、证据引用和置信度。
- `results.template` 必须与面板 `classification.result_template` 相同。
- 每个模板只包含适用字段；必需但无法获得的字段使用明确状态，不得删除或填零。
- 数值、单位、区间、误差定义和统计方法分字段保存，不拼成不可解析长句。
- 公开表只渲染科学字段，不显示内部 ID、状态枚举或 JSON 路径。

## 模板矩阵

| 模板 | 最低机器字段 | 公开表重点 |
|---|---|---|
| `group_comparison` | `group`, `endpoint`, `result`, `error_definition`, `sample_size`, `statistical_method` | 组别、终点、结果、误差、n、统计方法 |
| `dose_response` | `agent`, `experimental_system`, `dose_range`, `response_endpoint`, `potency`, `interval`, `fit_model` | 药物/刺激、系统、剂量范围、响应、IC50/EC50、区间、拟合 |
| `omics_feature` | `feature`, `direction`, `contrast`, `effect_size`, `significance`, `thresholds`, `multiple_testing` | 特征、比较、效应、方向、P/FDR、阈值 |
| `clinical_effect` | `endpoint`, `population`, `effect_measure`, `estimate`, `confidence_interval`, `p_value`, `reference_group`, `adjustment_model` | 终点、人群、效应量、估计、95% CI、P、参考、模型 |
| `image_observation` | `sample`, `modality`, `stain_or_channel`, `observation`, `scale_bar`, `quantification`, `limitations` | 样本、模态、通道/染色、所见、比例尺、定量、限制 |
| `blot_lane` | `lane`, `target`, `molecular_weight`, `loading_control`, `control`, `band_observation`, `quantification` | 泳道、靶标、分子量、内参、对照、条带、定量 |
| `flow_population` | `population`, `gating_hierarchy`, `markers`, `denominator`, `proportion_or_count` | 群体、门控层级、标记、分母、比例/计数 |
| `workflow_step` | `step`, `input`, `operation`, `parameters`, `output`, `predecessors`, `branch` | 步骤、输入、操作、参数、输出、前置、分支 |
| `mechanism_relation` | `upstream`, `relation`, `downstream`, `direction`, `evidence_nature`, `confidence` | 上游、关系、下游、方向、证据性质、置信度 |
| `specialized_table` | `variable`, `group`, `statistic`, `missingness`, `interval`, `footnote_definition` | 变量、分组、统计量、缺失、区间、脚注 |

## `group_comparison`

- `group` 必须表示可辨认的组或条件；参考组另有信息时在条件或统计语境中保存。
- `result` 保留值、单位和边界关系。
- `error_definition` 分清 SD、SEM、CI、IQR、范围、须线、无或未知。
- `sample_size` 包含数值、分析单位和重复层级；仅有“重复三次”时不得猜重复类型。
- `statistical_method` 包含方法及具体比较；描述性图没有检验时使用不适用，不制造缺失 P 值。

## `dose_response`

- `potency` 同时保存参数名称和值，例如 IC50 与 1.4 µM；不得把 log(IC50) 当作 IC50。
- `interval` 必须注明区间类型和水平；未报告时使用正确缺失状态。
- `fit_model` 保留模型名称和参数化；重拟合结果通过派生值记录。

## `omics_feature`

- `effect_size` 明确是 log2FC、相关系数、NES 或其他量。
- `significance` 保留原始或校正后定义及关系符号。
- `thresholds` 与 `multiple_testing` 分开，不能用阈值名称代替校正方法。

## `clinical_effect`

- `effect_measure`、`estimate`、`confidence_interval` 和 `p_value` 分列。
- `reference_group` 与 `adjustment_model` 不能藏在自由文本估计值中。
- 不同效应量类型不能合并为一个无类型数值列。

## 图像、泳道和流式模板

- `image_observation` 以直接所见为核心；`quantification` 仅接受作者报告或有校准的测量。
- `blot_lane` 每条记录对应一条泳道或一个明确比较，不把多泳道压成一句话。
- `flow_population` 的比例必须绑定父门或分母；群体名称不能只由点云位置猜测。

## 流程、机制和专门表格模板

- `workflow_step.predecessors` 只存有效步骤 ID；报告解析为步骤名称。
- `mechanism_relation.evidence_nature` 通常为 `depicted`；只有另有直接证据时才使用其他性质。
- `specialized_table.statistic` 保留统计量类型和值；`footnote_definition` 解析符号、单位、参考组和缺失规则。

## 渲染约束

- 省略所有记录均为 `not_applicable` 的列。
- 保留影响解释的 `unknown` 或 `not_recoverable`，但用自然语言显示原因。
- 不把工作流、图像或机制记录强制渲染成 x/y/误差表。
- 高维记录按 `reporting_scope` 渲染；不得静默截断。
