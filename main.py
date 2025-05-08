import os
import requests
from flask import Flask, render_template
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COINS = ["bitcoin", "ethereum", "solana"]
SYMBOLS = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}

def fetch_data():
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(COINS)}&vs_currencies=usd"
    response = requests.get(url)
    prices = response.json()

    indicadores = {}
    for coin in COINS:
        price = prices.get(coin, {}).get("usd", 0)
        rsi = round(50 + (price % 20 - 10), 2)
        macd = round((price % 5) - 2.5, 2)
        signal = round(macd - (macd * 0.8), 2)
        tendencia = "📈 Alta" if macd > signal else "📉 Baixa"

        indicadores[coin] = {
            "price": price,
            "rsi": rsi,
            "macd": macd,
            "signal": signal,
            "tendencia": tendencia
        }

    return indicadores

def formatar_preco(valor):
    return f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def enviar_alertas(indicadores):
    if not TOKEN or not CHAT_ID:
        return

    for coin, data in indicadores.items():
        if data["macd"] > data["signal"]:
            texto = f"🚨 COMPRA: {SYMBOLS[coin]} com MACD acima do Signal!\nRSI: {data['rsi']}"
        elif data["macd"] < data["signal"]:
            texto = f"⚠️ VENDA: {SYMBOLS[coin]} com MACD abaixo do Signal!\nRSI: {data['rsi']}"
        else:
            texto = f"🔍 OBSERVAÇÃO: {SYMBOLS[coin]} está neutro.\nRSI: {data['rsi']}"
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={texto}")

@app.route("/")
def index():
    dados = fetch_data()
    enviar_alertas(dados)

    return render_template("index.html",
        btc=formatar_preco(dados["bitcoin"]["price"]),
        eth=formatar_preco(dados["ethereum"]["price"]),
        sol=formatar_preco(dados["solana"]["price"]),
        btc_data=dados["bitcoin"],
        eth_data=dados["ethereum"],
        sol_data=dados["solana"]
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5055))
    app.run(debug=True, port=port)