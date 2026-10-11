# NC Wealth Corporation Website

A Streamlit landing website with Investing and Trading sections.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Create a new GitHub repository containing `app.py` and `requirements.txt`, then deploy it as a **new** Streamlit Community Cloud app with entrypoint `app.py`. Do not replace the existing EMA screener deployment.

Flow: Home → Investing → EMA Stock Screener (opens existing site). Trading shows a coming-soon page.
