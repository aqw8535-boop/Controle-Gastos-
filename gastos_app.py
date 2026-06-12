import streamlit as st
import psycopg2
import psycopg2.extras
import psycopg2.pool
import pandas as pd
from datetime import date, timedelta
import hashlib
import hmac
import re
import calendar
import smtplib
import secrets as _secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─────────────────────────────────────────────
#  CONFIG DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(page_title="Gastei", page_icon="💳", layout="wide")

# ─────────────────────────────────────────────
#  PWA — META TAGS
# ─────────────────────────────────────────────
st.markdown("""
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Gastos">
<meta name="theme-color" content="#6a3de8">
<meta name="application-name" content="Controle de Gastos">
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE — inicializa ANTES de tudo
# ─────────────────────────────────────────────
_SS_DEFAULTS = {
    "usuario_id":        None,
    "usuario_nome":      None,
    "lang":              "PT",
    "salario":           0.0,
    "pref_aberto":       False,
    "reset_step":        0,
    "reset_email":       "",
    "_salario_carregado": False,   # MISSÃO 1: flag para só buscar 1x por sessão
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────
#  SESSION STATE — inicializa ANTES de tudo
# ─────────────────────────────────────────────
_SS_DEFAULTS = {
    "usuario_id":        None,
    "usuario_nome":      None,
    "lang":              "PT",
    "salario":           0.0,
    "pref_aberto":       False,
    "reset_step":        0,
    "reset_email":       "",
    "_salario_carregado": False,
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# FUNÇÃO REATIVA DO SELETOR: Roda no exato milésimo de segundo do clique!
def mudar_idioma_callback():
    if "seletor_idioma" in st.session_state:
        _escolha = st.session_state["seletor_idioma"]
        if "English" in _escolha:
            st.session_state.lang = "EN"
        elif "Français" in _escolha:
            st.session_state.lang = "FR"
        else:
            st.session_state.lang = "PT"

# ─────────────────────────────────────────────
#  MISSÃO 2 — FIXAR IDIOMA: lê/aplica ANTES de renderizar qualquer widget
#  A chave "seletor_idioma" é estática; o valor vem sempre do session_state.
# ─────────────────────────────────────────────
_LANG_OPTIONS  = {"Português": "PT", "English": "EN", "Français": "FR"}
_LANG_LABELS   = list(_LANG_OPTIONS.keys())
_LANG_CODES    = list(_LANG_OPTIONS.values())

# 1. INTERCEPTAÇÃO ANTICIPADA: Se o usuário mexer no rádio da tela de login,
# atualizamos o estado interno antes de carregar o dicionário get_t()!
if "seletor_idioma" in st.session_state and st.session_state["seletor_idioma"] is not None:
    _escolha_usuario = st.session_state["seletor_idioma"]
    _codigo_detectado = "PT"
    
    if "English" in _escolha_usuario:
        _codigo_detectado = "EN"
    elif "Français" in _escolha_usuario:
        _codigo_detectado = "FR"
        
    if st.session_state.lang != _codigo_detectado:
        st.session_state.lang = _codigo_detectado
        st.rerun()

# 2. Garante que lang seja sempre um código válido por padrão
if st.session_state.lang not in _LANG_CODES:
    st.session_state.lang = "PT"
# ─────────────────────────────────────────────
#  DICIONÁRIO I18N — TRILÍNGUE
# ─────────────────────────────────────────────
IDIOMAS = {
    "PT": {
        "app_subtitle":         "Finanças Pessoais Premium Inteligentes",
        "ola":                  "Olá",
        "sair":                 "🚪",
        "aba_gastos":           "📊 Meus Gastos",
        "aba_feedback":         "💬 Feedbacks & Sugestões",
        "total_saidas":         "Total de Saídas Contratadas",
        "comprometido_mes":     "Comprometido Este Mês",
        "salario_comprometido": "Salário Comprometido (Próx. Mês)",
        "novo_lancamento":      "➕ Novo Lançamento",
        "o_que_comprou":        "O que comprou / Pagou",
        "placeholder_desc":     "Ex: iPhone 16, Aluguel, Internet...",
        "valor_total":          "Valor Total (R$)",
        "conta_fixa":           "🔁 Conta Fixa / Recorrente (sem data de término — Aluguel, Internet...)",
        "dia_vencimento":       "Dia de Vencimento (Data de Início)",
        "num_parcelas":         "Número de Parcelas",
        "data_primeiro_venc":   "Data do Primeiro Vencimento",
        "valor_mensal":         "**Valor mensal:**",
        "tipo_recorrente":      "**Tipo:**",
        "prox_vencimento":      "**Próximo vencimento:**",
        "valor_parcela":        "**Valor por parcela:**",
        "parcelas_restantes":   "**Parcelas restantes:**",
        "venc_parcela1":        "**Vencimento da Parcela 1:**",
        "salvar_lancamento":    "💾 Salvar Lançamento",
        "salvo_sucesso":        "✅ **{}** salvo com sucesso!",
        "err_descricao":        "⚠️ Preencha a descrição do gasto.",
        "err_valor":            "⚠️ O valor deve ser maior que zero.",
        "historico":            "### 📋 Histórico de Vencimentos",
        "filtrar":              "🔍 Filtrar por descrição",
        "placeholder_busca":    "Digite para buscar...",
        "nenhum_lancamento":    "Nenhum lançamento ainda.",
        "conta_atrasada_s":     "conta atrasada",
        "conta_atrasada_p":     "contas atrasadas",
        "conta_hoje_s":         "conta vence hoje",
        "conta_hoje_p":         "contas vencem hoje",
        "conta_breve_s":        "conta vence",
        "conta_breve_p":        "contas vencem",
        "alerta_breve_sufixo":  "nos próximos 3 dias",
        "alerta_hoje_sufixo":   "não deixe passar!",
        "alerta_atrasada_sufixo": "quite agora para não acumular juros!",
        "col_descricao":        "Descrição",
        "col_valor":            "Valor",
        "col_vencimento":       "Próximo Vencimento",
        "col_situacao":         "Situação",
        "col_acoes":            "Ações",
        "label_mensal":         "mensal",
        "label_parcela":        "por parcela",
        "conta_mensal_fixa":    "Conta Mensal Fixa",
        "total_label":          "Total:",
        "inicio_label":         "Início:",
        "divida_encerrada":     "Dívida Encerrada",
        "ultima_parcela":       "Última parcela:",
        "falta_pagar":          "Falta pagar:",
        "recorrente_inf":       "Recorrente ∞",
        "x_restantes":          "x restantes",
        "btn_pagar":            "💸 Pagar Parcela",
        "btn_quitar":           "🏁 Quitar Tudo",
        "btn_excluir":          "🗑️ Excluir",
        "salario_titulo":       "💰 Meu Salário Mensal",
        "salario_input":        "Salário Mensal Líquido (R$)",
        "salario_btn":          "💾 Salvar Salário",
        "salario_salvo":        "✅ Salário atualizado!",
        "salario_zero_aviso":   "⚠️ Cadastre seu salário no painel ⚙️ para ver o % comprometido.",
        "pct_label":            "% do salário comprometido no próximo mês",
        "sim_alerta":           (
            "⚠️ TEM CERTEZA QUE QUER FAZER ESTA CONTA? {:.1f}% DO SEU SALÁRIO ESTARÁ COMPROMETIDO; "
            "É MELHOR NÃO FAZER ESTA CONTA, POIS ESTÁ ALÉM DO QUE VOCÊ CONSEGUE PAGAR PARA O PRÓXIMO MÊS!"
        ),
        "sim_ok":               "✅ Dentro do limite saudável (abaixo de 70% do salário).",
        "sim_info":             "💡 Com este gasto: **R$ {:.2f}/mês** comprometido ({:.1f}% do salário).",
        "pref_fechar":          "Fechar",
        "feedback_titulo":      "### 💬 Canal Direct de Sugestões & Feedbacks",
        "feedback_sub":         "Sua opinião molda as próximas atualizações da nossa plataforma!",
        "feedback_label":       "Sua mensagem",
        "feedback_placeholder": "Ex: Seria massa ver um gráfico de pizza no topo... Ou: Encontrei um bug visual no botão X...",
        "feedback_btn":         "📨 Enviar Meu Feedback",
        "feedback_vazio":       "⚠️ Escreva algo antes de clicar em enviar.",
        "feedback_curto":       "⚠️ Detalhe um pouquinho mais a sua mensagem.",
        "feedback_ok":          "✅ Feedback enviado com absoluto sucesso! Muito obrigado 🙏",
        "rodape":               "© 2026 Gastei App. Todos os direitos reservados. Suporte: finatechsuporte@gmail.com",
        "idioma_label":         "🌐 Idioma",
        "login_titulo_app": "Finanças Premium",
        "login_sub_app": "Controle de Gastos de Alta Performance",
        "aba_entrar": "🔑  Entrar",
        "aba_criar_conta": "✨  Criar Conta",
        "btn_entrar_seta": "Entrar →",
        "err_preencha_dados": "Preencha e-mail e senha.",
        "msg_suporte_wa": "Olá! Quero verificar o status do meu acesso no app Gastei.",
        "link_suporte": "Problemas com o acesso? — Falar com o Suporte",
        "link_vendas": "Ainda não tem acesso? Conheça o Gastei →",
        "link_vendas_planos": "Ainda não comprou? Conheça os planos →",
        "expander_termos": "🛡️ Termos de Uso e Política de Privacidade",
        "texto_termos": "Seus dados financeiros são armazenados de forma criptografada e privativa. Não compartilhamos suas informações.",
        "info_reset_email": "📧 Informe o e-mail cadastrado. Enviaremos um código de 6 dígitos.",
        "input_email_cadastrado": "E-mail cadastrado",
        "btn_enviar_codigo": "Enviar código →",
        "err_email_nao_encontrado": "E-mail não encontrado.",
        "sucesso_codigo_enviado": "✅ Código enviado para **{}**.",
        "input_codigo_digitos": "Código de 6 dígitos",
        "input_nova_senha": "Nova senha",
        "input_confirmar_nova": "Confirmar nova senha",
        "btn_redefinir_senha": "Redefinir senha →",
        "err_informe_codigo": "Informe o código.",
        "err_senha_curta": "Mínimo 6 caracteres.",
        "err_senhas_diferentes": "Senhas não conferem.",
        "err_codigo_expirado": "Código inválido ou expirado.",
        "sucesso_senha_redefinida": "🎉 Senha redefinida! Faça login.",
        "input_nome": "Seu nome",
        "input_telefone": "WhatsApp / Telefone",
        "input_confirmar_senha": "Confirmar senha",
        "btn_criar_conta": "Criar minha conta →",
        "err_campos_vazios": "Preencha todos os campos.",
        "err_tel_invalido": "Telefone inválido.",
        "sucesso_conta_criada": "✅ Conta criada! Faça login na aba ao lado.",
        
    },
    "EN": {"input_senha": "Password",
        "input_nova_senha": "New Password",
        "input_confirmar_nova": "Confirm New Password",
        "input_confirmar_senha": "Confirm Password",
        "app_subtitle":         "Intelligent Premium Personal Finance",
        "ola":                  "Hello",
        "sair":                 "🚪",
        "aba_gastos":           "📊 My Expenses",
        "aba_feedback":         "💬 Feedback & Suggestions",
        "total_saidas":         "Total Contracted Expenses",
        "comprometido_mes":     "Committed This Month",
        "salario_comprometido": "Salary Committed (Next Month)",
        "novo_lancamento":      "➕ New Entry",
        "o_que_comprou":        "What did you buy / pay",
        "placeholder_desc":     "e.g.: iPhone 16, Rent, Internet...",
        "valor_total":          "Total Amount (R$)",
        "conta_fixa":           "🔁 Fixed / Recurring Bill (no end date — Rent, Internet...)",
        "dia_vencimento":       "Due Day (Start Date)",
        "num_parcelas":         "Number of Installments",
        "data_primeiro_venc":   "First Due Date",
        "valor_mensal":         "**Monthly amount:**",
        "tipo_recorrente":      "**Type:**",
        "prox_vencimento":      "**Next due date:**",
        "valor_parcela":        "**Installment value:**",
        "parcelas_restantes":   "**Remaining installments:**",
        "venc_parcela1":        "**Due date of installment 1:**",
        "salvar_lancamento":    "💾 Save Entry",
        "salvo_sucesso":        "✅ **{}** saved successfully!",
        "err_descricao":        "⚠️ Please fill in the expense description.",
        "err_valor":            "⚠️ Amount must be greater than zero.",
        "historico":            "### 📋 Payment History",
        "filtrar":              "🔍 Filter by description",
        "placeholder_busca":    "Type to search...",
        "nenhum_lancamento":    "No entries yet.",
        "conta_atrasada_s":     "overdue bill",
        "conta_atrasada_p":     "overdue bills",
        "conta_hoje_s":         "bill due today",
        "conta_hoje_p":         "bills due today",
        "conta_breve_s":        "bill due",
        "conta_breve_p":        "bills due",
        "alerta_breve_sufixo":  "in the next 3 days",
        "alerta_hoje_sufixo":   "don't let it pass!",
        "alerta_atrasada_sufixo": "pay now to avoid late fees!",
        "col_descricao":        "Description",
        "col_valor":            "Amount",
        "col_vencimento":       "Next Due Date",
        "col_situacao":         "Status",
        "col_acoes":            "Actions",
        "label_mensal":         "monthly",
        "label_parcela":        "per installment",
        "conta_mensal_fixa":    "Fixed Monthly Bill",
        "total_label":          "Total:",
        "inicio_label":         "Start:",
        "divida_encerrada":     "Debt Settled",
        "ultima_parcela":       "Last installment:",
        "falta_pagar":          "Remaining:",
        "recorrente_inf":       "Recurring ∞",
        "x_restantes":          "remaining",
        "btn_pagar":            "💸 Pay Installment",
        "btn_quitar":           "🏁 Pay Off All",
        "btn_excluir":          "🗑️ Delete",
        "salario_titulo":       "💰 My Monthly Salary",
        "salario_input":        "Net Monthly Salary (R$)",
        "salario_btn":          "💾 Save Salary",
        "salario_salvo":        "✅ Salary updated!",
        "salario_zero_aviso":   "⚠️ Set your salary in the ⚙️ panel to see the committed % of income.",
        "pct_label":            "% of salary committed next month",
        "sim_alerta":           (
            "⚠️ ARE YOU SURE YOU WANT TO MAKE THIS EXPENSE? {:.1f}% OF YOUR SALARY WILL BE COMMITTED; "
            "IT IS BETTER NOT TO MAKE THIS EXPENSE, AS IT IS BEYOND WHAT YOU CAN AFFORD FOR NEXT MONTH!"
        ),
        "sim_ok":               "✅ Within healthy limit (below 70% of salary).",
        "sim_info":             "💡 With this expense: **R$ {:.2f}/month** committed ({:.1f}% of salary).",
        "pref_fechar":          "Close",
        "feedback_titulo":      "### 💬 Suggestions & Feedback Channel",
        "feedback_sub":         "Your opinion shapes the next updates to our platform!",
        "feedback_label":       "Your message",
        "feedback_placeholder": "e.g.: It'd be great to see a pie chart at the top... Or: I found a visual bug in button X...",
        "feedback_btn":         "📨 Send My Feedback",
        "feedback_vazio":       "⚠️ Please write something before clicking send.",
        "feedback_curto":       "⚠️ Please elaborate a little more on your message.",
        "feedback_ok":          "✅ Feedback sent successfully! Thank you so much 🙏",
        "rodape":               "© 2026 Gastei App. All rights reserved. Support: finatechsuporte@gmail.com",
        "idioma_label":         "🌐 Language",
        "login_titulo_app": "Premium Finance",
        "login_sub_app": "High Performance Expense Control",
        "aba_entrar": "🔑  Login",
        "aba_criar_conta": "✨  Register",
        "btn_entrar_seta": "Login →",
        "err_preencha_dados": "Please enter email and password.",
        "msg_suporte_wa": "Hello! I want to check my access status on the Gastei app.",
        "link_suporte": "Access issues? — Contact Support",
        "link_vendas": "Don't have access yet? Discover Gastei →",
        "link_vendas_planos": "Haven't bought yet? Check plans →",
        "expander_termos": "🛡️ Terms of Use and Privacy Policy",
        "texto_termos": "Your financial data is stored encrypted and private. We do not share your information.",
        "info_reset_email": "📧 Enter your registered email. We will send a 6-digit code.",
        "input_email_cadastrado": "Registered Email",
        "btn_enviar_codigo": "Send code →",
        "err_email_nao_encontrado": "Email not found.",
        "sucesso_codigo_enviado": "✅ Code sent to **{}**.",
        "input_codigo_digitos": "6-digit code",
        "input_nova_senha": "New password",
        "input_confirmar_nova": "Confirm new password",
        "btn_redefinir_senha": "Reset password →",
        "err_informe_codigo": "Enter the code.",
        "err_senha_curta": "Minimum 6 characters.",
        "err_senhas_diferentes": "Passwords do not match.",
        "err_codigo_expirado": "Invalid or expired code.",
        "sucesso_senha_redefinida": "🎉 Password reset! Please login.",
        "input_nome": "Your name",
        "input_telefone": "WhatsApp / Phone",
        "input_confirmar_senha": "Confirm password",
        "btn_criar_conta": "Create my account →",
        "err_campos_vazios": "Please fill in all fields.",
        "err_tel_invalido": "Invalid phone number.",
        "sucesso_conta_criada": "✅ Account created! Login in the next tab.",
    },
    "FR": {
        "input_senha": "Mot de passe",
        "input_nova_senha": "Nouveau mot de passe",
        "input_confirmar_nova": "Confirmer le mot de passe",
        "input_confirmar_senha": "Confirmer le mot de passe",
        "app_subtitle":         "Finances Personnelles Premium Intelligentes",
        "ola":                  "Bonjour",
        "sair":                 "🚪",
        "aba_gastos":           "📊 Mes Dépenses",
        "aba_feedback":         "💬 Retours & Suggestions",
        "total_saidas":         "Total des Dépenses Contractées",
        "comprometido_mes":     "Engagé Ce Mois",
        "salario_comprometido": "Salaire Engagé (Mois Prochain)",
        "novo_lancamento":      "➕ Nouvelle Entrée",
        "o_que_comprou":        "Qu'avez-vous acheté / payé",
        "placeholder_desc":     "Ex: iPhone 16, Loyer, Internet...",
        "valor_total":          "Montant Total (R$)",
        "conta_fixa":           "🔁 Facture Fixe / Récurrente (sans date de fin — Loyer, Internet...)",
        "dia_vencimento":       "Jour d'Échéance (Date de Début)",
        "num_parcelas":         "Nombre de Versements",
        "data_primeiro_venc":   "Date de la Première Échéance",
        "valor_mensal":         "**Montant mensuel :**",
        "tipo_recorrente":      "**Type :**",
        "prox_vencimento":      "**Prochaine échéance :**",
        "valor_parcela":        "**Valeur du versement :**",
        "parcelas_restantes":   "**Versements restants :**",
        "venc_parcela1":        "**Échéance du versement 1 :**",
        "salvar_lancamento":    "💾 Enregistrer",
        "salvo_sucesso":        "✅ **{}** enregistré avec succès !",
        "err_descricao":        "⚠️ Veuillez renseigner la description de la dépense.",
        "err_valor":            "⚠️ Le montant doit être supérieur à zéro.",
        "historico":            "### 📋 Historique des Échéances",
        "filtrar":              "🔍 Filtrer par description",
        "placeholder_busca":    "Tapez pour rechercher...",
        "nenhum_lancamento":    "Aucune entrée pour l'instant.",
        "conta_atrasada_s":     "facture en retard",
        "conta_atrasada_p":     "factures en retard",
        "conta_hoje_s":         "facture due aujourd'hui",
        "conta_hoje_p":         "factures dues aujourd'hui",
        "conta_breve_s":        "facture due",
        "conta_breve_p":        "factures dues",
        "alerta_breve_sufixo":  "dans les 3 prochains jours",
        "alerta_hoje_sufixo":   "ne laissez pas passer !",
        "alerta_atrasada_sufixo": "payez maintenant pour éviter les pénalités !",
        "col_descricao":        "Description",
        "col_valor":            "Montant",
        "col_vencimento":       "Prochaine Échéance",
        "col_situacao":         "Statut",
        "col_acoes":            "Actions",
        "label_mensal":         "mensuel",
        "label_parcela":        "par versement",
        "conta_mensal_fixa":    "Facture Mensuelle Fixe",
        "total_label":          "Total :",
        "inicio_label":         "Début :",
        "divida_encerrada":     "Dette Réglée",
        "ultima_parcela":       "Dernier versement :",
        "falta_pagar":          "Reste à payer :",
        "recorrente_inf":       "Récurrent ∞",
        "x_restantes":          "restants",
        "btn_pagar":            "💸 Payer le Versement",
        "btn_quitar":           "🏁 Tout Régler",
        "btn_excluir":          "🗑️ Supprimer",
        "salario_titulo":       "💰 Mon Salaire Mensuel",
        "salario_input":        "Salaire Mensuel Net (R$)",
        "salario_btn":          "💾 Sauvegarder",
        "salario_salvo":        "✅ Salaire mis à jour !",
        "salario_zero_aviso":   "⚠️ Enregistrez votre salaire dans le panneau ⚙️ pour voir le % engagé.",
        "pct_label":            "% du salaire engagé le mois prochain",
        "sim_alerta":           (
            "⚠️ ÊTES-VOUS SÛR DE VOULOIR FAIRE CETTE DÉPENSE ? {:.1f}% DE VOTRE SALAIRE SERA ENGAGÉ ; "
            "IL VAUT MIEUX NE PAS FAIRE CETTE DÉPENSE, CAR ELLE DÉPASSE CE QUE VOUS POUVEZ PAYER POUR LE MOIS PROCHAIN !"
        ),
        "sim_ok":               "✅ Dans la limite saine (moins de 70% du salaire).",
        "sim_info":             "💡 Avec cette dépense : **R$ {:.2f}/mois** engagé ({:.1f}% du salaire).",
        "pref_fechar":          "Fermer",
        "feedback_titulo":      "### 💬 Canal de Suggestions & Retours",
        "feedback_sub":         "Votre avis façonne les prochaines mises à jour de notre plateforme !",
        "feedback_label":       "Votre message",
        "feedback_placeholder": "Ex : Ce serait super d'avoir un graphique en secteurs... Ou : J'ai trouvé un bug visuel sur le bouton X...",
        "feedback_btn":         "📨 Envoyer Mon Retour",
        "feedback_vazio":       "⚠️ Veuillez écrire quelque chose avant d'envoyer.",
        "feedback_curto":       "⚠️ Veuillez développer un peu plus votre message.",
        "feedback_ok":          "✅ Retour envoyé avec succès ! Merci beaucoup 🙏",
        "rodape":               "© 2026 Gastei App. Tous droits réservés. Support : finatechsuporte@gmail.com",
        "idioma_label":         "🌐 Langue",
        "login_titulo_app": "Finances Premium",
        "login_sub_app": "Contrôle des Dépenses Haute Performance",
        "aba_entrar": "🔑  Connexion",
        "aba_criar_conta": "✨  Créer un Compte",
        "btn_entrar_seta": "Se connecter →",
        "err_preencha_dados": "Veuillez entrer l'e-mail et le mot de passe.",
        "msg_suporte_wa": "Bonjour! Je souhaite vérifier le statut de mon accès sur l'application Gastei.",
        "link_suporte": "Problèmes d'accès? — Contacter le Support",
        "link_vendas": "Pas encore d'accès? Découvrez Gastei →",
        "link_vendas_planos": "Pas encore acheté? Voir les plans →",
        "expander_termos": "🛡️ Conditions d'Utilisation et Politique de Confidentialité",
        "texto_termos": "Vos données financières sont stockées de manière cryptée et privée. Nous ne partageons pas vos informations.",
        "info_reset_email": "📧 Entrez votre e-mail enregistré. Nous vous enverrons un code à 6 chiffres.",
        "input_email_cadastrado": "E-mail enregistré",
        "btn_enviar_codigo": "Envoyer le code →",
        "err_email_nao_encontrado": "E-mail non trouvé.",
        "sucesso_codigo_enviado": "✅ Code envoyé à **{}**.",
        "input_codigo_digitos": "Code à 6 chiffres",
        "input_nova_senha": "Nouveau mot de passe",
        "input_confirmar_nova": "Confirmer le mot de passe",
        "btn_redefinir_senha": "Réinitialiser le mot de passe →",
        "err_informe_codigo": "Entrez le code.",
        "err_senha_curta": "Minimum 6 caractères.",
        "err_senhas_diferentes": "Les mots de passe ne correspondent pas.",
        "err_codigo_expirado": "Code invalide ou expiré.",
        "sucesso_senha_redefinida": "🎉 Mot de passe réinitialisé! Connectez-vous.",
        "input_nome": "Votre nom",
        "input_telefone": "WhatsApp / Téléphone",
        "input_confirmar_senha": "Confirmer le mot de passe",
        "btn_criar_conta": "Créer mon compte →",
        "err_campos_vazios": "Veuillez remplir tous les champs.",
        "err_tel_invalido": "Numéro de téléphone invalide.",
        "sucesso_conta_criada": "✅ Compte créé! Connectez-vous dans l'onglet d'à côté.",
    },
}

# ─────────────────────────────────────────────
#  ATALHO GLOBAL — sempre lê do session_state
# ─────────────────────────────────────────────
def get_t():
    return IDIOMAS[st.session_state.lang]

# ─────────────────────────────────────────────
#  CSS GLOBAL
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%); min-height: 100vh; }
h1 {
    font-family: 'Sora', sans-serif !important; font-weight: 700 !important;
    background: linear-gradient(90deg, #e2c4f0, #9b8dff, #64b5f6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.5px;
}
h2, h3 { font-family: 'Sora', sans-serif !important; color: #c9d1f0 !important; }

/* LOGIN */
.login-wrap {
    max-width: 460px; margin: 60px auto 0;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(155,141,255,0.2);
    border-radius: 24px; padding: 48px 40px;
    box-shadow: 0 8px 60px rgba(106,61,232,0.25); backdrop-filter: blur(12px);
}
.login-logo { text-align:center; font-size:52px; margin-bottom:8px; }
.login-title {
    text-align:center; font-size:26px; font-weight:700;
    background: linear-gradient(90deg, #e2c4f0, #9b8dff, #64b5f6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom:4px;
}
.login-sub { text-align:center; font-size:13px; color:#6b7280; margin-bottom:32px; }

/* CARDS */
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
.salario-card {
    background: linear-gradient(135deg, #1a2e1e 0%, #0d2118 100%);
    border: 1px solid rgba(52,211,153,0.25); border-radius: 20px; padding: 24px 32px; margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.salario-card.alerta { background: linear-gradient(135deg, #2e1a1a 0%, #210d0d 100%); border-color: rgba(239,68,68,0.35); }
.salario-label { font-size:13px; font-weight:600; letter-spacing:2px; text-transform:uppercase; color:rgba(52,211,153,0.75); margin-bottom:6px; }
.salario-card.alerta .salario-label { color:rgba(239,68,68,0.75); }
.salario-value { font-family:'JetBrains Mono',monospace; font-size:34px; font-weight:700; color:#34d399; }
.salario-card.alerta .salario-value { color:#ef4444; }

/* ALERTA SIMULAÇÃO PISCANTE */
@keyframes pulse-alerta {
    0%,100% { box-shadow: 0 0 0 1px rgba(239,68,68,0.5), 0 0 20px rgba(239,68,68,0.2); opacity:1; }
    50%      { box-shadow: 0 0 0 2px rgba(239,68,68,0.8), 0 0 40px rgba(239,68,68,0.4); opacity:0.88; }
}
.alerta-simulacao {
    background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(251,146,60,0.1));
    border: 2px solid rgba(239,68,68,0.6); border-radius: 14px; padding: 18px 22px;
    font-size: 13px; font-weight: 700; color: #fca5a5; letter-spacing: 0.03em; line-height: 1.6;
    animation: pulse-alerta 1.8s ease-in-out infinite; margin-top: 12px;
}
.alerta-simulacao .pct-destaque {
    font-size: 24px; font-weight: 800; color: #ef4444;
    display: block; margin-bottom: 8px; font-family: 'JetBrains Mono', monospace;
}

/* FORMULÁRIO */
.form-section {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px; padding: 28px 32px; margin-bottom: 32px; backdrop-filter: blur(10px);
}

/* LINHAS TABELA */
.lancamento-row {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 18px 24px; margin-bottom: 10px;
    display: grid; grid-template-columns: 2.2fr 1fr 1fr 1fr 0.8fr;
    align-items: center; transition: all 0.2s;
}
.lancamento-row:hover { background: rgba(155,141,255,0.08); border-color: rgba(155,141,255,0.3); }
.lancamento-row.fixa  { border-color: rgba(251,191,36,0.25); }
.lancamento-row.fixa:hover { background: rgba(251,191,36,0.06); border-color: rgba(251,191,36,0.45); }
.lancamento-row.urgente {
    border-color: rgba(239,68,68,0.7); background: rgba(239,68,68,0.08);
    box-shadow: 0 0 0 1px rgba(239,68,68,0.3), -4px 0 0 0 #ef4444;
}
.lancamento-row.urgente:hover { background: rgba(239,68,68,0.13); }
.lancamento-row.hoje {
    border-color: rgba(251,146,60,0.8); background: rgba(251,146,60,0.09);
    box-shadow: 0 0 0 1px rgba(251,146,60,0.35), -4px 0 0 0 #f97316;
    animation: pulse-hoje 2s ease-in-out infinite;
}
.lancamento-row.hoje:hover { background: rgba(251,146,60,0.15); }
@keyframes pulse-hoje {
    0%,100% { box-shadow: 0 0 0 1px rgba(251,146,60,0.35), -4px 0 0 0 #f97316; }
    50%      { box-shadow: 0 0 14px rgba(251,146,60,0.35), -4px 0 0 0 #f97316; }
}
.lancamento-row.em-breve {
    border-color: rgba(234,179,8,0.55); background: rgba(234,179,8,0.06); box-shadow: -4px 0 0 0 #ca8a04;
}
.lancamento-row.em-breve:hover { background: rgba(234,179,8,0.1); }
.lancamento-row.pago { opacity: 0.38; }

.alerta-banner {
    display:flex; align-items:center; gap:8px; background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.3); border-radius: 10px; padding: 7px 14px;
    font-size:11px; font-weight:700; color:#fca5a5; letter-spacing:0.04em; margin-bottom: 20px;
}
.alerta-banner .count { background: #ef4444; color:#fff; border-radius: 999px; padding: 1px 8px; font-size:11px; font-weight:800; }
.hoje-banner {
    display:flex; align-items:center; gap:8px; background: rgba(251,146,60,0.12);
    border: 1px solid rgba(251,146,60,0.35); border-radius: 10px; padding: 7px 14px;
    font-size:11px; font-weight:700; color:#fdba74; letter-spacing:0.04em; margin-bottom: 8px;
}
.badge-em-breve { background:rgba(234,179,8,0.15); border:1px solid rgba(234,179,8,0.4); color:#fde047; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; display:inline-block; }

/* INPUTS */
label { color:#a0aec0 !important; font-size:13px !important; font-weight:600 !important; letter-spacing:0.5px !important; }
input, textarea, .stTextInput input, .stNumberInput input, .stDateInput input,
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, div[data-testid="stDateInput"] input {
    border-radius: 10px !important; color: #1a1a2e !important;
    font-family: 'Sora', sans-serif !important; font-size: 15px !important; caret-color: #6a3de8 !important;
}
input::placeholder, textarea::placeholder { color: rgba(80,80,120,0.5) !important; }
.stCheckbox label { color:#c9d1f0 !important; font-size:14px !important; font-weight:600 !important; }

/* BOTÕES */
.stButton > button {
    background: linear-gradient(135deg, #6a3de8, #9b8dff) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important; font-weight: 600 !important; font-size: 14px !important;
    padding: 12px 28px !important; width: 100% !important;
    letter-spacing: 0.5px !important; box-shadow: 0 4px 20px rgba(106,61,232,0.4) !important; transition: all 0.2s !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(106,61,232,0.6) !important; }
.btn-link > button {
    background: transparent !important; border: none !important; color: #9b8dff !important; font-size: 13px !important;
    padding: 4px 0 !important; box-shadow: none !important; width: auto !important;
    text-decoration: underline !important; text-underline-offset: 3px !important; opacity: 0.85 !important;
}
.btn-link > button:hover { opacity: 1 !important; transform: none !important; box-shadow: none !important; }
.logout-btn > button {
    background: rgba(255,255,255,0.06) !important; border: 1px solid rgba(255,255,255,0.12) !important;
    font-size: 12px !important; padding: 6px 14px !important; box-shadow: none !important;
    width: auto !important; color: #9ca3af !important;
}
.logout-btn > button:hover { background: rgba(255,80,80,0.12) !important; color: #fca5a5 !important; border-color: rgba(255,80,80,0.3) !important; }
.pref-btn > button {
    background: rgba(155,141,255,0.1) !important; border: 1px solid rgba(155,141,255,0.3) !important;
    color: #c4b5fd !important; font-size: 18px !important; padding: 6px 12px !important;
    border-radius: 10px !important; box-shadow: none !important; width: auto !important; transition: all 0.2s !important;
}
.pref-btn > button:hover {
    background: rgba(155,141,255,0.22) !important; border-color: rgba(155,141,255,0.6) !important;
    transform: rotate(30deg) !important; box-shadow: 0 0 12px rgba(155,141,255,0.3) !important;
}
.btn-pagar > button {
    background: linear-gradient(135deg, #059669, #34d399) !important;
    font-size: 11px !important; padding: 6px 10px !important;
    box-shadow: 0 2px 10px rgba(5,150,105,0.3) !important; width: 100% !important;
}
.btn-quitar > button {
    background: linear-gradient(135deg, #7c3aed, #a78bfa) !important;
    font-size: 11px !important; padding: 6px 10px !important;
    box-shadow: 0 2px 10px rgba(124,58,237,0.3) !important; width: 100% !important;
}

/* PAINEL PREFERÊNCIAS */
.pref-panel {
    background: rgba(26,26,46,0.97); border: 1px solid rgba(155,141,255,0.25);
    border-radius: 16px; padding: 20px 24px; margin-bottom: 20px;
    backdrop-filter: blur(14px); box-shadow: 0 8px 40px rgba(106,61,232,0.25);
    animation: fadeInDown 0.18s ease;
}
@keyframes fadeInDown {
    from { opacity:0; transform:translateY(-8px); }
    to   { opacity:1; transform:translateY(0); }
}

/* BADGES */
.badge-parcelas { background:rgba(106,61,232,0.25); border:1px solid rgba(155,141,255,0.4); color:#c4b5fd; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-vence    { background:rgba(100,181,246,0.15); border:1px solid rgba(100,181,246,0.35); color:#90cdf4; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-fixa     { background:rgba(251,191,36,0.15); border:1px solid rgba(251,191,36,0.4); color:#fbbf24; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-urgente  { background:rgba(239,68,68,0.2); border:1px solid rgba(239,68,68,0.5); color:#fca5a5; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-hoje     { background:rgba(251,146,60,0.2); border:1px solid rgba(251,146,60,0.5); color:#fdba74; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-pago     { background:rgba(52,211,153,0.1); border:1px solid rgba(52,211,153,0.4); color:#6ee7b7; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }

hr { border-color:rgba(255,255,255,0.07) !important; margin:28px 0 !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1100px; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(155,141,255,0.4); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CONNECTION POOL
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
#  INIT DB
# ─────────────────────────────────────────────
def init_db():
    run_query("""CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE, senha TEXT NOT NULL)""")
    run_query("""CREATE TABLE IF NOT EXISTS licencas_ativas (
        id SERIAL PRIMARY KEY, email TEXT NOT NULL UNIQUE, tipo_licenca TEXT NOT NULL,
        expira_em DATE, criado_em TIMESTAMP NOT NULL DEFAULT NOW())""")
    run_query("""CREATE TABLE IF NOT EXISTS lancamentos (
        id SERIAL PRIMARY KEY, usuario_id INTEGER NOT NULL DEFAULT 0, descricao TEXT NOT NULL,
        valor_total NUMERIC(12,2) NOT NULL, parcelas_totais INTEGER NOT NULL,
        parcelas_pagas INTEGER NOT NULL DEFAULT 0, inicio_pagamento DATE NOT NULL,
        final_pagamento DATE, recorrente SMALLINT NOT NULL DEFAULT 0, pago BOOLEAN NOT NULL DEFAULT FALSE)""")
    run_query("""CREATE TABLE IF NOT EXISTS feedbacks (
        id SERIAL PRIMARY KEY, usuario_id INTEGER NOT NULL, mensagem TEXT NOT NULL,
        criado_em TIMESTAMP NOT NULL DEFAULT NOW())""")
    run_query("""CREATE TABLE IF NOT EXISTS reset_tokens (
        id SERIAL PRIMARY KEY, email TEXT NOT NULL, token TEXT NOT NULL UNIQUE,
        criado_em TIMESTAMP NOT NULL DEFAULT NOW(), usado BOOLEAN NOT NULL DEFAULT FALSE)""")
    for col, defn in [
        ("recorrente","SMALLINT NOT NULL DEFAULT 0"), ("usuario_id","INTEGER NOT NULL DEFAULT 0"),
        ("pago","BOOLEAN NOT NULL DEFAULT FALSE"),    ("parcelas_pagas","INTEGER NOT NULL DEFAULT 0"),
    ]:
        run_query(f"""DO $$ BEGIN IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns WHERE table_name='lancamentos' AND column_name='{col}'
        ) THEN ALTER TABLE lancamentos ADD COLUMN {col} {defn}; END IF; END$$""")
    run_query("""DO $$ BEGIN IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns WHERE table_name='usuarios' AND column_name='telefone'
    ) THEN ALTER TABLE usuarios ADD COLUMN telefone TEXT DEFAULT ''; END IF; END$$""")
    # MISSÃO 1: garante que a coluna salario existe na tabela usuarios
    run_query("""DO $$ BEGIN IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns WHERE table_name='usuarios' AND column_name='salario'
    ) THEN ALTER TABLE usuarios ADD COLUMN salario NUMERIC(12,2) NOT NULL DEFAULT 0; END IF; END$$""")

@st.cache_resource
def init_db_once():
    init_db()

try:
    init_db_once()
except Exception as e:
    st.error(f"❌ Erro ao conectar ao banco: {e}")
    st.stop()

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def hash_senha(s): return hashlib.sha256(s.encode()).hexdigest()
def email_valido(e): return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e))
def telefone_valido(tel): d = re.sub(r'\D','',tel); return 10 <= len(d) <= 13
def to_date(val):
    if val is None: return None
    if isinstance(val, date): return val
    if hasattr(val, "date"): return val.date()
    return date.fromisoformat(str(val))

def _token_secret():
    return st.secrets.get("token_secret", "dev-fallback-inseguro-troque-nos-secrets")

def gerar_token_sessao(uid):
    payload = str(uid)
    sig = hmac.new(_token_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"

def validar_token_sessao(token):
    try:
        payload, sig_r = token.rsplit(".", 1)
        sig_e = hmac.new(_token_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig_e, sig_r): return int(payload)
    except: pass
    return None

# ─────────────────────────────────────────────
#  PAYWALL
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def verificar_status_licenca(email):
    try:
        rows = run_query("SELECT * FROM licencas_ativas WHERE email=%s", (email.strip().lower(),), fetch=True)
        if not rows: return False, "não_autorizado"
        l = rows[0]
        if l["tipo_licenca"] == "vitalicio": return True, "vitalicio"
        if l["tipo_licenca"] == "assinatura":
            if l["expira_em"] is None: return True, "assinatura_valida"
            return (True,"assinatura_valida") if to_date(l["expira_em"]) >= date.today() else (False,"assinatura_expirada")
        return False, "invalido"
    except: return False, "erro"

# ─────────────────────────────────────────────
#  RESET DE SENHA
# ─────────────────────────────────────────────
def gerar_token_reset(email):
    try:
        run_query("UPDATE reset_tokens SET usado=TRUE WHERE email=%s AND usado=FALSE", (email.strip().lower(),))
        token = str(_secrets.randbelow(900000) + 100000)
        run_query("INSERT INTO reset_tokens (email, token) VALUES (%s,%s)", (email.strip().lower(), token))
        return token
    except Exception as e:
        st.error(f"❌ Erro ao gerar token: {e}"); return None

def validar_token_reset(email, token):
    try:
        rows = run_query(
            "SELECT id FROM reset_tokens WHERE email=%s AND token=%s AND usado=FALSE AND criado_em > NOW() - INTERVAL '15 minutes'",
            (email.strip().lower(), token.strip()), fetch=True)
        return bool(rows)
    except: return False

def consumir_token_reset(email, token):
    try:
        run_query("UPDATE reset_tokens SET usado=TRUE WHERE email=%s AND token=%s", (email.strip().lower(), token.strip()))
        return True
    except: return False

def trocar_senha(email, nova):
    try:
        run_query("UPDATE usuarios SET senha=%s WHERE email=%s", (hash_senha(nova), email.strip().lower()))
        return True
    except Exception as e:
        st.error(f"❌ {e}"); return False

def enviar_email_reset(destinatario, token):
    try:
        cfg = st.secrets["email"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🔐 Gastei — Código de Redefinição de Senha"
        msg["From"] = cfg["remetente"]; msg["To"] = destinatario
        html = f"""<div style="font-family:Sora,sans-serif;max-width:480px;margin:auto;background:#1a1a2e;border-radius:16px;padding:40px;color:#e8e4ff;">
            <div style="text-align:center;font-size:48px;margin-bottom:8px;">💳</div>
            <h2 style="text-align:center;background:linear-gradient(90deg,#9b8dff,#64b5f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:24px;">Redefinição de Senha</h2>
            <p style="color:#9ca3af;text-align:center;margin-bottom:32px;">Use o código abaixo. Ele expira em <strong style="color:#e8e4ff;">15 minutos</strong>.</p>
            <div style="background:#6a3de8;border-radius:12px;padding:20px;text-align:center;letter-spacing:12px;font-size:36px;font-weight:700;color:#fff;font-family:'JetBrains Mono',monospace;margin-bottom:28px;">{token}</div>
            <p style="color:#6b7280;font-size:12px;text-align:center;">Se não solicitou, ignore.<br>Suporte: suporte@finatec.com.br</p></div>"""
        msg.attach(MIMEText(html, "html"))
        porta = int(cfg.get("smtp_port", 587))
        if porta == 465:
            import ssl; ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["smtp_host"], porta, context=ctx) as s:
                s.login(cfg["remetente"], cfg["senha_smtp"]); s.sendmail(cfg["remetente"], destinatario, msg.as_string())
        else:
            with smtplib.SMTP(cfg["smtp_host"], porta, timeout=10) as s:
                s.ehlo(); s.starttls(); s.ehlo(); s.login(cfg["remetente"], cfg["senha_smtp"])
                s.sendmail(cfg["remetente"], destinatario, msg.as_string())
        return True
    except Exception as e:
        st.error(f"❌ Falha ao enviar e-mail: {e}"); return False

# ─────────────────────────────────────────────
#  USUÁRIOS
# ─────────────────────────────────────────────
def criar_usuario(nome, email, senha, telefone=""):
    ok, motivo = verificar_status_licenca(email)
    if not ok:
        msgs = {"não_autorizado": "Acesso Negado! Este e-mail não possui licença ativa.",
                "assinatura_expirada": "Assinatura expirada! Renove para reativar."}
        return False, msgs.get(motivo, "Licença inválida.")
    try:
        run_query("INSERT INTO usuarios (nome,email,senha,telefone) VALUES (%s,%s,%s,%s)",
                  (nome.strip(), email.strip().lower(), hash_senha(senha), telefone.strip()))
        return True, "ok"
    except psycopg2.errors.UniqueViolation:
        return False, "Este e-mail já está cadastrado."
    except Exception as e:
        return False, f"Erro: {e}"

def autenticar_usuario(email, senha):
    try:
        ok, _ = verificar_status_licenca(email)
        if not ok: return "bloqueado"
        rows = run_query("SELECT id,nome FROM usuarios WHERE email=%s AND senha=%s",
                         (email.strip().lower(), hash_senha(senha)), fetch=True)
        return (rows[0]["id"], rows[0]["nome"]) if rows else None
    except: return None

# ─────────────────────────────────────────────
#  MISSÃO 1 — SALÁRIO NO SUPABASE
#  Funções dedicadas: buscar e atualizar
# ─────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def buscar_salario_db(uid: int) -> float:
    """Lê o salário do banco. Cacheado por 2 min para evitar roundtrips."""
    try:
        rows = run_query("SELECT salario FROM usuarios WHERE id=%s", (uid,), fetch=True)
        if rows and rows[0]["salario"] is not None:
            return float(rows[0]["salario"])
    except Exception as e:
        st.error(f"❌ Erro ao buscar salário: {e}")
    return 0.0

def salvar_salario_db(uid: int, valor: float) -> bool:
    """Persiste o salário no Supabase. Chamado SOMENTE ao clicar no botão."""
    try:
        run_query("UPDATE usuarios SET salario=%s WHERE id=%s", (float(valor), uid))
        buscar_salario_db.clear()          # invalida cache para refletir novo valor
        st.session_state.salario = valor   # atualiza estado local imediatamente
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar salário: {e}"); return False

# ─────────────────────────────────────────────
#  LANÇAMENTOS
# ─────────────────────────────────────────────
def inserir_lancamento(uid, desc, valor, parcelas, inicio, final, recorrente):
    try:
        run_query("""INSERT INTO lancamentos
            (usuario_id,descricao,valor_total,parcelas_totais,parcelas_pagas,inicio_pagamento,final_pagamento,recorrente,pago)
            VALUES (%s,%s,%s,%s,0,%s,%s,%s,FALSE)""",
            (uid, desc, float(valor), parcelas, inicio, final or None, 1 if recorrente else 0))
        invalidar_cache_lancamentos()
    except Exception as e: st.error(f"❌ {e}")

# MISSÃO 3 — cache com ttl=60 nas leituras do banco
@st.cache_data(ttl=60, show_spinner=False)
def carregar_lancamentos(uid):
    try:
        rows = run_query("SELECT * FROM lancamentos WHERE usuario_id=%s", (uid,), fetch=True)
        if not rows:
            return pd.DataFrame(columns=["id","usuario_id","descricao","valor_total","parcelas_totais",
                                          "parcelas_pagas","inicio_pagamento","final_pagamento","recorrente","pago"])
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        st.error(f"❌ {e}"); return pd.DataFrame()

def invalidar_cache_lancamentos(): carregar_lancamentos.clear()

def excluir_lancamento(id_):
    try: run_query("DELETE FROM lancamentos WHERE id=%s", (id_,)); invalidar_cache_lancamentos()
    except Exception as e: st.error(f"❌ {e}")

def marcar_pago(id_):
    try: run_query("UPDATE lancamentos SET pago=TRUE WHERE id=%s", (id_,)); invalidar_cache_lancamentos()
    except Exception as e: st.error(f"❌ {e}")

def _prox_mes_date(inicio_pagamento):
    inicio = to_date(inicio_pagamento); dia = inicio.day
    mes = inicio.month % 12 + 1; ano = inicio.year + (1 if inicio.month == 12 else 0)
    try: return date(ano, mes, dia)
    except: return date(ano, mes, calendar.monthrange(ano, mes)[1])

def avancar_parcela_recorrente(id_, inicio):
    try:
        run_query("UPDATE lancamentos SET inicio_pagamento=%s, pago=FALSE WHERE id=%s", (_prox_mes_date(inicio), id_))
        invalidar_cache_lancamentos()
    except Exception as e: st.error(f"❌ {e}")

def avancar_parcela_parcelada_excel(id_, inicio, parc_tot, pagas):
    try:
        prox = pagas + 1
        if prox >= parc_tot:
            run_query("UPDATE lancamentos SET parcelas_pagas=%s, pago=TRUE WHERE id=%s", (parc_tot, id_))
        else:
            run_query("UPDATE lancamentos SET inicio_pagamento=%s, parcelas_pagas=%s WHERE id=%s",
                      (_prox_mes_date(inicio), prox, id_))
        invalidar_cache_lancamentos()
    except Exception as e: st.error(f"❌ {e}")

def inserir_feedback(uid, mensagem):
    try:
        run_query("INSERT INTO feedbacks (usuario_id,mensagem) VALUES (%s,%s)", (uid, mensagem.strip()))
        return True
    except Exception as e: st.error(f"❌ {e}"); return False

# ─────────────────────────────────────────────
#  CÁLCULOS
# ─────────────────────────────────────────────
def calcular_proxima_recorrente(inicio_pagamento):
    hoje = date.today(); inicio = to_date(inicio_pagamento); dia = inicio.day
    def montar(ano, mes):
        try: return date(ano, mes, dia)
        except: return date(ano, mes, (date(ano, mes % 12 + 1, 1) - timedelta(days=1)).day)
    c = montar(hoje.year, hoje.month)
    if c < hoje:
        mes = hoje.month % 12 + 1; ano = hoje.year + (1 if hoje.month == 12 else 0)
        c = montar(ano, mes)
    return c

def calcular_valor_parcela(valor_total, parcelas_totais):
    return float(valor_total) / parcelas_totais if parcelas_totais > 0 else 0.0

def calcular_gasto_mensal(df):
    if df.empty: return 0.0
    df_a = df[~df["pago"].astype(bool)].copy()
    if df_a.empty: return 0.0
    df_a["valor_total"] = df_a["valor_total"].astype(float)
    df_a["parcelas_totais"] = df_a["parcelas_totais"].astype(int)
    rec = df_a[df_a["recorrente"].astype(int) == 1]["valor_total"].sum()
    par = df_a[df_a["recorrente"].astype(int) == 0]
    return float(rec + (par["valor_total"] / par["parcelas_totais"].replace(0, 1)).sum())

# ═════════════════════════════════════════════
#  VALIDAÇÃO TOKEN DE SESSÃO NA URL
# ═════════════════════════════════════════════
if st.session_state.usuario_id is None:
    token_param = st.query_params.get("s", None)
    if token_param:
        uid_val = validar_token_sessao(token_param)
        if uid_val:
            try:
                rows = run_query("SELECT id,nome FROM usuarios WHERE id=%s", (uid_val,), fetch=True)
                if rows:
                    st.session_state.usuario_id   = rows[0]["id"]
                    st.session_state.usuario_nome = rows[0]["nome"]
                else: st.query_params.clear()
            except: pass
        else: st.query_params.clear()

# ═════════════════════════════════════════════
#  TELA DE LOGIN / CADASTRO (INTERNACIONALIZADA)
# ═════════════════════════════════════════════
if st.session_state.usuario_id is None:

    # ── MISSÃO 2 — Seletor de idioma com key estática na tela de login ──
    _lang_map = {"🇧🇷 Português": "PT", "🇺🇸 English": "EN", "🇫🇷 Français": "FR"}
    _, _lc_lang, _ = st.columns([1, 1.6, 1])
    with _lc_lang:
        _sel_login = st.radio(
            "idioma_login",
            options=list(_lang_map.keys()),
            index=list(_lang_map.values()).index(st.session_state.lang),
            horizontal=True,
            key="seletor_idioma",          # chave estática — nunca reseta
            label_visibility="collapsed"
        )
        _novo_lang_login = _lang_map[_sel_login]
        if _novo_lang_login != st.session_state.lang:
            st.session_state.lang = _novo_lang_login
            st.rerun()   # força reexecução imediata para aplicar tradução sem delay

    # Puxa as traduções atualizadas para a renderização abaixo
    t = get_t()

    _, col_center, _ = st.columns([1, 1.6, 1])
    with col_center:
        st.markdown(f"""
        <div class="login-wrap">
            <div class="login-logo">💳</div>
            <div class="login-title">Gastei - {t.get('login_titulo_app', 'Finanças Premium')}</div>
            <div class="login-sub">{t.get('login_sub_app', 'Controle de Gastos de Alta Performance')}</div>
        </div>
        """, unsafe_allow_html=True)

        aba_login, aba_cadastro = st.tabs([t.get('aba_entrar', "🔑  Entrar"), t.get('aba_criar_conta', "✨  Criar Conta")])

        with aba_login:
            if st.session_state.reset_step == 0:
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                email_login = st.text_input(t.get('input_email', "E-mail"), key="login_email", placeholder="seu@email.com")
                senha_login = st.text_input(t.get('input_senha', "Senha"), type="password", key="login_senha", placeholder="••••••••")
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                
                if st.button(t.get('btn_entrar_seta', "Entrar →"), key="btn_login"):
                    if not email_login or not senha_login:
                        st.error(t.get('err_preencha_dados', "Preencha e-mail e senha."))
                    else:
                        resultado = autenticar_usuario(email_login, senha_login)
                        if resultado == "bloqueado":
                            st.error(t.get('err_bloqueado', "🛑 Acesso Bloqueado! Assinatura expirada ou e-mail não autorizado."))
                        elif resultado:
                            st.session_state.usuario_id   = resultado[0]
                            st.session_state.usuario_nome = resultado[1]
                            st.query_params["s"] = gerar_token_sessao(resultado[0])
                            st.rerun()
                        else:
                            st.error(t.get('err_dados_invalidos', "E-mail ou senha incorretos."))
                            
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                st.markdown('<div class="btn-link">', unsafe_allow_html=True)
                if st.button(t.get('link_esqueceu', "🔑 Esqueci minha senha"), key="btn_forgot"):
                    st.session_state.reset_step = 1; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
                numero_suporte = "5567991158892"
                msg_wa = t.get('msg_suporte_wa', "Olá! Quero verificar o status do meu acesso no app Gastei.")
                link_wa = f"https://wa.me/{numero_suporte}?text={msg_wa.replace(' ','%20')}"
                st.markdown(f"""
                <div style='text-align:center;margin-top:8px;'>
                    <a href="{link_wa}" target="_blank" style="color:#9b8dff;font-size:13px;text-decoration:none;opacity:0.8;">
                        🔒 {t.get('link_suporte', 'Problemas com o acesso? — Falar com o Suporte')}</a>
                </div>
                <div style='text-align:center;margin-top:8px;'>
                    <a href="https://finatechlab.com/pagina-vendas-gastei/" target="_blank"
                       style="color:#64b5f6;font-size:12px;text-decoration:none;opacity:0.65;">
                        🛒 {t.get('link_vendas', 'Ainda não tem acesso? Conheça o Gastei →')}</a>
                </div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander(t.get('expander_termos', "🛡️ Termos de Uso e Política de Privacidade")):
                    st.write(t.get('texto_termos', "Seus dados financeiros são armazenados de forma criptografada e privativa. Não compartilhamos suas informações."))

            elif st.session_state.reset_step == 1:
                st.info(t.get('info_reset_email', "📧 Informe o e-mail cadastrado. Enviaremos um código de 6 dígitos."))
                email_reset = st.text_input(t.get('input_email_cadastrado', "E-mail cadastrado"), key="reset_email_input", placeholder="seu@email.com")
                col_env, col_vol = st.columns(2)
                with col_env:
                    if st.button(t.get('btn_enviar_codigo', "Enviar código →"), key="btn_send_token"):
                        if not email_valido(email_reset): st.error(t.get('err_email_invalido', "E-mail inválido."))
                        else:
                            rows = run_query("SELECT id FROM usuarios WHERE email=%s", (email_reset.strip().lower(),), fetch=True)
                            if not rows: st.error(t.get('err_email_nao_encontrado', "E-mail não encontrado."))
                            else:
                                tok = gerar_token_reset(email_reset)
                                if tok and enviar_email_reset(email_reset, tok):
                                    st.session_state.reset_email = email_reset.strip().lower()
                                    st.session_state.reset_step  = 2; st.rerun()
                with col_vol:
                    if st.button(t.get('link_voltar_login', "← Voltar"), key="btn_back_1"):
                        st.session_state.reset_step = 0; st.rerun()

            elif st.session_state.reset_step == 2:
                msg_sucesso_cod = t.get('sucesso_codigo_enviado', "✅ Código enviado para **{}**.").format(st.session_state.reset_email)
                st.success(msg_sucesso_cod)
                codigo = st.text_input(t.get('input_codigo_digitos', "Código de 6 dígitos"), key="reset_token_input", placeholder="123456", max_chars=6)
                nova1  = st.text_input(t.get('input_nova_senha', "Nova senha"), type="password", key="reset_pass1", placeholder="Mínimo 6 caracteres")
                nova2  = st.text_input(t.get('input_confirmar_nova', "Confirmar nova senha"), type="password", key="reset_pass2", placeholder="Repita a senha")
                col_conf, col_vol2 = st.columns(2)
                with col_conf:
                    if st.button(t.get('btn_redefinir_senha', "Redefinir senha →"), key="btn_confirm_reset"):
                        erros = []
                        if not codigo.strip(): erros.append(t.get('err_informe_codigo', "Informe o código."))
                        if len(nova1) < 6:     erros.append(t.get('err_senha_curta', "Mínimo 6 caracteres."))
                        if nova1 != nova2:     erros.append(t.get('err_senhas_diferentes', "Senhas não conferem."))
                        if erros:
                            for e in erros: st.error(e)
                        elif not validar_token_reset(st.session_state.reset_email, codigo):
                            st.error(t.get('err_codigo_expirado', "Código inválido ou expirado."))
                        else:
                            if trocar_senha(st.session_state.reset_email, nova1):
                                consumir_token_reset(st.session_state.reset_email, codigo)
                                st.success(t.get('sucesso_senha_redefinida', "🎉 Senha redefinida! Faça login."))
                                st.session_state.reset_step = 0; st.session_state.reset_email = ""; st.rerun()
                with col_vol2:
                    if st.button(t.get('link_voltar_login', "← Voltar"), key="btn_back_2"):
                        st.session_state.reset_step = 1; st.rerun()

        with aba_cadastro:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            nome_cad   = st.text_input(t.get('input_nome', "Seu nome"),            key="cad_nome",   placeholder="João Silva")
            email_cad  = st.text_input(t.get('input_email', "E-mail"),              key="cad_email",  placeholder="O mesmo e-mail usado na compra")
            tel_cad    = st.text_input(t.get('input_telefone', "WhatsApp / Telefone"), key="cad_tel",    placeholder="(67) 99999-9999")
            senha_cad  = st.text_input(t.get('input_senha', "Senha"),           type="password", key="cad_senha",  placeholder="Mínimo 6 caracteres")
            senha_cad2 = st.text_input(t.get('input_confirmar_senha', "Confirmar senha"), type="password", key="cad_senha2", placeholder="Repita a senha")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            
            if st.button(t.get('btn_criar_conta', "Criar minha conta →"), key="btn_cadastro"):
                erros = []
                if not all([nome_cad, email_cad, tel_cad, senha_cad, senha_cad2]):
                    erros.append(t.get('err_campos_vazios', "Preencha todos os campos."))
                elif not email_valido(email_cad):  erros.append(t.get('err_email_invalido', "E-mail inválido."))
                elif not telefone_valido(tel_cad): erros.append(t.get('err_tel_invalido', "Telefone inválido."))
                elif len(senha_cad) < 6:           erros.append(t.get('err_senha_curta', "Senha: mínimo 6 caracteres."))
                elif senha_cad != senha_cad2:      erros.append(t.get('err_senhas_diferentes', "Senhas não conferem."))
                if erros:
                    for e in erros: st.error(e)
                else:
                    ok, msg = criar_usuario(nome_cad, email_cad, senha_cad, tel_cad)
                    if ok: st.success(t.get('sucesso_conta_criada', "✅ Conta criada! Faça login na aba ao lado."))
                    else:  st.error(msg)
                    
            st.markdown(f"""<div style='text-align:center;margin-top:16px;'>
                <a href="https://finatechlab.com/pagina-vendas-gastei/" target="_blank"
                   style="color:#64b5f6;font-size:12px;text-decoration:none;opacity:0.65;">
                    🛒 {t.get('link_vendas_planos', 'Ainda não comprou? Conheça os planos →')}</a></div>""", unsafe_allow_html=True)

    st.stop()

# ═════════════════════════════════════════════
#  APP PRINCIPAL
# ═════════════════════════════════════════════
uid = st.session_state.usuario_id
st.query_params["s"] = gerar_token_sessao(uid)

# ─────────────────────────────────────────────
# MISSÃO 1 — Carrega salário do banco UMA VEZ por sessão logo após o login
# ─────────────────────────────────────────────
if not st.session_state._salario_carregado:
    st.session_state.salario = buscar_salario_db(uid)
    st.session_state._salario_carregado = True

# ─────────────────────────────────────────────
#  SIDEBAR / SELETOR DE IDIOMA GLOBAL
# ─────────────────────────────────────────────
with st.sidebar:
    t = get_t()
    st.markdown(f"### {t.get('idioma_label', '🌐 Idioma / Language')}")
    
    # 1. Calcula dinamicamente o índice inicial correto para o componente
    _indice_padrao = 0
    if st.session_state.lang == "EN":
        _indice_padrao = 1
    elif st.session_state.lang == "FR":
        _indice_padrao = 2
        
    # 2. Componente de Seleção Limpo e Unificado
    _smap = {"🇧🇷 Português": "PT", "🇺🇸 English": "EN", "🇫🇷 Français": "FR"}
    _sel_idioma_sidebar = st.selectbox(
        label="Select Language",
        options=list(_smap.keys()),
        index=_indice_padrao,
        key="seletor_idioma",  # Chave lida pelo interceptador do topo do arquivo
        label_visibility="collapsed"
    )
    
    # 3. Faz a mudança em tempo de execução de forma limpa
    _novo_lang = _smap[_sel_idioma_sidebar]
    if _novo_lang != st.session_state.lang:
        st.session_state.lang = _novo_lang
        st.rerun()

    st.markdown("---")
    
    # MISSÃO 1 — Salário na sidebar (Apenas visível se logado, usando tratamento seguro .get)
    st.markdown(f"### {t.get('salario_titulo', 'Salário Atual')}")
    _sal_sb = st.number_input(
        t.get('salario_input', 'Valor'), min_value=0.0, step=100.0, format="%.2f",
        value=float(st.session_state.salario),
        key="input_salario_sidebar", label_visibility="collapsed"
    )
    if st.button(t.get('salario_btn', 'Salvar Salário'), key="btn_sal_sidebar"):
        if 'uid' in locals() or 'uid' in globals():
            if salvar_salario_db(st.session_state.usuario_id, _sal_sb):
                st.success(t.get('salario_salvo', 'Salvo com sucesso!'))

# ── Recarrega t após possível mudança na sidebar ──
t = get_t()

# ─────────────────────────────────────────────
#  HEADER DA APLICAÇÃO (LOGADO)
# ─────────────────────────────────────────────
col_titulo, col_usuario, col_pref, col_logout = st.columns([5, 2, 0.6, 0.8])
with col_titulo:
    st.markdown("# GASTEI ⚡")
    st.markdown(f"<p style='color:#6b7280;margin-top:-12px;margin-bottom:28px;'>{t.get('app_subtitle', '')}</p>", unsafe_allow_html=True)

with col_usuario:
    st.markdown(f"<div style='text-align:right;padding-top:18px;font-size:13px;color:#9ca3af;'>{t.get('ola', 'Olá')}, <strong style='color:#c4b5fd'>{st.session_state.usuario_nome}</strong> 👋</div>", unsafe_allow_html=True)

with col_pref:
    st.markdown("<div style='padding-top:14px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="pref-btn">', unsafe_allow_html=True)
    if st.button("⚙️", key="btn_pref_toggle"):
        st.session_state.pref_aberto = not st.session_state.pref_aberto
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col_logout:
    st.markdown("<div style='padding-top:14px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button(t.get('sair', 'Sair'), key="btn_logout"):
        for k in ["usuario_id", "usuario_nome", "salario", "pref_aberto", "_salario_carregado"]:
            if k in ("usuario_id", "usuario_nome"): 
                st.session_state[k] = None
            elif k == "pref_aberto":               
                st.session_state[k] = False
            elif k == "_salario_carregado":        
                st.session_state[k] = False
            else:                                  
                st.session_state[k] = 0.0
        st.query_params.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
# ── Painel ⚙️ inline ─────────────────────────────
if st.session_state.pref_aberto:
    st.markdown('<div class="pref-panel">', unsafe_allow_html=True)
    _pc1, _pc2, _pc3 = st.columns([1.2, 1.5, 0.6])
    with _pc1:
        # MISSÃO 2 — radio dentro do painel usa key estática (compartilhada com sidebar via session_state)
        st.markdown(f"<p style='color:#9b8dff;font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;'>{t['idioma_label']}</p>", unsafe_allow_html=True)
        _pmap = {"Português": "PT", "English": "EN", "Français": "FR"}
        _psel = st.radio(
            "lang_panel", options=list(_pmap.keys()),
            index=list(_pmap.values()).index(st.session_state.lang),
            key="lang_radio_panel", label_visibility="collapsed"
        )
        _novo_lang_panel = _pmap[_psel]
        if _novo_lang_panel != st.session_state.lang:
            st.session_state.lang = _novo_lang_panel
            st.rerun()
        t = get_t()
    with _pc2:
        # MISSÃO 1 — salário no painel: só salva no DB ao clicar no botão
        st.markdown(f"<p style='color:#9b8dff;font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;'>💰 {t['salario_titulo']}</p>", unsafe_allow_html=True)
        _sal_p = st.number_input(
            t["salario_input"], min_value=0.0, step=100.0, format="%.2f",
            value=float(st.session_state.salario),
            key="sal_panel", label_visibility="collapsed"
        )
        if st.button(t["salario_btn"], key="btn_sal_panel"):
            if salvar_salario_db(uid, _sal_p):
                st.success(t["salario_salvo"])
    with _pc3:
        st.markdown("<div style='padding-top:26px'></div>", unsafe_allow_html=True)
        if st.button(f"✕ {t['pref_fechar']}", key="btn_pref_close"):
            st.session_state.pref_aberto = False; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Abas principais ─────────────────────────────
aba_principal, aba_feedback = st.tabs([t["aba_gastos"], t["aba_feedback"]])

# ══════════════════════════════
# ABA 1 — GASTOS
# ══════════════════════════════
with aba_principal:
    # MISSÃO 3 — uma única chamada cacheada; df_all é reutilizado tanto nos cards quanto no histórico
    df_all       = carregar_lancamentos(uid)
    total_saidas = df_all["valor_total"].astype(float).sum() if not df_all.empty else 0.0
    gasto_mensal = calcular_gasto_mensal(df_all) if not df_all.empty else 0.0
    salario      = float(st.session_state.salario)

    # ── 3 cards de resumo ──────────────────────
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""<div class="total-card">
            <div><div class="total-label">{t['total_saidas']}</div>
                 <div class="total-value">R$ {total_saidas:,.2f}</div></div>
            <div class="total-icon">📊</div></div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="parcela-card">
            <div><div class="parcela-label">{t['comprometido_mes']}</div>
                 <div class="parcela-value">R$ {gasto_mensal:,.2f}</div></div>
            <div style="font-size:48px;opacity:0.4;">📅</div></div>""", unsafe_allow_html=True)
    with col_c:
        if salario > 0:
            pct  = (gasto_mensal / salario) * 100
            cls  = "salario-card alerta" if pct >= 70 else "salario-card"
            icon = "🚨" if pct >= 70 else "💰"
            st.markdown(f"""<div class="{cls}">
                <div><div class="salario-label">{t['salario_comprometido']}</div>
                     <div class="salario-value">{pct:.1f}%</div>
                     <div style="font-size:11px;color:#6b7280;margin-top:4px;">{t['pct_label']}</div></div>
                <div style="font-size:48px;opacity:0.5;">{icon}</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="salario-card" style="opacity:0.55;">
                <div><div class="salario-label">{t['salario_comprometido']}</div>
                     <div class="salario-value">--%</div></div>
                <div style="font-size:48px;opacity:0.3;">💰</div></div>""", unsafe_allow_html=True)
            st.caption(t["salario_zero_aviso"])

    # ── Formulário novo lançamento ─────────────
    # MISSÃO 3 — st.form isola todos os inputs; o Streamlit só re-renderiza
    #            a simulação ao submeter, eliminando reruns a cada dígito digitado.
    #            A simulação leve fica em st.empty() fora do form para feedback visual.
    st.markdown(f"### {t['novo_lancamento']}")
    st.markdown('<div class="form-section">', unsafe_allow_html=True)

    _sim_placeholder = st.empty()   # exibe prévia da simulação ACIMA do form (sem travar inputs)

    with st.form("form_novo_lancamento", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            descricao = st.text_input(t["o_que_comprou"], placeholder=t["placeholder_desc"])
        with col2:
            valor_total = st.number_input(t["valor_total"], min_value=0.0, step=0.01, format="%.2f", value=0.0)

        is_recorrente = st.checkbox(t["conta_fixa"])

        if is_recorrente:
            col4, _ = st.columns([1, 2])
            with col4:
                inicio_pagamento = st.date_input(t["dia_vencimento"], value=date.today(), format="DD/MM/YYYY")
            parcelas_totais = 0; final_pagamento = None
            # Prévia apenas se campos preenchidos — dentro do form é estático até Submit
            if descricao and valor_total > 0:
                proxima_rec = calcular_proxima_recorrente(inicio_pagamento)
                st.markdown("<hr>", unsafe_allow_html=True)
                pc1, pc2, pc3 = st.columns(3)
                with pc1: st.markdown(f"{t['valor_mensal']} `R$ {valor_total:,.2f}`")
                with pc2: st.markdown(f"{t['tipo_recorrente']} `🔁 Recorrente`")
                with pc3: st.markdown(f"{t['prox_vencimento']} `{proxima_rec.strftime('%d/%m/%Y')}`")
        else:
            col3, col4 = st.columns(2)
            with col3:
                parcelas_totais = st.number_input(t["num_parcelas"], min_value=1, max_value=360, step=1, value=1)
            with col4:
                inicio_pagamento = st.date_input(t["data_primeiro_venc"], value=date.today(), format="DD/MM/YYYY")
            final_pagamento = None
            if descricao and valor_total > 0:
                val_p = calcular_valor_parcela(valor_total, parcelas_totais)
                st.markdown("<hr>", unsafe_allow_html=True)
                pc1, pc2, pc3 = st.columns(3)
                with pc1: st.markdown(f"{t['valor_parcela']} `R$ {val_p:.2f}`")
                with pc2: st.markdown(f"{t['parcelas_restantes']} `{parcelas_totais}x`")
                with pc3: st.markdown(f"{t['venc_parcela1']} `{inicio_pagamento.strftime('%d/%m/%Y')}`")

        # ── SIMULAÇÃO DE IMPACTO (dentro do form — processa ao Submit) ──
        if valor_total > 0 and salario > 0:
            parc_sim    = parcelas_totais if (parcelas_totais and not is_recorrente) else 1
            mensal_novo = valor_total / parc_sim if parc_sim > 0 else valor_total
            total_sim   = gasto_mensal + mensal_novo
            pct_sim     = (total_sim / salario) * 100
            st.markdown(t["sim_info"].format(total_sim, pct_sim))
            if pct_sim > 70:
                st.markdown(f"""<div class="alerta-simulacao">
                    <span class="pct-destaque">⚠️ {pct_sim:.1f}%</span>
                    {t["sim_alerta"].format(pct_sim)}
                </div>""", unsafe_allow_html=True)
            else:
                st.success(t["sim_ok"])
        elif valor_total > 0 and salario == 0:
            st.caption(t["salario_zero_aviso"])

        col_btn, _ = st.columns([1, 3])
        with col_btn:
            submitted = st.form_submit_button(t["salvar_lancamento"])

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Processa o submit FORA do form (sem bloquear re-render do form) ──
    if submitted:
        erros = []
        if not descricao.strip(): erros.append(t["err_descricao"])
        if valor_total <= 0:      erros.append(t["err_valor"])
        if erros:
            for e in erros: st.error(e)
        else:
            inserir_lancamento(uid, descricao.strip(), valor_total, parcelas_totais,
                               inicio_pagamento, final_pagamento, is_recorrente)
            st.success(t["salvo_sucesso"].format(descricao))
            st.rerun()

    # ── Histórico ──────────────────────────────
    # MISSÃO 3 — reutiliza df_all já cacheado; não faz segunda consulta ao banco
    st.markdown(t["historico"])
    df = df_all.copy()
    if df.empty:
        st.markdown(f"<div style='text-align:center;padding:60px 20px;color:#4b5563;'><div style='font-size:48px;'>📭</div>{t['nenhum_lancamento']}</div>", unsafe_allow_html=True)
    else:
        busca = st.text_input(t["filtrar"], placeholder=t["placeholder_busca"], key="busca")
        if busca.strip():
            df = df[df["descricao"].str.contains(busca.strip(), case=False, na=False)]

        hoje = date.today()
        df["_pago"] = df["pago"].astype(bool)
        df["_rec"]  = df["recorrente"].astype(int) == 1
        df["_venc"] = df.apply(lambda r: calcular_proxima_recorrente(to_date(r["inicio_pagamento"]))
                                if r["_rec"] else to_date(r["inicio_pagamento"]), axis=1)
        def _grp(row):
            if row["_pago"]: return (4, date(9999,12,31))
            v = row["_venc"]
            if v < hoje:                          return (0, v)
            if v == hoje:                         return (1, v)
            if v <= hoje + timedelta(days=3):     return (2, v)
            return (3, v)
        df["_sort"] = df.apply(_grp, axis=1)
        df = df.sort_values("_sort").drop(columns=["_pago","_rec","_venc","_sort"])

        # ── Banners de alerta ──
        _ativos   = ~df["pago"].astype(bool)
        _vc       = df.apply(lambda r: calcular_proxima_recorrente(to_date(r["inicio_pagamento"]))
                             if int(r["recorrente"]) == 1 else to_date(r["inicio_pagamento"]), axis=1)
        n_atr  = int((_ativos & (_vc < hoje)).sum())
        n_hj   = int((_ativos & (_vc == hoje)).sum())
        n_brv  = int((_ativos & (_vc > hoje) & (_vc <= hoje + timedelta(days=3))).sum())

        if n_atr:
            pl = t["conta_atrasada_s"] if n_atr == 1 else t["conta_atrasada_p"]
            st.markdown(f"""<div class="alerta-banner">
                🚨 <span class="count">{n_atr}</span> {pl} — {t['alerta_atrasada_sufixo']}
            </div>""", unsafe_allow_html=True)
        if n_hj:
            pl = t["conta_hoje_s"] if n_hj == 1 else t["conta_hoje_p"]
            st.markdown(f"""<div class="hoje-banner">
                🔥 <span style="background:#f97316;color:#fff;border-radius:999px;padding:1px 8px;font-weight:800;">{n_hj}</span>
                {pl} — {t['alerta_hoje_sufixo']}
            </div>""", unsafe_allow_html=True)
        if n_brv and not n_atr and not n_hj:
            pl = t["conta_breve_s"] if n_brv == 1 else t["conta_breve_p"]
            st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;background:rgba(234,179,8,0.09);
                border:1px solid rgba(234,179,8,0.3);border-radius:10px;padding:7px 14px;
                font-size:11px;font-weight:700;color:#fde047;margin-bottom:8px;">
                ⚡ {n_brv} {pl} — {t['alerta_breve_sufixo']}
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""<div style="display:grid;grid-template-columns:2.2fr 1fr 1fr 1fr 0.8fr;
            padding:10px 24px;font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">
            <div>{t['col_descricao']}</div><div>{t['col_valor']}</div>
            <div>{t['col_vencimento']}</div><div>{t['col_situacao']}</div>
            <div style="text-align:center">{t['col_acoes']}</div>
        </div>""", unsafe_allow_html=True)

        for _, row in df.iterrows():
            id_           = row["id"]
            desc          = row["descricao"]
            v_tot         = float(row["valor_total"])
            parc_tot      = int(row["parcelas_totais"])
            parc_pagas    = int(row.get("parcelas_pagas", 0))
            parc_rest     = max(0, parc_tot - parc_pagas)
            eh_fixa       = int(row["recorrente"]) == 1
            pago_fim      = bool(row["pago"])
            val_exibir    = v_tot if eh_fixa else calcular_valor_parcela(v_tot, parc_tot)
            venc_data     = calcular_proxima_recorrente(to_date(row["inicio_pagamento"])) if eh_fixa else to_date(row["inicio_pagamento"])

            col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns([2.2, 1, 1, 1, 0.8])
            with col_r1:
                sub = f"{t['total_label']} R$ {v_tot:,.2f} · {t['inicio_label']} {to_date(row['inicio_pagamento']).strftime('%d/%m/%Y')}" if not eh_fixa else t["conta_mensal_fixa"]
                st.markdown(f"<div style='padding-top:12px'><strong style='color:#fff;font-size:15px;'>{desc}</strong><br><span style='color:#6b7280;font-size:11px;'>{sub}</span></div>", unsafe_allow_html=True)
            with col_r2:
                lbl = t["label_mensal"] if eh_fixa else t["label_parcela"]
                st.markdown(f"<div style='padding-top:12px'><strong style='font-family:JetBrains Mono;color:#9b8dff;font-size:16px;'>R$ {val_exibir:,.2f}</strong><br><span style='color:#6b7280;font-size:11px;'>{lbl}</span></div>", unsafe_allow_html=True)
            with col_r3:
                if pago_fim:
                    st.markdown("<div style='padding-top:18px'><span class='badge-pago'>Concluído ✅</span></div>", unsafe_allow_html=True)
                elif venc_data == hoje:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-hoje'>🔥 HOJE ({venc_data.strftime('%d/%m/%Y')})</span></div>", unsafe_allow_html=True)
                elif venc_data < hoje:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-urgente'>⚠️ ATRASADO ({venc_data.strftime('%d/%m/%Y')})</span></div>", unsafe_allow_html=True)
                elif venc_data <= hoje + timedelta(days=3):
                    dr = (venc_data - hoje).days
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-em-breve'>⚡ {venc_data.strftime('%d/%m/%Y')} (em {dr}d)</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-vence'>📅 {venc_data.strftime('%d/%m/%Y')}</span></div>", unsafe_allow_html=True)
            with col_r4:
                if pago_fim:
                    st.markdown(f"<div style='padding-top:18px;color:#4b5563;font-size:13px;'>{t['divida_encerrada']}</div>", unsafe_allow_html=True)
                elif eh_fixa:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-fixa'>{t['recorrente_inf']}</span></div>", unsafe_allow_html=True)
                else:
                    try:
                        mf = max(0, parc_rest - 1)
                        du = venc_data.day
                        mu = (venc_data.month + mf - 1) % 12 + 1
                        au = venc_data.year + ((venc_data.month + mf - 1) // 12)
                        try:    dup = date(au, mu, du)
                        except: dup = date(au, mu, calendar.monthrange(au, mu)[1])
                        txt_u = dup.strftime('%d/%m/%Y')
                    except: txt_u = "--/--/----"
                    falta = max(0.0, v_tot - (parc_pagas * val_exibir))
                    st.markdown(f"""<div style='padding-top:4px'>
                        <span class='badge-parcelas'>{parc_rest}x {t['x_restantes']}</span><br>
                        <span style='color:#6b7280;font-size:11px;display:block;margin-top:2px;'>{t['ultima_parcela']} <strong style='color:#90cdf4;'>{txt_u}</strong></span>
                        <span style='color:#6b7280;font-size:10px;display:block;'>{t['falta_pagar']} R$ {falta:,.2f}</span>
                    </div>""", unsafe_allow_html=True)
            with col_r5:
                if not pago_fim:
                    st.markdown('<div class="btn-pagar">', unsafe_allow_html=True)
                    if st.button(t["btn_pagar"], key=f"btn_p_{id_}"):
                        if eh_fixa: avancar_parcela_recorrente(id_, row["inicio_pagamento"])
                        else: avancar_parcela_parcelada_excel(id_, row["inicio_pagamento"], parc_tot, parc_pagas)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<div class="btn-quitar">', unsafe_allow_html=True)
                    if st.button(t["btn_quitar"], key=f"btn_q_{id_}"):
                        marcar_pago(id_); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    if st.button(t["btn_excluir"], key=f"btn_del_{id_}"):
                        excluir_lancamento(id_); st.rerun()

        st.markdown(f"<br><br><center style='color:#4b5563;font-size:12px;'>{t['rodape']}</center>", unsafe_allow_html=True)

# ══════════════════════════════
# ABA 2 — FEEDBACK
# ══════════════════════════════
with aba_feedback:
    t = get_t()
    st.markdown(t["feedback_titulo"])
    st.markdown(f"<p style='color:#9ca3af;margin-top:-10px;'>{t['feedback_sub']}</p>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        mensagem_fb = st.text_area(t["feedback_label"], placeholder=t["feedback_placeholder"], height=160, key="feedback_texto")
        col_fb, _ = st.columns([1, 3])
        with col_fb:
            if st.button(t["feedback_btn"], key="btn_feedback"):
                if not mensagem_fb.strip():       st.error(t["feedback_vazio"])
                elif len(mensagem_fb.strip()) < 8: st.error(t["feedback_curto"])
                else:
                    if inserir_feedback(uid, mensagem_fb):
                        st.success(t["feedback_ok"]); st.balloons()
        st.markdown('</div>', unsafe_allow_html=True)
