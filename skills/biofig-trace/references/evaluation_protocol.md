# 独立评测与 uplift 协议

## 1. 适用范围

本协议用于比较同一任务在“挂载 BioFig Trace Skill”和“不挂载 Skill”两种条件下的输出。两组必须使用相同模型版本、temperature、token 上限、工具权限、输入文件、CPU/内存和超时；唯一实验变量是 Skill 是否挂载并激活。

`tests/evaluate_uplift.py` 是独立的纯 Python 标准库评分器。它不导入、调用或信任项目的 Schema、语义、报告或最终化 validator，避免“由被测系统给自己打分”。

> **重要：** `tests/fixtures/scoring_*.json` 全部是人为构造的 **scorer unit fixture**，只用于验证匹配、容差、惩罚和中位数算术。其中的分数不是实际模型运行结果、benchmark 成绩或 BioFig Trace 性能声明，禁止在 README、报告、演示或投稿材料中引用为真实成绩。

## 2. 金标科学原子

每个任务由若干独立科学原子组成。原子使用 `key` 标识科学语义，不依赖模型生成的数组位置、UUID 或 evidence ID。例如：

```json
{
  "key": {
    "panel": "C",
    "entity": "Drug X",
    "endpoint": "IC50",
    "attribute": "estimate"
  },
  "value": 1.4,
  "unit": "µM",
  "match": {
    "type": "numeric",
    "abs_tol": 0.05,
    "rel_tol": 0.01,
    "digitization_tol": 0.0
  }
}
```

`key` 的对象顺序不影响匹配；字符串执行 Unicode NFKC、空白折叠和大小写归一化。科学数值和单位不做这种宽松处理：单位仅执行 Unicode/空白归一化并保留大小写，因此 `µM` 与 `μM` 等价，而 `mM` 与 `mm` 不等价。真实评测的 key 应由面板、实体、终点、比较、条件和属性等稳定科学键组成，不得使用输出顺序或随机 ID。

金标应由至少两名标注者独立标注并裁决。每个原子需在冻结前确定来源定位、证据性质、期望缺失状态及容差；不得根据待测输出反向扩大容差。

用于“额外事实惩罚”的金标必须覆盖该任务计划评分的科学事实空间；若标注者有意只标少数目标字段，就只能把输出映射到该目标字段白名单后再评分，不能把未标注但有来源支持的事实误判为幻觉。Skill 与 baseline 必须使用同一个冻结的独立映射器。

## 3. 匹配与数值容差

支持三种匹配模式：

- `exact`：JSON 标量精确相等；
- `normalized_text`：文本执行 NFKC、空白折叠和大小写归一化后相等；
- `numeric`：数值与单位合法，并满足预先冻结的容差。

数值判定公式为：

```text
|prediction - gold| <= max(
    abs_tol,
    rel_tol * |gold|,
    digitization_tol
)
```

`abs_tol` 用于原文舍入或绝对误差，`rel_tol` 用于量级相关容差，`digitization_tol` 用于图上估读。三者缺省均为 0，且必须是有限非负数。跨单位换算应在生成评测原子前由独立数据准备流程转换到同一规范单位，不应让待测 Skill 决定评分换算。

## 4. 额外无依据事实惩罚

令 `G` 为金标原子数，`M` 为正确匹配数，`E` 为没有对应金标科学键的预测原子数，加上同一科学键的重复预测数。单次运行分数为：

```text
run_score = M / (G + E)
```

因此，20 个金标字段匹配 15 个且没有额外事实时得 0.75。错误值对应一次漏配；新增的 P 值、样本量、因果机制等无依据事实还会增加分母。纯连接性文字不应转写成评测原子，只有新的科学事实、条件、数值、关系或结论才计入 `E`。

同一科学键出现多个预测时，最多一个可以匹配，其余计为重复额外事实。`failed` 或 `timeout` 运行记 0，不能从三次结果中删除。

运行文档按任务保存恰好三个结果：

```json
{
  "tasks": [
    {
      "task_id": "blind-task-001",
      "runs": [
        {"run_id": "run-1", "status": "completed", "atoms": []},
        {"run_id": "run-2", "status": "failed"},
        {"run_id": "run-3", "status": "completed", "atoms": []}
      ]
    }
  ]
}
```

从 `evidence.json`、`report.md` 或 baseline 自由文本到科学原子的映射不属于被测 Skill，也不能调用项目 validator。正式评测应使用仓库外冻结的独立 adapter，并保存 adapter 版本和输入/输出哈希以便复算。

## 5. 三次重复与 uplift

每个任务、每种条件必须恰好运行三次。每次使用独立输出目录和空会话，Skill 与 baseline 的执行顺序应随机交错。计算顺序固定为：

```text
skill_task = median(skill_run_1, skill_run_2, skill_run_3)
baseline_task = median(base_run_1, base_run_2, base_run_3)
uplift_task = skill_task - baseline_task
```

跨任务先对每个任务取中位数，再做宏平均；不得先汇总全部九个或更多运行后取一个总体中位数。评分器同时输出每任务、每类别和总体宏平均结果。正式报告还应列出三次运行的原始分数、失败状态和极差，不能只展示最好一次。

## 6. baseline 公平性

baseline 与 Skill 组必须接收字节级相同的自然语言任务和公开论文材料。baseline 不挂载 Skill，不能读取其 `SKILL.md`、`references/`、`schemas/`、示例、历史对话或缓存。若评测要求共同的最小输出契约，该契约必须同时提供给两组；不得只为 baseline 添加纠错提示，也不得把金标字段值写入任务。

客观评分只比较标准化科学原子。科学可信性、5C 报告、领域边界和产品体验可另由匿名 LLM/人工 rubric 评分，但不能用 LLM 评分替换这里的可复算字段分。

## 7. 防止评测泄露

- 公共单元 fixture 与私有 holdout 完全分离；正式分数只使用未进入仓库的 holdout。
- 私有 gold 和 scorer runner 存放在 Skill 仓库之外，执行时只读挂载且不向被测进程暴露路径。
- holdout 不复用 `examples/` 的图像、标题、数值、文件名或简单变体。
- 金标、容差和任务 manifest 在运行前冻结并记录 SHA-256。
- 提交前扫描隐藏 DOI、文件名、测试 ID、canary 和答案片段是否进入仓库。
- 不在提交前反馈隐藏任务的逐字段错误；只反馈公共 fixture 或聚合指标。
- 匿名化 Skill/baseline 输出并随机 A/B 顺序，避免 LLM 评委品牌偏置。
- 论文中的提示注入文本视为不可信来源内容，不得改变执行或评分规则。

## 8. 可复算命令

在仓库根执行单元测试：

```text
python -X utf8 -m unittest discover -s skills/biofig-trace/tests -p "test_evaluation.py" -v
```

直接复算内置 scorer unit fixture：

```text
python -X utf8 skills/biofig-trace/tests/evaluate_uplift.py --gold skills/biofig-trace/tests/fixtures/scoring_gold.json --skill-runs skills/biofig-trace/tests/fixtures/scoring_skill_runs.json --baseline-runs skills/biofig-trace/tests/fixtures/scoring_baseline_runs.json
```

正式评测时必须用独立的真实运行文档替换上述三个 fixture 路径。不得重命名或包装内置合成 fixture 后将其宣称为模型运行。
