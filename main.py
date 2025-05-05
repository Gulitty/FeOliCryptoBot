import requests
from flask import Flask, render_template_string
import pandas as pd

app = Flask(__name__)

TICKERS = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana"
}

def get_binance_klines(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    return df

def calculate_indicators(df):
    df["EMA12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

@app.route("/")
def home():
    dados = []
    for symbol, name in TICKERS.items():
        try:
            df = get_binance_klines(symbol)
            df = calculate_indicators(df)
            last = df.iloc[-1]

            price = round(df['close'].iloc[-1], 2)
            rsi = round(last["RSI"], 2)
            macd = round(last["MACD"], 4)
            signal = round(last["Signal"], 4)

            tendencia = "▲ Alta" if macd > signal else "▼ Baixa"

            dados.append({
                "nome": name,
                "preco": f"${price}",
                "rsi": rsi,
                "macd": macd,
                "signal": signal,
                "tendencia": tendencia,
                "alerta": "—"
            })
        except Exception as e:
            dados.append({
                "nome": name,
                "preco": "$0.00",
                "rsi": 0.00,
                "macd": 0.0000,
                "signal": 0.0000,
                "tendencia": "▼ Erro",
                "alerta": f"⚠️ Erro: {str(e)}"
            })

    return render_template_string(TEMPLATE, dados=dados)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; }
        h1 { text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ccc; padding: 10px; text-align: center; }
        th { background-color: #f2f2f2; font-size: 18px; }
        .legenda { margin-top: 40px; padding: 20px; background-color: #f9f9f9; border-radius: 8px; }
        .legenda h3 { margin-bottom: 10px; }
        .verde { color: green; font-weight: bold; }
        .vermelho { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <h1>FeOliCryptoBot - Painel</h1>
    <table>
        <tr>
            <th>Cripto</th>
            <th>Preço Atual</th>
            <th>RSI</th>
            <th>MACD</th>
            <th>Signal</th>
            <th>Tendência</th>
            <th>Último Alerta</th>
        </tr>
        {% for d in dados %}
        <tr>
            <td>{{ d.nome }}</td>
            <td>{{ d.preco }}</td>
            <td>{{ d.rsi }}</td>
            <td>{{ d.macd }}</td>
            <td>{{ d.signal }}</td>
            <td>{{ d.tendencia }}</td>
            <td>{{ d.alerta }}</td>
        </tr>
        {% endfor %}
    </table>
    <div class="legenda">
        <h3>📘 Legenda dos Alertas:</h3>
        <p class="verde">🟢 Alerta de COMPRA</p>
        <p class="vermelho">🔴 Alerta de VENDA</p>
    </div>
    <p style="text-align:center; color:gray;">Atualizado a cada minuto (modo debug)</p>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)