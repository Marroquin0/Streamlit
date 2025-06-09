

import pandas as pd

def tratamento_dados():
    df = pd.read_csv('basesoriginais/Growth_dados.csv', sep=';', encoding='utf-8')

    df['preco'] = df.precos.str.replace('\n', ' ') \
        .str.replace(' ,', ',').str.replace(', ', ',') \
        .str.replace('R$ ', '').str.split(' ').str.get(0) \
        .str.replace(',', '').str.replace('.', '').str.replace('', '.')

    df['desconto'] = df.precos.str.replace('\n', ' ') \
        .str.replace(' ,', ',').str.replace(', ', ',') \
        .str.replace('R$ ', '').str.split(' ').str.get(1)

    df.drop(columns=['precos'], inplace=True)

    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)

    df.columns = df.columns.str.lower().str.title()
    
    df['preco'] = pd.to_numeric(df['Preco'], errors='coerce')
    df = df[df['Preco'].notnull()]
    
 

    
    df.to_csv('basestratadas/Growth_dados.csv', sep=';', index=False, encoding='utf-8')
    print("Dados tratados e salvos com sucesso!")

if __name__ == '__main__':
    tratamento_dados()
