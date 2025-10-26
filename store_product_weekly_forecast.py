"""Utilities for analysing store-level sales data and producing weekly forecasts.

This module loads the historical transactional data provided by the user, prepares
weekly demand series for each (store, product) combination, evaluates multiple
forecasting models, and returns the best forecast per series together with model
diagnostics.

The expected input schema is based on the description from the user:

* ``月份`` (optional) – month string, not used directly in the modelling.
* ``送货地址`` – delivery address, not used directly.
* ``送货专卖店卡号`` – unique identifier of the store.
* ``货品代码`` – unique identifier of the product.
* ``数量`` – numeric quantity sold (can be negative).
* ``货品名称`` – product name (optional).
* ``下单时间`` – order timestamp.
* ``配送方式`` – delivery channel (optional).
* ``省`` and ``市`` – location fields (optional).

The script can be executed as a command line tool:

```
python store_product_weekly_forecast.py --input sales.csv --horizon 4 --output forecasts.csv
```

The resulting CSV contains one row per future week per (store, product) series
with the chosen forecasting method, the point forecast and the backtest metrics.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas import Series
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX


# ---------------------------------------------------------------------------
# Data preparation helpers
# ---------------------------------------------------------------------------


REQUIRED_COLUMNS = {
    "store_id": "送货专卖店卡号",
    "product_id": "货品代码",
    "quantity": "数量",
    "order_time": "下单时间",
}


def load_sales_data(path: Path) -> pd.DataFrame:
    """Load the raw sales data and normalise column names.

    Parameters
    ----------
    path:
        Path to the input CSV file.

    Returns
    -------
    pandas.DataFrame
        Cleaned dataframe with English column names and parsed datetimes.
    """

    df = pd.read_csv(path)
    column_map = {v: k for k, v in REQUIRED_COLUMNS.items() if v in df.columns}

    missing = [v for v in REQUIRED_COLUMNS.values() if v not in df.columns]
    if missing:
        raise ValueError(
            "Input file is missing required columns: " + ", ".join(missing)
        )

    df = df.rename(columns=column_map)
    df["order_time"] = pd.to_datetime(df["order_time"], errors="coerce")
    df = df.dropna(subset=["store_id", "product_id", "order_time", "quantity"])
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df = df.dropna(subset=["quantity"])
    return df


def summarize_dataset(df: pd.DataFrame) -> Dict[str, object]:
    """Compute descriptive statistics of the dataset used for reporting."""

    summary = {
        "num_rows": int(len(df)),
        "num_stores": int(df["store_id"].nunique()),
        "num_products": int(df["product_id"].nunique()),
        "date_range": (
            df["order_time"].min().strftime("%Y-%m-%d")
            if not df["order_time"].empty
            else None,
            df["order_time"].max().strftime("%Y-%m-%d")
            if not df["order_time"].empty
            else None,
        ),
        "quantity_stats": df["quantity"].describe().to_dict(),
    }
    summary["quantity_stats"] = {
        k: (float(v) if pd.notna(v) else None) for k, v in summary["quantity_stats"].items()
    }
    return summary


def weekly_series(df: pd.DataFrame) -> Iterable[Tuple[Tuple[str, str], Series]]:
    """Yield weekly aggregated sales series for each store/product pair."""

    df = df.set_index("order_time").sort_index()
    grouped = df.groupby(["store_id", "product_id"])

    for (store, product), sub_df in grouped:
        weekly = (
            sub_df["quantity"].resample("W-MON", label="left", closed="left").sum().dropna()
        )
        if len(weekly) >= 4:  # Require at least 4 observations to forecast.
            yield (store, product), weekly


# ---------------------------------------------------------------------------
# Forecasting models
# ---------------------------------------------------------------------------


@dataclass
class ForecastResult:
    store_id: str
    product_id: str
    model_name: str
    forecast: pd.Series
    metrics: Dict[str, float]


def _naive_forecast(train: Series, horizon: int) -> pd.Series:
    last_value = train.iloc[-1]
    index = pd.date_range(start=train.index[-1] + pd.offsets.Week(1), periods=horizon, freq="W-MON")
    return pd.Series(last_value, index=index, name="naive")


def _exponential_smoothing_forecast(train: Series, horizon: int) -> pd.Series:
    seasonal_periods = max(2, min(52, len(train) // 2))
    model = ExponentialSmoothing(
        train,
        seasonal_periods=seasonal_periods,
        seasonal="add",
        trend="add",
        initialization_method="estimated",
    ).fit(optimized=True, use_brute=True)
    forecast = model.forecast(horizon)
    return forecast.rename("holt_winters")


def _sarimax_forecast(train: Series, horizon: int, order: Tuple[int, int, int]) -> pd.Series:
    model = SARIMAX(train, order=order, enforce_stationarity=False, enforce_invertibility=False)
    fitted = model.fit(disp=False)
    forecast = fitted.forecast(steps=horizon)
    return forecast.rename(f"sarimax_{order[0]}{order[1]}{order[2]}")


def _compute_metrics(actual: Series, predicted: Series) -> Dict[str, float]:
    residual = actual - predicted
    rmse = float(np.sqrt(np.nanmean(np.square(residual))))
    mae = float(np.nanmean(np.abs(residual)))

    actual_safe = actual.replace(0, np.nan)
    mape = float(np.nanmean(np.abs(residual / actual_safe)))

    denominator = (np.abs(actual) + np.abs(predicted)).replace(0, np.nan)
    smape = float(np.nanmean(2 * np.abs(predicted - actual) / denominator))

    metrics = {"rmse": rmse, "mae": mae, "mape": mape, "smape": smape}
    return {k: (v if np.isfinite(v) else float("nan")) for k, v in metrics.items()}


def select_best_model(series: Series, horizon: int) -> ForecastResult:
    """Train a set of candidate models and select the best one via backtesting."""

    if len(series) <= horizon + 1:
        horizon = max(1, len(series) // 3)

    train = series.iloc[:-horizon]
    test = series.iloc[-horizon:]

    candidates: List[Tuple[str, Series]] = []

    candidates.append(("naive", _naive_forecast(train, horizon)))

    try:
        if len(train) >= 10:
            candidates.append(("holt_winters", _exponential_smoothing_forecast(train, horizon)))
    except Exception:
        pass

    for order in [(0, 1, 1), (1, 1, 1)]:
        try:
            if len(train) >= 8:
                candidates.append((f"sarimax_{order[0]}{order[1]}{order[2]}", _sarimax_forecast(train, horizon, order)))
        except Exception:
            continue

    evaluations: List[Tuple[float, str, Series, Dict[str, float]]] = []
    for name, forecast in candidates:
        aligned = forecast.loc[test.index]
        if len(aligned) != len(test):
            continue
        metrics = _compute_metrics(test, aligned)
        smape = metrics.get("smape", float("nan"))
        evaluations.append((smape, name, forecast, metrics))

    if not evaluations:
        # Fall back to naive forecast using the last observed value.
        best_name, best_forecast = "naive", _naive_forecast(series, horizon)
        metrics = {"rmse": float("nan"), "mae": float("nan"), "mape": float("nan"), "smape": float("nan")}
    else:
        _, best_name, _, metrics = min(
            evaluations, key=lambda x: x[0] if np.isfinite(x[0]) else np.inf
        )
        # Retrain the winning model on the full series for the final forecast
        if best_name == "naive":
            best_forecast = _naive_forecast(series, horizon)
        elif best_name == "holt_winters":
            best_forecast = _exponential_smoothing_forecast(series, horizon)
        elif best_name.startswith("sarimax"):
            order = tuple(map(int, best_name.split("_")[1]))
            best_forecast = _sarimax_forecast(series, horizon, order)
        else:
            best_forecast = _naive_forecast(series, horizon)

    return ForecastResult(
        store_id="",
        product_id="",
        model_name=best_name,
        forecast=best_forecast,
        metrics=metrics,
    )


def forecast_series(series: Series, horizon: int) -> ForecastResult:
    """Convenience wrapper to maintain store/product identifiers in the result."""

    result = select_best_model(series, horizon)
    result.store_id = str(series.attrs.get("store_id", ""))
    result.product_id = str(series.attrs.get("product_id", ""))
    return result


def forecast_all(df: pd.DataFrame, horizon: int, min_observations: int = 8) -> Tuple[List[ForecastResult], Dict[str, object]]:
    """Compute forecasts for every (store, product) series.

    Parameters
    ----------
    df:
        Preprocessed dataframe.
    horizon:
        Number of weeks to forecast.
    min_observations:
        Minimum number of weekly observations required to run a forecast.
    """

    summary = summarize_dataset(df)
    results: List[ForecastResult] = []

    for (store, product), series in weekly_series(df):
        if len(series) < min_observations:
            continue
        series.attrs["store_id"] = store
        series.attrs["product_id"] = product
        result = forecast_series(series, horizon)
        results.append(result)

    return results, summary


def results_to_dataframe(results: Iterable[ForecastResult]) -> pd.DataFrame:
    records: List[Dict[str, object]] = []
    for result in results:
        metrics_clean = {
            key: (value if np.isfinite(value) else None)
            for key, value in result.metrics.items()
        }
        for timestamp, value in result.forecast.items():
            records.append(
                {
                    "store_id": result.store_id,
                    "product_id": result.product_id,
                    "forecast_week": timestamp.strftime("%Y-%m-%d"),
                    "forecast_quantity": float(value),
                    "model": result.model_name,
                    "metrics": json.dumps(metrics_clean, ensure_ascii=False),
                }
            )
    return pd.DataFrame.from_records(records)


def run_cli(args: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Store/Product weekly sales forecasting")
    parser.add_argument("--input", type=Path, required=True, help="Path to the CSV file with raw sales data")
    parser.add_argument("--output", type=Path, required=False, help="Optional path to save the forecast CSV")
    parser.add_argument("--horizon", type=int, default=4, help="Number of weeks to forecast")
    parser.add_argument(
        "--min-observations", type=int, default=8, help="Minimum weekly observations required to run a forecast"
    )

    namespace = parser.parse_args(args=args)

    df = load_sales_data(namespace.input)
    results, summary = forecast_all(df, horizon=namespace.horizon, min_observations=namespace.min_observations)

    print("Dataset summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    forecast_df = results_to_dataframe(results)
    if namespace.output:
        forecast_df.to_csv(namespace.output, index=False)
        print(f"Saved forecast results to {namespace.output}")
    else:
        print(forecast_df.to_string(index=False))


if __name__ == "__main__":
    run_cli()

