from django.urls import path
from analytics import views

urlpatterns = [
    path("",           views.dashboard,       name="dashboard"),
    path("api/aqi/",   views.api_aqi_trends,  name="api_aqi_trends"),
    path("api/pollutants/", views.api_pollutants, name="api_pollutants"),
    path("api/weather/",    views.api_weather,    name="api_weather"),
    path("api/regional/",   views.api_regional,   name="api_regional"),
]
