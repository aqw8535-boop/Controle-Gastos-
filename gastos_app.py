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
