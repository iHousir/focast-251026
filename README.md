# focast-251026

## Weekly store-product forecasting / 周度门店-产品销量预测

This repository provides a Python command line utility (`store_product_weekly_forecast.py`)
for analysing historical store-level product sales and producing weekly demand forecasts
with automatic model selection.

本项目包含一个 Python 命令行工具（`store_product_weekly_forecast.py`），用于分析门店级别的历史销量数据，自动挑选预测模型，并生成周度销量预测结果。

### Contents / 目录

1. [Environment Requirements / 环境要求](#environment-requirements--环境要求)
2. [Installation / 安装依赖](#installation--安装依赖)
3. [Data Preparation / 准备数据](#data-preparation--准备数据)
4. [Running Example / 运行示例](#running-example--运行示例)
5. [Usage Guide / 使用指南](#usage-guide--使用指南)
6. [Project Structure / 项目结构](#project-structure--项目结构)
7. [Configuration / 配置说明](#configuration--配置说明)
8. [Model Parameters / 模型参数](#model-parameters--模型参数)
9. [FAQ / 常见问题](#faq--常见问题)

---

### Environment Requirements / 环境要求

* **Python**: 3.9 or later is recommended to ensure compatibility with `pandas`、`statsmodels` 等科学计算库。
* **Operating system**: Windows, macOS 或 Linux 均可，建议在 64 位环境中运行以获得更好性能。
* **Memory**: 至少 4 GB 可用内存以处理较大的历史数据集。
* **Locale/Encoding**: 输入文件需使用 UTF-8（或可由 `pandas.read_csv` 自动解析的编码）以避免中文字段乱码。

### Installation / 安装依赖

1. 可选：创建并激活虚拟环境。

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 用户运行 .venv\Scripts\activate
   ```

2. 安装所需依赖库：

   ```bash
   pip install --upgrade pip
   pip install pandas numpy statsmodels
   ```

3. （可选）若需导出 Excel 报告，可额外安装 `openpyxl` 等库。

### Data Preparation / 准备数据

The script expects a CSV file with the following columns (column names can be in Chinese as listed):

脚本默认从 CSV 文件读取数据，需包含下列字段（支持使用中文原始表头）：

| English alias | 中文字段 | 必填 | 说明 |
| ------------- | -------- | ---- | ---- |
| `store_id`    | 送货专卖店卡号 | ✅ | 门店唯一标识 |
| `product_id`  | 货品代码 | ✅ | 产品唯一标识 |
| `quantity`    | 数量 | ✅ | 每日销量，可为负值 |
| `order_time`  | 下单时间 | ✅ | 下单日期或时间戳 |
| `product_name`| 货品名称 | ⭕ | 仅用于报告展示 |
| `province` / `city` | 省 / 市 | ⭕ | 可用于后续分组分析 |

数据准备建议 / Tips:

* 确保日期字段能被 `pandas.to_datetime` 正确解析（例如 `YYYY-MM-DD HH:MM:SS`）。
* 可存在缺失值，脚本会在建模前自动丢弃关键字段为空的记录。
* 建议对同一天的同一门店-产品记录进行汇总，以减少重复记录对预测的影响。

### Running Example / 运行示例

Assuming your historical data is stored at `data/sales_history.csv`, run:

假设历史数据位于 `data/sales_history.csv`，可以执行：

```bash
python store_product_weekly_forecast.py \
  --input data/sales_history.csv \
  --horizon 8 \
  --output output/weekly_forecasts.csv
```

终端输出包含两部分：

1. **Dataset summary / 数据集摘要**：JSON 结构显示行数、门店数量、时间范围及销量描述统计。
2. **Forecast table / 预测表**：每个门店-产品组合、每个预测周一行，包括预测值、入选模型名称以及 RMSE/MAE/MAPE/sMAPE 等指标。

若提供 `--output` 参数，预测表将写入指定 CSV 文件；否则结果打印到控制台。

### Usage Guide / 使用指南

1. **Prepare environment / 准备环境**：按“安装依赖”步骤配置 Python 虚拟环境。
2. **Inspect data / 检查数据**：确保 CSV 字段完整、无严重缺失；必要时使用 Excel 或 SQL 预处理。
3. **Run analysis / 执行预测**：通过命令行运行脚本，可根据需求调整预测周数、最小观测数等参数。
4. **Review output / 审阅结果**：查看摘要和预测表，确认所选模型是否符合业务预期。
5. **Iterate / 迭代优化**：如需限制模型或增加自定义逻辑，可编辑 `store_product_weekly_forecast.py` 中的模型列表或数据清洗流程。

### Project Structure / 项目结构

```
focast-251026/
├── README.md                       # 项目说明（当前文件）
└── store_product_weekly_forecast.py# 主脚本：数据处理与预测逻辑
```

### Configuration / 配置说明

所有配置通过命令行参数完成：

| 参数 | 默认值 | 说明 |
| ---- | ------ | ---- |
| `--input` | _必须指定_ | 输入 CSV 文件路径。 |
| `--output` | 无 | 结果输出 CSV 路径，未指定则打印到终端。 |
| `--horizon` | `4` | 预测未来的周数。 |
| `--min-observations` | `8` | 至少需要的周度观测数（不足则跳过该系列）。 |

高级配置建议：

* **自定义聚合周期**：可在 `weekly_series` 函数中修改 `resample("W-MON")` 为其他周起始日或月度聚合。
* **扩展评估指标**：在 `_compute_metrics` 中新增或修改指标计算逻辑。
* **调整候选模型**：在 `select_best_model` 中添加或移除模型（例如 Prophet、XGBoost 等），并在回测比较时更新逻辑。

### Model Parameters / 模型参数

The script currently evaluates the following baseline models. Users can tune the embedded parameters by editing the relevant helper functions.

当前版本默认评估以下模型，具体参数可在脚本对应函数中调整：

| 模型 | 函数位置 | 关键参数 | 说明 |
| ---- | -------- | -------- | ---- |
| 朴素法 (Naïve) | `_naive_forecast` | 最近一周销量 | 使用最新观测值做平行预测，适合稳定序列。 |
| Holt-Winters (加性) | `_exponential_smoothing_forecast` | `seasonal_periods` 自动取值、`trend="add"` | 当历史数据具有趋势或季节性时效果较好。 |
| SARIMAX | `_sarimax_forecast` | `order` in `[(0,1,1),(1,1,1)]` | 采用两组常见阶数组合，可扩展到更复杂的季节差分或外生变量。 |

Backtesting selects the model with the lowest sMAPE on the most recent horizon and retrains it on the full history to produce the final forecast.

回测阶段会选取 sMAPE 最低的模型，并使用全部历史数据重新训练后输出最终预测。

### FAQ / 常见问题

**Q1: 数据集中存在缺失字段怎么办？**  
A: 若缺少必填列（如 送货专卖店卡号），脚本会报错提示；需在数据源中补齐或映射为脚本识别的列名。

**Q2: 数量为负数是否会影响模型？**  
A: 支持负值，模型会直接使用；若负值代表退货，可考虑在导入前做业务层面的净化处理。

**Q3: 数据量太少导致无法预测？**  
A: 当周度观测少于 `--min-observations` 时会跳过该系列，可降低参数值或补充更多历史数据。

**Q4: 如何更换评估指标或阈值？**  
A: 修改 `_compute_metrics` 函数即可自定义 RMSE/MAE 之外的指标，并在 `select_best_model` 中变更排序逻辑。

**Q5: 是否支持批量运行多个配置？**  
A: 可在 shell 脚本或调度系统中循环调用命令行，并根据不同 CSV/参数组合生成多个预测结果。

