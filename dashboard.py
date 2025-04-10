import sqlite3
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from io import BytesIO
import base64
import plotly.express as px

# Streamlit config
st.set_page_config(page_title="Delhi Heatwave Dashboard", layout="wide")

# Read and embed logo image
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

img_base64 = get_base64_image("logo.png")

st.markdown(f"""
<div style="display: flex; justify-content: center;">
    <img src="data:image/png;base64,{img_base64}" width="100">
</div>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style='text-align: center;'>
    Delhi Rising - Heatwave Risk — Delhi & NCR
</h1>
""", unsafe_allow_html=True)

# --- City Coordinates ---
city_coords = {
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

# --- Sidebar Filters ---
with st.sidebar:
    st.header("🔍 Filters")
    available_cities = list(city_coords.keys())
    city = st.selectbox("🏙️ Select City", sorted(available_cities))

# Fetch data
conn = sqlite3.connect("weather.db")

# Fetch for entire df to get date limits
df = pd.read_sql("SELECT * FROM forecasts", conn)
df['date'] = pd.to_datetime(df['date'])

# Set date range for UI
today = pd.to_datetime("today").normalize()
min_date, max_date = df['date'].min(), df['date'].max()

with st.sidebar:
    date_range = st.date_input("📅 Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

# Convert date input to datetime
date_start = pd.to_datetime(date_range[0])
date_end = pd.to_datetime(date_range[1])

# Filter by city and date
filtered = df[(df['city'] == city) & (df['date'] >= date_start) & (df['date'] <= date_end)]

# Risk label mapping
risk_map = {
    0: "🟢 No Risk",
    1: "🟡 Low Risk",
    2: "🟠 Moderate Risk",
    3: "🔴 High Risk"
}
filtered['risk_level_label'] = filtered['is_heatwave'].map(risk_map)

# --- Folium Heatmap ---
st.title("🗺️ Interactive Heatwave Risk Map (Delhi & NCR)")

selected_date = st.date_input("📅 Select Date for Map", min_value=min_date, max_value=max_date, value=today)
heatmap_df = df[df['date'] == pd.to_datetime(selected_date)]

risk_color_map = {
    0: "green",
    1: "orange",
    2: "darkorange",
    3: "red"
}
heatmap_df['risk_color'] = heatmap_df['is_heatwave'].map(risk_color_map)

folium_map = folium.Map(location=[28.6139, 77.2090], zoom_start=10, tiles="CartoDB positron")
marker_cluster = MarkerCluster().add_to(folium_map)

for city_name, (lat, lon) in city_coords.items():
    city_data = heatmap_df[heatmap_df["city"] == city_name]
    if not city_data.empty:
        risk_level = city_data["is_heatwave"].values[0]
        risk_label = risk_map[risk_level]
        risk_color = risk_color_map[risk_level]
    else:
        risk_label = "No Data"
        risk_color = "gray"

    folium.Marker(
        location=[lat, lon],
        popup=f"<b>{city_name}</b><br>{risk_label}",
        icon=folium.Icon(color=risk_color if risk_color != "gray" else "lightgray")
    ).add_to(marker_cluster)

st_folium(folium_map, width=1000, height=600)

# --- Forecast Visualization ---
st.title(f"📊 Temperature & Heatwave Forecast for {city}")
st.subheader("📈 Temperature Forecast")

fig = px.line(
    filtered,
    x="date",
    y="max_temp",
    title=f"Max Daily Temperature in {city}",
    markers=True,
    labels={"max_temp": "Temperature (°C)", "date": "Date"}
)
st.plotly_chart(fig, use_container_width=True)

# --- Risk Table ---
st.subheader("🔥 Heatwave Risk Levels")
st.dataframe(
    filtered[['date', 'max_temp', 'is_heatwave', 'risk_level_label']].rename(columns={
        'date': 'Date',
        'max_temp': 'Temperature (°C)',
        'is_heatwave': 'Risk Code',
        'risk_level_label': 'Risk Level'
    })
)

# --- Export to Excel ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Forecast')
    return output.getvalue()

excel_data = to_excel(filtered[['date', 'max_temp', 'is_heatwave', 'risk_level_label']])
st.download_button("⬇️ Download Forecast as Excel", data=excel_data, file_name=f"{city}_forecast.xlsx")

# --- Full Weather Forecast Table ---
weather_df = pd.read_sql("SELECT * FROM full_weather_data WHERE city = ?", conn, params=(city,))
weather_df['date'] = pd.to_datetime(weather_df['date'])
weather_df = weather_df[(weather_df['date'] >= date_start) & (weather_df['date'] <= date_end)]

st.subheader(f"🌦️ Full Weather Forecast for {city}")
st.write("Below is the full weather data for the selected date range:")
st.dataframe(weather_df[['date', 'max_temp', 'min_temp', 'precipitation', 'wind_speed']])
