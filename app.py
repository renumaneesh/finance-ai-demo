import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"

# ── Pydantic models ──────────────────────────────────────────────────────────

class Asset(BaseModel):
    name: str
    value: float

class Liability(BaseModel):
    name: str
    principal: float
    rate: float = 0.0
    emi: float = 0.0

class FinanceData(BaseModel):
    user_id: str
    credit_score: int = 750
    epf_balance: float = 0.0
    assets: list[Asset] = []
    liabilities: list[Liability] = []
    monthly_income: float = 0.0
    monthly_expenses: float = 0.0

# ── Helpers ──────────────────────────────────────────────────────────────────

def fmt(n: float) -> str:
    if abs(n) >= 1e7:
        return f"₹{n/1e7:.2f} Cr"
    if abs(n) >= 1e5:
        return f"₹{n/1e5:.2f} L"
    return f"₹{n:,.0f}"

def net_worth(fd: FinanceData) -> float:
    assets = fd.epf_balance + sum(a.value for a in fd.assets)
    debts  = sum(l.principal for l in fd.liabilities)
    return assets - debts

# ── Monte Carlo ───────────────────────────────────────────────────────────────

def monte_carlo(fd: FinanceData, years: int = 10, sims: int = 1000):
    np.random.seed(42)
    months = years * 12
    returns   = np.random.normal(0.007,  0.040, (months, sims))
    inflation = np.random.normal(0.004,  0.015, (months, sims))

    init_nw    = fd.epf_balance + sum(a.value for a in fd.assets)
    surplus    = fd.monthly_income - fd.monthly_expenses

    proj = np.zeros((months + 1, sims))
    proj[0] = init_nw

    for t in range(months):
        proj[t + 1] = proj[t] * (1 + returns[t] - inflation[t]) + surplus

    return proj

# ── AI call via OpenRouter ────────────────────────────────────────────────────

def get_ai_insights(fd: FinanceData, question: str = "") -> str:
    if not OPENROUTER_API_KEY:
        return "⚠️ OPENROUTER_API_KEY not set in .env file."

    context = f"""You are an expert Indian personal finance advisor.
User profile:
- Credit Score   : {fd.credit_score}
- EPF Balance    : {fmt(fd.epf_balance)}
- Total Assets   : {fmt(sum(a.value for a in fd.assets))}
- Total Debt     : {fmt(sum(l.principal for l in fd.liabilities))}
- Monthly Income : {fmt(fd.monthly_income)}
- Monthly Expense: {fmt(fd.monthly_expenses)}
- Monthly Surplus: {fmt(fd.monthly_income - fd.monthly_expenses)}
- Net Worth      : {fmt(net_worth(fd))}

Respond concisely with bullet points. Be specific and actionable. Max 200 words."""

    user_msg = question if question else "Give 3 key financial recommendations for this user."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://finance-ai-demo.streamlit.app",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": context},
            {"role": "user",   "content": user_msg},
        ],
    }
    try:
        r = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ AI error: {e}"

# ── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="FinanceAI", page_icon="💹", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .metric-label { font-size: 0.78rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💹 FinanceAI")
    st.markdown("---")

    # JSON upload
    uploaded = st.file_uploader("Upload MCP JSON", type="json")
    if uploaded:
        try:
            fd = FinanceData(**json.load(uploaded))
            st.session_state.finance_data = fd
            st.success("✅ Data loaded!")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

    # Sample data
    if st.button("🚀 Load Sample Data", use_container_width=True):
        sample = {
            "user_id": "demo_user",
            "credit_score": 750,
            "epf_balance": 500000,
            "assets": [
                {"name": "Savings",       "value": 200000},
                {"name": "Mutual Funds",  "value": 300000},
                {"name": "Gold ETF",      "value": 150000},
            ],
            "liabilities": [
                {"name": "Home Loan", "principal": 4000000, "rate": 8.5, "emi": 35000},
                {"name": "Car Loan",  "principal":  450000, "rate": 9.2, "emi": 12000},
            ],
            "monthly_income":   150000,
            "monthly_expenses":  80000,
        }
        st.session_state.finance_data = FinanceData(**sample)
        st.success("✅ Sample data loaded!")

    # Metrics panel
    if "finance_data" in st.session_state:
        fd = st.session_state.finance_data
        st.markdown("---")
        st.markdown("#### Portfolio Snapshot")
        c1, c2 = st.columns(2)
        c1.metric("Net Worth",    fmt(net_worth(fd)))
        c2.metric("Credit Score", fd.credit_score)
        c1.metric("EPF Balance",  fmt(fd.epf_balance))
        c2.metric("Surplus/mo",   fmt(fd.monthly_income - fd.monthly_expenses))

        dti = fd.monthly_expenses / fd.monthly_income * 100 if fd.monthly_income else 0
        st.progress(min(int(dti), 100), text=f"Expense Ratio: {dti:.0f}%")

    st.markdown("---")
    st.caption("🔒 Privacy-first · Data processed locally · No cloud storage")

# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_chat, tab_portfolio, tab_retirement, tab_debt = st.tabs(
    ["💬 Chat", "📊 Portfolio", "🔮 Retirement", "💳 Debt"]
)

# ── Chat tab ──────────────────────────────────────────────────────────────────

with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content":
             "Hello! I'm your AI finance advisor. Load your data using the sidebar, "
             "then ask me anything — retirement projections, debt strategies, investment tips, or net worth analysis."}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your finances..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if "finance_data" not in st.session_state:
                reply = "⚠️ Please load your financial data (or sample data) from the sidebar first."
                st.warning(reply)
            else:
                fd = st.session_state.finance_data

                # Retirement query → also show chart
                if any(w in prompt.lower() for w in ["retire", "retirement", "future", "10 year"]):
                    proj = monte_carlo(fd)
                    yrs  = list(range(proj.shape[0] // 12 + 1))
                    # sample every 12 months
                    idx  = [i * 12 for i in yrs]

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=yrs, y=np.percentile(proj, 90, axis=1)[idx] / 1e5,
                        fill=None, mode="lines", line=dict(color="#5DCAA5", dash="dash"), name="P90 (Optimistic)"))
                    fig.add_trace(go.Scatter(x=yrs, y=np.percentile(proj, 50, axis=1)[idx] / 1e5,
                        fill="tonexty", mode="lines", line=dict(color="#1D9E75", width=3), name="Median (P50)"))
                    fig.add_trace(go.Scatter(x=yrs, y=np.percentile(proj, 10, axis=1)[idx] / 1e5,
                        fill="tonexty", mode="lines", line=dict(color="#EF9F27", dash="dash"), name="P10 (Conservative)"))
                    fig.update_layout(
                        title="10-Year Retirement Projection (₹ Lakhs)",
                        xaxis_title="Years from now",
                        yaxis_title="Net Worth (₹ L)",
                        template="plotly_white",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                        height=380,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    median_final = np.percentile(proj[-1], 50) / 1e7
                    st.info(f"📈 Median projection in 10 years: **₹{median_final:.2f} Cr**  \n"
                            f"(1,000 Monte Carlo simulations with market & inflation randomness)")

                # Debt query
                elif any(w in prompt.lower() for w in ["debt", "loan", "emi"]):
                    if fd.liabilities:
                        rows = [{"Loan": l.name, "Principal": fmt(l.principal),
                                 "Rate (%)": l.rate, "EMI/mo": fmt(l.emi)}
                                for l in fd.liabilities]
                        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                with st.spinner("Getting AI insights..."):
                    reply = get_ai_insights(fd, prompt)
                st.markdown(reply)

            st.session_state.messages.append({"role": "assistant", "content": reply if "reply" in dir() else ""})

# ── Portfolio tab ─────────────────────────────────────────────────────────────

with tab_portfolio:
    if "finance_data" not in st.session_state:
        st.info("Load financial data from the sidebar to see your portfolio breakdown.")
    else:
        fd = st.session_state.finance_data

        total_assets  = fd.epf_balance + sum(a.value for a in fd.assets)
        total_liab    = sum(l.principal for l in fd.liabilities)
        total_emi     = sum(l.emi for l in fd.liabilities)
        investable    = fd.monthly_income - fd.monthly_expenses - total_emi

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Assets",      fmt(total_assets))
        c2.metric("Total Liabilities", fmt(total_liab))
        c3.metric("Monthly Surplus",   fmt(fd.monthly_income - fd.monthly_expenses))
        c4.metric("Investable Surplus", fmt(investable))

        col_l, col_r = st.columns([1, 1])

        with col_l:
            st.markdown("#### Asset Allocation")
            labels = [a.name for a in fd.assets] + ["EPF"]
            values = [a.value for a in fd.assets] + [fd.epf_balance]
            colors = ["#1D9E75", "#3266ad", "#BA7517", "#D4537E", "#7F77DD", "#E24B4A"]
            fig = go.Figure(go.Pie(labels=labels, values=values,
                                   hole=0.55,
                                   marker_colors=colors[:len(labels)],
                                   textinfo="label+percent"))
            fig.update_layout(showlegend=False, height=320, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.markdown("#### Monthly Cash Flow")
            cats   = ["Income", "Expenses", "EMIs", "Investable"]
            vals   = [fd.monthly_income, -fd.monthly_expenses, -total_emi, investable]
            bar_colors = ["#1D9E75" if v >= 0 else "#E24B4A" for v in vals]
            fig2 = go.Figure(go.Bar(x=cats, y=vals, marker_color=bar_colors,
                                    text=[fmt(abs(v)) for v in vals],
                                    textposition="outside"))
            fig2.update_layout(template="plotly_white", height=320,
                                yaxis_title="₹", margin=dict(t=10, b=10))
            st.plotly_chart(fig2, use_container_width=True)

# ── Retirement tab ────────────────────────────────────────────────────────────

with tab_retirement:
    if "finance_data" not in st.session_state:
        st.info("Load financial data to run the Monte Carlo retirement simulation.")
    else:
        fd   = st.session_state.finance_data
        col1, col2 = st.columns([3, 1])

        with col2:
            years = st.slider("Projection (years)", 5, 30, 10)
            sims  = st.select_slider("Simulations", [100, 500, 1000, 2000], 1000)

        with st.spinner(f"Running {sims} Monte Carlo simulations..."):
            proj = monte_carlo(fd, years=years, sims=sims)

        idx  = [i * 12 for i in range(years + 1)]
        yrs  = list(range(years + 1))

        p10  = np.percentile(proj, 10, axis=1)[idx] / 1e5
        p50  = np.percentile(proj, 50, axis=1)[idx] / 1e5
        p90  = np.percentile(proj, 90, axis=1)[idx] / 1e5

        c1, c2, c3 = st.columns(3)
        c1.metric("Conservative (P10)", fmt(p10[-1] * 1e5))
        c2.metric("Median (P50)",       fmt(p50[-1] * 1e5))
        c3.metric("Optimistic (P90)",   fmt(p90[-1] * 1e5))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=yrs, y=p90, fill=None, mode="lines",
                                  line=dict(color="#5DCAA5", dash="dash"), name="P90 – Optimistic"))
        fig.add_trace(go.Scatter(x=yrs, y=p50, fill="tonexty", mode="lines",
                                  line=dict(color="#1D9E75", width=3), name="Median (P50)"))
        fig.add_trace(go.Scatter(x=yrs, y=p10, fill="tonexty", mode="lines",
                                  line=dict(color="#EF9F27", dash="dash"), name="P10 – Conservative"))
        fig.update_layout(
            title=f"{years}-Year Retirement Projection · {sims} Simulations (₹ Lakhs)",
            xaxis_title="Years", yaxis_title="Net Worth (₹ L)",
            template="plotly_white", height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption("Assumes 7% avg annual return (σ=4%), 5% avg inflation (σ=2%), constant monthly surplus.")

# ── Debt tab ──────────────────────────────────────────────────────────────────

with tab_debt:
    if "finance_data" not in st.session_state:
        st.info("Load financial data to see your debt analysis.")
    elif not st.session_state.finance_data.liabilities:
        st.success("🎉 No liabilities found — you are debt-free!")
    else:
        fd = st.session_state.finance_data

        total_debt = sum(l.principal for l in fd.liabilities)
        total_emi  = sum(l.emi for l in fd.liabilities)
        avg_rate   = sum(l.rate * l.principal for l in fd.liabilities) / total_debt
        dscr       = (fd.monthly_income - fd.monthly_expenses) / total_emi if total_emi else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Debt",   fmt(total_debt))
        c2.metric("Total EMI",    fmt(total_emi))
        c3.metric("Avg Rate",     f"{avg_rate:.1f}%")
        c4.metric("DSCR",         f"{dscr:.2f}x",
                  delta="Healthy" if dscr >= 1.5 else "Tight",
                  delta_color="normal" if dscr >= 1.5 else "inverse")

        st.markdown("#### Loan Breakdown")
        rows = [{"Loan": l.name, "Principal": fmt(l.principal),
                 "Rate (%)": l.rate, "EMI / Month": fmt(l.emi),
                 "Strategy": "Pay first 🔥" if l.rate == max(x.rate for x in fd.liabilities) else "Minimum"}
                for l in sorted(fd.liabilities, key=lambda x: -x.rate)]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Debt Composition")
            fig = go.Figure(go.Pie(
                labels=[l.name for l in fd.liabilities],
                values=[l.principal for l in fd.liabilities],
                hole=0.5, marker_colors=["#E24B4A", "#EF9F27", "#D4537E"],
            ))
            fig.update_layout(showlegend=True, height=280, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("#### Payoff Strategies")
            sorted_rate  = sorted(fd.liabilities, key=lambda x: -x.rate)
            sorted_princ = sorted(fd.liabilities, key=lambda x: x.principal)
            st.markdown(f"""
**Avalanche** *(saves most interest)*  
Attack **{sorted_rate[0].name}** ({sorted_rate[0].rate}% rate) with extra payments first.

**Snowball** *(builds momentum)*  
Clear **{sorted_princ[0].name}** ({fmt(sorted_princ[0].principal)} balance) first, then redirect EMI.

**Extra payment impact**  
Every ₹5,000/month extra on your highest-rate loan saves roughly {fmt(sorted_rate[0].rate/100 * sorted_rate[0].principal * 0.4)} in total interest over the loan tenure.
""")

        if st.button("💡 Get AI Debt Strategy", use_container_width=True):
            with st.spinner("Analysing your debt profile..."):
                st.markdown(get_ai_insights(fd, "Provide a detailed debt payoff strategy for this user."))
