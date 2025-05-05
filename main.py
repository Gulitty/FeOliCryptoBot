
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__)

TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin: 40px; }
        table { border-collapse: collapse; width: 90%; margin: auto; }
        th, td { border: 1px solid #999; padding: 8px; }
        th { background: #eee; font-size: 20px; }
        .green { color: green; font-weight: bold; }
        .red { color: red; font-weight: bold; }
        .emoji { font-size: 18px; }
        .legend { margin-top: 30px; background: #f5f5f5; padding: 20px; border-radius: 8px; width: 90%; margin: 30px auto; }
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
        {% for nome in nomes %}
        <tr>
            <td>{{ nome }}</td>
            <td>${{ '%.2f' % precos[nome] }}</td>
            <td>{{ '%.2f' % ind[nome]['RSI'] }}</td>
            <td>{{ '%.4f' % ind[nome]['MACD'] }}</td>
            <td>{{ '%.4f' % ind[nome]['Signal'] }}</td>
            <td class="{{ 'green' if ind[nome]['Trend'] == 'Alta' else 'red' }}">
                <span class="emoji">{{ '▲' if ind[nome]['Trend'] == 'Alta' else '▼' }}</span>
                {{ ind[nome]['Trend'] }}
            </td>
            <td>{{ alertas.get(nome, '—') }}</td>
        </tr>
        {% endfor %}
    </table>

    <div class="legend">
        <h3>📘 Legenda dos Alertas:</h3>
        <p>🟢 <b>Alerta de COMPRA</b>: RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal</p>
        <p>🔴 <b>Alerta de VENDA</b>: RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal</p>
    </div>

    <p style="color: gray;">Atualizado a cada minuto (modo debug)</p>
</body>
</html>
'''

TICKERS = {
    'Bitcoin': 'BTC-USD',
    'Ethereum': 'ETH-USD',
    'Solana': 'SOL-USD'
}

def calcular_indicadores(df):
    close = df['Close']

    rsi = calcular_rsi(close)
    macd_line, signal_line = calcular_macd(close)

    if macd_line[-1] > signal_line[-1]:
        trend = 'Alta'
    else:
        trend = 'Baixa'

    return {
        'RSI': rsi.iloc[-1],
        'MACD': macd_line.iloc[-1],
        'Signal': signal_line.iloc[-1],
        'Trend': trend
    }

def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calcular_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

@app.route('/')
def home():
    precos = {}
    indicadores = {}
    alertas = {}

    for nome, ticker in TICKERS.items():
        try:
            df = yf.download(ticker, period='3mo', interval='1d', progress=False)
            if df.empty or len(df) < 35:
                raise ValueError("Dados insuficientes para análise")

            precos[nome] = float(df['Close'].iloc[-1])
            indicadores[nome] = calcular_indicadores(df)

            rsi = indicadores[nome]['RSI']
            macd = indicadores[nome]['MACD']
            signal = indicadores[nome]['Signal']

            if rsi < 30 and macd > signal:
                alertas[nome] = '🟢 COMPRA'
            elif rsi > 70 and macd < signal:
                alertas[nome] = '🔴 VENDA'

        except Exception as e:
            precos[nome] = 0.0
            indicadores[nome] = {'RSI': 0.0, 'MACD': 0.0, 'Signal': 0.0, 'Trend': 'Erro'}
            alertas[nome] = f"⚠️ Erro: {str(e)}"

    return render_template_string(TEMPLATE, precos=precos, ind=indicadores, nomes=TICKERS, alertas=alertas)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
