# 人工复核与失败策略

本文件规定何时创建 `review.suggestions`、如何确定优先级、如何审计来源消费，以及失败时如何保留可用结果。复核是风险控制，不表示研究结果重要或不重要。

## 创建复核建议

每条建议必须包含：

- 稳定 `code`；
- `priority`；
- 受影响的 `panel_ids`；
- 具体科学风险 `reason`；
- 最小决定性动作 `action`；
- 可用的证据引用。

不要写“请人工确认”一类泛化动作。应写“查看未裁切 blot 以确认第 4 泳道的 loading control”或“核对方法段中误差线定义”。

## 优先级

| 优先级 | 判定标准 | 示例 |
|---|---|---|
| `critical` | 可能改变研究对象、轴、组别、单位、效应量类型、方向或主结论 | 图例映射反转、HR 被误作 OR、剂量单位不明 |
| `high` | 影响关键数值、统计支持、模型解释、证据性质或可复现性 | IC50 模型不明、流式父门缺失、未解决来源冲突 |
| `medium` | 局部条件或元数据缺失，限制解释但通常不改变主方向 | 暴露时间缺失、图像比例尺不可读 |
| `low` | 非关键定位或展示问题 | 打印页码未知但 PDF 页可定位 |

任一 `critical` 或 `high` 建议都要求面板及根级 `review.required=true`。根级 `highest_priority` 必须等于所有建议中的最高值。只有 `low` 建议时，可按用户请求决定是否要求复核，但必须保持布尔值与说明一致。

## 推荐复核代码

- `MISSING_CAPTION`：图注缺失或不完整。
- `UNREADABLE_AXIS`：轴标签、刻度、尺度或单位不可读。
- `UNREADABLE_LEGEND`：视觉标记无法映射到组或系列。
- `LOW_IMAGE_QUALITY`：分辨率、压缩、焦点、饱和或裁切阻止恢复。
- `VALUE_NOT_RECOVERABLE`：必要值无法在不猜测的情况下恢复。
- `AMBIGUOUS_CLASSIFICATION`：具体图型或结果模板无法可靠确定。
- `MIXED_PANEL_NOT_SEGMENTED`：异质内容仍未分面板。
- `AMBIGUOUS_CONDITION`：处理、对照、时间或固定条件映射不明。
- `MISSING_DENOMINATOR`：比例、百分比或条件概率缺少分母。
- `MISSING_STATISTICS`：已有推断性结论但所需统计支持缺失。
- `UNMAPPED_SIGNIFICANCE`：星号或符号缺阈值/比较映射。
- `MISSING_MULTIPLE_TESTING`：多重检验校正定义缺失。
- `MISSING_MODEL_SPECIFICATION`：效应、预测或拟合模型语境不完整。
- `MISSING_SCALE_OR_CHANNEL`：比例尺、通道、染色或颜色映射缺失。
- `MISSING_LANE_OR_CONTROL`：泳道、靶标、内参、IgG 或其他对照缺失。
- `MISSING_GATE_OR_DENOMINATOR`：流式门控层级、父群体或分母缺失。
- `MISSING_FIT_INFORMATION`：剂量响应模型、区间或拟合信息缺失。
- `SOURCE_CONFLICT`：来源在同一语境下不一致。
- `DERIVATION_MISMATCH`：复算值与报告值超出有依据的容差。
- `VISUAL_CHECK_NOT_PERFORMED`：请求涉及图像但未完成视觉检查。
- `OTHER`：其他实质风险；必须在 `reason` 中精确定义。

`MISSING_STATISTICS` 只用于论文或当前解释提出推断/显著性结论的情况。纯描述性面板没有 P 值不是自动缺陷。

## 来源消费审计

对每个选中的图像、图注、方法、结果和补充来源建立 `source_coverage`：

- `consumed`：相关事实已进入一个或多个可解析 `field_paths`；
- `partially_consumed`：仅部分事实进入字段，`reason` 说明剩余限制；
- `not_consumed`：相关来源被检查但有明确理由未采用，路径为空；
- `unavailable`：来源未取得或不可读，路径为空并说明访问限制。

`consumed` 和 `partially_consumed` 至少有一个有效 JSON Pointer。`not_consumed` 和 `unavailable` 不得有路径。不可用来源不得被证据项引用。不要静默遗漏已选择的相关来源。

## 局部失败

- 只将受影响字段设为 `unknown` 或 `not_recoverable`，保留其他可验证内容。
- 一个面板不可读不应使其他面板失败。
- 未请求精确数字化时，缺少逐点数值不是自动失败。
- 图像、流程或机制图不因没有方差而失败。
- 缺少原始数据时保留作者报告值和限制，不伪造复算。
- 无法分类时保留可确定的粗粒度信息并提出最小复核动作。

## 冲突处置

冲突出现时保留各来源陈述和证据，说明它影响哪个字段和结论。只有事实类型适用、来源范围相同且依据明确时才使用来源优先规则；即使形成工作解释，也不得删除其他陈述。未解决或不可评估冲突至少为 `high`，并必须出现在报告中。

## 完成与验证

- `run.status=complete` 表示请求范围已处理，不表示论文报告了所有科学字段。
- `partial` 用于关键来源、面板或请求字段未处理完成，但仍有可交付证据。
- `failed` 运行不得留下声称 `validated` 的正式 `evidence.json` 或 `report.md`。
- 验证戳只能由最终验证脚本在 Schema、语义、报告和复验全部通过后写入。
- 最终写入必须原子化；验证失败时保留诊断，不覆盖上一份有效交付物。
