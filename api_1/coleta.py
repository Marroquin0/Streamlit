import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By


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

 


    df.to_csv('basesoriginais/Growth_dados.csv', sep=';', index=False)
    print("Dados coletados e salvos com sucesso!")

if __name__ == '__main__':
    coleta_dados()