"""
admin_indices.py

Rotas de administração dos índices de correção.
Protegidas por HTTP Basic Auth (ver core/admin_auth.py).

Como plugar no main.py:

    from admin_indices import router as admin_router
    app.include_router(admin_router)

Rotas:
    GET  /admin           -> formulário + tabela com a última data cadastrada de cada índice
    POST /admin/valor      -> grava (insere ou atualiza) um valor de índice num mês/ano
"""
import os
from datetime import date

import psycopg2
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse

from core.admin_auth import verificar_admin

router = APIRouter()


def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def listar_indices_com_ultima_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.id, i.nome, MAX(v.data) AS ultima_data
        FROM indices i
        LEFT JOIN valores v ON v.indice_id = i.id
        GROUP BY i.id, i.nome
        ORDER BY i.nome
    """)
    linhas = cur.fetchall()
    conn.close()
    return linhas


def salvar_valor(indice_id: int, data_valor: date, valor: float):
    conn = get_conn()
    cur = conn.cursor()
    # upsert: se já existir um valor pra esse índice+data, atualiza; senão insere
    cur.execute("""
        INSERT INTO valores (indice_id, data, valor)
        VALUES (%s, %s, %s)
        ON CONFLICT (indice_id, data)
        DO UPDATE SET valor = EXCLUDED.valor
    """, (indice_id, data_valor, valor))
    conn.commit()
    conn.close()


def render_pagina(mensagem: str = "") -> str:
    linhas = listar_indices_com_ultima_data()

    opcoes_html = "".join(
        f'<option value="{id_}">{nome}</option>' for id_, nome, _ in linhas
    )

    linhas_html = "".join(
        f"<tr><td>{nome}</td><td>{ultima_data.strftime('%d/%m/%Y') if ultima_data else '— sem dados —'}</td></tr>"
        for _, nome, ultima_data in linhas
    )

    mensagem_html = f'<p class="msg">{mensagem}</p>' if mensagem else ""

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Admin Aequita — Índices</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }}
            h1 {{ font-size: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 16px 0 32px; }}
            th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #ddd; font-size: 14px; }}
            form {{ display: flex; flex-direction: column; gap: 10px; max-width: 300px; }}
            label {{ font-size: 13px; font-weight: bold; }}
            input, select {{ padding: 6px; font-size: 14px; }}
            button {{ padding: 8px; font-size: 14px; cursor: pointer; }}
            .msg {{ background: #e6ffed; border: 1px solid #34a853; padding: 8px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <h1>Admin — Índices de Correção (Aequita)</h1>
        {mensagem_html}

        <h2 style="font-size:15px;">Última data cadastrada por índice</h2>
        <table>
            <tr><th>Índice</th><th>Última data</th></tr>
            {linhas_html}
        </table>

        <h2 style="font-size:15px;">Adicionar / atualizar valor</h2>
        <form method="post" action="/admin/valor">
            <label>Índice</label>
            <select name="indice_id" required>
                {opcoes_html}
            </select>

            <label>Data (mês de referência)</label>
            <input type="date" name="data_valor" required>

            <label>Valor (%)</label>
            <input type="number" step="0.0001" name="valor" required placeholder="ex: 0.53">

            <button type="submit">Salvar</button>
        </form>
    </body>
    </html>
    """


@router.get("/admin", response_class=HTMLResponse)
def admin_home(usuario: str = Depends(verificar_admin)):
    return render_pagina()


@router.post("/admin/valor", response_class=HTMLResponse)
def admin_salvar_valor(
    indice_id: int = Form(...),
    data_valor: date = Form(...),
    valor: float = Form(...),
    usuario: str = Depends(verificar_admin),
):
    salvar_valor(indice_id, data_valor, valor)
    return render_pagina(mensagem=f"Valor salvo com sucesso para {data_valor.strftime('%d/%m/%Y')}.")
