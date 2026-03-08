import streamlit as st

st.markdown("""
<style>
    .stApp { background-color: #f5f7fb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
    section[data-testid="stSidebar"] * { color: #fff !important; }
    section[data-testid="stSidebar"] a { color: #e0d4ff !important; }
    h1, h2, h3 { color: #2d3436 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 💰 Dribbble Profitability")
st.caption("P&L аналітика Dribbble каналу — витрати vs дохід, ROI, окупність")

st.divider()

st.markdown("""
### 🚧 Coming Soon

Ця сторінка покаже рентабельність Dribbble як маркетингового каналу:

**Витрати (Costs):**
- 👨‍💻 Фрілансери (дизайн шотів)
- 📣 Просування та реклама
- 💼 Зарплати (% часу команди на Dribbble)
- 🔧 Підписки (Dribbble Pro, інструменти)

**Дохід (Revenue):**
- 💵 Закриті угоди з Dribbble лідів
- 📊 Дані з Pipedrive CRM (конвертовані ліди)

**Метрики:**
- 📈 **ROI** — return on investment по місяцях
- 💰 **CAC** — вартість залучення клієнта через Dribbble
- ⏱️ **Payback Period** — за скільки місяців канал окупається
- 📊 **Revenue per Shot** — дохід на 1 опублікований шот
- 🔄 **Conversion Rate** — % лідів що стали клієнтами

**Джерело даних:** QuickBooks API (автоматично)

---

### 🔌 Як підключити

Для автоматичного отримання фінансових даних потрібен **QuickBooks API**:

1. Зайти на [developer.intuit.com](https://developer.intuit.com)
2. Створити акаунт (або увійти через існуючий QuickBooks акаунт)
3. **Create an App** → виберіть QuickBooks Online → Accounting
4. У налаштуваннях app скопіювати:
   - **Client ID**
   - **Client Secret**
   - **Redirect URI** — вказати `https://valmax-dribbble.streamlit.app/callback`
5. **Company ID** (Realm ID) — знайдете в URL коли залогінені в QuickBooks: `https://app.qbo.intuit.com/app/homepage?companyId=XXXXXXX`
6. Надіслати мені Client ID, Client Secret та Company ID

Після цього я:
- Налаштую OAuth2 авторизацію
- Підключу автоматичне отримання P&L звітів
- Зроблю щомісячний cron для оновлення

**Безкоштовно** з існуючою підпискою QuickBooks.
""")

st.divider()

# Placeholder metrics
st.markdown("### 📊 Preview (estimated)")
st.caption("Приблизні дані на основі 25% середньої маржі та даних з CRM")

col1, col2, col3, col4 = st.columns(4)
col1.metric("💵 Est. Revenue (Q1)", "~$45,000", help="Оцінка на основі конвертованих лідів з Pipedrive")
col2.metric("💸 Est. Costs (Q1)", "~$12,000", help="Оцінка: фрілансери + підписки + час команди")
col3.metric("📈 Est. ROI", "~275%", help="(Revenue - Costs) / Costs × 100%")
col4.metric("💰 Est. Profit", "~$33,000", help="Revenue - Costs")

st.caption("⚠️ Це приблизні дані. Точні цифри після підключення QuickBooks.")

st.divider()
st.caption("💰 Profitability | Потрібен QuickBooks API для точних даних")
