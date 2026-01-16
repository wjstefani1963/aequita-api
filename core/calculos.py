#from app.models import Indice, Valor
from datetime import datetime
import calendar
import re
from pydantic import BaseModel
from datetime import date
import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "indices.sqlite"


#BASE_DIR = Path(__file__).resolve().parent.parent   # vai para a raiz do projeto
#DB_PATH = BASE_DIR / "data" / "indices.sqlite"
print("DB existe?", DB_PATH.exists())  # só para checar se o Python encontra o arquivo

def parse_currency(value_str):
    """
    Normaliza várias formas de string de moeda para float.
    Ex.: "1.234,56" -> 1234.56, "1234.56" -> 1234.56, "1.000.00" -> 1000.00
    """
    if value_str is None:
        return 0.0

    s = str(value_str).strip()
    if s == '':
        return 0.0

    # remove espaços e caracteres não numéricos (exceto . , -)
    s = s.replace(' ', '')
    s = re.sub(r'[^0-9\.,\-]', '', s)

    # formato brasileiro → vírgula é decimal
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        # apenas pontos → pode haver múltiplos (1.000.00)
        if s.count('.') > 1:
            parts = s.split('.')
            s = ''.join(parts[:-1]) + '.' + parts[-1]

    return float(s)

def meses_decimais(data_inicio, data_fim):
    """
    Calcula diferenÃ§a entre datas em meses decimais
    data_inicio e data_fim: datetime.date ou datetime.datetime
    """
    anos = data_fim.year - data_inicio.year
    meses = data_fim.month - data_inicio.month
    dias = data_fim.day - data_inicio.day

    dias_no_mes_inicio = calendar.monthrange(data_inicio.year, data_inicio.month)[1]
    meses_dec = anos * 12 + meses + dias / dias_no_mes_inicio
    return meses_dec

def calcular_fator_entre_datas(indice_nome, data_inicio, data_fim, aceitar_negativos):
    """
    Calcula o fator acumulado entre duas datas usando SQLite
    """

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM indices WHERE nome = ?",
        (indice_nome,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return 1.0

    indice_id = row[0]
    '''
    cursor.execute("""
        SELECT data, valor
        FROM valores
        WHERE indice_id = ?
          AND data >= ?
          AND data <= ?
        ORDER BY data
    """, (indice_id, data_inicio, data_fim))
    '''

    # garantir que o primeiro registro do mês de data_inicio seja incluído
    primeiro_dia_mes = data_inicio.replace(day=1)
    cursor.execute("""
        SELECT data, valor
        FROM valores
        WHERE indice_id = ?
        AND data >= ?
        AND data <= ?
        ORDER BY data
    """, (indice_id, primeiro_dia_mes, data_fim))
    valores = cursor.fetchall()
    conn.close()

    ajustes = {
        (1986, 2): 1000,
        (1989, 1): 1000,
        (1993, 8): 1000,
        (1994, 7): 2750,
    }

    ci = 1.0


    # --- mês inicial parcial se data_inicio não tiver registro no banco ---
    if valores:
        primeiro_valor_data, primeiro_valor = valores[0]
        primeiro_valor_data_obj = datetime.strptime(primeiro_valor_data, "%Y-%m-%d")
        if data_inicio < primeiro_valor_data_obj.date():
            dias_no_mes = calendar.monthrange(data_inicio.year, data_inicio.month)[1]
            proporcao = (dias_no_mes - data_inicio.day + 1) / dias_no_mes
            val_ind = float(primeiro_valor)
            if not aceitar_negativos and val_ind < 0:
                val_ind = 0.0
            ci += round(ci * val_ind / 100 * proporcao, 4)
        print('passou aqui',primeiro_valor_data_obj)     


    for i,(data_str, valor) in enumerate(valores):
        data_obj = datetime.strptime(data_str, "%Y-%m-%d")
        val_ind = float(valor)

        # regra principal
        if not aceitar_negativos and val_ind < 0:
            val_ind = 0.0
        
            # primeiro mês parcial
        if i == 0 and data_inicio.day > 1:
            dias_no_mes = calendar.monthrange(data_inicio.year, data_inicio.month)[1]
            proporcao = (dias_no_mes - data_inicio.day + 1) / dias_no_mes
            ci += round(ci * val_ind / 100 * proporcao, 4)
            print('proporc>>>',val_ind,proporcao)
        # último mês proporcional (opcional, se data_fim não for último dia)
        elif i == len(valores) - 1 and data_fim.day < calendar.monthrange(data_fim.year, data_fim.month)[1]:
            dias_no_mes = calendar.monthrange(data_fim.year, data_fim.month)[1]
            proporcao = data_fim.day / dias_no_mes
            ci += round(ci * val_ind / 100 * proporcao, 4)
        else:
            ci += round(ci * val_ind / 100, 4)


        '''
            # calcular proporção do mês parcial
        dias_no_mes = calendar.monthrange(data_obj.year, data_obj.month)[1]
        if i == 0:  # primeiro mês parcial
            proporcao = (dias_no_mes - data_inicio.day + 1) / dias_no_mes
        elif i == len(valores) - 1:  # último mês parcial
            proporcao = data_fim.day / dias_no_mes
        else:  # meses completos
            proporcao = 1.0
        ''' 
        
        #ci += round(ci * (val_ind / 100) * proporcao, 4)
        #print(data_obj,ci)
        chave = (data_obj.year, data_obj.month)
        if chave in ajustes:
            ci = ci / ajustes[chave]
        #print(data_obj, val_ind, ci)  # debug, opciona
    return ci


'''
def calcular_fator_entre_datas(indice_nome, data_inicio, data_fim, aceitar_negativos):
    """
    Calcula o fator acumulado entre duas datas (como na funÃ§Ã£o original)
    """
    indice = Indice.query.filter_by(nome=indice_nome).first()
    if not indice:
        return 1.0

    valores = Valor.query.filter(
        Valor.indice_id == indice.id,
        Valor.data >= data_inicio,
        Valor.data <= data_fim
    ).order_by(Valor.data).all()
    #print(aceitar_negativos)
    # Ajustes por mês/ano
    ajustes = {
        (1986, 2): 1000,   # fevereiro/1986
        (1989, 1): 1000,   # janeiro/1989
        (1993, 8): 1000,   # agosto/1993
        (1994, 7): 2750,   # julho/1994
    }


    ci = 1.0
    for v in valores:
        #print(f"DEBUG â†’ {v.data} | {v.valor!r} | tipo={type(v.valor)}")
            # Converte a string para datetime
        if isinstance(v.data, str):
            data_obj = datetime.strptime(v.data, "%Y-%m-%d")
        else:
            data_obj = v.data  # já é datetime

        val_ind = float(v.valor)
        
        if aceitar_negativos or val_ind > 0:
            ci += round(ci * val_ind / 100, 4)

        # mês e ano da linha atual
        #chave = (v.data.year, v.data.month)
        chave = (data_obj.year, data_obj.month)
        # Verifica se precisa aplicar divisor
        if chave in ajustes:
            divisor = ajustes[chave]
            ci = ci / divisor



    return ci
'''

def calcular_indice(valor_original, data_inicio, data_fim, indice_nome, aceitar_negativos):
    try:
        fator = calcular_fator_entre_datas(
            indice_nome,
            data_inicio,
            data_fim,
            aceitar_negativos
        )
        resultado = valor_original * fator

        if not aceitar_negativos and resultado < 0:
            resultado = 0

        return round(float(resultado), 2)

    except Exception as e:
        print("ERRO NO CÁLCULO:", e)
        raise

'''
def calcular_indice(valor_original, data_inicio, data_fim, indice_nome, aceitar_negativos):
    fator = calcular_fator_entre_datas(indice_nome, data_inicio, data_fim, aceitar_negativos)
    resultado = valor_original * fator
    if not aceitar_negativos and resultado < 0:
        resultado = 0
    return resultado  # apenas um float
'''

def juros_simples(valor: float, taxa_mensal: float, meses: float) -> float:
    """
    Juros simples aplicados sobre 'valor' por 'meses' (pode ser decimal).
    taxa_mensal em porcentagem (ex: 1.5 -> 1.5% ao mÃªs)
    Retorna o valor final (valor + juros).
    """
    if meses <= 0 or taxa_mensal == 0:
        return float(valor)
    juros = valor * (taxa_mensal / 100.0) * meses
    return float(valor + juros)


def juros_compostos(valor: float, taxa_mensal: float, meses: float) -> float:
    """
    Juros compostos: valor * (1 + taxa) ** meses
    meses pode ser decimal (faz exponenciaÃ§Ã£o real).
    """
    if meses <= 0 or taxa_mensal == 0:
        return float(valor)
    return float(valor * ((1 + taxa_mensal / 100.0) ** meses))




def databras(dtx):
    """Converte data yyyy-mm-dd em dd/mm/yyyy"""
    try:
        dtx = str(dtx)
        return f"{dtx[8:10]}/{dtx[5:7]}/{dtx[0:4]}"
    except Exception:
        return dtx

def brl(value):
    """Formata nÃºmero como R$ 1.234,56"""
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"




def calcular_valor_corrigido(valor, data_inicio, data_fim, indice, aceitar_negativos):

    # cálculo fictício só para validar a API
    dias = (data_fim - data_inicio).days
    fator = 1 + (0.01 * (dias / 365))  # 1% ao ano fake
    return round(valor * fator, 2)


def indice_existe_no_periodo(indice: str, data_inicio: str, data_fim: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1
        FROM valores
        WHERE indice = ?
          AND data >= ?
          AND data <= ?
        LIMIT 1
    """, (indice, data_inicio, data_fim))

    existe = cursor.fetchone() is not None
    conn.close()

    return existe
