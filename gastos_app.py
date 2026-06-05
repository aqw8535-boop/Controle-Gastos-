import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import date, timedelta
import hashlib

# ─────────────────────────────────────────────
#  CONFIG DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(page_title="Controle de Gastos", page_icon="💳", layout="wide")


# ─────────────────────────────────────────────
#  PWA — META TAGS + MANIFEST INLINE + SERVICE WORKER
# ─────────────────────────────────────────────
st.markdown("""
<link rel="manifest" href="data:application/json;base64,eyJuYW1lIjoiQ29udHJvbGUgZGUgR2FzdG9zIiwic2hvcnRfbmFtZSI6Ikdhc3RvcyIsInN0YXJ0X3VybCI6Ii8iLCJkaXNwbGF5Ijoic3RhbmRhbG9uZSIsImJhY2tncm91bmRfY29sb3IiOiIjMGYwZjFhIiwidGhlbWVfY29sb3IiOiIjNmEzZGU4IiwiaWNvbnMiOlt7InNyYyI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQ0FBQUFBZ0NBWUFBQUQ4R08yekFBQUFBWGxXU0ZsekFBQXNFd0FBTEJNQi91WnF6QUFBQVR4SlJFRlVPTm9yMVYyN2tpUUEvUi9QQUVYZjBjN2ZZZ29VQkxXUXBuY1hSQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQT09Iiwic2l6ZXMiOiIxOTJ4MTkyIiwidHlwZSI6ImltYWdlL3BuZyJ9XX0=">

<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Gastos">
<meta name="theme-color" content="#6a3de8">
<meta name="application-name" content="Controle de Gastos">

<style>
  /* Remove barra de endereço no standalone */
  @media all and (display-mode: standalone) {
    body { margin-top: env(safe-area-inset-top); }
  }
</style>

<script>
  // Registra service worker para funcionar offline e ser instalável
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function() {
      const swCode = `
        const CACHE = "gastos-v1";
        self.addEventListener("install", e => {
          self.skipWaiting();
        });
        self.addEventListener("activate", e => {
          e.waitUntil(caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
          ));
        });
        self.addEventListener("fetch", e => {
          e.respondWith(
            fetch(e.request).catch(() => caches.match(e.request))
          );
        });
      `;
      const blob = new Blob([swCode], {type: "application/javascript"});
      const swUrl = URL.createObjectURL(blob);
      navigator.serviceWorker.register(swUrl).catch(() => {});
    });
  }

  // Banner de instalação Android (evento beforeinstallprompt)
  let deferredPrompt;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    const btn = document.getElementById("pwa-install-btn");
    if (btn) btn.style.display = "flex";
  });

  function installPWA() {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(() => {
        deferredPrompt = null;
        const btn = document.getElementById("pwa-install-btn");
        if (btn) btn.style.display = "none";
      });
    }
  }

  window.addEventListener("appinstalled", () => {
    const btn = document.getElementById("pwa-install-btn");
    if (btn) btn.style.display = "none";
  });
</script>

<!-- Botão de instalação Android (aparece só quando disponível) -->
<div id="pwa-install-btn" style="
  display: none;
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 9999;
  background: linear-gradient(135deg, #6a3de8, #9b8dff);
  color: white; border: none; border-radius: 999px;
  padding: 14px 28px; cursor: pointer;
  font-family: Sora, sans-serif; font-size: 15px; font-weight: 600;
  box-shadow: 0 6px 30px rgba(106,61,232,0.55);
  align-items: center; gap: 10px; white-space: nowrap;
  animation: floatin 2s ease-in-out infinite;
" onclick="installPWA()">
  💳 Instalar app na tela inicial
</div>

<style>
@keyframes floatin {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50%       { transform: translateX(-50%) translateY(-6px); }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CSS GLOBAL
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    min-height: 100vh;
}

h1 {
    font-family: 'Sora', sans-serif !important; font-weight: 700 !important;
    background: linear-gradient(90deg, #e2c4f0, #9b8dff, #64b5f6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
}
h2, h3 { font-family: 'Sora', sans-serif !important; color: #c9d1f0 !important; }

/* ── TELA DE LOGIN ── */
.login-wrap {
    max-width: 460px; margin: 60px auto 0;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(155,141,255,0.2);
    border-radius: 24px; padding: 48px 40px;
    box-shadow: 0 8px 60px rgba(106,61,232,0.25);
    backdrop-filter: blur(12px);
}
.login-logo  { text-align:center; font-size:52px; margin-bottom:8px; }
.login-title {
    text-align:center; font-size:26px; font-weight:700;
    background: linear-gradient(90deg, #e2c4f0, #9b8dff, #64b5f6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}
.login-sub { text-align:center; font-size:13px; color:#6b7280; margin-bottom:32px; }

/* ── CARDS DASHBOARD ── */
.total-card {
    background: linear-gradient(135deg, #6a3de8 0%, #9b8dff 100%);
    border-radius: 20px; padding: 32px 40px;
    box-shadow: 0 8px 40px rgba(106,61,232,0.45); margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between;
}
.total-label { font-size:13px; font-weight:600; letter-spacing:2px; text-transform:uppercase; color:rgba(255,255,255,0.75); margin-bottom:6px; }
.total-value { font-family:'JetBrains Mono',monospace; font-size:42px; font-weight:700; color:#fff; letter-spacing:-1px; }
.total-icon  { font-size:56px; opacity:0.5; }

.parcela-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
    border: 1px solid rgba(100,181,246,0.25); border-radius: 20px; padding: 24px 32px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3); margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between;
}
.parcela-label { font-size:13px; font-weight:600; letter-spacing:2px; text-transform:uppercase; color:rgba(100,181,246,0.75); margin-bottom:6px; }
.parcela-value { font-family:'JetBrains Mono',monospace; font-size:34px; font-weight:700; color:#64b5f6; }

/* ── FORMULÁRIO ── */
.form-section {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px; padding: 28px 32px; margin-bottom: 32px; backdrop-filter: blur(10px);
}

/* ── LINHAS DA TABELA ── */
.lancamento-row {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 18px 24px; margin-bottom: 10px;
    display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 0.5fr;
    align-items: center; transition: all 0.2s;
}
.lancamento-row:hover { background: rgba(155,141,255,0.08); border-color: rgba(155,141,255,0.3); }
.lancamento-row.fixa  { border-color: rgba(251,191,36,0.25); }
.lancamento-row.fixa:hover { background: rgba(251,191,36,0.06); border-color: rgba(251,191,36,0.45); }

/* ── INPUTS ── */
label { color:#a0aec0 !important; font-size:13px !important; font-weight:600 !important; letter-spacing:0.5px !important; }
input, textarea,
.stTextInput input, .stNumberInput input, .stDateInput input,
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input {
    border-radius: 10px !important; color: #1a1a2e !important;
    font-family: 'Sora', sans-serif !important; font-size: 15px !important;
    caret-color: #6a3de8 !important;
}
input::placeholder, textarea::placeholder { color: rgba(80,80,120,0.5) !important; }
.stCheckbox label { color:#c9d1f0 !important; font-size:14px !important; font-weight:600 !important; }

/* ── BOTÕES ── */
.stButton > button {
    background: linear-gradient(135deg, #6a3de8, #9b8dff) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important; font-weight: 600 !important;
    font-size: 14px !important; padding: 12px 28px !important; width: 100% !important;
    letter-spacing: 0.5px !important; box-shadow: 0 4px 20px rgba(106,61,232,0.4) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(106,61,232,0.6) !important; }

.logout-btn > button {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    font-size: 12px !important; padding: 6px 14px !important;
    box-shadow: none !important; width: auto !important; color: #9ca3af !important;
}
.logout-btn > button:hover { background: rgba(255,80,80,0.12) !important; color: #fca5a5 !important; border-color: rgba(255,80,80,0.3) !important; }

/* ── BADGES ── */
.badge-parcelas { background:rgba(106,61,232,0.25); border:1px solid rgba(155,141,255,0.4); color:#c4b5fd; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-vence    { background:rgba(100,181,246,0.15); border:1px solid rgba(100,181,246,0.35); color:#90cdf4; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-fixa     { background:rgba(251,191,36,0.15); border:1px solid rgba(251,191,36,0.4); color:#fbbf24; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }

hr { border-color:rgba(255,255,255,0.07) !important; margin:28px 0 !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1100px; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(155,141,255,0.4); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CONEXÃO POSTGRESQL (Supabase)
#  Credenciais lidas exclusivamente de st.secrets
# ─────────────────────────────────────────────
@st.cache_resource
def get_conn():
    cfg = st.secrets["postgres"]
    conn = psycopg2.connect(
        host=cfg["host"],
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        port=cfg.get("port", 5432),
        sslmode="require",
        connect_timeout=10,
    )
    conn.autocommit = False
    return conn

def run_query(sql: str, params=None, fetch=False):
    """Executa SQL com reconexão automática em caso de conexão perdida."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch:
                rows = cur.fetchall()
                conn.commit()
                return rows
            conn.commit()
    except psycopg2.OperationalError:
        # Limpa o cache e reconecta uma vez
        get_conn.clear()
        conn = get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch:
                rows = cur.fetchall()
                conn.commit()
                return rows
            conn.commit()

# ─────────────────────────────────────────────
#  INICIALIZAÇÃO DAS TABELAS
# ─────────────────────────────────────────────
def init_db():
    # Tabela Usuarios
    run_query("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id     SERIAL PRIMARY KEY,
            nome   TEXT   NOT NULL,
            email  TEXT   NOT NULL UNIQUE,
            senha  TEXT   NOT NULL
        )
    """)
    # Tabela Lancamentos
    run_query("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id               SERIAL PRIMARY KEY,
            usuario_id       INTEGER NOT NULL DEFAULT 0,
            descricao        TEXT    NOT NULL,
            valor_total      NUMERIC(12,2) NOT NULL,
            parcelas_totais  INTEGER NOT NULL,
            inicio_pagamento DATE    NOT NULL,
            final_pagamento  DATE,
            recorrente       SMALLINT NOT NULL DEFAULT 0
        )
    """)
    # Migrações seguras — adiciona colunas se ainda não existirem
    for col, definition in [
        ("recorrente",  "SMALLINT NOT NULL DEFAULT 0"),
        ("usuario_id",  "INTEGER NOT NULL DEFAULT 0"),
    ]:
        run_query(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='lancamentos' AND column_name='{col}'
                ) THEN
                    ALTER TABLE lancamentos ADD COLUMN {col} {definition};
                END IF;
            END$$
        """)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()

# ── Usuários ──────────────────────────────────
def criar_usuario(nome, email, senha):
    try:
        run_query(
            "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)",
            (nome.strip(), email.strip().lower(), hash_senha(senha))
        )
        return True, "ok"
    except psycopg2.errors.UniqueViolation:
        get_conn().rollback()
        return False, "Este e-mail já está cadastrado."
    except Exception as e:
        get_conn().rollback()
        return False, str(e)

def autenticar_usuario(email, senha):
    rows = run_query(
        "SELECT id, nome FROM usuarios WHERE email = %s AND senha = %s",
        (email.strip().lower(), hash_senha(senha)),
        fetch=True
    )
    return (rows[0]["id"], rows[0]["nome"]) if rows else None

# ── Lançamentos ───────────────────────────────
def inserir_lancamento(uid, descricao, valor_total, parcelas_totais, inicio, final, recorrente):
    run_query("""
        INSERT INTO lancamentos
            (usuario_id, descricao, valor_total, parcelas_totais,
             inicio_pagamento, final_pagamento, recorrente)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        uid, descricao, float(valor_total), parcelas_totais,
        inicio,
        final if final else None,
        1 if recorrente else 0
    ))

def carregar_lancamentos(uid) -> pd.DataFrame:
    rows = run_query(
        "SELECT * FROM lancamentos WHERE usuario_id = %s ORDER BY id DESC",
        (uid,), fetch=True
    )
    if not rows:
        return pd.DataFrame(columns=[
            "id","usuario_id","descricao","valor_total","parcelas_totais",
            "inicio_pagamento","final_pagamento","recorrente"
        ])
    return pd.DataFrame([dict(r) for r in rows])

def excluir_lancamento(id_):
    run_query("DELETE FROM lancamentos WHERE id = %s", (id_,))

# ─────────────────────────────────────────────
#  LÓGICA DE CÁLCULO
# ─────────────────────────────────────────────
def calcular_parcelas_a_pagar(final_pagamento) -> int:
    hoje  = date.today()
    final = final_pagamento if isinstance(final_pagamento, date) else (
        final_pagamento.date() if hasattr(final_pagamento, "date") else date.fromisoformat(str(final_pagamento))
    )
    return max(0, round(((final - hoje).days / 30.4375) + 0.5))

def calcular_proxima_parcela(final_pagamento, parcelas_a_pagar: int) -> date:
    final = final_pagamento if isinstance(final_pagamento, date) else (
        final_pagamento.date() if hasattr(final_pagamento, "date") else date.fromisoformat(str(final_pagamento))
    )
    return final - timedelta(days=(parcelas_a_pagar - 1) * 30.4375)

def calcular_proxima_recorrente(inicio_pagamento) -> date:
    hoje   = date.today()
    inicio = inicio_pagamento if isinstance(inicio_pagamento, date) else (
        inicio_pagamento.date() if hasattr(inicio_pagamento, "date") else date.fromisoformat(str(inicio_pagamento))
    )
    dia = inicio.day
    def montar(ano, mes):
        try:    return date(ano, mes, dia)
        except: return date(ano, mes, (date(ano, mes % 12 + 1, 1) - timedelta(days=1)).day)
    c = montar(hoje.year, hoje.month)
    if c < hoje:
        mes = hoje.month % 12 + 1
        ano = hoje.year + (1 if hoje.month == 12 else 0)
        c   = montar(ano, mes)
    return c

def calcular_valor_parcela(valor_total: float, parcelas_totais: int) -> float:
    return float(valor_total) / parcelas_totais if parcelas_totais > 0 else 0.0

def calcular_gasto_mensal(df: pd.DataFrame) -> float:
    total = 0.0
    for _, row in df.iterrows():
        if int(row.get("recorrente", 0)) == 1:
            total += float(row["valor_total"])
        elif row["final_pagamento"] is not None and str(row["final_pagamento"]) not in ("None", ""):
            final = row["final_pagamento"] if isinstance(row["final_pagamento"], date) else (
                row["final_pagamento"].date() if hasattr(row["final_pagamento"], "date")
                else date.fromisoformat(str(row["final_pagamento"]))
            )
            if calcular_parcelas_a_pagar(final) > 0:
                total += calcular_valor_parcela(row["valor_total"], row["parcelas_totais"])
    return total

# ─────────────────────────────────────────────
#  INICIALIZAÇÃO
# ─────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"❌ Erro ao conectar ao banco de dados: {e}")
    st.info("Verifique se os secrets do Supabase estão configurados corretamente em Settings → Secrets.")
    st.stop()

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "usuario_id"   not in st.session_state: st.session_state.usuario_id   = None
if "usuario_nome" not in st.session_state: st.session_state.usuario_nome = None

# ═════════════════════════════════════════════
#  TELA DE LOGIN / CADASTRO
# ═════════════════════════════════════════════
if st.session_state.usuario_id is None:

    _, col_center, _ = st.columns([1, 1.6, 1])
    with col_center:
        st.markdown("""
        <div class="login-wrap">
            <div class="login-logo">💳</div>
            <div class="login-title">Controle de Gastos</div>
            <div class="login-sub">Parcelamentos · Contas Fixas · Multi-usuário</div>
        </div>
        """, unsafe_allow_html=True)

        aba_login, aba_cadastro = st.tabs(["🔑  Entrar", "✨  Criar Conta"])

        with aba_login:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            email_login = st.text_input("E-mail", key="login_email", placeholder="seu@email.com")
            senha_login = st.text_input("Senha", type="password", key="login_senha", placeholder="••••••••")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("Entrar →", key="btn_login"):
                if not email_login or not senha_login:
                    st.error("Preencha e-mail e senha.")
                else:
                    resultado = autenticar_usuario(email_login, senha_login)
                    if resultado:
                        st.session_state.usuario_id   = resultado[0]
                        st.session_state.usuario_nome = resultado[1]
                        st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos.")

        with aba_cadastro:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            nome_cad   = st.text_input("Seu nome",       key="cad_nome",   placeholder="João Silva")
            email_cad  = st.text_input("E-mail",         key="cad_email",  placeholder="seu@email.com")
            senha_cad  = st.text_input("Senha", type="password", key="cad_senha",  placeholder="Mínimo 6 caracteres")
            senha_cad2 = st.text_input("Confirmar senha",type="password", key="cad_senha2", placeholder="Repita a senha")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("Criar minha conta →", key="btn_cadastro"):
                if not all([nome_cad, email_cad, senha_cad, senha_cad2]):
                    st.error("Preencha todos os campos.")
                elif len(senha_cad) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres.")
                elif senha_cad != senha_cad2:
                    st.error("As senhas não conferem.")
                else:
                    ok, msg = criar_usuario(nome_cad, email_cad, senha_cad)
                    if ok: st.success("Conta criada! Faça login na aba ao lado.")
                    else:  st.error(msg)

    st.stop()

# ═════════════════════════════════════════════
#  APP PRINCIPAL
# ═════════════════════════════════════════════
uid = st.session_state.usuario_id

# ── Cabeçalho + logout ────────────────────────
col_titulo, col_usuario, col_logout = st.columns([5, 2, 1])
with col_titulo:
    st.markdown("# 💳 Controle de Gastos")
    st.markdown("<p style='color:#6b7280; margin-top:-12px; margin-bottom:28px;'>Parcelamentos · Contas Fixas · Vencimentos automáticos</p>", unsafe_allow_html=True)
with col_usuario:
    st.markdown(f"""
    <div style='text-align:right; padding-top:18px; font-size:13px; color:#9ca3af; line-height:1.4;'>
        Olá, <strong style='color:#c4b5fd'>{st.session_state.usuario_nome}</strong> 👋
    </div>""", unsafe_allow_html=True)
with col_logout:
    st.markdown("<div style='padding-top:14px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("Sair 🚪", key="btn_logout"):
        st.session_state.usuario_id   = None
        st.session_state.usuario_nome = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Dashboard ─────────────────────────────────
df = carregar_lancamentos(uid)
total_saidas = df["valor_total"].astype(float).sum() if not df.empty else 0.0
gasto_mensal = calcular_gasto_mensal(df) if not df.empty else 0.0

col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f"""
    <div class="total-card">
        <div>
            <div class="total-label">Total de Saídas (Soma dos Valores)</div>
            <div class="total-value">R$ {total_saidas:,.2f}</div>
        </div>
        <div class="total-icon">📊</div>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown(f"""
    <div class="parcela-card">
        <div>
            <div class="parcela-label">Comprometido Este Mês</div>
            <div class="parcela-value">R$ {gasto_mensal:,.2f}</div>
        </div>
        <div style="font-size:48px; opacity:0.4;">📅</div>
    </div>""", unsafe_allow_html=True)

# ── Formulário novo lançamento ────────────────
st.markdown("### ➕ Novo Lançamento")
with st.container():
    st.markdown('<div class="form-section">', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        descricao = st.text_input("O que comprou / Pagou", placeholder="Ex: iPhone 16, Aluguel, Internet...")
    with col2:
        valor_total = st.number_input("Valor Total (R$)", min_value=0.01, step=0.01, format="%.2f")

    is_recorrente = st.checkbox("🔁  Conta Fixa / Recorrente  (sem data de término — Aluguel, Pensão, Internet...)")

    if is_recorrente:
        col4, _ = st.columns([1, 2])
        with col4:
            inicio_pagamento = st.date_input("Dia de Vencimento (Data de Início)", value=date.today(), format="DD/MM/YYYY")
        parcelas_totais = 0
        final_pagamento = None
        if descricao and valor_total > 0:
            proxima_rec = calcular_proxima_recorrente(inicio_pagamento)
            st.markdown("<hr>", unsafe_allow_html=True)
            pc1, pc2, pc3 = st.columns(3)
            with pc1: st.markdown(f"**Valor mensal:** `R$ {valor_total:,.2f}`")
            with pc2: st.markdown("**Tipo:** `🔁 Recorrente (sem fim)`")
            with pc3: st.markdown(f"**Próximo vencimento:** `{proxima_rec.strftime('%d/%m/%Y')}`")
    else:
        col3, col4, col5 = st.columns(3)
        with col3:
            parcelas_totais = st.number_input("Número de Parcelas", min_value=1, max_value=360, step=1, value=1)
        with col4:
            inicio_pagamento = st.date_input("Data de Início", value=date.today(), format="DD/MM/YYYY")
        with col5:
            dias_sug = int((parcelas_totais - 1) * 30.4375)
            final_pagamento = st.date_input("Data Final do Pagamento",
                                            value=inicio_pagamento + timedelta(days=dias_sug),
                                            format="DD/MM/YYYY")
        if descricao and valor_total > 0:
            parc_prev = calcular_parcelas_a_pagar(final_pagamento)
            prox_prev = calcular_proxima_parcela(final_pagamento, parc_prev) if parc_prev > 0 else None
            val_p     = calcular_valor_parcela(valor_total, parcelas_totais)
            st.markdown("<hr>", unsafe_allow_html=True)
            pc1, pc2, pc3 = st.columns(3)
            with pc1: st.markdown(f"**Valor por parcela:** `R$ {val_p:.2f}`")
            with pc2: st.markdown(f"**Parcelas a pagar hoje:** `{parc_prev}x`")
            with pc3:
                if prox_prev: st.markdown(f"**Próximo vencimento:** `{prox_prev.strftime('%d/%m/%Y')}`")
                else:         st.markdown("**Próximo vencimento:** `Quitado ✅`")

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("💾 Salvar Lançamento"):
            if not descricao.strip():
                st.error("⚠️ Preencha a descrição do gasto.")
            elif not is_recorrente and final_pagamento < inicio_pagamento:
                st.error("⚠️ A data final não pode ser anterior à data de início.")
            else:
                inserir_lancamento(uid, descricao.strip(), valor_total, parcelas_totais,
                                   inicio_pagamento, final_pagamento, is_recorrente)
                st.success(f"✅ **{descricao}** salvo com sucesso!")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ── Histórico de lançamentos ──────────────────
st.markdown("### 📋 Histórico de Lançamentos")
df = carregar_lancamentos(uid)

if df.empty:
    st.markdown("""
    <div style='text-align:center; padding:60px 20px; color:#4b5563;'>
        <div style='font-size:48px; margin-bottom:12px;'>📭</div>
        <div style='font-size:16px;'>Nenhum lançamento ainda.<br>Adicione seu primeiro gasto acima!</div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style='display:grid; grid-template-columns:2fr 1fr 1fr 1fr 0.5fr;
                padding:10px 24px; margin-bottom:4px;
                font-size:11px; font-weight:700; letter-spacing:1.5px;
                text-transform:uppercase; color:#6b7280;'>
        <span>Descrição</span><span>Valor</span>
        <span>Próximo Vencimento</span><span>Situação</span><span></span>
    </div>""", unsafe_allow_html=True)

    for _, row in df.iterrows():
        eh_fixa = int(row.get("recorrente", 0)) == 1

        if eh_fixa:
            inicio = row["inicio_pagamento"]
            if hasattr(inicio, "date"): inicio = inicio.date()
            elif not isinstance(inicio, date): inicio = date.fromisoformat(str(inicio))
            proxima      = calcular_proxima_recorrente(inicio)
            status_badge = f'<span class="badge-vence">📅 {proxima.strftime("%d/%m/%Y")}</span>'
            parc_badge   = '<span class="badge-fixa">🔁 Conta Fixa</span>'
            valor_label  = f"R$ {float(row['valor_total']):,.2f} / mês"
            sub_info     = f"Vence todo dia {inicio.day:02d} · Início: {inicio.strftime('%d/%m/%Y')}"
            row_class    = "lancamento-row fixa"
            cor_valor    = "#fbbf24"
            label_tipo   = "por mês"
        else:
            fp = row["final_pagamento"]
            if fp is not None and str(fp) not in ("None", ""):
                final = fp.date() if hasattr(fp, "date") else (fp if isinstance(fp, date) else date.fromisoformat(str(fp)))
            else:
                final = None
            parc_rest = calcular_parcelas_a_pagar(final) if final else 0
            val_p     = calcular_valor_parcela(row["valor_total"], row["parcelas_totais"])
            if parc_rest > 0:
                proxima = calcular_proxima_parcela(final, parc_rest)
                status_badge = f'<span class="badge-vence">📅 {proxima.strftime("%d/%m/%Y")}</span>'
                parc_badge   = f'<span class="badge-parcelas">🔢 {parc_rest}x restantes</span>'
            else:
                status_badge = '<span class="badge-vence" style="background:rgba(52,211,153,0.1);border-color:rgba(52,211,153,0.4);color:#6ee7b7;">✅ Quitado</span>'
                parc_badge   = '<span class="badge-parcelas" style="background:rgba(52,211,153,0.1);border-color:rgba(52,211,153,0.4);color:#6ee7b7;">0x</span>'
            ip = row["inicio_pagamento"]
            ip = ip.date() if hasattr(ip,"date") else (ip if isinstance(ip,date) else date.fromisoformat(str(ip)))
            valor_label = f"R$ {val_p:,.2f}"
            sub_info    = f"Total: R$ {float(row['valor_total']):,.2f} · {row['parcelas_totais']}x · Início: {ip.strftime('%d/%m/%Y')}"
            row_class   = "lancamento-row"
            cor_valor   = "#a78bfa"
            label_tipo  = "por parcela"

        col_row, col_del = st.columns([11, 1])
        with col_row:
            st.markdown(f"""
            <div class="{row_class}">
                <div>
                    <div style="font-weight:600; color:#e2e8f0; font-size:15px;">{row['descricao']}</div>
                    <div style="font-size:12px; color:#6b7280; margin-top:2px;">{sub_info}</div>
                </div>
                <div style="font-family:'JetBrains Mono',monospace; font-weight:700;
                            color:{cor_valor}; font-size:16px;">
                    {valor_label}
                    <div style="font-size:11px; color:#6b7280; font-weight:400;">{label_tipo}</div>
                </div>
                <div>{status_badge}</div>
                <div>{parc_badge}</div>
            </div>""", unsafe_allow_html=True)
        with col_del:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_{row['id']}", help="Excluir lançamento"):
                excluir_lancamento(row["id"])
                st.rerun()

    fixas  = sum(1 for _, r in df.iterrows() if int(r.get("recorrente", 0)) == 1)
    ativos = sum(1 for _, r in df.iterrows()
                 if int(r.get("recorrente", 0)) == 0 and r["final_pagamento"] is not None
                 and str(r["final_pagamento"]) not in ("None","")
                 and calcular_parcelas_a_pagar(
                     r["final_pagamento"].date() if hasattr(r["final_pagamento"],"date")
                     else date.fromisoformat(str(r["final_pagamento"]))
                 ) > 0)
    st.markdown(f"""
    <div style='margin-top:20px; padding:14px 24px;
                background:rgba(255,255,255,0.03); border-radius:12px;
                font-size:13px; color:#6b7280; display:flex; gap:24px; flex-wrap:wrap;'>
        <span>📦 <strong style='color:#9ca3af'>{len(df)}</strong> lançamentos</span>
        <span>🔁 <strong style='color:#fbbf24'>{fixas}</strong> contas fixas</span>
        <span>🔄 <strong style='color:#9ca3af'>{ativos}</strong> parcelamentos ativos</span>
        <span>💰 Total acumulado: <strong style='color:#a78bfa'>R$ {df['valor_total'].astype(float).sum():,.2f}</strong></span>
    </div>""", unsafe_allow_html=True)
