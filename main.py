from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# ==============================
# Conexão com o Postgres (Railway)
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não está definido nas variáveis de ambiente!")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
conn.autocommit = True

# Garante que a tabela exista
with conn.cursor() as cur:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS temperature_logs (
            id SERIAL PRIMARY KEY,
            device_id TEXT NOT NULL,
            temperature_c DOUBLE PRECISION NOT NULL,
            measured_at TIMESTAMP,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

# ==============================
# Modelo de dados recebido do ESP32
# ==============================
class TemperaturePayload(BaseModel):
    device_id: str
    temperature_c: float
    timestamp: str | None = None  # ex.: "2025-11-24T14:30:00-03:00" (horário do Brasil)

# ==============================
# App FastAPI
# ==============================
app = FastAPI(title="Autolog API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/temperatura")
def receber_temperatura(payload: TemperaturePayload):
    """
    Recebe:
    {
      "device_id": "logger-01",
      "temperature_c": 23.12,
      "timestamp": "2025-11-24T14:30:00-03:00"   (horário do Brasil UTC-3)
    }

    Salva APENAS a data/hora sem timezone (ignora o fuso).
    Se o ESP32 envia 14:30, o banco salva 14:30.
    """

    # Trata timestamp enviado pelo ESP32 (opcional)
    measured_at = None
    if payload.timestamp:
        try:
            # Remove o timezone do timestamp antes de salvar
            # 2025-11-24T14:30:00-03:00 → 2025-11-24T14:30:00
            timestamp_str = payload.timestamp.split('-03:00')[0].split('Z')[0].split('+')[0]
            dt = datetime.fromisoformat(timestamp_str)
            measured_at = dt
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"timestamp inválido: {str(e)}")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO temperature_logs (device_id, temperature_c, measured_at)
            VALUES (%s, %s, %s)
            RETURNING id, created_at, measured_at;
            """,
            (payload.device_id, payload.temperature_c, measured_at),
        )
        row = cur.fetchone()

    return {
        "status": "ok",
        "id": row["id"],
        "created_at": row["created_at"],
        "measured_at": row["measured_at"],
    }
