from flask import Flask, render_template_string
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #fff; text-align: center; }
        table { margin: 0 auto; border-collapse: collapse; }
        th, td { border: 1px solid #ccc; padding: 10px; }
        th { background: #eee; }
        .compra { color: green; font-weight: bold; }
        .venda { color: red; font-weight: bold; }
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
        {% for c in criptos %}
        <tr>
            <td>{{ c['nome'] }}</td>
            <td>${{ "{:.2f}".format(c['preco']) }}</td>
            <td>{{ "{:.2f}".format(c['rsi']) }}</td>
            <td>{{ "{:.4f}".format(c['macd']) }}</td>
            <td>{{ "{:.4f}".format(c['signal']) }}</td>
            <td>{{ c['tendencia'] }}</td>
            <td>{{ c['alerta'] }}</td>
        </tr>
        {% endfor %}
    </table>

    <div style="margin-top: 40px; text-align: center;">
        <h3>📘 Legenda dos Alertas:</h3>
        <p style="color: green;"><b>🟢 Alerta de COMPRA:</b> RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal</p>
        <p style="color: red;"><b>🔴 Alerta de VENDA:</b> RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal</p>
        <p style="color: gray;">Atualizado a cada minuto (modo debug)</p>
    </div>
</body>
</html>
'''

COINGECKO_IDS = {
    'Bitcoin': 'bitcoin',
    'Ethereum': 'ethereum',
    'Solana': 'solana'
}

def fetch_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=2&interval=hourly"
        r = requests.get(url)
        data = r.json()
        prices = [x[1] for x in data["prices"]]
        df = pd.DataFrame(prices, columns=["close"])
        df['close'] = df['close'].astype(float)
        return df
    except:
        return None

def calcular_indicadores(df):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi

    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    return df

@app.route('/')
def home():
    resultado = []
    for nome, coin_id in COINGECKO_IDS.items():
        df = fetch_data(coin_id)
        if df is not None and not df.empty:
            df = calcular_indicadores(df)
            preco = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1] if not pd.isna(df['rsi'].iloc[-1]) else 0
            macd = df['macd'].iloc[-1]
            signal = df['signal'].iloc[-1]

            if rsi < 30 and macd > signal:
                alerta = "🟢 Alerta de COMPRA"
                tendencia = "📈 Alta"
            elif rsi > 70 and macd < signal:
                alerta = "🔴 Alerta de VENDA"
                tendencia = "📉 Baixa"
            else:
                alerta = "Sem alerta"
                tendencia = "—"
        else:
            preco = 0
            rsi = macd = signal = 0
            alerta = "⚠️ Erro: dados indisponíveis"
            tendencia = "—"

        resultado.append({
            "nome": nome,
            "preco": preco,
            "rsi": rsi,
            "macd": macd,
            "signal": signal,
            "tendencia": tendencia,
            "alerta": alerta
        })

    return render_template_string(TEMPLATE, criptos=resultado)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
