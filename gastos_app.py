# gastos_app.py — Gastei | versão refatorada com Google OAuth + Trial de 7 dias
# Ordem de execução garantida: imports → config → session_state → CSS →
# get_pool → run_query → CALLBACK OAUTH → init_db → helpers → funções →
# validação de sessão "s" → tela login (se não logado) → app principal

import streamlit as st
import psycopg2
import psycopg2.extras
import psycopg2.pool
import pandas as pd
import requests
import hashlib
import hmac
import re
import calendar
import smtplib
import secrets as _secrets
from datetime import date, timedelta
from urllib.parse import urlencode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─────────────────────────────────────────────
#  CONSTANTES GLOBAIS
# ─────────────────────────────────────────────
TRIAL_DIAS       = 7
KIWIFY_URL       = "https://pay.kiwify.com.br/CtPYesz"
WA_SUPORTE       = "5567991158892"
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_INFO_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

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
<meta name="apple-mobile-web-app-title" content="Gastei">
<meta name="theme-color" content="#6a3de8">
<meta name="application-name" content="Controle de Gastos">
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE — inicializa ANTES de tudo
# ─────────────────────────────────────────────
_SS_DEFAULTS = {
    "usuario_id":         None,
    "usuario_nome":       None,
    "lang":               "PT",
    "salario":            0.0,
    "pref_aberto":        False,
    "reset_step":         0,
    "reset_email":        "",
    "_salario_carregado": False,
    "oauth_state":        "",
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────
#  IDIOMA — intercepta antes de qualquer widget
# ─────────────────────────────────────────────
_LANG_CODES = ["PT", "EN", "FR"]
if "seletor_idioma" in st.session_state and st.session_state["seletor_idioma"]:
    _esc = st.session_state["seletor_idioma"]
    _det = "EN" if "English" in _esc else ("FR" if "Français" in _esc else "PT")
    if st.session_state.lang != _det:
        st.session_state.lang = _det
        st.rerun()
if st.session_state.lang not in _LANG_CODES:
    st.session_state.lang = "PT"

# ─────────────────────────────────────────────
#  I18N — TRILÍNGUE
# ─────────────────────────────────────────────
IDIOMAS = {
    "PT": {
        "app_subtitle": "Finanças Pessoais Premium Inteligentes",
        "ola": "Olá", "sair": "🚪",
        "aba_gastos": "📊 Meus Gastos", "aba_feedback": "💬 Feedbacks & Sugestões",
        "total_saidas": "Total de Saídas Contratadas",
        "comprometido_mes": "Comprometido Este Mês",
        "salario_comprometido": "Salário Comprometido (Próx. Mês)",
        "novo_lancamento": "➕ Novo Lançamento",
        "o_que_comprou": "O que comprou / Pagou",
        "placeholder_desc": "Ex: iPhone 16, Aluguel, Internet...",
        "valor_total": "Valor Total (R$)",
        "conta_fixa": "🔁 Conta Fixa / Recorrente (sem data de término — Aluguel, Internet...)",
        "dia_vencimento": "Dia de Vencimento (Data de Início)",
        "num_parcelas": "Número de Parcelas",
        "data_primeiro_venc": "Data do Primeiro Vencimento",
        "valor_mensal": "**Valor mensal:**", "tipo_recorrente": "**Tipo:**",
        "prox_vencimento": "**Próximo vencimento:**", "valor_parcela": "**Valor por parcela:**",
        "parcelas_restantes": "**Parcelas restantes:**", "venc_parcela1": "**Vencimento da Parcela 1:**",
        "salvar_lancamento": "💾 Salvar Lançamento",
        "salvo_sucesso": "✅ **{}** salvo com sucesso!",
        "err_descricao": "⚠️ Preencha a descrição do gasto.",
        "err_valor": "⚠️ O valor deve ser maior que zero.",
        "historico": "### 📋 Histórico de Vencimentos",
        "filtrar": "🔍 Filtrar por descrição", "placeholder_busca": "Digite para buscar...",
        "nenhum_lancamento": "Nenhum lançamento ainda.",
        "conta_atrasada_s": "conta atrasada", "conta_atrasada_p": "contas atrasadas",
        "conta_hoje_s": "conta vence hoje", "conta_hoje_p": "contas vencem hoje",
        "conta_breve_s": "conta vence", "conta_breve_p": "contas vencem",
        "alerta_breve_sufixo": "nos próximos 3 dias",
        "alerta_hoje_sufixo": "não deixe passar!",
        "alerta_atrasada_sufixo": "quite agora para não acumular juros!",
        "col_descricao": "Descrição", "col_valor": "Valor",
        "col_vencimento": "Próximo Vencimento", "col_situacao": "Situação", "col_acoes": "Ações",
        "label_mensal": "mensal", "label_parcela": "por parcela",
        "conta_mensal_fixa": "Conta Mensal Fixa", "total_label": "Total:", "inicio_label": "Início:",
        "divida_encerrada": "Dívida Encerrada", "ultima_parcela": "Última parcela:",
        "falta_pagar": "Falta pagar:", "recorrente_inf": "Recorrente ∞", "x_restantes": "x restantes",
        "btn_pagar": "💸 Pagar Parcela", "btn_quitar": "🏁 Quitar Tudo", "btn_excluir": "🗑️ Excluir",
        "salario_titulo": "💰 Meu Salário Mensal", "salario_input": "Salário Mensal Líquido (R$)",
        "salario_btn": "💾 Salvar Salário", "salario_salvo": "✅ Salário atualizado!",
        "salario_zero_aviso": "⚠️ Cadastre seu salário no painel ⚙️ para ver o % comprometido.",
        "pct_label": "% do salário comprometido no próximo mês",
        "sim_alerta": (
            "⚠️ TEM CERTEZA QUE QUER FAZER ESTA CONTA? {:.1f}% DO SEU SALÁRIO ESTARÁ COMPROMETIDO; "
            "É MELHOR NÃO FAZER ESTA CONTA, POIS ESTÁ ALÉM DO QUE VOCÊ CONSEGUE PAGAR PARA O PRÓXIMO MÊS!"
        ),
        "sim_ok": "✅ Dentro do limite saudável (abaixo de 70% do salário).",
        "sim_info": "💡 Com este gasto: **R$ {:.2f}/mês** comprometido ({:.1f}% do salário).",
        "pref_fechar": "Fechar",
        "feedback_titulo": "### 💬 Canal Direct de Sugestões & Feedbacks",
        "feedback_sub": "Sua opinião molda as próximas atualizações da nossa plataforma!",
        "feedback_label": "Sua mensagem",
        "feedback_placeholder": "Ex: Seria massa ver um gráfico de pizza no topo...",
        "feedback_btn": "📨 Enviar Meu Feedback",
        "feedback_vazio": "⚠️ Escreva algo antes de clicar em enviar.",
        "feedback_curto": "⚠️ Detalhe um pouquinho mais a sua mensagem.",
        "feedback_ok": "✅ Feedback enviado com absoluto sucesso! Muito obrigado 🙏",
        "rodape": "© 2026 Gastei App. Todos os direitos reservados. Suporte: finatechsuporte@gmail.com",
        "idioma_label": "🌐 Idioma",
        "login_titulo_app": "Finanças Premium", "login_sub_app": "Controle de Gastos de Alta Performance",
        "aba_entrar": "🔑  Entrar", "aba_criar_conta": "✨  Criar Conta",
        "btn_entrar_seta": "Entrar →", "err_preencha_dados": "Preencha e-mail e senha.",
        "msg_suporte_wa": "Olá! Quero verificar o status do meu acesso no app Gastei.",
        "link_suporte": "Problemas com o acesso? — Falar com o Suporte",
        "link_vendas": "Ainda não tem acesso? Conheça o Gastei →",
        "link_vendas_planos": "Ainda não comprou? Conheça os planos →",
        "expander_termos": "🛡️ Termos de Uso e Política de Privacidade",
        "texto_termos": "Seus dados financeiros são armazenados de forma criptografada e privativa. Não compartilhamos suas informações.",
        "info_reset_email": "📧 Informe o e-mail cadastrado. Enviaremos um código de 6 dígitos.",
        "input_email_cadastrado": "E-mail cadastrado", "btn_enviar_codigo": "Enviar código →",
        "err_email_nao_encontrado": "E-mail não encontrado.",
        "sucesso_codigo_enviado": "✅ Código enviado para **{}**.",
        "input_codigo_digitos": "Código de 6 dígitos", "input_nova_senha": "Nova senha",
        "input_confirmar_nova": "Confirmar nova senha", "btn_redefinir_senha": "Redefinir senha →",
        "err_informe_codigo": "Informe o código.", "err_senha_curta": "Mínimo 6 caracteres.",
        "err_senhas_diferentes": "Senhas não conferem.", "err_codigo_expirado": "Código inválido ou expirado.",
        "sucesso_senha_redefinida": "🎉 Senha redefinida! Faça login.",
        "input_nome": "Seu nome", "input_telefone": "WhatsApp / Telefone",
        "input_confirmar_senha": "Confirmar senha", "btn_criar_conta": "Criar minha conta →",
        "err_campos_vazios": "Preencha todos os campos.", "err_tel_invalido": "Telefone inválido.",
        "sucesso_conta_criada": "✅ Conta criada! Faça login na aba ao lado.",
        "não_autorizado": "Acesso Negado! Este e-mail não possui licença ativa.",
        "assinatura_expirada": "Assinatura expirada! Renove para reativar.",
        "input_email": "E-mail", "holder_email": "seu@email.com", "input_senha": "Senha",
        "link_esqueceu": "🔑 Esqueci minha senha",
        "err_bloqueado": "🛑 Acesso Bloqueado! Assinatura expirada ou e-mail não autorizado.",
        "err_dados_invalidos": "E-mail ou senha incorretos.",
        "trial_aviso": "⏰ Seu teste grátis termina em **{} dia(s)**!",
        "trial_assinar": "🔓 Assinar agora",
    },
    "EN": {
        "app_subtitle": "Intelligent Premium Personal Finance",
        "ola": "Hello", "sair": "🚪",
        "aba_gastos": "📊 My Expenses", "aba_feedback": "💬 Feedback & Suggestions",
        "total_saidas": "Total Contracted Expenses",
        "comprometido_mes": "Committed This Month",
        "salario_comprometido": "Salary Committed (Next Month)",
        "novo_lancamento": "➕ New Entry", "o_que_comprou": "What did you buy / pay",
        "placeholder_desc": "e.g.: iPhone 16, Rent, Internet...", "valor_total": "Total Amount (R$)",
        "conta_fixa": "🔁 Fixed / Recurring Bill (no end date — Rent, Internet...)",
        "dia_vencimento": "Due Day (Start Date)", "num_parcelas": "Number of Installments",
        "data_primeiro_venc": "First Due Date", "valor_mensal": "**Monthly amount:**",
        "tipo_recorrente": "**Type:**", "prox_vencimento": "**Next due date:**",
        "valor_parcela": "**Installment value:**", "parcelas_restantes": "**Remaining installments:**",
        "venc_parcela1": "**Due date of installment 1:**", "salvar_lancamento": "💾 Save Entry",
        "salvo_sucesso": "✅ **{}** saved successfully!", "err_descricao": "⚠️ Please fill in the expense description.",
        "err_valor": "⚠️ Amount must be greater than zero.", "historico": "### 📋 Payment History",
        "filtrar": "🔍 Filter by description", "placeholder_busca": "Type to search...",
        "nenhum_lancamento": "No entries yet.",
        "conta_atrasada_s": "overdue bill", "conta_atrasada_p": "overdue bills",
        "conta_hoje_s": "bill due today", "conta_hoje_p": "bills due today",
        "conta_breve_s": "bill due", "conta_breve_p": "bills due",
        "alerta_breve_sufixo": "in the next 3 days", "alerta_hoje_sufixo": "don't let it pass!",
        "alerta_atrasada_sufixo": "pay now to avoid late fees!",
        "col_descricao": "Description", "col_valor": "Amount",
        "col_vencimento": "Next Due Date", "col_situacao": "Status", "col_acoes": "Actions",
        "label_mensal": "monthly", "label_parcela": "per installment",
        "conta_mensal_fixa": "Fixed Monthly Bill", "total_label": "Total:", "inicio_label": "Start:",
        "divida_encerrada": "Debt Settled", "ultima_parcela": "Last installment:",
        "falta_pagar": "Remaining:", "recorrente_inf": "Recurring ∞", "x_restantes": "remaining",
        "btn_pagar": "💸 Pay Installment", "btn_quitar": "🏁 Pay Off All", "btn_excluir": "🗑️ Delete",
        "salario_titulo": "💰 My Monthly Salary", "salario_input": "Net Monthly Salary (R$)",
        "salario_btn": "💾 Save Salary", "salario_salvo": "✅ Salary updated!",
        "salario_zero_aviso": "⚠️ Set your salary in the ⚙️ panel to see the committed % of income.",
        "pct_label": "% of salary committed next month",
        "sim_alerta": (
            "⚠️ ARE YOU SURE YOU WANT TO MAKE THIS EXPENSE? {:.1f}% OF YOUR SALARY WILL BE COMMITTED; "
            "IT IS BETTER NOT TO MAKE THIS EXPENSE, AS IT IS BEYOND WHAT YOU CAN AFFORD FOR NEXT MONTH!"
        ),
        "sim_ok": "✅ Within healthy limit (below 70% of salary).",
        "sim_info": "💡 With this expense: **R$ {:.2f}/month** committed ({:.1f}% of salary).",
        "pref_fechar": "Close",
        "feedback_titulo": "### 💬 Suggestions & Feedback Channel",
        "feedback_sub": "Your opinion shapes the next updates to our platform!",
        "feedback_label": "Your message",
        "feedback_placeholder": "e.g.: It'd be great to see a pie chart at the top...",
        "feedback_btn": "📨 Send My Feedback",
        "feedback_vazio": "⚠️ Please write something before clicking send.",
        "feedback_curto": "⚠️ Please elaborate a little more on your message.",
        "feedback_ok": "✅ Feedback sent successfully! Thank you so much 🙏",
        "rodape": "© 2026 Gastei App. All rights reserved. Support: finatechsuporte@gmail.com",
        "idioma_label": "🌐 Language",
        "login_titulo_app": "Premium Finance", "login_sub_app": "High-Performance Expense Control",
        "aba_entrar": "🔑  Login", "aba_criar_conta": "✨  Create Account",
        "btn_entrar_seta": "Login →", "err_preencha_dados": "Please fill in email and password.",
        "msg_suporte_wa": "Hello! I want to check the status of my access in the Gastei app.",
        "link_suporte": "Access problems? — Contact Support",
        "link_vendas": "Don't have access yet? Meet Gastei →",
        "link_vendas_planos": "Haven't purchased yet? See the plans →",
        "expander_termos": "🛡️ Terms of Use and Privacy Policy",
        "texto_termos": "Your financial data is stored in an encrypted and private way. We do not share your information.",
        "info_reset_email": "📧 Enter your registered email. We'll send a 6-digit code.",
        "input_email_cadastrado": "Registered email", "btn_enviar_codigo": "Send code →",
        "err_email_nao_encontrado": "Email not found.",
        "sucesso_codigo_enviado": "✅ Code sent to **{}**.",
        "input_codigo_digitos": "6-digit code", "input_nova_senha": "New password",
        "input_confirmar_nova": "Confirm new password", "btn_redefinir_senha": "Reset password →",
        "err_informe_codigo": "Enter the code.", "err_senha_curta": "Minimum 6 characters.",
        "err_senhas_diferentes": "Passwords don't match.", "err_codigo_expirado": "Invalid or expired code.",
        "sucesso_senha_redefinida": "🎉 Password reset! Please login.",
        "input_nome": "Your name", "input_telefone": "WhatsApp / Phone",
        "input_confirmar_senha": "Confirm password", "btn_criar_conta": "Create my account →",
        "err_campos_vazios": "Please fill in all fields.", "err_tel_invalido": "Invalid phone number.",
        "sucesso_conta_criada": "✅ Account created! Log in on the next tab.",
        "não_autorizado": "Access Denied! This email does not have an active license.",
        "assinatura_expirada": "Subscription expired! Renew to reactivate.",
        "input_email": "Email", "holder_email": "your@email.com", "input_senha": "Password",
        "link_esqueceu": "🔑 Forgot my password",
        "err_bloqueado": "🛑 Access Blocked! Subscription expired or email not authorized.",
        "err_dados_invalidos": "Incorrect email or password.",
        "trial_aviso": "⏰ Your free trial ends in **{} day(s)**!",
        "trial_assinar": "🔓 Subscribe now",
    },
    "FR": {
        "app_subtitle": "Finances Personnelles Premium Intelligentes",
        "ola": "Bonjour", "sair": "🚪",
        "aba_gastos": "📊 Mes Dépenses", "aba_feedback": "💬 Retours & Suggestions",
        "total_saidas": "Total des Dépenses Contractées",
        "comprometido_mes": "Engagé Ce Mois",
        "salario_comprometido": "Salaire Engagé (Mois Prochain)",
        "novo_lancamento": "➕ Nouvelle Entrée", "o_que_comprou": "Qu'avez-vous acheté / payé",
        "placeholder_desc": "Ex: iPhone 16, Loyer, Internet...", "valor_total": "Montant Total (R$)",
        "conta_fixa": "🔁 Facture Fixe / Récurrente (sans date de fin — Loyer, Internet...)",
        "dia_vencimento": "Jour d'Échéance (Date de Début)", "num_parcelas": "Nombre de Versements",
        "data_primeiro_venc": "Date de la Première Échéance", "valor_mensal": "**Montant mensuel :**",
        "tipo_recorrente": "**Type :**", "prox_vencimento": "**Prochaine échéance :**",
        "valor_parcela": "**Valeur du versement :**", "parcelas_restantes": "**Versements restants :**",
        "venc_parcela1": "**Échéance du versement 1 :**", "salvar_lancamento": "💾 Enregistrer",
        "salvo_sucesso": "✅ **{}** enregistré avec succès !",
        "err_descricao": "⚠️ Veuillez renseigner la description de la dépense.",
        "err_valor": "⚠️ Le montant doit être supérieur à zéro.", "historico": "### 📋 Historique des Échéances",
        "filtrar": "🔍 Filtrer par description", "placeholder_busca": "Tapez pour rechercher...",
        "nenhum_lancamento": "Aucune entrée pour l'instant.",
        "conta_atrasada_s": "facture en retard", "conta_atrasada_p": "factures en retard",
        "conta_hoje_s": "facture due aujourd'hui", "conta_hoje_p": "factures dues aujourd'hui",
        "conta_breve_s": "facture due", "conta_breve_p": "factures dues",
        "alerta_breve_sufixo": "dans les 3 prochains jours", "alerta_hoje_sufixo": "ne laissez pas passer !",
        "alerta_atrasada_sufixo": "payez maintenant pour éviter les pénalités !",
        "col_descricao": "Description", "col_valor": "Montant",
        "col_vencimento": "Prochaine Échéance", "col_situacao": "Statut", "col_acoes": "Actions",
        "label_mensal": "mensuel", "label_parcela": "par versement",
        "conta_mensal_fixa": "Facture Mensuelle Fixe", "total_label": "Total :", "inicio_label": "Début :",
        "divida_encerrada": "Dette Réglée", "ultima_parcela": "Dernier versement :",
        "falta_pagar": "Reste à payer :", "recorrente_inf": "Récurrent ∞", "x_restantes": "restants",
        "btn_pagar": "💸 Payer le Versement", "btn_quitar": "🏁 Tout Régler", "btn_excluir": "🗑️ Supprimer",
        "salario_titulo": "💰 Mon Salaire Mensuel", "salario_input": "Salaire Mensuel Net (R$)",
        "salario_btn": "💾 Sauvegarder", "salario_salvo": "✅ Salaire mis à jour !",
        "salario_zero_aviso": "⚠️ Enregistrez votre salaire dans le panneau ⚙️ pour voir le % engagé.",
        "pct_label": "% du salaire engagé le mois prochain",
        "sim_alerta": (
            "⚠️ ÊTES-VOUS SÛR DE VOULOIR FAIRE CETTE DÉPENSE ? {:.1f}% DE VOTRE SALAIRE SERA ENGAGÉ ; "
            "IL VAUT MIEUX NE PAS FAIRE CETTE DÉPENSE, CAR ELLE DÉPASSE CE QUE VOUS POUVEZ PAYER POUR LE MOIS PROCHAIN !"
        ),
        "sim_ok": "✅ Dans la limite saine (moins de 70% du salaire).",
        "sim_info": "💡 Avec cette dépense : **R$ {:.2f}/mois** engagé ({:.1f}% du salaire).",
        "pref_fechar": "Fermer",
        "feedback_titulo": "### 💬 Canal de Suggestions & Retours",
        "feedback_sub": "Votre avis façonne les prochaines mises à jour de notre plateforme !",
        "feedback_label": "Votre message",
        "feedback_placeholder": "Ex : Ce serait super d'avoir un graphique en secteurs...",
        "feedback_btn": "📨 Envoyer Mon Retour",
        "feedback_vazio": "⚠️ Veuillez écrire quelque chose avant d'envoyer.",
        "feedback_curto": "⚠️ Veuillez développer un peu plus votre message.",
        "feedback_ok": "✅ Retour envoyé avec succès ! Merci beaucoup 🙏",
        "rodape": "© 2026 Gastei App. Tous droits réservés. Support : finatechsuporte@gmail.com",
        "idioma_label": "🌐 Langue",
        "login_titulo_app": "Finances Premium", "login_sub_app": "Contrôle des Dépenses Haute Performance",
        "aba_entrar": "🔑  Connexion", "aba_criar_conta": "✨  Créer un Compte",
        "btn_entrar_seta": "Se connecter →", "err_preencha_dados": "Veuillez entrer l'e-mail et le mot de passe.",
        "msg_suporte_wa": "Bonjour! Je souhaite vérifier le statut de mon accès sur l'application Gastei.",
        "link_suporte": "Problèmes d'accès? — Contacter le Support",
        "link_vendas": "Pas encore d'accès? Découvrez Gastei →",
        "link_vendas_planos": "Pas encore acheté? Voir les plans →",
        "expander_termos": "🛡️ Conditions d'Utilisation et Politique de Confidentialité",
        "texto_termos": "Vos données financières sont stockées de manière cryptée et privée. Nous ne partageons pas vos informations.",
        "info_reset_email": "📧 Entrez votre e-mail enregistré. Nous vous enverrons un code à 6 chiffres.",
        "input_email_cadastrado": "E-mail enregistré", "btn_enviar_codigo": "Envoyer le code →",
        "err_email_nao_encontrado": "E-mail non trouvé.",
        "sucesso_codigo_enviado": "✅ Code envoyé à **{}**.",
        "input_codigo_digitos": "Code à 6 chiffres", "input_nova_senha": "Nouveau mot de passe",
        "input_confirmar_nova": "Confirmer le mot de passe", "btn_redefinir_senha": "Réinitialiser le mot de passe →",
        "err_informe_codigo": "Entrez le code.", "err_senha_curta": "Minimum 6 caractères.",
        "err_senhas_diferentes": "Les mots de passe ne correspondent pas.", "err_codigo_expirado": "Code invalide ou expiré.",
        "sucesso_senha_redefinida": "🎉 Mot de passe réinitialisé! Connectez-vous.",
        "input_nome": "Votre nom", "input_telefone": "WhatsApp / Téléphone",
        "input_confirmar_senha": "Confirmer le mot de passe", "btn_criar_conta": "Créer mon compte →",
        "err_campos_vazios": "Veuillez remplir tous les champs.", "err_tel_invalido": "Numéro de téléphone invalide.",
        "sucesso_conta_criada": "✅ Compte créé! Connectez-vous dans l'onglet d'à côté.",
        "não_autorizado": "Accès Refusé! Cet e-mail n'a pas de licence active.",
        "assinatura_expirada": "Abonnement expiré! Renouvelez pour réactiver.",
        "input_email": "E-mail", "holder_email": "votre@email.com", "input_senha": "Mot de passe",
        "link_esqueceu": "🔑 Mot de passe oublié",
        "err_bloqueado": "🛑 Accès Bloqué! Abonnement expiré ou e-mail non autorisé.",
        "err_dados_invalidos": "E-mail ou mot de passe incorrect.",
        "trial_aviso": "⏰ Votre essai gratuit se termine dans **{} jour(s)** !",
        "trial_assinar": "🔓 S'abonner maintenant",
    },
}

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
h1 { font-family: 'Sora', sans-serif !important; font-weight: 700 !important;
    background: linear-gradient(90deg, #e2c4f0, #9b8dff, #64b5f6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.5px; }
h2, h3 { font-family: 'Sora', sans-serif !important; color: #c9d1f0 !important; }
.login-wrap { max-width: 460px; margin: 60px auto 0;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(155,141,255,0.2);
    border-radius: 24px; padding: 48px 40px;
    box-shadow: 0 8px 60px rgba(106,61,232,0.25); backdrop-filter: blur(12px); }
.login-logo { text-align:center; font-size:52px; margin-bottom:8px; }
.login-title { text-align:center; font-size:26px; font-weight:700;
    background: linear-gradient(90deg, #e2c4f0, #9b8dff, #64b5f6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom:4px; }
.login-sub { text-align:center; font-size:13px; color:#6b7280; margin-bottom:32px; }
.total-card { background: linear-gradient(135deg, #6a3de8 0%, #9b8dff 100%);
    border-radius: 20px; padding: 32px 40px;
    box-shadow: 0 8px 40px rgba(106,61,232,0.45); margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between; }
.total-label { font-size:13px; font-weight:600; letter-spacing:2px; text-transform:uppercase; color:rgba(255,255,255,0.75); margin-bottom:6px; }
.total-value { font-family:'JetBrains Mono',monospace; font-size:42px; font-weight:700; color:#fff; letter-spacing:-1px; }
.total-icon  { font-size:56px; opacity:0.5; }
.parcela-card { background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
    border: 1px solid rgba(100,181,246,0.25); border-radius: 20px; padding: 24px 32px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3); margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between; }
.parcela-label { font-size:13px; font-weight:600; letter-spacing:2px; text-transform:uppercase; color:rgba(100,181,246,0.75); margin-bottom:6px; }
.parcela-value { font-family:'JetBrains Mono',monospace; font-size:34px; font-weight:700; color:#64b5f6; }
.salario-card { background: linear-gradient(135deg, #1a2e1e 0%, #0d2118 100%);
    border: 1px solid rgba(52,211,153,0.25); border-radius: 20px; padding: 24px 32px; margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
.salario-card.alerta { background: linear-gradient(135deg, #2e1a1a 0%, #210d0d 100%); border-color: rgba(239,68,68,0.35); }
.salario-label { font-size:13px; font-weight:600; letter-spacing:2px; text-transform:uppercase; color:rgba(52,211,153,0.75); margin-bottom:6px; }
.salario-card.alerta .salario-label { color:rgba(239,68,68,0.75); }
.salario-value { font-family:'JetBrains Mono',monospace; font-size:34px; font-weight:700; color:#34d399; }
.salario-card.alerta .salario-value { color:#ef4444; }
@keyframes pulse-alerta {
    0%,100% { box-shadow: 0 0 0 1px rgba(239,68,68,0.5), 0 0 20px rgba(239,68,68,0.2); opacity:1; }
    50%      { box-shadow: 0 0 0 2px rgba(239,68,68,0.8), 0 0 40px rgba(239,68,68,0.4); opacity:0.88; } }
.alerta-simulacao { background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(251,146,60,0.1));
    border: 2px solid rgba(239,68,68,0.6); border-radius: 14px; padding: 18px 22px;
    font-size: 13px; font-weight: 700; color: #fca5a5; letter-spacing: 0.03em; line-height: 1.6;
    animation: pulse-alerta 1.8s ease-in-out infinite; margin-top: 12px; }
.alerta-simulacao .pct-destaque { font-size: 24px; font-weight: 800; color: #ef4444;
    display: block; margin-bottom: 8px; font-family: 'JetBrains Mono', monospace; }
.form-section { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px; padding: 28px 32px; margin-bottom: 32px; backdrop-filter: blur(10px); }
.alerta-banner { display:flex; align-items:center; gap:8px; background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.3); border-radius: 10px; padding: 7px 14px;
    font-size:11px; font-weight:700; color:#fca5a5; letter-spacing:0.04em; margin-bottom: 20px; }
.alerta-banner .count { background: #ef4444; color:#fff; border-radius: 999px; padding: 1px 8px; font-size:11px; font-weight:800; }
.hoje-banner { display:flex; align-items:center; gap:8px; background: rgba(251,146,60,0.12);
    border: 1px solid rgba(251,146,60,0.35); border-radius: 10px; padding: 7px 14px;
    font-size:11px; font-weight:700; color:#fdba74; letter-spacing:0.04em; margin-bottom: 8px; }
label { color:#a0aec0 !important; font-size:13px !important; font-weight:600 !important; letter-spacing:0.5px !important; }
.stCheckbox label { color:#c9d1f0 !important; font-size:14px !important; font-weight:600 !important; }
.stButton > button { background: linear-gradient(135deg, #6a3de8, #9b8dff) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important; font-weight: 600 !important; font-size: 14px !important;
    padding: 12px 28px !important; width: 100% !important;
    letter-spacing: 0.5px !important; box-shadow: 0 4px 20px rgba(106,61,232,0.4) !important; transition: all 0.2s !important; }
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(106,61,232,0.6) !important; }
.btn-link > button { background: transparent !important; border: none !important; color: #9b8dff !important;
    font-size: 13px !important; padding: 4px 0 !important; box-shadow: none !important; width: auto !important;
    text-decoration: underline !important; text-underline-offset: 3px !important; opacity: 0.85 !important; }
.btn-link > button:hover { opacity: 1 !important; transform: none !important; box-shadow: none !important; }
.logout-btn > button { background: rgba(255,255,255,0.06) !important; border: 1px solid rgba(255,255,255,0.12) !important;
    font-size: 12px !important; padding: 6px 14px !important; box-shadow: none !important;
    width: auto !important; color: #9ca3af !important; }
.logout-btn > button:hover { background: rgba(255,80,80,0.12) !important; color: #fca5a5 !important; border-color: rgba(255,80,80,0.3) !important; }
.pref-btn > button { background: rgba(155,141,255,0.1) !important; border: 1px solid rgba(155,141,255,0.3) !important;
    color: #c4b5fd !important; font-size: 18px !important; padding: 6px 12px !important;
    border-radius: 10px !important; box-shadow: none !important; width: auto !important; transition: all 0.2s !important; }
.pref-btn > button:hover { background: rgba(155,141,255,0.22) !important; border-color: rgba(155,141,255,0.6) !important;
    transform: rotate(30deg) !important; box-shadow: 0 0 12px rgba(155,141,255,0.3) !important; }
.btn-pagar > button { background: linear-gradient(135deg, #059669, #34d399) !important;
    font-size: 11px !important; padding: 6px 10px !important;
    box-shadow: 0 2px 10px rgba(5,150,105,0.3) !important; width: 100% !important; }
.btn-quitar > button { background: linear-gradient(135deg, #7c3aed, #a78bfa) !important;
    font-size: 11px !important; padding: 6px 10px !important;
    box-shadow: 0 2px 10px rgba(124,58,237,0.3) !important; width: 100% !important; }
.pref-panel { background: rgba(26,26,46,0.97); border: 1px solid rgba(155,141,255,0.25);
    border-radius: 16px; padding: 20px 24px; margin-bottom: 20px;
    backdrop-filter: blur(14px); box-shadow: 0 8px 40px rgba(106,61,232,0.25);
    animation: fadeInDown 0.18s ease; }
@keyframes fadeInDown { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:translateY(0); } }
.badge-parcelas { background:rgba(106,61,232,0.25); border:1px solid rgba(155,141,255,0.4); color:#c4b5fd; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-vence    { background:rgba(100,181,246,0.15); border:1px solid rgba(100,181,246,0.35); color:#90cdf4; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-fixa     { background:rgba(251,191,36,0.15); border:1px solid rgba(251,191,36,0.4); color:#fbbf24; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-urgente  { background:rgba(239,68,68,0.2); border:1px solid rgba(239,68,68,0.5); color:#fca5a5; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-hoje     { background:rgba(251,146,60,0.2); border:1px solid rgba(251,146,60,0.5); color:#fdba74; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-em-breve { background:rgba(234,179,8,0.15); border:1px solid rgba(234,179,8,0.4); color:#fde047; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; display:inline-block; }
.badge-pago     { background:rgba(52,211,153,0.1); border:1px solid rgba(52,211,153,0.4); color:#6ee7b7; border-radius:999px; padding:4px 12px; font-size:12px; font-weight:600; font-family:'JetBrains Mono',monospace; display:inline-block; }
.blq { max-width:560px; margin:60px auto 0; background:rgba(255,255,255,0.03);
    border:1px solid rgba(239,68,68,0.25); border-radius:24px; padding:48px 40px;
    box-shadow:0 8px 60px rgba(239,68,68,0.12); backdrop-filter:blur(14px);
    text-align:center; animation:blqIn .4s ease; }
@keyframes blqIn { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
.blq-titulo { font-size:28px; font-weight:800;
    background:linear-gradient(90deg,#ef4444,#fca5a5);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:10px; }
.blq-sub { color:#9ca3af; font-size:15px; margin-bottom:28px; line-height:1.65; }
.blq-badge { display:inline-block; background:rgba(106,61,232,0.16);
    border:1px solid rgba(155,141,255,0.4); border-radius:999px;
    padding:7px 22px; color:#c4b5fd; font-size:13px; font-weight:700; margin-bottom:24px; }
.blq-features { text-align:left; margin:0 auto 24px; max-width:320px;
    color:#9ca3af; font-size:14px; list-style:none; padding:0; }
.blq-features li { padding:5px 0; }
.blq-features li::before { content:"✅ "; }
.blq-btn { display:block; background:linear-gradient(135deg,#6a3de8,#9b8dff);
    color:#fff!important; text-decoration:none!important; border-radius:14px;
    padding:18px 32px; font-size:17px; font-weight:700; letter-spacing:.5px;
    box-shadow:0 4px 24px rgba(106,61,232,.45);
    transition:transform .2s,box-shadow .2s; margin-bottom:14px; }
.blq-btn:hover { transform:translateY(-2px); box-shadow:0 8px 36px rgba(106,61,232,.6); }
.blq-wa { display:inline-flex; align-items:center; gap:8px;
    color:#34d399!important; text-decoration:none!important;
    font-size:14px; font-weight:600; opacity:.85; }
.blq-wa:hover { opacity:1; }
hr { border-color:rgba(255,255,255,0.07) !important; margin:28px 0 !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1100px; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(155,141,255,0.4); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════
#  CONNECTION POOL + run_query
# ═════════════════════════════════════════════
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

# ═════════════════════════════════════════════
#  GOOGLE OAUTH — funções (definidas APÓS run_query)
# ═════════════════════════════════════════════
def google_auth_url(state: str) -> str:
    try:
        cfg = st.secrets["google_oauth"]
        p = {
            "client_id":     cfg["client_id"],
            "redirect_uri":  cfg["redirect_uri"],
            "response_type": "code",
            "scope":         "openid email profile",
            "access_type":   "offline",
            "state":         state,
            "prompt":        "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(p)}"
    except Exception:
        return ""

def google_exchange_code(code: str) -> dict | None:
    try:
        cfg = st.secrets["google_oauth"]
        tok = requests.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri":  cfg["redirect_uri"],
            "grant_type":    "authorization_code",
        }, timeout=10)
        tok.raise_for_status()
        info = requests.get(GOOGLE_INFO_URL, headers={
            "Authorization": f"Bearer {tok.json()['access_token']}"
        }, timeout=10)
        info.raise_for_status()
        u = info.json()
        return {
            "provider_id": u.get("sub", ""),
            "email":       u.get("email", "").lower().strip(),
            "nome":        u.get("name") or u.get("given_name") or "Usuário Google",
            "avatar_url":  u.get("picture", ""),
        }
    except Exception as e:
        st.error(f"❌ Erro Google OAuth: {e}"); return None

def upsert_usuario_google(dados: dict) -> tuple[int, str] | None:
    """
    Cria ou localiza o usuário Google no banco.
    Recebe o dict direto (sem run_query_fn como parâmetro) pois run_query
    já está definida no escopo global neste ponto do arquivo.
    Ordem: provider_id → e-mail existente → cria novo em trial.
    """
    email = dados["email"]
    pid   = dados["provider_id"]
    nome  = dados["nome"]
    av    = dados["avatar_url"]
    try:
        # 1. busca pelo ID único do Google
        rows = run_query(
            "SELECT id,nome FROM usuarios WHERE provedor='google' AND provider_id=%s",
            (pid,), fetch=True)
        if rows:
            return rows[0]["id"], rows[0]["nome"]

        # 2. busca por e-mail (conta manual pré-existente) → vincula
        rows = run_query("SELECT id,nome FROM usuarios WHERE email=%s", (email,), fetch=True)
        if rows:
            run_query(
                "UPDATE usuarios SET provedor='google', provider_id=%s, avatar_url=%s WHERE id=%s",
                (pid, av, rows[0]["id"]))
            return rows[0]["id"], rows[0]["nome"]

        # 3. cria conta nova diretamente em trial
        run_query("""
            INSERT INTO usuarios
              (nome, email, senha, telefone, provedor, provider_id, avatar_url,
               status_assinatura, trial_inicio, salario)
            VALUES (%s, %s, '', '', 'google', %s, %s, 'trial', NOW(), 0)
        """, (nome, email, pid, av))
        rows = run_query("SELECT id FROM usuarios WHERE email=%s", (email,), fetch=True)
        if rows:
            _expira = date.today() + timedelta(days=TRIAL_DIAS)
            try:
                run_query("""
                    INSERT INTO licencas_ativas (email, tipo_licenca, expira_em)
                    VALUES (%s, 'trial', %s)
                    ON CONFLICT (email) DO NOTHING
                """, (email, _expira))
            except Exception:
                pass
            return rows[0]["id"], nome
    except Exception as e:
        st.error(f"❌ Erro ao registrar usuário Google: {e}")
    return None

# ═════════════════════════════════════════════
#  CALLBACK DO GOOGLE — intercepta AQUI (run_query já existe)
# ═════════════════════════════════════════════
if st.session_state.usuario_id is None and "code" in st.query_params:
    _code = st.query_params["code"]
    st.query_params.clear()   # limpa URL imediatamente para evitar loop
    with st.spinner("Conectando sua conta Google..."):
        try:
            _dados = google_exchange_code(_code)
            if _dados and "email" in _dados:
                _retorno = upsert_usuario_google(_dados)
                if _retorno:
                    st.session_state.usuario_id   = _retorno[0]
                    st.session_state.usuario_nome = _retorno[1]
                    st.rerun()
                else:
                    st.error("❌ Não foi possível registrar sua conta. Tente novamente.")
            else:
                st.error("❌ Não foi possível obter seus dados do Google. Tente novamente.")
        except Exception as _e:
            st.error(f"❌ Erro crítico na autenticação Google: {_e}")

# ═════════════════════════════════════════════
#  INIT DB
# ═════════════════════════════════════════════
def init_db():
    run_query("""CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL DEFAULT '')""")
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
    # colunas opcionais em lancamentos
    for col, defn in [
        ("recorrente",    "SMALLINT NOT NULL DEFAULT 0"),
        ("usuario_id",    "INTEGER NOT NULL DEFAULT 0"),
        ("pago",          "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("parcelas_pagas","INTEGER NOT NULL DEFAULT 0"),
    ]:
        run_query(f"""DO $$ BEGIN IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='lancamentos' AND column_name='{col}'
        ) THEN ALTER TABLE lancamentos ADD COLUMN {col} {defn}; END IF; END$$""")
    # colunas de usuários
    for col, defn in [
        ("telefone",          "TEXT DEFAULT ''"),
        ("salario",           "NUMERIC(12,2) NOT NULL DEFAULT 0"),
        ("provedor",          "TEXT NOT NULL DEFAULT 'email'"),
        ("provider_id",       "TEXT NOT NULL DEFAULT ''"),
        ("avatar_url",        "TEXT NOT NULL DEFAULT ''"),
        ("status_assinatura", "TEXT NOT NULL DEFAULT 'trial'"),
        ("trial_inicio",      "TIMESTAMP NOT NULL DEFAULT NOW()"),
        ("aviso_d1_enviado",  "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("aviso_d0_enviado",  "BOOLEAN NOT NULL DEFAULT FALSE"),
    ]:
        run_query(f"""DO $$ BEGIN IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='usuarios' AND column_name='{col}'
        ) THEN ALTER TABLE usuarios ADD COLUMN {col} {defn}; END IF; END$$""")

@st.cache_resource
def init_db_once():
    init_db()

try:
    init_db_once()
except Exception as e:
    st.error(f"❌ Erro ao conectar ao banco: {e}")
    st.stop()

# ═════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════
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

# ═════════════════════════════════════════════
#  PAYWALL (licenças manuais)
# ═════════════════════════════════════════════
from datetime import datetime

@st.cache_data(ttl=60, show_spinner=False) # Diminuí o TTL para 1 minuto para testar mais rápido
    # 1. REMOVEMOS O CACHE temporariamente para testar sem interferência da memória
def verificar_status_licenca(email):
    try:
        rows = run_query("SELECT tipo_licenca, expira_em FROM licencas_ativas WHERE email=%s", (email.strip().lower(),), fetch=True)
        
        if not rows: 
            return False, "não_autorizado"
            
        dados_licenca = rows[0]
        tipo = dados_licenca.get("tipo_licenca")
        expira_em = dados_licenca.get("expira_em")
        
        if tipo == "trial" and expira_em:
            import datetime as dt
            if isinstance(expira_em, str):
                data_expiracao = dt.datetime.strptime(expira_em, "%Y-%m-%d").date()
            else:
                data_expiracao = expira_em
                
            # Se hoje passou da data, retorna EXATAMENTE o que o seu app espera para bloquear:
            if dt.date.today() > data_expiracao:
                return False, "não_autorizado"
                
        return True, "autorizado"
        
    except Exception as e:
        return False, "não_autorizado"
# ═════════════════════════════════════════════
#  RESET DE SENHA
# ═════════════════════════════════════════════
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
            <div style="text-align:center;font-size:48px;">💳</div>
            <h2 style="text-align:center;background:linear-gradient(90deg,#9b8dff,#64b5f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Redefinição de Senha</h2>
            <p style="color:#9ca3af;text-align:center;">Use o código abaixo. Ele expira em <strong style="color:#e8e4ff;">15 minutos</strong>.</p>
            <div style="background:#6a3de8;border-radius:12px;padding:20px;text-align:center;letter-spacing:12px;font-size:36px;font-weight:700;color:#fff;font-family:'JetBrains Mono',monospace;margin:20px 0;">{token}</div>
            <p style="color:#6b7280;font-size:12px;text-align:center;">Se não solicitou, ignore.</p></div>"""
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

# ═════════════════════════════════════════════
#  USUÁRIOS
# ═════════════════════════════════════════════
def criar_usuario(nome, email, senha, telefone=""):
    # Usuários manuais precisam de licença prévia na licencas_ativas
    ok, motivo = verificar_status_licenca(email)
    if not ok:
        t_ = get_t()
        msgs = {
            "não_autorizado":   t_.get("não_autorizado", "Acesso Negado! Este e-mail não possui licença ativa."),
            "assinatura_expirada": t_.get("assinatura_expirada", "Assinatura expirada! Renove para reativar."),
        }
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

# ═════════════════════════════════════════════
#  SALÁRIO
# ═════════════════════════════════════════════
@st.cache_data(ttl=120, show_spinner=False)
def buscar_salario_db(uid: int) -> float:
    try:
        rows = run_query("SELECT salario FROM usuarios WHERE id=%s", (uid,), fetch=True)
        if rows and rows[0]["salario"] is not None:
            return float(rows[0]["salario"])
    except Exception as e:
        st.error(f"❌ Erro ao buscar salário: {e}")
    return 0.0

def salvar_salario_db(uid: int, valor: float) -> bool:
    try:
        run_query("UPDATE usuarios SET salario=%s WHERE id=%s", (float(valor), uid))
        buscar_salario_db.clear()
        st.session_state.salario = valor
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar salário: {e}"); return False

# ═════════════════════════════════════════════
#  MOTOR DE TRIAL
# ═════════════════════════════════════════════
@st.cache_data(ttl=60, show_spinner=False)
def verificar_trial(usuario_id: int) -> dict:
    try:
        rows = run_query(
            "SELECT status_assinatura, trial_inicio FROM usuarios WHERE id=%s",
            (usuario_id,), fetch=True)
        if not rows:
            return {"acesso": False, "status": "erro", "dias_restantes": 0}
        u      = rows[0]
        status = u["status_assinatura"]
        if status in ("pago", "vitalicio", "assinatura_valida"):
            return {"acesso": True, "status": status, "dias_restantes": 999}
        if status == "trial":
            inicio = u["trial_inicio"]
            if hasattr(inicio, "date"): inicio = inicio.date()
            expira    = inicio + timedelta(days=TRIAL_DIAS)
            restantes = (expira - date.today()).days
            if restantes > 0:
                return {"acesso": True,  "status": "trial",    "dias_restantes": restantes}
            else:
                return {"acesso": False, "status": "expirado", "dias_restantes": 0}
    except Exception:
        pass
    return {"acesso": False, "status": "erro", "dias_restantes": 0}

def _smtp_send(cfg, dest, assunto, html):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto; msg["From"] = cfg["remetente"]; msg["To"] = dest
        msg.attach(MIMEText(html, "html"))
        porta = int(cfg.get("smtp_port", 587))
        if porta == 465:
            import ssl; ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["smtp_host"], porta, context=ctx) as s:
                s.login(cfg["remetente"], cfg["senha_smtp"])
                s.sendmail(cfg["remetente"], dest, msg.as_string())
        else:
            with smtplib.SMTP(cfg["smtp_host"], porta, timeout=10) as s:
                s.ehlo(); s.starttls(); s.ehlo()
                s.login(cfg["remetente"], cfg["senha_smtp"])
                s.sendmail(cfg["remetente"], dest, msg.as_string())
    except Exception: pass

def _job_emails_trial():
    hoje = date.today()
    try:
        cfg = st.secrets.get("email", {})
        if not cfg: return
        amanha = hoje + timedelta(days=1)
        rows = run_query(f"""
            SELECT id,nome,email FROM usuarios
            WHERE status_assinatura='trial' AND aviso_d1_enviado=FALSE
              AND (trial_inicio::date + interval '{TRIAL_DIAS-1} days')::date = '{amanha}'
        """, fetch=True)
        for u in (rows or []):
            html = f"""<div style="font-family:sans-serif;max-width:500px;margin:auto;background:#1a1a2e;border-radius:16px;padding:36px;color:#e8e4ff;">
              <div style="text-align:center;font-size:48px;">⏰</div>
              <h2 style="text-align:center;color:#fbbf24;">Seu teste termina amanhã!</h2>
              <p style="color:#9ca3af;text-align:center;">Olá, <strong style="color:#fff;">{u['nome']}</strong>! Não perca o controle das suas finanças.</p>
              <a href="{KIWIFY_URL}" style="display:block;background:linear-gradient(135deg,#6a3de8,#9b8dff);color:#fff;text-align:center;padding:16px;border-radius:12px;font-weight:700;font-size:15px;text-decoration:none;margin-top:24px;">
                🔓 Assinar Gastei Premium — R$ 24,90/mês</a></div>"""
            _smtp_send(cfg, u["email"], "⏰ Seu teste grátis termina amanhã — Gastei", html)
            run_query("UPDATE usuarios SET aviso_d1_enviado=TRUE WHERE id=%s", (u["id"],))
        rows = run_query(f"""
            SELECT id,nome,email FROM usuarios
            WHERE status_assinatura='trial' AND aviso_d0_enviado=FALSE
              AND (trial_inicio::date + interval '{TRIAL_DIAS} days')::date <= '{hoje}'
        """, fetch=True)
        for u in (rows or []):
            html = f"""<div style="font-family:sans-serif;max-width:500px;margin:auto;background:#1a1a2e;border-radius:16px;padding:36px;color:#e8e4ff;">
              <div style="text-align:center;font-size:48px;">🔒</div>
              <h2 style="text-align:center;color:#ef4444;">Acesso suspenso</h2>
              <p style="color:#9ca3af;text-align:center;">Olá, <strong style="color:#fff;">{u['nome']}</strong>! Seus {TRIAL_DIAS} dias gratuitos chegaram ao fim.</p>
              <a href="{KIWIFY_URL}" style="display:block;background:linear-gradient(135deg,#6a3de8,#9b8dff);color:#fff;text-align:center;padding:16px;border-radius:12px;font-weight:700;font-size:15px;text-decoration:none;margin-top:24px;">
                🚀 Reativar acesso — R$ 24,90/mês</a></div>"""
            _smtp_send(cfg, u["email"], "🔒 Seu acesso ao Gastei foi suspenso", html)
            run_query("UPDATE usuarios SET aviso_d0_enviado=TRUE WHERE id=%s", (u["id"],))
    except Exception: pass

@st.cache_data(ttl=86400, show_spinner=False)
def _job_diario(_dummy: int):
    _job_emails_trial()

# ═════════════════════════════════════════════
#  TELA DE BLOQUEIO
# ═════════════════════════════════════════════
def renderizar_tela_bloqueio(nome: str = ""):
    link_wa = f"https://wa.me/{WA_SUPORTE}?text=Quero%20assinar%20o%20Gastei%20Premium"
    nome_d  = f", {nome}" if nome else ""
    st.markdown(f"""
    <div class="blq">
      <div style="font-size:64px;margin-bottom:8px;">🔒</div>
      <div class="blq-titulo">Seu teste gratuito acabou</div>
      <p class="blq-sub">
        Olá{nome_d}! Seus <strong style="color:#fff;">{TRIAL_DIAS} dias grátis</strong>
        chegaram ao fim.<br>Seus dados estão salvos e esperando por você.
      </p>
      <div class="blq-badge">💳 Apenas R$ 24,90/mês · Cancele quando quiser</div>
      <ul class="blq-features">
        <li>Lançamentos e parcelas ilimitados</li>
        <li>Controle de contas fixas e variáveis</li>
        <li>Alertas de vencimento em tempo real</li>
        <li>Análise de % do salário comprometido</li>
        <li>Suporte prioritário via WhatsApp</li>
      </ul>
      <a href="{KIWIFY_URL}" target="_blank" class="blq-btn">
        🚀 Assinar Gastei Premium — R$ 24,90/mês
      </a><br>
      <a href="{link_wa}" target="_blank" class="blq-wa">
        💬 Falar com o suporte no WhatsApp
      </a>
    </div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    _, _cm, _ = st.columns([2, 1, 2])
    with _cm:
        if st.button("← Usar outra conta", key="btn_logout_blq"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.query_params.clear(); st.rerun()

# ═════════════════════════════════════════════
#  LANÇAMENTOS
# ═════════════════════════════════════════════
def inserir_lancamento(uid, desc, valor, parcelas, inicio, final, recorrente):
    try:
        run_query("""INSERT INTO lancamentos
            (usuario_id,descricao,valor_total,parcelas_totais,parcelas_pagas,inicio_pagamento,final_pagamento,recorrente,pago)
            VALUES (%s,%s,%s,%s,0,%s,%s,%s,FALSE)""",
            (uid, desc, float(valor), parcelas, inicio, final or None, 1 if recorrente else 0))
        invalidar_cache_lancamentos()
    except Exception as e: st.error(f"❌ {e}")

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

# ═════════════════════════════════════════════
#  CÁLCULOS
# ═════════════════════════════════════════════
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
    df_a["valor_total"]     = df_a["valor_total"].astype(float)
    df_a["parcelas_totais"] = df_a["parcelas_totais"].astype(int)
    rec = df_a[df_a["recorrente"].astype(int) == 1]["valor_total"].sum()
    par = df_a[df_a["recorrente"].astype(int) == 0]
    return float(rec + (par["valor_total"] / par["parcelas_totais"].replace(0, 1)).sum())

# ═════════════════════════════════════════════
#  VALIDAÇÃO DO TOKEN DE SESSÃO "s" NA URL
#  (somente leitura — run_query já existe aqui)
# ═════════════════════════════════════════════
if st.session_state.usuario_id is None:
    _token_url = st.query_params.get("s", None)
    if _token_url:
        _uid_val = validar_token_sessao(_token_url)
        if _uid_val:
            try:
                _rows_s = run_query("SELECT id,nome FROM usuarios WHERE id=%s", (_uid_val,), fetch=True)
                if _rows_s:
                    st.session_state.usuario_id   = _rows_s[0]["id"]
                    st.session_state.usuario_nome = _rows_s[0]["nome"]
                else:
                    st.query_params.clear()
            except:
                pass
        else:
            st.query_params.clear()

# ═════════════════════════════════════════════
#  TELA DE LOGIN / CADASTRO
# ═════════════════════════════════════════════
if st.session_state.usuario_id is None:

    _lang_map = {"🇧🇷 Português": "PT", "🇺🇸 English": "EN", "🇫🇷 Français": "FR"}
    _, _lc_lang, _ = st.columns([1, 1.6, 1])
    with _lc_lang:
        _sel_login = st.radio(
            "idioma_login", options=list(_lang_map.keys()),
            index=list(_lang_map.values()).index(st.session_state.lang),
            horizontal=True, key="seletor_idioma", label_visibility="collapsed"
        )
        _novo_lang_login = _lang_map[_sel_login]
        if _novo_lang_login != st.session_state.lang:
            st.session_state.lang = _novo_lang_login
            st.rerun()

    t = get_t()
    _, col_center, _ = st.columns([1, 1.6, 1])
    with col_center:
        st.markdown(f"""
        <div class="login-wrap">
            <div class="login-logo">💳</div>
            <div class="login-title">Gastei - {t.get('login_titulo_app','Finanças Premium')}</div>
            <div class="login-sub">{t.get('login_sub_app','Controle de Gastos de Alta Performance')}</div>
        </div>""", unsafe_allow_html=True)

        aba_login, aba_cadastro = st.tabs([
            t.get("aba_entrar", "🔑  Entrar"),
            t.get("aba_criar_conta", "✨  Criar Conta")
        ])

        # ── ABA LOGIN ──────────────────────────────
        with aba_login:
            if st.session_state.reset_step == 0:
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

                # Botão Google OAuth
                _state_g = _secrets.token_hex(16)
                st.session_state.oauth_state = _state_g
                _url_google = google_auth_url(_state_g)
                if _url_google:
                    st.link_button("🔵  Continuar com Google", url=_url_google, use_container_width=True)

                st.markdown("""
                <div style="display:flex;align-items:center;gap:10px;margin:18px 0 12px;">
                  <div style="flex:1;height:1px;background:rgba(255,255,255,0.1);"></div>
                  <span style="color:#4b5563;font-size:12px;font-weight:600;">ou entre com e-mail</span>
                  <div style="flex:1;height:1px;background:rgba(255,255,255,0.1);"></div>
                </div>""", unsafe_allow_html=True)

                email_login = st.text_input(t.get("input_email","E-mail"), key="login_email",
                                            placeholder=t.get("holder_email","seu@email.com"))
                senha_login = st.text_input(t.get("input_senha","Senha"), type="password",
                                            key="login_senha", placeholder="••••••••")
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                if st.button(t.get("btn_entrar_seta","Entrar →"), key="btn_login"):
                    if not email_login or not senha_login:
                        st.error(t.get("err_preencha_dados","Preencha e-mail e senha."))
                    else:
                        resultado = autenticar_usuario(email_login, senha_login)
                        if resultado == "bloqueado":
                            st.error(t.get("err_bloqueado","🛑 Acesso Bloqueado!"))
                        elif resultado:
                            st.session_state.usuario_id   = resultado[0]
                            st.session_state.usuario_nome = resultado[1]
                            st.query_params["s"] = gerar_token_sessao(resultado[0])
                            st.rerun()
                        else:
                            st.error(t.get("err_dados_invalidos","E-mail ou senha incorretos."))

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                st.markdown('<div class="btn-link">', unsafe_allow_html=True)
                if st.button(t.get("link_esqueceu","🔑 Esqueci minha senha"), key="btn_forgot"):
                    st.session_state.reset_step = 1; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                _msg_wa  = t.get("msg_suporte_wa","Olá! Quero verificar o status do meu acesso no app Gastei.")
                _link_wa = f"https://wa.me/{WA_SUPORTE}?text={_msg_wa.replace(' ','%20')}"
                st.markdown(f"""
                <div style='text-align:center;margin-top:8px;'>
                    <a href="{_link_wa}" target="_blank" style="color:#9b8dff;font-size:13px;text-decoration:none;opacity:0.8;">
                        🔒 {t.get('link_suporte','Problemas com o acesso? — Falar com o Suporte')}</a>
                </div>
                <div style='text-align:center;margin-top:8px;'>
                    <a href="https://finatechlab.com/pagina-vendas-gastei/" target="_blank"
                       style="color:#64b5f6;font-size:12px;text-decoration:none;opacity:0.65;">
                        🛒 {t.get('link_vendas','Ainda não tem acesso? Conheça o Gastei →')}</a>
                </div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander(t.get("expander_termos","🛡️ Termos de Uso e Política de Privacidade")):
                    st.write(t.get("texto_termos","Seus dados financeiros são armazenados de forma criptografada e privativa."))

            elif st.session_state.reset_step == 1:
                st.info(t.get("info_reset_email","📧 Informe o e-mail cadastrado. Enviaremos um código de 6 dígitos."))
                email_reset = st.text_input(t.get("input_email_cadastrado","E-mail cadastrado"),
                                            key="reset_email_input", placeholder="seu@email.com")
                col_env, col_vol = st.columns(2)
                with col_env:
                    if st.button(t.get("btn_enviar_codigo","Enviar código →"), key="btn_send_token"):
                        if not email_valido(email_reset): st.error("E-mail inválido.")
                        else:
                            rows = run_query("SELECT id FROM usuarios WHERE email=%s",
                                             (email_reset.strip().lower(),), fetch=True)
                            if not rows: st.error(t.get("err_email_nao_encontrado","E-mail não encontrado."))
                            else:
                                tok = gerar_token_reset(email_reset)
                                if tok and enviar_email_reset(email_reset, tok):
                                    st.session_state.reset_email = email_reset.strip().lower()
                                    st.session_state.reset_step  = 2; st.rerun()
                with col_vol:
                    if st.button("← Voltar", key="btn_back_1"):
                        st.session_state.reset_step = 0; st.rerun()

            elif st.session_state.reset_step == 2:
                st.success(t.get("sucesso_codigo_enviado","✅ Código enviado para **{}**.").format(st.session_state.reset_email))
                codigo = st.text_input(t.get("input_codigo_digitos","Código de 6 dígitos"),
                                       key="reset_token_input", placeholder="123456", max_chars=6)
                nova1  = st.text_input(t.get("input_nova_senha","Nova senha"), type="password",
                                       key="reset_pass1", placeholder="Mínimo 6 caracteres")
                nova2  = st.text_input(t.get("input_confirmar_nova","Confirmar nova senha"),
                                       type="password", key="reset_pass2", placeholder="Repita a senha")
                col_conf, col_vol2 = st.columns(2)
                with col_conf:
                    if st.button(t.get("btn_redefinir_senha","Redefinir senha →"), key="btn_confirm_reset"):
                        erros = []
                        if not codigo.strip(): erros.append(t.get("err_informe_codigo","Informe o código."))
                        if len(nova1) < 6:     erros.append(t.get("err_senha_curta","Mínimo 6 caracteres."))
                        if nova1 != nova2:     erros.append(t.get("err_senhas_diferentes","Senhas não conferem."))
                        if erros:
                            for e in erros: st.error(e)
                        elif not validar_token_reset(st.session_state.reset_email, codigo):
                            st.error(t.get("err_codigo_expirado","Código inválido ou expirado."))
                        else:
                            if trocar_senha(st.session_state.reset_email, nova1):
                                consumir_token_reset(st.session_state.reset_email, codigo)
                                st.success(t.get("sucesso_senha_redefinida","🎉 Senha redefinida! Faça login."))
                                st.session_state.reset_step = 0; st.session_state.reset_email = ""; st.rerun()
                with col_vol2:
                    if st.button("← Voltar", key="btn_back_2"):
                        st.session_state.reset_step = 1; st.rerun()

        # ── ABA CADASTRO ───────────────────────────
        with aba_cadastro:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            nome_cad   = st.text_input(t.get("input_nome","Seu nome"),         key="cad_nome",   placeholder="João Silva")
            email_cad  = st.text_input(t.get("input_email","E-mail"),           key="cad_email",  placeholder="O mesmo e-mail usado na compra")
            tel_cad    = st.text_input(t.get("input_telefone","WhatsApp / Telefone"), key="cad_tel", placeholder="(67) 99999-9999")
            senha_cad  = st.text_input(t.get("input_senha","Senha"),     type="password", key="cad_senha",  placeholder="Mínimo 6 caracteres")
            senha_cad2 = st.text_input(t.get("input_confirmar_senha","Confirmar senha"), type="password", key="cad_senha2", placeholder="Repita a senha")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(t.get("btn_criar_conta","Criar minha conta →"), key="btn_cadastro"):
                erros = []
                if not all([nome_cad, email_cad, tel_cad, senha_cad, senha_cad2]):
                    erros.append(t.get("err_campos_vazios","Preencha todos os campos."))
                elif not email_valido(email_cad):   erros.append("E-mail inválido.")
                elif not telefone_valido(tel_cad):  erros.append(t.get("err_tel_invalido","Telefone inválido."))
                elif len(senha_cad) < 6:            erros.append(t.get("err_senha_curta","Mínimo 6 caracteres."))
                elif senha_cad != senha_cad2:       erros.append(t.get("err_senhas_diferentes","Senhas não conferem."))
                if erros:
                    for e in erros: st.error(e)
                else:
                    ok, msg = criar_usuario(nome_cad, email_cad, senha_cad, tel_cad)
                    if ok: st.success(t.get("sucesso_conta_criada","✅ Conta criada! Faça login na aba ao lado."))
                    else:  st.error(msg)
            st.markdown(f"""<div style='text-align:center;margin-top:16px;'>
                <a href="https://finatechlab.com/pagina-vendas-gastei/" target="_blank"
                   style="color:#64b5f6;font-size:12px;text-decoration:none;opacity:0.65;">
                    🛒 {t.get('link_vendas_planos','Ainda não comprou? Conheça os planos →')}</a></div>""",
                    print("Ei, sabia que pode acessar gratuítamente por 7 dias se voltar e entrar com a sua conta do Google?")
                unsafe_allow_html=True)

    st.stop()

# ═════════════════════════════════════════════
#  APP PRINCIPAL (só chega aqui se logado)
# ═════════════════════════════════════════════
uid = st.session_state.usuario_id
st.query_params["s"] = gerar_token_sessao(uid)

# Job de e-mails diário (silencioso, 1x/dia por instância)
_job_diario(0)

# Carrega salário uma vez por sessão
if not st.session_state._salario_carregado:
    st.session_state.salario = buscar_salario_db(uid)
    st.session_state._salario_carregado = True

# ── Verifica trial e bloqueia se expirado ────
_trial = verificar_trial(uid)
if not _trial["acesso"]:
    renderizar_tela_bloqueio(st.session_state.get("usuario_nome", ""))
    st.stop()

# ── Sidebar ──────────────────────────────────
with st.sidebar:
    t = get_t()
    st.markdown(f"### {t.get('idioma_label','🌐 Idioma')}")
    _smap = {"🇧🇷 Português": "PT", "🇺🇸 English": "EN", "🇫🇷 Français": "FR"}
    _ssel = st.selectbox(
        t.get("idioma_label","Idioma"),
        options=list(_smap.keys()),
        index=list(_smap.values()).index(st.session_state.lang),
        key="seletor_idioma", label_visibility="collapsed"
    )
    if _smap[_ssel] != st.session_state.lang:
        st.session_state.lang = _smap[_ssel]; st.rerun()
    t = get_t()

    st.markdown("---")
    st.markdown(f"### {t.get('salario_titulo','💰 Meu Salário Mensal')}")
    _sal_sb = st.number_input(
        t.get("salario_input","Salário"), min_value=0.0, step=100.0, format="%.2f",
        value=float(st.session_state.salario),
        key="input_salario_sidebar", label_visibility="collapsed"
    )
    if st.button(t.get("salario_btn","💾 Salvar Salário"), key="btn_sal_sidebar"):
        if salvar_salario_db(uid, _sal_sb):
            st.success(t.get("salario_salvo","✅ Salário atualizado!"))

t = get_t()

# ── Header ───────────────────────────────────
col_titulo, col_usuario, col_pref, col_logout = st.columns([5, 2, 0.6, 0.8])
with col_titulo:
    st.markdown("# GASTEI ⚡")
    st.markdown(f"<p style='color:#6b7280;margin-top:-12px;margin-bottom:28px;'>{t.get('app_subtitle','')}</p>",
                unsafe_allow_html=True)
with col_usuario:
    st.markdown(f"<div style='text-align:right;padding-top:18px;font-size:13px;color:#9ca3af;'>"
                f"{t.get('ola','Olá')}, <strong style='color:#c4b5fd'>{st.session_state.usuario_nome}</strong> 👋</div>",
                unsafe_allow_html=True)
with col_pref:
    st.markdown("<div style='padding-top:14px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="pref-btn">', unsafe_allow_html=True)
    if st.button("⚙️", key="btn_pref_toggle"):
        st.session_state.pref_aberto = not st.session_state.pref_aberto; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with col_logout:
    st.markdown("<div style='padding-top:14px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button(t.get("sair","🚪"), key="btn_logout"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.query_params.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Banner de aviso de trial (≤ 2 dias) ──────
if _trial["status"] == "trial" and _trial.get("dias_restantes", 999) <= 2:
    _dr = _trial["dias_restantes"]
    st.markdown(f"""
    <div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.4);
                border-radius:10px;padding:10px 18px;margin-bottom:16px;
                display:flex;align-items:center;justify-content:space-between;gap:12px;">
      <span style="color:#fde047;font-size:13px;font-weight:700;">
        {t.get('trial_aviso','⏰ Seu teste grátis termina em **{} dia(s)**!').format(_dr)}
      </span>
      <a href="{KIWIFY_URL}" target="_blank"
         style="background:linear-gradient(135deg,#6a3de8,#9b8dff);color:#fff;
                text-decoration:none;padding:7px 18px;border-radius:8px;
                font-size:12px;font-weight:700;white-space:nowrap;">
        {t.get('trial_assinar','🔓 Assinar agora')}
      </a>
    </div>""", unsafe_allow_html=True)

# ── Painel ⚙️ ────────────────────────────────
if st.session_state.pref_aberto:
    st.markdown('<div class="pref-panel">', unsafe_allow_html=True)
    _pc1, _pc2, _pc3 = st.columns([1.2, 1.5, 0.6])
    with _pc1:
        st.markdown(f"<p style='color:#9b8dff;font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;'>{t.get('idioma_label','🌐 Idioma')}</p>",
                    unsafe_allow_html=True)
        _pmap = {"🇧🇷 Português": "PT", "🇺🇸 English": "EN", "🇫🇷 Français": "FR"}
        _psel = st.radio("lang_panel", options=list(_pmap.keys()),
                         index=list(_pmap.values()).index(st.session_state.lang),
                         key="lang_radio_panel", label_visibility="collapsed")
        if _pmap[_psel] != st.session_state.lang:
            st.session_state.lang = _pmap[_psel]; st.rerun()
        t = get_t()
    with _pc2:
        st.markdown(f"<p style='color:#9b8dff;font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;'>💰 {t.get('salario_titulo','Salário')}</p>",
                    unsafe_allow_html=True)
        _sal_p = st.number_input(
            t.get("salario_input","Salário"), min_value=0.0, step=100.0, format="%.2f",
            value=float(st.session_state.salario), key="sal_panel", label_visibility="collapsed"
        )
        if st.button(t.get("salario_btn","💾 Salvar Salário"), key="btn_sal_panel"):
            if salvar_salario_db(uid, _sal_p):
                st.success(t.get("salario_salvo","✅ Salário atualizado!"))
    with _pc3:
        st.markdown("<div style='padding-top:26px'></div>", unsafe_allow_html=True)
        if st.button(f"✕ {t.get('pref_fechar','Fechar')}", key="btn_pref_close"):
            st.session_state.pref_aberto = False; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Abas ─────────────────────────────────────
aba_principal, aba_feedback = st.tabs([t.get("aba_gastos","📊 Meus Gastos"), t.get("aba_feedback","💬 Feedbacks")])

# ══════════════════════════════
# ABA 1 — GASTOS
# ══════════════════════════════
with aba_principal:
    df_all       = carregar_lancamentos(uid)
    total_saidas = df_all["valor_total"].astype(float).sum() if not df_all.empty else 0.0
    gasto_mensal = calcular_gasto_mensal(df_all) if not df_all.empty else 0.0
    salario      = float(st.session_state.salario)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""<div class="total-card">
            <div><div class="total-label">{t.get('total_saidas','Total de Saídas')}</div>
                 <div class="total-value">R$ {total_saidas:,.2f}</div></div>
            <div class="total-icon">📊</div></div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="parcela-card">
            <div><div class="parcela-label">{t.get('comprometido_mes','Comprometido Este Mês')}</div>
                 <div class="parcela-value">R$ {gasto_mensal:,.2f}</div></div>
            <div style="font-size:48px;opacity:0.4;">📅</div></div>""", unsafe_allow_html=True)
    with col_c:
        if salario > 0:
            pct = (gasto_mensal / salario) * 100
            cls = "salario-card alerta" if pct >= 70 else "salario-card"
            ico = "🚨" if pct >= 70 else "💰"
            st.markdown(f"""<div class="{cls}">
                <div><div class="salario-label">{t.get('salario_comprometido','Salário Comprometido')}</div>
                     <div class="salario-value">{pct:.1f}%</div>
                     <div style="font-size:11px;color:#6b7280;margin-top:4px;">{t.get('pct_label','% do salário comprometido no próximo mês')}</div></div>
                <div style="font-size:48px;opacity:0.5;">{ico}</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="salario-card" style="opacity:0.55;">
                <div><div class="salario-label">{t.get('salario_comprometido','Salário Comprometido')}</div>
                     <div class="salario-value">--%</div></div>
                <div style="font-size:48px;opacity:0.3;">💰</div></div>""", unsafe_allow_html=True)
            st.caption(t.get("salario_zero_aviso","⚠️ Cadastre seu salário no painel ⚙️."))

    # ── Formulário novo lançamento ─────────────
    st.markdown(f"### {t.get('novo_lancamento','➕ Novo Lançamento')}")
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    with st.form("form_novo_lancamento", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            descricao = st.text_input(t.get("o_que_comprou","O que comprou / Pagou"),
                                      placeholder=t.get("placeholder_desc","Ex: iPhone 16, Aluguel..."))
        with col2:
            valor_total = st.number_input(t.get("valor_total","Valor Total (R$)"),
                                          min_value=0.0, step=0.01, format="%.2f", value=0.0)
        is_recorrente = st.checkbox(t.get("conta_fixa","🔁 Conta Fixa / Recorrente"))

        if is_recorrente:
            col4, _ = st.columns([1, 2])
            with col4:
                inicio_pagamento = st.date_input(t.get("dia_vencimento","Dia de Vencimento"),
                                                 value=date.today(), format="DD/MM/YYYY")
            parcelas_totais = 0; final_pagamento = None
            if descricao and valor_total > 0:
                prox_rec = calcular_proxima_recorrente(inicio_pagamento)
                st.markdown("<hr>", unsafe_allow_html=True)
                pc1, pc2, pc3 = st.columns(3)
                with pc1: st.markdown(f"{t.get('valor_mensal','**Valor mensal:**')} `R$ {valor_total:,.2f}`")
                with pc2: st.markdown(f"{t.get('tipo_recorrente','**Tipo:**')} `🔁 Recorrente`")
                with pc3: st.markdown(f"{t.get('prox_vencimento','**Próximo vencimento:**')} `{prox_rec.strftime('%d/%m/%Y')}`")
        else:
            col3, col4 = st.columns(2)
            with col3:
                parcelas_totais = st.number_input(t.get("num_parcelas","Número de Parcelas"),
                                                  min_value=1, max_value=360, step=1, value=1)
            with col4:
                inicio_pagamento = st.date_input(t.get("data_primeiro_venc","Data do Primeiro Vencimento"),
                                                 value=date.today(), format="DD/MM/YYYY")
            final_pagamento = None
            if descricao and valor_total > 0:
                val_p = calcular_valor_parcela(valor_total, parcelas_totais)
                st.markdown("<hr>", unsafe_allow_html=True)
                pc1, pc2, pc3 = st.columns(3)
                with pc1: st.markdown(f"{t.get('valor_parcela','**Valor por parcela:**')} `R$ {val_p:.2f}`")
                with pc2: st.markdown(f"{t.get('parcelas_restantes','**Parcelas restantes:**')} `{parcelas_totais}x`")
                with pc3: st.markdown(f"{t.get('venc_parcela1','**Vencimento da Parcela 1:**')} `{inicio_pagamento.strftime('%d/%m/%Y')}`")

        if valor_total > 0 and salario > 0:
            parc_sim    = parcelas_totais if (parcelas_totais and not is_recorrente) else 1
            mensal_novo = valor_total / parc_sim if parc_sim > 0 else valor_total
            total_sim   = gasto_mensal + mensal_novo
            pct_sim     = (total_sim / salario) * 100
            st.markdown(t.get("sim_info","💡 Com este gasto: **R$ {:.2f}/mês** comprometido ({:.1f}% do salário).").format(total_sim, pct_sim))
            if pct_sim > 70:
                st.markdown(f"""<div class="alerta-simulacao">
                    <span class="pct-destaque">⚠️ {pct_sim:.1f}%</span>
                    {t.get("sim_alerta","").format(pct_sim)}
                </div>""", unsafe_allow_html=True)
            else:
                st.success(t.get("sim_ok","✅ Dentro do limite saudável."))
        elif valor_total > 0 and salario == 0:
            st.caption(t.get("salario_zero_aviso","⚠️ Cadastre seu salário no painel ⚙️."))

        col_btn, _ = st.columns([1, 3])
        with col_btn:
            submitted = st.form_submit_button(t.get("salvar_lancamento","💾 Salvar Lançamento"))
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        erros = []
        if not descricao.strip(): erros.append(t.get("err_descricao","⚠️ Preencha a descrição."))
        if valor_total <= 0:      erros.append(t.get("err_valor","⚠️ O valor deve ser maior que zero."))
        if erros:
            for e in erros: st.error(e)
        else:
            inserir_lancamento(uid, descricao.strip(), valor_total, parcelas_totais,
                               inicio_pagamento, final_pagamento, is_recorrente)
            st.success(t.get("salvo_sucesso","✅ **{}** salvo com sucesso!").format(descricao))
            st.rerun()

    # ── Histórico ──────────────────────────────
    st.markdown(t.get("historico","### 📋 Histórico de Vencimentos"))
    df = df_all.copy()
    if df.empty:
        st.markdown(f"<div style='text-align:center;padding:60px 20px;color:#4b5563;'><div style='font-size:48px;'>📭</div>{t.get('nenhum_lancamento','Nenhum lançamento ainda.')}</div>",
                    unsafe_allow_html=True)
    else:
        busca = st.text_input(t.get("filtrar","🔍 Filtrar por descrição"),
                              placeholder=t.get("placeholder_busca","Digite para buscar..."), key="busca")
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
            if v < hoje:                      return (0, v)
            if v == hoje:                     return (1, v)
            if v <= hoje + timedelta(days=3): return (2, v)
            return (3, v)
        df["_sort"] = df.apply(_grp, axis=1)
        df = df.sort_values("_sort").drop(columns=["_pago","_rec","_venc","_sort"])

        _ativos = ~df["pago"].astype(bool)
        _vc = df.apply(lambda r: calcular_proxima_recorrente(to_date(r["inicio_pagamento"]))
                       if int(r["recorrente"]) == 1 else to_date(r["inicio_pagamento"]), axis=1)
        n_atr = int((_ativos & (_vc < hoje)).sum())
        n_hj  = int((_ativos & (_vc == hoje)).sum())
        n_brv = int((_ativos & (_vc > hoje) & (_vc <= hoje + timedelta(days=3))).sum())

        if n_atr:
            pl = t.get("conta_atrasada_s","conta atrasada") if n_atr == 1 else t.get("conta_atrasada_p","contas atrasadas")
            st.markdown(f"""<div class="alerta-banner">🚨 <span class="count">{n_atr}</span> {pl} — {t.get('alerta_atrasada_sufixo','quite agora!')}</div>""",
                        unsafe_allow_html=True)
        if n_hj:
            pl = t.get("conta_hoje_s","conta vence hoje") if n_hj == 1 else t.get("conta_hoje_p","contas vencem hoje")
            st.markdown(f"""<div class="hoje-banner">🔥 <span style="background:#f97316;color:#fff;border-radius:999px;padding:1px 8px;font-weight:800;">{n_hj}</span> {pl} — {t.get('alerta_hoje_sufixo','não deixe passar!')}</div>""",
                        unsafe_allow_html=True)
        if n_brv and not n_atr and not n_hj:
            pl = t.get("conta_breve_s","conta vence") if n_brv == 1 else t.get("conta_breve_p","contas vencem")
            st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;background:rgba(234,179,8,0.09);border:1px solid rgba(234,179,8,0.3);border-radius:10px;padding:7px 14px;font-size:11px;font-weight:700;color:#fde047;margin-bottom:8px;">
                ⚡ {n_brv} {pl} — {t.get('alerta_breve_sufixo','nos próximos 3 dias')}</div>""", unsafe_allow_html=True)

        st.markdown(f"""<div style="display:grid;grid-template-columns:2.2fr 1fr 1fr 1fr 0.8fr;
            padding:10px 24px;font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">
            <div>{t.get('col_descricao','Descrição')}</div><div>{t.get('col_valor','Valor')}</div>
            <div>{t.get('col_vencimento','Próximo Vencimento')}</div><div>{t.get('col_situacao','Situação')}</div>
            <div style="text-align:center">{t.get('col_acoes','Ações')}</div></div>""", unsafe_allow_html=True)

        for _, row in df.iterrows():
            id_        = row["id"]
            desc       = row["descricao"]
            v_tot      = float(row["valor_total"])
            parc_tot   = int(row["parcelas_totais"])
            parc_pagas = int(row.get("parcelas_pagas", 0))
            parc_rest  = max(0, parc_tot - parc_pagas)
            eh_fixa    = int(row["recorrente"]) == 1
            pago_fim   = bool(row["pago"])
            val_exibir = v_tot if eh_fixa else calcular_valor_parcela(v_tot, parc_tot)
            venc_data  = calcular_proxima_recorrente(to_date(row["inicio_pagamento"])) if eh_fixa else to_date(row["inicio_pagamento"])

            col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns([2.2, 1, 1, 1, 0.8])
            with col_r1:
                sub = f"{t.get('total_label','Total:')} R$ {v_tot:,.2f} · {t.get('inicio_label','Início:')} {to_date(row['inicio_pagamento']).strftime('%d/%m/%Y')}" if not eh_fixa else t.get("conta_mensal_fixa","Conta Mensal Fixa")
                st.markdown(f"<div style='padding-top:12px'><strong style='color:#fff;font-size:15px;'>{desc}</strong><br><span style='color:#6b7280;font-size:11px;'>{sub}</span></div>", unsafe_allow_html=True)
            with col_r2:
                lbl = t.get("label_mensal","mensal") if eh_fixa else t.get("label_parcela","por parcela")
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
                    st.markdown(f"<div style='padding-top:18px;color:#4b5563;font-size:13px;'>{t.get('divida_encerrada','Dívida Encerrada')}</div>", unsafe_allow_html=True)
                elif eh_fixa:
                    st.markdown(f"<div style='padding-top:18px'><span class='badge-fixa'>{t.get('recorrente_inf','Recorrente ∞')}</span></div>", unsafe_allow_html=True)
                else:
                    try:
                        mf = max(0, parc_rest - 1); du = venc_data.day
                        mu = (venc_data.month + mf - 1) % 12 + 1
                        au = venc_data.year + ((venc_data.month + mf - 1) // 12)
                        try:    dup = date(au, mu, du)
                        except: dup = date(au, mu, calendar.monthrange(au, mu)[1])
                        txt_u = dup.strftime('%d/%m/%Y')
                    except: txt_u = "--/--/----"
                    falta = max(0.0, v_tot - (parc_pagas * val_exibir))
                    st.markdown(f"""<div style='padding-top:4px'>
                        <span class='badge-parcelas'>{parc_rest}x {t.get('x_restantes','x restantes')}</span><br>
                        <span style='color:#6b7280;font-size:11px;display:block;margin-top:2px;'>{t.get('ultima_parcela','Última parcela:')} <strong style='color:#90cdf4;'>{txt_u}</strong></span>
                        <span style='color:#6b7280;font-size:10px;display:block;'>{t.get('falta_pagar','Falta pagar:')} R$ {falta:,.2f}</span>
                    </div>""", unsafe_allow_html=True)
            with col_r5:
                if not pago_fim:
                    st.markdown('<div class="btn-pagar">', unsafe_allow_html=True)
                    if st.button(t.get("btn_pagar","💸 Pagar Parcela"), key=f"btn_p_{id_}"):
                        if eh_fixa: avancar_parcela_recorrente(id_, row["inicio_pagamento"])
                        else: avancar_parcela_parcelada_excel(id_, row["inicio_pagamento"], parc_tot, parc_pagas)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<div class="btn-quitar">', unsafe_allow_html=True)
                    if st.button(t.get("btn_quitar","🏁 Quitar Tudo"), key=f"btn_q_{id_}"):
                        marcar_pago(id_); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    if st.button(t.get("btn_excluir","🗑️ Excluir"), key=f"btn_del_{id_}"):
                        excluir_lancamento(id_); st.rerun()

        st.markdown(f"<br><br><center style='color:#4b5563;font-size:12px;'>{t.get('rodape','© 2026 Gastei App.')}</center>", unsafe_allow_html=True)

# ══════════════════════════════
# ABA 2 — FEEDBACK
# ══════════════════════════════
with aba_feedback:
    t = get_t()
    st.markdown(t.get("feedback_titulo","### 💬 Canal Direct de Sugestões & Feedbacks"))
    st.markdown(f"<p style='color:#9ca3af;margin-top:-10px;'>{t.get('feedback_sub','')}</p>", unsafe_allow_html=True)
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    mensagem_fb = st.text_area(t.get("feedback_label","Sua mensagem"),
                               placeholder=t.get("feedback_placeholder","Ex: Seria massa ver um gráfico..."),
                               height=160, key="feedback_texto")
    col_fb, _ = st.columns([1, 3])
    with col_fb:
        if st.button(t.get("feedback_btn","📨 Enviar Meu Feedback"), key="btn_feedback"):
            if not mensagem_fb.strip():        st.error(t.get("feedback_vazio","⚠️ Escreva algo antes de clicar em enviar."))
            elif len(mensagem_fb.strip()) < 8: st.error(t.get("feedback_curto","⚠️ Detalhe um pouquinho mais."))
            else:
                if inserir_feedback(uid, mensagem_fb):
                    st.success(t.get("feedback_ok","✅ Feedback enviado! Muito obrigado 🙏")); st.balloons()
    st.markdown('</div>', unsafe_allow_html=True)
