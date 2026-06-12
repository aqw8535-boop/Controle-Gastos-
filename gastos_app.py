import streamlit as st
import psycopg2
import psycopg2.extras
import psycopg2.pool
import pandas as pd
from datetime import date, timedelta, datetime
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
#  DICIONÁRIO I18N — TRILÍNGUE
# ─────────────────────────────────────────────
IDIOMAS = {
    "PT": {
        # Geral
        "app_subtitle":         "Finanças Pessoais Premium Inteligentes",
        "ola":                  "Olá",
        "sair":                 "Sair 🚪",
        # Abas principais
        "aba_gastos":           "📊 Meus Gastos",
        "aba_feedback":         "💬 Feedbacks & Sugestões",
        # Cards de total
        "total_saidas":         "Total de Saídas Contratadas",
        "comprometido_mes":     "Comprometido Este Mês",
        "salario_comprometido": "Salário Comprometido (Próx. Mês)",
        # Formulário de lançamento
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
        # Histórico
        "historico":            "### 📋 Histórico de Vencimentos",
        "filtrar":              "🔍 Filtrar por descrição",
        "placeholder_busca":    "Digite para buscar...",
        "nenhum_lancamento":    "Nenhum lançamento ainda.",
        # Alertas de vencimento
        "conta_atrasada_s":     "conta atrasada",
        "conta_atrasada_p":     "contas atrasadas",
        "alerta_atrasada":      "🚨 {} {} — quite agora para não acumular juros!",
        "conta_hoje_s":         "conta vence hoje",
        "conta_hoje_p":         "contas vencem hoje",
        "alerta_hoje":          "🔥 {} {} — não deixe passar!",
        "conta_breve_s":        "conta vence",
        "conta_breve_p":        "contas vencem",
        "alerta_breve":         "⚡ {} {} nos próximos 3 dias",
        # Cabeçalho da tabela
        "col_descricao":        "Descrição",
        "col_valor":            "Valor",
        "col_vencimento":       "Próximo Vencimento",
        "col_situacao":         "Situação",
        "col_acoes":            "Ações",
        # Badges e labels de linha
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
        # Botões de ação
        "btn_pagar":            "💸 Pagar Parcela",
        "btn_quitar":           "🏁 Quitar Tudo",
        "btn_excluir":          "🗑️ Excluir",
        # Salário
        "salario_titulo":       "💰 Meu Salário Mensal",
        "salario_input":        "Salário Mensal Líquido (R$)",
        "salario_salvo":        "✅ Salário atualizado!",
        "salario_zero_aviso":   "⚠️ Cadastre seu salário na barra lateral para ver o % comprometido.",
        "pct_label":            "% do salário comprometido no próximo mês",
        # Simulação
        "simulacao_titulo":     "### 🧮 Simulador de Gasto",
        "simulacao_desc":       "Simule quanto ficaria comprometido ao adicionar um novo gasto.",
        "sim_valor":            "Valor do gasto simulado (R$)",
        "sim_parcelas":         "Em quantas parcelas?",
        "sim_resultado":        "Com este gasto, você comprometeria **R$ {:.2f}/mês** ({:.1f}% do salário).",
        "sim_ok":               "✅ Dentro do limite saudável (abaixo de 70% do salário).",
        "sim_alerta":           (
            "TEM CERTEZA QUE QUER FAZER ESTA CONTA? {:.1f}% DO SEU SALÁRIO ESTARÁ COMPROMETIDO; "
            "É MELHOR NÃO FAZER ESTA CONTA, POIS ESTÁ ALÉM DO QUE VOCÊ CONSEGUE PAGAR PARA O PRÓXIMO MÊS"
        ),
        # Feedback
        "feedback_titulo":      "### 💬 Canal Direct de Sugestões & Feedbacks",
        "feedback_sub":         "Sua opinião molda as próximas atualizações da nossa plataforma!",
        "feedback_label":       "Sua mensagem",
        "feedback_placeholder": "Ex: Seria massa ver um gráfico de pizza no topo... Ou: Encontrei um bug visual no botão X...",
        "feedback_btn":         "📨 Enviar Meu Feedback",
        "feedback_vazio":       "⚠️ Escreva algo antes de clicar em enviar.",
        "feedback_curto":       "⚠️ Detalhe um pouquinho mais a sua mensagem.",
        "feedback_ok":          "✅ Feedback enviado com absoluto sucesso! Muito obrigado 🙏",
        # Rodapé
        "rodape":               "© 2026 Gastei App. Todos os direitos reservados. Suporte: finatechsuporte@gmail.com",
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
        "alerta_atrasada":      "🚨 {} {} — pay now to avoid late fees!",
        "conta_hoje_s":         "bill due today",
        "conta_hoje_p":         "bills due today",
        "alerta_hoje":          "🔥 {} {} — don't let it pass!",
        "conta_breve_s":        "bill due",
        "conta_breve_p":        "bills due",
        "alerta_breve":         "⚡ {} {} in the next 3 days",
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
        "salario_salvo":        "✅ Salary updated!",
        "salario_zero_aviso":   "⚠️ Set your salary in the sidebar to see the committed % of income.",
        "pct_label":            "% of salary committed next month",
        "simulacao_titulo":     "### 🧮 Expense Simulator",
        "simulacao_desc":       "Simulate how much you'd commit by adding a new expense.",
        "sim_valor":            "Simulated expense amount (R$)",
        "sim_parcelas":         "In how many installments?",
        "sim_resultado":        "With this expense, you'd commit **R$ {:.2f}/month** ({:.1f}% of salary).",
        "sim_ok":               "✅ Within healthy limit (below 70% of salary).",
        "sim_alerta":           (
            "ARE YOU SURE YOU WANT TO MAKE THIS EXPENSE? {:.1f}% OF YOUR SALARY WILL BE COMMITTED; "
            "IT IS BETTER NOT TO MAKE THIS EXPENSE, AS IT IS BEYOND WHAT YOU CAN AFFORD FOR NEXT MONTH"
        ),
        "feedback_titulo":      "### 💬 Suggestions & Feedback Channel",
        "feedback_sub":         "Your opinion shapes the next updates to our platform!",
        "feedback_label":       "Your message",
        "feedback_placeholder": "e.g.: It'd be great to see a pie chart at the top... Or: I found a visual bug in button X...",
        "feedback_btn":         "📨 Send My Feedback",
        "feedback_vazio":       "⚠️ Please write something before clicking send.",
        "feedback_curto":       "⚠️ Please elaborate a little more on your message.",
        "feedback_ok":          "✅ Feedback sent successfully! Thank you so much 🙏",
        "rodape":               "© 2026 Gastei App. All rights reserved. Support: finatechsuporte@gmail.com",
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
        "alerta_atrasada":      "🚨 {} {} — payez maintenant pour éviter les pénalités !",
        "conta_hoje_s":         "facture due aujourd'hui",
        "conta_hoje_p":         "factures dues aujourd'hui",
        "alerta_hoje":          "🔥 {} {} — ne laissez pas passer !",
        "conta_breve_s":        "facture due",
        "conta_breve_p":        "factures dues",
        "alerta_breve":         "⚡ {} {} dans les 3 prochains jours",
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
        "salario_salvo":        "✅ Salaire mis à jour !",
        "salario_zero_aviso":   "⚠️ Enregistrez votre salaire dans la barre latérale pour voir le % engagé.",
        "pct_label":            "% du salaire engagé le mois prochain",
        "simulacao_titulo":     "### 🧮 Simulateur de Dépense",
        "simulacao_desc":       "Simulez combien vous engageriez en ajoutant une nouvelle dépense.",
        "sim_valor":            "Montant de la dépense simulée (R$)",
        "sim_parcelas":         "En combien de versements ?",
        "sim_resultado":        "Avec cette dépense, vous engageriez **R$ {:.2f}/mois** ({:.1f}% du salaire).",
        "sim_ok":               "✅ Dans la limite saine (moins de 70% du salaire).",
        "sim_alerta":           (
            "ÊTES-VOUS SÛR DE VOULOIR FAIRE CETTE DÉPENSE ? {:.1f}% DE VOTRE SALAIRE SERA ENGAGÉ ; "
            "IL VAUT MIEUX NE PAS FAIRE CETTE DÉPENSE, CAR ELLE DÉPASSE CE QUE VOUS POUVEZ PAYER POUR LE MOIS PROCHAIN"
        ),
        "feedback_titulo":      "### 💬 Canal de Suggestions & Retours",
        "feedback_sub":         "Votre avis façonne les prochaines mises à jour de notre plateforme !",
        "feedback_label":       "Votre message",
        "feedback_placeholder": "Ex : Ce serait super d'avoir un graphique en secteurs... Ou : J'ai trouvé un bug visuel sur le bouton X...",
        "feedback_btn":         "📨 Envoyer Mon Retour",
        "feedback_vazio":       "⚠️ Veuillez écrire quelque chose avant d'envoyer.",
        "feedback_curto":       "⚠️ Veuillez développer un peu plus votre message.",
        "feedback_ok":          "✅ Retour envoyé avec succès ! Merci beaucoup 🙏",
        "rodape":               "© 2026 Gastei App. Tous droits réservés. Support : finatechsuporte@gmail.com",
    },
}

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

/* CARD SALÁRIO % */
.salario-card {
    background: linear-gradient(135deg, #1a2e1e 0%, #0d2118 100%);
    border: 1px solid rgba(52,211,153,0.25); border-radius: 20px;
    padding: 24px 32px; margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.salario-card.alerta {
    background: linear-gradient(135deg, #2e1a1a 0%, #210d0d 100%);
    border-color: rgba(239,68,68,0.35);
}
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
    border: 2px solid rgba(239,68,68,0.6);
    border-radius: 14px; padding: 18px 22px;
    font-size: 13px; font-weight: 700; color: #fca5a5;
    letter-spacing: 0.03em; line-height: 1.6;
    animation: pulse-alerta 1.8s ease-in-out infinite;
    margin-top: 12px;
}
.alerta-simulacao .pct-destaque {
    font-size: 22px; font-weight: 800; color: #ef4444;
    display: block; margin-bottom: 6px; font-family: 'JetBrains Mono', monospace;
}

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
.lancamento-row.urgente {
    border-color: rgba(239,68,68,0.7);
    background: rgba(239,68,68,0.08);
    box-shadow: 0 0 0 1px rgba(239,68,68,0.3), -4px 0 0 0 #ef4444;
}
.lancamento-row.urgente:hover { background: rgba(239,68,68,0.13); }
.lancamento-row.hoje {
    border-color: rgba(251,146,60,0.8);
    background: rgba(251,146,60,0.09);
    box-shadow: 0 0 0 1px rgba(251,146,60,0.35), -4px 0 0 0 #f97316;
    animation: pulse-hoje 2s ease-in-out infinite;
}
.lancamento-row.hoje:hover { background: rgba(251,146,60,0.15); }
@keyframes pulse-hoje {
    0%,100% { box-shadow: 0 0 0 1px rgba(251,146,60,0.35), -4px 0 0 0 #f97316; }
    50%      { box-shadow: 0 0 14px rgba(251,146,60,0.35), -4px 0 0 0 #f97316; }
}
.lancamento-row.em-breve {
    border-color: rgba(234,179,8,0.55);
    background: rgba(234,179,8,0.06);
    box-shadow: -4px 0 0 0 #ca8a04;
}
.lancamento-row.em-breve:hover { background: rgba(234,179,8,0.1); }
.lancamento-row.pago { opacity: 0.38; }
.alerta-banner {
    display:flex; align-items:center; gap:8px;
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 10px; padding: 7px 14px;
    font-size:11px; font-weight:700; color:#fca5a5;
    letter-spacing:0.04em; margin-bottom: 20px;
}
.alerta-banner .count {
    background: #ef4444; color:#fff;
    border-radius: 999px; padding: 1px 8px;
    font-size:11px; font-weight:800;
}
.hoje-banner {
    display:flex; align-items:center; gap:8px;
    background: rgba(251,146,60,0.12);
    border: 1px solid rgba(251,146,60,0.35);
    border-radius: 10px; padding: 7px 14px;
    font-size:11px; font-weight:700; color:#fdba74;
    letter-spacing:0.04em; margin-bottom: 8px;
}
.badge-em-breve { background:rgba(234,179,8,0.15); border:1px solid rgba(234,179,8,0.4); color:#fde047; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; display:inline-block; }

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

.btn-link > button {
    background: transparent !important; border: none !important;
    color: #9b8dff !important; font-size: 13px !important;
    padding: 4px 0 !important; box-shadow: none !important;
    width: auto !important; text-decoration: underline !important;
    text-underline-offset: 3px !important; opacity: 0.85 !important;
}
.btn-link > button:hover { opacity: 1 !important; transform: none !important; box-shadow: none !important; }

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

# ─────────────────────────────────────────────
#  PAYWALL
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

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def hash_senha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def _token_secret() -> str:
    return st.secrets.get("token_secret", "dev-fallback-inseguro-troque-nos-secrets")

def gerar_token_sessao(usuario_id: int) -> str:
    payload = str(usuario_id)
    sig = hmac.new(
        _token_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{payload}.{sig}"

def validar_token_sessao(token: str):
    try:
        payload, sig_recebida = token.rsplit(".", 1)
        sig_esperada = hmac.new(
            _token_secret().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        if hmac.compare_digest(sig_esperada, sig_recebida):
            return int(payload)
    except Exception:
        pass
    return None

def email_valido(e: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e))

def to_date(val):
    if val is None: return None
    if isinstance(val, date): return val
    if hasattr(val, "date"): return val.date()
    return date.fromisoformat(str(val))

def telefone_valido(tel: str) -> bool:
    digits = re.sub(r'\D', '', tel)
    return 10 <= len(digits) <= 13

# ── Reset de Senha ──────────────────────────────
def gerar_token_reset(email: str) -> str | None:
    try:
        run_query(
            "UPDATE reset_tokens SET usado=TRUE WHERE email=%s AND usado=FALSE",
            (email.strip().lower(),)
        )
        token = str(_secrets.randbelow(900000) + 100000)
        run_query(
            "INSERT INTO reset_tokens (email, token) VALUES (%s, %s)",
            (email.strip().lower(), token)
        )
        return token
    except Exception as e:
        st.error(f"❌ Erro ao gerar token: {e}")
        return None

def validar_token_reset(email: str, token: str) -> bool:
    try:
        rows = run_query(
            """SELECT id FROM reset_tokens
               WHERE email=%s AND token=%s AND usado=FALSE
                 AND criado_em > NOW() - INTERVAL '15 minutes'""",
            (email.strip().lower(), token.strip()),
            fetch=True
        )
        return bool(rows)
    except Exception:
        return False

def consumir_token_reset(email: str, token: str) -> bool:
    try:
        run_query(
            "UPDATE reset_tokens SET usado=TRUE WHERE email=%s AND token=%s",
            (email.strip().lower(), token.strip())
        )
        return True
    except Exception:
        return False

def trocar_senha(email: str, nova_senha: str) -> bool:
    try:
        run_query(
            "UPDATE usuarios SET senha=%s WHERE email=%s",
            (hash_senha(nova_senha), email.strip().lower())
        )
        return True
    except Exception as e:
        st.error(f"❌ Erro ao trocar senha: {e}")
        return False

def enviar_email_reset(destinatario: str, token: str) -> bool:
    try:
        cfg = st.secrets["email"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🔐 Gastei — Código de Redefinição de Senha"
        msg["From"]    = cfg["remetente"]
        msg["To"]      = destinatario
        html = f"""
        <div style="font-family:Sora,sans-serif; max-width:480px; margin:auto;
                    background:#1a1a2e; border-radius:16px; padding:40px; color:#e8e4ff;">
            <div style="text-align:center; font-size:48px; margin-bottom:8px;">💳</div>
            <h2 style="text-align:center; background:linear-gradient(90deg,#9b8dff,#64b5f6);
                       -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                       margin-bottom:24px;">Redefinição de Senha</h2>
            <p style="color:#9ca3af; text-align:center; margin-bottom:32px;">
                Use o código abaixo para redefinir sua senha.<br>
                Ele expira em <strong style="color:#e8e4ff;">15 minutos</strong>.
            </p>
            <div style="background:#6a3de8; border-radius:12px; padding:20px;
                        text-align:center; letter-spacing:12px;
                        font-size:36px; font-weight:700; color:#fff;
                        font-family:'JetBrains Mono',monospace; margin-bottom:28px;">
                {token}
            </div>
            <p style="color:#6b7280; font-size:12px; text-align:center;">
                Se você não solicitou isso, ignore este e-mail.<br>
                Suporte: suporte@finatec.com.br
            </p>
        </div>
        """
        msg.attach(MIMEText(html, "html"))
        porta = int(cfg.get("smtp_port", 587))
        if porta == 465:
            ctx = __import__('ssl').create_default_context()
            with smtplib.SMTP_SSL(cfg["smtp_host"], porta, context=ctx) as srv:
                srv.login(cfg["remetente"], cfg["senha_smtp"])
                srv.sendmail(cfg["remetente"], destinatario, msg.as_string())
        else:
            with smtplib.SMTP(cfg["smtp_host"], porta, timeout=10) as srv:
                srv.ehlo(); srv.starttls(); srv.ehlo()
                srv.login(cfg["remetente"], cfg["senha_smtp"])
                srv.sendmail(cfg["remetente"], destinatario, msg.as_string())
        return True
    except Exception as e:
        st.error(f"❌ Falha ao enviar e-mail: {e}")
        return False

# ── Usuários ──────────────────────────────────
def criar_usuario(nome, email, senha, telefone=""):
    permitido, motivo = verificar_status_licenca(email)
    if not permitido:
        if motivo == "não_autorizado":
            return False, "Acesso Negado! Este e-mail não possui uma licença ativa. Compre o acesso na nossa página oficial antes de se cadastrar."
        elif motivo == "assinatura_expirada":
            return False, "Sua assinatura expirou! Por favor, realize a renovação para reativar seu cadastro."
        return False, "Licença de acesso inválida."
    try:
        run_query(
            "INSERT INTO usuarios (nome, email, senha, telefone) VALUES (%s, %s, %s, %s)",
            (nome.strip(), email.strip().lower(), hash_senha(senha), telefone.strip())
        )
        return True, "ok"
    except psycopg2.errors.UniqueViolation:
        try: get_pool().getconn().rollback()
        except: pass
        return False, "Este e-mail já está cadastrado."
    except Exception as e:
        return False, f"Erro ao criar conta: {e}"

def autenticar_usuario(email, sender_senha):
    try:
        permitido, _ = verificar_status_licenca(email)
        if not permitido:
            return "bloqueado"
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
        invalidar_cache_lancamentos()
    except Exception as e:
        st.error(f"❌ Erro ao salvar lançamento: {e}")

@st.cache_data(ttl=30, show_spinner=False)
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

def invalidar_cache_lancamentos():
    carregar_lancamentos.clear()

def excluir_lancamento(id_):
    try:
        run_query("DELETE FROM lancamentos WHERE id=%s", (id_,))
        invalidar_cache_lancamentos()
    except Exception as e:
        st.error(f"❌ Erro ao excluir: {e}")

def marcar_pago(id_):
    try:
        run_query("UPDATE lancamentos SET pago=TRUE WHERE id=%s", (id_,))
        invalidar_cache_lancamentos()
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
        invalidar_cache_lancamentos()
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
        invalidar_cache_lancamentos()
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
    if df.empty:
        return 0.0
    df_a = df[~df["pago"].astype(bool)].copy()
    if df_a.empty:
        return 0.0
    df_a["valor_total"]     = df_a["valor_total"].astype(float)
    df_a["parcelas_totais"] = df_a["parcelas_totais"].astype(int)
    recorrentes  = df_a[df_a["recorrente"].astype(int) == 1]["valor_total"].sum()
    parcelados   = df_a[df_a["recorrente"].astype(int) == 0]
    parcela_vals = parcelados["valor_total"] / parcelados["parcelas_totais"].replace(0, 1)
    return float(recorrentes + parcela_vals.sum())

def calcular_gasto_proximo_mes(df: pd.DataFrame) -> float:
    """Soma do que será devido no próximo mês (recorrentes + parcelas ativas)."""
    return calcular_gasto_mensal(df)

# ─────────────────────────────────────────────
#  INIT EXECUTION
# ─────────────────────────────────────────────
@st.cache_resource
def init_db_once():
    init_db()

try:
    init_db_once()
except Exception as e:
    st.error(f"❌ Erro ao conectar ao banco: {e}")
    st.stop()

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "usuario_id"   not in st.session_state: st.session_state.usuario_id   = None
if "usuario_nome" not in st.session_state: st.session_state.usuario_nome = None
if "lang"         not in st.session_state: st.session_state.lang         = "PT"
if "salario"      not in st.session_state: st.session_state.salario      = 0.0

if st.session_state.usuario_id is None:
    token_param = st.query_params.get("s", None)
    if token_param:
        uid_validado = validar_token_sessao(token_param)
        if uid_validado:
            try:
                rows = run_query("SELECT id, nome FROM usuarios WHERE id=%s", (uid_validado,), fetch=True)
                if rows:
                    st.session_state.usuario_id   = rows[0]["id"]
                    st.session_state.usuario_nome = rows[0]["nome"]
                else:
                    st.query_params.clear()
            except Exception:
                pass
        else:
            st.query_params.clear()

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
            if "reset_step"  not in st.session_state: st.session_state.reset_step  = 0
            if "reset_email" not in st.session_state: st.session_state.reset_email = ""

            if st.session_state.reset_step == 0:
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                email_login = st.text_input("E-mail", key="login_email", placeholder="seu@email.com")
                senha_login = st.text_input("Senha", type="password", key="login_senha", placeholder="••••••••")
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                if st.button("Entrar →", key="btn_login"):
                    if not email_login or not senha_login:
                        st.error("Preencha e-mail e senha.")
                    else:
                        resultado = autenticar_usuario(email_login, senha_login)
                        if resultado == "bloqueado":
                            st.error("🛑 Acesso Bloqueado! Sua assinatura expirou ou seu e-mail não está autorizado. Entre em contato com o suporte para renovar.")
                        elif resultado:
                            st.session_state.usuario_id   = resultado[0]
                            st.session_state.usuario_nome = resultado[1]
                            st.query_params["s"] = gerar_token_sessao(resultado[0])
                            st.rerun()
                        else:
                            st.error("E-mail ou senha incorretos.")

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                st.markdown('<div class="btn-link">', unsafe_allow_html=True)
                if st.button("🔑 Esqueci minha senha", key="btn_forgot"):
                    st.session_state.reset_step = 1
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

                numero_suporte = "5567991158892"
                msg_wa = "Olá! Quero verificar o status do meu acesso no app Gastei."
                link_wa = f"https://wa.me/{numero_suporte}?text={msg_wa.replace(' ', '%20')}"
                st.markdown(f"""
                <div style='text-align:center; margin-top:2px;'>
                    <a href="{link_wa}" target="_blank"
                       style="color:#9b8dff; font-size:13px; text-decoration:none; opacity:0.8;">
                        🔒 Problemas com o acesso? — Falar com o Suporte
                    </a>
                </div>
                <div style='text-align:center; margin-top:10px;'>
                    <a href="https://finatechlab.com/pagina-vendas-gastei/" target="_blank"
                       style="color:#64b5f6; font-size:12px; text-decoration:none; opacity:0.65;">
                        🛒 Ainda não tem acesso? Conheça o Gastei →
                    </a>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("🛡️ Termos de Uso e Política de Privacidade"):
                    st.write("Seus dados financeiros são armazenados de forma criptografada e privativa na nossa infraestrutura do Supabase. Não compartilhamos e nem realizamos leitura de suas informações para qualquer outra finalidade que não seja o seu controle estrito.")

            elif st.session_state.reset_step == 1:
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.info("📧 Informe o e-mail cadastrado. Enviaremos um código de 6 dígitos.")
                email_reset = st.text_input("E-mail cadastrado", key="reset_email_input", placeholder="seu@email.com")
                col_enviar, col_voltar = st.columns([1, 1])
                with col_enviar:
                    if st.button("Enviar código →", key="btn_send_token"):
                        if not email_valido(email_reset):
                            st.error("E-mail inválido.")
                        else:
                            rows = run_query(
                                "SELECT id FROM usuarios WHERE email=%s",
                                (email_reset.strip().lower(),), fetch=True
                            )
                            if not rows:
                                st.error("E-mail não encontrado.")
                            else:
                                token = gerar_token_reset(email_reset)
                                if token and enviar_email_reset(email_reset, token):
                                    st.session_state.reset_email = email_reset.strip().lower()
                                    st.session_state.reset_step  = 2
                                    st.rerun()
                with col_voltar:
                    if st.button("← Voltar", key="btn_back_1"):
                        st.session_state.reset_step = 0
                        st.rerun()

            elif st.session_state.reset_step == 2:
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.success(f"✅ Código enviado para **{st.session_state.reset_email}**. Verifique sua caixa de entrada (e o spam).")
                codigo = st.text_input("Código de 6 dígitos", key="reset_token_input", placeholder="123456", max_chars=6)
                nova1  = st.text_input("Nova senha", type="password", key="reset_pass1", placeholder="Mínimo 6 caracteres")
                nova2  = st.text_input("Confirmar nova senha", type="password", key="reset_pass2", placeholder="Repita a senha")
                col_confirmar, col_voltar2 = st.columns([1, 1])
                with col_confirmar:
                    if st.button("Redefinir senha →", key="btn_confirm_reset"):
                        erros = []
                        if not codigo.strip():        erros.append("Informe o código recebido.")
                        if len(nova1) < 6:            erros.append("A senha deve ter pelo menos 6 caracteres.")
                        if nova1 != nova2:            erros.append("As senhas não conferem.")
                        if erros:
                            for e in erros: st.error(e)
                        elif not validar_token_reset(st.session_state.reset_email, codigo):
                            st.error("Código inválido ou expirado. Solicite um novo.")
                        else:
                            if trocar_senha(st.session_state.reset_email, nova1):
                                consumir_token_reset(st.session_state.reset_email, codigo)
                                st.success("🎉 Senha redefinida com sucesso! Faça login.")
                                st.session_state.reset_step  = 0
                                st.session_state.reset_email = ""
                                st.rerun()
                with col_voltar2:
                    if st.button("← Voltar", key="btn_back_2"):
                        st.session_state.reset_step = 1
                        st.rerun()

        with aba_cadastro:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            nome_cad   = st.text_input("Seu nome",            key="cad_nome",   placeholder="João Silva")
            email_cad  = st.text_input("E-mail",              key="cad_email",  placeholder="O mesmo e-mail usado na compra")
            tel_cad    = st.text_input("WhatsApp / Telefone", key="cad_tel",    placeholder="(67) 99999-9999")
            senha_cad  = st.text_input("Senha",  type="password", key="cad_senha",  placeholder="Mínimo 6 caracteres")
            senha_cad2 = st.text_input("Confirmar senha", type="password", key="cad_senha2", placeholder="Repita a senha")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            if st.button("Criar minha conta →", key="btn_cadastro"):
                erros = []
                if not all([nome_cad, email_cad, tel_cad, senha_cad, senha_cad2]):
                    erros.append("Preencha todos os campos, incluindo o telefone.")
                elif not email_valido(email_cad):
                    erros.append("E-mail inválido.")
                elif not telefone_valido(tel_cad):
                    erros.append("Telefone inválido. Use o formato (67) 99999-9999.")
                elif len(senha_cad) < 6:
                    erros.append("A senha deve ter pelo menos 6 caracteres.")
                elif senha_cad != senha_cad2:
                    erros.append("As senhas não conferem.")
                if erros:
                    for e in erros: st.error(e)
                else:
                    ok, msg = criar_usuario(nome_cad, email_cad, senha_cad, tel_cad)
                    if ok: st.success("✅ Conta autorizada e criada! Faça login na aba ao lado.")
                    else:  st.error(msg)

            st.markdown("""
            <div style='text-align:center; margin-top:16px;'>
                <a href="https://finatechlab.com/pagina-vendas-gastei/" target="_blank"
                   style="color:#64b5f6; font-size:12px; text-decoration:none; opacity:0.65;">
                    🛒 Ainda não comprou? Conheça os planos do Gastei →
                </a>
            </div>
            """, unsafe_allow_html=True)
    st.stop()

# ═════════════════════════════════════════════
#  APP PRINCIPAL
# ═════════════════════════════════════════════
uid = st.session_state.usuario_id
st.query_params["s"] = gerar_token_sessao(uid)

# ── Sidebar: idioma + salário ──────────────────
with st.sidebar:
    st.markdown("### ⚙️ Preferências")
    idioma_opcoes = {"Português": "PT", "English": "EN", "Français": "FR"}
    idioma_sel = st.selectbox(
        "🌐 Idioma / Language / Langue",
        options=list(idioma_opcoes.keys()),
        index=list(idioma_opcoes.values()).index(st.session_state.lang),
        key="sel_idioma"
    )
    st.session_state.lang = idioma_opcoes[idioma_sel]
    t = IDIOMAS[st.session_state.lang]   # atalho global

    st.markdown("---")
    st.markdown(f"### {t['salario_titulo']}")
    novo_salario = st.number_input(
        t["salario_input"],
        min_value=0.0, step=100.0, format="%.2f",
        value=float(st.session_state.salario),
        key="input_salario"
    )
    if st.button("💾 Salvar", key="btn_salvar_salario"):
        st.session_state.salario = novo_salario
        st.success(t["salario_salvo"])

# garante que t exista caso o sidebar não tenha sido renderizado ainda
t = IDIOMAS[st.session_state.lang]

# ── Header ────────────────────────────────────
col_titulo, col_usuario, col_logout = st.columns([5, 2, 1])
with col_titulo:
    st.markdown("# GASTEI ⚡")
    st.markdown(f"<p style='color:#6b7280; margin-top:-12px; margin-bottom:28px;'>{t['app_subtitle']}</p>", unsafe_allow_html=True)
with col_usuario:
    st.markdown(f"<div style='text-align:right; padding-top:18px; font-size:13px; color:#9ca3af;'>{t['ola']}, <strong style='color:#c4b5fd'>{st.session_state.usuario_nome}</strong> 👋</div>", unsafe_allow_html=True)
with col_logout:
    st.markdown("<div style='padding-top:14px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button(t["sair"], key="btn_logout"):
        st.session_state.usuario_id   = None
        st.session_state.usuario_nome = None
        st.query_params.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

aba_principal, aba_feedback = st.tabs([t["aba_gastos"], t["aba_feedback"]])

# ══════════════════════════════
# ABA 1 — GASTOS
# ══════════════════════════════
with aba_principal:
    df_all = carregar_lancamentos(uid)
    total_saidas = df_all["valor_total"].astype(float).sum() if not df_all.empty else 0.0
    gasto_mensal = calcular_gasto_mensal(df_all) if not df_all.empty else 0.0
    salario      = float(st.session_state.salario)

    # ── Cards de resumo (3 colunas) ────────────
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""
        <div class="total-card">
            <div>
                <div class="total-label">{t['total_saidas']}</div>
                <div class="total-value">R$ {total_saidas:,.2f}</div>
            </div>
            <div class="total-icon">📊</div>
        </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown(f"""
        <div class="parcela-card">
            <div>
                <div class="parcela-label">{t['comprometido_mes']}</div>
                <div class="parcela-value">R$ {gasto_mensal:,.2f}</div>
            </div>
            <div style="font-size:48px;opacity:0.4;">📅</div>
        </div>""", unsafe_allow_html=True)

    with col_c:
        if salario > 0:
            pct = (gasto_mensal / salario) * 100
            card_class = "salario-card alerta" if pct >= 70 else "salario-card"
            icon = "🚨" if pct >= 70 else "💰"
            st.markdown(f"""
            <div class="{card_class}">
                <div>
                    <div class="salario-label">{t['salario_comprometido']}</div>
                    <div class="salario-value">{pct:.1f}%</div>
                    <div style="font-size:11px; color:#6b7280; margin-top:4px;">{t['pct_label']}</div>
                </div>
                <div style="font-size:48px;opacity:0.5;">{icon}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="salario-card" style="opacity:0.55;">
                <div>
                    <div class="salario-label">{t['salario_comprometido']}</div>
                    <div class="salario-value">--%</div>
                </div>
                <div style="font-size:48px;opacity:0.3;">💰</div>
            </div>""", unsafe_allow_html=True)
            st.caption(t["salario_zero_aviso"])

    # ── Formulário de novo lançamento ──────────
    st.markdown(f"### {t['novo_lancamento']}")
    with st.container():
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        with col1:
            descricao = st.text_input(t["o_que_comprou"], placeholder=t["placeholder_desc"])
        with col2:
            valor_total = st.number_input(t["valor_total"], min_value=0.01, step=0.01, format="%.2f")

        is_recorrente = st.checkbox(t["conta_fixa"])

        if is_recorrente:
            col4, _ = st.columns([1, 2])
            with col4:
                inicio_pagamento = st.date_input(t["dia_vencimento"], value=date.today(), format="DD/MM/YYYY")
            parcelas_totais = 0
            final_pagamento = None
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

        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button(t["salvar_lancamento"]):
                erros = []
                if not descricao.strip(): erros.append(t["err_descricao"])
                if valor_total <= 0:      erros.append(t["err_valor"])
                if erros:
                    for e in erros: st.error(e)
                else:
                    inserir_lancamento(uid, descricao.strip(), valor_total, parcelas_totais, inicio_pagamento, final_pagamento, is_recorrente)
                    st.success(t["salvo_sucesso"].format(descricao))
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Simulador de Gasto ─────────────────────
    st.markdown(t["simulacao_titulo"])
    with st.container():
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown(f"<p style='color:#9ca3af; margin-top:-8px;'>{t['simulacao_desc']}</p>", unsafe_allow_html=True)
        sim_col1, sim_col2 = st.columns([2, 1])
        with sim_col1:
            sim_valor = st.number_input(t["sim_valor"], min_value=0.0, step=10.0, format="%.2f", key="sim_val")
        with sim_col2:
            sim_parcelas = st.number_input(t["sim_parcelas"], min_value=1, max_value=360, step=1, value=1, key="sim_parc")

        if sim_valor > 0:
            sim_mensal = sim_valor / sim_parcelas
            total_com_sim = gasto_mensal + sim_mensal
            if salario > 0:
                pct_sim = (total_com_sim / salario) * 100
                st.markdown(t["sim_resultado"].format(total_com_sim, pct_sim))
                if pct_sim > 70:
                    st.markdown(f"""
                    <div class="alerta-simulacao">
                        <span class="pct-destaque">⚠️ {pct_sim:.1f}%</span>
                        {t["sim_alerta"].format(pct_sim)}
                    </div>""", unsafe_allow_html=True)
                else:
                    st.success(t["sim_ok"])
            else:
                st.markdown(t["sim_resultado"].format(total_com_sim, 0.0))
                st.caption(t["salario_zero_aviso"])
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Histórico de lançamentos ───────────────
    st.markdown(t["historico"])
    df = carregar_lancamentos(uid)
    if df.empty:
        st.markdown(f"<div style='text-align:center; padding:60px 20px; color:#4b5563;'><div style='font-size:48px;'>📭</div>{t['nenhum_lancamento']}</div>", unsafe_allow_html=True)
    else:
        busca = st.text_input(t["filtrar"], placeholder=t["placeholder_busca"], key="busca")
        if busca.strip():
            df = df[df["descricao"].str.contains(busca.strip(), case=False, na=False)]

        hoje = date.today()
        df["_pago"] = df["pago"].astype(bool)
        df["_rec"]  = df["recorrente"].astype(int) == 1
        df["_venc"] = df.apply(
            lambda r: calcular_proxima_recorrente(to_date(r["inicio_pagamento"]))
                      if r["_rec"] else to_date(r["inicio_pagamento"]),
            axis=1
        )
        def _grp(row):
            if row["_pago"]:                              return (4, date(9999,12,31))
            v = row["_venc"]
            if v < hoje:                                  return (0, v)
            if v == hoje:                                 return (1, v)
            if v <= hoje + timedelta(days=3):             return (2, v)
            return (3, v)
        df["_sort"] = df.apply(_grp, axis=1)
        df = df.sort_values("_sort").drop(columns=["_pago", "_rec", "_venc", "_sort"])

        # ── banners de alerta ──────────────────
        df_alerta = carregar_lancamentos(uid)
        if not df_alerta.empty:
            _hoje = date.today()
            _venc_col = df_alerta.apply(
                lambda r: calcular_proxima_recorrente(to_date(r["inicio_pagamento"]))
                          if int(r["recorrente"]) == 1 else to_date(r["inicio_pagamento"]),
                axis=1
            )
            _ativos      = ~df_alerta["pago"].astype(bool)
            n_atrasadas  = int((_ativos & (_venc_col < _hoje)).sum())
            n_hoje       = int((_ativos & (_venc_col == _hoje)).sum())
            n_breve      = int((_ativos & (_venc_col > _hoje) & (_venc_col <= _hoje + timedelta(days=3))).sum())

            if n_atrasadas:
                pl = t["conta_atrasada_s"] if n_atrasadas == 1 else t["conta_atrasada_p"]
                st.markdown(f"""
                <div class="alerta-banner">
                    🚨 <span class="count">{n_atrasadas}</span> {t['alerta_atrasada'].format(n_atrasadas, pl).split('🚨 ')[1]}
                </div>""", unsafe_allow_html=True)
            if n_hoje:
                pl = t["conta_hoje_s"] if n_hoje == 1 else t["conta_hoje_p"]
                st.markdown(f"""
                <div class="hoje-banner">
                    🔥 <span style="background:#f97316;color:#fff;border-radius:999px;padding:1px 8px;font-weight:800;">{n_hoje}</span> {pl} — {t['alerta_hoje'].split('🔥 ')[1].split(' — ')[1]}
                </div>""", unsafe_allow_html=True)
            if n_breve and not n_atrasadas and not n_hoje:
                pl = t["conta_breve_s"] if n_breve == 1 else t["conta_breve_p"]
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;background:rgba(234,179,8,0.09);border:1px solid rgba(234,179,8,0.3);border-radius:10px;padding:7px 14px;font-size:11px;font-weight:700;color:#fde047;margin-bottom:8px;">
                    ⚡ {n_breve} {pl} {t['alerta_breve'].split('⚡ ')[1].split(str(n_breve)+' ')[1] if str(n_breve)+' ' in t['alerta_breve'] else 'nos próximos 3 dias'}
                </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="display:grid; grid-template-columns: 2.2fr 1fr 1fr 1fr 0.8fr; padding:10px 24px; font-size:11px; font-weight:700; color:#6b7280; text-transform:uppercase; letter-spacing:1px;">
            <div>{t['col_descricao']}</div>
            <div>{t['col_valor']}</div>
            <div>{t['col_vencimento']}</div>
            <div>{t['col_situacao']}</div>
            <div style="text-align:center">{t['col_acoes']}</div>
        </div>
        """, unsafe_allow_html=True)

        for _, row in df.iterrows():
            id_           = row["id"]
            desc          = row["descricao"]
            v_tot         = float(row["valor_total"])
            parc_tot      = int(row["parcelas_totais"])
            parc_pagas    = int(row.get("parcelas_pagas", 0))
            parc_restantes = max(0, parc_tot - parc_pagas)
            eh_fixa       = int(row["recorrente"]) == 1
            pago_fim      = bool(row["pago"])

            if eh_fixa:
                val_exibir = v_tot
                venc_data  = calcular_proxima_recorrente(to_date(row["inicio_pagamento"]))
            else:
                val_exibir = calcular_valor_parcela(v_tot, parc_tot)
                venc_data  = to_date(row["inicio_pagamento"])

            classe_row = "lancamento-row"
            if pago_fim:
                classe_row += " pago"
            elif venc_data < hoje:
                classe_row += " urgente"
            elif venc_data == hoje:
                classe_row += " hoje"
            elif venc_data <= hoje + timedelta(days=3):
                classe_row += " em-breve"
            elif eh_fixa:
                classe_row += " fixa"

            col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns([2.2, 1, 1, 1, 0.8])

            with col_r1:
                sub_desc = f"{t['total_label']} R$ {v_tot:,.2f} · {t['inicio_label']} {to_date(row['inicio_pagamento']).strftime('%d/%m/%Y')}" if not eh_fixa else t["conta_mensal_fixa"]
                st.markdown(f"<div style='padding-top:12px'><strong style='color:#fff; font-size:15px;'>{desc}</strong><br><span style='color:#6b7280; font-size:11px;'>{sub_desc}</span></div>", unsafe_allow_html=True)

            with col_r2:
                label_p = t["label_mensal"] if eh_fixa else t["label_parcela"]
                st.markdown(f"<div style='padding-top:12px'><strong style='font-family:JetBrains Mono; color:#9b8dff; font-size:16px;'>R$ {val_exibir:,.2f}</strong><br><span style='color:#6b7280; font-size:11px;'>{label_p}</span></div>", unsafe_allow_html=True)

            with col_r3:
                if pago_fim:
                    st.markdown("<div style='padding-top:18px'><span class='badge-pago'>Concluído ✅</span></div>", unsafe_allow_html=True)
                elif venc_data == hoje:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-hoje'>🔥 HOJE ({venc_data.strftime('%d/%m/%Y')})</span></div>", unsafe_allow_html=True)
                elif venc_data < hoje:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-urgente'>⚠️ ATRASADO ({venc_data.strftime('%d/%m/%Y')})</span></div>", unsafe_allow_html=True)
                elif venc_data <= hoje + timedelta(days=3):
                    dias_r = (venc_data - hoje).days
                    txt_r  = f"em {dias_r}d" if dias_r > 0 else "hoje"
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-em-breve'>⚡ {venc_data.strftime('%d/%m/%Y')} ({txt_r})</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-vence'>📅 {venc_data.strftime('%d/%m/%Y')}</span></div>", unsafe_allow_html=True)

            with col_r4:
                if pago_fim:
                    st.markdown(f"<div style='padding-top:18px; color:#4b5563; font-size:13px;'>{t['divida_encerrada']}</div>", unsafe_allow_html=True)
                elif eh_fixa:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-fixa'>{t['recorrente_inf']}</span></div>", unsafe_allow_html=True)
                else:
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
                        <span class='badge-parcelas'>{parc_restantes}x {t['x_restantes']}</span><br>
                        <span style='color:#6b7280; font-size:11px; display:block; margin-top:2px;'>{t['ultima_parcela']} <strong style='color:#90cdf4;'>{txt_ultima}</strong></span>
                        <span style='color:#6b7280; font-size:10px; display:block;'>{t['falta_pagar']} R$ {falta_pagar:,.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)

            with col_r5:
                st.markdown("<div style='padding-top:6px; display:flex; flex-direction:column; gap:4px;'>", unsafe_allow_html=True)
                if not pago_fim:
                    c_pagar  = f"btn_p_{id_}"
                    c_quitar = f"btn_q_{id_}"
                    st.markdown('<div class="btn-pagar">', unsafe_allow_html=True)
                    if st.button(t["btn_pagar"], key=c_pagar):
                        if eh_fixa:
                            avancar_parcela_recorrente(id_, row["inicio_pagamento"])
                        else:
                            avancar_parcela_parcelada_excel(id_, row["inicio_pagamento"], parc_tot, parc_pagas)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<div class="btn-quitar">', unsafe_allow_html=True)
                    if st.button(t["btn_quitar"], key=c_quitar):
                        marcar_pago(id_)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    if st.button(t["btn_excluir"], key=f"btn_del_{id_}"):
                        excluir_lancamento(id_)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"<br><br><center style='color:#4b5563; font-size:12px;'>{t['rodape']}</center>", unsafe_allow_html=True)

# ══════════════════════════════
# ABA 2 — FEEDBACK
# ══════════════════════════════
with aba_feedback:
    st.markdown(t["feedback_titulo"])
    st.markdown(f"<p style='color:#9ca3af; margin-top:-10px;'>{t['feedback_sub']}</p>", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        mensagem_fb = st.text_area(
            t["feedback_label"],
            placeholder=t["feedback_placeholder"],
            height=160,
            key="feedback_texto"
        )
        col_fb, _ = st.columns([1, 3])
        with col_fb:
            if st.button(t["feedback_btn"], key="btn_feedback"):
                if not mensagem_fb.strip():
                    st.error(t["feedback_vazio"])
                elif len(mensagem_fb.strip()) < 8:
                    st.error(t["feedback_curto"])
                else:
                    if inserir_feedback(uid, mensagem_fb):
                        st.success(t["feedback_ok"])
                        st.balloons()
        st.markdown('</div>', unsafe_allow_html=True)
