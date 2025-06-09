import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException # Importa exceções específicas
import streamlit as st
import plotly.express as px
import os

def coleta_dados():
    if not os.path.exists('basesoriginais/Growth_dados.csv'):
        st.info("Coletando dados da web... isso pode levar um momento.")
        navegador = None # Inicializa navegador como None para garantir que seja fechado
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            navegador = webdriver.Chrome(options=options)

            navegador.get('https://www.gsuplementos.com.br/lancamentos')

            # Espera até que o elemento principal da lista de produtos esteja presente
            wait = WebDriverWait(navegador, 20) # Aumentado o tempo de espera
            wait.until(EC.presence_of_element_located((By.ID, 'listagemProds')))

            lista_produtos = []
            lista_precos = []

            # Coleta de produtos
            # Tenta pegar todos os elementos de produto para maior robustez
            product_elements = navegador.find_elements(By.XPATH, '//*[@id="listagemProds"]/div/div/div[contains(@class, "item-prod")]')

            if not product_elements:
                st.warning("Nenhum elemento de produto encontrado na página com o XPATH fornecido. O XPATH pode estar incorreto ou a página não carregou como esperado.")
                return # Sai da função se não encontrar produtos

            for product_elem in product_elements:
                nome = None
                valor = None
                try:
                    nome = product_elem.find_element(By.XPATH, './/div[contains(@class, "info-prod")]/span/h3').text
                except NoSuchElementException:
                    st.warning("Nome do produto não encontrado para um item.")
                
                try:
                    valor = product_elem.find_element(By.XPATH, './/div[contains(@class, "preco-prod")]/div/div/span[1]').text
                except NoSuchElementException:
                    st.warning("Preço do produto não encontrado para um item.")
                
                lista_produtos.append(nome)
                lista_precos.append(valor)
            
            # Garante que as listas tenham o mesmo comprimento para o DataFrame, preenchendo com None
            max_len = max(len(lista_produtos), len(lista_precos))
            lista_produtos.extend([None] * (max_len - len(lista_produtos)))
            lista_precos.extend([None] * (max_len - len(lista_precos)))

            navegador.quit()

            df_coletado = pd.DataFrame({'produto': lista_produtos, 'precos': lista_precos})
            
            # --- DEPURAÇÃO: Mostra o DataFrame coletado antes de salvar ---
            st.subheader("DEBUG: DataFrame Coletado (Primeiras 5 linhas)")
            st.dataframe(df_coletado.head())
            st.write("Colunas do DataFrame Coletado:", df_coletado.columns.tolist())
            # --- FIM DEPURAÇÃO ---

            if df_coletado.empty or 'precos' not in df_coletado.columns or df_coletado['precos'].isnull().all():
                st.error("Erro na coleta: O DataFrame coletado está vazio, a coluna 'precos' está faltando ou todos os valores de preço são nulos. Verifique os XPATHs e o carregamento da página.")
                return # Sai da função se a coleta falhou criticamente

            os.makedirs('basesoriginais', exist_ok=True)
            df_coletado.to_csv('basesoriginais/Growth_dados.csv', sep=';', index=False)
            st.success("Dados coletados e salvos com sucesso!")
        except TimeoutException:
            st.error("Erro de tempo limite durante a coleta: A página ou um elemento demorou muito para carregar. Verifique sua conexão ou aumente o tempo de espera.")
        except Exception as e:
            st.error(f"Erro inesperado durante a coleta de dados: {e}. Verifique o driver do Chrome e a acessibilidade do site. Detalhes: {str(e)}")
        finally:
            if navegador: # Garante que o navegador seja fechado mesmo se ocorrer um erro
                navegador.quit()
    else:
        st.info("Usando dados existentes para evitar nova coleta.")


def tratamento_dados():
    # Esta condição é importante: Se a coleta falhou e retornou None, não tente ler o CSV.
    if not os.path.exists('basestratadas/Growth_dados.csv') or not os.path.exists('basesoriginais/Growth_dados.csv'):
        st.warning("Arquivo original ou tratado não encontrado. Tentando realizar a coleta de dados.")
        coleta_dados() # Tenta coletar se os arquivos não existem
        if not os.path.exists('basesoriginais/Growth_dados.csv'):
            st.error("Não foi possível coletar dados para tratamento após a tentativa. Verifique logs da coleta.")
            return pd.DataFrame()

    try:
        df = pd.read_csv('basesoriginais/Growth_dados.csv', sep=';', encoding='utf-8')

        # --- DEPURAÇÃO: Mostra o DataFrame lido antes do tratamento ---
        st.subheader("DEBUG: DataFrame Lido (Primeiras 5 linhas)")
        st.dataframe(df.head())
        st.write("Colunas do DataFrame Lido:", df.columns.tolist())
        # --- FIM DEPURAÇÃO ---

        # Adiciona um check para garantir que 'precos' existe no DataFrame lido
        if 'precos' not in df.columns:
            st.error("Erro no tratamento: A coluna 'precos' não foi encontrada no DataFrame lido do CSV. Isso indica um problema na etapa de coleta ou no arquivo CSV gerado.")
            return pd.DataFrame()

        df['precos'] = df['precos'].astype(str).str.replace('\n', ' ', regex=False).str.strip()
        
        # Filtra linhas onde 'precos' não se parece com um preço válido (para evitar erros de regex)
        df = df[df['precos'].str.contains(r'R\$\s?[\d.,]+', na=False)].copy() # Adiciona .copy() para evitar SettingWithCopyWarning
        
        # Usa .str.extract diretamente
        extracted_data = df['precos'].str.extract(r'R\$\s?([\d.,]+)\s+(\d+)%')
        df['Preco'] = extracted_data[0]
        df['Desconto'] = extracted_data[1]

        df['Preco'] = df['Preco'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
        df['Desconto'] = pd.to_numeric(df['Desconto'], errors='coerce')
        
        df.dropna(subset=['Preco', 'Desconto'], inplace=True)
        df.drop_duplicates(inplace=True)
        
        df.columns = df.columns.str.lower().str.title()
        
        if 'Precos' in df.columns: # 'Precos' com P maiúsculo após df.columns.str.title()
            df.drop(columns=['Precos'], inplace=True) # Remove a coluna original 'precos'

        os.makedirs('basestratadas', exist_ok=True)
        df.to_csv('basestratadas/Growth_dados.csv', sep=';', index=False, encoding='utf-8')
        st.success("Dados tratados e salvos com sucesso!")
        return df
    except Exception as e:
        st.error(f"Erro no tratamento de dados: {e}. Detalhes: {str(e)}")
        return pd.DataFrame()


st.title('Análise de Produtos da Growth Suplementos')

# A lógica de chamada já está no `tratamento_dados` para garantir que o CSV exista.
df = tratamento_dados()

if not df.empty:
    st.subheader('Dados Coletados e Tratados')
    st.dataframe(df)

    # Verifica se a coluna 'Preco' existe após o tratamento
    if 'Preco' not in df.columns:
        st.error("Erro: A coluna 'Preco' (após tratamento) não foi encontrada. Verifique as etapas de extração de preço.")
        st.stop() # Para a execução do Streamlit aqui

    df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
    df.dropna(subset=['Preco'], inplace=True)

    st.subheader('Análise de Nulos')
    aux = df.isnull().sum().reset_index()
    aux.columns = ['Variavel', 'Qtd_Miss']
    st.dataframe(aux)

    st.subheader('Análises Univariadas')
    st.write('Medidas resumo')
    st.dataframe(df.describe())

    lista_de_colunas_numericas = df.select_dtypes(include=['number']).columns
    if 'Preco' in lista_de_colunas_numericas:
        precos = st.selectbox('Escolha a coluna para análise de preço', lista_de_colunas_numericas)

        media = round(df[precos].mean(),2)
        desvio = round(df[precos].std(),2)
        mediana = round(df[precos].quantile(0.5),2)
        maximo = round(df[precos].max(),2)
        consumo_minimo = df[precos].min()

        st.write(f'A coluna escolhida foi **{precos}**. A sua média é **R$ {media}**. Seu desvio padrão indica que, quando há desvio, desvia em média **R$ {desvio}**. E 50% dos dados vão até o valor **R$ {mediana}**. E seu máximo é de **R$ {maximo}**.')
        st.write(f'O menor valor de **{precos}** é **R$ {consumo_minimo}** Reais')

        st.write('Histograma')
        fig = px.histogram(df, x=[precos], title=f'Distribuição de {precos}')
        st.plotly_chart(fig)

        st.write('Boxplot')
        fig2 = px.box(df, x=[precos], title=f'Boxplot de {precos}')
        st.plotly_chart(fig2)
    else:
        st.warning("Não há coluna numérica 'Preco' para análise univariada. Verifique o tratamento de dados.")

    st.subheader('Análises Multivariadas')
    lista_de_colunas_para_dispersao = df.select_dtypes(include=['number']).columns.tolist()
    lista_de_escolhas = st.multiselect('Escolha exatamente 2 colunas numéricas para avaliar', lista_de_colunas_para_dispersao)

    st.markdown('Gráfico de dispersão')
    if len(lista_de_escolhas) != 2:
        st.error('Por favor, escolha **somente 2 colunas** para o gráfico de dispersão.')
    else:
        fig3 = px.scatter(df, x=lista_de_escolhas[0], y=lista_de_escolhas[1],
                          title=f'Dispersão entre {lista_de_escolhas[0]} e {lista_de_escolhas[1]}')
        st.plotly_chart(fig3)
else:
    st.error("Não foi possível carregar os dados para análise. Verifique as etapas de coleta e tratamento.")