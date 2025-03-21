import os
from dotenv import load_dotenv
import mysql.connector
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import numpy as np

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

def run_query(query, commit=False):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query)
        if query.strip().lower().startswith("select"):
            result = cursor.fetchall()
            conn.close()
            if result:
                return pd.DataFrame(result)
            else:
                return pd.DataFrame()  # Retorna DataFrame vazio em vez de None
        if commit:
            conn.commit()
        return None
    finally:
        conn.close()

# Layout do dashboard
st.set_page_config(page_title="Dashboard de Sócios", layout="wide")

st.title("📊 Dashboard de Sócios e Consumo")

# Abas para separar os relatórios
tab1, tab5, tab2, tab3, tab4, tab6 = st.tabs(["📜 Convites", "🏠 Sócios por Cidade", "🏠 Sócios por Bairro", "💰 Consumo", "📊 Consumo por Bairro", "🔍 Clusters de Perfil"])

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
        SUM(c.total) AS total_consumo,
        COUNT(DISTINCT s.id) AS qtd_socios
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
        SUM(REPLACE(total_consumo,',','.')) AS consumo_bairro,
        SUM(total_consumo) / (qtd_socios) AS ticket_medio
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

    # Gráfico com ticket médio
    fig = px.bar(df_consumo_bairro, x="bairro", y=["consumo_bairro", "ticket_medio"], title=f"Consumo por Bairro (Top {quantidade_bairros})")
    st.plotly_chart(fig)
    
    if not df_consumo_bairro.empty:
        fig = px.pie(df_consumo_bairro, names="bairro", values="consumo_bairro", title="Consumo por Bairro")
        st.plotly_chart(fig)
    else:
        st.warning("Nenhum consumo registrado para exibição.")


# 2️⃣ Sócios por Cidade
with tab5:
    st.subheader("Sócios por Cidade")
    quantidade_socios_city = st.selectbox("Selecione a quantidade de cidades a ser exibida:", [10, 20, 30, 50, 100], key="cidade")
    query_socios_city = f"""
    SELECT Cidade, COUNT(*) AS total_socios
    FROM socios
    WHERE cidade != ''
    GROUP BY cidade
    ORDER BY total_socios DESC
    LIMIT {quantidade_socios_city};
    """
    df_socios_city = run_query(query_socios_city)
    st.dataframe(df_socios_city)

    # Ajuste no gráfico para usar a coluna "Cidade"
    fig = px.bar(df_socios_city, x="Cidade", y="total_socios", title=f"Quantidade de Sócios por Cidade (Top {quantidade_socios_city})")
    st.plotly_chart(fig)
with tab6:
    st.subheader("Análise de Perfil por Bairro")

    query_perfil_bairros = """
    SELECT 
        cidade,
        bairro,
        COUNT(DISTINCT cota) AS total_familias,
        AVG(idade) AS idade_media,
        SUM(CASE WHEN parentesco = 'Filho' OR parentesco = 'Filha' THEN 1 ELSE 0 END) / COUNT(DISTINCT cota) AS media_filhos_por_familia,  -- Média de filhos por família
        COUNT(*) AS total_socios,
        -- Perfil familiar dominante
        (SELECT parentesco 
         FROM socios s2
         WHERE s2.bairro = s1.bairro
         GROUP BY parentesco
         ORDER BY COUNT(*) DESC
         LIMIT 1) AS perfil_familiar_dominante
    FROM socios s1
    WHERE bairro IS NOT NULL AND bairro != ''
    GROUP BY bairro
    ORDER BY total_socios DESC
    ;
    """
    
    df_perfil = run_query(query_perfil_bairros)
    
    if df_perfil is None or df_perfil.empty:
        st.warning("Não há dados suficientes para análise.")
    else:
        # Arredondar valores após consulta
        df_perfil['idade_media'] = df_perfil['idade_media'].round(2)
        df_perfil['media_filhos_por_familia'] = df_perfil['media_filhos_por_familia'].round(2)

        st.dataframe(df_perfil)
        
        # Prepara os dados para clustering
        df_cluster = df_perfil[['total_socios', 'total_familias', 'idade_media', 'media_filhos_por_familia']]
        
        # Normalização (opcional, mas recomendado para KMeans)
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(df_cluster)
        
        # Aplicar KMeans para clusterização
        kmeans = KMeans(n_clusters=3, random_state=42)  # Definir o número de clusters
        df_perfil['cluster'] = kmeans.fit_predict(df_scaled)
        
        # Exibir resultados
        df_perfil["media_gasto_familia"] = df_perfil["total_socios"] / df_perfil["total_familias"]
        df_perfil["media_gasto_familia"].fillna(0, inplace=True)  # Evita divisão por zero
        
        # Gráfico de dispersão para visualizar os bairros em cada cluster
        fig = px.scatter(df_perfil, 
                         x="total_socios", 
                         y="media_filhos_por_familia", 
                         color="cluster",  # A cor do ponto indica o cluster
                         title="Distribuição de Bairros por Cluster",
                         labels={"total_socios": "Total de Sócios", "media_filhos_por_familia": "Média de Filhos por Família"},
                         hover_data=["cidade", "bairro", "idade_media", "total_familias", "perfil_familiar_dominante"])  # Exibe mais informações no hover

        st.plotly_chart(fig)

        # Exibe os clusters
        st.write("Cluster de Bairros:", df_perfil[['bairro', 'cluster']])
