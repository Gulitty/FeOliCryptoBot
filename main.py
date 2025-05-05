
import yfinance as yf
import pandas as pd
from flask import Flask, render_template_string
import requests

app = Flask(__name__)

TICKERS = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana"
}

ALERTAS = {t: "—" for t in TICKERS}

TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: sans-serif; text-align: center; margin: 40px; }
        table { width: 90%; margin: auto; border-collapse: collapse; }
        th, td { border: 2px solid black; padding: 12px; font-size: 18px; }
        th { background-color: #f2f2f2; font-size: 22px; }
        .alta { color: green; font-weight: bold; }
        .baixa { color: red; font-weight: bold; }
        .compra { color: green; font-weight: bold; }
        .venda { color: red; font-weight: bold; }
        .legenda { margin-top: 30px; background: #f8f8f8; padding: 20px; width: 80%; margin-left: auto; margin-right: auto; border: 1px solid #ccc; border-radius: 5px; }
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
        {% for t in nomes %}
        <tr>
            <td>{{ nomes[t] }}</td>
            <td>${{ "%.2f"|format(precos[t]) }}</td>
            <td>{{ "%.2f"|format(ind[t]["RSI"]) }}</td>
            <td>{{ "%.4f"|format(ind[t]["MACD"]) }}</td>
            <td>{{ "%.4f"|format(ind[t]["Signal"]) }}</td>
            <td class="{{ 'alta' if ind[t]['Tendência'] == 'Alta' else 'baixa' }}">
                {{ '▲ Alta' if ind[t]["Tendência"] == 'Alta' else '▼ Baixa' }}
            </td>
            <td>{{ alertas[t] }}</td>
        </tr>
        {% endfor %}
    </table>

    <div class="legenda">
        <p style="font-size: 20px;">
            📘 <strong>Legenda dos Alertas:</strong><br><br>
            🟢 <strong>Alerta de COMPRA</strong>: RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal<br>
            🔴 <strong>Alerta de VENDA</strong>: RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal
        </p>
    </div>

    <p style="margin-top: 20px; color: gray;">Atualizado a cada minuto (modo debug)</p>
</body>
</html>
'''

def calcular_indicadores(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1h")
        close = df["Close"]
        if close.isnull().all():
            raise ValueError("Dados insuficientes")

        rsi = 100 - (100 / (1 + close.pct_change().rolling(14).mean() / close.pct_change().rolling(14).std()))
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()

        atual = {
            "RSI": float(rsi.iloc[-1]),
            "MACD": float(macd.iloc[-1]),
            "Signal": float(signal.iloc[-1]),
        }
        atual["Tendência"] = "Alta" if atual["MACD"] > atual["Signal"] else "Baixa"
        return atual
    except Exception as e:
        print(f"Erro ao calcular indicadores para {ticker}: {e}")
        return {
            "RSI": 0.0,
            "MACD": 0.0,
            "Signal": 0.0,
            "Tendência": "Erro"
        }

def enviar_alerta(mensagem):
    token = "SEU_BOT_TOKEN"
    chat_id = "SEU_CHAT_ID"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": mensagem}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

@app.route("/")
def home():
    precos = {}
    indicadores = {}
    for t in TICKERS:
        try:
            df = yf.download(t, period="1d", interval="1h")
            precos[t] = float(df["Close"].iloc[-1])
            indicadores[t] = calcular_indicadores(t)

            rsi = indicadores[t]["RSI"]
            macd = indicadores[t]["MACD"]
            signal = indicadores[t]["Signal"]
            tendencia = indicadores[t]["Tendência"]

            if rsi < 30 and macd > signal:
                alerta = f"🟢 Alerta de COMPRA para {TICKERS[t]}!"
                if ALERTAS[t] != alerta:
                    ALERTAS[t] = alerta
                    enviar_alerta(alerta)
            elif rsi > 70 and macd < signal:
                alerta = f"🔴 Alerta de VENDA para {TICKERS[t]}!"
                if ALERTAS[t] != alerta:
                    ALERTAS[t] = alerta
                    enviar_alerta(alerta)
            else:
                ALERTAS[t] = "—"
        except Exception as e:
            print(f"⚠️ Erro analisando {t}: {e}")
            ALERTAS[t] = "Erro"

    return render_template_string(TEMPLATE, precos=precos, ind=indicadores, nomes=TICKERS, alertas=ALERTAS)

if __name__ == "__main__":
    app.run(debug=True, port=8080, host="0.0.0.0")
