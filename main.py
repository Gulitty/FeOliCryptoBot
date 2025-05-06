from flask import Flask, render_template_string
import pandas as pd
import requests
import numpy as np

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { text-align: center; padding: 8px; border: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .alerta-compra { color: green; font-weight: bold; }
        .alerta-venda { color: red; font-weight: bold; }
        .erro { color: orange; }
        .tendencia-alta { color: green; }
        .tendencia-baixa { color: red; }
        .legenda { margin-top: 30px; padding: 20px; background-color: #f9f9f9; border-radius: 8px; }
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
        {% for cripto in dados %}
        <tr>
            <td>{{ cripto['nome'] }}</td>
            <td>{{ cripto['preco'] }}</td>
            <td>{{ cripto['rsi'] }}</td>
            <td>{{ cripto['macd'] }}</td>
            <td>{{ cripto['signal'] }}</td>
            <td class="{{ cripto['tendencia_classe'] }}">{{ cripto['tendencia'] }}</td>
            <td class="{{ cripto['alerta_classe'] }}">{{ cripto['alerta'] }}</td>
        </tr>
        {% endfor %}
    </table>

    <div class="legenda">
        <h3>📘 Legenda dos Alertas:</h3>
        <p>🟢 <span class="alerta-compra">Alerta de COMPRA:</span> RSI abaixo de 30 <strong>e</strong> MACD cruzando acima da Signal</p>
        <p>🔴 <span class="alerta-venda">Alerta de VENDA:</span> RSI acima de 70 <strong>e</strong> MACD cruzando abaixo da Signal</p>
        <p style="color: gray;">Atualizado a cada minuto (modo debug)</p>
    </div>
</body>
</html>
"""

CRIPTO_IDS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana"
}

def calcular_rsi(close_prices, period=14):
    delta = close_prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calcular_macd(close_prices, short=12, long=26, signal=9):
    ema_short = close_prices.ewm(span=short, adjust=False).mean()
    ema_long = close_prices.ewm(span=long, adjust=False).mean()
    macd = ema_short - ema_long
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def buscar_preco(coin_id):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        preco = data[coin_id]["usd"]
        print(f"[DEBUG] Preço de {coin_id}: ${preco}")
        return preco
    except Exception as e:
        print(f"[ERRO] Falha ao buscar preço de {coin_id}: {e}")
        return None

@app.route("/")
def home():
    dados = []

    for nome, coin_id in CRIPTO_IDS.items():
        try:
            preco = buscar_preco(coin_id)
            if preco is None:
                raise ValueError("Preço indisponível")

            # Geração de dados simulados para RSI e MACD:
            closes = pd.Series(np.random.normal(preco, preco * 0.01, 100))
            rsi = calcular_rsi(closes).iloc[-1]
            macd, signal = calcular_macd(closes)
            macd_val = macd.iloc[-1]
            signal_val = signal.iloc[-1]

            tendencia = "📈" if macd_val > signal_val else "📉"
            tendencia_classe = "tendencia-alta" if macd_val > signal_val else "tendencia-baixa"

            if rsi < 30 and macd_val > signal_val:
                alerta = "🟢 Alerta de COMPRA"
                alerta_classe = "alerta-compra"
            elif rsi > 70 and macd_val < signal_val:
                alerta = "🔴 Alerta de VENDA"
                alerta_classe = "alerta-venda"
            else:
                alerta = "—"
                alerta_classe = ""

            dados.append({
                "nome": nome,
                "preco": f"${preco:,.2f}",
                "rsi": f"{rsi:.2f}",
                "macd": f"{macd_val:.4f}",
                "signal": f"{signal_val:.4f}",
                "tendencia": tendencia,
                "tendencia_classe": tendencia_classe,
                "alerta": alerta,
                "alerta_classe": alerta_classe
            })

        except Exception as e:
            print(f"[ERRO] Falha ao processar {nome}: {e}")
            dados.append({
                "nome": nome,
                "preco": "$0.00",
                "rsi": "0.00",
                "macd": "0.0000",
                "signal": "0.0000",
                "tendencia": "—",
                "tendencia_classe": "",
                "alerta": "⚠️ Erro: dados indisponíveis",
                "alerta_classe": "erro"
            })

    return render_template_string(TEMPLATE, dados=dados)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
