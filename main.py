
import yfinance as yf
import pandas as pd
import time
import requests
from keep_alive import keep_alive
import os

TOKEN = "7733542207:AAEgogN0zgimnJEo1Q3vNaQX6Ayc7tpHF_s"
CHAT_ID = "6290071192"

cryptos = {
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum',
    'SOL-USD': 'Solana'
}

# Armazena os últimos alertas para não repetir
ultimo_alerta = {}

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
    df = yf.download(ticker, interval="1h", period="7d")
    if df.empty:
        return

    df['RSI'] = get_rsi(df)
    df['MACD'], df['Signal'] = get_macd(df)

    atual = df.iloc[-1]
    anterior = df.iloc[-2]

    nome = cryptos[ticker]
    preco = atual['Close']
    rsi = atual['RSI']
    macd = atual['MACD']
    signal = atual['Signal']

    msg = None
    chave = f"{ticker}_compra" if rsi < 30 and anterior['MACD'] < anterior['Signal'] and macd > signal else f"{ticker}_venda" if rsi > 70 and anterior['MACD'] > anterior['Signal'] and macd < signal else None

    if chave:
        if ultimo_alerta.get(ticker) != chave:
            tipo = "🟢 COMPRA" if "compra" in chave else "🔴 VENDA"
            msg = f"{tipo} sinalizado para {nome}\nPreço: ${preco:.2f}\nRSI: {rsi:.2f}\nMACD: {macd:.4f} | Signal: {signal:.4f}"
            ultimo_alerta[ticker] = chave
            send_telegram(msg)

# Iniciar servidor Flask (caso queira usar UptimeRobot)
keep_alive()

# Loop principal
while True:
    for ativo in cryptos.keys():
        try:
            analisar(ativo)
        except Exception as erro:
            send_telegram(f"⚠️ Erro analisando {ativo}: {erro}")
    time.sleep(3600)
