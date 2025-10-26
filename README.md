# focast-251026

## Weekly store-product forecasting

This repository contains a Python utility (`store_product_weekly_forecast.py`) that
ingests the historical 门店级别 sales data described in the prompt and produces
weekly forecasts for each (store, product) series.

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

The console output starts with a JSON summary of the dataset (e.g., number of
stores, date range, quantity statistics). The forecast table contains one row
per future week with the 门店卡号、货品代码、预测值、所选模型以及评估指标。
