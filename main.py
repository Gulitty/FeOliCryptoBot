from flask import Flask, render_template_string
import requests
import pandas as pd

app = Flask(__name__)

PAIRS = {
    "Bitcoin": "BTCUSDT",
    "Ethereum": "ETHUSDT",
    "Solana": "SOLUSDT"
}

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 30px; background: #f7f7f7; color: #222; }
        h1 { text-align: center; }
        table { border-collapse: collapse; margin: auto; width: 90%; }
        th, td { border: 1px solid #ccc; padding: 10px; text-align: center; }
        th { background-color: #eee; }
        .up { color: green; font-weight: bold; }
        .down { color: red; font-weight: bold; }
        .error { color: orange; font-weight: bold; }
        .legenda { background: #f3f3f3; padding: 15px; border-radius: 10px; width: 85%; margin: 30px auto; }
        .footer { text-align: center; font-size: 14px; color: gray; margin-top: 20px; }
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
        {% for nome, dados in info.items() %}
        <tr>
            <td>{{ nome }}</td>
            <td>${{ '%.2f'|format(dados['preco']) }}</td>
            <td>{{ '%.2f'|format(dados['rsi']) }}</td>
            <td>{{ '%.4f'|format(dados['macd']) }}</td>
            <td>{{ '%.4f'|format(dados['signal']) }}</td>
            <td>
                {% if dados['erro'] %}
                    <span class="error">—</span>
                {% elif dados['tendencia'] == 'Alta' %}
                    <span class="up">▲ Alta</span>
                {% elif dados['tendencia'] == 'Baixa' %}
                    <span class="down">▼ Baixa</span>
                {% else %}
                    —
                {% endif %}
            </td>
            <td>
                {% if dados['erro'] %}
                    ⚠️ Erro: dados indisponíveis
                {% else %}
                    {{ dados['alerta'] or '—' }}
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>

    <div class="legenda">
        <p>📘 <strong>Legenda dos Alertas:</strong></p>
        <p>🟢 <strong>Alerta de COMPRA:</strong> RSI abaixo de 30 e MACD cruzando acima da Signal</p>
        <p>🔴 <strong>Alerta de VENDA:</strong> RSI acima de 70 e MACD cruzando abaixo da Signal</p>
    </div>

    <p class="footer">Atualizado a cada minuto (modo debug)</p>
</body>
</html>
"""

def get_binance_ohlc(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["close"] = pd.to_numeric(df["close"])
        return df
    except Exception:
        return pd.DataFrame()

def calcular_rsi(close, period=14):
    delta = close.diff()
    ganho = delta.where(delta > 0, 0).rolling(window=period).mean()
    perda = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = ganho / perda
    return 100 - (100 / (1 + rs))

def calcular_macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

@app.route("/")
def home():
    info = {}
    for nome, symbol in PAIRS.items():
        try:
            df = get_binance_ohlc(symbol)
            if df.empty or len(df) < 50:
                raise ValueError("Dados insuficientes")

            close = df["close"]

            rsi = calcular_rsi(close).iloc[-1]
            macd_series, signal_series = calcular_macd(close)
            macd = macd_series.iloc[-1]
            signal = signal_series.iloc[-1]
            preco = float(close.iloc[-1])

            if rsi < 30 and macd > signal:
                alerta = "🟢 Alerta de COMPRA"
            elif rsi > 70 and macd < signal:
                alerta = "🔴 Alerta de VENDA"
            else:
                alerta = None

            tendencia = "Alta" if macd > signal else "Baixa"

            info[nome] = {
                "preco": preco,
                "rsi": rsi,
                "macd": macd,
                "signal": signal,
                "tendencia": tendencia,
                "alerta": alerta,
                "erro": False
            }
        except Exception as e:
            info[nome] = {
                "preco": 0.0,
                "rsi": 0.0,
                "macd": 0.0,
                "signal": 0.0,
                "tendencia": None,
                "alerta": None,
                "erro": True
            }

    return render_template_string(TEMPLATE, info=info)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)