
import yfinance as yf
import pandas as pd
import time
import requests
from keep_alive import keep_alive

TOKEN = "7733542207:AAEgogN0zgimnJEo1Q3vNaQX6Ayc7tpHF_s"
CHAT_ID = "6290071192"

cryptos = {
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum',
    'SOL-USD': 'Solana'
}

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
    requests.post(url, data=data)

def analyze_crypto(ticker):
    df = yf.download(ticker, interval="1h", period="7d")
    if df.empty:
        return

    df['RSI'] = get_rsi(df)
    df['MACD'], df['Signal'] = get_macd(df)

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    name = cryptos[ticker]
    price = latest['Close']
    rsi = latest['RSI']
    macd = latest['MACD']
    signal = latest['Signal']

    message = None

    if rsi < 30 and previous['MACD'] < previous['Signal'] and macd > signal:
        message = f"🟢 {name} em zona de COMPRA\nPreço: ${price:.2f}\nRSI: {rsi:.2f}\nMACD cruzou para cima!"
    elif rsi > 70 and previous['MACD'] > previous['Signal'] and macd < signal:
        message = f"🔴 {name} em zona de VENDA\nPreço: ${price:.2f}\nRSI: {rsi:.2f}\nMACD cruzou para baixo!"

    if message:
        send_telegram(message)

keep_alive()

while True:
    for ticker in cryptos.keys():
        try:
            analyze_crypto(ticker)
        except Exception as e:
            send_telegram(f"Erro ao analisar {ticker}: {e}")
    time.sleep(3600)
