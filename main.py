import os
import requests
import pandas as pd
from flask import Flask, render_template
from telegram import Bot
import asyncio

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

CRYPTOS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL"
}

def fetch_data():
    try:
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={",".join(CRYPTOS.keys())}&vs_currencies=usd'
        r = requests.get(url)
        prices = r.json()

        data = {}

        for key, symbol in CRYPTOS.items():
            price = prices.get(key, {}).get("usd")

            if price is None:
                print(f"[Erro] Não foi possível obter o preço de {key}.")
                continue

            rsi = round(30 + (price % 40), 2)
            macd = round(price % 5, 4)
            signal = round((price / 2) % 5, 4)

            if macd > signal and 40 <= rsi <= 60:
                tendencia = "🟢 Compra"
                alerta = "ALERTA DE COMPRA"
                asyncio.run(send_alert(symbol, price, tendencia))
            elif macd < signal or rsi > 70 or rsi < 30:
                tendencia = "🔴 Venda"
                alerta = "ALERTA DE VENDA"
                asyncio.run(send_alert(symbol, price, tendencia))
            else:
                tendencia = "🔶 Neutra"
                alerta = ""

            data[symbol] = {
                "price": price,
                "rsi": rsi,
                "macd": macd,
                "signal": signal,
                "tendencia": tendencia,
                "alerta": alerta
            }

        return data

    except Exception as e:
        print("Erro ao buscar dados:", e)
        return {}

async def send_alert(symbol, price, tendencia):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    mensagem = f"{tendencia} detectado para {symbol} — ${price:,.2f}"
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensagem)

@app.route("/")
def index():
    data = fetch_data()
    return render_template("index.html", cryptos=data)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)