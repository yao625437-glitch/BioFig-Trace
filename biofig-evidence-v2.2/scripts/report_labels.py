#!/usr/bin/env python3
"""Stable human-facing labels for Biofig Evidence reports."""

EXTRACTION_STATUS = {"complete": "完整", "partial": "部分完成", "failed": "未完成"}
CONFIDENCE = {"high": "高", "medium": "中", "low": "低", "unknown": "待定"}
SEVERITY = {"critical": "关键", "major": "重要", "minor": "一般"}
SOURCE_TYPE = {
    "image": "原图", "caption": "图注", "results": "结果正文", "methods": "方法",
    "supplement": "补充材料", "metadata": "文献元数据", "user": "用户说明",
}
SOURCE_SCOPE = {
    "figure_context": "图表语境", "experimental_conditions": "实验条件", "results": "结果解释",
    "statistics": "统计定义", "other": "其他",
}
CONDITION_NAME = {
    "age": "年龄", "assay": "检测方法", "batch": "批次", "cell line": "细胞系",
    "absolute log2fc threshold": "|log₂FC| 阈值", "contrast": "比较", "dose": "剂量",
    "endpoint": "终点", "exposure": "暴露时间", "fdr threshold": "FDR 阈值",
    "feature": "特征",
    "fit model": "拟合模型", "group": "分组", "model": "模型", "normalization": "归一化",
    "population": "研究人群", "reference group": "参照组", "risk group": "风险分组",
    "sex": "性别", "strain": "品系", "temperature": "温度",
    "threshold": "阈值", "time": "时间", "treatment": "处理",
}
COVERAGE_STATUS = {
    "consumed": "已使用", "partially_consumed": "部分使用",
    "not_consumed": "未使用", "unavailable": "不可用", "not_applicable": "未使用",
}
ERROR_KIND = {"sd": "SD", "sem": "SEM", "ci": "置信区间", "range": "范围", "unknown": "类型未说明", "none": "未显示"}
COMPARISON_STATUS = {"consistent": "一致", "conflict": "不一致", "not_comparable": "不可比较"}
CONFLICT_KIND = {
    "source_text": "正文来源不一致", "image_text": "图文不一致", "calculation": "复算不一致",
    "unit": "单位不一致", "direction": "方向不一致", "other": "其他不一致",
}
RESOLUTION = {"unresolved": "尚未解决", "reported_with_caveat": "保留并注明限制", "resolved_by_primary_source": "已由主要来源核定"}
EPISTEMIC_STATUS = {"depicted": "图中示意", "observed": "图中可见", "reported": "作者报告", "inferred": "基于证据推断"}
DIRECTION = {"directed": "单向", "undirected": "无向", "bidirectional": "双向", "unknown": "方向未明"}
SIGN = {
    "activation": "激活", "inhibition": "抑制", "association": "关联", "flow": "流向",
    "containment": "包含", "binding": "结合", "unknown": "作用未明", "not_applicable": "不适用",
}
REVIEW_CODE = {
    "MISSING_CAPTION": "图注缺失或不完整",
    "UNREADABLE_AXIS": "坐标轴信息无法可靠读取",
    "UNREADABLE_LEGEND": "图例无法可靠读取",
    "LOW_IMAGE_QUALITY": "图像质量限制信息恢复",
    "VALUE_NOT_RECOVERABLE": "关键数值无法可靠恢复",
    "MISSING_STATISTICS": "支持推断所需的统计信息缺失",
    "UNMAPPED_SIGNIFICANCE": "显著性符号未给出阈值映射",
    "AMBIGUOUS_COMPARISON": "统计结果对应的比较不明确",
    "SOURCE_CONFLICT": "不同来源或复算结果不一致",
    "UNSUPPORTED_FIGURE": "当前流程不足以可靠解析该图",
    "AMBIGUOUS_CONDITION": "实验条件归属不明确",
    "AMBIGUOUS_SERIES_MAPPING": "系列与图形标记的对应不明确",
    "MISSING_DENOMINATOR": "比例或百分比的分母缺失",
    "UNSPECIFIED_ERROR_PROPAGATION": "派生指标的误差传播方法未说明",
    "MISSING_SCALE_BAR": "空间图像缺少可靠比例尺",
    "MISSING_NORMALIZATION": "归一化或数据变换方法缺失",
    "MISSING_MULTIPLE_TESTING": "多重检验校正信息缺失",
    "MISSING_RISK_TABLE": "生存图风险人数表缺失",
    "MISSING_MODEL_SPECIFICATION": "统计或预测模型设定不完整",
    "MISSING_CONTROL": "关键实验对照缺失或不明确",
    "MISSING_CHANNEL_MAPPING": "成像通道、染色或标记映射缺失",
    "MISSING_GATE_OR_DENOMINATOR": "流式门控或比例分母缺失",
    "MISSING_LANE_METADATA": "泳道、靶标或内参信息缺失",
    "MISSING_FIT_INFORMATION": "拟合模型、区间或拟合质量信息缺失",
    "MIXED_PANEL_NOT_SEGMENTED": "异质子图尚未拆分",
    "OTHER": "其他需复核事项",
}
