import os
from dotenv import load_dotenv
import mysql.connector
import pandas as pd
import plotly.express as px
import streamlit as st

# Carregar variáveis do .env
load_dotenv()

# Verificar se as variáveis de ambiente foram carregadas corretamente
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
def run_query(query):
    conn = mysql.connector.connect(**DB_CONFIG)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Layout do dashboard
st.set_page_config(page_title="Dashboard de Sócios", layout="wide")

st.title("📊 Dashboard de Sócios e Consumo")

# Abas para separar os relatórios
tab1, tab2, tab3 = st.tabs(["📜 Convites", "🏠 Sócios por Bairro", "💰 Consumo"])

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
    fig = px.bar(df_convites, x="id", y=["convite_gratuito", "convite_pago"], title=f"Convites por ID (Top {quantidade_convites})")
    st.plotly_chart(fig)

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
    df_socios['total_socios'] = df_socios['total_socios'].apply(lambda x: int(x))
    st.dataframe(df_socios)
    fig = px.bar(df_socios, x="bairro", y="total_socios", title=f"Quantidade de Sócios por Bairro (Top {quantidade_socios})")
    st.plotly_chart(fig)

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
    fig = px.bar(df_consumo, x="cota", y="total_consumo", title=f"Top {quantidade_consumo} Maiores Consumos")
    st.plotly_chart(fig)
