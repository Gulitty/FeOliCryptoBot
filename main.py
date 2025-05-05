
import yfinance as yf
import pandas as pd
import time
import requests
import threading
from flask import Flask, render_template_string

TOKEN = "7733542207:AAEgogN0zgimnJEo1Q3vNaQX6Ayc7tpHF_s"
CHAT_ID = "6290071192"

cryptos = {
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum',
    'SOL-USD': 'Solana'
}

ultimo_alerta = {}
precos_atuais = {}
indicadores = {}

def get_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_macd(data):
    short_ema = data['Close'].ewm(span=12, adjust=False).mean()
    long_ema = data['Close'].ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Erro ao enviar mensagem:", e)

def analisar(ticker):
    df = yf.download(ticker, interval="1h", period="7d", progress=False)
    if df.empty:
        return

    df['RSI'] = get_rsi(df)
    df['MACD'], df['Signal'] = get_macd(df)

    atual = df.iloc[-1]
    anterior = df.iloc[-2]

    nome = cryptos[ticker]
    preco = atual['Close'].item()
    rsi = atual['RSI'].item()
    macd = atual['MACD'].item()
    signal = atual['Signal'].item()

    precos_atuais[ticker] = preco
    indicadores[ticker] = {"rsi": rsi, "macd": macd, "signal": signal}

    chave = f"{ticker}_compra" if rsi < 30 and anterior['MACD'] < anterior['Signal'] and macd > signal else f"{ticker}_venda" if rsi > 70 and anterior['MACD'] > anterior['Signal'] and macd < signal else None

    if chave:
        if ultimo_alerta.get(ticker) != chave:
            tipo = "🟢 COMPRA" if "compra" in chave else "🔴 VENDA"
            msg = f"{tipo} sinalizado para {nome}\nPreço: ${preco:.2f}\nRSI: {rsi:.2f}\nMACD: {macd:.4f} | Signal: {signal:.4f}"
            ultimo_alerta[ticker] = chave
            send_telegram(msg)

# Flask App
app = Flask(__name__)

@app.route("/")
def painel():
    html = '''
    <html><head><title>Status CriptoBot</title></head>
    <body style="font-family:sans-serif;padding:20px;">
    <h1>FeOliCryptoBot - Painel</h1>
    <table border="1" cellpadding="10">
        <tr><th>Cripto</th><th>Preço Atual</th><th>RSI</th><th>MACD</th><th>Último Alerta</th></tr>
        {% for k,v in precos.items() %}
        <tr>
            <td>{{ nomes[k] }}</td>
            <td>${{ '%.2f' % v }}</td>
            <td>{{ '%.2f' % ind[k]['rsi'] }}</td>
            <td>{{ '%.4f' % ind[k]['macd'] }}</td>
            <td>{{ alertas.get(k, '—') }}</td>
        </tr>
        {% endfor %}
    </table>
    <p style="margin-top:20px;font-size:0.9em;color:gray;">Atualizado a cada minuto (modo debug)</p>
    </body></html>
    '''
    return render_template_string(html, precos=precos_atuais, alertas=ultimo_alerta, nomes=cryptos, ind=indicadores)

def loop_principal():
    while True:
        for ativo in cryptos.keys():
            try:
                analisar(ativo)
            except Exception as erro:
                send_telegram(f"⚠️ Erro analisando {ativo}: {erro}")
        time.sleep(60)  # modo debug: 60 segundos

# Iniciar análise em thread separada
threading.Thread(target=loop_principal, daemon=True).start()

# Iniciar servidor Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
