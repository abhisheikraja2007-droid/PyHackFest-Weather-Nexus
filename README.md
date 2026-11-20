# 🌦️ Weather Nexus — Real-Time Indian Weather & Air Quality Intelligence

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django)
![Pandas](https://img.shields.io/badge/Pandas-Data_Analysis-150458?style=for-the-badge&logo=pandas)
![Hackathon](https://img.shields.io/badge/PyHackFest-Winner-gold?style=for-the-badge)

A data analytics platform developed for **PyHackFest** that ingests historical and live meteorological data across major Indian cities, computes Air Quality Indices (AQI), detects climatic anomalies, and renders interactive analytical dashboards.

---

## 📌 Key Capabilities
- **Comprehensive Indian Climate Dataset**: Ingests and processes millions of meteorological records across all Indian states and union territories (`IndianWeatherRepository.csv`, `city_day.csv`).
- **Real-Time AQI & Weather Ingestion**: Automated background pipeline (`ingest_data.py`) querying public atmospheric APIs with rate-limiting and failover.
- **Statistical Analytics Engine**: Calculates rolling temperature means, precipitation variance, particulate matter ratios ($PM_{2.5} / PM_{10}$), and heat index alerts.
- **Django Interactive Dashboard**: Dynamic web interface displaying meteorological trend graphs, city comparisons, and automated alert banners.

---

## 📂 Project Structure
```text
PyHackFest/
├── IndianWeatherRepository.csv    # Comprehensive national climate dataset
├── city_day.csv                   # Daily city-level air quality observations
├── utils.py                       # Numerical transforms and metric utilities
├── weather_nexus/                 # Django core project
│   ├── manage.py                  # Django CLI
│   ├── ingest_data.py             # Automated dataset ingestion script
│   ├── test_api.py                # API validation test suite
│   ├── analytics/                 # Weather analytics app
│   │   ├── views.py               # Dashboard views and REST endpoints
│   │   ├── db.py                  # Database queries and cache layer
│   │   └── templates/             # UI dashboard templates
│   └── weather_nexus/             # Configuration & routing
└── README.md                      # Documentation
```

---

## 🚀 Quickstart

### 1. Setup Environment
```bash
pip install django pandas numpy requests
```

### 2. Ingest Data & Run Migrations
```bash
cd weather_nexus
python manage.py migrate
python ingest_data.py
```

### 3. Launch Development Server
```bash
python manage.py runserver
```
Visit `http://localhost:8000` to explore the dashboard.
