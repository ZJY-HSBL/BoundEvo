# BoundEvo

**Adaptive Boundary Evolutionary Optimization｜自适应边界演化优化算法**

BoundEvo 是一个面向实数编码、多父体重组的轻量级 Python 演化优化库。核心实现是自适应边界约束系数生成器，并同时提供随机穷举法（RE）与经验概率分布法（EDBF）用于对照实验。

## 核心问题

多父体重组系数向量需要满足：

```text
sum(alpha) = 1
-0.5 <= alpha_i <= 1.5
```

传统随机生成在父代数量增大时会产生大量无效系数向量。BoundEvo 根据当前已生成系数之和 `s` 动态调整下一个系数的采样区间：

```text
lower = max(-0.5 - s, -0.5)
upper = min( 1.5 - s,  1.5)
alpha_i ~ Uniform(lower, upper)
```

先生成前 `M-1` 个系数，再令：

```text
alpha_M = 1 - s
```

因为每一步都保证累计和位于 `[-0.5, 1.5]`，所以最后一个系数天然满足边界约束，不需要拒绝采样。ABC 生成器因此始终一次生成成功。

## 安装

```bash
git clone https://github.com/ZJY-HSBL/BoundEvo.git
cd BoundEvo
pip install -e .
```

开发与测试：

```bash
pip install -e ".[dev]"
pytest
```

## 快速使用

```python
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
```

默认的 `N=100, M=15, K=5, L=1` 与原始实验中的主要参数设置一致。

## 算法结构

每轮迭代先依据“约束违反量优先、目标函数其次”的规则排序种群，然后保留前 `K` 个精英父代，再从其余个体中随机选取 `M-K` 个父代。通过满足约束的系数向量对 `M` 个父代进行线性重组，生成 `L` 个子代，选出其中最优者，与当前最差个体比较并决定是否替换。

对于越过变量上下界的子代，本实现采用投影修复，即直接裁剪回定义域。这是为了让多父体仿射重组能够稳定用于有界优化问题而加入的明确实现策略。

## 三种系数生成方法

```python
import numpy as np
from boundevo import generate_coefficients

rng = np.random.default_rng(42)
for method in ("re", "edbf", "abc"):
    result = generate_coefficients(15, method=method, rng=rng)
    print(method, result.attempts, result.coefficients)
```

其中：

- `re`：随机穷举/拒绝采样；
- `edbf`：经验概率分布生成；
- `abc`：自适应边界约束生成，也是 BoundEvo 默认方法。

运行生成效率对比：

```bash
python scripts/benchmark_generators.py --min-m 2 --max-m 20 --repeats 10000
```

## 关于流程图中的索引

源材料中的 ABC 流程图在循环判断处印为 `i == M-1`，紧接着却直接生成 `alpha_M = 1-s`。如果完全按字面执行，会少定义一个系数，与前文定义的 M 维系数向量矛盾。因此本仓库没有静默照抄该处，而采用数学上自洽的实现：随机生成前 `M-1` 个系数，再由和约束确定第 `M` 个系数。详细说明见 [`docs/algorithm.md`](docs/algorithm.md)。

## 测试

当前测试覆盖：

- ABC 在不同父代规模下始终一次生成合格系数向量；
- 系数和为 1 且每一项位于 `[-0.5, 1.5]`；
- RE / EDBF 生成合法性；
- 约束优先比较逻辑；
- Sphere 连续优化；
- 简单不等式约束优化。

```bash
pytest
```

## CEC2017 实验复现

v0.2 已加入完整的 CEC2017 实验层。默认实验集合为 29 个问题，即 `F1` 与 `F3-F30`。主实验配置封装为 `N=100, M=15, K=5, L=1`，而测试维度作为显式参数保留，避免把源材料未明确给出的维度静默写死。

安装 CEC2017 可选依赖：

```bash
pip install -e ".[cec2017]"
```

建议先运行小规模验证：

```bash
python scripts/run_cec2017.py --functions 1,10,20,30 --methods abc --dimension 10 --evaluations 5000
```

再运行完整 29 函数对比：

```bash
python scripts/run_cec2017.py --dimension 10 --repeats 30
```

程序会自动生成 `results/cec2017_trials.csv` 与 `results/cec2017_summary.csv`，分别保存逐次运行结果和按函数/方法汇总的统计结果。需要绘图时安装 `pip install -e ".[plot]"`，然后运行 `python scripts/plot_cec2017.py`。

实验设置来源与实现选择的边界说明见 [`docs/reproduction.md`](docs/reproduction.md)。

## License

MIT License。
