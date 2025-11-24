from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import pytz

app = Flask(__name__)
CORS(app)

# -------------------------
# Configuração do Postgres
# -------------------------

def get_db_connection():
    return psycopg2.connect(
        host="containers-us-west-103.railway.app",
        database="railway",
        user="postgres",
        password="YOUR_PASSWORD_HERE",  # <= mantenha seu original
        port=12345
    )

# -------------------------
# API ROOT
# -------------------------

@app.route("/")
def home():
    return "API ONLINE"

# -------------------------
# RECEBE DADOS DO LOGGER
# -------------------------

@app.route("/api/log", methods=["POST"])
def receive_log():

    data = request.get_json()

    device_id = data.get("device_id")
    temperature_c = data.get("temperature_c")
    timestamp_str = data.get("timestamp")  # <-- AGORA USADO!

    if not device_id or temperature_c is None or not timestamp_str:
        return jsonify({"status": "erro", "msg": "dados incompletos"}), 400

    # -------------------------
    # CONVERTE TIMESTAMP
    # -------------------------

    try:
        # interpretar como horário LOCAL do Brasil
        br_tz = pytz.timezone("America/Sao_Paulo")
        dt_local = br_tz.localize(datetime.fromisoformat(timestamp_str))

        # converter para UTC para salvar corretamente
        dt_utc = dt_local.astimezone(pytz.UTC)

    except Exception as e:
        return jsonify({"status": "erro", "msg": f"timestamp inválido: {str(e)}"}), 400

    # -------------------------
    # SALVA NO BANCO
    # -------------------------

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO logs (device_id, temperature_c, measurement_at)
    VALUES (%s, %s, %s)
    RETURNING id;
    """

    cur.execute(query, (device_id, temperature_c, dt_utc))
    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok", "id": new_id}), 200


# -------------------------
# LISTA LOGS (AJUDA PARA TESTAR)
# -------------------------

@app.route("/api/list")
def list_logs():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, device_id, temperature_c,
               measurement_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo' AS measurement_br
        FROM logs
        ORDER BY id DESC
        LIMIT 50;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)


# -------------------------
# EXECUTAR
# -------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

