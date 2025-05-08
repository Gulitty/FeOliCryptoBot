import os
import requests
import pandas as pd
import numpy as np
from flask import Flask, render_template
import telegram

# Variáveis de ambiente (no Render)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

# Lista de criptos a monitorar
CRYPTOS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL"
}

# Estado anterior para evitar alertas repetidos
last_signals = {}

# Função para obter dados históricos simulados (CoinGecko não oferece históricos longos via API gratuita)
def get_mock_data():
    np.random.seed(0)
    data = np.cumsum(np.random.randn(100)) + 1000
    return pd.Series(data)

# RSI
def compute_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# MACD e Signal
def compute_macd(prices):
    exp1 = prices.ewm(span=12, adjust=False).mean()
    exp2 = prices.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

# Obter preço atual da CoinGecko
def get_current_price(crypto_id):
    try:
        response = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price",
            params={"ids": crypto_id, "vs_currencies": "usd"},
            timeout=10
        )
        data = response.json()
        return data[crypto_id]["usd"]
    except:
        return None

# Verifica o tipo de sinal
def check_signal(rsi, macd, signal):
    if macd > signal and 40 <= rsi <= 60:
        return "compra"
    elif macd < signal or rsi >= 70 or rsi <= 30:
        return "venda"
    else:
        return "neutro"

# Enviar alerta apenas se houver mudança
def send_telegram_alert(crypto, signal_text):
    global last_signals
    if last_signals.get(crypto) != signal_text:
        last_signals[crypto] = signal_text
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        mensagem = f"📣 Sinal para {crypto.upper()}: {signal_text.upper()}"
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensagem)

@app.route("/")
def index():
    data = {}
    for crypto_id, symbol in CRYPTOS.items():
        prices = get_mock_data()
        rsi = compute_rsi(prices).iloc[-1]
        macd, signal = compute_macd(prices)
        macd_val = macd.iloc[-1]
        signal_val = signal.iloc[-1]
        price = get_current_price(crypto_id)

        if price is None:
            continue

        tipo_sinal = check_signal(rsi, macd_val, signal_val)
        send_telegram_alert(symbol, tipo_sinal)

        data[symbol] = {
            "price": price,
            "rsi": rsi,
            "macd": macd_val,
            "signal": signal_val,
            "alert": tipo_sinal
        }

    return render_template("index.html", cryptos=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)