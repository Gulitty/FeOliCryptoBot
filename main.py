
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
        r = requests.post(url, json=payload)
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

            rsi = 100 - (100 / (1 + (close.pct_change().rolling(14).mean() /
                                     close.pct_change().rolling(14).std())))
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()

            atual = {
                "rsi": rsi.iloc[-1],
                "macd": macd.iloc[-1],
                "signal": signal.iloc[-1]
            }

            precos[t] = float(close.iloc[-1])
            indicadores[t] = atual

            # ALERTAS
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

TEMPLATE = """" + legenda_template + """""

if __name__ == "__main__":
    threading.Thread(target=atualizar, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
