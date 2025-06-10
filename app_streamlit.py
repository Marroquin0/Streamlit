import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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

@st.cache_data
def coleta_dados():
    """
    Usa Selenium para coletar dados, salva arquivos de depuração e retorna um DataFrame.
    Esta função NÃO deve ter nenhum comando st.(widget).
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    servico = Service(executable_path='/usr/bin/chromedriver')
    navegador = webdriver.Chrome(service=servico, options=options)
    
    lista_produtos = []
    lista_precos = []
    
    navegador.get('https://www.gsuplementos.com.br/lancamentos')
    time.sleep(7)

    # Salva arquivos de depuração
    try:
        navegador.save_screenshot("debug_screenshot.png")
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(navegador.page_source)
    except Exception as e:
        # Se der erro aqui, imprimimos no log do terminal
        print(f"Erro ao criar arquivos de depuração: {e}")

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

    # Se a lista estiver vazia, retorna um DataFrame vazio.
    # A lógica para mostrar o erro será feita fora desta função.
    if not lista_produtos:
        return pd.DataFrame()

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

# --- Interface Principal do Aplicativo ---
# Esta parte é executada toda vez. É aqui que os widgets devem ficar.

if st.button("🚀 Iniciar Coleta e Análise de Dados"):
    # Limpa o estado da sessão anterior para forçar uma nova coleta
    if 'df_final' in st.session_state:
        del st.session_state.df_final
    
    with st.spinner('Aguarde! Coletando e tratando dados...'):
        df_raw = coleta_dados()
        df_tratado = tratamento_dados(df_raw)
        
        # Se a coleta falhou (retornou df vazio), não guarda nada na sessão.
        # Se funcionou, guarda o resultado na sessão.
        if not df_tratado.empty:
            st.session_state.df_final = df_tratado
        else:
            # Garante que se a coleta falhar, o dashboard antigo não continue aparecendo
            if 'df_final' in st.session_state:
                del st.session_state.df_final

# Lógica de exibição fora do botão
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

    # ... (resto do seu dashboard continua aqui) ...

else:
    # Se o df_final não está na sessão, significa que ou o botão não foi apertado,
    # ou a coleta falhou. Agora verificamos se foi por falha na coleta.
    if os.path.exists("debug_screenshot.png"):
        st.error("Não foi possível coletar os produtos. O site pode ter mudado sua estrutura, ou pode estar bloqueando o robô.")
        st.info("Arquivos de depuração foram gerados. Use os botões abaixo para baixá-los e analisar o problema.")
        
        with open("debug_screenshot.png", "rb") as file:
            st.download_button(
                label="Baixar Foto da Tela (screenshot.png)",
                data=file,
                file_name="screenshot.png",
                mime="image/png"
            )
        with open("debug_page.html", "r", encoding="utf-8") as file:
            st.download_button(
                label="Baixar Código HTML da Página (pagina.html)",
                data=file,
                file_name="pagina.html",
                mime="text/html"
            )