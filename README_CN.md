<div align="center">

# BoundEvo

**Adaptive Boundary Evolutionary Optimization｜自适应边界演化优化**

面向实数编码多父体重组的轻量级、可复现实验型 Python 演化优化库。

[![CI](https://github.com/ZJY-HSBL/BoundEvo/actions/workflows/ci.yml/badge.svg)](https://github.com/ZJY-HSBL/BoundEvo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Release](https://img.shields.io/badge/release-v0.8.0-2F6FEB)
![License](https://img.shields.io/badge/license-MIT-3DA639)

[English](README.md) · [算法说明](docs/algorithm.md) · [实验复现](docs/reproduction.md) · [研究工作流](docs/research_workflow.md) · [实验索引与对比](docs/run_registry.md) · [v0.8.0 说明](docs/releases/v0.8.0.md)

</div>

<!-- BENCHMARK_RESULTS_START -->
## 真实 CEC2017 实验结果（30 维）

**以下均为真实运行数据，而非模拟结果。** D=30，每次 3,000 次函数评价，每种方法 10 个配对初始种子，共 120 次独立优化试验。同一函数及重复编号下，ABC、EDBF、RE 具有相同的初始化种群。

![CEC2017 30D normalized objective error](docs/figures/cec2017-30d-relative-error.svg)

![CEC2017 30D runtime comparison](docs/figures/cec2017-30d-runtime.svg)

**最终平均目标误差（越低越好）**

| 测试函数 | ABC | EDBF | RE |
|:---|---:|---:|---:|
| F1 | **1.747e+11** | 7.536e+11 | 4.038e+11 |
| F3 | **84,611.2** | 294,908.6 | 241,204.0 |
| F10 | 8,157.7 | **8,047.6** | 8,174.2 |
| F30 | **4.884e+06** | 1.262e+09 | 3.776e+08 |

实验来源：[120 次原始记录](docs/experiments/cec2017-reference-30d-2026-10-17/trials.csv) · [均值/标准差](docs/experiments/cec2017-reference-30d-2026-10-17/summary.csv) · [配对检验](docs/experiments/cec2017-reference-30d-2026-10-17/paired_sign_tests.csv) · [环境记录](docs/experiments/cec2017-reference-30d-2026-10-17/environment.json) · [中文分析报告](docs/experiments/cec2017-reference-30d-2026-10-17/statistical_analysis_CN.md)

**解释边界：**ABC 在 F1、F3、F30 的平均误差最低，**F10 则由 EDBF 略优**。这只能说明当前所测函数与预算下的表现，不能推导出对全部函数的普遍优势。独立 Python 后端并非原始官方 C 程序；58/58 项仅为有限采样点的数值预检，且每次 3,000 次评价不等于论文级完整复现。

### 全部 29 个函数：10,000 次评价与收敛曲线

**261 次真实优化试验**，CEC2017 30 维，每方法 3 个配对种子。每函数重复次数仍较少，结果仅用于探索性比较。

![Measured 29-function leaderboard at 10k FEs](docs/figures/cec2017-30d-fullsuite-10k-winners.svg)

![F10 F20 F22 F30 measured convergence histories](docs/figures/cec2017-30d-fullsuite-10k-convergence.svg)

观测平均目标误差最低的函数数目：ABC 27, EDBF 1, RE 1.

**跨函数配对 Wilcoxon 检验**（对各函数平均误差取 log10，两项比较统一 Holm 校正）：

| 对照 | ABC 领先/落后 | 原始 p | Holm 校正 p |
|:---|---:|---:|---:|
| abc_vs_edbf | 28/1 | 7.4506e-09 | 1.4901e-08 |
| abc_vs_re | 28/1 | 1.1176e-08 | 1.4901e-08 |

[261 条原始试验](docs/experiments/cec2017-fullsuite-30d-10k-2026-10-17/trials.csv) · [收敛历史](docs/experiments/cec2017-fullsuite-30d-10k-2026-10-17/history.csv) · [逐函数汇总](docs/experiments/cec2017-fullsuite-30d-10k-2026-10-17/summary.csv) · [统计报告](docs/experiments/cec2017-fullsuite-30d-10k-2026-10-17/report.md) · [环境与源码修订](docs/experiments/cec2017-fullsuite-30d-10k-2026-10-17/environment.json)

**适用范围：**这是全部 29 函数的 10k 次评价探索实验，不是原论文 100k 次评价的完整复现。不同预算、不同基准实现的数据不得混合统计。

### 高评价预算验证：每次 10,000 次函数评价

**120 次真实试验**，D=30，测试 F10、F20、F22、F30，每方法 10 个配对初始种子。重点检验此前 ABC 未领先的函数。

![10k-FE error ratio compared to RE](docs/figures/cec2017-30d-longbudget-relative-error.svg)

![3k vs 10k evaluation-budget progression on F10 and F30](docs/figures/cec2017-30d-budget-progression.svg)

| 函数 | ABC | EDBF | RE |
|:---|---:|---:|---:|
| F10 | **7,470.2** | 7,501.9 | 7,661.9 |
| F20 | **785.2** | 1,129.8 | 1,049.5 |
| F22 | **5,717.6** | 7,651.5 | 7,300.1 |
| F30 | **188,044.0** | 6.193e+07 | 5.511e+06 |

**跨预算验证**（同一参考后端与种子规则，3,000 → 10,000 次评价）：

| 函数 | 方法 | 3k 次评价误差 | 10k 次评价误差 |
|:---|:---|---:|---:|
| F10 | ABC | 8,157.7 | 7,470.2 |
| F10 | EDBF | 8,047.6 | 7,501.9 |
| F10 | RE | 8,174.2 | 7,661.9 |
| F30 | ABC | 4.884e+06 | 188,044.0 |
| F30 | EDBF | 1.262e+09 | 6.193e+07 |
| F30 | RE | 3.776e+08 | 5.511e+06 |

**配对精确符号检验（全部 8 项统一 Holm 校正，仅探索性）：**

| 函数 | 对照 | ABC 胜/负/平 | 原始 p | Holm 校正 p |
|:---|:---|---:|---:|---:|
| F10 | ABC vs EDBF | 4/6/0 | 0.75391 | 1 |
| F10 | ABC vs RE | 5/4/1 | 1 | 1 |
| F20 | ABC vs EDBF | 10/0/0 | 0.0019531 | 0.015625 |
| F20 | ABC vs RE | 10/0/0 | 0.0019531 | 0.015625 |
| F22 | ABC vs EDBF | 7/3/0 | 0.34375 | 1 |
| F22 | ABC vs RE | 7/3/0 | 0.34375 | 1 |
| F30 | ABC vs EDBF | 10/0/0 | 0.0019531 | 0.015625 |
| F30 | ABC vs RE | 10/0/0 | 0.0019531 | 0.015625 |

四个函数共 40 组配对种子中 ABC 的获胜次数（不计平局）：vs EDBF 31/40; vs RE 32/40.

[120 次原始试验](docs/experiments/cec2017-longbudget-30d-2026-10-17/trials.csv) · [均值和方差](docs/experiments/cec2017-longbudget-30d-2026-10-17/summary.csv) · [配对检验](docs/experiments/cec2017-longbudget-30d-2026-10-17/paired_sign_tests.csv) · [环境记录](docs/experiments/cec2017-longbudget-30d-2026-10-17/environment.json) · [中文分析报告](docs/experiments/cec2017-longbudget-30d-2026-10-17/statistical_analysis_CN.md)

**解释边界：**这只是选定四函数的高预算试验，不是完整 29 函数的 10k 次评价复现。不同预算不能合并统计，均值领先不等于显著优势。

### 全部 29 个函数：30 维探索性普查

共 **261 次真实试验**；每种方法 3 个配对种子、每次 1,200 次函数评价。颜色只表示观测均值最低，并不表示统计显著。

![CEC2017 all 29 functions screening winner map](docs/figures/cec2017-30d-29function-screen.svg)

获得最低观测平均误差的函数数量：ABC 27, EDBF 0, RE 2.

[261 条原始记录](docs/experiments/cec2017-screen-30d-2026-10-17/trials.csv) · [逐函数均值](docs/experiments/cec2017-screen-30d-2026-10-17/summary.csv) · [实验环境](docs/experiments/cec2017-screen-30d-2026-10-17/environment.json) · [中文结果分析](docs/experiments/cec2017-screen-30d-2026-10-17/statistical_analysis_CN.md)

**预算限制：**本轮 1,200 次评价的普查结果不得与前述 3,000 次评价的实验合并统计。

<details><summary>更早的 10 维探索性实验（使用另一后端，数据不得混合统计）</summary>

![Earlier 10D pilot](docs/experiments/cec2017-pilot-2026-10-17/error_comparison.png)

[10 维原始数据](docs/experiments/cec2017-pilot-2026-10-17/validation_trials.csv) · [试验说明](docs/experiments/cec2017-pilot-2026-10-17/validation_readme.md)

</details>
<!-- BENCHMARK_RESULTS_END -->

## 项目定位

BoundEvo 解决多父体仿射重组中的一个核心问题：高效生成满足下列条件的系数向量。

    sum(alpha) = 1
    -0.5 <= alpha_i <= 1.5

自适应边界方法根据当前累计和动态计算下一个系数的可行区间。先生成前 M-1 个系数，再通过总和约束确定最后一个系数，因此 ABC 方法不需要拒绝采样。

仓库在同一套演化优化框架中保留三类系数生成方法：

| 方法 | 系数生成方式 | 定位 |
|:---|:---|:---|
| RE | 随机穷举 / 拒绝采样 | EP-GTA 风格基线 |
| EDBF | 经验概率分布采样 | 改进基线 |
| ABC | 自适应边界约束 | BoundEvo 默认方法 |

## 当前能力

| 层级 | 已实现内容 |
|:---|:---|
| 算法核心 | 精英保留、多父体仿射重组、有界域修复 |
| 系数生成 | RE、EDBF、ABC |
| Benchmark | Sphere、Rosenbrock、Rastrigin、Ackley、CEC2017 |
| 主实验 | CEC2017 共 29 个函数：F1 与 F3-F30 |
| M 消融 | F1、F10、F20、F30 上 M=10..16 |
| 效率实验 | M=1..20 系数向量生成效率 |
| 统计分析 | 平均排名、Win/Tie/Loss、Wilcoxon + Holm、Friedman |
| 可复现性 | 自动记录完整配置、运行环境和源码版本的 JSON Manifest |
| 输出 | CSV、Markdown、PNG、自包含 HTML 实验报告 |
| 跨实验比较 | Run Registry、测试项对齐、三目标 Pareto 前沿 |
| 验证 | Python 3.10/3.11/3.12 CI 与真实 CEC2017 smoke test |

## 安装

仅使用核心算法：

~~~bash
git clone https://github.com/ZJY-HSBL/BoundEvo.git
cd BoundEvo
pip install -e .
~~~

完整实验环境：

~~~bash
pip install -e ".[cec2017,analysis,plot]"
~~~

开发与测试：

~~~bash
pip install -e ".[dev]"
ruff check .
pytest
~~~

## 统一命令行

当前命令行已经覆盖“实验 → 统计 → 报告”的完整流程：

~~~bash
boundevo --version
boundevo benchmark --config configs/cec2017.json
boundevo sweep --config configs/parent_sweep.json
boundevo efficiency --config configs/efficiency.json
boundevo analyze --config configs/analysis.json
boundevo report --config configs/report.json
boundevo pipeline --config configs/pipeline.json
boundevo runs --root results/runs
boundevo compare --root results/runs
~~~

<code>configs/</code> 中的 JSON 文件用于固定实验参数，避免每次手工输入导致配置漂移。常用参数仍可以直接通过命令行覆盖。

需要一次性执行完整研究流程时，可以直接运行 <code>boundevo pipeline</code>。程序会生成唯一 Run ID，并将该次实验的主实验、M 消融、系数效率、统计检验、Manifest 和最终 HTML 报告统一保存到一个不可覆盖的目录：

    results/runs/<run-id>/
    ├── benchmark/
    ├── sweep/
    ├── efficiency/
    ├── analysis/
    ├── report/
    └── manifest.json

## 历史实验检索与比较

`boundevo runs` 可查看已完成、未完成及文件异常的实验目录；`boundevo compare` 只按相同的 `(测试函数、维度、算法)` 条目对齐计算，分别选出目标误差、运行时间、评价次数三个指标的领先实验，并给出非支配 Pareto 前沿。如果测试项不一致，默认拒绝比较，只有显式指定 `--allow-partial` 才按交集分析。

```bash
boundevo compare --root results/runs \\
  --run-id experiment-001 \\
  --run-id experiment-002 \\
  --output results/comparison.md
```

**Pareto 非支配不等于综合最优**。不同硬件、计算预算、代码版本及重复次数均可能影响比较结果，具体规则见[实验索引与对比文档](docs/run_registry.md)。

## Python 快速使用

~~~python
from boundevo import BoundEvo, BoundEvoConfig
from boundevo.benchmarks import make_box_problem

problem = make_box_problem("rastrigin", dimension=10)

optimizer = BoundEvo(
    BoundEvoConfig(
        population_size=100,
        parent_count=15,
        elite_parent_count=5,
        offspring_count=1,
        max_evaluations=50_000,
        seed=42,
    )
)

result = optimizer.minimize(problem)
print(result.objective)
print(result.x)
~~~

## 独立 CEC2017 基准后端（开发中）

目前新增了一个独立可选的 CEC2017 实现，它由原始 C 代码改写为 NumPy，固定使用上游提交 `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f`，保留官方函数编号。

~~~bash
pip install "git+https://github.com/tilleyd/cec2017-py.git@424a9fa2757914c3e4cfdd8f59a268b1aeb3197f"
boundevo benchmark --backend reference --dimension 30 --repeats 10
~~~

独立验证流程在 10 维和 30 维检查全部 29 个官方函数编号，再在 F1、F3、F10、F30 上进行 120 组 30 维对照试验。不同后端的数值不会混入同一统计结果。详见[独立基准验证说明](docs/reference_backend.md)。

## 真实数值验证（2026 年 10 月）

已在 GitHub Actions 上完成一轮 60 组真实试验：CEC2017 F1、F3、F5、F20，10 维，每组最多 1500 次函数评价；ABC、EDBF、RE 各重复 5 次，相同函数及重复编号使用相同初始种子。

[完整实验记录与结论](docs/experiments/cec2017-pilot-2026-10-17/validation_readme.md) · [原始 CSV](docs/experiments/cec2017-pilot-2026-10-17/validation_trials.csv) · [汇总 CSV](docs/experiments/cec2017-pilot-2026-10-17/validation_summary.csv)

**基准实现完整性警告：**实测 opfunu 1.0.1 的 F10 曾出现低于声明最优值的目标值，F30 在一个测试点出现非有限输出。本轮不采用这两个函数，当前也不能宣称已经完成全部 29 个函数的正式数值复现。相关问题见 [Issue #3](https://github.com/ZJY-HSBL/BoundEvo/issues/3)。

## 实验复现矩阵

主实验按以下参数封装：

    N = 100
    M = 15
    K = 5
    L = 1

M 消融固定 N=100、K=5、L=1，并在 F1、F10、F20、F30 上测试 <code>M=10..16</code>。

当前提取到的实验设置文字没有明确给出 CEC2017 测试维度，因此本仓库没有把维度写成“原实验固定参数”。配置文件默认使用 10 维，只作为可直接运行的默认值，维度始终可以显式修改。

## 统计分析

生成 <code>results/cec2017_summary.csv</code> 后运行：

~~~bash
boundevo analyze --config configs/analysis.json
~~~

自动得到平均排名、Win/Tie/Loss、双侧配对 Wilcoxon 符号秩检验、Holm 多重比较校正以及 Friedman 总体检验。默认使用 <code>mean_error</code>，并按“越小越好”处理。

## 可复现实验清单与 HTML 报告

现在每个主要 CLI 阶段都会自动写出 JSON Manifest，记录最终生效的参数、BoundEvo 版本、Python 版本、运行平台、NumPy/SciPy/opfunu/Matplotlib 版本、可获取的源码提交 SHA 以及输出文件位置。

完成实验与统计后运行：

~~~bash
boundevo report --config configs/report.json
~~~

会生成 <code>results/report.html</code>。这是一个单文件、自包含的实验报告，直接用浏览器即可查看，不依赖 Python 环境。当前报告已经能够直接绘制采样后的收敛曲线、M 参数敏感性曲线以及系数生成效率曲线，图形以内联 SVG 写入 HTML，不需要 JavaScript 或额外绘图库才能查看。

长时间实验通过 <code>history_interval</code> 控制历史采样，默认每 100 代记录一次，同时始终保留最终状态，避免把每一代都写入 CSV 导致结果文件过大。完整研究流程见 [docs/research_workflow.md](docs/research_workflow.md)。

## 实现边界

源材料的 ABC 流程图在最后一个系数的下标处存在歧义。若完全按字面执行，会出现一个系数未定义。BoundEvo 采用与 M 维系数向量及总和约束一致的解释：先生成 M-1 个系数，再由总和约束计算第 M 个系数。

多父体仿射重组产生越界子代时，本仓库采用投影裁剪回变量定义域。这属于明确记录的工程实现选择，不将其静默描述为源方法本身。

## 仓库结构

    boundevo/       优化器、系数生成、CEC2017、统计、Manifest、报告、CLI
    configs/        可复现实验 JSON 配置
    docs/           算法、复现、工作流与 Release 文档
    examples/       Python 使用示例
    scripts/        绘图和独立实验工具
    tests/          单元测试与集成测试
    .github/        CI 与 Release 工作流

## Release

[v0.8.0](https://github.com/ZJY-HSBL/BoundEvo/releases/tag/v0.8.0) 为当前正式版本。完整版本记录见 [CHANGELOG.md](CHANGELOG.md)。

## License

MIT License。
