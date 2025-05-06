from flask import Flask, render_template_string
import pandas as pd
import requests
import time

app = Flask(__name__)

TICKERS = {
    'BTCUSDT': 'Bitcoin',
    'ETHUSDT': 'Ethereum',
    'SOLUSDT': 'Solana'
}

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial; padding: 20px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 40px; }
        th, td { border: 1px solid #ccc; padding: 10px; text-align: center; }
        th { background-color: #f2f2f2; font-size: 18px; }
        .up { color: green; font-weight: bold; }
        .down { color: red; font-weight: bold; }
        .legend { background: #f7f7f7; padding: 20px; border-radius: 10px; }
        .dot-up { height: 15px; width: 15px; background-color: green; border-radius: 50%; display: inline-block; }
        .dot-down { height: 15px; width: 15px; background-color: red; border-radius: 50%; display: inline-block; }
    </style>
</head>
<body>
    <h1>FeOliCryptoBot - Painel</h1>
    <table>
        <tr>
            <th>Cripto</th><th>Preço Atual</th><th>RSI</th><th>MACD</th><th>Signal</th><th>Tendência</th><th>Último Alerta</th>
        </tr>
        {% for t in nomes %}
        <tr>
            <td>{{ nomes[t] }}</td>
            <td>${{ precos[t] }}</td>
            <td>{{ ind[t]['rsi'] }}</td>
            <td>{{ ind[t]['macd'] }}</td>
            <td>{{ ind[t]['signal'] }}</td>
            <td>{{ ind[t]['tendencia'] }}</td>
            <td>{{ alertas[t] }}</td>
        </tr>
        {% endfor %}
    </table>

    <div class="legend">
        <h3>📘 Legenda dos Alertas:</h3>
        <p><span class="dot-up"></span> <strong>Alerta de COMPRA:</strong> RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal</p>
        <p><span class="dot-down"></span> <strong>Alerta de VENDA:</strong> RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal</p>
    </div>

    <p style="color:gray;">Atualizado a cada minuto (modo debug)</p>
</body>
</html>
"""

def get_binance_klines(symbol, interval='1h', limit=100):
    url = f"https://api.binance.com/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    response = requests.get(url, params=params)
    data = response.json()

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError(f"Nenhum dado retornado da Binance para {symbol}")

    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    return df

def calcular_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calcular_macd(df):
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

@app.route('/')
def home():
    precos = {}
    indicadores = {}
    alertas = {}

    for ticker in TICKERS:
        try:
            df = get_binance_klines(ticker)
            if df.empty:
                raise ValueError("DataFrame vazio")

            rsi_series = calcular_rsi(df)
            macd_series, signal_series = calcular_macd(df)

            rsi = round(rsi_series.iloc[-1], 2)
            macd = round(macd_series.iloc[-1], 4)
            signal = round(signal_series.iloc[-1], 4)
            preco = round(df['close'].iloc[-1], 2)

            if macd > signal:
                tendencia = '<span class="up">▲ Alta</span>'
            else:
                tendencia = '<span class="down">▼ Baixa</span>'

            # Alertas
            alerta = '—'
            if rsi < 30 and macd > signal:
                alerta = '🟢 Compra'
            elif rsi > 70 and macd < signal:
                alerta = '🔴 Venda'

            precos[ticker] = preco
            indicadores[ticker] = {
                'rsi': rsi,
                'macd': macd,
                'signal': signal,
                'tendencia': tendencia
            }
            alertas[ticker] = alerta

        except Exception as e:
            precos[ticker] = 0.00
            indicadores[ticker] = {
                'rsi': 0.00,
                'macd': 0.0000,
                'signal': 0.0000,
                'tendencia': '<span class="down">▼ Erro</span>'
            }
            alertas[ticker] = f'⚠️ Erro: {str(e)}'

    return render_template_string(TEMPLATE, precos=precos, ind=indicadores, nomes=TICKERS, alertas=alertas)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
