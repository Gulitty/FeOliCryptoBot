
import requests
import pandas as pd
from flask import Flask, render_template_string

app = Flask(__name__)

TICKERS = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana"
}

def get_binance_klines(symbol, interval='1h', limit=100):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    df['close'] = pd.to_numeric(df['close'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_indicators(df):
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@app.route('/')
def home():
    precos = {}
    indicadores = {}
    alertas = {}
    for symbol, nome in TICKERS.items():
        try:
            df = get_binance_klines(symbol)
            df = calculate_indicators(df)
            atual = df.iloc[-1]
            preco = float(atual['close'])
            rsi = round(float(atual['RSI']), 2)
            macd = round(float(atual['MACD']), 4)
            signal = round(float(atual['Signal']), 4)

            tendencia = "Alta" if macd > signal else "Baixa"
            alerta = ""
            if rsi < 30 and macd > signal:
                alerta = "🔔 Alerta de COMPRA"
            elif rsi > 70 and macd < signal:
                alerta = "🔔 Alerta de VENDA"

            precos[symbol] = preco
            indicadores[symbol] = {
                "RSI": rsi,
                "MACD": macd,
                "Signal": signal,
                "Tendencia": tendencia
            }
            alertas[symbol] = alerta or "—"
        except Exception as e:
            precos[symbol] = 0
            indicadores[symbol] = {"RSI": 0, "MACD": 0, "Signal": 0, "Tendencia": "Erro"}
            alertas[symbol] = f"⚠️ Erro: {e}"

    TEMPLATE = '''
    <html>
    <head><meta charset="UTF-8"><title>FeOliCryptoBot</title></head>
    <body style="font-family:sans-serif;">
    <h1 style="text-align:center;">FeOliCryptoBot - Painel</h1>
    <table border="1" cellpadding="8" cellspacing="0" style="margin:auto;text-align:center;font-size:18px;">
        <tr style="background:#eee;font-weight:bold;">
            <td>Cripto</td><td>Preço Atual</td><td>RSI</td><td>MACD</td><td>Signal</td><td>Tendência</td><td>Último Alerta</td>
        </tr>
        {% for t, nome in nomes.items() %}
        <tr>
            <td>{{ nome }}</td>
            <td>${{ '%.2f' % precos[t] }}</td>
            <td>{{ '%.2f' % ind[t]['RSI'] }}</td>
            <td>{{ '%.4f' % ind[t]['MACD'] }}</td>
            <td>{{ '%.4f' % ind[t]['Signal'] }}</td>
            <td style="color:{{ 'green' if ind[t]['Tendencia']=='Alta' else 'red' }}">
                {{ '▲ Alta' if ind[t]['Tendencia']=='Alta' else '▼ Baixa' }}
            </td>
            <td>{{ alertas[t] }}</td>
        </tr>
        {% endfor %}
    </table>
    <div style="margin:40px auto;width:80%;padding:20px;background:#f8f8f8;border-radius:10px;">
        <p><strong>📘 Legenda dos Alertas:</strong></p>
        <p>🟢 <strong>Alerta de COMPRA</strong>: RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal</p>
        <p>🔴 <strong>Alerta de VENDA</strong>: RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal</p>
    </div>
    <p style="text-align:center;color:gray;">Atualizado a cada minuto (modo debug)</p>
    </body>
    </html>
    '''
    return render_template_string(TEMPLATE, precos=precos, ind=indicadores, nomes=TICKERS, alertas=alertas)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
