
import requests
import pandas as pd
import numpy as np
import time
from flask import Flask, render_template_string
from datetime import datetime
import pytz

app = Flask(__name__)

TICKERS = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana"
}

ALERTAS = {}

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; }
        table { border-collapse: collapse; width: 90%; margin: auto; }
        th, td { border: 1px solid #ccc; padding: 12px; }
        th { background-color: #f2f2f2; font-size: 20px; }
        td { font-size: 18px; }
        .tendencia-alta { color: green; font-weight: bold; }
        .tendencia-baixa { color: red; font-weight: bold; }
        .erro { color: red; }
        .legenda { background-color: #f8f8f8; margin-top: 30px; padding: 20px; width: 80%; margin-left: auto; margin-right: auto; border-radius: 10px; }
        .legenda p { font-size: 18px; text-align: left; }
        .verde { color: green; font-weight: bold; }
        .vermelho { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <h1>FeOliCryptoBot - Painel</h1>
    <table>
        <tr>
            <th>Cripto</th>
            <th>Preço Atual</th>
            <th>RSI</th>
            <th>MACD</th>
            <th>Signal</th>
            <th>Tendência</th>
            <th>Último Alerta</th>
        </tr>
        {% for t, nome in nomes.items() %}
        <tr>
            <td>{{ nome }}</td>
            <td>${{ '%.2f' % precos[t] }}</td>
            <td>{{ '%.2f' % ind[t]['rsi'] }}</td>
            <td>{{ '%.4f' % ind[t]['macd'] }}</td>
            <td>{{ '%.4f' % ind[t]['signal'] }}</td>
            <td class="{{ 'tendencia-alta' if ind[t]['tendencia'] == 'alta' else 'tendencia-baixa' }}">
                {{ '▲ Alta' if ind[t]['tendencia'] == 'alta' else '▼ Baixa' }}
            </td>
            <td>
                {% if alertas[t] == 1 %}
                    🟢 Alerta de Compra
                {% elif alertas[t] == -1 %}
                    🔴 Alerta de Venda
                {% elif alertas[t] == 0 %}
                    —
                {% else %}
                    ⚠️ Erro: {{ alertas[t] }}
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>

    <div class="legenda">
        <h3>📘 Legenda dos Alertas:</h3>
        <p>🟢 <span class="verde">Alerta de COMPRA</span>: RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal</p>
        <p>🔴 <span class="vermelho">Alerta de VENDA</span>: RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal</p>
    </div>

    <p style="margin-top: 30px; color: gray;">Atualizado a cada minuto (modo debug)</p>
</body>
</html>
'''

def fetch_binance_ohlc(symbol, interval="1d", limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "number_of_trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = pd.to_numeric(df["close"])
    df["timestamp"] = pd.to_datetime(df["close_time"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df

def calcula_indicadores(df):
    close = df["close"]
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    return rsi, macd, signal

@app.route("/")
def home():
    precos = {}
    indicadores = {}
    for t in TICKERS:
        try:
            df = fetch_binance_ohlc(t)
            if df.empty or len(df) < 30:
                raise ValueError("Dados insuficientes")

            rsi, macd, signal = calcula_indicadores(df)
            atual = df.iloc[-1]
            precos[t] = float(atual["close"])

            rsi_val = rsi.iloc[-1]
            macd_val = macd.iloc[-1]
            signal_val = signal.iloc[-1]

            tendencia = "alta" if macd_val > signal_val else "baixa"

            indicadores[t] = {
                "rsi": rsi_val,
                "macd": macd_val,
                "signal": signal_val,
                "tendencia": tendencia
            }

            # alerta
            if rsi_val < 30 and macd_val > signal_val:
                ALERTAS[t] = 1
            elif rsi_val > 70 and macd_val < signal_val:
                ALERTAS[t] = -1
            else:
                ALERTAS[t] = 0

        except Exception as e:
            precos[t] = 0.0
            indicadores[t] = {"rsi": 0, "macd": 0, "signal": 0, "tendencia": "baixa"}
            ALERTAS[t] = str(e)

    return render_template_string(TEMPLATE, precos=precos, ind=indicadores, nomes=TICKERS, alertas=ALERTAS)

if __name__ == "__main__":
    app.run(debug=True)
