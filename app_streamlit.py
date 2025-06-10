import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import plotly.express as px
import os
import time

# --- Configuração da Página do Streamlit ---
st.set_page_config(
    page_title="Dashboard de Preços Growth",
    page_icon="💪",
    layout="wide"
)

st.title("💪 Dashboard de Análise de Preços - Growth Supplements")

# --- Funções de Coleta e Tratamento (Otimizadas para Streamlit) ---

# @st.cache_data fará com que esta função só rode uma vez, a menos que o código mude.
# Isso evita fazer a coleta demorada toda vez que o usuário mexe em um filtro.
@st.cache_data
def coleta_dados():
    """Usa Selenium para coletar dados do site da Growth e retorna um DataFrame."""
    # Usando webdriver-manager para gerenciar o driver do Chrome automaticamente
    options = Options()
    options.add_argument("--headless")  # ESSENCIAL: Roda o Chrome sem interface gráfica
    options.add_argument("--no-sandbox") # Necessário para rodar em muitos ambientes Linux
    options.add_argument("--disable-dev-shm-usage") # Evita problemas de memória em contêineres
    options.add_argument("--disable-gpu")
    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico)
    
    lista_produtos = []
    lista_precos = []
    
    with st.spinner('Aguarde! Conectando e coletando dados do site... Isso pode levar um minuto.'):
        navegador.get('https://www.gsuplementos.com.br/lancamentos')
        time.sleep(5) # Espera a página carregar completamente

        # Encontra os containers de produtos para uma raspagem mais robusta
        produtos = navegador.find_elements(By.CLASS_NAME, 'mobile-shelf-item')
        
        for produto in produtos:
            try:
                nome = produto.find_element(By.TAG_NAME, 'h3').text
                preco = produto.find_element(By.CLASS_NAME, 'price').text
                lista_produtos.append(nome)
                lista_precos.append(preco)
            except Exception as e:
                # É bom saber se algo deu errado, em vez de usar 'pass'
                print(f"Erro ao coletar um produto: {e}")
                
    navegador.quit()

    if not lista_produtos:
        st.error("Não foi possível coletar os produtos. O site pode ter mudado sua estrutura.")
        return pd.DataFrame()

    df = pd.DataFrame({'produto': lista_produtos, 'precos': lista_precos})
    
    # Salvar o arquivo original continua sendo uma boa prática
    os.makedirs('basesoriginais', exist_ok=True)
    df.to_csv('basesoriginais/Growth_dados_raw.csv', sep=';', index=False)
    
    return df

@st.cache_data
def tratamento_dados(df_raw):
    """Recebe um DataFrame bruto, limpa e trata os dados, e retorna um DataFrame tratado."""
    if df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    
    df['precos'] = df['precos'].str.replace('\n', ' ', regex=False).str.strip()
    # Extrai o preço principal (antes do "ou")
    df['Preco'] = df['precos'].str.extract(r'R\$\s*([\d,]+)')
    
    df['Preco'] = df['Preco'].str.replace(',', '.', regex=False)
    df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
    
    df.dropna(subset=['Preco'], inplace=True)
    df.drop_duplicates(inplace=True)
    
    # Renomeia as colunas para um padrão limpo
    df = df[['produto', 'Preco']].rename(columns={'produto': 'Produto'})

    os.makedirs('basestratadas', exist_ok=True)
    df.to_csv('basestratadas/Growth_dados_tratados.csv', sep=';', index=False, encoding='utf-8')
    
    return df

# --- Interface do Aplicativo ---

# Botão para iniciar o processo. O app só começa de verdade depois disso.
if st.button("🚀 Iniciar Coleta e Análise de Dados"):
    df_raw = coleta_dados()
    if not df_raw.empty:
        df_tratado = tratamento_dados(df_raw)
        # Salva o dataframe tratado no estado da sessão para que não se perca
        st.session_state.df_final = df_tratado 
        st.success("Dados coletados e tratados com sucesso!")

# O dashboard só será exibido se o dataframe estiver na sessão
if 'df_final' in st.session_state:
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

    # A análise multivariada não faz muito sentido com apenas 'Produto' e 'Preço',
    # mas mantive a lógica caso você adicione mais colunas numéricas no futuro (ex: 'Nota', 'Peso').
    st.divider()
    st.header("Análises Multivariadas (Exemplo)")
    st.info("Para o gráfico de dispersão, você precisaria de mais uma coluna numérica (ex: 'Peso em kg', 'Nota de Avaliação').")