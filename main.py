
from flask import Flask, render_template_string
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time

app = Flask(__name__)

TICKERS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
API_URL = 'https://api.binance.com/api/v3/klines'
ALERTAS = {}
INTERVAL = '1m'
LIMIT = 100

def get_binance_data(symbol, interval='1m', limit=100):
    url = f"{API_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'open_time','open','high','low','close','volume',
        'close_time','quote_asset_volume','number_of_trades',
        'taker_buy_base_asset_volume','taker_buy_quote_asset_volume','ignore'
    ])
    df['close'] = df['close'].astype(float)
    return df

def calculate_indicators(df):
    close = df['close']
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)

    avg_gain = up.rolling(window=14).mean()
    avg_loss = down.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()

    tendencia = []
    for i in range(len(macd)):
        if pd.isna(macd[i]) or pd.isna(signal[i]):
            tendencia.append("-")
        elif macd[i] > signal[i]:
            tendencia.append("Alta")
        elif macd[i] < signal[i]:
            tendencia.append("Baixa")
        else:
            tendencia.append("Neutra")

    return round(rsi.iloc[-1], 2), round(macd.iloc[-1], 4), round(signal.iloc[-1], 4), tendencia[-1]

@app.route("/")
def home():
    precos = {}
    indicadores = {}
    for t in TICKERS:
        df = get_binance_data(t, interval=INTERVAL, limit=LIMIT)
        preco = float(df['close'].iloc[-1])
        rsi, macd, signal, tendencia = calculate_indicators(df)
        precos[t] = preco
        indicadores[t] = {'RSI': rsi, 'MACD': macd, 'Signal': signal, 'Tendência': tendencia}

    legenda = "<strong>Legenda:</strong> RSI &lt; 30 = possível compra | RSI &gt; 70 = possível venda | MACD cruza Signal de baixo pra cima = compra | de cima pra baixo = venda"
    template = """
    <h1>Painel de Criptoativos (Binance)</h1>
    <p>{{ legenda|safe }}</p>
    <table border="1" cellpadding="5">
        <tr>
            <th>Par</th>
            <th>Preço</th>
            <th>RSI</th>
            <th>MACD</th>
            <th>Signal</th>
            <th>Tendência</th>
        </tr>
        {% for nome in nomes %}
        <tr>
            <td>{{ nome }}</td>
            <td>{{ precos[nome] }}</td>
            <td>{{ ind[nome]['RSI'] }}</td>
            <td>{{ ind[nome]['MACD'] }}</td>
            <td>{{ ind[nome]['Signal'] }}</td>
            <td>{{ ind[nome]['Tendência'] }}</td>
        </tr>
        {% endfor %}
    </table>
    <br>
    <p>Atualizado a cada minuto (modo debug)</p>
    """
    return render_template_string(template, precos=precos, ind=indicadores, nomes=TICKERS, legenda=legenda)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
