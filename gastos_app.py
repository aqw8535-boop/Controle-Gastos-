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
#  FUNÇÃO GATILHO PARA TER REFRESH IMEDIATO
# ─────────────────────────────────────────────
def callback_mudar_idioma():
    mapeamento_opcoes = {"Português": "PT", "English": "EN", "Français": "FR"}
    # Grava no estado o código correspondente à escolha visual da tela
    st.session_state["lang"] = mapeamento_opcoes.get(st.session_state["seletor_visual_idioma"], "PT")

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

# ─────────────────────────────────────────────
#  DICIONÁRIO I18N — TRILÍNGUE (PT, EN, FR)
# ─────────────────────────────────────────────
IDIOMAS = {
    "PT": {
        "app_subtitle":         "Finanças Pessoais Premium Inteligentes",
        "ola":                  "Olá",
        "sair":                 "Sair 🚪",
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
        "salario_salvo":        "✅ Salário updated!",
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
    },
    "EN": {
        "app_subtitle":         "Intelligent Premium Personal Finance",
        "ola":                  "Hello",
        "sair":                 "Logout 🚪",
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
    },
    "FR": {
        "app_subtitle":         "Finances Personnelles Premium Intelligentes",
        "ola":                  "Bonjour",
        "sair":                 "Déconnexion 🚪",
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
        "feedback_curto":       "⚠️ Veuillez développer un peu mais votre message.",
        "feedback_ok":          "✅ Retour envoyé avec succès ! Merci beaucoup 🙏",
        "rodape":               "© 2026 Gastei App. Tous droits réservés. Support : finatechsuporte@gmail.com",
        "idioma_label":         "🌐 Langue",
    },
}

# ─────────────────────────────────────────────
#  ATALHO GLOBAL — sempre lê do session_state
# ─────────────────────────────────────────────
def get_t():
    return IDIOMAS[st.session_state.lang]
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

/* LOGIN */
.login-wrap {
    max-width: 460px; margin: 60px auto 0;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(155,141,255,0.2);
    border-radius: 24px; padding: 48px 40px;
    box-shadow: 0 8px 60px rgba(106,61,232,0.25); backdrop-filter: blur(12px);
}
.login-logo  { text-align:center; font-size:52px; margin-bottom:8px; }
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
    border: 1px solid rgba(100,181,246,0.25); border-radius: 20px;
    padding: 24px 32px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3); margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between;
}
.parcela-label { font-size:13px; font-weight:600; letter-spacing:2px; text-transform:uppercase; color:rgba(100,181,246,0.75); margin-bottom:6px; }
.parcela-value { font-family:'JetBrains Mono',monospace; font-size:34px; font-weight:700; color:#64b5f6; }

/* FORMULÁRIO */
.form-section {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px; padding: 28px 32px; margin-bottom: 32px; backdrop-filter: blur(10px);
}

/* LINHAS TABELA */
.lancamento-row {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 18px 24px;
    margin-bottom: 10px;
    display: grid; grid-template-columns: 2.2fr 1fr 1fr 1fr 0.8fr;
    align-items: center; transition: all 0.2s;
}
.lancamento-row:hover { background: rgba(155,141,255,0.08); border-color: rgba(155,141,255,0.3); }
.lancamento-row.fixa  { border-color: rgba(251,191,36,0.25); }
.lancamento-row.fixa:hover { background: rgba(251,191,36,0.06); border-color: rgba(251,191,36,0.45); }
.lancamento-row.urgente { border-color: rgba(239,68,68,0.5); background: rgba(239,68,68,0.06); }
.lancamento-row.urgente:hover { background: rgba(239,68,68,0.1); }
.lancamento-row.pago { opacity: 0.45; }

/* INPUTS */
label { color:#a0aec0 !important; font-size:13px !important; font-weight:600 !important; letter-spacing:0.5px !important; }
input, textarea,
.stTextInput input, .stNumberInput input, .stDateInput input,
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input {
    border-radius: 10px !important;
    color: #1a1a2e !important;
    font-family: 'Sora', sans-serif !important; font-size: 15px !important;
    caret-color: #6a3de8 !important;
}
input::placeholder, textarea::placeholder { color: rgba(80,80,120,0.5) !important; }
.stCheckbox label { color:#c9d1f0 !important; font-size:14px !important; font-weight:600 !important; }

/* BOTÕES */
.stButton > button {
    background: linear-gradient(135deg, #6a3de8, #9b8dff) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important; font-weight: 600 !important;
    font-size: 14px !important;
    padding: 12px 28px !important; width: 100% !important;
    letter-spacing: 0.5px !important; box-shadow: 0 4px 20px rgba(106,61,232,0.4) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(106,61,232,0.6) !important; }

.logout-btn > button {
    background: rgba(255,255,255,0.06) !important; border: 1px solid rgba(255,255,255,0.12) !important;
    font-size: 12px !important; padding: 6px 14px !important;
    box-shadow: none !important; width: auto !important; color: #9ca3af !important;
}
.logout-btn > button:hover { background: rgba(255,80,80,0.12) !important; color: #fca5a5 !important; border-color: rgba(255,80,80,0.3) !important; }

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
#  CONEXÃO POSTGRESQL (Supabase)
# ─────────────────────────────────────────────
@st.cache_resource
def get_conn():
    cfg = st.secrets["postgres"]
    conn = psycopg2.connect(
        host=cfg["host"], dbname=cfg["dbname"], user=cfg["user"],
        password=cfg["password"], port=cfg.get("port", 5432),
        sslmode="require", connect_timeout=10,
    )
    conn.autocommit = False
    return conn

def run_query(sql: str, params=None, fetch=False):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch:
                rows = cur.fetchall(); conn.commit(); return rows
            conn.commit()
    except psycopg2.OperationalError:
        get_conn.clear(); conn = get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch:
                rows = cur.fetchall(); conn.commit(); return rows
            conn.commit()
    except Exception:
        try: conn.rollback()
        except: pass
        raise

# ─────────────────────────────────────────────
#  INIT DB
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

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def hash_senha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def email_valido(e: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e))

def to_date(val):
    if val is None: return None
    if isinstance(val, date): return val
    if hasattr(val, "date"): return val.date()
    return date.fromisoformat(str(val))

# ── Usuários ──────────────────────────────────
def criar_usuario(nome, email, senha):
    try:
        run_query(
            "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)",
            (nome.strip(), email.strip().lower(), hash_senha(senha))
        )
        return True, "ok"
    except psycopg2.errors.UniqueViolation:
        try: get_conn().rollback()
        except: pass
        return False, "Este e-mail já está cadastrado."
    except Exception as e:
        try: get_conn().rollback()
        except: pass
        return False, f"Erro ao criar conta: {e}"

def autenticar_usuario(email, sender_senha):
    try:
        rows = run_query(
            "SELECT id, nome FROM usuarios WHERE email=%s AND senha=%s",
            (email.strip().lower(), hash_senha(sender_senha)), fetch=True
        )
        return (rows[0]["id"], rows[0]["nome"]) if rows else None
    except Exception:
        return None

# ── Lançamentos ───────────────────────────────
def inserir_lancamento(uid, descricao, valor_total, parcelas_totais, inicio, final, recorrente):
    try:
        run_query("""
            INSERT INTO lancamentos
                (usuario_id, descricao, valor_total, parcelas_totais, parcelas_pagas,
                 inicio_pagamento, final_pagamento, recorrente, pago)
            VALUES (%s,%s,%s,%s,0,%s,%s,%s,FALSE)
        """, (uid, descricao, float(valor_total), parcelas_totais,
              inicio, final if final else None, 1 if recorrente else 0))
    except Exception as e:
        st.error(f"❌ Erro ao salvar lançamento: {e}")

def carregar_lancamentos(uid) -> pd.DataFrame:
    try:
        rows = run_query(
            "SELECT * FROM lancamentos WHERE usuario_id=%s", (uid,), fetch=True
        )
        if not rows:
            return pd.DataFrame(columns=[
                "id","usuario_id","descricao","valor_total","parcelas_totais","parcelas_pagas",
                "inicio_pagamento","final_pagamento","recorrente","pago"
            ])
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        st.error(f"❌ Erro ao carregar lançamentos: {e}")
        return pd.DataFrame()

def excluir_lancamento(id_):
    try:
        run_query("DELETE FROM lancamentos WHERE id=%s", (id_,))
    except Exception as e:
        st.error(f"❌ Erro ao excluir: {e}")

def marcar_pago(id_):
    try:
        run_query("UPDATE lancamentos SET pago=TRUE WHERE id=%s", (id_,))
    except Exception as e:
        st.error(f"❌ Erro ao marcar como pago: {e}")

def avancar_parcela_recorrente(id_, inicio_pagamento):
    try:
        inicio = to_date(inicio_pagamento)
        dia = inicio.day
        mes = inicio.month % 12 + 1
        ano = inicio.year + (1 if inicio.month == 12 else 0)
        try:
            novo_inicio = date(ano, mes, dia)
        except ValueError:
            novo_inicio = date(ano, mes, calendar.monthrange(ano, mes)[1])
        run_query(
            "UPDATE lancamentos SET inicio_pagamento=%s, pago=FALSE WHERE id=%s",
            (novo_inicio, id_)
        )
    except Exception as e:
        st.error(f"❌ Erro ao avançar parcela recorrente: {e}")

def avancar_parcela_parcelada_excel(id_, inicio_pagamento, parcelas_totais, parcelas_pagas_atual):
    try:
        proxima_paga = parcelas_pagas_atual + 1
        
        if proxima_paga >= parcelas_totais:
            run_query("UPDATE lancamentos SET parcelas_pagas=%s, pago=TRUE WHERE id=%s", (parcelas_totais, id_))
        else:
            inicio = to_date(inicio_pagamento)
            dia = inicio.day
            mes = inicio.month % 12 + 1
            ano = inicio.year + (1 if inicio.month == 12 else 0)
            try:
                novo_inicio = date(ano, mes, dia)
            except ValueError:
                novo_inicio = date(ano, mes, calendar.monthrange(ano, mes)[1])
                
            run_query(
                "UPDATE lancamentos SET inicio_pagamento=%s, parcelas_pagas=%s WHERE id=%s",
                (novo_inicio, proxima_paga, id_)
            )
    except Exception as e:
        st.error(f"❌ Erro ao avançar parcela: {e}")

def inserir_feedback(uid, mensagem):
    try:
        run_query(
            "INSERT INTO feedbacks (usuario_id, mensagem) VALUES (%s,%s)",
            (uid, mensagem.strip())
        )
        return True
    except Exception as e:
        st.error(f"❌ Erro ao enviar feedback: {e}")
        return False

# ─────────────────────────────────────────────
#  LÓGICA DE CÁLCULO
# ─────────────────────────────────────────────
def calcular_proxima_recorrente(inicio_pagamento) -> date:
    hoje  = date.today()
    inicio = to_date(inicio_pagamento)
    dia   = inicio.day
    def montar(ano, mes):
        try:    return date(ano, mes, dia)
        except: return date(ano, mes, (date(ano, mes % 12 + 1, 1) - timedelta(days=1)).day)
    c = montar(hoje.year, hoje.month)
    if c < hoje:
        mes = hoje.month % 12 + 1
        ano = hoje.year + (1 if hoje.month == 12 else 0)
        c   = montar(ano, mes)
    return c

def calcular_valor_parcela(valor_total, parcelas_totais: int) -> float:
    return float(valor_total) / parcelas_totais if parcelas_totais > 0 else 0.0

def calcular_gasto_mensal(df: pd.DataFrame) -> float:
    total = 0.0
    for _, row in df.iterrows():
        if row.get("pago", False): continue
        if int(row.get("recorrente", 0)) == 1:
            total += float(row["valor_total"])
        else:
            total += calcular_valor_parcela(row["valor_total"], row["parcelas_totais"])
    return total

def get_sort_key(row) -> tuple:
    hoje = date.today()
    if row.get("pago", False):
        return (2, date(9999, 12, 31))
    
    eh_fixa = int(row.get("recorrente", 0)) == 1
    if eh_fixa:
        proxima = calcular_proxima_recorrente(to_date(row["inicio_pagamento"]))
    else:
        proxima = to_date(row["inicio_pagamento"])
        
    if proxima <= hoje:
        return (0, proxima)
    return (1, proxima)

# ─────────────────────────────────────────────
#  INIT EXECUTION
# ─────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"❌ Erro ao conectar ao banco: {e}")
    st.stop()

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "usuario_id"   not in st.session_state: st.session_state.usuario_id   = None
if "usuario_nome" not in st.session_state: st.session_state.usuario_nome = None

if st.session_state.usuario_id is None:
    uid_param = st.query_params.get("s", None)
    if uid_param:
        try:
            rows = run_query("SELECT id, nome FROM usuarios WHERE id=%s", (int(uid_param),), fetch=True)
            if rows:
                st.session_state.usuario_id   = rows[0]["id"]
                st.session_state.usuario_nome = rows[0]["nome"]
        except Exception:
            pass

# ═════════════════════════════════════════════
#  TELA DE LOGIN / CADASTRO
# ═════════════════════════════════════════════
if st.session_state.usuario_id is None:
    _, col_center, _ = st.columns([1, 1.6, 1])
    with col_center:
        st.markdown("""
        <div class="login-wrap">
            <div class="login-logo">💳</div>
            <div class="login-title">Gastei - Finanças Premium</div>
            <div class="login-sub">Controle de Gastos de Alta Performance</div>
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
                        st.query_params["s"] = str(resultado[0])
                        st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos.")

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            numero_suporte = "5567991158892"
            msg_wa = "Olá! Esqueci minha senha do app Gastei. Pode me ajudar?"
            link_wa = f"https://wa.me/{numero_suporte}?text={msg_wa.replace(' ', '%20')}"
            st.markdown(f"""
            <div style='text-align:center; margin-top:4px;'>
                <a href="{link_wa}" target="_blank" style="color:#9b8dff; font-size:13px; text-decoration:none; opacity:0.8;">
                    🔒 Esqueci minha senha — Falar com o Suporte
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🛡️ Termos de Uso e Política de Privacidade"):
                st.write("Seus dados financeiros são armazenados de forma criptografada e privativa na nossa infraestrutura do Supabase. Não compartilhamos e nem realizamos leitura de suas informações para qualquer outra finalidade que não seja o seu controle estrito.")

        with aba_cadastro:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            nome_cad   = st.text_input("Seu nome",        key="cad_nome",   placeholder="João Silva")
            email_cad  = st.text_input("E-mail",          key="cad_email",  placeholder="seu@email.com")
            senha_cad  = st.text_input("Senha", type="password", key="cad_senha",  placeholder="Mínimo 6 caracteres")
            senha_cad2 = st.text_input("Confirmar senha", type="password", key="cad_senha2", placeholder="Repita a senha")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            if st.button("Criar minha conta →", key="btn_cadastro"):
                erros = []
                if not all([nome_cad, email_cad, senha_cad, senha_cad2]):
                    erros.append("Preencha todos os campos.")
                elif not email_valido(email_cad):
                    erros.append("E-mail inválido.")
                elif len(senha_cad) < 6:
                    erros.append("A senha deve ter pelo menos 6 caracteres.")
                elif senha_cad != senha_cad2:
                    erros.append("As senhas não conferem.")
                if erros:
                    for e in erros: st.error(e)
                else:
                    ok, msg = criar_usuario(nome_cad, email_cad, senha_cad)
                    if ok: st.success("✅ Conta criada! Faça login na aba ao lado.")
                    else:  st.error(msg)
    st.stop()

# ═════════════════════════════════════════════
#  APP PRINCIPAL
# ═════════════════════════════════════════════
uid = st.session_state.usuario_id
st.query_params["s"] = str(uid)

col_titulo, col_usuario, col_logout = st.columns([5, 2, 1])
with col_titulo:
    st.markdown("# GASTEI ⚡")
    st.markdown("<p style='color:#6b7280; margin-top:-12px; margin-bottom:28px;'>Finanças Pessoais Premium Inteligentes</p>", unsafe_allow_html=True)
with col_usuario:
    st.markdown(f"<div style='text-align:right; padding-top:18px; font-size:13px; color:#9ca3af;'>Olá, <strong style='color:#c4b5fd'>{st.session_state.usuario_nome}</strong> 👋</div>", unsafe_allow_html=True)
with col_logout:
    st.markdown("<div style='padding-top:14px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("Sair 🚪", key="btn_logout"):
        st.session_state.usuario_id   = None
        st.session_state.usuario_nome = None
        st.query_params.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

aba_principal, aba_feedback = st.tabs(["📊 Meus Gastos", "💬 Feedbacks & Sugestões"])

# ══════════════════════════════
# ABA 1 — GASTOS
# ══════════════════════════════
with aba_principal:
    df_all = carregar_lancamentos(uid)
    total_saidas = df_all["valor_total"].astype(float).sum() if not df_all.empty else 0.0
    gasto_mensal = calcular_gasto_mensal(df_all) if not df_all.empty else 0.0
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div class="total-card">
            <div>
                <div class="total-label">Total de Saídas Contratadas</div>
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
            <div style="font-size:48px;opacity:0.4;">📅</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("### ➕ Novo Lançamento")
    with st.container():
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        with col1:
            descricao = st.text_input("O que comprou / Pagou", placeholder="Ex: iPhone 16, Aluguel, Internet...")
        with col2:
            valor_total = st.number_input("Valor Total (R$)", min_value=0.01, step=0.01, format="%.2f")
            
        is_recorrente = st.checkbox("🔁 Conta Fixa / Recorrente (sem data de término — Aluguel, Internet...)")
        
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
                with pc2: st.markdown("**Tipo:** `🔁 Recorrente`")
                with pc3: st.markdown(f"**Próximo vencimento:** `{proxima_rec.strftime('%d/%m/%Y')}`")
        else:
            col3, col4 = st.columns(2)
            with col3:
                parcelas_totais = st.number_input("Número de Parcelas", min_value=1, max_value=360, step=1, value=1)
            with col4:
                inicio_pagamento = st.date_input("Data do Primeiro Vencimento", value=date.today(), format="DD/MM/YYYY")
            
            final_pagamento = None
            if descricao and valor_total > 0:
                val_p = calcular_valor_parcela(valor_total, parcelas_totais)
                st.markdown("<hr>", unsafe_allow_html=True)
                pc1, pc2, pc3 = st.columns(3)
                with pc1: st.markdown(f"**Valor por parcela:** `R$ {val_p:.2f}`")
                with pc2: st.markdown(f"**Parcelas restantes:** `{parcelas_totais}x`")
                with pc3: st.markdown(f"**Vencimento da Parcela 1:** `{inicio_pagamento.strftime('%d/%m/%Y')}`")
                
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("💾 Salvar Lançamento"):
                erros = []
                if not descricao.strip(): erros.append("⚠️ Preencha a descrição do gasto.")
                if valor_total <= 0: erros.append("⚠️ O valor deve ser maior que zero.")
                if erros:
                    for e in erros: st.error(e)
                else:
                    inserir_lancamento(uid, descricao.strip(), valor_total, parcelas_totais, inicio_pagamento, final_pagamento, is_recorrente)
                    st.success(f"✅ **{descricao}** salvo com sucesso!")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### 📋 Histórico de Vencimentos")
    df = carregar_lancamentos(uid)
    if df.empty:
        st.markdown("<div style='text-align:center; padding:60px 20px; color:#4b5563;'><div style='font-size:48px;'>📭</div>Nenhum lançamento ainda.</div>", unsafe_allow_html=True)
    else:
        busca = st.text_input("🔍 Filtrar por descrição", placeholder="Digite para buscar...", key="busca")
        if busca.strip():
            df = df[df["descricao"].str.contains(busca.strip(), case=False, na=False)]
            
        hoje = date.today()
        df["_sort_key"] = df.apply(get_sort_key, axis=1)
        df = df.sort_values(by="_sort_key").drop(columns=["_sort_key"])
        
        # Cabeçalhos
        st.markdown("""
        <div style="display:grid; grid-template-columns: 2.2fr 1fr 1fr 1fr 0.8fr; padding:10px 24px; font-size:11px; font-weight:700; color:#6b7280; text-transform:uppercase; letter-spacing:1px;">
            <div>Descrição</div>
            <div>Valor</div>
            <div>Próximo Vencimento</div>
            <div>Situação</div>
            <div style="text-align:center">Ações</div>
        </div>
        """, unsafe_allow_html=True)
        
        for _, row in df.iterrows():
            id_ = row["id"]
            desc = row["descricao"]
            v_tot = float(row["valor_total"])
            parc_tot = int(row["parcelas_totais"])
            parc_pagas = int(row.get("parcelas_pagas", 0))
            parc_restantes = max(0, parc_tot - parc_pagas)
            eh_fixa = int(row["recorrente"]) == 1
            pago_fim = bool(row["pago"])
            
            if eh_fixa:
                val_exibir = v_tot
                venc_data = calcular_proxima_recorrente(to_date(row["inicio_pagamento"]))
            else:
                val_exibir = calcular_valor_parcela(v_tot, parc_tot)
                venc_data = to_date(row["inicio_pagamento"])
                
            classe_row = "lancamento-row"
            if pago_fim:
                classe_row += " pago"
            elif eh_fixa:
                classe_row += " fixa"
                if venc_data <= hoje: classe_row += " urgente"
            else:
                if venc_data <= hoje: classe_row += " urgente"
                
            col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns([2.2, 1, 1, 1, 0.8])
            
            with col_r1:
                sub_desc = f"Total: R$ {v_tot:,.2f} · Início: {to_date(row['inicio_pagamento']).strftime('%d/%m/%Y')}" if not eh_fixa else "Conta Mensal Fixa"
                st.markdown(f"<div style='padding-top:12px'><strong style='color:#fff; font-size:15px;'>{desc}</strong><br><span style='color:#6b7280; font-size:11px;'>{sub_desc}</span></div>", unsafe_allow_html=True)
                
            with col_r2:
                label_p = "mensal" if eh_fixa else "por parcela"
                st.markdown(f"<div style='padding-top:12px'><strong style='font-family:JetBrains Mono; color:#9b8dff; font-size:16px;'>R$ {val_exibir:,.2f}</strong><br><span style='color:#6b7280; font-size:11px;'>{label_p}</span></div>", unsafe_allow_html=True)
                
            with col_r3:
                if pago_fim:
                    st.markdown("<div style='padding-top:18px'><span class='badge-pago'>Concluído ✅</span></div>", unsafe_allow_html=True)
                elif venc_data == hoje:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-hoje'>🔥 HOJE ({venc_data.strftime('%d/%m/%Y')})</span></div>", unsafe_allow_html=True)
                elif venc_data < hoje:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-urgente'>⚠️ ATRASADO ({venc_data.strftime('%d/%m/%Y')})</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-vence'>📅 {venc_data.strftime('%d/%m/%Y')}</span></div>", unsafe_allow_html=True)
                    
            with col_r4:
                if pago_fim:
                    st.markdown("<div style='padding-top:18px; color:#4b5563; font-size:13px;'>Dívida Encerrada</div>", unsafe_allow_html=True)
                elif eh_fixa:
                    st.markdown("<div style='padding-top:18px'><span class='badge-fixa'>Recorrente ∞</span></div>", unsafe_allow_html=True)
                else:
                    # ── CÁLCULO DA DATA DA ÚLTIMA PARCELA (ESTILO EXCEL) ──
                    try:
                        meses_para_fim = max(0, parc_restantes - 1)
                        dia_u = venc_data.day
                        mes_u = (venc_data.month + meses_para_fim - 1) % 12 + 1
                        ano_u = venc_data.year + ((venc_data.month + meses_para_fim - 1) // 12)
                        try:
                            data_ultima_parc = date(ano_u, mes_u, dia_u)
                        except ValueError:
                            data_ultima_parc = date(ano_u, mes_u, calendar.monthrange(ano_u, mes_u)[1])
                        txt_ultima = data_ultima_parc.strftime('%d/%m/%Y')
                    except:
                        txt_ultima = "--/--/----"

                    falta_pagar = max(0.0, v_tot - (parc_pagas * val_exibir))
                    st.markdown(f"""
                    <div style='padding-top:4px'>
                        <span class='badge-parcelas'>{parc_restantes}x restantes</span><br>
                        <span style='color:#6b7280; font-size:11px; display:block; margin-top:2px;'>Última parcela: <strong style='color:#90cdf4;'>{txt_ultima}</strong></span>
                        <span style='color:#6b7280; font-size:10px; display:block;'>Falta pagar: R$ {falta_pagar:,.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
            with col_r5:
                st.markdown("<div style='padding-top:6px; display:flex; flex-direction:column; gap:4px;'>", unsafe_allow_html=True)
                if not pago_fim:
                    c_pagar = f"btn_p_{id_}"
                    c_quitar = f"btn_q_{id_}"
                    
                    st.markdown('<div class="btn-pagar">', unsafe_allow_html=True)
                    if st.button("💸 Pagar Parcela", key=c_pagar):
                        if eh_fixa:
                            avancar_parcela_recorrente(id_, row["inicio_pagamento"])
                        else:
                            avancar_parcela_parcelada_excel(id_, row["inicio_pagamento"], parc_tot, parc_pagas)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown('<div class="btn-quitar">', unsafe_allow_html=True)
                    if st.button("🏁 Quitar Tudo", key=c_quitar):
                        marcar_pago(id_)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    if st.button("🗑️ Excluir", key=f"btn_del_{id_}"):
                        excluir_lancamento(id_)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                
        st.markdown("<br><br><center style='color:#4b5563; font-size:12px;'>© 2026 Gastei App. Todos os direitos reservados. Suporte: suporte@seudominio.com</center>", unsafe_allow_html=True)

# ══════════════════════════════
# ABA 2 — FEEDBACK
# ══════════════════════════════
with aba_feedback:
    st.markdown("### 💬 Canal Direto de Sugestões & Feedbacks")
    st.markdown("<p style='color:#9ca3af; margin-top:-10px;'>Sua opinião molda as próximas atualizações da nossa plataforma!</p>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        mensagem_fb = st.text_area(
            "Sua mensagem",
            placeholder="Ex: Seria massa ver um gráfico de pizza no topo... Ou: Encontrei um bug visual no botão X...",
            height=160,
            key="feedback_texto"
        )
        
        col_fb, _ = st.columns([1, 3])
        with col_fb:
            if st.button("📨 Enviar Meu Feedback", key="btn_feedback"):
                if not mensagem_fb.strip():
                    st.error("⚠️ Escreva algo antes de clicar em enviar.")
                elif len(mensagem_fb.strip()) < 8:
                    st.error("⚠️ Detalhe um pouquinho mais a sua mensagem.")
                else:
                    # Correção de variável efetuada de forma segura
                    if inserir_feedback(uid, mensagem_fb):
                        st.success("✅ Feedback enviado com absoluto sucesso! Muito obrigado 🙏")
                        st.balloons()
        st.markdown('</div>', unsafe_allow_html=True)
