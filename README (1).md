# 💹 FinanceAI — AI-Powered Personal Finance Intelligence

A Streamlit prototype for intelligent personal finance analysis with Monte Carlo retirement simulations, debt optimization, and AI-powered recommendations via OpenRouter.

---

## Features

- **Chat interface** — natural language queries about your finances
- **Portfolio tab** — asset allocation donut chart + cash flow waterfall
- **Retirement tab** — Monte Carlo simulation (up to 2,000 paths, configurable years)
- **Debt tab** — loan breakdown, avalanche/snowball strategy, AI recommendations
- **MCP JSON upload** — structured data ingestion (assets / liabilities / EPF / credit score)
- **Privacy-first** — all data processed in-session, no persistence, no cloud storage

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/finance-ai-demo.git
cd finance-ai-demo
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
cp .env.example .env
# Open .env and paste your OpenRouter key
```

Get a free key at https://openrouter.ai/keys

### 4. Run

```bash
streamlit run app.py
```

---

## Deploy on Streamlit Cloud

1. Push this repo to GitHub
2. Go to https://share.streamlit.io → New app → select your repo
3. Add `OPENROUTER_API_KEY` under **Settings → Secrets**:

```toml
OPENROUTER_API_KEY = "sk-or-v1-..."
```

4. Click **Deploy** — done!

---

## MCP JSON Format

Upload a `.json` file with this structure:

```json
{
  "user_id": "string",
  "credit_score": 750,
  "epf_balance": 500000,
  "assets": [
    {"name": "Mutual Funds", "value": 300000}
  ],
  "liabilities": [
    {"name": "Home Loan", "principal": 4000000, "rate": 8.5, "emi": 35000}
  ],
  "monthly_income": 150000,
  "monthly_expenses": 80000
}
```

A ready-to-use sample is included as `sample_data.json`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit 1.38 |
| Charts | Plotly 5.24 |
| Simulation | NumPy (Monte Carlo) |
| Data validation | Pydantic v2 |
| AI | OpenRouter → GPT-4o-mini |
| Env config | python-dotenv |

---

## Project Structure

```
finance-ai-demo/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── sample_data.json    # Test MCP JSON file
├── .env.example        # API key template
├── .gitignore          # Excludes .env from git
└── README.md
```

---

## License

MIT
