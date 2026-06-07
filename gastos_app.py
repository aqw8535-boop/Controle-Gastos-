import os
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel
import psycopg2
from datetime import date, timedelta

app = FastAPI(title="Webhook Kiwify - Gastei App")

# ─────────────────────────────────────────────
# CONF DO BANCO (Substitua ou puxe das variáveis de ambiente)
# ─────────────────────────────────────────────
# Como você usa st.secrets no Streamlit, aqui na API o ideal é definir
# como variáveis de ambiente no servidor onde for hospedar (Render, Railway, etc.)
DB_HOST = os.getenv("DB_HOST", "seu-projeto-supabase.supabase.co")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "sua-senha-do-banco")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, 
        password=DB_PASS, port=DB_PORT, sslmode="require"
    )

# ─────────────────────────────────────────────
# MODELOS DE DADOS (O que a Kiwify envia no POST)
# ─────────────────────────────────────────────
class ProductModel(BaseModel):
    product_id: str
    product_name: str

class CustomerModel(BaseModel):
    email: str
    name: str

class KiwifyWebhook(BaseModel):
    status: str  # approved, refunded, chargedback
    Product: ProductModel
    Customer: CustomerModel

# ─────────────────────────────────────────────
# ENDPOINT DO WEBHOOK
# ─────────────────────────────────────────────
@app.post("/webhook-kiwify", status_code=status.HTTP_200_OK)
async def receber_webhook(data: KiwifyWebhook, request: Request):
    # Dica: Se quiser validar o token de segurança que a Kiwify envia no cabeçalho:
    # token_header = request.headers.get("X-Kiwify-Signature")
    
    email = data.Customer.email.strip().lower()
    status_venda = data.status.strip().lower()
    product_id = data.Product.product_id.strip()
    
    # IDs dos seus produtos na Kiwify (Troque pelos números reais do seu painel)
    ID_PLANO_ANUAL = "123456"      
    ID_PLANO_VITALICIO = "789101"  

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 🟢 CASO 1: VENDA APROVADA
        if status_venda == "approved":
            if product_id == ID_PLANO_ANUAL:
                tipo_licenca = "assinatura"
                # Define a expiração para 1 ano a partir de hoje
                expira_em = date.today() + timedelta(days=365)
            elif product_id == ID_PLANO_VITALICIO:
                tipo_licenca = "vitalicio"
                expira_em = None
            else:
                raise HTTPException(status_code=400, detail="ID de produto não reconhecido.")

            # Insere ou atualiza o Paywall (tabela 'licencas_ativas' do seu init_db)
            query = """
                INSERT INTO licencas_ativas (email, tipo_licenca, expira_em, criado_em)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (email) 
                DO UPDATE SET tipo_licenca = EXCLUDED.tipo_licenca, 
                              expira_em = EXCLUDED.expira_em;
            """
            cur.execute(query, (email, tipo_licenca, expira_em))
            conn.commit()
            return {"status": "sucesso", "mensagem": f"Licença {tipo_licenca} liberada para {email}"}

        # 🔴 CASO 2: REEMBOLSO OU CHARGEBACK (BLOQUEIO)
        elif status_venda in ["refunded", "chargedback"]:
            # Deleta ou atualiza para expirado na tabela licencas_ativas
            query = "DELETE FROM licencas_ativas WHERE email = %s;"
            cur.execute(query, (email,))
            conn.commit()
            return {"status": "sucesso", "mensagem": f"Acesso removido para o e-mail: {email}"}
            
        else:
            return {"status": "ignorado", "mensagem": f"Status {status_venda} não requer ação."}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {str(e)}")
    finally:
        cur.close()
        conn.close()
