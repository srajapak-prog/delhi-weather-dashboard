import requests
import sqlite3
from datetime import datetime
import schedule
import time

# Cities and coordinates
cities = {
    "New Delhi": (28.6139, 77.2090),
    "North Delhi": (28.7110, 77.2090),
    "South Delhi": (28.5300, 77.2300),
    "East Delhi": (28.6448, 77.2550),
    "West Delhi": (28.6465, 77.0723),
    "Central Delhi": (28.6302, 77.2197),
    "North West Delhi": (28.7073, 77.1734),
    "South West Delhi": (28.5284, 77.1088),
    "Shahdara": (28.6667, 77.2833),
    "Dwarka": (28.5733, 77.0120),
    "Rohini": (28.7359, 77.1325),
    "Vasant Kunj": (28.5416, 77.1362),
    "Pitampura": (28.7033, 77.1397),
    "Saket": (28.5293, 77.2211),
    "Preet Vihar": (28.6247, 77.2934),
    "Karol Bagh": (28.6465, 77.2090),
    "Moti Nagar": (28.6452, 77.1470),
    "Janakpuri": (28.5934, 77.0822),
    "Lajpat Nagar": (28.5721, 77.2292),
    "Rajouri Garden": (28.6347, 77.1245),
    "Greater Kailash": (28.5491, 77.2494),
    "Okhla": (28.5514, 77.2622),
    "Connaught Place": (28.6300, 77.2150),
    "Gurugram": (28.4595, 77.0266),
    "Noida": (28.5355, 77.3910),
    "Faridabad": (28.4089, 77.3165)
}

# Risk level based on temperature
def calculate_risk_level(temp):
    if temp < 35:
        return 0  # No risk
    elif temp < 38:
        return 1  # Low risk
    elif temp < 40:
        return 2  # Moderate risk
    else:
        return 3  # High risk

# Fetch 14-day forecast for heatwave
def fetch_forecast(city, lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max"
        f"&forecast_days=14"
        f"&timezone=Asia%2FKolkata"
    )
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data['daily']['time'], data['daily']['temperature_2m_max']
    else:
        print(f"Failed to fetch data for {city}. Status code: {response.status_code}")
        return [], []

# Fetch full weather forecast data
def fetch_full_weather(city, lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
        f"&forecast_days=14"
        f"&timezone=Asia%2FKolkata"
    )
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return data['daily']['time'], data['daily']['temperature_2m_max'], data['daily']['temperature_2m_min'], data['daily']['precipitation_sum'], data['daily']['wind_speed_10m_max']
    else:
        print(f"Failed to fetch full weather data for {city}. Status code: {response.status_code}")
        return [], [], [], [], []

# Save forecast to DB
def save_to_db(conn, city, dates, temps, full_weather=False):
    cursor = conn.cursor()
    for date, temp in zip(dates, temps):
        if full_weather:
            cursor.execute("""
                INSERT OR REPLACE INTO full_weather_data (city, date, max_temp, min_temp, precipitation, wind_speed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (city, date, temp[0], temp[1], temp[2], temp[3]))
        else:
            risk = calculate_risk_level(temp)
            cursor.execute("""
                INSERT OR REPLACE INTO forecasts (city, date, max_temp, is_heatwave)
                VALUES (?, ?, ?, ?)
            """, (city, date, temp, risk))
    conn.commit()

# Create DB tables if not exists
def initialize_db():
    conn = sqlite3.connect("weather.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            city TEXT,
            date TEXT,
            max_temp REAL,
            is_heatwave INTEGER,
            PRIMARY KEY (city, date)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS full_weather_data (
            city TEXT,
            date TEXT,
            max_temp REAL,
            min_temp REAL,
            precipitation REAL,
            wind_speed REAL,
            PRIMARY KEY (city, date)
        )
    """)
    conn.commit()
    return conn

# Main logic to run periodically
def fetch_and_store_forecasts():
    print(f"\n📅 Running fetch job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    conn = initialize_db()

    for city, (lat, lon) in cities.items():
        print(f"🌤️ Fetching forecast for {city}...")
        dates, temps = fetch_forecast(city, lat, lon)
        if dates and temps:
            save_to_db(conn, city, dates, temps)

        # Fetch and save full weather data
        full_dates, max_temps, min_temps, precip, wind_speeds = fetch_full_weather(city, lat, lon)
        if full_dates and max_temps:
            full_weather_data = list(zip(max_temps, min_temps, precip, wind_speeds))
            save_to_db(conn, city, full_dates, full_weather_data, full_weather=True)

    conn.close()
    print("✅ Forecast data updated.\n")

# Schedule every 24 hours
schedule.every(24).hours.do(fetch_and_store_forecasts)

if __name__ == "__main__":
    fetch_and_store_forecasts()  # Run immediately
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
