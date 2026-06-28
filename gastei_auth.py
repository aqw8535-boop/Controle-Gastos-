# gastei_auth.py
# ─────────────────────────────────────────────────────────
#  Módulo de autenticação OAuth e controle de trial — Gastei
#  Importe em gastos_app.py com: from gastei_auth import *
# ─────────────────────────────────────────────────────────

import streamlit as st
import requests
import time
import jwt
import smtplib
from datetime import date, timedelta
from urllib.parse import urlencode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False


# ══════════════════════════════════════════
#  CONSTANTES (lidas dos secrets)
# ══════════════════════════════════════════
def _s(section, key, default=""):
    try:
        return st.secrets.get(section, {}).get(key, default)
    except Exception:
        return default

TRIAL_DIAS         = int(_s("trial", "dias") or 7)
KIWIFY_URL         = _s("kiwify", "checkout_url") or "https://pay.kiwify.com.br/CtPYesz"
WHATSAPP_SUPORTE   = _s("kiwify", "whatsapp_suporte") or "5567991158892"
GOOGLE_CLIENT_ID   = _s("google_oauth", "client_id")
GOOGLE_SECRET      = _s("google_oauth", "client_secret")
GOOGLE_REDIRECT    = _s("google_oauth", "redirect_uri")
APPLE_CLIENT_ID    = _s("apple_oauth", "client_id")
APPLE_TEAM_ID      = _s("apple_oauth", "team_id")
APPLE_KEY_ID       = _s("apple_oauth", "key_id")
APPLE_PRIVATE_KEY  = _s("apple_oauth", "private_key")
APPLE_REDIRECT     = _s("apple_oauth", "redirect_uri")

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"
APPLE_AUTH_URL   = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL  = "https://appleid.apple.com/auth/token"


# ══════════════════════════════════════════
#  SEÇÃO A — GOOGLE OAUTH
# ══════════════════════════════════════════

def google_get_auth_url(state):
    # Puxa direto do secrets configurado no painel do Streamlit Cloud
    client_id = st.secrets["google_oauth"]["client_id"]
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
    
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id.strip()}&"  # .strip() remove qualquer espaço invisível bizarro
        f"redirect_uri={redirect_uri.strip()}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"state={state}"
    )
    return url

def google_exchange_code(code: str) -> dict | None:
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"
    
    try:
        # Puxa rigorosamente as mesmas chaves do secrets
        client_id     = st.secrets["google_oauth"]["client_id"]
        client_secret = st.secrets["google_oauth"]["client_secret"]
        redirect_uri  = st.secrets["google_oauth"]["redirect_uri"]

        token_resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     client_id.strip(),
            "client_secret": client_secret.strip(),
            "redirect_uri":  redirect_uri.strip(),
            "grant_type":    "authorization_code",
        }, timeout=10)
        token_resp.raise_for_status()
        tokens = token_resp.json()

        user_resp = requests.get(GOOGLE_USERINFO, headers={
            "Authorization": f"Bearer {tokens['access_token']}"
        }, timeout=10)
        user_resp.raise_for_status()
        user = user_resp.json()

        return {
            "provider_id": user.get("sub", ""),
            "email":       user.get("email", "").lower().strip(),
            "nome":        user.get("name") or user.get("given_name") or "Usuário Google",
            "avatar_url":  user.get("picture", ""),
            "provedor":    "google",
        }
    except Exception as e:
        st.error(f"❌ Erro no OAuth Google (Exchange): {e}")
        return None
# ══════════════════════════════════════════
#  SEÇÃO B — APPLE SIGN-IN
# ══════════════════════════════════════════

def _gerar_apple_client_secret() -> str:
    """
    Gera o JWT client_secret exigido pela Apple.
    Válido por 6 meses, assinado com a chave privada ES256.
    """
    if not _CRYPTO_OK:
        raise RuntimeError("Instale: pip install cryptography")

    now = int(time.time())
    private_key = serialization.load_pem_private_key(
        APPLE_PRIVATE_KEY.encode(), password=None, backend=default_backend()
    )
    payload = {
        "iss": APPLE_TEAM_ID,
        "iat": now,
        "exp": now + (86400 * 180),
        "aud": "https://appleid.apple.com",
        "sub": APPLE_CLIENT_ID,
    }
    return jwt.encode(
        payload, private_key,
        algorithm="ES256",
        headers={"kid": APPLE_KEY_ID}
    )


def apple_get_auth_url(state: str) -> str:
    """Gera a URL de autorização do Apple Sign-In."""
    params = {
        "client_id":     APPLE_CLIENT_ID,
        "redirect_uri":  APPLE_REDIRECT,
        "response_type": "code id_token",
        "response_mode": "form_post",
        "scope":         "name email",
        "state":         state,
    }
    return f"{APPLE_AUTH_URL}?{urlencode(params)}"


def apple_exchange_code(code: str, id_token: str = "") -> dict | None:
    """
    Troca o authorization code Apple pelos dados do usuário.
    A Apple só envia nome na PRIMEIRA autenticação.
    """
    try:
        client_secret = _gerar_apple_client_secret()
        token_resp = requests.post(APPLE_TOKEN_URL, data={
            "client_id":     APPLE_CLIENT_ID,
            "client_secret": client_secret,
            "code":          code,
            "grant_type":    "authorization_code",
            "redirect_uri":  APPLE_REDIRECT,
        }, timeout=10)
        token_resp.raise_for_status()
        tokens = token_resp.json()

        decoded = jwt.decode(
            tokens.get("id_token") or id_token,
            options={"verify_signature": False}
        )
        email = decoded.get("email", "").lower().strip()
        sub   = decoded.get("sub", "")

        return {
            "provider_id": sub,
            "email":       email,
            "nome":        decoded.get("name") or f"Usuário Apple",
            "avatar_url":  "",
            "provedor":    "apple",
        }
    except Exception as e:
        st.error(f"❌ Erro no Apple Sign-In: {e}")
        return None


# ══════════════════════════════════════════
#  SEÇÃO C — UPSERT DE USUÁRIO OAUTH
# ══════════════════════════════════════════

def upsert_usuario_oauth(run_query_fn, dados: dict) -> tuple[int, str] | None:
    """
    Cria ou localiza o usuário OAuth no banco.

    Estratégia de lookup (em ordem):
    1. provider_id  → login recorrente
    2. e-mail       → usuário criou conta manual antes; vincula o OAuth
    3. nenhum       → cria conta nova em status 'trial'

    Retorna (id, nome) ou None.
    """
    email       = dados["email"]
    provedor    = dados["provedor"]
    provider_id = dados["provider_id"]
    nome        = dados["nome"]
    avatar      = dados["avatar_url"]

    try:
            dados_usuario = google_exchange_code(_code)
            
            if dados_usuario and isinstance(dados_usuario, dict) and "email" in dados_usuario:
                
                # 🚀 CORREÇÃO AQUI: Passa a sua função de query (geralmente chamada de run_query ou executar_query)
                # e o dicionário de dados inteiro. Ela vai retornar o ID e o Nome do usuário.
                retorno_banco = upsert_usuario_oauth(run_query, dados_usuario)
                
                if retorno_banco:
                    usuario_id, usuario_nome = retorno_banco
                    
                    # Salva os dados corretos no session_state global
                    st.session_state.usuario_id = usuario_id
                    st.session_state.usuario_email = dados_usuario["email"]
                    st.session_state.usuario_nome = usuario_nome
                    
                    # Recarrega a página de forma limpa, agora 100% LOGADO!
                    st.rerun()
                else:
                    st.error("Erro ao registrar ou localizar sua conta no banco de dados.")
                
        except Exception as e:
            st.error(f"Erro crítico na autenticação: {e}")
    try:
        run_query_fn("""
            INSERT INTO licencas_ativas
              (email, tipo_licenca, expira_em, trial_usuario_id)
            VALUES (%s, 'trial', %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (email, expira, usuario_id))
    except Exception:
        pass


# ══════════════════════════════════════════
#  SEÇÃO D — MOTOR DE TRIAL
# ══════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def verificar_acesso_trial(usuario_id: int, _run_query_fn) -> dict:
    """
    Verifica o status de acesso do usuário logado.

    Retorna:
    {
        "acesso":         True | False,
        "status":         "trial" | "pago" | "vitalicio" | "expirado" | "erro",
        "dias_restantes": int,
        "expira_em":      date | None,
    }

    Cache de 60s para não bater no banco a cada clique.
    Ao mudar plano, chame verificar_acesso_trial.clear().
    """
    try:
        rows = _run_query_fn(
            """SELECT status_assinatura, trial_inicio,
                      trial_aviso_enviado, trial_expirou_email
               FROM usuarios WHERE id=%s""",
            (usuario_id,), fetch=True
        )
        if not rows:
            return {"acesso": False, "status": "erro", "dias_restantes": 0, "expira_em": None}

        u      = rows[0]
        status = u["status_assinatura"]

        if status in ("pago", "vitalicio", "assinatura_valida"):
            return {"acesso": True, "status": status, "dias_restantes": 999, "expira_em": None}

        if status == "trial":
            inicio = u["trial_inicio"]
            if hasattr(inicio, "date"):
                inicio = inicio.date()
            elif not isinstance(inicio, date):
                inicio = date.today()

            expira    = inicio + timedelta(days=TRIAL_DIAS)
            hoje      = date.today()
            restantes = (expira - hoje).days

            if restantes > 0:
                return {
                    "acesso":         True,
                    "status":         "trial",
                    "dias_restantes": restantes,
                    "expira_em":      expira,
                }
            else:
                return {
                    "acesso":         False,
                    "status":         "expirado",
                    "dias_restantes": 0,
                    "expira_em":      expira,
                }

        return {"acesso": False, "status": "invalido", "dias_restantes": 0, "expira_em": None}

    except Exception:
        return {"acesso": False, "status": "erro", "dias_restantes": 0, "expira_em": None}


def marcar_usuario_pago(run_query_fn, usuario_id: int) -> bool:
    """
    Promove o usuário para status 'pago'.
    Chame via webhook da Kiwify ou manualmente após confirmação de pagamento.
    """
    try:
        run_query_fn(
            "UPDATE usuarios SET status_assinatura='pago' WHERE id=%s",
            (usuario_id,)
        )
        verificar_acesso_trial.clear()
        return True
    except Exception:
        return False


# ══════════════════════════════════════════
#  SEÇÃO E — E-MAILS DE TRIAL
# ══════════════════════════════════════════

def _enviar_email_html(cfg: dict, destinatario: str, assunto: str, html: str) -> bool:
    """Envia e-mail HTML via SMTP. Reutiliza a config existente do projeto."""
    try:
        msg             = MIMEMultipart("alternative")
        msg["Subject"]  = assunto
        msg["From"]     = cfg["remetente"]
        msg["To"]       = destinatario
        msg.attach(MIMEText(html, "html"))
        porta = int(cfg.get("smtp_port", 587))
        if porta == 465:
            import ssl
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["smtp_host"], porta, context=ctx) as s:
                s.login(cfg["remetente"], cfg["senha_smtp"])
                s.sendmail(cfg["remetente"], destinatario, msg.as_string())
        else:
            with smtplib.SMTP(cfg["smtp_host"], porta, timeout=10) as s:
                s.ehlo(); s.starttls(); s.ehlo()
                s.login(cfg["remetente"], cfg["senha_smtp"])
                s.sendmail(cfg["remetente"], destinatario, msg.as_string())
        return True
    except Exception:
        return False


def enviar_email_aviso_trial(cfg: dict, destinatario: str, nome: str,
                             dias_restantes: int, kiwify_url: str) -> bool:
    """E-mail de aviso enviado 1 dia antes do trial expirar."""
    assunto = "⏰ Seu teste grátis termina amanhã — Gastei"
    html = f"""
    <div style="font-family:Sora,sans-serif;max-width:520px;margin:auto;
                background:#1a1a2e;border-radius:16px;padding:40px;color:#e8e4ff;">
      <div style="text-align:center;font-size:52px;margin-bottom:4px;">⏰</div>
      <h2 style="text-align:center;
                 background:linear-gradient(90deg,#fbbf24,#f97316);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 margin-bottom:8px;">Seu teste termina amanhã!</h2>
      <p style="color:#9ca3af;text-align:center;margin-bottom:28px;">
        Olá, <strong style="color:#e8e4ff;">{nome}</strong>!<br>
        Você está aproveitando o Gastei há {TRIAL_DIAS - dias_restantes} dias.
        Não perca o controle das suas finanças.
      </p>
      <div style="background:rgba(251,191,36,0.1);
                  border:1px solid rgba(251,191,36,0.35);
                  border-radius:12px;padding:20px;text-align:center;margin-bottom:28px;">
        <div style="font-size:48px;font-weight:800;color:#fbbf24;
                    font-family:'JetBrains Mono',monospace;">1 dia</div>
        <div style="color:#9ca3af;font-size:13px;margin-top:4px;">
          restante no seu teste grátis</div>
      </div>
      <a href="{kiwify_url}"
         style="display:block;background:linear-gradient(135deg,#6a3de8,#9b8dff);
                color:#fff;text-align:center;padding:16px;border-radius:12px;
                font-weight:700;font-size:16px;text-decoration:none;
                letter-spacing:0.5px;box-shadow:0 4px 20px rgba(106,61,232,0.4);">
        🔓 Continuar com Gastei Premium — R$ 24,90/mês
      </a>
      <p style="color:#6b7280;font-size:11px;text-align:center;margin-top:20px;">
        Sem fidelidade. Cancele quando quiser.<br>
        Suporte: finatechsuporte@gmail.com
      </p>
    </div>"""
    return _enviar_email_html(cfg, destinatario, assunto, html)


def enviar_email_trial_expirado(cfg: dict, destinatario: str, nome: str,
                                kiwify_url: str) -> bool:
    """E-mail enviado no dia em que o trial expira."""
    assunto = "🔒 Seu acesso ao Gastei foi suspenso — Reative agora"
    html = f"""
    <div style="font-family:Sora,sans-serif;max-width:520px;margin:auto;
                background:#1a1a2e;border-radius:16px;padding:40px;color:#e8e4ff;">
      <div style="text-align:center;font-size:52px;margin-bottom:4px;">🔒</div>
      <h2 style="text-align:center;
                 background:linear-gradient(90deg,#ef4444,#fca5a5);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 margin-bottom:8px;">Acesso suspenso</h2>
      <p style="color:#9ca3af;text-align:center;margin-bottom:24px;">
        Olá, <strong style="color:#e8e4ff;">{nome}</strong>! Seus {TRIAL_DIAS} dias de teste
        gratuito chegaram ao fim. Seus dados financeiros estão salvos e esperando por você.
      </p>
      <a href="{kiwify_url}"
         style="display:block;background:linear-gradient(135deg,#6a3de8,#9b8dff);
                color:#fff;text-align:center;padding:16px;border-radius:12px;
                font-weight:700;font-size:16px;text-decoration:none;
                letter-spacing:0.5px;box-shadow:0 4px 20px rgba(106,61,232,0.4);
                margin-bottom:16px;">
        🚀 Reativar acesso — R$ 24,90/mês
      </a>
      <p style="color:#6b7280;font-size:12px;text-align:center;">
        Sem fidelidade. Cancele quando quiser.<br>
        Suporte: finatechsuporte@gmail.com
      </p>
    </div>"""
    return _enviar_email_html(cfg, destinatario, assunto, html)


def rodar_job_emails_trial(run_query_fn):
    """
    Verifica e envia e-mails de trial para:
    - Usuários com trial expirando AMANHÃ  → e-mail de aviso D-1
    - Usuários com trial expirado HOJE     → e-mail de bloqueio D+0

    Execute com cache de 24h para rodar apenas uma vez por dia:

        @st.cache_data(ttl=86400, show_spinner=False)
        def _job_diario(_):
            rodar_job_emails_trial(run_query)
        _job_diario(0)
    """
    hoje = date.today()
    try:
        cfg = st.secrets.get("email", {})
        if not cfg:
            return

        # D-1: aviso de expiração amanhã
        amanha     = hoje + timedelta(days=1)
        rows_aviso = run_query_fn(f"""
            SELECT id, nome, email FROM usuarios
            WHERE status_assinatura = 'trial'
              AND trial_aviso_enviado = FALSE
              AND (trial_inicio::date + interval '{TRIAL_DIAS - 1} days')::date = '{amanha}'
        """, fetch=True)

        for u in (rows_aviso or []):
            ok = enviar_email_aviso_trial(cfg, u["email"], u["nome"], 1, KIWIFY_URL)
            if ok:
                run_query_fn(
                    "UPDATE usuarios SET trial_aviso_enviado=TRUE WHERE id=%s",
                    (u["id"],)
                )

        # D+0: trial expirou hoje ou antes
        rows_exp = run_query_fn(f"""
            SELECT id, nome, email FROM usuarios
            WHERE status_assinatura = 'trial'
              AND trial_expirou_email = FALSE
              AND (trial_inicio::date + interval '{TRIAL_DIAS} days')::date <= '{hoje}'
        """, fetch=True)

        for u in (rows_exp or []):
            ok = enviar_email_trial_expirado(cfg, u["email"], u["nome"], KIWIFY_URL)
            if ok:
                run_query_fn(
                    "UPDATE usuarios SET trial_expirou_email=TRUE WHERE id=%s",
                    (u["id"],)
                )

    except Exception:
        pass   # Job silencioso — nunca deve quebrar a UI


# ══════════════════════════════════════════
#  SEÇÃO F — TELA DE BLOQUEIO PREMIUM
# ══════════════════════════════════════════

def renderizar_tela_bloqueio(nome_usuario: str = ""):
    """
    Renderiza a tela de bloqueio quando o trial expira.
    Sempre chame st.stop() logo após esta função.

    Exemplo de uso:
        if not trial_info["acesso"]:
            renderizar_tela_bloqueio(st.session_state.usuario_nome)
            st.stop()
    """
    link_wa = (
        f"https://wa.me/{WHATSAPP_SUPORTE}"
        f"?text=Quero%20assinar%20o%20Gastei%20Premium"
    )
    nome_display = f", {nome_usuario}" if nome_usuario else ""

    st.markdown("""
    <style>
    .bloqueio-overlay {
        max-width: 580px; margin: 60px auto 0;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(239,68,68,0.25);
        border-radius: 24px; padding: 48px 44px;
        box-shadow: 0 8px 60px rgba(239,68,68,0.12),
                    0 0 0 1px rgba(239,68,68,0.08);
        backdrop-filter: blur(14px);
        text-align: center;
        animation: bFadeIn .45s ease;
    }
    @keyframes bFadeIn {
        from { opacity:0; transform:translateY(18px); }
        to   { opacity:1; transform:translateY(0); }
    }
    .bloqueio-icon   { font-size:68px; margin-bottom:8px; }
    .bloqueio-titulo {
        font-size:30px; font-weight:800;
        background: linear-gradient(90deg,#ef4444,#fca5a5);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        margin-bottom:12px;
    }
    .bloqueio-sub {
        color:#9ca3af; font-size:15px;
        margin-bottom:28px; line-height:1.65;
    }
    .preco-badge {
        display:inline-block;
        background:rgba(106,61,232,0.16);
        border:1px solid rgba(155,141,255,0.4);
        border-radius:999px; padding:7px 22px;
        color:#c4b5fd; font-size:13px; font-weight:700;
        margin-bottom:28px;
    }
    .feature-list {
        text-align:left; margin:0 auto 28px;
        max-width:340px; color:#9ca3af;
        font-size:14px; list-style:none; padding:0;
    }
    .feature-list li { padding:5px 0; }
    .feature-list li::before { content:"✅ "; }
    .btn-kiwify {
        display:block;
        background:linear-gradient(135deg,#6a3de8,#9b8dff);
        color:#fff !important; text-decoration:none !important;
        border-radius:14px; padding:18px 32px;
        font-size:17px; font-weight:700; letter-spacing:0.5px;
        box-shadow:0 4px 24px rgba(106,61,232,0.45);
        transition:transform .2s, box-shadow .2s;
        margin-bottom:14px;
    }
    .btn-kiwify:hover {
        transform:translateY(-2px);
        box-shadow:0 8px 36px rgba(106,61,232,0.6);
    }
    .btn-wa {
        display:inline-flex; align-items:center; gap:8px;
        color:#34d399 !important; text-decoration:none !important;
        font-size:14px; font-weight:600; opacity:.85;
    }
    .btn-wa:hover { opacity:1; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="bloqueio-overlay">
      <div class="bloqueio-icon">🔒</div>
      <div class="bloqueio-titulo">Seu teste gratuito acabou</div>
      <p class="bloqueio-sub">
        Olá{nome_display}! Seus
        <strong style="color:#e8e4ff;">{TRIAL_DIAS} dias grátis</strong>
        chegaram ao fim.<br>
        Seus dados financeiros estão salvos e esperando por você.
      </p>
      <div class="preco-badge">💳 Apenas R$ 24,90/mês · Cancele quando quiser</div>
      <ul class="feature-list">
        <li>Lançamentos e parcelas ilimitados</li>
        <li>Controle de contas fixas e variáveis</li>
        <li>Alertas de vencimento em tempo real</li>
        <li>Análise de % do salário comprometido</li>
        <li>Suporte prioritário via WhatsApp</li>
      </ul>
      <a href="{KIWIFY_URL}" target="_blank" class="btn-kiwify">
        🚀 Assinar Gastei Premium — R$ 24,90/mês
      </a>
      <br>
      <a href="{link_wa}" target="_blank" class="btn-wa">
        💬 Falar com o suporte no WhatsApp
      </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_mid, _ = st.columns([2, 1, 2])
    with col_mid:
        if st.button("← Usar outra conta", key="btn_logout_bloqueio"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.query_params.clear()
            st.rerun()
