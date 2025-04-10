from fastapi import FastAPI
import sqlite3
import pandas as pd

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Heatwave Predictor API"}

@app.get("/heatwave/{city}")
def get_heatwave(city: str):
    conn = sqlite3.connect("weather.db")
    df = pd.read_sql("SELECT * FROM forecasts WHERE city = ?", conn, params=(city,))
    conn.close()
    df = df[df['is_heatwave'] == 1]
    return df.to_dict(orient="records")

