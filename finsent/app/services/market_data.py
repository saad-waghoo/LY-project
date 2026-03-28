from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


class MarketDataService:
    def fetch_intraday_prices(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        interval: str = "15m",
    ) -> pd.DataFrame:
        padded_start = start - timedelta(days=2)
        padded_end = end + timedelta(days=2)

        frame = yf.download(
            tickers=ticker.upper(),
            start=padded_start,
            end=padded_end,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if frame.empty:
            return frame

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)

        frame.index = pd.to_datetime(frame.index).tz_localize(None)
        return frame[["Open", "High", "Low", "Close", "Volume"]].dropna()
