
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import numpy as np
import time
import threading
import requests

app = Flask(__name__)

TICKERS = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana"
}

CHAT_ID = "6290071192"
TOKEN = "7733542207:AAEgogN0zgimnJEo1Q3vNaQX6Ayc7tpHF_s"
ALERTAS = {}
DEBUG = True

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, json=payload)
    except:
        pass

def analisar():
    global precos, indicadores, ALERTAS
    precos = {}
    indicadores = {}

    for t, nome in TICKERS.items():
        try:
            df = yf.download(t, period="3mo", interval="1d", progress=False)
            df.dropna(inplace=True)
            close = df["Close"]

            if len(close) < 30:
                continue

            rsi_series = 100 - (100 / (1 + (close.pct_change().rolling(14).mean() /
                                            close.pct_change().rolling(14).std())))
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd_series = exp1 - exp2
            signal_series = macd_series.ewm(span=9, adjust=False).mean()

            rsi = rsi_series.iloc[-1]
            macd = macd_series.iloc[-1]
            signal = signal_series.iloc[-1]

            if pd.isna(rsi) or pd.isna(macd) or pd.isna(signal):
                continue

            atual = {
                "rsi": float(rsi),
                "macd": float(macd),
                "signal": float(signal)
            }

            precos[t] = float(close.iloc[-1])
            indicadores[t] = atual

            alerta = None
            if atual["rsi"] < 30 and atual["macd"] > atual["signal"]:
                alerta = f"🟢 Alerta de COMPRA em {nome}"
            elif atual["rsi"] > 70 and atual["macd"] < atual["signal"]:
                alerta = f"🔴 Alerta de VENDA em {nome}"

            if alerta and ALERTAS.get(t) != alerta:
                send_telegram(alerta)
                ALERTAS[t] = alerta

        except Exception as e:
            send_telegram(f"⚠️ Erro analisando {t}: {e}")

def atualizar():
    while True:
        analisar()
        time.sleep(60 if DEBUG else 3600)

@app.route("/")
def home():
    return render_template_string(TEMPLATE, precos=precos, ind=indicadores, nomes=TICKERS, alertas=ALERTAS)

TEMPLATE = """ 
<html><head><title>Status CriptoBot</title></head>
<body style="font-family:sans-serif;padding:20px;">
<h1>FeOliCryptoBot - Painel</h1>
<table border="1" cellpadding="10">
    <tr><th>Cripto</th><th>Preço Atual</th><th>RSI</th><th>MACD</th><th>Signal</th><th>Tendência</th><th>Último Alerta</th></tr>
    {% for k,v in precos.items() %}
    <tr>
        <td>{{ nomes[k] }}</td>
        <td>${{ '%.2f' % v }}</td>
        <td>{{ '%.2f' % ind[k]['rsi'] }}</td>
        <td>{{ '%.4f' % ind[k]['macd'] }}</td>
        <td>{{ '%.4f' % ind[k]['signal'] }}</td>
        <td>
            {% if ind[k]['macd'] > ind[k]['signal'] %}
                <span style="color:green;">&uarr; Alta</span>
            {% elif ind[k]['macd'] < ind[k]['signal'] %}
                <span style="color:red;">&darr; Baixa</span>
            {% else %}
                &harr; Neutro
            {% endif %}
        </td>
        <td>{{ alertas.get(k, '—') }}</td>
    </tr>
    {% endfor %}
</table>

<div style="margin-top:20px; font-size:14px; padding:10px; border:1px solid #ccc; background:#f9f9f9;">
    <strong>📘 Legenda dos Alertas:</strong><br>
    🟢 <strong>Alerta de COMPRA</strong>: RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal<br>
    🔴 <strong>Alerta de VENDA</strong>: RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal
</div>

<p style="margin-top:10px;font-size:0.9em;color:gray;">Atualizado a cada minuto (modo debug)</p>
</body></html>
"""

if __name__ == "__main__":
    threading.Thread(target=atualizar, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
