<<<<<<< HEAD
import pandas as pd
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
import streamlit as st
import plotly.express as px
import os

# Função de coleta de dados
def coleta_dados():
    # Verifique se o arquivo já existe ou se você precisa coletar novos dados
    # Uma boa prática é evitar coletar dados a cada execução do Streamlit
    # especialmente se o site tiver proteções contra scraping ou se a coleta demorar.
    # Você pode adicionar uma lógica para só coletar se o arquivo não existir ou for muito antigo.
    if not os.path.exists('basesoriginais/Growth_dados.csv'):
        st.info("Coletando dados da web... isso pode levar um momento.")
        try:
            # Usar opções headless para rodar Selenium em ambientes sem interface gráfica
            # (necessário para Streamlit Sharing)
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            navegador = webdriver.Chrome(options=options)

            navegador.get('https://www.gsuplementos.com.br/lancamentos')
            # navegador.maximize_window() # maximize_window não funciona em headless

            lista_produtos = []
            # Use um range menor para testes ou seja mais específico com XPATH
            for produto in range(1, 31): # 30 produtos é um bom número para a página
                try:
                    # Adicione uma espera para garantir que o elemento esteja carregado
                    # from selenium.webdriver.support.ui import WebDriverWait
                    # from selenium.webdriver.support import expected_conditions as EC
                    # wait = WebDriverWait(navegador, 10)
                    # nome_element = wait.until(EC.presence_of_element_located((By.XPATH, f'//*[@id="listagemProds"]/div/div/div[{produto}]/div/a/div[1]/div[2]/span/h3')))
                    # nome = nome_element.text
                    nome = navegador.find_element(By.XPATH, f'//*[@id="listagemProds"]/div/div/div[{produto}]/div/a/div[1]/div[2]/span/h3').text
                    lista_produtos.append(nome)
                except Exception as e:
                    # st.warning(f"Não foi possível coletar o produto {produto}: {e}")
                    pass

            lista_precos = []
            for preco in range(1, 31):
                try:
                    # valor_element = wait.until(EC.presence_of_element_located((By.XPATH, f'//*[@id="listagemProds"]/div/div/div[{preco}]/div/a/div[2]/div/div/span[1]')))
                    # valor = valor_element.text
                    valor = navegador.find_element(By.XPATH, f'//*[@id="listagemProds"]/div/div/div[{preco}]/div/a/div[2]/div/div/span[1]').text
                    lista_precos.append(valor)
                except Exception as e:
                    # st.warning(f"Não foi possível coletar o preço {preco}: {e}")
                    pass

            navegador.quit() # Fechar o navegador após a coleta

            tb1 = pd.DataFrame(lista_produtos, columns=['produto'])
            tb2 = pd.DataFrame(lista_precos, columns=['precos'])
            df_coletado = pd.concat([tb1, tb2], axis=1)

            os.makedirs('basesoriginais', exist_ok=True)
            df_coletado.to_csv('basesoriginais/Growth_dados.csv', sep=';', index=False)
            st.success("Dados coletados e salvos com sucesso!")
        except Exception as e:
            st.error(f"Erro na coleta de dados: {e}. Verifique o driver do Chrome e a acessibilidade do site.")
    else:
        st.info("Usando dados existentes para evitar nova coleta.")


# Função de tratamento de dados
def tratamento_dados():
    if not os.path.exists('basestratadas/Growth_dados.csv') or not os.path.exists('basesoriginais/Growth_dados.csv'):
        st.warning("Arquivo original não encontrado para tratamento. Realize a coleta de dados primeiro.")
        coleta_dados() # Chama a coleta se o original não existe
        if not os.path.exists('basesoriginais/Growth_dados.csv'): # Verifica de novo
            st.error("Não foi possível coletar dados para tratamento.")
            return pd.DataFrame() # Retorna DataFrame vazio se a coleta falhar

    try:
        df = pd.read_csv('basesoriginais/Growth_dados.csv', sep=';', encoding='utf-8')

        df['precos'] = df['precos'].str.replace('\n', ' ', regex=False).str.strip()
        df[['Preco', 'Desconto']] = df['precos'].str.extract(r'R\$\s?([\d.,]+)\s+(\d+)%')
        df['Preco'] = df['Preco'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
        df['Desconto'] = pd.to_numeric(df['Desconto'], errors='coerce')
        df.dropna(subset=['Preco', 'Desconto'], inplace=True)
        df.drop_duplicates(inplace=True)
        df.columns = df.columns.str.lower().str.title()
        if 'Precos' in df.columns: # Corrigido para 'Precos' capitalizado
            df.drop(columns=['Precos'], inplace=True)

        os.makedirs('basestratadas', exist_ok=True)
        df.to_csv('basestratadas/Growth_dados.csv', sep=';', index=False, encoding='utf-8')
        st.success("Dados tratados e salvos com sucesso!")
        return df # Retorna o DataFrame tratado
    except Exception as e:
        st.error(f"Erro no tratamento de dados: {e}")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

# --- Aplicação Streamlit ---

st.title('Análise de Produtos da Growth Suplementos')

# Chama as funções de coleta e tratamento
coleta_dados()
df = tratamento_dados() # A função agora retorna o DataFrame

if not df.empty:
    st.subheader('Dados Coletados e Tratados')
    st.dataframe(df)

    df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
    df.dropna(subset=['Preco'], inplace=True)

    st.subheader('Análise de Nulos')
    aux = df.isnull().sum().reset_index()
    aux.columns = ['Variavel', 'Qtd_Miss']
    st.dataframe(aux)
    # print(aux) # Comentado para evitar output no terminal do Streamlit

    st.subheader('Análises Univariadas')
    st.write('Medidas resumo')
    # print(df.describe()) # Comentado para evitar output no terminal do Streamlit
    st.dataframe(df.describe())

    lista_de_colunas_numericas = df.select_dtypes(include=['number']).columns
    if 'Preco' in lista_de_colunas_numericas:
        precos = 'Preco' # Definindo 'Preco' como a coluna padrão para esta seção
        # Ou, se quiser deixar o usuário escolher:
        # precos = st.selectbox('Escolha a coluna para análise de preço', lista_de_colunas_numericas)

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
    # Filtra apenas colunas numéricas para o multiselect
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