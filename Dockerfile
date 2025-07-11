FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python init_db.py && uvicorn weather_microservice:app --host 0.0.0.0 --port 8000"]
