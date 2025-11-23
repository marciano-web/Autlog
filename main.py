import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# =========================
# CONFIG DO BANCO
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class TemperatureReading(Base):
    __tablename__ = "temperature_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True, nullable=False)
    temperature_c = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

Base.metadata.create_all(bind=engine)

# =========================
# MODELO DE ENTRADA
# =========================
class TemperaturePayload(BaseModel):
    device_id: str
    temperature_c: float

# =========================
# FASTAPI
# =========================
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/api/temperatura")
def receber_temperatura(payload: TemperaturePayload):
    try:
        db = SessionLocal()
        leitura = TemperatureReading(
            device_id=payload.device_id,
            temperature_c=payload.temperature_c,
        )
        db.add(leitura)
        db.commit()
        db.refresh(leitura)
    except Exception as e:
        print("Erro ao salvar:", e)
        raise HTTPException(status_code=500, detail="erro ao salvar")
    finally:
        db.close()

    return {"status": "ok", "id": leitura.id}
