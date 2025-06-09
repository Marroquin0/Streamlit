import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import streamlit as st
import plotly.express as px
import os

def coleta_dados():
    if not os.path.exists('basesoriginais/Growth_dados.csv'):
        st.info("Coletando dados da web... isso pode levar um momento.")
        navegador = None
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            navegador = webdriver.Chrome(options=options)

            navegador.get('https://www.gsuplementos.com.br/lancamentos')

            wait = WebDriverWait(navegador, 30)
            wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="listagemProds"]/div/div/div[contains(@class, "item-prod")]')))

            lista_produtos = []
            lista_precos = []

            product_elements = navegador.find_elements(By.XPATH, '//*[@id="listagemProds"]/div/div/div[contains(@class, "item-prod")]')

            if not product_elements:
                st.error("ERRO GRAVE: Nenhum elemento de produto encontrado com o XPATH principal.")
                return

            st.write(f"DEBUG: Encontrados {len(product_elements)} elementos de produto.")

            for i, product_elem in enumerate(product_elements):
                nome = None
                valor = None

                try:
                    nome_element = product_elem.find_element(By.XPATH, './/div[contains(@class, "info-prod")]/span/h3')
                    nome = nome_element.text.strip()
                    if not nome:
                        nome = None
                except NoSuchElementException:
                    st.warning(f"Nome do produto não encontrado para o item {i+1}.")
                except Exception as e:
                    st.warning(f"Erro ao coletar nome para o item {i+1}: {e}")

                try:
                    # Novo XPath do preço
                    preco_element = product_elem.find_element(By.XPATH, './/span[1]')
                    valor = preco_element.text.strip()

                    # Adiciona "R$" caso não esteja presente
                    if valor and not valor.startswith('R$'):
                        valor = f'R$ {valor}'

                    if not valor:
                        valor = None
                except NoSuchElementException:
                    st.warning(f"Preço do produto não encontrado para o item {i+1}.")
                except Exception as e:
                    st.warning(f"Erro ao coletar preço para o item {i+1}: {e}")

                lista_produtos.append(nome)
                lista_precos.append(valor)

            max_len = max(len(lista_produtos), len(lista_precos))
            lista_produtos.extend([None] * (max_len - len(lista_produtos)))
            lista_precos.extend([None] * (max_len - len(lista_precos)))

            navegador.quit()

            df_coletado = pd.DataFrame({'produto': lista_produtos, 'precos': lista_precos})

            st.subheader("DEBUG: DataFrame Coletado (Primeiras 5 linhas)")
            st.dataframe(df_coletado.head(50))
            st.write("Colunas do DataFrame Coletado:", df_coletado.columns.tolist())

            if df_coletado.empty or 'precos' not in df_coletado.columns or df_coletado['precos'].dropna().empty:
                st.error("Erro na coleta: O DataFrame está vazio ou sem valores válidos na coluna 'precos'.")
                return

            os.makedirs('basesoriginais', exist_ok=True)
            df_coletado.to_csv('basesoriginais/Growth_dados.csv', sep=';', index=False)
            st.success("Dados coletados e salvos com sucesso!")

        except TimeoutException:
            st.error("Erro de tempo limite: A página demorou muito para carregar ou o elemento não foi encontrado.")
        except Exception as e:
            st.error(f"Erro inesperado na coleta: {e}")
        finally:
            if navegador:
                navegador.quit()
    else:
        st.info("Usando dados existentes para evitar nova coleta.")


def tratamento_dados():
    if not os.path.exists('basestratadas/Growth_dados.csv') or not os.path.exists('basesoriginais/Growth_dados.csv'):
        st.warning("Arquivo original ou tratado não encontrado. Tentando realizar a coleta de dados.")
        coleta_dados()
        if not os.path.exists('basesoriginais/Growth_dados.csv'):
            st.error("Não foi possível coletar dados para tratamento após a tentativa. Verifique logs da coleta.")
            return pd.DataFrame()

    try:
        df = pd.read_csv('basesoriginais/Growth_dados.csv', sep=';', encoding='utf-8')

        df.columns = df.columns.str.lower()

        st.subheader("DEBUG: DataFrame Lido (Primeiras 5 linhas)")
        st.dataframe(df.head(50)) # Mostra mais linhas para depuração
        st.write("Colunas do DataFrame Lido:", df.columns.tolist())

        if 'precos' not in df.columns:
            st.error("Erro no tratamento: A coluna 'precos' (minúscula) não foi encontrada no DataFrame lido do CSV após a conversão para minúsculas. Isso indica um problema na etapa de coleta ou no arquivo CSV gerado (verifique se a coluna 'Precos' com P maiúsculo existia).")
            return pd.DataFrame()
        
        # Converte a coluna 'precos' para string, trata 'None' ou NaN como string vazia para regex
        df['precos'] = df['precos'].fillna('').astype(str).str.replace('\n', ' ', regex=False).str.strip()
        
        # Filtra linhas onde 'precos' não se parece com um preço válido (para evitar erros de regex)
        # Usa .copy() para evitar SettingWithCopyWarning
        df = df[df['precos'].str.contains(r'R\$\s?[\d.,]+', na=False)].copy()
        
        # Verifica se o DataFrame ficou vazio após a filtragem
        if df.empty:
            st.error("Nenhum preço válido foi encontrado no DataFrame após a filtragem por padrão R$. O scraping de preços pode estar falhando.")
            return pd.DataFrame()

        # Extrai Preço e Desconto
        extracted_data = df['precos'].str.extract(r'R\$\s?([\d.,]+)\s+(\d+)%')
        df['Preco'] = extracted_data[0]
        df['Desconto'] = extracted_data[1]

        df['Preco'] = df['Preco'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
        df['Desconto'] = pd.to_numeric(df['Desconto'], errors='coerce')
        
        df.dropna(subset=['Preco', 'Desconto'], inplace=True)
        df.drop_duplicates(inplace=True)
        
        # Garante que as colunas finais fiquem em Title Case
        df.columns = df.columns.str.lower().str.title()
        
        if 'Precos' in df.columns:
            df.drop(columns=['Precos'], inplace=True)

        os.makedirs('basestratadas', exist_ok=True)
        df.to_csv('basestratadas/Growth_dados.csv', sep=';', index=False, encoding='utf-8')
        st.success("Dados tratados e salvos com sucesso!")
        return df
    except Exception as e:
        st.error(f"Erro no tratamento de dados: {e}. Detalhes: {str(e)}")
        return pd.DataFrame()


st.title('Análise de Produtos da Growth Suplementos')

df = tratamento_dados()

if not df.empty:
    st.subheader('Dados Coletados e Tratados')
    st.dataframe(df)

    if 'Preco' not in df.columns:
        st.error("Erro: A coluna 'Preco' (após tratamento) não foi encontrada. Verifique as etapas de extração de preço.")
        st.stop()

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