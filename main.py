from flask import Flask, render_template
import requests

app = Flask(__name__)

def get_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data[coin_id]['usd']
    except Exception as e:
        print(f"Erro ao buscar {coin_id}: {e}")
        return 0

@app.route('/')
def home():
    btc_price = get_price("bitcoin")
    eth_price = get_price("ethereum")
    sol_price = get_price("solana")
    
    return render_template("index.html", btc=btc_price, eth=eth_price, sol=sol_price)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
