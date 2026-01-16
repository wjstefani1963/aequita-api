from fastapi import FastAPI
#from pathlib import Path
from pydantic import BaseModel
from datetime import date
from datetime import datetime
from core.calculos import calcular_valor_corrigido,indice_existe_no_periodo
from core.calculos import calcular_indice
import os
from fastapi.middleware.cors import CORSMiddleware
#import sqlite3
#from pydantic import BaseModel, EmailStr
from fastapi import Request, HTTPException

app = FastAPI(title="Aequita Simple API")

#DB_PATH = Path(r"C:\Meus_Projetos\indices_central\indices.sqlite")
#print("DB existe?", DB_PATH.exists())
'''
BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "indices.sqlite"
print("DB existe?", DB_PATH.exists())

if os.getenv("RENDER") == "true":
    DB_DIR = Path("/data")
else:
    DB_DIR = Path("data")

DB_DIR.mkdir(parents=True, exist_ok=True)


DB_LEADS = DB_DIR / "app.sqlite"
'''

class LeadRequest(BaseModel):
    email: str

'''
def init_db():
    conn = sqlite3.connect(DB_LEADS)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

'''



@app.post("/lead")
def lead(req: LeadRequest):
    destinatario = req.email
    remetente = os.getenv("SMTP_USER")  # seu Gmail
    senha = os.getenv("SMTP_PASS")      # senha de app

    try:
        msg = email.message.Message()
        msg["Subject"] = "Obrigado pelo seu cadastro"
        msg["From"] = remetente
        msg["To"] = destinatario

        corpo_email = f"""
        <p>Olá,</p>
        <p>Recebemos seu email: {destinatario}</p>
        <p>Obrigado por se cadastrar!</p>
        """
        corpo_email = corpo_email.encode("utf-8")
        msg.add_header("Content-Type", "text/html")
        msg.set_payload(corpo_email)

        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(remetente, senha)
        servidor.send_message(msg)
        servidor.quit()

        return {"status": "ok", "email_enviado": destinatario}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
💡
@app.get("/ping")
def ping():
    return {"ok": True}


'''
@app.get("/leads")
def listar_leads():
    try:
        conn = sqlite3.connect(DB_LEADS)
        cur = conn.cursor()
        cur.execute("SELECT id, email, created_at FROM leads ORDER BY id DESC LIMIT 20")
        rows = cur.fetchall()
        conn.close()
        return {"leads": [{"id": r[0], "email": r[1], "created_at": r[2]} for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # depois você restringe
    allow_credentials=True,
    allow_methods=["*"],          # MUITO IMPORTANTE
    allow_headers=["*"],
)

class CalculoRequest(BaseModel):
    valor: float
    data_inicio: date
    data_fim: date
    indice: str
    aceitar_negativos: bool 

class CalculoResponse(BaseModel):
    dias: int
    fator: float
    valor_final: float






@app.post("/calcular")
def calcular(req: CalculoRequest):

    #data_inicio = datetime.strptime(req.data_inicio, "%Y-%m-%d").date()
    #data_fim = datetime.strptime(req.data_fim, "%Y-%m-%d").date()

    resultado = calcular_indice(
        req.valor,
        req.data_inicio,
        req.data_fim,
        req.indice,
        req.aceitar_negativos
    )

    return {
        "resultado": round(resultado, 2)
    }


'''
@app.post("/calcular")
def calcular(req: CalculoRequest):
    resultado = calcular_indice(
        req.valor,
        req.data_inicio,
        req.data_fim,
        req.indice,
        req.aceitar_negativos
    )


    return {"resultado": resultado}


@app.post("/calcular")
def calcular(req: CalculoRequest):

    if not indice_existe_no_periodo(
        req.indice,
        req.data_inicio,
        req.data_fim
    ):
        raise HTTPException(
            status_code=400,
            detail="O índice selecionado não possui valores para o período informado."
        )

    resultado = calcular_indice(
        req.valor,
        req.data_inicio,
        req.data_fim,
        req.indice,
        req.aceitar_negativos
    )

    return {"resultado": round(resultado, 2)}

'''

@app.get("/indices")
def listar_indices():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT nome FROM indices ORDER BY nome")
    rows = cursor.fetchall()

    conn.close()

    indices = [row[0] for row in rows]

    return {"indices": indices}


@app.get("/")
def home():
    return {"status": "API Aequita no ar"}


@app.get("/teste-db")
def teste_db():
    import sqlite3

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM indices LIMIT 5")
        rows = cursor.fetchall()
        conn.close()
        return {"primeiros_indices": [row[0] for row in rows]}
    except Exception as e:
        return {"erro": str(e)}


@app.get("/versao")
def versao():
    return {
        "app": "aequita-api",
        "versao": "2026-01-16",
        "commit": "1.1"
    }


# --- ESTA PARTE É O FINAL ---
if __name__ == "__main__":
    app.run(debug=True, port=8000)
