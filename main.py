from flask import Flask, render_template_string
import requests
import pandas as pd

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <title>FeOliCryptoBot - Painel</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #fff; color: #333; }
        h1 { text-align: center; margin-top: 30px; }
        table { border-collapse: collapse; width: 90%; margin: 0 auto; margin-top: 20px; }
        th, td { border: 1px solid #999; padding: 10px; text-align: center; }
        th { background-color: #f0f0f0; }
        .legenda { width: 90%; margin: 40px auto; padding: 20px; background-color: #f8f8f8; border-radius: 8px; }
        .legenda h2 { margin-top: 0; }
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
        {% for item in dados %}
        <tr>
            <td>{{ item['nome'] }}</td>
            <td>{{ item['preco'] }}</td>
            <td>{{ item['rsi'] }}</td>
            <td>{{ item['macd'] }}</td>
            <td>{{ item['signal'] }}</td>
            <td>{{ item['tendencia'] }}</td>
            <td>{{ item['alerta'] }}</td>
        </tr>
        {% endfor %}
    </table>

    <div class="legenda">
        <h2>📘 Legenda dos Alertas:</h2>
        <p class="verde">🟢 Alerta de COMPRA:</strong> RSI abaixo de 30 <u>e</u> MACD cruzando acima da Signal</p>
        <p class="vermelho">🔴 Alerta de VENDA:</strong> RSI acima de 70 <u>e</u> MACD cruzando abaixo da Signal</p>
        <p style="text-align: center; margin-top: 30px;">Atualizado a cada minuto (modo debug)</p>
    </div>
</body>
</html>
"""

CRIPTO_LISTA = [
    {"nome": "Bitcoin", "symbol": "BTCUSDT"},
    {"nome": "Ethereum", "symbol": "ETHUSDT"},
    {"nome": "Solana", "symbol": "SOLUSDT"}
]

def calcular_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(0)

def calcular_macd(df):
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def baixar_dados(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
        ])
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"Erro ao baixar dados de {symbol}: {e}")
        return None

@app.route('/')
def home():
    # Teste de conexão com Binance
    try:
        test = requests.get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1")
        test.raise_for_status()
        print("✅ Teste de conexão com Binance OK")
    except Exception as e:
        print("❌ Falha na conexão com Binance:", e)

    dados = []
    for cripto in CRIPTO_LISTA:
        try:
            df = baixar_dados(cripto['symbol'])
            if df is None or df.empty:
                raise ValueError("dados indisponíveis")

            preco = float(df['close'].iloc[-1])
            rsi = calcular_rsi(df).iloc[-1]
            macd, signal = calcular_macd(df)
            macd_val = macd.iloc[-1]
            signal_val = signal.iloc[-1]

            tendencia = "📈 Alta" if macd_val > signal_val else "📉 Baixa"
            alerta = "—"
            if rsi < 30 and macd_val > signal_val:
                alerta = "🟢 COMPRA"
            elif rsi > 70 and macd_val < signal_val:
                alerta = "🔴 VENDA"

            dados.append({
                "nome": cripto['nome'],
                "preco": f"${preco:,.2f}",
                "rsi": f"{rsi:.2f}",
                "macd": f"{macd_val:.4f}",
                "signal": f"{signal_val:.4f}",
                "tendencia": tendencia,
                "alerta": alerta
            })

        except Exception as e:
            print(f"Erro ao processar {cripto['nome']}: {e}")
            dados.append({
                "nome": cripto['nome'],
                "preco": "$0.00",
                "rsi": "0.00",
                "macd": "0.0000",
                "signal": "0.0000",
                "tendencia": "—",
                "alerta": f"⚠️ Erro: dados indisponíveis"
            })

    return render_template_string(TEMPLATE, dados=dados)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
