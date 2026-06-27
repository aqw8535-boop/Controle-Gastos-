import streamlit as st
from utils import supabase_client, get_user_data, user_has_allowed_role
import extra_streamlit_components as stx
from autenticacao.google_auth import (
    get_login_url,
    get_tokens_from_code,
    get_user_info_from_token,
    clear_session_state,
)

# 1. Configuração inicial da página (Deve ser a primeira linha Streamlit)
st.set_page_config(
    page_title="Gestão de Demandas - Login",
    page_icon="🔒",
    layout="centered"
)

# 2. Inicialização segura do Session State
if "usuario_id" not in st.session_state:
    st.session_state.usuario_id = None
if "usuario_email" not in st.session_state:
    st.session_state.usuario_email = None
if "usuario_nome" not in st.session_state:
    st.session_state.usuario_nome = None
if "usuario_foto" not in st.session_state:
    st.session_state.usuario_foto = None

# Inicializa o gerenciador de cookies
cookie_manager = stx.CookieManager()

# 3. Fluxo de Autenticação / Verificação de Cookies
if st.session_state.usuario_id is None:
    # Tenta recuperar o token dos cookies se o usuário não estiver logado na sessão
    access_token = cookie_manager.get(cookie="sb-access-token")
    refresh_token = cookie_manager.get(cookie="sb-refresh-token")

    if access_token and refresh_token:
        try:
            res = supabase_client.auth.set_session(access_token, refresh_token)
            user = res.user
            if user:
                user_data = get_user_data(user.id)
                if user_data and user_has_allowed_role(user_data):
                    st.session_state.usuario_id = user.id
                    st.session_state.usuario_email = user.email
                    st.session_state.usuario_nome = user_data.get("nome", user.email)
                    st.session_state.usuario_foto = user_data.get("avatar_url", "")
                    st.rerun()
        except Exception:
            # Se o token expirou ou falhou, limpa e segue para o login visual
            cookie_manager.delete("sb-access-token")
            cookie_manager.delete("sb-refresh-token")

    # Captura os parâmetros da URL para o retorno do Google OAuth
    params = st.query_params

    if "code" in params:
        code = params["code"]
        # Limpa os parâmetros da URL para evitar loops de reenvio
        st.query_params.clear()
        
        with st.spinner("Autenticando com o Google..."):
            tokens = get_tokens_from_code(code)
            if tokens and "access_token" in tokens:
                user_info = get_user_info_from_token(tokens["access_token"])
                if user_info and "email" in user_info:
                    email = user_info["email"]
                    import secrets as _sec_oauth
                    password = _sec_oauth.token_urlsafe(16)

                    try:
                        # Tenta logar ou criar o usuário no Supabase via Google
                        res = supabase_client.auth.sign_in_with_password(
                            {"email": email, "password": password}
                        )
                    except Exception:
                        try:
                            res = supabase_client.auth.sign_up(
                                {"email": email, "password": password}
                            )
                        except Exception as e:
                            st.error(f"Erro ao registrar usuário: {e}")
                            res = None

                    if res and res.user:
                        user_data = get_user_data(res.user.id)
                        if user_data and user_has_allowed_role(user_data):
                            st.session_state.usuario_id = res.user.id
                            st.session_state.usuario_email = res.user.email
                            st.session_state.usuario_nome = user_info.get("name", email)
                            st.session_state.usuario_foto = user_info.get("picture", "")
                            
                            # Salva a sessão nos cookies do navegador
                            cookie_manager.set("sb-access-token", res.session.access_token)
                            cookie_manager.set("sb-refresh-token", res.session.refresh_token)
                            st.rerun()
                        else:
                            st.error("Seu usuário não tem permissão para acessar este sistema.")
            else:
                st.error("Falha ao obter o token de autenticação.")

    # 4. Interface Visual da Tela de Login (Caso não esteja logado)
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 2rem;'>
            <h1 style='color: #1E3A8A;'>Gestão de Demandas</h1>
            <p style='color: #6B7280;'>Faça login para acessar o painel</p>
        </div>
        """, 
        unsafe_allow_value=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        login_url = get_login_url()
        st.markdown(
            f"""
            <a href="{login_url}" target="_self" style="text-decoration: none;">
                <button style="
                    width: 100%;
                    background-color: #4285F4;
                    color: white;
                    border: none;
                    padding: 12px;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: bold;
                    cursor: pointer;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                ">
                    <img src="https://fonts.gstatic.com/s/i/productlogos/googleg/v6/web-24dp/logo_googleg_color_24dp.png" width="20px"/>
                    Entrar com o Google
                </button>
            </a>
            """,
            unsafe_allow_value=True,
        )

# 5. Fluxo de Usuário já Autenticado
else:
    st.title("Painel de Controle")
    st.write(f"Bem-vindo, **{st.session_state.usuario_nome}**!")
    
    if st.session_state.usuario_foto:
        st.image(st.session_state.usuario_foto, width=100)

    if st.button("Sair / Logout"):
        clear_session_state()
        cookie_manager.delete("sb-access-token")
        cookie_manager.delete("sb-refresh-token")
        st.rerun()
