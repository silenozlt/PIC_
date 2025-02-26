import os
from dotenv import load_dotenv
import mysql.connector
import pandas as pd
import plotly.express as px
import streamlit as st

# Carregar variáveis do .env
load_dotenv()

# Configuração do banco
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE"),
    "port": int(os.getenv("DB_PORT", 3306))
}

if not all(DB_CONFIG.values()):
    st.error("Erro: Algumas variáveis de ambiente não foram carregadas corretamente.")
    st.stop()

# Função para executar queries
def run_query(query, commit=False):
    """Executa consultas SQL no MySQL e retorna um DataFrame se for um SELECT."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(query)

    if commit:
        conn.commit()
        cursor.close()
        conn.close()
        return None

    # Se for um SELECT, retorna os resultados
    if query.strip().upper().startswith("SELECT"):
        result = cursor.fetchall()
        df = pd.DataFrame(result)
        cursor.close()
        conn.close()
        return df

    cursor.close()
    conn.close()
    return None

# Layout do dashboard
st.set_page_config(page_title="Dashboard de Sócios", layout="wide")
st.title("📊 Dashboard de Sócios e Consumo")

# Abas para separar os relatórios
tab1, tab2, tab3, tab4 = st.tabs(["📜 Convites", "🏠 Sócios por Bairro", "💰 Consumo", "📊 Consumo por Bairro"])

# 1️⃣ Convites Emitidos
with tab1:
    st.subheader("Convites Emitidos e Novos Sócios")
    quantidade_convites = st.selectbox("Selecione a quantidade de registros a ser exibida:", [10, 20, 30, 50, 100], key="convites")
    query_convites = f"""
    SELECT 
        id,
        SUM(CASE WHEN TIPO_CONVITE = 'GRATUITO' THEN 1 ELSE 0 END) AS convite_gratuito,
        SUM(CASE WHEN TIPO_CONVITE = 'PAGO' THEN 1 ELSE 0 END) AS convite_pago,
        COUNT(*) AS total_convites,
        SUM(CASE WHEN tornou_socio = 'SIM' THEN 1 ELSE 0 END) AS novos_socios
    FROM convites
    GROUP BY id
    ORDER BY novos_socios DESC, total_convites DESC
    LIMIT {quantidade_convites};
    """
    df_convites = run_query(query_convites)
    st.dataframe(df_convites)

# 2️⃣ Sócios por Bairro
with tab2:
    st.subheader("Sócios por Bairro")
    quantidade_socios = st.selectbox("Selecione a quantidade de bairros a ser exibida:", [10, 20, 30, 50, 100], key="socios")
    query_socios = f"""
    SELECT bairro, COUNT(*) AS total_socios
    FROM socios
    WHERE bairro != ''
    GROUP BY bairro
    ORDER BY total_socios DESC
    LIMIT {quantidade_socios};
    """
    df_socios = run_query(query_socios)
    st.dataframe(df_socios)

# 3️⃣ Maiores Consumos
with tab3:
    st.subheader("Maiores Consumos por Cota")
    quantidade_consumo = st.selectbox("Selecione a quantidade de registros a ser exibida:", [10, 20, 30, 50, 100], key="consumo")
    query_consumo = f"""
    SELECT 
        s.cota,
        s.bairro,
        s.estado_civil,
        COUNT(DISTINCT CASE WHEN s.tipo_socio != 'TITULAR' AND s.parentesco NOT IN ('Filho', 'Filha') THEN s.id END) AS qtd_dependentes,
        s.ocupacao,
        SUM(c.total) AS total_consumo
    FROM socios s
    LEFT JOIN consumo c ON (s.id = c.id)
    GROUP BY s.cota
    ORDER BY total_consumo DESC
    LIMIT {quantidade_consumo};
    """
    df_consumo = run_query(query_consumo)
    st.dataframe(df_consumo)

# 4️⃣ Consumo por Bairro
with tab4:
    st.subheader("Consumo por Bairro")

    # 🔄 Apagar e recriar a tabela x_bairro
    run_query("DROP TABLE IF EXISTS x_bairro;", commit=True)
    run_query("""
    CREATE TABLE x_bairro AS
    SELECT 
        s.cota,
        s.bairro,
        s.estado_civil,
        COUNT(DISTINCT CASE WHEN s.tipo_socio != 'TITULAR' AND s.parentesco NOT IN ('Filho', 'Filha') THEN s.id END) AS qtd_dependentes,
        s.ocupacao,
        SUM(c.total) AS total_consumo
    FROM socios s
    LEFT JOIN consumo c ON (s.id = c.id)
    GROUP BY s.bairro
    ORDER BY total_consumo DESC;
    """, commit=True)

    # 📌 Seleção da quantidade de bairros a exibir
    quantidade_bairros = st.selectbox("Selecione a quantidade de bairros a ser exibida:", [10, 20, 30, 50, 100], key="bairros")

    # 📊 Consulta final para exibição
    query_consumo_bairro = f"""
    SELECT
        bairro, 
        SUM(REPLACE(total_consumo,',','.')) AS consumo_bairro 
    FROM 
        x_bairro 
    GROUP BY
        bairro 
    HAVING consumo_bairro > 0
    ORDER BY consumo_bairro DESC
    LIMIT {quantidade_bairros};
    """

    df_consumo_bairro = run_query(query_consumo_bairro)

    st.dataframe(df_consumo_bairro)

    if not df_consumo_bairro.empty:
        fig = px.pie(df_consumo_bairro, names="bairro", values="consumo_bairro", title="Consumo por Bairro")
        st.plotly_chart(fig)
    else:
        st.warning("Nenhum consumo registrado para exibição.")
