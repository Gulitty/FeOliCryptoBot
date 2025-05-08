from flask import Flask, render_template
import requests
import os
import threading
import time
import telegram

app = Flask(__name__)

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Lista de criptos e seus IDs no CoinGecko
CRYPTO_IDS = {
    "bitcoin": "bitcoin",
    "ethereum": "ethereum",
    "solana": "solana"
}

# Armazena último alerta enviado
last_alerts = {}

def fetch_crypto_data():
    url = "https://api.coingecko.com/api/v3/simple/price"
    ids = ",".join(CRYPTO_IDS.values())
    params = {
        "ids": ids,
        "vs_currencies": "usd"
    }
    try:
        response = requests.get(url, params=params).json()
        return {
            name: {
                "price": float(response.get(gecko_id, {}).get("usd", 0)),
                "rsi": 30,
                "macd": 1.0,
                "signal": 3.0
            }
            for name, gecko_id in CRYPTO_IDS.items()
        }
    except Exception as e:
        print("Erro ao buscar preços:", e)
        return {}

def calcular_tendencia(rsi, macd, signal):
    if macd > signal and 40 <= rsi <= 60:
        return "compra"
    elif macd < signal or rsi > 70 or rsi < 30:
        return "venda"
    else:
        return "neutra"

def send_telegram_alert(name, trend):
    global last_alerts
    if name not in last_alerts or last_alerts[name] != trend:
        emoji = {"compra": "🟢", "venda": "🔴", "neutra": "🟠"}[trend]
        mensagem = f"{emoji} Alerta para {name.upper()}: {trend.upper()}"
        try:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensagem)
            last_alerts[name] = trend
        except Exception as e:
            print("Erro no envio do alerta:", e)

@app.route("/")
def index():
    data = fetch_crypto_data()
    for name, value in data.items():
        rsi = value["rsi"]
        macd = value["macd"]
        signal = value["signal"]
        trend = calcular_tendencia(rsi, macd, signal)
        value["trend"] = trend
        send_telegram_alert(name, trend)
    return render_template("index.html", cryptos=data)

def bot_loop():
    while True:
        fetch_crypto_data()
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)