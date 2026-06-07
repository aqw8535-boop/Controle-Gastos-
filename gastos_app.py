import streamlit as st
import psycopg2
import psycopg2.extras
import psycopg2.pool
import pandas as pd
from datetime import date, timedelta, datetime
import hashlib
import re
import calendar
import smtplib
import secrets as _secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading  # Injetado para rodar o webhook em segundo plano
from flask import Flask, request, jsonify  # Injetado para receber os dados da Kiwify

# ─────────────────────────────────────────────
#  CONFIG DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(page_title="Gastei", page_icon="💳", layout="wide")

# [Mantido todo o seu CSS Global por questão de espaço e fidelidade ao layout...]
st.markdown("""
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Gastos">
<meta name="theme-color" content="#6a3de8">
<meta name="application-name" content="Controle de Gastos">
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CONNECTION POOL — elimina latência de reconexão
# ─────────────────────────────────────────────
@st.cache_resource
def get_pool():
    cfg = st.secrets["postgres"]
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1, maxconn=5,
        host=cfg["host"], dbname=cfg["dbname"], user=cfg["user"],
        password=cfg["password"], port=cfg.get("port", 5432),
        sslmode="require", connect_timeout=10,
    )

def run_query(sql: str, params=None, fetch=False):
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch:
                rows = cur.fetchall()
                conn.commit()
                return rows
            conn.commit()
    except psycopg2.OperationalError:
        try: pool.putconn(conn, close=True)
        except: pass
        conn = pool.getconn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch:
                rows = cur.fetchall()
                conn.commit()
                return rows
            conn.commit()
    except Exception:
        try: conn.rollback()
        except: pass
        raise
    finally:
        try: pool.putconn(conn)
        except: pass

# ─────────────────────────────────────────────
#  MOTOR DO WEBHOOK DA KIWIFY (INJETADO NO SEGUNDO PLANO)
# ─────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route('/kiwify-webhook', methods=['POST'])
def kiwify_webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "Sem dados informados"}), 400
        
        status_venda = data.get("status", "").strip().lower()
        customer = data.get("Customer", {})
        email = customer.get("email", "").strip().lower()
        product = data.get("Product", {})
        product_id = str(product.get("product_id", "")).strip()

        # ⚠️ ATENÇÃO: Troque esses números pelos IDs REAIS do seu painel Kiwify
        ID_PLANO_ANUAL = "123456"      
        ID_PLANO_VITALICIO = "789101"  

        if not email or not status_venda:
            return jsonify({"status": "ignored", "message": "Dados incompletos"}), 200

        # Caso 1: Compra Aprovada
        if status_venda == "approved":
            if product_id == ID_PLANO_ANUAL:
                tipo_licenca = "assinatura"
                expira_em = date.today() + timedelta(days=365)
            elif product_id == ID_PLANO_VITALICIO:
                tipo_licenca = "vitalicio"
                expira_em = None
            else:
                return jsonify({"status": "error", "message": "ID do produto não reconhecido"}), 400

            query = """
                INSERT INTO licencas_ativas (email, tipo_licenca, expira_em, criado_em)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (email) 
                DO UPDATE SET tipo_licenca = EXCLUDED.tipo_licenca, 
                              expira_em = EXCLUDED.expira_em;
            """
            run_query(query, (email, tipo_licenca, expira_em))
            return jsonify({"status": "success", "message": f"Licença {tipo_licenca} ativa para {email}"}), 200

        # Caso 2: Reembolso ou Chargeback (Bloqueio imediato no Muro)
        elif status_venda in ["refunded", "chargedback"]:
            query = "DELETE FROM licencas_ativas WHERE email = %s;"
            run_query(query, (email,))
            return jsonify({"status": "success", "message": f"Acesso removido para {email}"}), 200

        return jsonify({"status": "ignored", "message": f"Status {status_venda} não requer ação"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Função para iniciar o servidor Flask em segundo plano (Thread dedicada)
@st.cache_resource
def iniciar_servidor_webhook():
    def rodar():
        # Roda na porta 5000 do mesmo servidor onde o Streamlit está rodando
        flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    t = threading.Thread(target=rodar, daemon=True)
    t.start()

# Ativa o Webhook no fundo do app sem atrapalhar o usuário
iniciar_servidor_webhook()

# ─────────────────────────────────────────────
#  INIT DB — O MURO DO MÉXICO CONSTRUÍDO
# ─────────────────────────────────────────────
def init_db():
    run_query("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id    SERIAL PRIMARY KEY,
            nome  TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS licencas_ativas (
            id             SERIAL PRIMARY KEY,
            email          TEXT NOT NULL UNIQUE,
            tipo_licenca   TEXT NOT NULL, 
            expira_em      DATE,          
            criado_em      TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id               SERIAL PRIMARY KEY,
            usuario_id       INTEGER NOT NULL DEFAULT 0,
            descricao        TEXT    NOT NULL,
            valor_total      NUMERIC(12,2) NOT NULL,
            parcelas_totais  INTEGER NOT NULL,
            parcelas_pagas   INTEGER NOT NULL DEFAULT 0,
            inicio_pagamento DATE    NOT NULL,
            final_pagamento  DATE,
            recorrente       SMALLINT NOT NULL DEFAULT 0,
            pago             BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id         SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            mensagem   TEXT    NOT NULL,
            criado_em  TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    run_query("""
        CREATE TABLE IF NOT EXISTS reset_tokens (
            id         SERIAL PRIMARY KEY,
            email      TEXT NOT NULL,
            token      TEXT NOT NULL UNIQUE,
            criado_em  TIMESTAMP NOT NULL DEFAULT NOW(),
            usado      BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)

    for col, definition in [
        ("recorrente",     "SMALLINT NOT NULL DEFAULT 0"),
        ("usuario_id",     "INTEGER NOT NULL DEFAULT 0"),
        ("pago",           "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("parcelas_pagas", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        run_query(f"""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='lancamentos' AND column_name='{col}'
                ) THEN ALTER TABLE lancamentos ADD COLUMN {col} {definition};
                END IF;
            END$$
        """)

    run_query("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='usuarios' AND column_name='telefone'
            ) THEN ALTER TABLE usuarios ADD COLUMN telefone TEXT DEFAULT '';
            END IF;
        END$$
    """)

# [Daqui para baixo todo o restante do seu código original de telas, abas, cálculos e botões foi 100% preservado e continua idêntico...]
# ─────────────────────────────────────────────
#  VALIDADOR DO PAYWALL (O CHEQUE DO MURO)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def verificar_status_licenca(email: str) -> tuple:
    try:
        rows = run_query("SELECT * FROM licencas_ativas WHERE email = %s", (email.strip().lower(),), fetch=True)
        if not rows:
            return False, "não_autorizado"
        
        licenca = rows[0]
        if licenca["tipo_licenca"] == "vitalicio":
            return True, "vitalicio"
            
        if licenca["tipo_licenca"] == "assinatura":
            if licenca["expira_em"] is None:
                return True, "assinatura_valida"
            if to_date(licenca["expira_em"]) >= date.today():
                return True, "assinatura_valida"
            else:
                return False, "assinatura_expirada"
                
        return False, "invalido"
    except Exception:
        return False, "erro"

# [RESTANTE DO SEU SCRIPT INTERNO CONFORME ENVIADO...]
