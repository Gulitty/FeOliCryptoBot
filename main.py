from flask import Flask, render_template
import requests
import time
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

cryptos = {
    "bitcoin": {"symbol": "BTC", "color": "🟡"},
    "ethereum": {"symbol": "ETH", "color": "🔵"},
    "solana": {"symbol": "SOL", "color": "🟣"},
}

def format_price(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_crypto_data():
    url = "https://api.coingecko.com/api/v3/simple/price"
    ids = ",".join(cryptos.keys())
    params = {"ids": ids, "vs_currencies": "usd"}
    try:
        response = requests.get(url, params=params, timeout=10)
        prices = response.json()
    except Exception as e:
        print("Erro ao buscar dados do CoinGecko:", e)
        prices = {}

    data = {}
    for name in cryptos:
        price = prices.get(name, {}).get("usd", 0)
        rsi = round(30 + (price % 20), 2)
        macd = round(1 + (price % 3), 2)
        signal = round(1 + ((price + 5) % 3), 2)
        tendencia = "🔺 Compra" if macd > signal and rsi < 30 else "🔻 Venda" if macd < signal and rsi > 70 else "🔸 Neutra"

        data[name] = {
            "preco": price,
            "preco_formatado": format_price(price),
            "rsi": rsi,
            "macd": macd,
            "signal": signal,
            "tendencia": tendencia,
            "color": cryptos[name]["color"],
            "symbol": cryptos[name]["symbol"],
        }

    return data

def enviar_alerta(criptomoeda, tendencia, preco_formatado):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    mensagem = f"🚨 Alerta de Tendência\n\n{criptomoeda.upper()} - {tendencia}\nPreço atual: {preco_formatado}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Erro ao enviar alerta para Telegram:", e)

@app.route("/")
def index():
    data = get_crypto_data()

    for nome, info in data.items():
        if info["tendencia"] in ["🔺 Compra", "🔻 Venda"]:
            enviar_alerta(info["symbol"], info["tendencia"], info["preco_formatado"])

    return render_template("index.html", cryptos=data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5055))
    app.run(host="0.0.0.0", port=port, debug=True)