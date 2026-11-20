"""
ingest_data.py
Run once to load CSVs into MongoDB collections.
  python ingest_data.py
"""
import sys
import os
import math
import pandas as pd
import pymongo

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI   = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB    = os.environ.get("MONGO_DB",  "weather_nexus")

WEATHER_CSV = os.path.join(os.path.dirname(__file__), "..", "IndianWeatherRepository.csv")
AQI_CSV     = os.path.join(os.path.dirname(__file__), "..", "city_day.csv")

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean(record: dict) -> dict:
    """Replace NaN / inf with None so pymongo accepts the document."""
    out = {}
    for k, v in record.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = None
        else:
            out[k] = v
    return out


def ingest_weather(db):
    print("📥  Loading IndianWeatherRepository.csv …")
    df = pd.read_csv(WEATHER_CSV)
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")
    df = df.dropna(subset=["temperature_celsius"])
    df = df.rename(columns={
        "air_quality_PM2.5":              "pm2_5",
        "air_quality_PM10":               "pm10",
        "air_quality_Nitrogen_dioxide":   "no2",
        "air_quality_Sulphur_dioxide":    "so2",
        "air_quality_Carbon_Monoxide":    "co",
        "air_quality_Ozone":              "o3",
        "air_quality_us-epa-index":       "aqi_us",
    })
    # Convert datetime to string for mongo
    df["last_updated"] = df["last_updated"].astype(str)

    col = db["weather_snapshot"]
    col.drop()
    records = [clean(r) for r in df.to_dict("records")]
    col.insert_many(records)
    col.create_index("location_name")
    col.create_index("region")
    print(f"   ✅  {len(records):,} weather records inserted.")


def ingest_aqi(db):
    print("📥  Loading city_day.csv …")
    df = pd.read_csv(AQI_CSV)
    print(f"   📊  Columns in AQI CSV: {df.columns.tolist()}")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["AQI"])
    df["Year"]  = df["Date"].dt.year.astype(int)
    df["Month"] = df["Date"].dt.month.astype(int)
    df["Date"]  = df["Date"].astype(str)

    # Normalize column names for MongoDB (avoid dots)
    df = df.rename(columns={"PM2.5": "PM2_5"})

    col = db["aqi_history"]
    col.drop()
    records = [clean(r) for r in df.to_dict("records")]
    col.insert_many(records)
    col.create_index("City")
    col.create_index([("City", 1), ("Year", 1)])
    print(f"   ✅  {len(records):,} AQI history records inserted.")


def main():
    print(f"\n🔗  Connecting to MongoDB at {MONGO_URI} …")
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Ping to verify connection before doing heavy lifting
    try:
        client.admin.command("ping")
        print("   ✅  Connected successfully.\n")
    except Exception as e:
        print(f"   ❌  Cannot connect to MongoDB: {e}")
        sys.exit(1)

    db = client[MONGO_DB]
    ingest_weather(db)
    ingest_aqi(db)

    print("\n🏁  Ingestion complete.")
    print(f"   DB  : {MONGO_DB}")
    print(f"   Collections: {db.list_collection_names()}")
    client.close()


if __name__ == "__main__":
    main()
