from flask import Flask, jsonify
import pandas as pd
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
import streamlit as st
import plotly.express as px
import os



def coleta_dados():
    navegador = webdriver.Chrome()
    navegador.get('https://www.gsuplementos.com.br/lancamentos')
    navegador.maximize_window()

    lista_produtos = []
    for produto in range(1, 31):
        try:
            nome = navegador.find_element(By.XPATH, f'//*[@id="listagemProds"]/div/div/div[{produto}]/div/a/div[1]/div[2]/span/h3').text
            lista_produtos.append(nome)
        except:
            pass

    lista_precos = []
    for preco in range(1, 31):
        try:
            valor = navegador.find_element(By.XPATH, f'//*[@id="listagemProds"]/div/div/div[{preco}]/div/a/div[2]/div/div/span[1]').text
            lista_precos.append(valor)
        except:
            pass


    tb1 = pd.DataFrame(lista_produtos, columns=['produto'])
    tb2 = pd.DataFrame(lista_precos, columns=['precos'])
    df = pd.concat([tb1, tb2], axis=1)

 

    os.makedirs('basesoriginais', exist_ok=True)
    df.to_csv('basesoriginais/Growth_dados.csv', sep=';', index=False)
    print("Dados coletados e salvos com sucesso!")

if __name__ == '__main__':
    coleta_dados()

def tratamento_dados():
    df = pd.read_csv('basesoriginais/Growth_dados.csv', sep=';', encoding='utf-8')

    
    df['precos'] = df['precos'].str.replace('\n', ' ', regex=False).str.strip()

   
    df[['Preco', 'Desconto']] = df['precos'].str.extract(r'R\$\s?([\d.,]+)\s+(\d+)%')

    
    df['Preco'] = df['Preco'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')

    
    df['Desconto'] = pd.to_numeric(df['Desconto'], errors='coerce')

    
    df.dropna(subset=['Preco', 'Desconto'], inplace=True)
    df.drop_duplicates(inplace=True)

    
    df.columns = df.columns.str.lower().str.title()

    
    if 'precos' in df.columns:
        df.drop(columns=['Precos'], inplace=True)

    os.makedirs('basestratadas', exist_ok=True)
    df.to_csv('basestratadas/Growth_dados.csv', sep=';', index=False, encoding='utf-8')
    print("Dados tratados e salvos com sucesso!")


if __name__ == '__main__':
    tratamento_dados()


df = pd.read_csv('basestratadas/Growth_dados.csv', sep=';')
st.dataframe(df)

df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
df.dropna(subset=['Preco'], inplace=True)

st.subheader('Análise de nulos')
aux = df.isnull().sum().reset_index()
aux.columns = ['variavel', 'qtd_miss']
st.dataframe(aux)
print(aux)

st.subheader('Análises univariadas')
st.write('Medidas resumo')
print(df.describe())

st.dataframe(df.describe())
lista_de_colunas = df.columns
precos = st.selectbox('Preco',lista_de_colunas)
media = round(df['Preco'].mean(),2)
desvio = round(df['Preco'].std(),2)
mediana = round(df['Preco'].quantile(0.5),2)
maximo = round(df['Preco'].max(),2)
consumo_minimo = df['Preco'].min()

st.write(f'A coluna escolhida foi {precos}. A sua média é {media}. Seu desvio padrão indica que, quando há desvio, desvia em média {desvio}. E 50% dos dados vão até o valor {mediana}. E seu máximo é de {maximo}.')
st.write(f'O menor valor de {precos} é {consumo_minimo} Reais')
st.write('Histograma')

fig = px.histogram(df,x=[precos])
st.plotly_chart(fig)

st.write('Boxplot')
fig2 = px.box(df, x=[precos])
st.plotly_chart(fig2)


st.subheader('Análises multivariadas')
lista_de_escolhas = st.multiselect('Escolha mais de uma coluna para avaliar', lista_de_colunas)
st.markdown('Gráfico de dispersão')
if len(lista_de_escolhas)>2 or len(lista_de_escolhas)<2:
    st.error('Escolha somente 2 colunas')
else:
    fig3 = px.scatter(df, x=lista_de_escolhas[0], y=lista_de_escolhas[1])
    st.plotly_chart(fig3)