import requests
import pandas as pd
import numpy as np
from flask import Flask, render_template_string
import os

app = Flask(__name__)

TICKERS = {
    'BTCUSDT': 'Bitcoin',
    'ETHUSDT': 'Ethereum',
    'SOLUSDT': 'Solana'
}

ALERTAS = {}

TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; }
        table { margin: auto; border-collapse: collapse; width: 90%; }
        th, td { border: 1px solid #888; padding: 10px; }
        th { background-color: #eee; }
        .alta { color: green; font-weight: bold; }
        .baixa { color: red; font-weight: bold; }
        .legenda { margin-top: 30px; padding: 20px; background: #f7f7f7; border-radius: 10px; display: inline-block; text-align: left; }
        .alerta-compra { color: green; font-weight: bold; }
        .alerta-venda { color: darkred; font-weight: bold; }
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
        {% for ticker, nome in nomes.items() %}
        <tr>
            <td>{{ nome }}</td>
            <td>${{ "%.2f"|format(precos[ticker]) }}</td>
            <td>{{ "%.2f"|format(ind[ticker]['rsi']) }}</td>
            <td>{{ "%.4f"|format(ind[ticker]['macd']) }}</td>
            <td>{{ "%.4f"|format(ind[ticker]['signal']) }}</td>
            <td class="{{ 'alta' if ind[ticker]['tendencia'] == 'Alta' else 'baixa' }}">
                {{ '▲ Alta' if ind[ticker]['tendencia'] == 'Alta' else '▼ Baixa' if ind[ticker]['tendencia'] == 'Baixa' else '—' }}
            </td>
            <td>{{ alertas.get(ticker, '—') }}</td>
        </tr>
        {% endfor %}
    </table>

    <div class="legenda">
        <h3>📘 Legenda dos Alertas:</h3>
        <p><span class="alerta-compra">🟢 Alerta de COMPRA:</span> RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal</p>
        <p><span class="alerta-venda">🔴 Alerta de VENDA:</span> RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal</p>
    </div>

    <p style="color: gray; margin-top: 30px;">Atualizado a cada minuto (modo debug)</p>
</body>
</html>
'''

def obter_dados_binance(ticker, intervalo='1h', limite=100):
    url = f'https://api.binance.com/api/v3/klines?symbol={ticker}&interval={intervalo}&limit={limite}'
    try:
        r = requests.get(url)
        r.raise_for_status()
        df = pd.DataFrame(r.json(), columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        return df[['close']]
    except Exception as e:
        print(f'Erro ao obter dados para {ticker}: {e}')
        return None

def calcular_indicadores(df):
    if df is None or df.empty or len(df) < 35:
        return {'rsi': 0.0, 'macd': 0.0, 'signal': 0.0, 'tendencia': 'Erro'}

    try:
        close = df['close']
        delta = close.diff()
        ganho = np.where(delta > 0, delta, 0)
        perda = np.where(delta < 0, -delta, 0)
        ganho_medio = pd.Series(ganho).rolling(window=14).mean()
        perda_medio = pd.Series(perda).rolling(window=14).mean()
        rs = ganho_medio / perda_medio
        rsi = 100 - (100 / (1 + rs))
        rsi_atual = rsi.iloc[-1]

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_atual = macd.iloc[-1]
        signal_atual = signal.iloc[-1]

        tendencia = 'Alta' if macd_atual > signal_atual else 'Baixa'

        return {
            'rsi': float(rsi_atual),
            'macd': float(macd_atual),
            'signal': float(signal_atual),
            'tendencia': tendencia
        }
    except Exception as e:
        print(f'Erro ao calcular indicadores: {e}')
        return {'rsi': 0.0, 'macd': 0.0, 'signal': 0.0, 'tendencia': 'Erro'}

@app.route('/')
def home():
    precos = {}
    indicadores = {}

    for ticker in TICKERS:
        df = obter_dados_binance(ticker)
        if df is not None and not df.empty:
            try:
                preco = float(df['close'].iloc[-1])
                precos[ticker] = preco
                indicadores[ticker] = calcular_indicadores(df)
            except Exception as e:
                precos[ticker] = 0.0
                indicadores[ticker] = {'rsi': 0.0, 'macd': 0.0, 'signal': 0.0, 'tendencia': 'Erro'}
                ALERTAS[ticker] = f'⚠️ Erro: {str(e)}'
        else:
            precos[ticker] = 0.0
            indicadores[ticker] = {'rsi': 0.0, 'macd': 0.0, 'signal': 0.0, 'tendencia': 'Erro'}
            ALERTAS[ticker] = '⚠️ Erro: dados indisponíveis'

    return render_template_string(TEMPLATE, precos=precos, ind=indicadores, nomes=TICKERS, alertas=ALERTAS)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
