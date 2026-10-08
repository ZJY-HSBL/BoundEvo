<div align="center">

# BoundEvo

**Adaptive Boundary Evolutionary Optimization｜自适应边界演化优化**

面向实数编码多父体重组的轻量级、可复现实验型 Python 演化优化库。

[![CI](https://github.com/ZJY-HSBL/BoundEvo/actions/workflows/ci.yml/badge.svg)](https://github.com/ZJY-HSBL/BoundEvo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Release](https://img.shields.io/badge/release-v0.3.0-2F6FEB)
![License](https://img.shields.io/badge/license-MIT-3DA639)

[English](README.md) · [算法说明](docs/algorithm.md) · [实验复现](docs/reproduction.md) · [研究工作流](docs/research_workflow.md) · [v0.3.0 说明](docs/releases/v0.3.0.md)

</div>

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

[v0.3.0](https://github.com/ZJY-HSBL/BoundEvo/releases/tag/v0.3.0) 已正式发布。当前 main 分支进入 0.4 开发阶段，具体变更见 [CHANGELOG.md](CHANGELOG.md)。

## License

MIT License。
