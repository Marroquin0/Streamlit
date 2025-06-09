from flask import Flask, jsonify
import pandas as pd
import json

app = Flask(__name__)

@app.route('/')
def home():
    return ' Acesse -  http://127.0.0.1:5001/dados - para ver os dados.'

@app.route('/dados')
def carregardados():
    df = pd.read_csv('basestratadas/Growth_dados.csv', sep=';', encoding='utf-8')
    return jsonify(df.to_json())

if __name__ == '__main__':
    app.run(debug=True)