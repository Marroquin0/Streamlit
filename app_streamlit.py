import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager  # <--- MUDANÇA AQUI (NÃO PRECISAMOS MAIS DISSO)
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


@st.cache_data
def coleta_dados():
    """Usa Selenium para coletar dados do site da Growth e retorna um DataFrame."""
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    servico = Service(executable_path='/usr/bin/chromedriver')
    navegador = webdriver.Chrome(service=servico, options=options)
    
    lista_produtos = []
    lista_precos = []
    
    with st.spinner('Aguarde! Conectando e coletando dados do site... Isso pode levar um minuto.'):
        navegador.get('https://www.gsuplementos.com.br/lancamentos')
        time.sleep(7) # Aumentei um pouco o tempo de espera, por segurança

        # --- INÍCIO DO CÓDIGO DE DETETIVE ---
        # Vamos salvar uma foto e o HTML para ver o que o Selenium está enxergando.
        st.warning("Iniciando modo de depuração...")
        try:
            navegador.save_screenshot("debug_screenshot.png")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(navegador.page_source)
            st.success("Arquivos de depuração criados com sucesso!")
        except Exception as e:
            st.error(f"Erro ao criar arquivos de depuração: {e}")
        # --- FIM DO CÓDIGO DE DETETIVE ---

        produtos = navegador.find_elements(By.CLASS_NAME, 'mobile-shelf-item')
        
        for produto in produtos:
            try:
                nome = produto.find_element(By.TAG_NAME, 'h3').text
                preco = produto.find_element(By.CLASS_NAME, 'price').text
                lista_produtos.append(nome)
                lista_precos.append(preco)
            except Exception as e:
                print(f"Erro ao coletar um produto: {e}")
                
    navegador.quit()

    if not lista_produtos:
        st.error("Não foi possível coletar os produtos. O site pode ter mudado sua estrutura, ou pode estar bloqueando o robô. Verifique os arquivos de depuração baixados.")
        # Se os arquivos de depuração foram criados, oferece botões para download
        if os.path.exists("debug_screenshot.png"):
            with open("debug_screenshot.png", "rb") as file:
                st.download_button(
                    label="Baixar Foto da Tela (screenshot.png)",
                    data=file,
                    file_name="screenshot.png",
                    mime="image/png"
                )
        if os.path.exists("debug_page.html"):
            with open("debug_page.html", "r", encoding="utf-8") as file:
                st.download_button(
                    label="Baixar Código HTML da Página (pagina.html)",
                    data=file,
                    file_name="pagina.html",
                    mime="text/html"
                )
        return pd.DataFrame() # Retorna um DataFrame vazio para não dar erro

    # Se encontrar produtos, continua normalmente
    df = pd.DataFrame({'produto': lista_produtos, 'precos': lista_precos})
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
    df['Preco'] = df['precos'].str.extract(r'R\$\s*([\d,]+)')
    
    df['Preco'] = df['Preco'].str.replace(',', '.', regex=False)
    df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
    
    df.dropna(subset=['Preco'], inplace=True)
    df.drop_duplicates(inplace=True)
    
    df = df[['produto', 'Preco']].rename(columns={'produto': 'Produto'})

    os.makedirs('basestratadas', exist_ok=True)
    df.to_csv('basestratadas/Growth_dados_tratados.csv', sep=';', index=False, encoding='utf-8')
    
    return df

# --- Interface do Aplicativo ---
if st.button("🚀 Iniciar Coleta e Análise de Dados"):
    df_raw = coleta_dados()
    if not df_raw.empty:
        df_tratado = tratamento_dados(df_raw)
        st.session_state.df_final = df_tratado 
        st.success("Dados coletados e tratados com sucesso!")

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

    st.divider()
    st.header("Análises Multivariadas (Exemplo)")
    st.info("Para o gráfico de dispersão, você precisaria de mais uma coluna numérica (ex: 'Peso em kg', 'Nota de Avaliação').")


    
