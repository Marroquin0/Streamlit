import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import plotly.express as px
import os
import time


st.set_page_config(
    page_title="Dashboard de Preços Growth",
    page_icon="💪",
    layout="wide"
)

st.title("💪 Dashboard de Análise de Preços - Growth Supplements")



@st.cache_data
def coleta_dados():
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    servico = Service(executable_path='/usr/bin/chromedriver')
    navegador = webdriver.Chrome(service=servico, options=options)
    
    lista_produtos = [ ]
    lista_precos = [ ]
    
    navegador.get('https://www.gsuplementos.com.br/lancamentos')
    time.sleep(7)

    
    produtos = navegador.find_elements(By.CLASS_NAME, 'cardprod')
    
    for produto in produtos:
        try:
            #
            nome = produto.find_element(By.CLASS_NAME, 'cardprod-nomeProduto-t1').text
            preco = produto.find_element(By.CLASS_NAME, 'cardprod-valor').text
            lista_produtos.append(nome)
            lista_precos.append(preco)
        except Exception as e:
            
            print(f"Erro ao coletar um produto individual: {e}")
            
    navegador.quit()

    
    if not lista_produtos:
        return pd.DataFrame()

    df = pd.DataFrame({'produto': lista_produtos, 'precos': lista_precos})
    os.makedirs('basesoriginais', exist_ok=True)
    df.to_csv('basesoriginais/Growth_dados_raw.csv', sep=';', index=False)
    
    return df

@st.cache_data
def tratamento_dados(df_raw):
    
    if df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    
    df['precos'] = df['precos'].str.replace('\n', ' ', regex=False).str.strip()
    
    df['Preco'] = df['precos'].str.extract(r'R\$\s*([\d,]+)')
    
    df['Preco'] = df['Preco'].str.replace(',', '.', regex=False)
    df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
    
    df.dropna(subset=['Preco'], inplace=True)
    df.drop_duplicates(inplace=True)
    
    df = df[['produto', 'Preco']].rename(columns={'produto': 'Produto'})

    os.makedirs('basestratadas', exist_ok=True)
    df.to_csv('basestratadas/Growth_dados_tratados.csv', sep=';', index=False, encoding='utf-8')
    
    return df



if st.button("🚀 Iniciar Coleta e Análise de Dados"):
    
    if 'df_final' in st.session_state:
        del st.session_state.df_final
    
    with st.spinner('Aguarde! Coletando e tratando dados... Isso pode levar um minuto.'):
        df_raw = coleta_dados()
        df_tratado = tratamento_dados(df_raw)
        
        if not df_tratado.empty:
            st.session_state.df_final = df_tratado
        else:
            
            st.session_state.coleta_falhou = True




if 'df_final' in st.session_state:
    st.success("Dados coletados e tratados com sucesso!")
    df = st.session_state.df_final
    
    st.divider()
    st.header("Visualização dos Dados Tratados")
    st.dataframe(df)

    

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Análise de Nulos")
        st.dataframe(df.isnull().sum().reset_index().rename(columns={'index': 'Variável', 0: 'Qtd. Nulos'}))

    with col2:
        st.subheader("Estatísticas Descritivas")
        st.dataframe(df.describe())

    st.divider()
    st.header("Análises dos Preços")

    media = round(df['Preco'].mean(), 2)
    desvio = round(df['Preco'].std(), 2)
    mediana = round(df['Preco'].median(), 2)
    maximo = round(df['Preco'].max(), 2)
    minimo = round(df['Preco'].min(), 2)

    st.metric("Preço Médio", f"R$ {media}")
    st.write(f"O preço mediano (50% dos produtos custam até este valor) é de R$ {mediana}.")
    st.write(f"Os preços variam de **R$ {minimo}** a **R$ {maximo}**.")
    
    col_hist, col_box = st.columns(2)
    
    with col_hist:
        st.subheader("Histograma de Preços")
        fig_hist = px.histogram(df, x='Preco', nbins=20, title="Distribuição de Frequência dos Preços")
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_box:
        st.subheader("Boxplot de Preços")
        fig_box = px.box(df, y='Preco', title="Dispersão e Outliers dos Preços")
        st.plotly_chart(fig_box, use_container_width=True)


elif 'coleta_falhou' in st.session_state:
    st.error("Não foi possível coletar os produtos. O site pode ter mudado sua estrutura ou pode estar bloqueando o robô.")
    
    del st.session_state.coleta_falhou