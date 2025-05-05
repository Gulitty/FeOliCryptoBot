from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import requests
import os
import datetime

app = Flask(__name__)

TICKERS = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD"
}

ALERTAS = {nome: "—" for nome in TICKERS}
indicadores = {nome: {"RSI": 0, "MACD": 0, "SIGNAL": 0, "TENDENCIA": "—"} for nome in TICKERS}
precos = {nome: 0 for nome in TICKERS}

def calcular_indicadores(data):
    close = data['Close']
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()

    return rsi, macd, signal

def buscar_preco_binance(ticker_binance):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={ticker_binance}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return float(response.json()['price'])
    except:
        return None
    return None

def atualizar():
    global precos, indicadores, ALERTAS

    for nome, ticker in TICKERS.items():
        try:
            data = yf.download(ticker, period="15d", interval="1h", progress=False)
            if data.empty:
                raise ValueError("Dados do Yahoo vazios")

            rsi, macd, signal = calcular_indicadores(data)
            atual = pd.DataFrame({
                'RSI': [rsi.iloc[-1]],
                'MACD': [macd.iloc[-1]],
                'SIGNAL': [signal.iloc[-1]]
            })

            preco = float(data['Close'].iloc[-1])
            precos[nome] = preco
            indicadores[nome] = {
                "RSI": round(atual['RSI'].iloc[0], 2),
                "MACD": round(atual['MACD'].iloc[0], 4),
                "SIGNAL": round(atual['SIGNAL'].iloc[0], 4),
                "TENDENCIA": "🔻 Baixa" if atual['MACD'].iloc[0] < atual['SIGNAL'].iloc[0] else "🔺 Alta"
            }

            rsi_v = atual['RSI'].iloc[0]
            macd_v = atual['MACD'].iloc[0]
            sig_v = atual['SIGNAL'].iloc[0]

            if rsi_v < 30 and macd_v > sig_v:
                ALERTAS[nome] = "🟢 Alerta de COMPRA"
            elif rsi_v > 70 and macd_v < sig_v:
                ALERTAS[nome] = "🔴 Alerta de VENDA"
            else:
                ALERTAS[nome] = "—"

        except Exception as e:
            binance_symbol = ticker.replace("-USD", "USDT").replace("-", "")
            preco_binance = buscar_preco_binance(binance_symbol)

            precos[nome] = preco_binance if preco_binance else 0
            indicadores[nome] = {"RSI": 0, "MACD": 0, "SIGNAL": 0, "TENDENCIA": "🔻 Erro"}
            ALERTAS[nome] = f"⚠️ Erro: {str(e).splitlines()[0]}"

@app.route("/")
def home():
    atualizar()
    return render_template_string(TEMPLATE, precos=precos, ind=indicadores, nomes=TICKERS, alertas=ALERTAS)

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>FeOliCryptoBot - Painel</title>
</head>
<body style="font-family: Arial; margin: 40px;">
    <h1 style="text-align:center;">FeOliCryptoBot - Painel</h1>
    <table border="1" cellspacing="0" cellpadding="8" style="margin:auto; border-collapse: collapse;">
        <tr style="background-color:#eee;">
            <th>Cripto</th>
            <th>Preço Atual</th>
            <th>RSI</th>
            <th>MACD</th>
            <th>Signal</th>
            <th>Tendência</th>
            <th>Último Alerta</th>
        </tr>
        {% for nome in nomes %}
        <tr>
            <td>{{ nome }}</td>
            <td>${{ '%.2f' % precos[nome] }}</td>
            <td>{{ '%.2f' % ind[nome]["RSI"] }}</td>
            <td>{{ '%.4f' % ind[nome]["MACD"] }}</td>
            <td>{{ '%.4f' % ind[nome]["SIGNAL"] }}</td>
            <td><strong>{{ ind[nome]["TENDENCIA"] }}</strong></td>
            <td>{{ alertas[nome] }}</td>
        </tr>
        {% endfor %}
    </table>
    <div style="margin:40px auto; width:80%; background:#f7f7f7; padding:20px; border-radius:8px;">
        <h3>📘 Legenda dos Alertas:</h3>
        <p>🟢 <strong>Alerta de COMPRA</strong>: RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal</p>
        <p>🔴 <strong>Alerta de VENDA</strong>: RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal</p>
    </div>
    <p style="text-align:center; color:gray;">Atualizado a cada minuto (modo debug)</p>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
