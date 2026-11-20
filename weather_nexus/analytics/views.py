"""
analytics/views.py
Django views & JSON API endpoints backed by MongoDB aggregation pipelines.
"""
import json
from django.shortcuts import render
from django.http import JsonResponse
from .db import get_db


# ── helper ────────────────────────────────────────────────────────────────────
def _round(val, n=2):
    try:
        return round(float(val), n)
    except (TypeError, ValueError):
        return None


# ══════════════════════════════════════════════════════════════════════════════
# PAGE VIEW
# ══════════════════════════════════════════════════════════════════════════════
def dashboard(request):
    db = get_db()

    # cities for AQI city picker
    aqi_cities  = sorted(db["aqi_history"].distinct("City"))
    # cities for weather picker
    w_cities    = sorted(db["weather_snapshot"].distinct("location_name"))
    # regions
    regions     = sorted(db["weather_snapshot"].distinct("region"))
    # year range
    years       = sorted(db["aqi_history"].distinct("Year"))

    default_city = "Delhi" if "Delhi" in aqi_cities else (aqi_cities[0] if aqi_cities else "")
    default_wcity = w_cities[0] if w_cities else ""

    ctx = {
        "aqi_cities":   json.dumps(aqi_cities),
        "w_cities":     json.dumps(w_cities),
        "regions":      json.dumps(regions),
        "year_min":     years[0]  if years else 2015,
        "year_max":     years[-1] if years else 2020,
        "default_city": default_city,
        "default_wcity":default_wcity,
    }
    return render(request, "analytics/dashboard.html", ctx)


# ══════════════════════════════════════════════════════════════════════════════
# API : AQI TRENDS  (Tab 1)
# ══════════════════════════════════════════════════════════════════════════════
def api_aqi_trends(request):
    db   = get_db()
    city = request.GET.get("city", "Delhi")
    y1   = int(request.GET.get("y1", 2015))
    y2   = int(request.GET.get("y2", 2020))

    # ─ Chart 1: daily time-series ─────────────────────────────────────────
    raw = list(db["aqi_history"].find(
        {"City": city, "Year": {"$gte": y1, "$lte": y2}},
        {"_id": 0, "Date": 1, "AQI": 1, "AQI_Bucket": 1}
    ).sort("Date", 1))
    ts = [{"date": r["Date"], "aqi": _round(r["AQI"]), "bucket": r.get("AQI_Bucket")}
          for r in raw if r.get("AQI") is not None]

    # ─ Chart 2: monthly averages ──────────────────────────────────────────
    pipeline_monthly = [
        {"$match": {"City": city, "Year": {"$gte": y1, "$lte": y2}}},
        {"$group": {"_id": "$Month", "avg_aqi": {"$avg": "$AQI"}}},
        {"$sort": {"_id": 1}},
    ]
    monthly = [{"month": r["_id"], "avg_aqi": _round(r["avg_aqi"])}
               for r in db["aqi_history"].aggregate(pipeline_monthly)]

    # ─ Chart 3: year-month heatmap ────────────────────────────────────────
    pipeline_heat = [
        {"$match": {"City": city, "Year": {"$gte": y1, "$lte": y2}}},
        {"$group": {"_id": {"year": "$Year", "month": "$Month"}, "avg_aqi": {"$avg": "$AQI"}}},
        {"$sort": {"_id": 1}},
    ]
    heat = [{"year": r["_id"]["year"], "month": r["_id"]["month"], "avg_aqi": _round(r["avg_aqi"])}
            for r in db["aqi_history"].aggregate(pipeline_heat)]

    # ─ Report Summary ─────────────────────────────────────────────────────
    avg_total = _round(sum(r['aqi'] for r in ts)/len(ts)) if ts else 0
    y1_list = [r['avg_aqi'] for r in heat if r['year']==y1]
    y2_list = [r['avg_aqi'] for r in heat if r['year']==y2]
    y1_avg = _round(sum(y1_list)/len(y1_list)) if y1_list else 0
    y2_avg = _round(sum(y2_list)/len(y2_list)) if y2_list else 0
    trend  = "worsening" if y2_avg > y1_avg else "improving"
    delta  = abs(_round(y2_avg - y1_avg)) if heat else 0

    # ─ SMA & Forecast (7 Days) ─────────────────────────────────────────────
    # Simple 7-day moving average
    val_list = [r['aqi'] for r in ts]
    sma = []
    if len(val_list) >= 7:
        for i in range(len(val_list)):
            if i < 6:
                sma.append(None)
            else:
                window = val_list[i-6:i+1]
                sma.append(_round(sum(window)/7))
    else:
        sma = [None] * len(val_list)

    # Simple Linear Projection (Forecast)
    forecast = []
    if len(val_list) >= 10:
        # Simple trend based on last 10 days
        last_10 = val_list[-10:]
        avg_delta = (last_10[-1] - last_10[0]) / 9
        curr = last_10[-1]
        for i in range(1, 8):
            curr += avg_delta
            forecast.append(_round(max(0, curr)))

    report = {
        "avg": avg_total,
        "trend_label": trend,
        "delta": delta,
        "peak": max(val_list) if val_list else 0,
        "who_who_breach_pct": _round(len([v for v in val_list if v > 50])/len(val_list)*100) if val_list else 0
    }

    return JsonResponse({
        "ts": ts, "monthly": monthly, "heat": heat, 
        "report": report, "sma": sma, "forecast": forecast,
        "thresholds": {"WHO_AQI": 50, "IND_SATISFACTORY": 100}
    })


# ══════════════════════════════════════════════════════════════════════════════
# API : POLLUTANTS  (Tab 2)
# ══════════════════════════════════════════════════════════════════════════════
def api_pollutants(request):
    db   = get_db()
    city = request.GET.get("city", "Delhi")

    pollutant_fields = ["PM2_5", "PM10", "NO", "NO2", "NOx", "NH3", "CO", "SO2", "O3"]

    # ─ Mean concentrations ────────────────────────────────────────────────
    group_stage = {"_id": None}
    for f in pollutant_fields:
        group_stage[f] = {"$avg": f"${f}"}
    pipeline = [{"$match": {"City": city}}, {"$group": group_stage}]
    res = list(db["aqi_history"].aggregate(pipeline))
    means = {}
    if res:
        for f in pollutant_fields:
            v = _round(res[0].get(f))
            if v is not None:
                means[f] = v

    # ─ Correlation Matrix (Pearson approximation) ─────────────────────────
    # We'll take a sample of 500 rows for performance
    cursor = db["aqi_history"].find({"City": city}, {"_id": 0, "AQI": 1, "PM2_5":1, "PM10":1, "NO2":1, "CO":1}).limit(500)
    import pandas as pd
    df = pd.DataFrame(list(cursor))
    corr = {}
    if not df.empty:
        corr_matrix = df.corr().round(2).to_dict()
        corr = corr_matrix

    # ─ Box Plot Stats (PM2.5) ─────────────────────────────────────────────
    cursor_pm = db["aqi_history"].find({"City": city, "PM2_5": {"$exists": True}}, {"PM2_5": 1})
    pm_vals = sorted([r["PM2_5"] for r in cursor_pm if r.get("PM2_5") is not None])
    box = {}
    if pm_vals:
        n = len(pm_vals)
        box = {
            "min": pm_vals[0],
            "q1":  pm_vals[int(n*0.25)],
            "med": pm_vals[int(n*0.5)],
            "q3":  pm_vals[int(n*0.75)],
            "max": pm_vals[-1],
        }

    # ─ AQI bucket distribution ──────────────────────────────────────
    pipeline_bucket = [
        {"$match": {"City": city}},
        {"$group": {"_id": "$AQI_Bucket", "count": {"$sum": 1}}},
    ]
    buckets = [{"bucket": r["_id"], "count": r["count"]}
               for r in db["aqi_history"].aggregate(pipeline_bucket) if r["_id"]]

    # ─ Report ─────────────────────────────────────────────────────────────
    top_p = max(means, key=means.get) if means else "N/A"
    poor_days = sum(b['count'] for b in buckets if b['bucket'] in ['Poor','Very Poor','Severe'])
    total_days = sum(b['count'] for b in buckets)
    risk_pct = _round((poor_days / total_days * 100)) if total_days else 0

    report = {
        "top_pollutant": top_p,
        "risk_pct": risk_pct,
        "total_days": total_days
    }

    return JsonResponse({
        "means": means, "buckets": buckets, "report": report, 
        "corr": corr, "box": box,
        "thresholds": {"WHO_PM25": 15, "WHO_NO2": 40}
    })


# ══════════════════════════════════════════════════════════════════════════════
# API : WEATHER SYNOPSIS  (Tab 3)
# ══════════════════════════════════════════════════════════════════════════════
def api_weather(request):
    db   = get_db()
    city = request.GET.get("city", "")

    # ─ Sparkline data (last 24 snapshots simulation if not time-series) ──────
    # For this project, we'll just return the current value and a fake jitter for visual sparkline
    snap = db["weather_snapshot"].find_one(
        {"location_name": {"$regex": city, "$options": "i"}},
        {"_id": 0}
    )
    if not snap:
        snap = {}

    gauges = {
        "temp":     _round(snap.get("temperature_celsius")),
        "humidity": _round(snap.get("humidity")),
        "pm2_5":    _round(snap.get("pm2_5")),
        "wind":     _round(snap.get("wind_kph")),
        "condition":snap.get("condition_text", ""),
        "region":   snap.get("region", ""),
    }

    # ─ Chemical mix ───────────────────────────────────────────────────────
    chem = {
        "NO2":  _round(snap.get("no2")),
        "SO2":  _round(snap.get("so2")),
        "O3":   _round(snap.get("o3")),
        "CO":   _round((snap.get("co") or 0) / 10),  # scaled
        "PM2.5":_round(snap.get("pm2_5")),
        "PM10": _round(snap.get("pm10")),
    }
    chem = {k: v for k, v in chem.items() if v is not None}

    # ─ City vs regional avg ─────────────────────────────────────────
    region = snap.get("region", "")
    pipeline_reg = [
        {"$match": {"region": region}},
        {"$group": {
            "_id": None,
            "avg_temp":     {"$avg": "$temperature_celsius"},
            "avg_humidity": {"$avg": "$humidity"},
            "avg_pm25":     {"$avg": "$pm2_5"},
        }},
    ]
    reg = list(db["weather_snapshot"].aggregate(pipeline_reg))
    region_avg = reg[0] if reg else {}

    comparison = {
        "metrics":   ["Temperature", "Humidity", "PM2.5"],
        "city":      [gauges["temp"], gauges["humidity"], gauges["pm2_5"]],
        "region_avg":[
            _round(region_avg.get("avg_temp")),
            _round(region_avg.get("avg_humidity")),
            _round(region_avg.get("avg_pm25")),
        ],
        "region_name": region,
    }

    # ─ Report ─────────────────────────────────────────────────────────────
    pm_diff = _round(gauges["pm2_5"] - (region_avg.get("avg_pm25") or 0)) if gauges["pm2_5"] else 0
    verdict = "higher" if pm_diff > 0 else "lower"
    report = {
        "pm_diff": abs(pm_diff),
        "verdict": verdict,
        "region": region
    }

    return JsonResponse({"gauges": gauges, "chem": chem, "comparison": comparison, "report": report})


# ══════════════════════════════════════════════════════════════════════════════
# API : REGIONAL (Tab 4)
# ══════════════════════════════════════════════════════════════════════════════
def api_regional(request):
    db      = get_db()
    regions = request.GET.getlist("regions")

    match = {"region": {"$in": regions}} if regions else {}

    # ─ Macro metrics ──────────────────────────────────────────────────────
    pipeline_macro = [
        {"$match": match},
        {"$group": {
            "_id":          "$region",
            "avg_temp":     {"$avg": "$temperature_celsius"},
            "avg_humidity": {"$avg": "$humidity"},
            "avg_pm25":     {"$avg": "$pm2_5"},
            "city_count":   {"$addToSet": "$location_name"},
        }},
        {"$project": {
            "avg_temp":     1, "avg_humidity": 1, "avg_pm25": 1,
            "city_count":   {"$size": "$city_count"},
        }},
        {"$sort": {"avg_temp": -1}},
    ]
    macro = [{
        "region":       r["_id"],
        "avg_temp":     _round(r["avg_temp"]),
        "avg_humidity": _round(r["avg_humidity"]),
        "avg_pm25":     _round(r.get("avg_pm25")),
        "city_count":   r["city_count"],
    } for r in db["weather_snapshot"].aggregate(pipeline_macro)]

    # ─ Mapbox Scatter Coordinates ──────────────────────────────────────────
    scatter = list(db["weather_snapshot"].find(
        match,
        {"_id": 0, "location_name": 1, "region": 1, "latitude": 1, "longitude": 1,
         "temperature_celsius": 1, "humidity": 1, "pm2_5": 1, "condition_text": 1}
    ))
    # Rename for Plotly frontend
    map_data = [{
        "city":      s.get("location_name"),
        "region":    s.get("region"),
        "lat":       s.get("latitude"),
        "lon":       s.get("longitude"),
        "temp":      s.get("temperature_celsius"),
        "pm25":      s.get("pm2_5"),
        "condition": s.get("condition_text")
    } for s in scatter]

    # ─ Top 10 most polluted cities (historical) ─────────────────────
    pipeline_top10 = [
        {"$group": {"_id": "$City", "avg_aqi": {"$avg": "$AQI"}}},
        {"$sort":  {"avg_aqi": -1}},
        {"$limit": 10},
    ]
    top10 = [{"city": r["_id"], "avg_aqi": _round(r["avg_aqi"])}
             for r in db["aqi_history"].aggregate(pipeline_top10)]

    # ─ Report ─────────────────────────────────────────────────────────────
    h_temp = macro[0]['region'] if macro else "None"
    h_pm   = max(macro, key=lambda x: x['avg_pm25'] or 0)['region'] if macro else "None"
    report = {
        "hottest_region": h_temp,
        "most_polluted": h_pm,
        "count": len(macro)
    }

    return JsonResponse({
        "macro": macro, "map_data": map_data, "top10": top10, "report": report
    })
