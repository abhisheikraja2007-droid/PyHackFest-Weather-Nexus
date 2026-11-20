import pandas as pd
import numpy as np
import streamlit as st
import pymongo
import os

# ── MongoDB Connection ────────────────────────────────────────────────────────
def get_db():
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGO_DB", "weather_nexus")
    client = pymongo.MongoClient(uri)
    return client[db_name]

# ── AQI category helpers ──────────────────────────────────────────────────────
AQI_COLORS = {
    "Good":        "#00e400",
    "Satisfactory":"#92d050",
    "Moderate":    "#ffff00",
    "Poor":        "#ff7e00",
    "Very Poor":   "#ff0000",
    "Severe":      "#7e0023",
}

AQI_EMOJI = {
    "Good":        "🟢",
    "Satisfactory":"🟡",
    "Moderate":    "🟠",
    "Poor":        "🔴",
    "Very Poor":   "🟣",
    "Severe":      "⚫",
}

def aqi_category(aqi: float) -> str:
    if pd.isna(aqi):        return "Unknown"
    if aqi <= 50:            return "Good"
    if aqi <= 100:           return "Satisfactory"
    if aqi <= 200:           return "Moderate"
    if aqi <= 300:           return "Poor"
    if aqi <= 400:           return "Very Poor"
    return "Severe"


# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data
def load_weather_data() -> pd.DataFrame:
    """Load and basic-clean from MongoDB weather_snapshot."""
    db = get_db()
    cursor = db["weather_snapshot"].find({}, {"_id": 0})
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return pd.DataFrame()
    
    # Pre-processing (already partly done during ingestion, but safety first)
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")
    df = df.dropna(subset=["temperature_celsius"])
    df["region"] = df["region"].str.strip().str.title()
    df["location_name"] = df["location_name"].str.strip()
    return df


@st.cache_data
def load_aqi_data() -> pd.DataFrame:
    """Load and basic-clean from MongoDB aqi_history."""
    db = get_db()
    cursor = db["aqi_history"].find({}, {"_id": 0})
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return pd.DataFrame()
        
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["AQI"])
    df["AQI_Bucket"] = df["AQI_Bucket"].fillna(df["AQI"].apply(aqi_category))
    df["Year"]  = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    return df


# ── Aggregation helpers ───────────────────────────────────────────────────────
def get_region_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Mean weather params by region (from weather dataset)."""
    return (
        df.groupby("region", as_index=False)
        .agg(
            avg_temp   =("temperature_celsius", "mean"),
            avg_humidity=("humidity", "mean"),
            total_precip=("precip_mm", "sum"),
            avg_pm25   =("pm2_5", "mean"),
            city_count =("location_name", "nunique"),
        )
        .sort_values("avg_temp", ascending=False)
    )


def get_city_aqi_trends(df: pd.DataFrame, city: str) -> pd.DataFrame:
    """Daily AQI time-series for one city."""
    return df[df["City"] == city].sort_values("Date")


def get_top_polluted_cities(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N cities by mean AQI (historical dataset)."""
    return (
        df.groupby("City", as_index=False)["AQI"]
        .mean()
        .sort_values("AQI", ascending=False)
        .head(n)
    )


def get_pollutant_profile(df_aqi: pd.DataFrame, city: str) -> pd.Series:
    """Mean per-pollutant values for the historical dataset."""
    cols = ["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "CO", "SO2", "O3"]
    available = [c for c in cols if c in df_aqi.columns]
    return df_aqi[df_aqi["City"] == city][available].mean()


def get_weather_city(df_weather: pd.DataFrame, city: str) -> pd.Series | None:
    """Get a single city row from the snapshot dataset."""
    rows = df_weather[df_weather["location_name"].str.lower() == city.lower()]
    if len(rows) == 0:
        return None
    return rows.iloc[0]


def get_comparison_data(df_weather: pd.DataFrame, city_name: str) -> pd.DataFrame:
    """Compares a specific city with its regional average."""
    city_row = get_weather_city(df_weather, city_name)
    if city_row is None: return pd.DataFrame()
    
    region = city_row["region"]
    region_avg = df_weather[df_weather["region"] == region].agg({
        "temperature_celsius": "mean",
        "humidity": "mean",
        "pm2_5": "mean"
    })
    
    data = {
        "Metric": ["Temperature", "Humidity", "PM2.5"],
        "City Value": [city_row["temperature_celsius"], city_row["humidity"], city_row["pm2_5"]],
        "Region Avg": [region_avg["temperature_celsius"], region_avg["humidity"], region_avg["pm2_5"]]
    }
    return pd.DataFrame(data)


def condition_icon(condition: str) -> str:
    c = str(condition).lower()
    if "sunny" in c or "clear" in c:              return "☀️"
    if "partly" in c or "partly cloudy" in c:    return "⛅"
    if "cloudy" in c or "overcast" in c:          return "☁️"
    if "rain" in c or "shower" in c:              return "🌧️"
    if "thunder" in c or "storm" in c:            return "⛈️"
    if "mist" in c or "fog" in c or "haze" in c: return "🌫️"
    if "snow" in c or "sleet" in c:               return "❄️"
    return "🌡️"
