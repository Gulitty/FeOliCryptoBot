import requests
import pandas as pd
import numpy as np
from flask import Flask, render_template
import asyncio
from telegram import Bot

app = Flask(__name__)

TELEGRAM_TOKEN = 'SUA_TOKEN_AQUI'
TELEGRAM_CHAT_ID = 'SEU_CHAT_ID_AQUI'
bot = Bot(token=TELEGRAM_TOKEN)

cryptos = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'solana': 'SOL'
}

ultimo_alerta = {ticker: '—' for ticker in cryptos.values()}

def fetch_price_history(crypto_id):
    url = f'https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart?vs_currency=usd&days=2&interval=hourly'
    response = requests.get(url)
    data = response.json()
    return [price[1] for price in data.get("prices", [])][-26:]

def calcular_rsi(precos, periodo=14):
    df = pd.Series(precos)
    delta = df.diff()
    ganho = delta.where(delta > 0, 0)
    perda = -delta.where(delta < 0, 0)
    media_ganho = ganho.rolling(window=periodo).mean()
    media_perda = perda.rolling(window=periodo).mean()
    rs = media_ganho / media_perda
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

def calcular_macd(precos):
    df = pd.Series(precos)
    ema12 = df.ewm(span=12, adjust=False).mean()
    ema26 = df.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd.iloc[-1], signal.iloc[-1]

def analisar_tendencia(rsi, macd, signal):
    if macd > signal and 40 <= rsi <= 60:
        return 'compra'
    elif macd < signal or rsi > 70 or rsi < 30:
        return 'venda'
    return 'neutra'

async def enviar_alerta(nome, tendencia):
    global ultimo_alerta
    if tendencia != ultimo_alerta[nome]:
        emoji = {'compra': '🟢', 'venda': '🔴', 'neutra': '🔶'}[tendencia]
        texto = f'{emoji} Alerta de {tendencia.upper()} para {nome}'
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=texto)
        ultimo_alerta[nome] = tendencia

@app.route('/')
def index():
    data = {}
    for nome, ticker in cryptos.items():
        try:
            precos = fetch_price_history(nome)
            rsi = calcular_rsi(precos)
            macd, signal = calcular_macd(precos)
            preco_atual = precos[-1] if precos else 0
            tendencia = analisar_tendencia(rsi, macd, signal)

            # Enviar alerta se necessário
            asyncio.run(enviar_alerta(ticker, tendencia))

            data[ticker] = {
                'price': preco_atual,
                'rsi': round(rsi, 2),
                'macd': round(macd, 4),
                'signal': round(signal, 4),
                'tendencia': tendencia,
                'alerta': ultimo_alerta[ticker]
            }
        except Exception:
            data[ticker] = {
                'price': 0,
                'rsi': 0,
                'macd': 0,
                'signal': 0,
                'tendencia': 'neutra',
                'alerta': '—'
            }

    return render_template('index.html', cryptos=data)

if __name__ == '__main__':
    app.run(debug=True, port=10000)