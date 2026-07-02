"""
FlowSync Data Loader
Reads all CSV files from the RTA Traffic Dataset and provides
a unified interface for simulation frames.
"""

import os
import pandas as pd
from typing import Optional

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "rta_traffic_dataset", "datasets")


class RTADataloader:
    """Loads and caches all RTA dataset CSVs."""

    def __init__(self, dataset_dir: str = DATASET_DIR):
        self.dataset_dir = dataset_dir
        self._cache: dict[str, pd.DataFrame] = {}

    def _load(self, filename: str, parse_dates: Optional[list] = None) -> pd.DataFrame:
        if filename not in self._cache:
            path = os.path.join(self.dataset_dir, filename)
            self._cache[filename] = pd.read_csv(path, parse_dates=parse_dates)
        return self._cache[filename]

    @property
    def traffic_volume(self) -> pd.DataFrame:
        """All 3 years of traffic volume data concatenated."""
        frames = []
        for year in (2023, 2024, 2025):
            df = self._load(f"traffic_volume_hourly_{year}.csv", parse_dates=["datetime"])
            frames.append(df)
        return pd.concat(frames, ignore_index=True)

    @property
    def signal_performance(self) -> pd.DataFrame:
        frames = []
        for year in (2023, 2024, 2025):
            df = self._load(f"signal_performance_hourly_{year}.csv", parse_dates=["datetime"])
            frames.append(df)
        return pd.concat(frames, ignore_index=True)

    @property
    def locations(self) -> pd.DataFrame:
        return self._load("locations_reference.csv")

    @property
    def junctions(self) -> pd.DataFrame:
        return self._load("signal_junctions_reference.csv")

    @property
    def signal_plans(self) -> pd.DataFrame:
        return self._load("signal_timing_plans.csv")

    @property
    def incidents(self) -> pd.DataFrame:
        return self._load("incidents_log.csv", parse_dates=["datetime_reported", "datetime_cleared"])

    @property
    def weather(self) -> pd.DataFrame:
        frames = []
        for year in (2023, 2024, 2025):
            df = self._load(f"weather_hourly_{year}.csv", parse_dates=["datetime"])
            frames.append(df)
        return pd.concat(frames, ignore_index=True)

    @property
    def calendar(self) -> pd.DataFrame:
        return self._load("calendar_context.csv", parse_dates=["date"])

    @property
    def salik(self) -> pd.DataFrame:
        frames = []
        for year in (2023, 2024, 2025):
            df = self._load(f"salik_toll_hourly_{year}.csv", parse_dates=["datetime"])
            frames.append(df)
        return pd.concat(frames, ignore_index=True)

    @property
    def metro_ridership(self) -> pd.DataFrame:
        return self._load("metro_ridership_daily.csv", parse_dates=["date"])

    def get_traffic_at(self, dt: pd.DataFrame) -> pd.DataFrame:
        """Get traffic volume rows for a specific datetime."""
        return self.traffic_volume[self.traffic_volume["datetime"] == dt]

    def get_signal_at(self, dt: pd.DataFrame) -> pd.DataFrame:
        """Get signal performance rows for a specific datetime."""
        return self.signal_performance[self.signal_performance["datetime"] == dt]

    def get_weather_at(self, dt: pd.DataFrame) -> pd.DataFrame:
        """Get weather row for a specific datetime."""
        return self.weather[self.weather["datetime"] == dt]

    def get_incidents_at(self, dt: pd.DataFrame) -> pd.DataFrame:
        """Get active incidents at a specific datetime."""
        mask = (self.incidents["datetime_reported"] <= dt) & (self.incidents["datetime_cleared"] >= dt)
        return self.incidents[mask]

    def get_unique_datetimes(self) -> list:
        """Return sorted list of unique datetimes across all traffic data."""
        return sorted(self.traffic_volume["datetime"].unique().tolist())

    def get_unique_dates(self) -> list:
        """Return sorted list of unique dates."""
        dates = self.traffic_volume["date"].unique().tolist()
        return sorted(dates)


# Singleton
loader = RTADataloader()
