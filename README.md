# PocketOption Signal Scanner (Docker) - Ready for Railway / Render

This package contains a Dockerized **signal-only** scanner that:
- Monitors **GOLD (XAUUSD via Yahoo/yfinance)** and **BTC/USD (via Binance public REST)**
- Uses EMA + RSI + MACD divergence + pivot-based support/resistance logic
- Sends signals and daily summaries to your Telegram bot
- **Does NOT** log into PocketOption or place trades

## Files included
- `scanner.py` - main scanner (runs continuously)
- `strategy.py` - indicator & signal logic
- `backtester.py` - run historical backtests from CSV candles
- `utils/telegram_bot.py` - Telegram messaging helper
- `Dockerfile`, `requirements.txt`, `.env.example`

## Quick deploy on Railway (recommended - free tier)
1. Create a new GitHub repository and push this project to it.
2. Go to https://railway.app and sign in.
3. Create a **New Project → Deploy from GitHub** and select your repo.
4. In Railway project settings, set the following Environment Variables (paste your values):
   - `TELEGRAM_TOKEN` (from @BotFather)
   - `TELEGRAM_CHAT_ID` (your numeric chat id)
   - Optionally adjust: `TIMEFRAME`, `ASSETS`, `ALERT_COOLDOWN`
5. Railway will detect the `Dockerfile` and build the container. Deploy.
6. Check logs on Railway dashboard. The bot will send signals to your Telegram chat.

## Local Docker run (if you prefer)
1. Copy `.env.example` → `.env` and fill values.
2. Build:
   ```bash
   docker build -t pocket-signals .
   ```
3. Run (mount logs to persist):
   ```bash
   docker run --env-file .env -v "$(pwd)/logs:/app/logs" --name pocket-signals -d pocket-signals
   ```
4. View logs:
   ```bash
   docker logs -f pocket-signals
   ```

## How to use the backtester
Provide a CSV with columns `timestamp,open,high,low,close,volume`.
Example:
```bash
python backtester.py --candles historical_gold_1m.csv --out results_gold.csv
```

## Notes & limitations
- Gold data via `yfinance` may have gaps during some hours; fallback to futures is included.
- BTC uses Binance public API (no API key required).
- Adjust strategy parameters inside `strategy.py` if you want different EMA/RSI/MACD lengths.
- Keep your Telegram token private. Use `.env` and Railway environment variables for safety.

## Support
If you want, I can provide step-by-step Railway deployment instructions or the exact `git` commands to push this repo to GitHub.
