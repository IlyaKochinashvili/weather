import os
import sqlite3
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import httpx
import logging
from dotenv import load_dotenv

# --- LOAD ENV ---
load_dotenv()

# --- CONFIG ---
CITIES = os.getenv("CITIES", "Kiev").split(",")
API_KEY = os.getenv("OWM_API_KEY", "d5ffa334b443157eff6d5e5bb6c96510")
X_TOKEN = os.getenv("X_TOKEN", "12345678901234567890123456789012")
DB_PATH = os.getenv("DB_PATH", "weather.db")

# --- INIT ---
app = FastAPI()
scheduler = BackgroundScheduler()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MIDDLEWARE ---
async def validate_token(request: Request):
    token = request.headers.get("x-token")
    if not token or len(token) != 32:
        raise HTTPException(status_code=403, detail="Forbidden: invalid x-token")

# --- MODELS ---
class TemperatureEntry(BaseModel):
    city: str
    temperature: float
    timestamp: str

class TemperatureResponse(BaseModel):
    entries: list[TemperatureEntry]

@app.on_event("startup")
async def startup_event():
    fetch_all_cities()

# --- FETCH + SAVE ---
def fetch_and_store_temperature_for_city(city: str):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        temperature = data["main"]["temp"]
        timestamp = datetime.utcnow().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO temperatures (city, temperature, timestamp) VALUES (?, ?, ?)",
                (city, temperature, timestamp)
            )
            conn.commit()
        logger.info(f"Saved temperature {temperature} for {city} at {timestamp}")
    except Exception:
        logger.exception(f"Failed to fetch or store temperature for {city}")

def fetch_all_cities():
    for city in CITIES:
        fetch_and_store_temperature_for_city(city.strip())

# --- ROUTES ---
@app.get("/temperature", response_model=TemperatureResponse)
async def get_temperature(
        day: str = Query(..., description="Format: YYYY-MM-DD"),
        city: str = Query(None, description="Optional city filter"),
        _: None = Depends(validate_token),
):
    try:
        date = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use Y-m-d")

    start = date.isoformat()
    end = (date + timedelta(days=1)).isoformat()

    query = "SELECT city, temperature, timestamp FROM temperatures WHERE timestamp >= ? AND timestamp < ?"
    params = [start, end]

    if city:
        query += " AND city = ?"
        params.append(city)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

    entries = [TemperatureEntry(city=city, temperature=temp, timestamp=ts) for city, temp, ts in rows]
    return TemperatureResponse(entries=entries)

# --- MAIN ---
scheduler.add_job(fetch_all_cities, "interval", hours=1)
scheduler.start()

if __name__ == "__main__":
    fetch_all_cities()  # вручную для первого раза
    scheduler.add_job(fetch_all_cities, "interval", hours=1)
    scheduler.start()
    import uvicorn
    uvicorn.run("weather_microservice:app", host="0.0.0.0", port=8000)
