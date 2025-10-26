# focast-251026

## Weekly store-product forecasting / 周度门店-产品销量预测

This repository contains a Python utility (`store_product_weekly_forecast.py`) that
ingests the historical 门店级别 sales data described in the prompt and produces
weekly forecasts for each (store, product) series.

本项目提供一个 Python 工具脚本（`store_product_weekly_forecast.py`），
用于读取提示中描述的门店级别历史销售数据，并为每个「门店-产品」组合
生成未来若干周的销量预测。

### Features

* Cleans and standardises the raw CSV columns (支持中文字段名)。
* Generates descriptive statistics to help understand the dataset coverage,
  missing values and value distributions.
* Aggregates daily transactions to weekly demand per 门店/货品 pair.
* Evaluates several forecasting models (Naïve, Holt-Winters, SARIMAX) through
  rolling backtests and automatically selects the best performer for each
  series.
* Outputs per-week forecasts alongside the chosen model name and accuracy
  metrics (RMSE/MAE/MAPE/sMAPE).

### Requirements

The script relies on `pandas`, `numpy` and `statsmodels`. Install them via:

```
pip install pandas numpy statsmodels
```

脚本依赖 `pandas`、`numpy`、`statsmodels`，可通过上述命令安装。

### Usage

```
python store_product_weekly_forecast.py \
  --input path/to/sales.csv \
  --horizon 4 \
  --output forecasts.csv
```

Arguments:

* `--input` (required): path to the CSV file containing the raw sales history.
* `--horizon`: number of future weeks to predict (default: 4).
* `--output`: optional path to save the resulting forecast table. When omitted,
  the results are printed to stdout.
* `--min-observations`: minimal number of weekly observations required to run a
  forecast (default: 8).

参数说明：

* `--input`（必填）：原始销售历史 CSV 文件路径。
* `--horizon`：需要预测的未来周数，默认为 4。
* `--output`：可选输出文件路径，若不提供则结果打印到终端。
* `--min-observations`：执行预测所需的最少周度观测数量，默认为 8。

The console output starts with a JSON summary of the dataset (e.g., number of
stores, date range, quantity statistics). The forecast table contains one row
per future week with the 门店卡号、货品代码、预测值、所选模型以及评估指标。

终端首先会输出数据集的 JSON 摘要（如门店数量、时间范围、销量统计等），
随后给出预测表，每周一行，包含门店卡号、货品代码、预测值、所选模型和
评估指标。
