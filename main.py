from flask import Flask, render_template
import requests
import pandas as pd
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CRYPTOS = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'solana': 'SOL'
}

def format_price(price):
    return f"${price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_price(coin):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        response = requests.get(url)
        return response.json()[coin]['usd']
    except:
        return 0.0

def get_mock_indicators(symbol):
    # MOCKS — Substitua futuramente por dados reais
    return {
        "RSI": round(30 + hash(symbol) % 40, 2),
        "MACD": round(hash(symbol + "macd") % 100 - 50, 2),
        "Signal": round(hash(symbol + "signal") % 100 - 50, 2),
        "Tendência": "Compra" if hash(symbol) % 2 == 0 else "Venda"
    }

def send_alert(crypto, price, tendencia):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        msg = f"📊 Alerta para {crypto.upper()}:\nPreço: {format_price(price)}\nTendência: {tendencia}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        requests.post(url, data=data)

@app.route("/")
def index():
    data = []

    for coin_id, symbol in CRYPTOS.items():
        price = get_price(coin_id)
        indicators = get_mock_indicators(symbol)
        data.append({
            "Cripto": symbol,
            "Preço Atual": format_price(price),
            "RSI": indicators["RSI"],
            "MACD": indicators["MACD"],
            "Signal": indicators["Signal"],
            "Tendência": indicators["Tendência"]
        })

        # Enviar alerta se for compra ou venda
        if indicators["Tendência"] in ["Compra", "Venda"]:
            send_alert(symbol, price, indicators["Tendência"])

    return render_template("index.html", cryptos=data)

if __name__ == "__main__":
    import os
port = int(os.environ.get("PORT", 5000))
app.run(debug=True, host="0.0.0.0", port=port)
