"""Fill-level forecasting (proposal §3.3.3.3).
Fits a linear trend on a bin's recent fill_pct history and estimates hours
until it reaches the collection threshold. Falls back gracefully on sparse data.
"""
import pandas as pd
from sklearn.linear_model import LinearRegression

THRESHOLD = 80.0  # % full -> schedule collection


def hours_until_full(history):
    """history: list of (timestamp, fill_pct) tuples, oldest first.
    Returns estimated hours until THRESHOLD, or None if not computable."""
    if len(history) < 3:
        return None
    df = pd.DataFrame(history, columns=["ts", "fill"])
    df["ts"] = pd.to_datetime(df["ts"])
    df["hours"] = (df["ts"] - df["ts"].iloc[0]).dt.total_seconds() / 3600.0
    X, y = df[["hours"]], df["fill"]
    model = LinearRegression().fit(X, y)
    rate = model.coef_[0]  # % per hour
    if rate <= 0:
        return None  # not filling
    last_h, last_fill = df["hours"].iloc[-1], df["fill"].iloc[-1]
    if last_fill >= THRESHOLD:
        return 0.0
    return float((THRESHOLD - last_fill) / rate)


if __name__ == "__main__":
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    hist = [(now - datetime.timedelta(hours=h), 20 + 2 * (10 - h))
            for h in range(10, 0, -1)]
    print("hours until full:", hours_until_full(hist))
