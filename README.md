# ⚡ Nexus Trader — Binance Algorithmic Trading Bot & Dashboard

An institutional-grade, fully automated crypto trading bot in Python with a real-time dark glassmorphic web dashboard, live WebSocket telemetry, TradingView candlestick charts, and multi-strategy support.

---

## 🌟 Key Features

1. **Dual Trading Environments**:
   * **Paper Trading Simulator (Default)**: Pre-funded with **$10,000 virtual USDT**. Simulates real-world execution with realistic taker fees (0.10%) and slippage (0.05%). Completely risk-free.
   * **Binance Spot Testnet**: Directly connects to `testnet.binance.vision` using official API keys without putting real capital at risk.
2. **Real-time Live Market Data**:
   * Streams live tick-by-tick prices and candlesticks directly from Binance's public WebSocket (`BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`, `DOGE/USDT`). **No API keys needed for live market feeds.**
3. **Institutional Web Dashboard**:
   * Powered by **TradingView Lightweight Charts v5** with interactive candlestick charts, Fast EMA (9), Slow EMA (21), and Buy/Sell execution marker arrows.
   * Dynamic telemetry: Total Equity, Realized/Unrealized P&L, Win Rate %, Profit Factor, Max Drawdown.
   * Audio sound cues for trade executions (Web Audio API synthesized chimes).
4. **Three Built-in Quantitative Strategies**:
   * **EMA 9/21 Crossover + RSI 14 Momentum**: Trend-following strategy with momentum filter.
   * **Bollinger Bands Mean Reversion**: Buys oversold dips at lower bands; exits at upper bands.
   * **Dynamic Volatility Grid Scalper**: Captures micro-fluctuations around moving average baselines.
5. **Strict Risk Management**:
   * Hard Stop-Loss % cutoff.
   * Take-Profit % target exit.
   * Trailing Stop protection (locks in profits as the trade rises).
   * **One-Click Emergency Panic Button**: Instantly liquidates open positions at market price and halts execution.

---

## 🚀 Quick Start Guide (Windows)

### Step 1: Open Terminal in Project Directory
Open PowerShell or Command Prompt in `d:\Project 2026\Trading_bot`:
```powershell
cd "d:\Project 2026\Trading_bot"
```

### Step 2: Run the Bot
```powershell
python run.py
```
* The launcher will automatically find a free port (default: `8000`), launch your default browser, and open:
  **`http://localhost:8000`**

---

## 🇧🇩 Bangladesh (BD) Setup Guide & Regulations

### Is Paper Trading Legal and Free from Bangladesh?
* **Yes!** Paper trading and Testnet trading use **simulated virtual money** (fake demo funds).
* You do **not** need to deposit real money, link a bank account, or perform foreign currency outward remittances (which Bangladesh Bank restricts).
* Binance's public market feeds and testnet are accessible directly from internet providers in Bangladesh.

---

## 🔑 How to Get Free Binance Testnet API Keys (Optional)

If you want to move from local Paper Trading to official Binance Testnet execution:

1. Visit the official Binance Spot Testnet: **[https://testnet.binance.vision](https://testnet.binance.vision)**
2. Click **"Log In with GitHub"** to authenticate (no KYC, passport, or credit card required).
3. Click **"Generate API Key"**.
4. Copy your **API Key** and **Secret Key**.
5. In the Nexus Dashboard:
   * Click the **Settings Gear (⚙️)** in the top right navigation bar.
   * Select **Binance Spot Testnet**.
   * Paste your **API Key** and **Secret Key**.
   * Click **Save Configuration**.

---

## 📊 Dashboard Controls Reference

| Control | Description |
| :--- | :--- |
| **START BOT / PAUSE BOT** | Starts or pauses algorithmic signal evaluation and automated order execution. |
| **PANIC EXIT** | Emergency kill switch: Market-sells open position immediately and pauses the bot. |
| **PAIR SELECTOR** | Switch between `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`, `DOGE/USDT`. |
| **TIMEFRAME (1m, 3m, 5m, 15m)** | Changes candle aggregation and indicator resolution on the fly. |
| **RESET WALLET** | Resets paper trading balance back to $10,000.00 and clears historical stats. |
| **AUDIO TOGGLE (🔊)** | Toggles the synthesized chime that rings when orders execute. |

---

## 🛠 Project Architecture

```
Trading_bot/
├── run.py                 # One-click launcher with auto-browser launch
├── server.py              # FastAPI server + WebSocket gateway
├── bot_engine.py          # Master trading loop & risk manager
├── paper_exchange.py      # Simulated exchange engine with fees & slippage
├── binance_service.py     # Binance WebSocket & CCXT testnet connector
├── indicators.py          # Vectorized technical indicators (NumPy/Pandas)
├── strategies.py          # Modular trading strategy classes
├── config.json            # Active bot configuration & parameters
├── web/
│   ├── index.html         # Modern cyber-dark dashboard
│   ├── style.css          # Glassmorphic CSS styling
│   ├── app.js             # Client WebSocket & TradingView charts logic
│   └── js/
│       └── lightweight-charts.js  # TradingView Lightweight Charts library
└── README.md              # Documentation & guide
```
